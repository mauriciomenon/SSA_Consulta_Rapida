from __future__ import annotations

import sqlite3

import pytest

from armazenamento.derivadas_schema import (
    ensure_derivadas_schema,
    ensure_derivadas_schema_on_connection,
    has_derivadas_schema,
    scan_derivadas_read_schema_readiness_from_path,
    scan_derivadas_schema_readiness_from_path,
)


def test_schema_scan_reports_missing_tables_on_fresh_db(temp_db):
    report = scan_derivadas_schema_readiness_from_path(temp_db)
    assert report["is_ready"] is False
    assert "ssa_derivada_matrix" in report["missing_tables"]
    assert "ssa_derivada_source" in report["missing_tables"]


def test_schema_scan_reports_ready_after_schema_bootstrap(temp_db):
    ensure_derivadas_schema(temp_db)
    report = scan_derivadas_schema_readiness_from_path(temp_db)
    assert report["is_ready"] is True
    assert report["missing_tables"] == []
    assert report["missing_columns"] == {}


def test_schema_scan_detects_legacy_missing_columns(temp_db):
    with sqlite3.connect(temp_db) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS ssa_derivada_matrix (
                parent_ssa TEXT NOT NULL,
                child_ssa TEXT NOT NULL,
                PRIMARY KEY (parent_ssa, child_ssa)
            )
            """
        )
        conn.commit()

    report = scan_derivadas_schema_readiness_from_path(temp_db)
    assert report["is_ready"] is False
    assert "ssa_derivada_matrix" in report["missing_columns"]
    assert "source_flags" in report["missing_columns"]["ssa_derivada_matrix"]


def test_read_schema_scan_reports_missing_tables_on_fresh_db(temp_db):
    report = scan_derivadas_read_schema_readiness_from_path(temp_db)
    assert report["is_ready"] is False
    assert "ssa_derivada_matrix" in report["missing_tables"]
    assert "ssa_derivada_closure" in report["missing_tables"]


def test_read_schema_scan_reports_ready_after_schema_bootstrap(temp_db):
    ensure_derivadas_schema(temp_db)
    report = scan_derivadas_read_schema_readiness_from_path(temp_db)
    assert report["is_ready"] is True
    assert report["missing_tables"] == []
    assert report["missing_columns"] == {}


def test_schema_scan_from_missing_path_does_not_create_database(tmp_path):
    db_path = tmp_path / "missing_derivadas.db"

    report = scan_derivadas_schema_readiness_from_path(str(db_path))

    assert report["is_ready"] is False
    assert not db_path.exists()
    assert "ssa_derivada_matrix" in report["missing_tables"]


def test_read_schema_scan_from_missing_path_does_not_create_database(tmp_path):
    db_path = tmp_path / "missing_derivadas_read.db"

    report = scan_derivadas_read_schema_readiness_from_path(str(db_path))

    assert report["is_ready"] is False
    assert not db_path.exists()
    assert "ssa_derivada_matrix" in report["missing_tables"]


def test_has_derivadas_schema_rejects_invalid_identifier(temp_db):
    with sqlite3.connect(temp_db) as conn:
        with pytest.raises(ValueError):
            has_derivadas_schema(conn, required=("ssa_derivada_matrix;drop",))


def test_ensure_schema_preserves_outer_transaction(temp_db):
    with sqlite3.connect(temp_db) as conn:
        conn.execute("CREATE TABLE t (id INTEGER PRIMARY KEY, name TEXT)")
        conn.execute("INSERT INTO t (name) VALUES ('before')")
        conn.commit()
        conn.execute("BEGIN")
        conn.execute("INSERT INTO t (name) VALUES ('inside_tx_before_schema')")
        ensure_derivadas_schema_on_connection(conn)
        conn.execute("ROLLBACK")

    with sqlite3.connect(temp_db) as conn:
        rows = conn.execute("SELECT name FROM t ORDER BY id").fetchall()
    assert rows == [('before',)]


def test_ensure_schema_adds_not_null_columns_with_safe_defaults(temp_db):
    with sqlite3.connect(temp_db) as conn:
        conn.execute(
            """
            CREATE TABLE ssa_derivada_matrix (
                parent_ssa TEXT NOT NULL,
                child_ssa TEXT NOT NULL,
                source_flags INTEGER NOT NULL DEFAULT 0,
                relation_type INTEGER NOT NULL DEFAULT 0,
                relation_raw_label TEXT,
                active INTEGER NOT NULL DEFAULT 1,
                PRIMARY KEY (parent_ssa, child_ssa)
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE ssa_derivada_closure (
                ancestor_ssa TEXT NOT NULL,
                descendant_ssa TEXT NOT NULL,
                path_count INTEGER NOT NULL DEFAULT 1,
                PRIMARY KEY (ancestor_ssa, descendant_ssa)
            )
            """
        )
        conn.execute(
            "INSERT INTO ssa_derivada_matrix (parent_ssa, child_ssa) VALUES ('000000001', '000000002')"
        )
        conn.execute(
            "INSERT INTO ssa_derivada_closure (ancestor_ssa, descendant_ssa) VALUES ('000000001', '000000002')"
        )

        ensure_derivadas_schema_on_connection(conn, include_legacy_backfill=False)

        matrix_row = conn.execute(
            "SELECT first_seen_at, last_seen_at, last_sync_at FROM ssa_derivada_matrix"
        ).fetchone()
        closure_row = conn.execute(
            "SELECT min_distance, max_distance, last_sync_at FROM ssa_derivada_closure"
        ).fetchone()

    assert matrix_row == ("", "", "")
    assert closure_row == (1, 1, "")
