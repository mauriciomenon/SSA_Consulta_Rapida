"""Database operations used by GUI controllers."""

from __future__ import annotations

import os
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Callable


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
        test_df = query_db_fn(db_file, table_name, raise_on_error=True)
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
    if dest == src:
        return {
            "ok": True,
            "db_file": str(src),
            "copied": False,
            "archived": None,
            "error": None,
        }

    archived_base: str | None = None
    if dest.exists():
        archived_base = f"{dest}.bak-{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"
        # Mesma ordem segura do emergency_import: WAL/ShM antes do .db.
        for suffix in ("-wal", "-shm", ""):
            stale = Path(f"{dest}{suffix}")
            if not stale.exists():
                continue
            try:
                os.replace(stale, f"{archived_base}{suffix}")
            except OSError as exc:
                return {
                    "ok": False,
                    "db_file": str(dest),
                    "copied": False,
                    "archived": archived_base,
                    "error": f"falha ao arquivar banco existente {stale}: {exc}",
                }

    dest_created = False
    try:
        source_uri = src.as_uri() + "?mode=ro"
        with sqlite3.connect(source_uri, uri=True) as source_conn:
            with sqlite3.connect(str(dest)) as dest_conn:
                dest_created = True
                source_conn.backup(dest_conn)
    except (OSError, sqlite3.Error, ValueError) as exc:
        if dest_created or dest.exists():
            # O destino neste path e produto desta chamada: a copia
            # original foi arquivada acima ou nunca existiu.
            for suffix in ("-wal", "-shm", ""):
                partial = Path(f"{dest}{suffix}")
                if partial.exists():
                    try:
                        os.remove(partial)
                    except OSError:
                        continue
        return {
            "ok": False,
            "db_file": str(dest),
            "copied": False,
            "archived": archived_base,
            "error": f"falha ao copiar banco: {exc}",
        }

    return {
        "ok": True,
        "db_file": str(dest),
        "copied": True,
        "archived": archived_base,
        "error": None,
    }
