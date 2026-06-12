from __future__ import annotations

import csv
import os
import sqlite3
import threading
import time
from pathlib import Path
from typing import Any, cast

import pandas as pd
import pytest

import armazenamento.derivadas_sync as derivadas_sync
from armazenamento.derivadas_schema import ensure_derivadas_schema_on_connection
from armazenamento.derivadas_sync import get_sync_stats, sync_derivadas
from utils.path_safety import PathSafetyError


def _insert_ssa_rows(db_path: str, rows: list[tuple[str, str | None]]) -> None:
    with sqlite3.connect(db_path) as conn:
        conn.executemany(
            "INSERT INTO ssa_table (numero_ssa, derivada_de, descricao_ssa) VALUES (?, ?, ?)",
            [
                (numero_ssa, derivada_de, f"SSA {numero_ssa}")
                for numero_ssa, derivada_de in rows
            ],
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
        matrix_active = conn.execute(
            "SELECT COUNT(*) FROM ssa_derivada_matrix WHERE active = 1"
        ).fetchone()[0]
        closure_total = conn.execute(
            "SELECT COUNT(*) FROM ssa_derivada_closure"
        ).fetchone()[0]
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


def test_sync_persists_actor_in_sync_run(temp_db):
    _insert_ssa_rows(
        temp_db,
        [
            ("202500001", None),
            ("202500002", "202500001"),
        ],
    )

    sync_derivadas(temp_db, actor="test-actor")

    with sqlite3.connect(temp_db) as conn:
        actor = conn.execute(
            "SELECT actor FROM ssa_derivada_sync_run ORDER BY sync_run_id DESC LIMIT 1"
        ).fetchone()[0]

    assert actor == "test-actor"


def test_sync_validates_database_path_before_open(temp_db, monkeypatch):
    def _blocked_path(*_args, **_kwargs):
        raise PathSafetyError("blocked derivadas db")

    monkeypatch.setattr(derivadas_sync, "ensure_path_is_allowed", _blocked_path)

    with pytest.raises(PathSafetyError, match="blocked derivadas db"):
        sync_derivadas(temp_db)


def test_sync_deactivates_db_source_when_derivada_field_is_cleared(temp_db):
    _insert_ssa_rows(
        temp_db,
        [
            ("202500001", None),
            ("202500002", "202500001"),
        ],
    )

    initial_report = sync_derivadas(temp_db)
    assert initial_report["active_edges"] == 1

    with sqlite3.connect(temp_db) as conn:
        conn.execute(
            "UPDATE ssa_table SET derivada_de = NULL WHERE numero_ssa = ?",
            ("202500002",),
        )
        conn.commit()

    report = sync_derivadas(temp_db)

    assert report["managed_sources"] == [derivadas_sync.SOURCE_DB_FIELD]
    assert report["active_edges"] == 0
    with sqlite3.connect(temp_db) as conn:
        active_source_rows = conn.execute(
            """
            SELECT COUNT(*)
            FROM ssa_derivada_source
            WHERE source_name = ? AND is_active = 1
            """,
            (derivadas_sync.SOURCE_DB_FIELD,),
        ).fetchone()[0]
        active_matrix_rows = conn.execute(
            "SELECT COUNT(*) FROM ssa_derivada_matrix WHERE active = 1"
        ).fetchone()[0]

    assert active_source_rows == 0
    assert active_matrix_rows == 0


def test_sync_manages_db_source_when_base_table_is_missing(
    tmp_path: Path,
):
    db_path = str(tmp_path / "missing_base_table.db")

    report = sync_derivadas(db_path, table_name="missing_ssa_table", verify_only=True)

    assert report["managed_sources"] == [derivadas_sync.SOURCE_DB_FIELD]
    assert report["db_stats"] == {"accepted_edges": 0}


def test_sync_cycle_detection_marks_only_cycle_nodes(temp_db):
    _insert_ssa_rows(
        temp_db,
        [
            ("202500001", "202500002"),
            ("202500002", "202500001"),
            ("202500003", "202500002"),
        ],
    )

    report = sync_derivadas(temp_db)
    assert report["reconciliation"]["cycle_node_count"] == 2

    with sqlite3.connect(temp_db) as conn:
        rows = {
            row[0]: int(row[1])
            for row in conn.execute(
                """
                SELECT ssa, has_cycle
                FROM ssa_derivada_summary
                WHERE ssa IN ('202500001', '202500002', '202500003')
                """
            ).fetchall()
        }

    assert rows["202500001"] == 1
    assert rows["202500002"] == 1
    assert rows["202500003"] == 0


def test_verify_only_reports_db_vs_sheet_conflict_without_writing(
    temp_db, tmp_path: Path
):
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
        writer = csv.DictWriter(
            fh, fieldnames=["parent_ssa", "child_ssa", "relation_label"]
        )
        writer.writeheader()
        writer.writerow(
            {
                "parent_ssa": "202500009",
                "child_ssa": "202500002",
                "relation_label": "Derivada da",
            }
        )

    report = sync_derivadas(
        temp_db,
        sheet_file=str(sheet_file),
        verify_only=True,
    )

    assert report["verify_only"] is True
    assert report["reconciliation"]["db_vs_sheet_conflict_count"] == 1

    with sqlite3.connect(temp_db) as conn:
        derivadas_tables = {
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table' AND name LIKE 'ssa_derivada_%'"
            ).fetchall()
        }
    assert derivadas_tables == set()


