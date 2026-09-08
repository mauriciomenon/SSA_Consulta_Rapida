"""Contract tests for the single heavy integrity check (S12-integrity).

Regression: the full-rescan startup used to run the heavy
verify_database_integrity twice back to back (once inside
repair_database_if_needed, once explicitly). The contract now is one
heavy check on the happy path via ensure_database_integrity, which
returns (ok, report); a fresh check runs only when the database changed.
"""

import os
import sqlite3
import sys
from contextlib import closing
from pathlib import Path

import pytest

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from armazenamento import database_integrity  # noqa: E402
from armazenamento.database import (  # noqa: E402
    ensure_database_integrity,
    initialize_database,
    repair_database_if_needed,
)

SCHEMA_FILE = os.path.join(project_root, "config", "schema_unified.sql")


def _healthy_db(tmp_path: Path) -> str:
    db_path = str(tmp_path / "ssas.db")
    initialize_database(db_path, SCHEMA_FILE)
    return db_path


def _counting_verify(monkeypatch: pytest.MonkeyPatch):
    counter = {"calls": 0}
    original = database_integrity.verify_database_integrity

    def counting(db_path, table_name):
        counter["calls"] += 1
        return original(db_path, table_name)

    monkeypatch.setattr(database_integrity, "verify_database_integrity", counting)
    return counter


def test_ensure_healthy_db_single_check_and_valid_report(tmp_path, monkeypatch):
    db_path = _healthy_db(tmp_path)
    counter = _counting_verify(monkeypatch)

    ok, report = ensure_database_integrity(db_path, SCHEMA_FILE)

    assert ok is True
    assert report["is_valid"] is True
    assert counter["calls"] == 1


def test_ensure_bootstrap_missing_db_creates_and_reports(tmp_path, monkeypatch):
    db_path = str(tmp_path / "missing" / "ssas.db")
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    counter = _counting_verify(monkeypatch)

    ok, report = ensure_database_integrity(db_path, SCHEMA_FILE)

    assert ok is True
    assert report["is_valid"] is True
    assert os.path.exists(db_path)
    assert counter["calls"] == 2


def test_ensure_corrupted_db_returns_false_with_issues(tmp_path, monkeypatch):
    db_path = str(tmp_path / "corrupt.db")
    Path(db_path).write_bytes(b"this is not a sqlite database" * 64)
    counter = _counting_verify(monkeypatch)

    ok, report = ensure_database_integrity(db_path, SCHEMA_FILE)

    assert ok is False
    assert report["is_valid"] is False
    assert report["issues"]
    assert counter["calls"] == 1


def test_repair_wrapper_keeps_boolean_contract(tmp_path):
    db_path = _healthy_db(tmp_path)

    assert repair_database_if_needed(db_path, SCHEMA_FILE) is True


def test_restore_returns_actual_schema_and_row_report(tmp_path, monkeypatch):
    db_path = _healthy_db(tmp_path)
    with closing(sqlite3.connect(db_path)) as conn, conn:
        conn.execute("INSERT INTO ssa_table (numero_ssa, situacao, data_cadastro) "
                     "VALUES ('202600001', 'ADM', '2026-01-01 00:00:00')")
    assert database_integrity._create_integrity_snapshot(db_path, force=True)
    Path(db_path).write_bytes(b"corrupted SQLite" * 64)
    counter = _counting_verify(monkeypatch)

    ok, report = ensure_database_integrity(db_path, SCHEMA_FILE)

    assert ok is True
    assert report["is_valid"] is True
    assert report["restored_from_snapshot"] is True
    assert report["table_exists"] is True
    assert report["schema_valid"] is True
    assert report["missing_required_columns"] == []
    assert report["issues"] == []
    assert counter["calls"] == 2
    with closing(sqlite3.connect(db_path)) as conn, conn:
        assert conn.execute("SELECT numero_ssa FROM ssa_table").fetchall() == [("202600001",)]


def test_prepare_working_database_runs_heavy_check_once(tmp_path, monkeypatch):
    from core import app_logic
    from armazenamento import database as database_module

    db_path = _healthy_db(tmp_path)
    counter = {"ensure": 0, "verify": 0}

    def fake_ensure(db_path_arg, schema_file="schema.sql", table_name="ssa_table"):
        counter["ensure"] += 1
        report = database_integrity.verify_database_integrity(db_path_arg, table_name)
        return bool(report["is_valid"]), report

    monkeypatch.setattr(database_module, "ensure_database_integrity", fake_ensure)
    monkeypatch.setattr(
        database_module,
        "verify_database_integrity",
        lambda *a, **k: counter.__setitem__("verify", counter["verify"] + 1)
        or {"is_valid": True, "issues": [], "warnings": []},
    )

    working, candidate, report = app_logic._prepare_working_database_for_import(
        data_dir=str(tmp_path / "data"),
        primary_db_path=db_path,
        run_id="test-run",
        force_import=False,
        table_name="ssa_table",
    )

    assert working == db_path
    assert candidate is None
    assert report["is_valid"] is True
    assert counter["ensure"] == 1
    assert counter["verify"] == 0
