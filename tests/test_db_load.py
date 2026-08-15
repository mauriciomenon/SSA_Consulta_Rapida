#!/usr/bin/env python3
"""Regression guards for database-load script assumptions."""

from __future__ import annotations

import sqlite3
from pathlib import Path


def _list_table_names(conn: sqlite3.Connection) -> list[str]:
    rows = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
    return [row[0] for row in rows]


def test_list_table_names_returns_created_tables(tmp_path: Path) -> None:
    db_path = tmp_path / "ssas.db"
    conn = sqlite3.connect(db_path)
    try:
        conn.execute("CREATE TABLE ssa_table (id INTEGER PRIMARY KEY, numero_ssa TEXT)")
        conn.execute("CREATE VIEW ssas AS SELECT * FROM ssa_table")
        conn.commit()
        names = _list_table_names(conn)
    finally:
        conn.close()

    assert "ssa_table" in names
