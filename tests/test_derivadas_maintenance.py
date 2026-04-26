from __future__ import annotations

import sqlite3
import time

import armazenamento.derivadas_sync as derivadas_sync_module
from armazenamento.derivadas_sync import (
    run_derivadas_maintenance,
    scan_derivadas_consistency,
    self_heal_derivadas,
    sync_derivadas,
)


def _seed_base_data(db_path: str) -> None:
    rows = [
        ("202500001", None),
        ("202500002", "202500001"),
        ("202500003", "202500002"),
    ]
    with sqlite3.connect(db_path) as conn:
        conn.executemany(
            "INSERT INTO ssa_table (numero_ssa, derivada_de, descricao_ssa) VALUES (?, ?, ?)",
            [
                (numero_ssa, derivada_de, f"SSA {numero_ssa}")
                for numero_ssa, derivada_de in rows
            ],
        )
        conn.commit()


def test_scan_detects_matrix_source_inconsistency(temp_db):
    _seed_base_data(temp_db)
    sync_derivadas(temp_db)

    with sqlite3.connect(temp_db) as conn:
        conn.execute(
            """
            UPDATE ssa_derivada_matrix
            SET source_flags = 0
            WHERE parent_ssa = '202500001' AND child_ssa = '202500002'
            """
        )
        conn.commit()

    report = scan_derivadas_consistency(temp_db)
    assert report["is_consistent"] is False
    assert report["issue_counts"]["flag_mismatch_pairs"] >= 1


def test_self_heal_repairs_inconsistency(temp_db):
    _seed_base_data(temp_db)
    sync_derivadas(temp_db)

    with sqlite3.connect(temp_db) as conn:
        conn.execute(
            """
            UPDATE ssa_derivada_matrix
            SET source_flags = 0
            WHERE active = 1
            """
        )
        conn.commit()

    healed = self_heal_derivadas(temp_db)
    assert healed["healed"] is True
    assert healed["after"]["is_consistent"] is True


def test_maintenance_interval_guard(temp_db):
    _seed_base_data(temp_db)
    sync_derivadas(temp_db)

    result = run_derivadas_maintenance(
        temp_db, min_interval_seconds=3600, auto_heal=True
    )
    assert result["ran"] is False
    assert result["reason"] == "interval_guard"


def test_scan_remains_read_only_under_write_lock(temp_db):
    _seed_base_data(temp_db)
    sync_derivadas(temp_db)

    lock_conn = sqlite3.connect(temp_db, timeout=0.1, check_same_thread=False)
    lock_conn.execute("BEGIN IMMEDIATE")
    started_at = time.perf_counter()
    try:
        report = scan_derivadas_consistency(temp_db)
        op_elapsed = time.perf_counter() - started_at
    finally:
        lock_conn.rollback()
        lock_conn.close()

    assert report["matrix_active_edges"] == 2
    assert op_elapsed < 0.5


def test_maintenance_interval_guard_remains_read_only_under_write_lock(temp_db):
    _seed_base_data(temp_db)
    sync_derivadas(temp_db)

    lock_conn = sqlite3.connect(temp_db, timeout=0.1, check_same_thread=False)
    lock_conn.execute("BEGIN IMMEDIATE")
    started_at = time.perf_counter()
    try:
        result = run_derivadas_maintenance(
            temp_db, min_interval_seconds=3600, auto_heal=True
        )
        op_elapsed = time.perf_counter() - started_at
    finally:
        lock_conn.rollback()
        lock_conn.close()

    assert result["ran"] is False
    assert result["reason"] == "interval_guard"
    assert op_elapsed < 0.5


def test_scan_detects_summary_extra_nodes(temp_db):
    _seed_base_data(temp_db)
    sync_derivadas(temp_db)

    with sqlite3.connect(temp_db) as conn:
        conn.execute(
            """
            INSERT INTO ssa_derivada_summary (
                ssa,
                direct_parents_count,
                direct_children_count,
                ancestors_count,
                descendants_count,
                level_from_root_min,
                level_from_root_max,
                levels_above_max,
                levels_below_max,
                component_size,
                has_cycle,
                last_sync_at
            ) VALUES (?, 0, 0, 0, 0, NULL, NULL, 0, 0, 1, 0, ?)
            """,
            ("202599999", "2026-02-12 00:00:00"),
        )
        conn.commit()

    report = scan_derivadas_consistency(temp_db)
    assert report["is_consistent"] is False
    assert report["issue_counts"]["summary_extra_nodes"] >= 1


def test_scan_on_fresh_db_does_not_create_derivadas_tables(temp_db):
    with sqlite3.connect(temp_db) as conn:
        before = {
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table' AND name LIKE 'ssa_derivada_%'"
            ).fetchall()
        }
    assert before == set()

    report = scan_derivadas_consistency(temp_db)
    assert report["schema_ready"] is False
    assert report["issue_counts"]["schema_not_ready"] == 1

    with sqlite3.connect(temp_db) as conn:
        after = {
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table' AND name LIKE 'ssa_derivada_%'"
            ).fetchall()
        }
    assert after == set()


def test_maintenance_on_fresh_db_reports_schema_not_ready(temp_db):
    result = run_derivadas_maintenance(temp_db, min_interval_seconds=0, auto_heal=True)
    assert result["ran"] is True
    assert result["scan_only"] is True
    assert result["reason"] == "schema_not_ready"
    assert result["scan"]["schema_ready"] is False


def test_maintenance_returns_database_locked_state_on_exclusive_lock(
    temp_db, monkeypatch
):
    _seed_base_data(temp_db)
    sync_derivadas(temp_db)
    monkeypatch.setattr(derivadas_sync_module, "DERIVADAS_BUSY_TIMEOUT_MS", 200)

    lock_conn = sqlite3.connect(temp_db, timeout=0.1, check_same_thread=False)
    lock_conn.execute("BEGIN EXCLUSIVE")
    try:
        result = run_derivadas_maintenance(
            temp_db, min_interval_seconds=0, auto_heal=False
        )
    finally:
        lock_conn.rollback()
        lock_conn.close()

    assert result["ran"] is False
    assert result["reason"] == "database_locked"
    assert result["phase"] in {"read_latest_sync", "scan"}
    assert "locked" in result["error"].lower()
