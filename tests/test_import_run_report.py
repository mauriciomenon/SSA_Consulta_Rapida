from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any, cast

import pytest

from core import app_logic


def _allow_tmp_path(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    from utils import path_safety

    monkeypatch.setattr(
        path_safety,
        "ALLOWED_ROOTS",
        list(path_safety.ALLOWED_ROOTS) + [tmp_path],
    )


def _mock_db_ok(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        app_logic.database,
        "repair_database_if_needed",
        lambda *args, **kwargs: True,
    )
    monkeypatch.setattr(
        app_logic.database,
        "verify_database_integrity",
        lambda *args, **kwargs: {
            "is_valid": True,
            "issues": [],
            "warnings": [],
            "database_accessible": True,
            "table_exists": True,
            "schema_valid": True,
            "data_consistent": True,
            "disk_space_sufficient": True,
        },
    )


def _init_minimal_ssa_db(db_path: Path, descricao: str) -> None:
    conn = sqlite3.connect(db_path)
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS ssa_table (
                numero_ssa TEXT,
                situacao TEXT,
                data_cadastro TEXT,
                descricao_ssa TEXT
            )
            """
        )
        conn.execute("DELETE FROM ssa_table")
        conn.execute(
            """
            INSERT INTO ssa_table (numero_ssa, situacao, data_cadastro, descricao_ssa)
            VALUES (?, ?, ?, ?)
            """,
            ("202500001", "OLD", "2025-01-01 00:00:00", descricao),
        )
        conn.commit()
    finally:
        conn.close()


def _read_descricao(db_path: Path) -> str:
    conn = sqlite3.connect(db_path)
    try:
        row = conn.execute(
            "SELECT descricao_ssa FROM ssa_table WHERE numero_ssa = ?",
            ("202500001",),
        ).fetchone()
    finally:
        conn.close()
    assert row is not None
    return str(row[0])


def test_run_importer_logic_writes_report_on_no_changes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    docs_dir = tmp_path / "docs_entrada"
    docs_dir.mkdir()
    (docs_dir / "legado.xls").write_text("legacy", encoding="utf-8")
    data_dir = tmp_path / "data"

    _allow_tmp_path(monkeypatch, tmp_path)
    _mock_db_ok(monkeypatch)
    monkeypatch.setattr(app_logic, "_get_files_to_process", lambda *args, **kwargs: [])
    monkeypatch.setattr(
        app_logic,
        "_discover_derivadas_sheet_files",
        lambda *args, **kwargs: [],
    )

    captured: dict[str, Any] = {}

    def _fake_write(payload: dict) -> str:
        captured["payload"] = payload
        return str(tmp_path / "import_run_fake.json")

    monkeypatch.setattr(app_logic, "_write_import_run_report", _fake_write)

    updated = app_logic.run_importer_logic(
        docs_dir=str(docs_dir),
        data_dir=str(data_dir),
        db_name="test.db",
        table_name="ssa_table",
        force_import=False,
    )

    assert updated is False
    assert "payload" in captured
    payload = cast(dict[str, Any], captured["payload"])
    assert payload["status"] == "no_changes"
    assert payload["result"] is False
    assert payload["counts"]["total_candidates"] == 0
    assert payload["counts"]["success_count"] == 0
    assert payload["counts"]["ignored_legacy_excel_count"] == 1
    assert payload["files"]["ignored_legacy_excel"] == ["legado.xls"]


def test_run_importer_logic_writes_report_on_success(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    docs_dir = tmp_path / "docs_entrada"
    docs_dir.mkdir()
    data_dir = tmp_path / "data"
    file_ok = docs_dir / "ok.xlsx"
    file_ok.write_text("placeholder", encoding="utf-8")
    (docs_dir / "legado.xls").write_text("legacy", encoding="utf-8")

    _allow_tmp_path(monkeypatch, tmp_path)
    _mock_db_ok(monkeypatch)
    monkeypatch.setattr(
        app_logic,
        "_get_files_to_process",
        lambda *args, **kwargs: [str(file_ok)],
    )
    monkeypatch.setattr(
        app_logic,
        "_discover_derivadas_sheet_files",
        lambda *args, **kwargs: [],
    )
    monkeypatch.setattr(
        app_logic,
        "_run_derivadas_sync_phase",
        lambda *args, **kwargs: (True, [], {"db_stats": {}, "merge_stats": {}}),
    )
    monkeypatch.setattr(
        app_logic,
        "_import_single_file",
        lambda *args, **kwargs: (True, 1),
    )
    monkeypatch.setattr(
        app_logic,
        "_update_cache_after_import",
        lambda *args, **kwargs: None,
    )

    captured: dict[str, Any] = {}

    def _fake_write(payload: dict) -> str:
        captured["payload"] = payload
        return str(tmp_path / "import_run_fake_success.json")

    monkeypatch.setattr(app_logic, "_write_import_run_report", _fake_write)

    updated = app_logic.run_importer_logic(
        docs_dir=str(docs_dir),
        data_dir=str(data_dir),
        db_name="test.db",
        table_name="ssa_table",
        force_import=False,
    )

    assert updated is True
    assert "payload" in captured
    payload = cast(dict[str, Any], captured["payload"])
    assert payload["status"] == "updated"
    assert payload["result"] is True
    assert payload["counts"]["total_candidates"] == 1
    assert payload["counts"]["success_count"] == 1
    assert payload["counts"]["ignored_legacy_excel_count"] == 1
    assert payload["files"]["success"] == ["ok.xlsx"]
    assert payload["files"]["ignored_legacy_excel"] == ["legado.xls"]


def test_run_importer_logic_report_includes_file_phase_metrics(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    docs_dir = tmp_path / "docs_entrada"
    docs_dir.mkdir()
    data_dir = tmp_path / "data"
    file_ok = docs_dir / "ok.xlsx"
    file_ok.write_text("placeholder", encoding="utf-8")

    _allow_tmp_path(monkeypatch, tmp_path)
    _mock_db_ok(monkeypatch)
    monkeypatch.setattr(
        app_logic,
        "_get_files_to_process",
        lambda *args, **kwargs: [str(file_ok)],
    )
    monkeypatch.setattr(
        app_logic,
        "_discover_derivadas_sheet_files",
        lambda *args, **kwargs: [],
    )

    def _fake_import_single_file(file_path: str, db_path: str, *args, **kwargs) -> tuple[bool, int]:
        metrics_out = kwargs.get("_metrics_out")
        if isinstance(metrics_out, dict):
            metrics_out.update(
                {
                    "file": "ok.xlsx",
                    "status": "success",
                    "durations": {
                        "extraction_seconds": 0.123,
                        "validation_seconds": 0.045,
                        "insert_seconds": 0.067,
                    },
                    "counts": {
                        "rows_extracted": 10,
                        "rows_before_invalid_filter": 12,
                        "rows_removed_invalid_identity": 2,
                        "rows_removed_required_validation": 1,
                        "rows_ready_for_insert": 7,
                        "rows_inserted": 7,
                    },
                    "invalid_identity_tracked": True,
                    "invalid_identity": {
                        "total_removed": 2,
                        "empty_removed": 1,
                        "payload_removed": 1,
                        "payload_columns_sample": ["data_cadastro", "responsavel_execucao"],
                    },
                }
            )
        return True, 7

    monkeypatch.setattr(app_logic, "_import_single_file", _fake_import_single_file)
    monkeypatch.setattr(
        app_logic,
        "_update_cache_after_import",
        lambda *args, **kwargs: None,
    )

    captured: dict[str, Any] = {}

    def _fake_write(payload: dict) -> str:
        captured["payload"] = payload
        return str(tmp_path / "import_run_fake_metrics.json")

    monkeypatch.setattr(app_logic, "_write_import_run_report", _fake_write)

    updated = app_logic.run_importer_logic(
        docs_dir=str(docs_dir),
        data_dir=str(data_dir),
        db_name="test.db",
        table_name="ssa_table",
        force_import=False,
    )

    assert updated is True
    payload = cast(dict[str, Any], captured["payload"])
    assert payload["counts"]["rows_extracted_total"] == 10
    assert payload["counts"]["rows_removed_invalid_identity_total"] == 2
    assert payload["counts"]["rows_ready_for_insert_total"] == 7
    assert payload["counts"]["rows_inserted_total"] == 7
    assert payload["durations"]["sum_file_extraction_seconds"] == 0.123
    assert payload["durations"]["sum_file_validation_seconds"] == 0.045
    assert payload["durations"]["sum_file_insert_seconds"] == 0.067
    assert "run_file_processing_seconds" in payload["durations"]
    assert "run_success_cache_update_seconds" in payload["durations"]
    assert "run_postprocess_move_seconds" in payload["durations"]
    assert "run_deterministic_cache_update_seconds" in payload["durations"]
    assert payload["file_reports"] == [
        {
            "file": "ok.xlsx",
            "status": "success",
            "durations": {
                "extraction_seconds": 0.123,
                "validation_seconds": 0.045,
                "insert_seconds": 0.067,
            },
            "counts": {
                "rows_extracted": 10,
                "rows_before_invalid_filter": 12,
                "rows_removed_invalid_identity": 2,
                "rows_removed_required_validation": 1,
                "rows_ready_for_insert": 7,
                "rows_inserted": 7,
            },
            "invalid_identity_tracked": True,
            "invalid_identity": {
                "total_removed": 2,
                "empty_removed": 1,
                "payload_removed": 1,
                "payload_columns_sample": ["data_cadastro", "responsavel_execucao"],
            },
        }
    ]


def test_run_importer_logic_moves_processed_files_and_updates_cache_paths(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    docs_dir = tmp_path / "docs_entrada"
    docs_dir.mkdir()
    data_dir = tmp_path / "data"
    file_ok = docs_dir / "ok.xlsx"
    file_empty = docs_dir / "empty.xlsx"
    file_ok.write_text("placeholder-ok", encoding="utf-8")
    file_empty.write_text("placeholder-empty", encoding="utf-8")

    _allow_tmp_path(monkeypatch, tmp_path)
    _mock_db_ok(monkeypatch)
    monkeypatch.setattr(
        app_logic,
        "_load_import_discovery_settings",
        lambda: {
            "include_processadas": False,
            "processadas_subdir": "processadas",
            "ignore_subdirs": ["nosurvivor"],
            "nosurvivor_subdir": "nosurvivor",
            "move_processed_after_import": True,
            "route_zero_survivor_to_nosurvivor": True,
        },
    )
    monkeypatch.setattr(
        app_logic,
        "_get_files_to_process",
        lambda *args, **kwargs: [str(file_ok), str(file_empty)],
    )
    monkeypatch.setattr(
        app_logic,
        "_discover_derivadas_sheet_files",
        lambda *args, **kwargs: [],
    )

    def _fake_import_single_file(file_path: str, db_path: str, *args, **kwargs) -> tuple[bool, int]:
        if Path(file_path).name == "empty.xlsx":
            return True, 0
        return True, 5

    monkeypatch.setattr(app_logic, "_import_single_file", _fake_import_single_file)
    monkeypatch.setattr(
        app_logic,
        "_update_cache_for_deterministic_failures",
        lambda failed_files, cache_file, docs_dir: None,
    )

    captured_cache: dict[str, Any] = {}

    def _capture_cache_paths(processed_files: list[str], cache_file: str, docs_dir: str) -> None:
        captured_cache["paths"] = list(processed_files)
        captured_cache["cache_file"] = cache_file
        captured_cache["docs_dir"] = docs_dir

    monkeypatch.setattr(app_logic, "_update_cache_after_import", _capture_cache_paths)

    updated = app_logic.run_importer_logic(
        docs_dir=str(docs_dir),
        data_dir=str(data_dir),
        db_name="test.db",
        table_name="ssa_table",
        force_import=False,
    )

    assert updated is True
    moved_ok = docs_dir / "processadas" / "ok.xlsx"
    moved_empty = docs_dir / "processadas" / "nosurvivor" / "empty.xlsx"
    assert moved_ok.exists()
    assert moved_empty.exists()
    assert not file_ok.exists()
    assert not file_empty.exists()
    assert "paths" in captured_cache
    assert sorted(Path(p).name for p in cast(list[str], captured_cache["paths"])) == [
        "empty.xlsx",
        "ok.xlsx",
    ]
    assert str(moved_ok) in cast(list[str], captured_cache["paths"])
    assert str(moved_empty) in cast(list[str], captured_cache["paths"])


def test_run_importer_logic_full_rescan_disables_postprocess_move(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    docs_dir = tmp_path / "docs_entrada"
    docs_dir.mkdir()
    data_dir = tmp_path / "data"
    file_ok = docs_dir / "ok.xlsx"
    file_ok.write_text("placeholder-ok", encoding="utf-8")

    _allow_tmp_path(monkeypatch, tmp_path)
    _mock_db_ok(monkeypatch)
    monkeypatch.setattr(
        app_logic,
        "_load_import_discovery_settings",
        lambda: {
            "include_processadas": False,
            "processadas_subdir": "processadas",
            "ignore_subdirs": ["nosurvivor"],
            "nosurvivor_subdir": "nosurvivor",
            "move_processed_after_import": True,
            "route_zero_survivor_to_nosurvivor": True,
        },
    )
    monkeypatch.setattr(
        app_logic,
        "_get_files_to_process",
        lambda *args, **kwargs: [str(file_ok)],
    )
    monkeypatch.setattr(
        app_logic,
        "_discover_derivadas_sheet_files",
        lambda *args, **kwargs: [],
    )
    monkeypatch.setattr(
        app_logic,
        "_run_derivadas_sync_phase",
        lambda *args, **kwargs: (True, [], {"db_stats": {}, "merge_stats": {}}),
    )
    monkeypatch.setattr(
        app_logic,
        "_import_single_file",
        lambda *args, **kwargs: (True, 1),
    )
    monkeypatch.setattr(
        app_logic,
        "_promote_full_rescan_candidate",
        lambda *args, **kwargs: None,
    )
    monkeypatch.setattr(
        app_logic,
        "_update_cache_after_import",
        lambda *args, **kwargs: None,
    )

    move_called = {"value": False}

    def _capture_move(**kwargs: Any) -> dict[str, str]:
        move_called["value"] = True
        return {}

    monkeypatch.setattr(app_logic, "_apply_postprocess_file_moves", _capture_move)

    updated = app_logic.run_importer_logic(
        docs_dir=str(docs_dir),
        data_dir=str(data_dir),
        db_name="test.db",
        table_name="ssa_table",
        force_import=True,
    )

    assert updated is True
    assert move_called["value"] is False
    assert file_ok.exists()


def test_run_importer_logic_full_rescan_failure_preserves_primary_db(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    docs_dir = tmp_path / "docs_entrada"
    docs_dir.mkdir()
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    file_bad = docs_dir / "bad.xlsx"
    file_bad.write_text("placeholder", encoding="utf-8")
    primary_db = data_dir / "test.db"
    _init_minimal_ssa_db(primary_db, "primary_old")

    _allow_tmp_path(monkeypatch, tmp_path)

    def _fake_repair(db_path: str, *args, **kwargs) -> bool:
        path = Path(db_path)
        if not path.exists():
            _init_minimal_ssa_db(path, "candidate_seed")
        return True

    monkeypatch.setattr(app_logic.database, "repair_database_if_needed", _fake_repair)
    monkeypatch.setattr(
        app_logic.database,
        "verify_database_integrity",
        lambda *args, **kwargs: {
            "is_valid": True,
            "issues": [],
            "warnings": [],
            "database_accessible": True,
            "table_exists": True,
            "schema_valid": True,
            "data_consistent": True,
            "disk_space_sufficient": True,
        },
    )
    monkeypatch.setattr(
        app_logic,
        "_get_files_to_process",
        lambda *args, **kwargs: [str(file_bad)],
    )
    monkeypatch.setattr(
        app_logic,
        "_discover_derivadas_sheet_files",
        lambda *args, **kwargs: [],
    )
    monkeypatch.setattr(
        app_logic,
        "_import_single_file",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            app_logic.ExtractionError("boom", error_code="MISSING_REQUIRED_COLUMNS")
        ),
    )

    captured: dict[str, Any] = {}

    def _fake_write(payload: dict) -> str:
        captured["payload"] = payload
        return str(tmp_path / "import_run_full_rescan_failure.json")

    monkeypatch.setattr(app_logic, "_write_import_run_report", _fake_write)

    updated = app_logic.run_importer_logic(
        docs_dir=str(docs_dir),
        data_dir=str(data_dir),
        db_name="test.db",
        table_name="ssa_table",
        force_import=True,
    )

    assert updated is False
    assert _read_descricao(primary_db) == "primary_old"
    payload = cast(dict[str, Any], captured["payload"])
    candidate_path = Path(str(payload["paths"]["candidate_db_path"]))
    assert candidate_path.exists()
    assert payload["paths"]["candidate_preserved"] is True
    assert payload["paths"]["working_db_path"] == str(candidate_path)


def test_run_importer_logic_full_rescan_success_promotes_candidate_at_end(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    docs_dir = tmp_path / "docs_entrada"
    docs_dir.mkdir()
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    file_ok = docs_dir / "ok.xlsx"
    file_ok.write_text("placeholder", encoding="utf-8")
    primary_db = data_dir / "test.db"
    _init_minimal_ssa_db(primary_db, "primary_old")

    _allow_tmp_path(monkeypatch, tmp_path)

    def _fake_repair(db_path: str, *args, **kwargs) -> bool:
        path = Path(db_path)
        if not path.exists():
            _init_minimal_ssa_db(path, "candidate_seed")
        return True

    monkeypatch.setattr(app_logic.database, "repair_database_if_needed", _fake_repair)
    monkeypatch.setattr(
        app_logic.database,
        "verify_database_integrity",
        lambda *args, **kwargs: {
            "is_valid": True,
            "issues": [],
            "warnings": [],
            "database_accessible": True,
            "table_exists": True,
            "schema_valid": True,
            "data_consistent": True,
            "disk_space_sufficient": True,
        },
    )
    monkeypatch.setattr(
        app_logic,
        "_get_files_to_process",
        lambda *args, **kwargs: [str(file_ok)],
    )
    monkeypatch.setattr(
        app_logic,
        "_discover_derivadas_sheet_files",
        lambda *args, **kwargs: [],
    )
    monkeypatch.setattr(
        app_logic,
        "_run_derivadas_sync_phase",
        lambda *args, **kwargs: (True, [], {"db_stats": {}, "merge_stats": {}}),
    )

    def _fake_import_single_file(file_path: str, db_path: str, *args, **kwargs) -> tuple[bool, int]:
        conn = sqlite3.connect(db_path)
        try:
            conn.execute("DELETE FROM ssa_table")
            conn.execute(
                """
                INSERT INTO ssa_table (numero_ssa, situacao, data_cadastro, descricao_ssa)
                VALUES (?, ?, ?, ?)
                """,
                ("202500001", "NEW", "2025-02-01 00:00:00", "candidate_new"),
            )
            conn.commit()
        finally:
            conn.close()
        return True, 1

    monkeypatch.setattr(app_logic, "_import_single_file", _fake_import_single_file)
    monkeypatch.setattr(
        app_logic,
        "_update_cache_after_import",
        lambda *args, **kwargs: None,
    )

    captured: dict[str, Any] = {}

    def _fake_write(payload: dict) -> str:
        captured["payload"] = payload
        return str(tmp_path / "import_run_full_rescan_success.json")

    monkeypatch.setattr(app_logic, "_write_import_run_report", _fake_write)

    updated = app_logic.run_importer_logic(
        docs_dir=str(docs_dir),
        data_dir=str(data_dir),
        db_name="test.db",
        table_name="ssa_table",
        force_import=True,
    )

    assert updated is True
    assert _read_descricao(primary_db) == "candidate_new"
    backups = sorted(data_dir.glob("test.db.full_rescan_backup_*"))
    assert backups
    assert _read_descricao(backups[-1]) == "primary_old"
    payload = cast(dict[str, Any], captured["payload"])
    assert payload["paths"]["working_db_path"] == str(primary_db)
    assert payload["paths"]["promoted_backup_path"] is not None
    candidate_path = Path(str(payload["paths"]["candidate_db_path"]))
    assert not candidate_path.exists()
    assert payload["paths"]["candidate_preserved"] is False
