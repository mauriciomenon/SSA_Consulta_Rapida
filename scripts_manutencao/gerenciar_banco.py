#!/usr/bin/env python3
"""
Script para gerenciamento do banco de dados e limpeza da pasta data.
Inclui funes para reset do DB, limpeza de backups antigos e sanitizao.
"""

import os
import re
import shutil
import sqlite3
import sys
from contextlib import closing
from datetime import datetime, timedelta
from pathlib import Path

# Adiciona o diretrio raiz do projeto ao PYTHONPATH
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from armazenamento.database import _clear_resolved_table_cache  # noqa: E402
from armazenamento.database_integrity import create_sqlite_backup  # noqa: E402
from armazenamento.database_lock import database_writer_lock  # noqa: E402
from shared.db_names import SSA_READ_REQUIRED_COLUMNS  # noqa: E402
from utils.sqlite_backup import bounded_sqlite_backup  # noqa: E402


def _is_symlink_directory(path: str) -> bool:
    # Ancestrais como /tmp no macOS podem ser aliases validos do sistema.
    # A limpeza recusa links no proprio data/ ou backups/.
    return Path(path).is_symlink()


# Todo artefato de backup gerado carrega um par data_hora
# (%Y%m%d_%H%M%S...). Nomes parecidos sem esse bloco sao arquivos do
# usuario (ex.: ssas_backup_prod.db, loja.db_backup_final.db) e nao
# podem entrar na limpeza.
_BACKUP_TIMESTAMP_RE = re.compile(r"\d{8}_\d{6}", re.ASCII)


def _is_db_backup_name(name: str, db_name: str) -> bool:
    # Backups com apenas o stem nao identificam um banco unico em pasta
    # compartilhada; bancos com extensoes diferentes podem ter o mesmo stem.
    candidate = name.lstrip(".").lower()
    lowered_db = db_name.lower()
    stem = Path(lowered_db).stem
    if candidate.startswith(
        (
            f"{lowered_db}.bak-",
            f"{lowered_db}.backup_",
            f"{lowered_db}.full_rescan_backup_",
            f"{lowered_db}_backup_",
            f"{lowered_db}.bkp",
            f"{lowered_db}_bkp",
        )
    ):
        return bool(_BACKUP_TIMESTAMP_RE.search(candidate))
    # Familia por stem exige o par data_hora logo apos o marcador: um
    # banco real datado por outra convencao (ssas_backup_prod_<ts>.db)
    # nao e confundido com artefato gerado.
    return bool(
        re.match(
            rf"{re.escape(stem)}_emergency_backup_\d{{8}}_\d{{6}}",
            candidate,
            re.ASCII,
        )
        or re.match(
            rf"{re.escape(stem)}_backup_(?:antes_limpeza_final_)?"
            rf"\d{{8}}_\d{{6}}",
            candidate,
            re.ASCII,
        )
    )


def _is_backup_artifact(
    name: str, bound: str, scope: str | None, backup_patterns: list[str]
) -> bool:
    """Artefato gerado de backup: nome ligado ao banco com par data_hora,
    ou (apenas no escopo default) nome generico legado fora da familia
    do stem do banco."""
    if scope:
        return _is_db_backup_name(name, scope)
    if _is_db_backup_name(name, bound):
        return True
    lowered = name.lstrip(".").lower()
    bound_stem = Path(bound).stem.lower()
    if lowered.startswith(
        (f"{bound_stem}_backup_", f"{bound_stem}_emergency_backup_")
    ):
        return False
    # Padroes genericos tambem exigem par data_hora: "backup_relatorio.db"
    # sem timestamp e arquivo do usuario, nao artefato de limpeza.
    return bool(_BACKUP_TIMESTAMP_RE.search(lowered)) and any(
        pattern in lowered for pattern in backup_patterns
    )