def test_sync_resolves_sheet_column_aliases(temp_db, tmp_path: Path):
    _insert_ssa_rows(
        temp_db,
        [
            ("202500001", None),
            ("202500002", None),
        ],
    )

    sheet_file = tmp_path / "derivadas_alias.csv"
    with sheet_file.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=["SSA Mae", "SSA Filha", "Relacao"])
        writer.writeheader()
        writer.writerow(
            {"SSA Mae": "202500001", "SSA Filha": "202500002", "Relacao": "Derivada da"}
        )

    report = sync_derivadas(
        temp_db,
        include_db_source=False,
        sheet_file=str(sheet_file),
        sheet_parent_col="parent_ssa",
        sheet_child_col="child_ssa",
        sheet_label_col="relation_label",
    )

    assert report["sheet_stats"]["accepted_edges"] == 1
    assert report["sheet_stats"]["resolved_parent_alias_rows"] == 1
    assert report["sheet_stats"]["resolved_child_alias_rows"] == 1
    assert report["sheet_stats"]["resolved_label_alias_rows"] == 1

    with sqlite3.connect(temp_db) as conn:
        row = conn.execute(
            """
            SELECT parent_ssa, child_ssa, source_flags, relation_raw_label
            FROM ssa_derivada_matrix
            WHERE active = 1
            """
        ).fetchone()

    assert row == ("202500001", "202500002", 2, "Derivada da")


def test_sync_merges_edges_from_multiple_sheet_files(temp_db, tmp_path: Path):
    _insert_ssa_rows(
        temp_db,
        [
            ("202500001", None),
            ("202500002", None),
            ("202500003", None),
        ],
    )

    sheet_one = tmp_path / "derivadas_part_1.csv"
    with sheet_one.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(
            fh, fieldnames=["parent_ssa", "child_ssa", "relation_label"]
        )
        writer.writeheader()
        writer.writerow(
            {
                "parent_ssa": "202500001",
                "child_ssa": "202500002",
                "relation_label": "Derivada da",
            }
        )

    sheet_two = tmp_path / "derivadas_part_2.csv"
    with sheet_two.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(
            fh, fieldnames=["parent_ssa", "child_ssa", "relation_label"]
        )
        writer.writeheader()
        writer.writerow(
            {
                "parent_ssa": "202500001",
                "child_ssa": "202500003",
                "relation_label": "Derivada da",
            }
        )

    report = sync_derivadas(
        temp_db,
        include_db_source=False,
        sheet_files=[str(sheet_one), str(sheet_two)],
    )

    assert report["sheet_stats"]["accepted_edges"] == 2
    assert report["sheet_stats"]["files_count"] == 2
    assert report["merge_stats"]["merged_edges"] == 2
    assert sorted(report["sheet_files"]) == sorted([str(sheet_one), str(sheet_two)])
    file_reports = report["sheet_file_reports"]
    assert len(file_reports) == 2
    assert all(bool(entry["has_parse_evidence"]) for entry in file_reports)
    evidence = report["sheet_evidence"]
    assert evidence["files_total"] == 2
    assert evidence["files_with_evidence"] == 2
    assert evidence["files_without_evidence"] == []
    assert evidence["is_complete"] is True

    with sqlite3.connect(temp_db) as conn:
        rows = conn.execute(
            """
            SELECT parent_ssa, child_ssa
            FROM ssa_derivada_matrix
            WHERE active = 1
            ORDER BY parent_ssa, child_ssa
            """
        ).fetchall()

    assert rows == [("202500001", "202500002"), ("202500001", "202500003")]


