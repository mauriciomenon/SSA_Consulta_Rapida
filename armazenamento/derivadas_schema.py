"""Schema bootstrap for derivadas support tables.

This module exists to keep derivadas schema setup isolated from legacy import
flows. It can be safely called before sync/query routines without affecting GUI.
"""

from __future__ import annotations

import logging
import sqlite3
from typing import Iterable

from armazenamento.database import get_db_connection

logger = logging.getLogger(__name__)


DERIVADAS_TABLES: tuple[str, ...] = (
    "ssa_derivada_matrix",
    "ssa_derivada_source",
    "ssa_derivada_closure",
    "ssa_derivada_summary",
    "ssa_derivada_sync_run",
)

DERIVADAS_SCHEMA_SQL = """
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

CREATE INDEX IF NOT EXISTS idx_derivada_matrix_parent ON ssa_derivada_matrix (parent_ssa);
CREATE INDEX IF NOT EXISTS idx_derivada_matrix_child ON ssa_derivada_matrix (child_ssa);
CREATE INDEX IF NOT EXISTS idx_derivada_matrix_flags ON ssa_derivada_matrix (source_flags);
CREATE INDEX IF NOT EXISTS idx_derivada_matrix_active ON ssa_derivada_matrix (active);
CREATE INDEX IF NOT EXISTS idx_derivada_matrix_active_parent ON ssa_derivada_matrix (active, parent_ssa);
CREATE INDEX IF NOT EXISTS idx_derivada_matrix_active_child ON ssa_derivada_matrix (active, child_ssa);

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

CREATE INDEX IF NOT EXISTS idx_derivada_source_name ON ssa_derivada_source (source_name);
CREATE INDEX IF NOT EXISTS idx_derivada_source_active ON ssa_derivada_source (is_active);
CREATE INDEX IF NOT EXISTS idx_derivada_source_parent ON ssa_derivada_source (parent_ssa);
CREATE INDEX IF NOT EXISTS idx_derivada_source_child ON ssa_derivada_source (child_ssa);
CREATE INDEX IF NOT EXISTS idx_derivada_source_name_active ON ssa_derivada_source (source_name, is_active);

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

CREATE INDEX IF NOT EXISTS idx_derivada_closure_ancestor ON ssa_derivada_closure (ancestor_ssa);
CREATE INDEX IF NOT EXISTS idx_derivada_closure_descendant ON ssa_derivada_closure (descendant_ssa);
CREATE INDEX IF NOT EXISTS idx_derivada_closure_min_distance ON ssa_derivada_closure (min_distance);
CREATE INDEX IF NOT EXISTS idx_derivada_closure_max_distance ON ssa_derivada_closure (max_distance);

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

CREATE INDEX IF NOT EXISTS idx_derivada_summary_direct_children ON ssa_derivada_summary (direct_children_count);
CREATE INDEX IF NOT EXISTS idx_derivada_summary_descendants ON ssa_derivada_summary (descendants_count);
CREATE INDEX IF NOT EXISTS idx_derivada_summary_ancestors ON ssa_derivada_summary (ancestors_count);
CREATE INDEX IF NOT EXISTS idx_derivada_summary_levels_below ON ssa_derivada_summary (levels_below_max);
CREATE INDEX IF NOT EXISTS idx_derivada_summary_levels_above ON ssa_derivada_summary (levels_above_max);

CREATE TABLE IF NOT EXISTS ssa_derivada_sync_run (
    sync_run_id INTEGER PRIMARY KEY AUTOINCREMENT,
    mode TEXT NOT NULL,
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
    message TEXT
);

CREATE INDEX IF NOT EXISTS idx_derivada_sync_run_status ON ssa_derivada_sync_run (status);
CREATE INDEX IF NOT EXISTS idx_derivada_sync_run_started ON ssa_derivada_sync_run (started_at);
"""


def ensure_derivadas_schema_on_connection(conn: sqlite3.Connection) -> None:
    """Create derivadas schema objects if they do not exist."""

    conn.executescript(DERIVADAS_SCHEMA_SQL)


def ensure_derivadas_schema(db_path: str) -> None:
    """Create derivadas schema objects in a DB path if needed."""

    with get_db_connection(db_path) as conn:
        ensure_derivadas_schema_on_connection(conn)
        conn.commit()


def has_derivadas_schema(conn: sqlite3.Connection, required: Iterable[str] = DERIVADAS_TABLES) -> bool:
    """Return True when all required derivadas tables exist."""

    names = {str(name) for name in required}
    if not names:
        return True
    cur = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name IN ({})".format(
            ",".join("?" for _ in names)
        ),
        tuple(sorted(names)),
    )
    existing = {row[0] for row in cur.fetchall()}
    return names.issubset(existing)

