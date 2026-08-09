"""Schema bootstrap for derivadas support tables.

This module exists to keep derivadas schema setup isolated from legacy import
flows. It can be safely called before sync/query routines without affecting GUI.
"""

from __future__ import annotations

import logging
import os
import sqlite3
from contextlib import closing
from typing import Any, Iterable

from armazenamento.database import get_db_connection
from armazenamento.identifier_utils import is_valid_identifier
from utils.path_safety import ensure_path_is_allowed

logger = logging.getLogger(__name__)


DERIVADAS_TABLES: tuple[str, ...] = (
    "ssa_derivada_matrix",
    "ssa_derivada_source",
    "ssa_derivada_closure",
    "ssa_derivada_summary",
    "ssa_derivada_sync_run",
)

EXPECTED_COLUMNS: dict[str, dict[str, str]] = {
    "ssa_derivada_matrix": {
        "parent_ssa": "TEXT NOT NULL",
        "child_ssa": "TEXT NOT NULL",
        "source_flags": "INTEGER NOT NULL DEFAULT 0",
        "relation_type": "INTEGER NOT NULL DEFAULT 0",
        "relation_raw_label": "TEXT",
        "active": "INTEGER NOT NULL DEFAULT 1",
        "first_seen_at": "TEXT NOT NULL",
        "last_seen_at": "TEXT NOT NULL",
        "last_sync_at": "TEXT NOT NULL",
    },
    "ssa_derivada_source": {
        "parent_ssa": "TEXT NOT NULL",
        "child_ssa": "TEXT NOT NULL",
        "source_name": "TEXT NOT NULL",
        "source_flag": "INTEGER NOT NULL DEFAULT 0",
        "relation_type": "INTEGER NOT NULL DEFAULT 0",
        "relation_raw_label": "TEXT",
        "is_active": "INTEGER NOT NULL DEFAULT 1",
        "first_seen_at": "TEXT NOT NULL",
        "last_seen_at": "TEXT NOT NULL",
        "last_sync_at": "TEXT NOT NULL",
    },
    "ssa_derivada_closure": {
        "ancestor_ssa": "TEXT NOT NULL",
        "descendant_ssa": "TEXT NOT NULL",
        "min_distance": "INTEGER NOT NULL",
        "max_distance": "INTEGER NOT NULL",
        "path_count": "INTEGER NOT NULL DEFAULT 1",
        "last_sync_at": "TEXT NOT NULL",
    },
    "ssa_derivada_summary": {
        "ssa": "TEXT",
        "direct_parents_count": "INTEGER NOT NULL DEFAULT 0",
        "direct_children_count": "INTEGER NOT NULL DEFAULT 0",
        "ancestors_count": "INTEGER NOT NULL DEFAULT 0",
        "descendants_count": "INTEGER NOT NULL DEFAULT 0",
        "level_from_root_min": "INTEGER",
        "level_from_root_max": "INTEGER",
        "levels_above_max": "INTEGER NOT NULL DEFAULT 0",
        "levels_below_max": "INTEGER NOT NULL DEFAULT 0",
        "component_size": "INTEGER NOT NULL DEFAULT 1",
        "has_cycle": "INTEGER NOT NULL DEFAULT 0",
        "last_sync_at": "TEXT NOT NULL",
    },
    "ssa_derivada_sync_run": {
        "sync_run_id": "INTEGER",
        "mode": "TEXT NOT NULL",
        "actor": "TEXT NOT NULL DEFAULT ''",
        "managed_sources": "TEXT NOT NULL DEFAULT ''",
        "started_at": "TEXT NOT NULL",
        "finished_at": "TEXT",
        "status": "TEXT NOT NULL DEFAULT 'running'",
        "db_edges": "INTEGER NOT NULL DEFAULT 0",
        "sheet_edges": "INTEGER NOT NULL DEFAULT 0",
        "merged_edges": "INTEGER NOT NULL DEFAULT 0",
        "active_edges": "INTEGER NOT NULL DEFAULT 0",
        "conflict_count": "INTEGER NOT NULL DEFAULT 0",
        "multiparent_count": "INTEGER NOT NULL DEFAULT 0",
        "orphan_parent_count": "INTEGER NOT NULL DEFAULT 0",
        "orphan_child_count": "INTEGER NOT NULL DEFAULT 0",
        "cycle_node_count": "INTEGER NOT NULL DEFAULT 0",
        "graph_fingerprint": "TEXT",
        "message": "TEXT",
    },
}