def test_sync_deactivates_sheet_source_when_sheet_later_has_no_edges(
    temp_db,
    tmp_path: Path,
):
    _insert_ssa_rows(
        temp_db,
        [
            ("202500001", None),
            ("202500002", None),
        ],
    )

    sheet_file = tmp_path / "derivadas.csv"
    with sheet_file.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(
            fh,
            fieldnames=["parent_ssa", "child_ssa", "relation_label"],
        )
        writer.writeheader()
        writer.writerow(
            {
                "parent_ssa": "202500001",
                "child_ssa": "202500002",
                "relation_label": "Derivada da",
            }
        )

    initial_report = sync_derivadas(
        temp_db,
        include_db_source=False,
        sheet_file=str(sheet_file),
    )
    assert initial_report["active_edges"] == 1

    empty_sheet_file = tmp_path / "derivadas_empty.csv"
    with empty_sheet_file.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(
            fh,
            fieldnames=["parent_ssa", "child_ssa", "relation_label"],
        )
        writer.writeheader()

    report = sync_derivadas(
        temp_db,
        include_db_source=False,
        sheet_file=str(empty_sheet_file),
    )

    assert report["managed_sources"] == [derivadas_sync.SOURCE_SHEET_DERIVADAS]
    assert report["active_edges"] == 0
    with sqlite3.connect(temp_db) as conn:
        active_source_rows = conn.execute(
            """
            SELECT COUNT(*)
            FROM ssa_derivada_source
            WHERE source_name = ? AND is_active = 1
            """,
            (derivadas_sync.SOURCE_SHEET_DERIVADAS,),
        ).fetchone()[0]
        active_matrix_rows = conn.execute(
            "SELECT COUNT(*) FROM ssa_derivada_matrix WHERE active = 1"
        ).fetchone()[0]

    assert active_source_rows == 0
    assert active_matrix_rows == 0


def test_sync_deduplicates_sheet_files_across_relative_and_absolute_paths(
    temp_db, tmp_path: Path
):
    _insert_ssa_rows(
        temp_db,
        [
            ("202500001", None),
            ("202500002", None),
        ],
    )

    sheet_file = tmp_path / "derivadas.csv"
    with sheet_file.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(
            fh, fieldnames=["parent_ssa", "child_ssa", "relation_label"]
        )
        writer.writeheader()
        writer.writerow(
            {
                "parent_ssa": "202500001",
                "child_ssa": "202500002",
                "relation_label": "Derivada da",
            }
        )

    relative = os.path.relpath(str(sheet_file.resolve()), start=str(Path.cwd()))
    absolute = str(sheet_file.resolve())
    report = sync_derivadas(
        temp_db,
        include_db_source=False,
        sheet_files=[relative, absolute],
    )

    assert report["sheet_stats"]["accepted_edges"] == 1
    assert report["sheet_stats"]["files_count"] == 1
    assert report["sheet_files"] == [absolute]
    assert len(report["sheet_file_reports"]) == 1
    assert report["sheet_file_reports"][0]["sheet_file"] == absolute
    assert report["sheet_file_reports"][0]["has_parse_evidence"] is True


