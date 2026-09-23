"""Database metadata access for DataLoaderWorker."""

from __future__ import annotations

import sqlite3
import threading
from contextlib import closing

from gui.workers.data_loader_query import quote_identifier, sanitize_identifier
from shared.db_names import ALL_SSA_TABLE_NAMES, CANONICAL_SSA_TABLE

TABLE_RESOLUTION_CACHE: dict[tuple[str, str], str] = {}
TABLE_RESOLUTION_LOCK = threading.Lock()


def resolve_target_table(db_path: str, table_name: str) -> str:
    cache_key = (str(db_path), str(table_name))
    with TABLE_RESOLUTION_LOCK:
        cached_table = TABLE_RESOLUTION_CACHE.get(cache_key)
    if cached_table:
        return cached_table

    requested = sanitize_identifier(table_name)
    candidates = []
    if requested:
        candidates.append(requested)
    for name in ALL_SSA_TABLE_NAMES:
        if name not in candidates:
            candidates.append(name)

    resolved_table = ""
    try:
        with closing(sqlite3.connect(db_path)) as conn:
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
        TABLE_RESOLUTION_CACHE[cache_key] = resolved_table
    return resolved_table


def resolve_table_columns(db_path: str, table_name: str) -> tuple[str, ...]:
    target_table = sanitize_identifier(table_name)
    if not target_table:
        return ()
    try:
        with closing(sqlite3.connect(db_path)) as conn:
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
