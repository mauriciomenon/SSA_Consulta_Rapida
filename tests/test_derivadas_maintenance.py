from __future__ import annotations

import sqlite3
import threading
import time

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
            [(numero_ssa, derivada_de, f"SSA {numero_ssa}") for numero_ssa, derivada_de in rows],
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

    result = run_derivadas_maintenance(temp_db, min_interval_seconds=3600, auto_heal=True)
    assert result["ran"] is False
    assert result["reason"] == "interval_guard"


def test_scan_remains_read_only_under_write_lock(temp_db):
    _seed_base_data(temp_db)
    sync_derivadas(temp_db)

    lock_conn = sqlite3.connect(temp_db, timeout=0.1, check_same_thread=False)
    lock_conn.execute("BEGIN IMMEDIATE")

    def _release_lock() -> None:
        time.sleep(1.0)
        lock_conn.rollback()
        lock_conn.close()

    releaser = threading.Thread(target=_release_lock)
    releaser.start()
    started_at = time.perf_counter()
    report = scan_derivadas_consistency(temp_db)
    op_elapsed = time.perf_counter() - started_at
    releaser.join(timeout=2.0)

    assert report["matrix_active_edges"] == 2
    assert op_elapsed < 0.5
