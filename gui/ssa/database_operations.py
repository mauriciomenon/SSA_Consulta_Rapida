"""Database operations used by GUI controllers."""

from __future__ import annotations

import logging
import os
import sqlite3
from contextlib import closing
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

from armazenamento.database import read_only_sqlite_uri

logger = logging.getLogger(__name__)


def execute_vacuum_analyze(
    db_path: str, vacuum_analyze_database_fn: Callable[[str], dict[str, Any]]
) -> dict[str, Any]:
    return vacuum_analyze_database_fn(db_path)


def validate_database_candidate(
    db_file: str,
    *,
    table_name: str,
    query_db_fn: Callable[..., Any],
) -> dict[str, Any]:
    try:
        # read_only: a validacao de um arquivo escolhido pelo usuario nao
        # pode escrever no .db dele (ex.: recuperacao de -journal quente).
        test_df = query_db_fn(db_file, table_name, raise_on_error=True, read_only=True)
    except Exception as exc:
        return {"ok": False, "error": str(exc), "db_file": db_file}
    has_rows = bool(test_df is not None and not test_df.empty)
    return {"ok": has_rows, "db_file": db_file}


def copy_database_into_data_dir(
    source_path: str,
    *,
    data_dir: str,
) -> dict[str, Any]:
    """Copia um banco externo para ``data_dir`` sem alterar a origem.

    Usa a backup API do SQLite com a origem aberta em modo read-only, o
    que produz um snapshot consistente inclusive com WAL aberto. Um
    destino existente e arquivado como ``.bak-<timestamp>`` (nunca
    sobrescrito); se a origem ja estiver dentro de ``data_dir`` a
    funcao e um no-op.

    Retorna ``{"ok": bool, "db_file": <destino>, "copied": bool,
    "archived": <base do backup ou None>, "error": <msg ou None>}``.
    """
    try:
        src = Path(source_path).expanduser().resolve()
    except (OSError, RuntimeError, ValueError) as exc:
        return {
            "ok": False,
            "db_file": source_path,
            "copied": False,
            "archived": None,
            "error": f"caminho de origem invalido: {exc}",
        }
    if not src.is_file():
        return {
            "ok": False,
            "db_file": str(src),
            "copied": False,
            "archived": None,
            "error": "arquivo de origem nao existe",
        }
    try:
        dest_dir = Path(data_dir).expanduser().resolve()
        dest_dir.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        return {
            "ok": False,
            "db_file": source_path,
            "copied": False,
            "archived": None,
            "error": f"falha ao preparar diretorio de dados: {exc}",
        }
    dest = dest_dir / src.name
    # Identidade precisa considerar aliases do filesystem: em volumes
    # case-insensitive (APFS/NTFS padrao) "data" e "Data" resolvem para o
    # mesmo inode, e a comparacao de strings deixaria a propria origem ser
    # arquivada como destino antigo.
    same_file = dest == src
    if not same_file and dest.exists():
        try:
            same_file = os.path.samefile(dest, src)
        except OSError:
            same_file = False
    if same_file:
        return {
            "ok": True,
            "db_file": str(src),
            "copied": False,
            "archived": None,
            "error": None,
        }

    staged_result = stage_database_copy(src, dest)
    if not staged_result.get("ok"):
        return staged_result
    return commit_staged_database_copy(
        str(staged_result["staged"]), str(staged_result["dest"])
    )


def stage_database_copy(src: Path, dest: Path) -> dict[str, Any]:
    """Grava o snapshot da origem em arquivo de staging ao lado do destino.

    Nao toca no destino: a promocao acontece em commit_staged_database_copy,
    o que permite ao chamador decidir (ou descartar) depois da copia pesada.
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    staged = dest.with_name(f"{dest.name}.copy-{timestamp}")
    try:
        # mode=ro (inclusive em UNC): a leitura nao pode disparar
        # recuperacao de journal quente na origem.
        source_uri = read_only_sqlite_uri(str(src))
        with closing(sqlite3.connect(source_uri, uri=True)) as source_conn:
            with closing(sqlite3.connect(str(staged))) as staged_conn:
                source_conn.backup(staged_conn)
    except (OSError, sqlite3.Error, ValueError) as exc:
        discard_staged_copy(staged)
        return {
            "ok": False,
            "db_file": str(dest),
            "copied": False,
            "archived": None,
            "error": f"falha ao copiar banco: {exc}",
        }
    return {
        "ok": True,
        "staged": str(staged),
        "dest": str(dest),
        "timestamp": timestamp,
        "db_file": str(dest),
        "copied": True,
        "archived": None,
        "error": None,
    }


def discard_staged_copy(staged: str | Path) -> None:
    """Remove arquivo de staging e sidecars orfaos (best-effort)."""
    for suffix in ("-wal", "-shm", "-journal", ""):
        partial = Path(f"{staged}{suffix}")
        if partial.exists():
            try:
                os.remove(partial)
            except OSError as exc:
                logger.warning(
                    "Falha ao remover copia parcial %s: %s", partial, exc
                )


def commit_staged_database_copy(staged: str, dest_str: str) -> dict[str, Any]:
    """Arquiva o destino existente e promove o staging atomicamente.

    Apenas renames (metadados), entao e seguro rodar na thread de UI. Em
    falha, restaura o que foi arquivado para manter o banco anterior
    utilizavel.
    """
    dest = Path(dest_str)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    archived_base: str | None = None
    moved: list[tuple[str, str]] = []
    # Arquiva o destino existente (sidecars antes do .db, como no
    # emergency_import; sidecars orfaos tambem sao arquivados).
    dest_sidecars = [dest] + [
        Path(f"{dest}{s}") for s in ("-wal", "-shm", "-journal")
    ]
    if any(p.exists() for p in dest_sidecars):
        archived_base = f"{dest}.bak-{timestamp}"
        for suffix in ("-wal", "-shm", "-journal", ""):
            stale = Path(f"{dest}{suffix}")
            if not stale.exists():
                continue
            target = f"{archived_base}{suffix}"
            try:
                os.replace(stale, target)
            except OSError as exc:
                for orig, archived_name in reversed(moved):
                    try:
                        os.replace(archived_name, orig)
                    except OSError as restore_exc:
                        logger.error(
                            "Falha ao restaurar %s de %s: %s",
                            orig,
                            archived_name,
                            restore_exc,
                        )
                discard_staged_copy(staged)
                return {
                    "ok": False,
                    "db_file": str(dest),
                    "copied": False,
                    "archived": archived_base,
                    "error": f"falha ao arquivar banco existente {stale}: {exc}",
                }
            moved.append((str(stale), target))

    try:
        os.replace(staged, dest)
    except OSError as exc:
        for orig, archived_name in reversed(moved):
            try:
                os.replace(archived_name, orig)
            except OSError as restore_exc:
                logger.error(
                    "Falha ao restaurar %s de %s: %s",
                    orig,
                    archived_name,
                    restore_exc,
                )
        discard_staged_copy(staged)
        return {
            "ok": False,
            "db_file": str(dest),
            "copied": False,
            "archived": archived_base,
            "error": f"falha ao promover copia para {dest}: {exc}",
        }

    return {
        "ok": True,
        "db_file": str(dest),
        "copied": True,
        "archived": archived_base,
        "error": None,
    }
