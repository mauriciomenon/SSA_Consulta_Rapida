from __future__ import annotations

from pathlib import Path

from core.import_staging import stage_external_import_files


def test_stage_external_import_files_accepts_xlsx_and_xls(tmp_path: Path) -> None:
    docs_dir = tmp_path / "docs_entrada"
    docs_dir.mkdir()
    source_dir = tmp_path / "fontes"
    source_dir.mkdir()

    xlsx_file = source_dir / "entrada.xlsx"
    xlsx_file.write_text("xlsx", encoding="utf-8")
    xls_file = source_dir / "entrada.xls"
    xls_file.write_text("xls", encoding="utf-8")

    staged_files, summary = stage_external_import_files(
        project_root=str(tmp_path),
        source_files=(str(xlsx_file), str(xls_file)),
    )

    assert summary["copied"] == 2
    assert summary["failed"] == 0
    assert summary["unsupported"] == 0
    assert len(staged_files) == 2
    assert (docs_dir / "entrada.xlsx").exists()
    assert (docs_dir / "entrada.xls").exists()


def test_stage_external_import_files_creates_unique_name_with_collisions(
    tmp_path: Path,
) -> None:
    docs_dir = tmp_path / "docs_entrada"
    docs_dir.mkdir()
    existing = docs_dir / "entrada.xlsx"
    existing.write_text("old", encoding="utf-8")

    source_dir = tmp_path / "fontes"
    source_dir.mkdir()
    source = source_dir / "entrada.xlsx"
    source.write_text("new", encoding="utf-8")

    staged_files, summary = stage_external_import_files(
        project_root=str(tmp_path),
        source_files=(str(source),),
    )

    assert summary["copied"] == 1
    assert staged_files == [str(docs_dir / "entrada__1.xlsx")]
    assert (docs_dir / "entrada__1.xlsx").exists()
