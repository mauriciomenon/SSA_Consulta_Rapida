"""Database metadata access for DataLoaderWorker."""

from __future__ import annotations

import sqlite3
import threading
from contextlib import closing
from pathlib import Path

from armazenamento.database import read_only_sqlite_uri
from gui.workers.data_loader_query import quote_identifier, sanitize_identifier
from shared.db_names import ALL_SSA_TABLE_NAMES, CANONICAL_SSA_TABLE

TABLE_RESOLUTION_CACHE: dict[tuple[str, str], tuple[tuple, str]] = {}
TABLE_RESOLUTION_LOCK = threading.Lock()


def _connect_metadata(db_path: str) -> sqlite3.Connection:
    if db_path == ":memory:":
        return sqlite3.connect(db_path)
    return sqlite3.connect(read_only_sqlite_uri(db_path), uri=True)


def _database_generation(db_path: str) -> tuple | None:
    if db_path == ":memory:":
        return None
    path = Path(db_path).resolve()
    parts = []
    for suffix in ("", "-wal", "-journal"):
        try:
            stat = Path(f"{path}{suffix}").stat()
        except FileNotFoundError:
            if not suffix:
                return None
            parts.append(None)
        except OSError:
            return None
        else:
            parts.append((stat.st_dev, stat.st_ino, stat.st_size, stat.st_mtime_ns))
    return str(path), tuple(parts)


def resolve_target_table(db_path: str, table_name: str) -> str:
    cache_key = (str(db_path), str(table_name))
    generation = _database_generation(db_path)
    with TABLE_RESOLUTION_LOCK:
        cached = TABLE_RESOLUTION_CACHE.get(cache_key) if generation else None
    if cached and cached[0] == generation:
        return cached[1]

    requested = sanitize_identifier(table_name)
    candidates = []
    if requested:
        candidates.append(requested)
    for name in ALL_SSA_TABLE_NAMES:
        if name not in candidates:
            candidates.append(name)

    resolved_table = ""
    try:
        with closing(_connect_metadata(db_path)) as conn:
            rows = conn.execute(
                "SELECT name FROM sqlite_master WHERE type IN ('table','view')"
            ).fetchall()
            existing = {str(row[0]) for row in rows if row and row[0]}
        for candidate in candidates:
            if candidate in existing:
                resolved_table = candidate
                break
    except (sqlite3.Error, OSError):
        resolved_table = ""

    if not resolved_table:
        fallback = candidates[0] if candidates else CANONICAL_SSA_TABLE
        resolved_table = sanitize_identifier(fallback) or CANONICAL_SSA_TABLE

    with TABLE_RESOLUTION_LOCK:
        if generation:
            TABLE_RESOLUTION_CACHE[cache_key] = (generation, resolved_table)
        else:
            TABLE_RESOLUTION_CACHE.pop(cache_key, None)
    return resolved_table


def resolve_table_columns(db_path: str, table_name: str) -> tuple[str, ...]:
    target_table = sanitize_identifier(table_name)
    if not target_table:
        return ()
    try:
        with closing(_connect_metadata(db_path)) as conn:
            rows = conn.execute(
                f"PRAGMA table_info({quote_identifier(target_table)})"  # nosec B608
            ).fetchall()
    except (sqlite3.Error, OSError):
        return ()
    columns = []
    for row in rows:
        if len(row) < 2:
            continue
        column = sanitize_identifier(str(row[1]))
        if column:
            columns.append(column)
    return tuple(columns)