READ_REQUIRED_COLUMNS: dict[str, set[str]] = {
    "ssa_derivada_matrix": {"parent_ssa", "child_ssa", "source_flags", "active"},
    "ssa_derivada_closure": {
        "ancestor_ssa",
        "descendant_ssa",
        "min_distance",
        "max_distance",
        "path_count",
    },
    "ssa_derivada_summary": {
        "ssa",
        "direct_parents_count",
        "direct_children_count",
        "ancestors_count",
        "descendants_count",
        "level_from_root_min",
        "level_from_root_max",
        "levels_above_max",
        "levels_below_max",
        "component_size",
        "has_cycle",
        "last_sync_at",
    },
}

DERIVADAS_TABLES_SQL = """
CREATE TABLE IF NOT EXISTS ssa_derivada_matrix (
    parent_ssa TEXT NOT NULL,
    child_ssa TEXT NOT NULL,
    source_flags INTEGER NOT NULL DEFAULT 0,
    relation_type INTEGER NOT NULL DEFAULT 0,
    relation_raw_label TEXT,
    active INTEGER NOT NULL DEFAULT 1,
    first_seen_at TEXT NOT NULL,
    last_seen_at TEXT NOT NULL,
    last_sync_at TEXT NOT NULL,
    PRIMARY KEY (parent_ssa, child_ssa),
    CHECK (parent_ssa <> child_ssa),
    CHECK (length(parent_ssa) = 9),
    CHECK (length(child_ssa) = 9),
    CHECK (parent_ssa GLOB '[0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9]'),
    CHECK (child_ssa GLOB '[0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9]'),
    CHECK (source_flags >= 0),
    CHECK (active IN (0, 1))
);

CREATE TABLE IF NOT EXISTS ssa_derivada_source (
    parent_ssa TEXT NOT NULL,
    child_ssa TEXT NOT NULL,
    source_name TEXT NOT NULL,
    source_flag INTEGER NOT NULL DEFAULT 0,
    relation_type INTEGER NOT NULL DEFAULT 0,
    relation_raw_label TEXT,
    is_active INTEGER NOT NULL DEFAULT 1,
    first_seen_at TEXT NOT NULL,
    last_seen_at TEXT NOT NULL,
    last_sync_at TEXT NOT NULL,
    PRIMARY KEY (parent_ssa, child_ssa, source_name),
    CHECK (parent_ssa <> child_ssa),
    CHECK (length(parent_ssa) = 9),
    CHECK (length(child_ssa) = 9),
    CHECK (parent_ssa GLOB '[0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9]'),
    CHECK (child_ssa GLOB '[0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9]'),
    CHECK (source_name <> ''),
    CHECK (source_flag >= 0),
    CHECK (is_active IN (0, 1))
);

CREATE TABLE IF NOT EXISTS ssa_derivada_closure (
    ancestor_ssa TEXT NOT NULL,
    descendant_ssa TEXT NOT NULL,
    min_distance INTEGER NOT NULL,
    max_distance INTEGER NOT NULL,
    path_count INTEGER NOT NULL DEFAULT 1,
    last_sync_at TEXT NOT NULL,
    PRIMARY KEY (ancestor_ssa, descendant_ssa),
    CHECK (ancestor_ssa <> descendant_ssa),
    CHECK (length(ancestor_ssa) = 9),
    CHECK (length(descendant_ssa) = 9),
    CHECK (ancestor_ssa GLOB '[0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9]'),
    CHECK (descendant_ssa GLOB '[0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9]'),
    CHECK (min_distance >= 1),
    CHECK (max_distance >= min_distance),
    CHECK (path_count >= 1)
);

CREATE TABLE IF NOT EXISTS ssa_derivada_summary (
    ssa TEXT PRIMARY KEY,
    direct_parents_count INTEGER NOT NULL DEFAULT 0,
    direct_children_count INTEGER NOT NULL DEFAULT 0,
    ancestors_count INTEGER NOT NULL DEFAULT 0,
    descendants_count INTEGER NOT NULL DEFAULT 0,
    level_from_root_min INTEGER,
    level_from_root_max INTEGER,
    levels_above_max INTEGER NOT NULL DEFAULT 0,
    levels_below_max INTEGER NOT NULL DEFAULT 0,
    component_size INTEGER NOT NULL DEFAULT 1,
    has_cycle INTEGER NOT NULL DEFAULT 0,
    last_sync_at TEXT NOT NULL,
    CHECK (length(ssa) = 9),
    CHECK (ssa GLOB '[0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9]'),
    CHECK (direct_parents_count >= 0),
    CHECK (direct_children_count >= 0),
    CHECK (ancestors_count >= 0),
    CHECK (descendants_count >= 0),
    CHECK (levels_above_max >= 0),
    CHECK (levels_below_max >= 0),
    CHECK (component_size >= 1),
    CHECK (has_cycle IN (0, 1))
);

CREATE TABLE IF NOT EXISTS ssa_derivada_sync_run (
    sync_run_id INTEGER PRIMARY KEY AUTOINCREMENT,
    mode TEXT NOT NULL,
    actor TEXT NOT NULL DEFAULT '',
    managed_sources TEXT NOT NULL DEFAULT '',
    started_at TEXT NOT NULL,
    finished_at TEXT,
    status TEXT NOT NULL DEFAULT 'running',
    db_edges INTEGER NOT NULL DEFAULT 0,
    sheet_edges INTEGER NOT NULL DEFAULT 0,
    merged_edges INTEGER NOT NULL DEFAULT 0,
    active_edges INTEGER NOT NULL DEFAULT 0,
    conflict_count INTEGER NOT NULL DEFAULT 0,
    multiparent_count INTEGER NOT NULL DEFAULT 0,
    orphan_parent_count INTEGER NOT NULL DEFAULT 0,
    orphan_child_count INTEGER NOT NULL DEFAULT 0,
    cycle_node_count INTEGER NOT NULL DEFAULT 0,
    graph_fingerprint TEXT,
    message TEXT
);
"""