def reset_database(db_path="data/ssas.db"):
    """
    Zera o banco de dados e recria apenas a estrutura das tabelas.

    Args:
        db_path (str): Caminho para o arquivo do banco de dados
    """
    print(f"  Resetando banco de dados: {db_path}")
    schema_path = Path(__file__).parent.parent / "config" / "schema.sql"
    schema_sql = schema_path.read_text(encoding="utf-8")

    with database_writer_lock(db_path):
        with closing(sqlite3.connect(":memory:")) as candidate:
            candidate.executescript(schema_sql)
            tables = {
                row[0]
                for row in candidate.execute(
                    "SELECT name FROM sqlite_master WHERE type = 'table'"
                )
            }
            if not {"ssa_table", "ssa_event_records"} <= tables:
                raise sqlite3.DatabaseError("Schema oficial incompleto")
            columns = {
                row[1] for row in candidate.execute("PRAGMA table_info(ssa_table)")
            }
            if set(SSA_READ_REQUIRED_COLUMNS) - columns:
                raise sqlite3.DatabaseError("Schema oficial sem colunas obrigatorias")
            if candidate.execute("PRAGMA quick_check").fetchone() != ("ok",):
                raise sqlite3.DatabaseError("Schema oficial falhou no quick_check")

            destination = Path(db_path)
            if destination.is_symlink():
                raise RuntimeError(f"Reset recusado: destino e symlink: {db_path}")
            if destination.exists():
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
                backup_path = f"{db_path}.backup_before_reset_{timestamp}"
                create_sqlite_backup(destination, backup_path)
                print(f" Backup criado: {backup_path}")

            created_here = False
            try:
                if not destination.exists():
                    # Instalacao nova: a pasta de dados pode ainda nao existir.
                    destination.parent.mkdir(parents=True, exist_ok=True)
                    sidecars = (
                        Path(f"{db_path}-wal"),
                        Path(f"{db_path}-shm"),
                        Path(f"{db_path}-journal"),
                    )
                    if any(os.path.lexists(path) for path in sidecars):
                        raise RuntimeError(
                            "Banco novo recusado: sidecars SQLite preexistentes"
                        )
                    descriptor = os.open(destination, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
                    created_here = True
                    os.close(descriptor)
                with closing(sqlite3.connect(destination, timeout=5)) as current:
                    bounded_sqlite_backup(candidate, current)
            except Exception:
                if created_here:
                    for created_path in (destination, *sidecars):
                        created_path.unlink(missing_ok=True)
                raise

        _clear_resolved_table_cache(db_path)
    print(f" Reset completo! Banco zerado em: {db_path}")


def clean_old_backups(
    data_dir="data", days_to_keep=7, db_basename=None, scope_name=None
):
    """
    Remove backups antigos da pasta data (mantm apenas os ltimos X dias).

    Args:
        data_dir (str): Diretrio data
        days_to_keep (int): Nmero de dias de backups para manter
    """
    print(f" Limpando backups antigos (mantendo ltimos {days_to_keep} dias)")

    cutoff_date = datetime.now() - timedelta(days=days_to_keep)
    removed_count = 0
    total_size_removed = 0

    # Padres de arquivos de backup
    backup_patterns = [
        "backup_",
        "ssas_backup_",
        "ssas_emergency_backup_",
        ".backup_",
        "_bkp",
        ".bkp",
        # Arquivo anterior preservado na promocao de copia e no import de
        # emergencia (<db>.bak-<timestamp> e sidecars).
        ".bak-",
    ]

    if _is_symlink_directory(data_dir):
        raise RuntimeError(f"Limpeza recusada: diretorio contem symlink: {data_dir}")
    data_path = Path(data_dir)
    backups_path = data_path / "backups"
    if _is_symlink_directory(str(backups_path)):
        raise RuntimeError(f"Limpeza recusada: backups contem symlink: {backups_path}")
    # Escopo customizado usa o nome completo do banco. Nome parecido de outro
    # arquivo nao autoriza limpeza em pasta compartilhada.
    scope = scope_name if scope_name is not None else db_basename
    # O banco ativo e seus sidecars nunca entram na limpeza, mesmo quando o
    # nome nao e o literal "ssas.db" (SSA_DB_PATH customizado).
    protected = {
        f"{db_basename}{suffix}"
        for suffix in ("", "-wal", "-shm", "-journal")
    } if db_basename else {"ssas.db"}
    bound = db_basename or "ssas.db"

    def _in_scope(name: str) -> bool:
        return not scope or _is_db_backup_name(name, scope)

    # Limpa pasta data principal
    for file_path in data_path.glob("*"):
        if file_path.is_file() and file_path.name not in protected and _in_scope(file_path.name):
            # Verifica se  um arquivo de backup
            is_backup = _is_backup_artifact(
                file_path.name, bound, scope, backup_patterns
            )

            if is_backup:
                file_time = datetime.fromtimestamp(file_path.stat().st_mtime)
                if file_time < cutoff_date:
                    file_size = file_path.stat().st_size
                    print(f"   Removendo: {file_path.name} ({file_size:,} bytes)")
                    file_path.unlink()
                    removed_count += 1
                    total_size_removed += file_size

    # Limpa pasta backups (mesmo filtro de padrao da pasta principal:
    # arquivo solto ali que nao seja backup nao pode ser removido)
    if backups_path.exists():
        for file_path in backups_path.glob("*"):
            if file_path.is_file() and file_path.name not in protected and _in_scope(file_path.name):
                if not _is_backup_artifact(
                    file_path.name, bound, scope, backup_patterns
                ):
                    continue
                file_time = datetime.fromtimestamp(file_path.stat().st_mtime)
                if file_time < cutoff_date:
                    file_size = file_path.stat().st_size
                    print(
                        f"   Removendo: backups/{file_path.name} ({file_size:,} bytes)"
                    )
                    file_path.unlink()
                    removed_count += 1
                    total_size_removed += file_size

    print(f" Limpeza concluda: {removed_count} arquivos removidos")
    print(
        f" Espao liberado: {total_size_removed:,} bytes ({total_size_removed / 1024 / 1024:.1f} MB)"
    )


def _remove_temporary_files(data_path: Path, scope: str | None, protected: set[str]) -> int:
    removed_temp = 0
    if scope:
        def _is_scoped_temp(name: str) -> bool:
            # Nomes genericos como <banco>.bak ou <banco>.tmp sao copias
            # manuais comuns do usuario; no escopo restrito so saem os
            # temporarios sufixados/instrumentados que a ferramenta cria.
            candidate = name.lstrip(".")
            if candidate.startswith(
                (f"{scope}.tmp-", f"{scope}.tmp.", f"{scope}.temp-", f"{scope}.temp.")
            ):
                return True
            return candidate.endswith(".tmp") and (
                candidate.startswith(
                    (f"{scope}.integrity_", f"{scope}.restore_", f"{scope}.rollback_")
                )
                or name.startswith(f".{scope}.")
            )

        temp_files = (
            path for path in data_path.glob("*")
            if _is_scoped_temp(path.name)
        )
    else:
        temp_files = (
            path
            for pattern in ("*.tmp", "*.temp", "*~", "*.swp", "*.bak")
            for path in data_path.glob(pattern)
        )
    for file_path in temp_files:
        if not file_path.is_file() or file_path.name in protected:
            continue
        print(f"    Removendo temp: {file_path.name}")
        file_path.unlink()
        removed_temp += 1
    return removed_temp


def sanitize_data_folder(data_dir="data", db_basename=None, scope_name=None):
    """
    Sanitiza a pasta data removendo arquivos temporrios e organizando estrutura.

    Args:
        data_dir (str): Diretrio data
    """
    print(f" Sanitizando pasta: {data_dir}")

    data_path = Path(data_dir)
    if _is_symlink_directory(data_dir):
        print(f"  Sanitizacao recusada: caminho contem symlink: {data_dir}")
        return
    if data_path.exists() and not data_path.is_dir():
        print(
            "  Sanitizacao recusada: caminho existe e nao e diretorio: "
            f"{data_dir}"
        )
        return
    if not data_path.is_dir():
        data_path.mkdir(parents=True, exist_ok=True)
    backups_path = data_path / "backups"
    if _is_symlink_directory(str(backups_path)):
        print(f"  Sanitizacao recusada: backups contem symlink: {backups_path}")
        return

    scope = scope_name if scope_name is not None else db_basename
    protected_sanitize = {
        f"{db_basename}{suffix}"
        for suffix in ("", "-wal", "-shm", "-journal")
    } if db_basename else {"ssas.db"}
    removed_temp = _remove_temporary_files(data_path, scope, protected_sanitize)

    # Garante que a pasta backups existe
    if not backups_path.exists():
        backups_path.mkdir()
        print("   Pasta backups criada")

    # Move backups soltos para a pasta backups
    moved_backups = 0
    backup_patterns = ["backup_", "ssas_backup_", "ssas_emergency_backup_", ".backup_"]
    bound = db_basename or "ssas.db"

    for file_path in data_path.glob("*"):
        if file_path.is_file() and file_path.name not in protected_sanitize:
            if not _is_backup_artifact(
                file_path.name, bound, scope, backup_patterns
            ):
                continue
            new_path = backups_path / file_path.name
            # Revalida no ponto de uso: a pasta pode ter sido trocada por
            # um symlink depois da checagem inicial.
            if _is_symlink_directory(str(backups_path)):
                print(
                    "  Sanitizacao interrompida: backups virou symlink: "
                    f"{backups_path}"
                )
                break
            if not new_path.exists():
                print(f"   Movendo backup: {file_path.name} -> backups/")
                shutil.move(str(file_path), str(new_path))
                moved_backups += 1

    print(" Sanitizao concluda:")
    print(f"  - {removed_temp} arquivos temporrios removidos")
    print(f"  - {moved_backups} backups organizados")


def show_data_status(data_dir="data"):
    """
    Mostra status atual da pasta data e poltica de backup.

    Args:
        data_dir (str): Diretrio data
    """
    print(f"Status da pasta: {data_dir}")

    data_path = Path(data_dir)

    if not data_path.exists():
        print("ERRO: Pasta data no encontrada!")
        return

    # Arquivo principal
    main_db = data_path / "ssas.db"
    if main_db.exists():
        size = main_db.stat().st_size
        modified = datetime.fromtimestamp(main_db.stat().st_mtime)
        print(f"  DB Principal: ssas.db ({size:,} bytes, modificado: {modified})")
    else:
        print("  ERRO: Banco principal (ssas.db) no encontrado!")

    # Backups na pasta principal
    backup_patterns = ["backup_", "ssas_backup_", "ssas_emergency_backup_", ".backup_"]
    main_backups = []

    for file_path in data_path.glob("*"):
        if file_path.is_file() and file_path.name != "ssas.db":
            is_backup = any(
                pattern in file_path.name.lower() for pattern in backup_patterns
            )
            if is_backup:
                main_backups.append(file_path)

    print(f"  Backups na pasta principal: {len(main_backups)}")

    # Backups na pasta backups
    backups_path = data_path / "backups"
    folder_backups = []
    if backups_path.exists():
        folder_backups = list(backups_path.glob("*"))

    print(f"  Backups na pasta backups/: {len(folder_backups)}")

    # Total de espao usado
    total_size = 0
    for file_path in data_path.rglob("*"):
        if file_path.is_file():
            total_size += file_path.stat().st_size

    print(
        f"  Espao total usado: {total_size:,} bytes ({total_size / 1024 / 1024:.1f} MB)"
    )

    # Poltica de backup recomendada
    print("\nPoltica de Backup Recomendada:")
    print("  - Manter backups dos ltimos 7 dias")
    print("  - Backups automticos antes de operaes crticas")
    print("  - Organizar backups na pasta data/backups/")
    print("  - Limpeza automtica de backups antigos")


def main():
    """Funo principal com menu interativo."""
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()

        if command == "reset":
            reset_database()
        elif command == "clean":
            days = int(sys.argv[2]) if len(sys.argv) > 2 else 7
            clean_old_backups(days_to_keep=days)
        elif command == "sanitize":
            sanitize_data_folder()
        elif command == "status":
            show_data_status()
        else:
            print("Comandos disponveis: reset, clean [dias], sanitize, status")
    else:
        # Menu interativo
        print("  Gerenciador do Banco de Dados SSA")
        print("\nOpes disponveis:")
        print("1. Reset do banco (zerar e recriar estrutura)")
        print("2. Limpar backups antigos")
        print("3. Sanitizar pasta data")
        print("4. Mostrar status")
        print("0. Sair")

        while True:
            choice = input("\nEscolha uma opo (0-4): ").strip()

            if choice == "1":
                confirm = (
                    input("  Tem certeza que quer ZERAR o banco? (sim/no): ")
                    .strip()
                    .lower()
                )
                if confirm in ["sim", "s", "yes", "y"]:
                    reset_database()
                else:
                    print(" Operao cancelada")
                break
            elif choice == "2":
                days_text = input(
                    "Manter backups dos ltimos quantos dias? (padro: 7): "
                ).strip()
                days = int(days_text) if days_text.isdigit() else 7
                clean_old_backups(days_to_keep=days)
                break
            elif choice == "3":
                sanitize_data_folder()
                break
            elif choice == "4":
                show_data_status()
                break
            elif choice == "0":
                print(" Saindo...")
                break
            else:
                print(" Opo invlida!")


if __name__ == "__main__":
    main()