def test_sync_parses_special_visual_derivadas_sheet_layout(temp_db, tmp_path: Path):
    _insert_ssa_rows(
        temp_db,
        [
            ("202500001", None),
            ("202500002", None),
            ("202500003", None),
        ],
    )

    sheet_file = tmp_path / "SSAs Derivadas e Relacionadas_13-02-2026_0124PM.xlsx"
    visual_rows = [
        [
            None,
            None,
            None,
            "SSAs Derivadas e Relacionadas",
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
        ],
        [
            "Numero da SSA",
            "Localizacao",
            "Setor Emissor",
            "Setor Executor",
            "Situacao",
            "Numero da SSA",
            "Setor Emissor",
            "Setor Executor",
            "Situacao",
            "Relacao",
            "Numero da SSA",
            "Setor Emissor",
            "Setor Executor",
            "Situacao",
        ],
        [
            "202500001",
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
        ],
        [
            None,
            None,
            None,
            None,
            None,
            "202500001",
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
        ],
        [
            None,
            None,
            None,
            None,
            None,
            "Sem derivadas em visualizacao simplificada.",
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
        ],
        [
            None,
            None,
            None,
            None,
            None,
            "202500002",
            None,
            None,
            None,
            "Derivada da",
            "202500001",
            None,
            None,
            None,
        ],
        [
            None,
            None,
            None,
            None,
            None,
            "202500003",
            None,
            None,
            None,
            "Derivada da",
            "202500001",
            None,
            None,
            None,
        ],
    ]
    pd.DataFrame(visual_rows).to_excel(sheet_file, index=False, header=False)

    report = sync_derivadas(
        temp_db,
        include_db_source=False,
        sheet_file=str(sheet_file),
    )

    assert report["sheet_stats"]["special_layout_detected"] == 1
    assert report["sheet_stats"]["accepted_edges"] == 2
    assert report["sheet_stats"]["informational_rows_skipped"] >= 3
    assert report["sheet_stats"]["invalid_parent"] == 0
    assert report["merge_stats"]["merged_edges"] == 2
    assert len(report["sheet_file_reports"]) == 1
    assert report["sheet_file_reports"][0]["has_parse_evidence"] is True
    assert report["sheet_evidence"]["is_complete"] is True

    with sqlite3.connect(temp_db) as conn:
        rows = conn.execute(
            """
            SELECT parent_ssa, child_ssa
            FROM ssa_derivada_matrix
            WHERE active = 1
            ORDER BY parent_ssa, child_ssa
            """
        ).fetchall()

    assert rows == [("202500001", "202500002"), ("202500001", "202500003")]


def test_sync_parses_special_visual_derivadas_sheet_shifted_columns(
    temp_db,
    tmp_path: Path,
):
    _insert_ssa_rows(
        temp_db,
        [
            ("202500001", None),
            ("202500002", None),
        ],
    )

    sheet_file = tmp_path / "SSAs Derivadas e Relacionadas_shifted.xlsx"
    visual_rows = [
        [None] * 16,
        [None] * 16,
        [None] * 16,
        [None] * 16,
    ]
    visual_rows[0][3] = "SSAs Derivadas e Relacionadas"
    visual_rows[1][0] = "Numero da SSA"
    visual_rows[1][6] = "Numero da SSA"
    visual_rows[1][10] = "Relacao"
    visual_rows[1][11] = "Numero da SSA"
    visual_rows[2][0] = "202500001"
    visual_rows[3][6] = "202500002"
    visual_rows[3][10] = "Derivada da"
    visual_rows[3][11] = "202500001"
    pd.DataFrame(visual_rows).to_excel(sheet_file, index=False, header=False)

    report = sync_derivadas(
        temp_db,
        include_db_source=False,
        sheet_file=str(sheet_file),
    )

    assert report["sheet_stats"]["special_layout_detected"] == 1
    assert report["sheet_stats"]["accepted_edges"] == 1

    with sqlite3.connect(temp_db) as conn:
        rows = conn.execute(
            """
            SELECT parent_ssa, child_ssa
            FROM ssa_derivada_matrix
            WHERE active = 1
            """
        ).fetchall()

    assert rows == [("202500001", "202500002")]


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
        conn.execute(
            "UPDATE ssa_table SET derivada_de = NULL WHERE numero_ssa = '202500003'"
        )
        conn.commit()

    second = sync_derivadas(temp_db, full_rebuild=True)
    assert second["active_edges"] == 1

    with sqlite3.connect(temp_db) as conn:
        total_matrix = conn.execute(
            "SELECT COUNT(*) FROM ssa_derivada_matrix"
        ).fetchone()[0]
        active_matrix = conn.execute(
            "SELECT COUNT(*) FROM ssa_derivada_matrix WHERE active = 1"
        ).fetchone()[0]

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

        cols = [
            row[1]
            for row in conn.execute("PRAGMA table_info(ssa_derivada_matrix)").fetchall()
        ]
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


