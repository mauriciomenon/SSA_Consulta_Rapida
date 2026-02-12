from __future__ import annotations

import sqlite3

import pytest

from armazenamento.derivadas_schema import (
    ensure_derivadas_schema,
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


def test_has_derivadas_schema_rejects_invalid_identifier(temp_db):
    with sqlite3.connect(temp_db) as conn:
        with pytest.raises(ValueError):
            has_derivadas_schema(conn, required=("ssa_derivada_matrix;drop",))