DERIVADAS_INDEXES_SQL = """
CREATE INDEX IF NOT EXISTS idx_derivada_matrix_parent ON ssa_derivada_matrix (parent_ssa);
CREATE INDEX IF NOT EXISTS idx_derivada_matrix_child ON ssa_derivada_matrix (child_ssa);
CREATE INDEX IF NOT EXISTS idx_derivada_matrix_flags ON ssa_derivada_matrix (source_flags);
CREATE INDEX IF NOT EXISTS idx_derivada_matrix_active ON ssa_derivada_matrix (active);
CREATE INDEX IF NOT EXISTS idx_derivada_matrix_active_parent ON ssa_derivada_matrix (active, parent_ssa);
CREATE INDEX IF NOT EXISTS idx_derivada_matrix_active_child ON ssa_derivada_matrix (active, child_ssa);

CREATE INDEX IF NOT EXISTS idx_derivada_source_name ON ssa_derivada_source (source_name);
CREATE INDEX IF NOT EXISTS idx_derivada_source_active ON ssa_derivada_source (is_active);
CREATE INDEX IF NOT EXISTS idx_derivada_source_parent ON ssa_derivada_source (parent_ssa);
CREATE INDEX IF NOT EXISTS idx_derivada_source_child ON ssa_derivada_source (child_ssa);
CREATE INDEX IF NOT EXISTS idx_derivada_source_name_active ON ssa_derivada_source (source_name, is_active);

CREATE INDEX IF NOT EXISTS idx_derivada_closure_ancestor ON ssa_derivada_closure (ancestor_ssa);
CREATE INDEX IF NOT EXISTS idx_derivada_closure_descendant ON ssa_derivada_closure (descendant_ssa);
CREATE INDEX IF NOT EXISTS idx_derivada_closure_min_distance ON ssa_derivada_closure (min_distance);
CREATE INDEX IF NOT EXISTS idx_derivada_closure_max_distance ON ssa_derivada_closure (max_distance);

CREATE INDEX IF NOT EXISTS idx_derivada_summary_direct_children ON ssa_derivada_summary (direct_children_count);
CREATE INDEX IF NOT EXISTS idx_derivada_summary_descendants ON ssa_derivada_summary (descendants_count);
CREATE INDEX IF NOT EXISTS idx_derivada_summary_ancestors ON ssa_derivada_summary (ancestors_count);
CREATE INDEX IF NOT EXISTS idx_derivada_summary_levels_below ON ssa_derivada_summary (levels_below_max);
CREATE INDEX IF NOT EXISTS idx_derivada_summary_levels_above ON ssa_derivada_summary (levels_above_max);

CREATE INDEX IF NOT EXISTS idx_derivada_sync_run_status ON ssa_derivada_sync_run (status);
CREATE INDEX IF NOT EXISTS idx_derivada_sync_run_started ON ssa_derivada_sync_run (started_at);
"""


