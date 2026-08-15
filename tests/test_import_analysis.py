#!/usr/bin/env python3
"""Regression guard for import-analysis helper script behavior."""

from __future__ import annotations

from pathlib import Path


def _build_report_path(output_dir: Path, stamp: str) -> Path:
    return output_dir / f"import_analysis_{stamp}.txt"


def test_import_analysis_report_path_uses_output_dir(tmp_path: Path) -> None:
    report = _build_report_path(tmp_path, "20260226_123000")
    assert report.parent == tmp_path
    assert report.name == "import_analysis_20260226_123000.txt"
