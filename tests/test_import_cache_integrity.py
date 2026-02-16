# tests/test_import_cache_integrity.py
from __future__ import annotations

from pathlib import Path

import pytest

from core.app_logic import run_importer_logic


def test_cache_not_updated_when_extraction_fails(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    docs_dir = tmp_path / "docs_entrada"
    docs_dir.mkdir()
    (docs_dir / "broken.xlsx").write_text("not an xlsx file", encoding="utf-8")

    data_dir = tmp_path / "data"

    # Path safety allowlist is computed at import-time. Ensure tmp_path is allowed
    # so this test is stable across platforms/pytest tempdir layouts.
    from utils import path_safety

    monkeypatch.setattr(
        path_safety,
        "ALLOWED_ROOTS",
        list(path_safety.ALLOWED_ROOTS) + [tmp_path],
    )

    updated = run_importer_logic(
        docs_dir=str(docs_dir),
        data_dir=str(data_dir),
        db_name="test.db",
        table_name="ssa_table",
        force_import=True,
    )

    assert updated is False
    assert not (data_dir / "file_cache.json").exists()

