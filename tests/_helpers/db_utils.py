"""Utilities and fixtures helpers for database related tests.

This module provides helper functions used by test fixtures to create an
isolated SQLite database instance using the project schema, and convenience
assertions for row counts.
"""

from __future__ import annotations

import os
import shutil
import sqlite3
import tempfile
from pathlib import Path
from typing import Any, Iterable

from armazenamento.identifier_utils import quote_identifier as _quote_identifier

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CONFIG_DIR = PROJECT_ROOT / "config"
DEFAULT_SCHEMA = CONFIG_DIR / "schema.sql"


def create_temp_db(schema_path: str | os.PathLike | None = None) -> tuple[str, str]:
    """Create a temporary sqlite database applying the project schema.

    Returns (db_path, tmp_dir). Caller is responsible for removing tmp_dir
    if a longer lifecycle is desired (pytest will usually clean tmp dirs automatically
    when using built-in tmp_path factories; here we rely on manual usage).
    """
    tmp_dir = tempfile.mkdtemp(prefix="ssa_db_test_")
    db_path = os.path.join(tmp_dir, "test.db")
    try:
        schema_to_use = Path(schema_path) if schema_path else DEFAULT_SCHEMA
        if not schema_to_use.exists():
            raise FileNotFoundError(f"Schema file not found: {schema_to_use}")
        sql = Path(schema_to_use).read_text(encoding="utf-8")
        conn = sqlite3.connect(db_path)
        try:
            conn.executescript(sql)
            conn.commit()
        finally:
            conn.close()
    except Exception:
        shutil.rmtree(tmp_dir, ignore_errors=True)
        raise
    return db_path, tmp_dir


def fetch_all(db_path: str, table: str) -> list[tuple]:
    table_name = _quote_identifier(table)
    conn = sqlite3.connect(db_path)
    try:
        # SQL identifiers cannot be bound as parameters; _quote_identifier validates
        # the table name against a strict allowlist before interpolation.
        # nosemgrep: python.lang.security.audit.formatted-sql-query.formatted-sql-query, python.sqlalchemy.security.sqlalchemy-execute-raw-query.sqlalchemy-execute-raw-query
        cur = conn.execute(f"SELECT * FROM {table_name}")
        return list(cur.fetchall())
    finally:
        conn.close()


def assert_rowcount(db_path: str, table: str, expected: int) -> None:
    rows = fetch_all(db_path, table)
    actual = len(rows)
    assert actual == expected, (
        f"Rowcount mismatch for {table}: got {actual}, expected {expected}"
    )


def insert_raw_rows(
    db_path: str, table: str, columns: Iterable[str], rows: Iterable[Iterable[Any]]
) -> None:
    conn = sqlite3.connect(db_path)
    try:
        column_names = list(columns)
        table_name = _quote_identifier(table)
        col_list = ",".join(_quote_identifier(column) for column in column_names)
        placeholders = ",".join(["?"] * len(column_names))
        conn.executemany(
            f"INSERT INTO {table_name} ({col_list}) VALUES ({placeholders})",
            (tuple(row) for row in rows),
        )
        conn.commit()
    finally:
        conn.close()