def test_sync_succeeds_after_short_write_lock_contention(temp_db):
    _insert_ssa_rows(
        temp_db,
        [
            ("202500001", None),
            ("202500002", "202500001"),
        ],
    )

    lock_conn = sqlite3.connect(temp_db, timeout=0.1, check_same_thread=False)
    lock_conn.execute("BEGIN EXCLUSIVE")

    begin_called = threading.Event()
    original_begin = derivadas_sync._begin_derivadas_write_transaction

    def patched_begin(conn: sqlite3.Connection) -> None:
        begin_called.set()
        return original_begin(conn)

    derivadas_sync._begin_derivadas_write_transaction = cast(Any, patched_begin)

    def release_lock() -> None:
        begin_called.wait(timeout=2.0)
        lock_conn.rollback()
        lock_conn.close()

    releaser = threading.Thread(target=release_lock, daemon=True)
    releaser.start()
    try:
        report = sync_derivadas(temp_db)
    finally:
        derivadas_sync._begin_derivadas_write_transaction = cast(Any, original_begin)
        releaser.join(timeout=2.0)

    assert report["active_edges"] == 1


def test_get_sync_stats_remains_read_only_under_write_lock(temp_db):
    _insert_ssa_rows(
        temp_db,
        [
            ("202500001", None),
            ("202500002", "202500001"),
        ],
    )
    sync_derivadas(temp_db)

    lock_conn = sqlite3.connect(temp_db, timeout=0.1, check_same_thread=False)
    lock_conn.execute("BEGIN IMMEDIATE")
    started_at = time.perf_counter()
    try:
        stats = get_sync_stats(temp_db)
        elapsed = time.perf_counter() - started_at
    finally:
        lock_conn.rollback()
        lock_conn.close()

    assert stats["matrix_active"] == 1
    assert elapsed < 0.5


def test_sync_requires_at_least_one_source(temp_db):
    _insert_ssa_rows(
        temp_db,
        [
            ("202500001", None),
            ("202500002", "202500001"),
        ],
    )

    with pytest.raises(ValueError, match="at least one source"):
        sync_derivadas(temp_db, include_db_source=False, sheet_file=None)


def test_get_sync_stats_on_fresh_db_reports_schema_not_ready(temp_db):
    stats = get_sync_stats(temp_db)
    assert stats["schema_ready"] is False
    assert stats["matrix_total"] == 0
    assert stats["latest_sync"] is None


def test_sync_rejects_missing_sheet_file(temp_db, tmp_path: Path):
    _insert_ssa_rows(
        temp_db,
        [
            ("202500001", None),
            ("202500002", None),
        ],
    )
    missing = tmp_path / "does_not_exist.csv"
    try:
        sync_derivadas(
            temp_db,
            include_db_source=False,
            sheet_file=str(missing),
        )
    except FileNotFoundError as exc:
        assert "not found" in str(exc).lower()
    else:
        assert False, "sync_derivadas should fail for non-existing sheet_file"


def test_sync_validates_sheet_file_path_before_read(temp_db, tmp_path: Path, monkeypatch):
    _insert_ssa_rows(
        temp_db,
        [
            ("202500001", None),
            ("202500002", None),
        ],
    )
    sheet_file = tmp_path / "blocked_derivadas.csv"
    sheet_file.write_text("parent_ssa,child_ssa\n202500001,202500002\n", encoding="utf-8")

    def _guard_path(path, *, purpose, expect_directory):
        assert expect_directory is False
        if "sheet file" in purpose:
            raise PathSafetyError("blocked derivadas sheet")
        return Path(path)

    def _unexpected_read(*_args, **_kwargs):
        raise AssertionError("sheet reader should not run before path validation")

    monkeypatch.setattr(derivadas_sync, "ensure_path_is_allowed", _guard_path)
    monkeypatch.setattr(derivadas_sync.pd, "read_csv", _unexpected_read)

    with pytest.raises(PathSafetyError, match="blocked derivadas sheet"):
        sync_derivadas(
            temp_db,
            include_db_source=False,
            sheet_file=str(sheet_file),
        )