def _execute_sql_script_without_committing(
    conn: sqlite3.Connection, sql_script: str
) -> None:
    statement_lines: list[str] = []
    for line in sql_script.splitlines():
        if not line.strip():
            continue
        statement_lines.append(line)
        statement = "\n".join(statement_lines).strip()
        if sqlite3.complete_statement(statement):
            conn.execute(statement)
            statement_lines.clear()
    trailing = "\n".join(statement_lines).strip()
    if trailing:
        raise ValueError("Incomplete derivadas schema SQL script")


def ensure_derivadas_schema_on_connection(
    conn: sqlite3.Connection,
    *,
    include_legacy_backfill: bool = True,
) -> None:
    """Create derivadas schema objects if they do not exist.

    include_legacy_backfill:
      - True: applies data backfill for legacy relation_label column.
      - False: schema-only checks/migrations without data updates.
    """

    _execute_sql_script_without_committing(conn, DERIVADAS_TABLES_SQL)
    _ensure_derivadas_columns(conn, include_legacy_backfill=include_legacy_backfill)
    _execute_sql_script_without_committing(conn, DERIVADAS_INDEXES_SQL)


def _existing_columns(conn: sqlite3.Connection, table_name: str) -> set[str]:
    if not is_valid_identifier(table_name):
        raise ValueError(f"Invalid table identifier for schema scan: {table_name!r}")
    rows = conn.execute(f'PRAGMA table_info("{table_name}")').fetchall()
    return {row[1] for row in rows}


def _validate_ddl_sql_type(sql_type: str, *, table_name: str, column_name: str) -> str:
    if not isinstance(sql_type, str) or not sql_type.strip():
        raise ValueError(
            f"Invalid sql_type for {table_name}.{column_name}: {sql_type!r}"
        )
    lowered = sql_type.casefold()
    if any(token in lowered for token in (";", "--", "/*", "*/")):
        raise ValueError(
            f"Unsafe sql_type for {table_name}.{column_name}: {sql_type!r}"
        )
    if "\n" in sql_type or "\r" in sql_type:
        raise ValueError(
            f"Unsafe sql_type for {table_name}.{column_name}: {sql_type!r}"
        )
    return sql_type.strip()


def _safe_add_column_sql_type(
    sql_type: str, *, table_name: str, column_name: str
) -> str:
    safe_type = _validate_ddl_sql_type(
        sql_type, table_name=table_name, column_name=column_name
    )
    lowered = safe_type.casefold()
    if "not null" not in lowered or "default" in lowered:
        return safe_type

    explicit_defaults = {
        ("ssa_derivada_closure", "min_distance"): "1",
        ("ssa_derivada_closure", "max_distance"): "1",
    }
    explicit_default = explicit_defaults.get((table_name, column_name))
    if explicit_default is not None:
        return f"{safe_type} DEFAULT {explicit_default}"

    if lowered.startswith("text"):
        return f"{safe_type} DEFAULT ''"
    if lowered.startswith("integer"):
        return f"{safe_type} DEFAULT 0"
    if lowered.startswith("real") or lowered.startswith("numeric"):
        return f"{safe_type} DEFAULT 0"
    raise ValueError(
        f"Unsafe NOT NULL add-column type without default for {table_name}.{column_name}: {sql_type!r}"
    )


