#!/usr/bin/env python3
"""Legacy integration smoke test for single Excel import path."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pandas as pd
import pytest

from armazenamento.database import insert_dataframe_to_db
from extracao.extractor import extract_data_from_excel


@pytest.fixture
def docs_entrada_dir() -> Path:
    path = Path("docs_entrada")
    if not path.exists():
        pytest.skip("docs_entrada not found")
    return path


@pytest.fixture
def excel_file_path(docs_entrada_dir: Path) -> Path:
    files = sorted(
        file_path
        for file_path in docs_entrada_dir.iterdir()
        if file_path.suffix.lower() == ".xlsx" and not file_path.name.startswith("~$")
    )
    if not files:
        pytest.skip("no xlsx files found in docs_entrada")
    return files[0]


@pytest.fixture
def extracted_dataframe(excel_file_path: Path) -> pd.DataFrame:
    df = extract_data_from_excel(str(excel_file_path))
    if df is None or df.empty:
        pytest.skip(f"extractor returned empty dataframe for {excel_file_path.name}")
    return df


@pytest.fixture
def temp_db_path(tmp_path: Path) -> Path:
    return tmp_path / "ssa_data.db"


def _write_markdown_report(
    report_path: Path, *, excel_name: str, row_count: int, inserted_count: int
) -> None:
    content = (
        "# Legacy Single Import Report\n\n"
        f"- excel_file: {excel_name}\n"
        f"- extracted_rows: {row_count}\n"
        f"- inserted_rows: {inserted_count}\n"
    )
    report_path.write_text(content, encoding="utf-8")


def test_single_file(
    extracted_dataframe: pd.DataFrame,
    temp_db_path: Path,
    tmp_path: Path,
    excel_file_path: Path,
) -> None:
    success = insert_dataframe_to_db(
        extracted_dataframe, str(temp_db_path), "ssa_table"
    )
    assert success is True

    with sqlite3.connect(temp_db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM ssa_table")
        inserted_count = int(cursor.fetchone()[0])

    assert inserted_count > 0

    report_path = tmp_path / "legacy_single_import_report.md"
    _write_markdown_report(
        report_path,
        excel_name=excel_file_path.name,
        row_count=len(extracted_dataframe),
        inserted_count=inserted_count,
    )
    assert report_path.exists()