def test_sync_validates_sheet_files_paths_before_read(temp_db, tmp_path: Path, monkeypatch):
    _insert_ssa_rows(
        temp_db,
        [
            ("202500001", None),
            ("202500002", None),
        ],
    )
    allowed = tmp_path / "allowed_derivadas.csv"
    blocked = tmp_path / "blocked_derivadas.csv"
    for sheet_file in (allowed, blocked):
        sheet_file.write_text(
            "parent_ssa,child_ssa\n202500001,202500002\n",
            encoding="utf-8",
        )

    def _guard_path(path, *, purpose, expect_directory):
        assert expect_directory is False
        if "sheet file" in purpose and Path(path).name == blocked.name:
            raise PathSafetyError("blocked derivadas sheet list")
        return Path(path)

    def _unexpected_read(*_args, **_kwargs):
        raise AssertionError("sheet reader should not run after a blocked sheet path")

    monkeypatch.setattr(derivadas_sync, "ensure_path_is_allowed", _guard_path)
    monkeypatch.setattr(derivadas_sync.pd, "read_csv", _unexpected_read)

    with pytest.raises(PathSafetyError, match="blocked derivadas sheet list"):
        sync_derivadas(
            temp_db,
            include_db_source=False,
            sheet_files=[str(allowed), str(blocked)],
        )


def test_sync_rejects_corrupt_excel_sheet_file_with_clear_error(
    temp_db, tmp_path: Path
):
    _insert_ssa_rows(
        temp_db,
        [
            ("202500001", None),
            ("202500002", None),
        ],
    )
    corrupt = tmp_path / "corrupt.xlsx"
    corrupt.write_bytes(b"not-a-real-workbook")

    with pytest.raises(
        ValueError, match="Failed to parse sheet source file"
    ) as exc_info:
        sync_derivadas(
            temp_db,
            include_db_source=False,
            sheet_file=str(corrupt),
        )

    assert str(corrupt) in str(exc_info.value)


def test_sync_sheet_only_verify_only_works_without_ssa_table(tmp_path: Path):
    db_path = tmp_path / "sheet_only_no_ssa_table.db"
    with sqlite3.connect(db_path) as conn:
        conn.execute("CREATE TABLE only_dummy_table (id INTEGER PRIMARY KEY)")
        conn.commit()

    sheet_file = tmp_path / "derivadas_sheet_only.csv"
    with sheet_file.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(
            fh, fieldnames=["parent_ssa", "child_ssa", "relation_label"]
        )
        writer.writeheader()
        writer.writerow(
            {
                "parent_ssa": "202500001",
                "child_ssa": "202500002",
                "relation_label": "Derivada da",
            }
        )

    report = sync_derivadas(
        str(db_path),
        include_db_source=False,
        sheet_file=str(sheet_file),
        verify_only=True,
    )

    assert report["verify_only"] is True
    assert report["sheet_stats"]["accepted_edges"] == 1
    assert report["reconciliation"]["orphan_parents_count"] == 1
    assert report["reconciliation"]["orphan_children_count"] == 1


def test_sync_tracks_longer_closure_paths_in_max_distance(temp_db):
    _insert_ssa_rows(
        temp_db,
        [
            ("202500001", None),
            ("202500002", "202500001"),
            ("202500003", "202500001"),
            ("202500004", "202500002"),
            ("202500005", "202500003"),
            ("202500005", "202500004"),
        ],
    )

    sync_derivadas(temp_db)

    with sqlite3.connect(temp_db) as conn:
        closure_row = conn.execute(
            """
            SELECT min_distance, max_distance, path_count
            FROM ssa_derivada_closure
            WHERE ancestor_ssa = '202500001' AND descendant_ssa = '202500005'
            """
        ).fetchone()

    assert closure_row == (2, 3, 1)


