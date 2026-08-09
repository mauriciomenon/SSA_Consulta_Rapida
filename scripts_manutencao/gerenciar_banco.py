#!/usr/bin/env python3
"""
Script para gerenciamento do banco de dados e limpeza da pasta data.
Inclui funes para reset do DB, limpeza de backups antigos e sanitizao.
"""

import os
import shutil
import sqlite3
import sys
from contextlib import closing
from datetime import datetime, timedelta
from pathlib import Path

# Adiciona o diretrio raiz do projeto ao PYTHONPATH
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Imports simplificados - evita dependncias complexas durante import
# from armazenamento.database import get_db_connection


def reset_database(db_path="data/ssas.db"):
    """
    Zera o banco de dados e recria apenas a estrutura das tabelas.

    Args:
        db_path (str): Caminho para o arquivo do banco de dados
    """
    print(f"  Resetando banco de dados: {db_path}")

    # Remove o arquivo do banco se existir
    if os.path.exists(db_path):
        # Faz backup antes de remover
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        backup_path = f"{db_path}.backup_before_reset_{timestamp}"
        source_path = Path(db_path).resolve()
        try:
            with closing(
                sqlite3.connect(f"{source_path.as_uri()}?mode=ro", uri=True)
            ) as source_conn:
                with closing(sqlite3.connect(backup_path)) as backup_conn:
                    source_conn.backup(backup_conn)
                    if backup_conn.execute("PRAGMA quick_check").fetchone() != ("ok",):
                        raise sqlite3.DatabaseError("backup falhou no quick_check")
        except (OSError, sqlite3.Error):
            Path(backup_path).unlink(missing_ok=True)
            raise
        print(f" Backup criado: {backup_path}")

        for database_file in (
            Path(db_path),
            Path(f"{db_path}-wal"),
            Path(f"{db_path}-shm"),
        ):
            database_file.unlink(missing_ok=True)
        print(f" Arquivo do banco removido: {db_path}")

    # Cria o banco usando o schema oficial
    schema_path = os.path.join(os.path.dirname(__file__), "..", "config", "schema.sql")

    with closing(sqlite3.connect(db_path)) as conn:
        # Lê e executa o schema oficial
        if os.path.exists(schema_path):
            with open(schema_path, "r", encoding="utf-8") as f:
                schema_sql = f.read()
            conn.executescript(schema_sql)
            print(" Estrutura das tabelas recriada usando schema oficial")
        else:
            # Fallback - cria tabela básica caso schema.sql não exista
            create_table_sql = """
            CREATE TABLE IF NOT EXISTS ssa_table (
                numero_ssa INTEGER PRIMARY KEY,
                situacao TEXT,
                setor_executor TEXT,
                descricao_ssa TEXT,
                data_cadastro TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """
            conn.execute(create_table_sql)
            print(" Estrutura básica da tabela criada (schema.sql não encontrado)")

        conn.commit()

    print(f" Reset completo! Banco zerado em: {db_path}")


def clean_old_backups(data_dir="data", days_to_keep=7):
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
    ]

    data_path = Path(data_dir)

    # Limpa pasta data principal
    for file_path in data_path.glob("*"):
        if file_path.is_file():
            # Verifica se  um arquivo de backup
            is_backup = any(
                pattern in file_path.name.lower() for pattern in backup_patterns
            )

            if is_backup:
                file_time = datetime.fromtimestamp(file_path.stat().st_mtime)
                if file_time < cutoff_date:
                    file_size = file_path.stat().st_size
                    print(f"   Removendo: {file_path.name} ({file_size:,} bytes)")
                    file_path.unlink()
                    removed_count += 1
                    total_size_removed += file_size

    # Limpa pasta backups
    backups_path = data_path / "backups"
    if backups_path.exists():
        for file_path in backups_path.glob("*"):
            if file_path.is_file():
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


def sanitize_data_folder(data_dir="data"):
    """
    Sanitiza a pasta data removendo arquivos temporrios e organizando estrutura.

    Args:
        data_dir (str): Diretrio data
    """
    print(f" Sanitizando pasta: {data_dir}")

    data_path = Path(data_dir)

    # Remove arquivos temporrios
    temp_patterns = ["*.tmp", "*.temp", "*~", "*.swp", "*.bak"]
    removed_temp = 0

    for pattern in temp_patterns:
        for file_path in data_path.glob(pattern):
            print(f"    Removendo temp: {file_path.name}")
            file_path.unlink()
            removed_temp += 1

    # Garante que a pasta backups existe
    backups_path = data_path / "backups"
    if not backups_path.exists():
        backups_path.mkdir()
        print("   Pasta backups criada")

    # Move backups soltos para a pasta backups
    moved_backups = 0
    backup_patterns = ["backup_", "ssas_backup_", "ssas_emergency_backup_", ".backup_"]

    for file_path in data_path.glob("*"):
        if file_path.is_file() and file_path.name != "ssas.db":
            is_backup = any(
                pattern in file_path.name.lower() for pattern in backup_patterns
            )
            if is_backup:
                new_path = backups_path / file_path.name
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
