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


def test_run_importer_logic_writes_report_on_success(
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
    assert payload["files"]["success"] == ["ok.xlsx"]


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
