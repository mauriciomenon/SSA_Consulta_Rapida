from __future__ import annotations

import csv
import sqlite3
from pathlib import Path

from armazenamento.derivadas_sync import get_sync_stats, sync_derivadas
from armazenamento.derivadas_schema import ensure_derivadas_schema_on_connection


def _insert_ssa_rows(db_path: str, rows: list[tuple[str, str | None]]) -> None:
    with sqlite3.connect(db_path) as conn:
        conn.executemany(
            "INSERT INTO ssa_table (numero_ssa, derivada_de, descricao_ssa) VALUES (?, ?, ?)",
            [(numero_ssa, derivada_de, f"SSA {numero_ssa}") for numero_ssa, derivada_de in rows],
        )
        conn.commit()


def test_sync_from_db_materializes_matrix_closure_summary(temp_db):
    _insert_ssa_rows(
        temp_db,
        [
            ("202500001", None),
            ("202500002", "202500001"),
            ("202500003", "202500002"),
            ("202500004", "202500001"),
        ],
    )

    report = sync_derivadas(temp_db)

    assert report["active_edges"] == 3
    assert report["closure_rows"] == 4
    assert report["summary_rows"] == 4
    assert report["reconciliation"]["db_vs_sheet_conflict_count"] == 0

    with sqlite3.connect(temp_db) as conn:
        matrix_active = conn.execute("SELECT COUNT(*) FROM ssa_derivada_matrix WHERE active = 1").fetchone()[0]
        closure_total = conn.execute("SELECT COUNT(*) FROM ssa_derivada_closure").fetchone()[0]
        summary_root = conn.execute(
            """
            SELECT direct_children_count, descendants_count
            FROM ssa_derivada_summary
            WHERE ssa = '202500001'
            """
        ).fetchone()

    assert matrix_active == 3
    assert closure_total == 4
    assert summary_root == (2, 3)


def test_verify_only_reports_db_vs_sheet_conflict_without_writing(temp_db, tmp_path: Path):
    _insert_ssa_rows(
        temp_db,
        [
            ("202500001", None),
            ("202500002", "202500001"),
            ("202500009", None),
        ],
    )

    sheet_file = tmp_path / "derivadas.csv"
    with sheet_file.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=["parent_ssa", "child_ssa", "relation_label"])
        writer.writeheader()
        writer.writerow({"parent_ssa": "202500009", "child_ssa": "202500002", "relation_label": "Derivada da"})

    report = sync_derivadas(
        temp_db,
        sheet_file=str(sheet_file),
        verify_only=True,
    )

    assert report["verify_only"] is True
    assert report["reconciliation"]["db_vs_sheet_conflict_count"] == 1

    with sqlite3.connect(temp_db) as conn:
        matrix_count = conn.execute("SELECT COUNT(*) FROM ssa_derivada_matrix").fetchone()[0]
    assert matrix_count == 0


def test_full_rebuild_hard_removes_stale_matrix_rows(temp_db):
    _insert_ssa_rows(
        temp_db,
        [
            ("202500001", None),
            ("202500002", "202500001"),
            ("202500003", "202500001"),
        ],
    )
    first = sync_derivadas(temp_db, full_rebuild=True)
    assert first["active_edges"] == 2

    with sqlite3.connect(temp_db) as conn:
        conn.execute("UPDATE ssa_table SET derivada_de = NULL WHERE numero_ssa = '202500003'")
        conn.commit()

    second = sync_derivadas(temp_db, full_rebuild=True)
    assert second["active_edges"] == 1

    with sqlite3.connect(temp_db) as conn:
        total_matrix = conn.execute("SELECT COUNT(*) FROM ssa_derivada_matrix").fetchone()[0]
        active_matrix = conn.execute("SELECT COUNT(*) FROM ssa_derivada_matrix WHERE active = 1").fetchone()[0]

    assert total_matrix == 1
    assert active_matrix == 1

    stats = get_sync_stats(temp_db)
    assert stats["matrix_active"] == 1
    assert stats["latest_sync"] is not None


def test_schema_migration_handles_legacy_matrix_without_active_column(temp_db):
    with sqlite3.connect(temp_db) as conn:
        conn.execute("DROP TABLE IF EXISTS ssa_derivada_matrix")
        conn.execute(
            """
            CREATE TABLE ssa_derivada_matrix (
                parent_ssa TEXT NOT NULL,
                child_ssa TEXT NOT NULL,
                source_flags INTEGER NOT NULL DEFAULT 0,
                relation_label TEXT,
                first_seen_at TEXT NOT NULL,
                last_seen_at TEXT NOT NULL,
                last_sync_at TEXT NOT NULL,
                PRIMARY KEY (parent_ssa, child_ssa)
            )
            """
        )
        conn.execute(
            """
            INSERT INTO ssa_derivada_matrix (
                parent_ssa, child_ssa, source_flags, relation_label, first_seen_at, last_seen_at, last_sync_at
            ) VALUES (
                '202500001', '202500002', 1, 'Derivada da', '2026-01-01 00:00:00', '2026-01-01 00:00:00', '2026-01-01 00:00:00'
            )
            """
        )
        ensure_derivadas_schema_on_connection(conn)
        conn.commit()

        cols = [row[1] for row in conn.execute("PRAGMA table_info(ssa_derivada_matrix)").fetchall()]
        row = conn.execute(
            """
            SELECT relation_type, relation_raw_label, active
            FROM ssa_derivada_matrix
            WHERE parent_ssa='202500001' AND child_ssa='202500002'
            """
        ).fetchone()

    assert "relation_type" in cols
    assert "relation_raw_label" in cols
    assert "active" in cols
    assert row == (0, "Derivada da", 1)