def test_sync_include_db_source_true_treats_missing_ssa_table_as_empty_source(
    tmp_path: Path,
):
    db_path = tmp_path / "include_db_source_without_ssa_table.db"
    with sqlite3.connect(db_path) as conn:
        conn.execute("CREATE TABLE only_dummy_table (id INTEGER PRIMARY KEY)")
        conn.commit()

    sheet_file = tmp_path / "derivadas_sheet_only_with_db_flag.csv"
    with sheet_file.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(
            fh, fieldnames=["parent_ssa", "child_ssa", "relation_label"]
        )
        writer.writeheader()
        writer.writerow(
            {
                "parent_ssa": "202500001",
                "child_ssa": "202500002",
                "relation_label": "Derivada da",
            }
        )

    report = sync_derivadas(
        str(db_path),
        include_db_source=True,
        sheet_file=str(sheet_file),
    )

    assert report["db_stats"]["accepted_edges"] == 0
    assert report["sheet_stats"]["accepted_edges"] == 1
    assert report["active_edges"] == 1


def test_sync_rolls_back_partial_writes_and_persists_error_run(temp_db, monkeypatch):
    _insert_ssa_rows(
        temp_db,
        [
            ("202500001", None),
            ("202500002", "202500001"),
        ],
    )

    def _raise_on_summary(*args, **kwargs):
        raise RuntimeError("forced summary failure")

    monkeypatch.setattr(derivadas_sync, "_replace_summary", _raise_on_summary)

    with pytest.raises(RuntimeError, match="forced summary failure"):
        sync_derivadas(temp_db)

    with sqlite3.connect(temp_db) as conn:
        matrix_total = conn.execute(
            "SELECT COUNT(*) FROM ssa_derivada_matrix"
        ).fetchone()[0]
        closure_total = conn.execute(
            "SELECT COUNT(*) FROM ssa_derivada_closure"
        ).fetchone()[0]
        summary_total = conn.execute(
            "SELECT COUNT(*) FROM ssa_derivada_summary"
        ).fetchone()[0]
        latest_run = conn.execute(
            """
            SELECT status, active_edges
            FROM ssa_derivada_sync_run
            ORDER BY sync_run_id DESC
            LIMIT 1
            """
        ).fetchone()

    assert matrix_total == 0
    assert closure_total == 0
    assert summary_total == 0
    assert latest_run == ("error", 0)


def test_sync_aborts_when_integrity_check_fails(temp_db, monkeypatch):
    _insert_ssa_rows(
        temp_db,
        [
            ("202500001", None),
            ("202500002", "202500001"),
        ],
    )

    def _fake_integrity_scan(_conn):
        return {
            "is_consistent": False,
            "issue_counts": {
                "missing_source_pairs": 1,
                "source_without_matrix_pairs": 0,
                "flag_mismatch_pairs": 0,
                "invalid_matrix_pairs": 0,
                "closure_self_rows": 0,
                "summary_missing_nodes": 0,
                "summary_extra_nodes": 0,
            },
            "matrix_active_edges": 1,
            "source_active_edges": 1,
            "summary_nodes": 2,
            "samples": {
                "missing_source_pairs": ["202500001->202500002"],
                "source_without_matrix_pairs": [],
                "flag_mismatch_pairs": [],
                "invalid_matrix_pairs": [],
                "summary_missing_nodes": [],
                "summary_extra_nodes": [],
            },
        }

    monkeypatch.setattr(
        derivadas_sync, "_scan_materialization_integrity", _fake_integrity_scan
    )

    with pytest.raises(RuntimeError, match="integrity check failed"):
        sync_derivadas(temp_db)

    with sqlite3.connect(temp_db) as conn:
        matrix_total = conn.execute(
            "SELECT COUNT(*) FROM ssa_derivada_matrix"
        ).fetchone()[0]
        latest_run = conn.execute(
            """
            SELECT status, active_edges
            FROM ssa_derivada_sync_run
            ORDER BY sync_run_id DESC
            LIMIT 1
            """
        ).fetchone()

    assert matrix_total == 0
    assert latest_run == ("error", 0)
