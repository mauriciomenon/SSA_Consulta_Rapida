from __future__ import annotations

import json
from pathlib import Path

from core import import_consolidation
from core.import_consolidation import consolidate_input_files


def test_consolidate_input_files_moves_success_and_zero_survivor(
    tmp_path: Path,
) -> None:
    docs_dir = tmp_path / "docs_entrada"
    logs_dir = tmp_path / "logs"
    docs_dir.mkdir()
    logs_dir.mkdir()

    (docs_dir / "ok.xlsx").write_text("ok", encoding="utf-8")
    (docs_dir / "zero.xls").write_text("zero", encoding="utf-8")
    (docs_dir / "pending.xlsx").write_text("pending", encoding="utf-8")

    payload = {
        "paths": {"docs_dir": str(docs_dir)},
        "file_reports": [
            {"file": "ok.xlsx", "counts": {"rows_inserted": 1}},
            {"file": "zero.xls", "counts": {"rows_inserted": 0}},
        ],
    }
    (logs_dir / "import_run_20260327_000001_000001.json").write_text(
        json.dumps(payload),
        encoding="utf-8",
    )

    result = consolidate_input_files(project_root=str(tmp_path))

    assert result["moved"] == 2
    assert result["nosurvivor"] == 1
    assert result["pending"] == 1
    assert result["failed"] == 0
    assert (docs_dir / "processadas" / "ok.xlsx").exists()
    assert (docs_dir / "processadas" / "nosurvivor" / "zero.xls").exists()
    assert (docs_dir / "pending.xlsx").exists()


def test_consolidate_input_files_preserves_existing_destination(
    tmp_path: Path,
) -> None:
    docs_dir = tmp_path / "docs_entrada"
    logs_dir = tmp_path / "logs"
    processadas_dir = docs_dir / "processadas"
    docs_dir.mkdir()
    logs_dir.mkdir()
    processadas_dir.mkdir()

    (docs_dir / "ok.xlsx").write_text("new", encoding="utf-8")
    (processadas_dir / "ok.xlsx").write_text("existing", encoding="utf-8")

    payload = {
        "paths": {"docs_dir": str(docs_dir)},
        "file_reports": [
            {"file": "ok.xlsx", "counts": {"rows_inserted": 1}},
        ],
    }
    (logs_dir / "import_run_20260327_000001_000001.json").write_text(
        json.dumps(payload),
        encoding="utf-8",
    )

    result = consolidate_input_files(project_root=str(tmp_path))

    assert result["moved"] == 1
    assert result["failed"] == 0
    assert (processadas_dir / "ok.xlsx").read_text(encoding="utf-8") == "existing"
    assert (processadas_dir / "ok__1.xlsx").read_text(encoding="utf-8") == "new"
    assert not (docs_dir / "ok.xlsx").exists()


def test_consolidate_input_files_reports_replace_failure_and_removes_reservation(
    tmp_path: Path,
    monkeypatch,
) -> None:
    docs_dir = tmp_path / "docs_entrada"
    logs_dir = tmp_path / "logs"
    docs_dir.mkdir()
    logs_dir.mkdir()

    (docs_dir / "ok.xlsx").write_text("new", encoding="utf-8")

    payload = {
        "paths": {"docs_dir": str(docs_dir)},
        "file_reports": [
            {"file": "ok.xlsx", "counts": {"rows_inserted": 1}},
        ],
    }
    (logs_dir / "import_run_20260327_000001_000001.json").write_text(
        json.dumps(payload),
        encoding="utf-8",
    )
    errors: list[str] = []

    def fail_replace(source: object, destination: object) -> None:
        raise PermissionError(f"blocked: {source} -> {destination}")

    monkeypatch.setattr(import_consolidation.os, "replace", fail_replace)

    result = consolidate_input_files(
        project_root=str(tmp_path),
        error_callback=errors.append,
    )

    assert result["moved"] == 0
    assert result["failed"] == 1
    assert (docs_dir / "ok.xlsx").exists()
    assert not (docs_dir / "processadas" / "ok.xlsx").exists()
    assert any("blocked:" in error for error in errors)
