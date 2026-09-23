from __future__ import annotations

from pathlib import Path

import pytest

from core import app_logic


@pytest.mark.parametrize(
    ("force_import", "explicit", "file_count", "expected_enforcement"),
    (
        (True, None, 797, False),
        (False, ("explicit.xlsx",), 65, True),
    ),
)
def test_run_importer_logic_applies_count_limit_only_outside_trusted_full_rescan(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    force_import: bool,
    explicit: tuple[str, ...] | None,
    file_count: int,
    expected_enforcement: bool,
) -> None:
    docs_dir = tmp_path / "docs_entrada"
    data_dir = tmp_path / "data"
    docs_dir.mkdir()
    data_dir.mkdir()
    discovered = [str(docs_dir / f"file_{index}.xlsx") for index in range(file_count)]
    captured_paths: list[str] = []
    captured_enforcement: list[bool] = []

    monkeypatch.setattr(
        app_logic,
        "_prepare_working_database_for_import",
        lambda **_kwargs: (str(data_dir / "ssas.db"), None, {}),
    )
    monkeypatch.setattr(
        app_logic,
        "_resolve_import_work_items",
        lambda **_kwargs: {
            "ignored_legacy_excel_files": [],
            "discovery_settings": {},
            "files_to_process": discovered,
            "derivadas_sheet_files": [],
            "move_processed_after_import": False,
        },
    )
    monkeypatch.setattr(app_logic, "_write_import_run_report", lambda _payload: None)

    def _capture_limits(paths, **kwargs):
        captured_paths.extend(paths)
        captured_enforcement.append(bool(kwargs["enforce_batch_file_limit"]))
        raise app_logic.extractor.ExtractionError("stop after preflight")

    monkeypatch.setattr(
        app_logic.extractor,
        "validate_excel_import_limits",
        _capture_limits,
    )

    with pytest.raises(app_logic.ImporterError, match="stop after preflight"):
        app_logic.run_importer_logic(
            docs_dir=str(docs_dir),
            data_dir=str(data_dir),
            force_import=force_import,
            explicit_files=explicit,
        )

    assert len(captured_paths) == file_count
    assert captured_enforcement == [expected_enforcement]
