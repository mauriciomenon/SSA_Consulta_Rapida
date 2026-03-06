from __future__ import annotations

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