def _ensure_derivadas_columns(
    conn: sqlite3.Connection, *, include_legacy_backfill: bool
) -> None:
    conn.execute("SAVEPOINT derivadas_ensure_columns")
    try:
        for table_name, expected in EXPECTED_COLUMNS.items():
            if not is_valid_identifier(table_name):
                raise ValueError(
                    f"Invalid table identifier for schema migration: {table_name!r}"
                )
            existing = _existing_columns(conn, table_name)
            if not existing:
                continue
            for column_name, sql_type in expected.items():
                if not is_valid_identifier(column_name):
                    raise ValueError(
                        f"Invalid column identifier for schema migration: {table_name}.{column_name!r}"
                    )
                if column_name in existing:
                    continue
                safe_type = _safe_add_column_sql_type(
                    sql_type, table_name=table_name, column_name=column_name
                )
                try:
                    conn.execute(
                        f'ALTER TABLE "{table_name}" ADD COLUMN "{column_name}" {safe_type}'
                    )
                    logger.info(
                        "Derivadas schema migration: added column %s.%s",
                        table_name,
                        column_name,
                    )
                except sqlite3.OperationalError as exc:
                    if "duplicate column name" not in str(exc).lower():
                        raise
        if include_legacy_backfill:
            # Compatibilidade com schema antigo: relation_label -> relation_raw_label
            matrix_cols = _existing_columns(conn, "ssa_derivada_matrix")
            if "relation_label" in matrix_cols and "relation_raw_label" in matrix_cols:
                conn.execute(
                    """
                    UPDATE ssa_derivada_matrix
                    SET relation_raw_label = relation_label
                    WHERE (relation_raw_label IS NULL OR trim(relation_raw_label) = '')
                      AND relation_label IS NOT NULL
                      AND trim(relation_label) <> ''
                    """
                )
    except Exception as original_exc:
        try:
            conn.execute("ROLLBACK TO derivadas_ensure_columns")
        except sqlite3.Error as rollback_exc:
            logger.warning(
                "Derivadas schema migration rollback failed after %s: %s",
                type(original_exc).__name__,
                rollback_exc,
            )
        try:
            conn.execute("RELEASE derivadas_ensure_columns")
        except sqlite3.Error as release_exc:
            logger.warning(
                "Derivadas schema migration release failed after %s: %s",
                type(original_exc).__name__,
                release_exc,
            )
        raise
    conn.execute("RELEASE derivadas_ensure_columns")


def has_derivadas_read_schema(conn: sqlite3.Connection) -> bool:
    """Return True when tables/columns required by query API are present."""

    if not has_derivadas_schema(conn, required=READ_REQUIRED_COLUMNS.keys()):
        return False
    for table_name, required_columns in READ_REQUIRED_COLUMNS.items():
        existing = _existing_columns(conn, table_name)
        if not required_columns.issubset(existing):
            return False
    return True


def ensure_derivadas_schema_for_read(conn: sqlite3.Connection) -> None:
    """Ensure derivadas read-path schema with minimal write contention.

    Fast path performs only metadata checks. DDL is executed only when required.
    """

    if has_derivadas_read_schema(conn):
        return
    ensure_derivadas_schema_on_connection(conn, include_legacy_backfill=False)


def ensure_derivadas_schema(db_path: str) -> None:
    """Create derivadas schema objects in a DB path if needed."""

    safe_db_path = str(
        ensure_path_is_allowed(db_path, purpose="ensure derivadas schema")
    )
    with get_db_connection(safe_db_path, write=True) as conn:
        ensure_derivadas_schema_on_connection(conn)
        conn.commit()


