from __future__ import annotations

from pathlib import Path

from core import import_staging
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


def test_stage_external_import_files_reserves_names_within_same_batch(
    tmp_path: Path,
) -> None:
    docs_dir = tmp_path / "docs_entrada"
    docs_dir.mkdir()
    source_a_dir = tmp_path / "fonte_a"
    source_b_dir = tmp_path / "fonte_b"
    source_a_dir.mkdir()
    source_b_dir.mkdir()
    source_a = source_a_dir / "entrada.xlsx"
    source_b = source_b_dir / "entrada.xlsx"
    source_a.write_text("a", encoding="utf-8")
    source_b.write_text("b", encoding="utf-8")

    staged_files, summary = stage_external_import_files(
        project_root=str(tmp_path),
        source_files=(str(source_a), str(source_b)),
    )

    assert summary["copied"] == 2
    assert staged_files == [
        str(docs_dir / "entrada.xlsx"),
        str(docs_dir / "entrada__1.xlsx"),
    ]
    assert (docs_dir / "entrada.xlsx").read_text(encoding="utf-8") == "a"
    assert (docs_dir / "entrada__1.xlsx").read_text(encoding="utf-8") == "b"


def test_stage_external_import_files_rejects_unsupported_and_invalid_paths(
    tmp_path: Path,
) -> None:
    (tmp_path / "docs_entrada").mkdir()
    source_dir = tmp_path / "fontes"
    source_dir.mkdir()
    txt_file = source_dir / "entrada.txt"
    txt_file.write_text("txt", encoding="utf-8")
    messages: list[str] = []

    staged_files, summary = stage_external_import_files(
        project_root=str(tmp_path),
        source_files=(str(txt_file), "bad\nname.xlsx"),
        output_callback=messages.append,
    )

    assert staged_files == []
    assert summary["copied"] == 0
    assert summary["failed"] == 0
    assert summary["unsupported"] == 2
    assert any("Arquivo nao suportado" in message for message in messages)
    assert any("caracteres invalidos" in message for message in messages)


def test_stage_external_import_files_reports_missing_source_as_failed(
    tmp_path: Path,
) -> None:
    (tmp_path / "docs_entrada").mkdir()
    missing_file = tmp_path / "fontes" / "ausente.xlsx"
    errors: list[str] = []

    staged_files, summary = stage_external_import_files(
        project_root=str(tmp_path),
        source_files=(str(missing_file),),
        error_callback=errors.append,
    )

    assert staged_files == []
    assert summary["copied"] == 0
    assert summary["failed"] == 1
    assert summary["unsupported"] == 0
    assert summary["staged"] == 0
    assert any("Arquivo inexistente" in error for error in errors)


def test_stage_external_import_files_removes_copied_file_when_cancelled(
    tmp_path: Path,
) -> None:
    docs_dir = tmp_path / "docs_entrada"
    docs_dir.mkdir()
    source_dir = tmp_path / "fontes"
    source_dir.mkdir()
    source = source_dir / "cancel.xlsx"
    source.write_text("payload", encoding="utf-8")
    cancel_calls = {"count": 0}

    def should_cancel() -> bool:
        cancel_calls["count"] += 1
        return cancel_calls["count"] >= 3

    staged_files, summary = stage_external_import_files(
        project_root=str(tmp_path),
        source_files=(str(source),),
        should_cancel=should_cancel,
    )

    assert staged_files == []
    assert summary["copied"] == 0
    assert summary["failed"] == 0
    assert summary["unsupported"] == 0
    assert summary["staged"] == 0
    assert not (docs_dir / "cancel.xlsx").exists()


def test_stage_external_import_files_reports_cleanup_failure_after_cancel(
    tmp_path: Path,
    monkeypatch,
) -> None:
    docs_dir = tmp_path / "docs_entrada"
    docs_dir.mkdir()
    source_dir = tmp_path / "fontes"
    source_dir.mkdir()
    source = source_dir / "cancel.xlsx"
    source.write_text("payload", encoding="utf-8")
    cancel_calls = {"count": 0}
    errors: list[str] = []

    def should_cancel() -> bool:
        cancel_calls["count"] += 1
        return cancel_calls["count"] >= 3

    def fail_remove(path: str) -> None:
        raise PermissionError(f"locked: {path}")

    monkeypatch.setattr(import_staging.os, "remove", fail_remove)

    staged_files, summary = stage_external_import_files(
        project_root=str(tmp_path),
        source_files=(str(source),),
        should_cancel=should_cancel,
        error_callback=errors.append,
    )

    assert staged_files == []
    assert summary["copied"] == 0
    assert summary["failed"] == 1
    assert summary["staged"] == 0
    assert (docs_dir / "cancel.xlsx").exists()
    assert any("Falha ao remover arquivo staged apos cancelamento" in error for error in errors)