def scan_derivadas_schema_readiness(
    conn: sqlite3.Connection,
    required: Iterable[str] = DERIVADAS_TABLES,
) -> dict[str, Any]:
    """Return schema readiness status without mutating the database."""

    required_tables = [str(name) for name in required]
    missing_tables: list[str] = []
    missing_columns: dict[str, list[str]] = {}
    existing_columns: dict[str, list[str]] = {}

    for table_name in required_tables:
        cols = _existing_columns(conn, table_name)
        if not cols:
            missing_tables.append(table_name)
            continue
        existing_columns[table_name] = sorted(cols)
        expected = set(EXPECTED_COLUMNS.get(table_name, {}).keys())
        if expected:
            missing = sorted(expected - cols)
            if missing:
                missing_columns[table_name] = missing

    is_ready = not missing_tables and not missing_columns
    return {
        "is_ready": is_ready,
        "required_tables": required_tables,
        "missing_tables": sorted(missing_tables),
        "missing_columns": missing_columns,
        "existing_columns": existing_columns,
    }


def scan_derivadas_schema_readiness_from_path(db_path: str) -> dict[str, Any]:
    """Run schema readiness scan from DB path without applying migrations."""

    safe_db_path = str(ensure_path_is_allowed(db_path, purpose="scan derivadas schema"))
    if not os.path.exists(safe_db_path):
        required_tables = list(DERIVADAS_TABLES)
        return {
            "is_ready": False,
            "required_tables": required_tables,
            "missing_tables": sorted(required_tables),
            "missing_columns": {},
            "existing_columns": {},
        }
    with closing(sqlite3.connect(f"file:{safe_db_path}?mode=ro", uri=True)) as conn:
        return scan_derivadas_schema_readiness(conn)


def scan_derivadas_read_schema_readiness(conn: sqlite3.Connection) -> dict[str, Any]:
    """Return read-path schema readiness without mutating the database."""

    required_tables = sorted(READ_REQUIRED_COLUMNS.keys())
    missing_tables: list[str] = []
    missing_columns: dict[str, list[str]] = {}

    for table_name in required_tables:
        existing = _existing_columns(conn, table_name)
        if not existing:
            missing_tables.append(table_name)
            continue
        required_cols = READ_REQUIRED_COLUMNS[table_name]
        missing = sorted(required_cols - existing)
        if missing:
            missing_columns[table_name] = missing

    return {
        "is_ready": not missing_tables and not missing_columns,
        "required_tables": required_tables,
        "missing_tables": sorted(missing_tables),
        "missing_columns": missing_columns,
    }


def scan_derivadas_read_schema_readiness_from_path(db_path: str) -> dict[str, Any]:
    """Run read-path schema readiness scan from DB path without migration."""

    required_tables = sorted(READ_REQUIRED_COLUMNS.keys())
    safe_db_path = str(
        ensure_path_is_allowed(db_path, purpose="scan derivadas read schema")
    )
    if not os.path.exists(safe_db_path):
        return {
            "is_ready": False,
            "required_tables": required_tables,
            "missing_tables": required_tables,
            "missing_columns": {},
        }
    with closing(sqlite3.connect(f"file:{safe_db_path}?mode=ro", uri=True)) as conn:
        return scan_derivadas_read_schema_readiness(conn)


def has_derivadas_schema(
    conn: sqlite3.Connection, required: Iterable[str] = DERIVADAS_TABLES
) -> bool:
    """Return True when all required derivadas tables exist."""

    names = {str(name) for name in required}
    if not names:
        return True
    invalid_names = sorted(name for name in names if not is_valid_identifier(name))
    if invalid_names:
        raise ValueError(f"Invalid table identifier(s): {invalid_names}")
    placeholders = ",".join("?" for _ in names)
    cur = conn.execute(
        f"SELECT name FROM sqlite_master WHERE type='table' AND name IN ({placeholders})",  # nosec B608  # skipcq: BAN-B608
        tuple(sorted(names)),
    )
    existing = {row[0] for row in cur.fetchall()}
    return names.issubset(existing)
