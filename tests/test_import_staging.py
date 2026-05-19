from __future__ import annotations

import builtins
import os
from pathlib import Path
from typing import Iterable

import pytest

from core import import_staging
from core.import_staging import stage_external_import_files
from utils import path_safety


def test_stage_external_import_files_accepts_only_backend_supported_formats(
    tmp_path: Path,
) -> None:
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

    assert summary["copied"] == 1
    assert summary["failed"] == 0
    assert summary["unsupported"] == 1
    assert len(staged_files) == 1
    assert (docs_dir / "entrada.xlsx").exists()
    assert not (docs_dir / "entrada.xls").exists()


def test_validate_external_source_path_accepts_explicit_selected_file(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runtime_root = tmp_path / "runtime"
    runtime_root.mkdir()
    outside_root = tmp_path / "outside"
    outside_root.mkdir()
    source = outside_root / "entrada.xlsx"
    source.write_text("payload", encoding="utf-8")
    monkeypatch.setattr(path_safety, "ALLOWED_ROOTS", [runtime_root])

    with pytest.raises(ValueError):
        import_staging.validate_external_source_path(source)

    resolved = import_staging.validate_external_source_path(
        source,
        extra_allowed_files=(source,),
    )

    assert resolved == str(source.resolve())


def test_validate_external_source_path_ignores_missing_extra_allowed_files(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runtime_root = tmp_path / "runtime"
    runtime_root.mkdir()
    outside_root = tmp_path / "outside"
    outside_root.mkdir()
    source = outside_root / "entrada.xlsx"
    source.write_text("payload", encoding="utf-8")
    missing_source = outside_root / "ausente.xlsx"
    monkeypatch.setattr(path_safety, "ALLOWED_ROOTS", [runtime_root])

    resolved = import_staging.validate_external_source_path(
        source,
        extra_allowed_files=(missing_source, source),
    )

    assert resolved == str(source.resolve())


def test_validate_external_source_path_rejects_explicit_directory(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runtime_root = tmp_path / "runtime"
    runtime_root.mkdir()
    outside_root = tmp_path / "outside"
    outside_root.mkdir()
    monkeypatch.setattr(path_safety, "ALLOWED_ROOTS", [runtime_root])

    with pytest.raises(ValueError):
        import_staging.validate_external_source_path(
            outside_root,
            extra_allowed_files=(outside_root,),
        )


def test_stage_external_import_files_accepts_explicit_external_source(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runtime_root = tmp_path / "runtime"
    docs_dir = runtime_root / "docs_entrada"
    docs_dir.mkdir(parents=True)
    outside_root = tmp_path / "outside"
    outside_root.mkdir()
    source = outside_root / "entrada.xlsx"
    source.write_text("payload", encoding="utf-8")
    monkeypatch.setattr(path_safety, "ALLOWED_ROOTS", [runtime_root])

    staged_files, summary = stage_external_import_files(
        project_root=str(runtime_root),
        source_files=(str(source),),
    )

    assert summary["copied"] == 1
    assert summary["failed"] == 0
    assert summary["unsupported"] == 0
    assert staged_files == [str(docs_dir / "entrada.xlsx")]
    assert (docs_dir / "entrada.xlsx").read_text(encoding="utf-8") == "payload"


def test_stage_external_import_files_normalizes_explicit_allowlist_once(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runtime_root = tmp_path / "runtime"
    docs_dir = runtime_root / "docs_entrada"
    docs_dir.mkdir(parents=True)
    outside_root = tmp_path / "outside"
    outside_root.mkdir()
    source_a = outside_root / "entrada_a.xlsx"
    source_b = outside_root / "entrada_b.xlsx"
    source_a.write_text("a", encoding="utf-8")
    source_b.write_text("b", encoding="utf-8")
    monkeypatch.setattr(path_safety, "ALLOWED_ROOTS", [runtime_root])
    original_normalize = import_staging._normalize_explicit_allowed_files
    call_count = 0

    def counting_normalize(
        extra_allowed_files: Iterable[str | os.PathLike[str]] | None,
    ) -> set[Path]:
        nonlocal call_count
        call_count += 1
        return original_normalize(extra_allowed_files)

    monkeypatch.setattr(
        import_staging,
        "_normalize_explicit_allowed_files",
        counting_normalize,
    )

    staged_files, summary = stage_external_import_files(
        project_root=str(runtime_root),
        source_files=(str(source_a), str(source_b)),
    )

    assert call_count == 1
    assert summary["copied"] == 2
    assert staged_files == [
        str(docs_dir / "entrada_a.xlsx"),
        str(docs_dir / "entrada_b.xlsx"),
    ]


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


@pytest.mark.parametrize("raw_source", ["", "   ", "-entrada.xlsx", "bad\x00name.xlsx"])
def test_validate_external_source_path_rejects_unsafe_text(raw_source: str) -> None:
    with pytest.raises(ValueError):
        import_staging.validate_external_source_path(raw_source)


def test_stage_external_import_files_keeps_file_already_in_docs_dir(
    tmp_path: Path,
) -> None:
    docs_dir = tmp_path / "docs_entrada"
    docs_dir.mkdir()
    source = docs_dir / "entrada.xlsx"
    source.write_text("payload", encoding="utf-8")

    staged_files, summary = stage_external_import_files(
        project_root=str(tmp_path),
        source_files=(str(source),),
    )

    assert staged_files == [str(source)]
    assert summary["copied"] == 0
    assert summary["failed"] == 0
    assert summary["unsupported"] == 0
    assert summary["staged"] == 1
    assert source.read_text(encoding="utf-8") == "payload"


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


def test_stage_external_import_files_reports_copy_os_errors(
    tmp_path: Path,
    monkeypatch,
) -> None:
    docs_dir = tmp_path / "docs_entrada"
    docs_dir.mkdir()
    source_dir = tmp_path / "fontes"
    source_dir.mkdir()
    source = source_dir / "falha.xlsx"
    source.write_text("payload", encoding="utf-8")
    errors: list[str] = []
    original_open = builtins.open

    def fail_open(path, mode="r", *args, **kwargs):  # noqa: ANN001,ANN002,ANN003
        if Path(path) == source and mode == "rb":
            raise PermissionError("blocked copy")
        return original_open(path, mode, *args, **kwargs)

    monkeypatch.setattr("utils.file_copy.open", fail_open, raising=False)

    staged_files, summary = stage_external_import_files(
        project_root=str(tmp_path),
        source_files=(str(source),),
        error_callback=errors.append,
    )

    assert staged_files == []
    assert summary["copied"] == 0
    assert summary["failed"] == 1
    assert summary["unsupported"] == 0
    assert summary["staged"] == 0
    assert any("blocked copy" in error for error in errors)


def test_stage_external_import_files_does_not_delete_file_on_create_collision(
    tmp_path: Path,
    monkeypatch,
) -> None:
    docs_dir = tmp_path / "docs_entrada"
    docs_dir.mkdir()
    source_dir = tmp_path / "fontes"
    source_dir.mkdir()
    source = source_dir / "race.xlsx"
    source.write_text("payload", encoding="utf-8")
    destination = docs_dir / "race.xlsx"
    original_open = builtins.open

    def open_with_create_collision(path, mode="r", *args, **kwargs):  # noqa: ANN001,ANN002,ANN003
        if Path(path) == destination and mode == "xb":
            with original_open(path, "wb") as handle:
                handle.write(b"foreign")
            raise FileExistsError("created by another process")
        return original_open(path, mode, *args, **kwargs)

    monkeypatch.setattr(
        "utils.file_copy.open",
        open_with_create_collision,
        raising=False,
    )

    staged_files, summary = stage_external_import_files(
        project_root=str(tmp_path),
        source_files=(str(source),),
    )

    retry_destination = docs_dir / "race__1.xlsx"
    assert staged_files == [str(retry_destination)]
    assert summary["copied"] == 1
    assert summary["failed"] == 0
    assert source.read_text(encoding="utf-8") == "payload"
    assert destination.read_text(encoding="utf-8") == "foreign"
    assert retry_destination.read_text(encoding="utf-8") == "payload"


def test_stage_external_import_files_copies_opened_file_when_source_path_changes(
    tmp_path: Path,
    monkeypatch,
) -> None:
    if os.name == "nt":
        pytest.skip("os.replace over open file is not supported on Windows")
    docs_dir = tmp_path / "docs_entrada"
    docs_dir.mkdir()
    source_dir = tmp_path / "fontes"
    source_dir.mkdir()
    source = source_dir / "entrada.xlsx"
    source.write_text("original", encoding="utf-8")
    replacement = source_dir / "replacement.xlsx"
    replacement.write_text("swapped", encoding="utf-8")
    original_open = builtins.open
    swapped = {"done": False}

    def open_then_replace(path, mode="r", *args, **kwargs):  # noqa: ANN001,ANN002,ANN003
        handle = original_open(path, mode, *args, **kwargs)
        if Path(path) == source and mode == "rb" and not swapped["done"]:
            import_staging.os.replace(replacement, source)
            swapped["done"] = True
        return handle

    monkeypatch.setattr(
        "utils.file_copy.open",
        open_then_replace,
        raising=False,
    )

    staged_files, summary = stage_external_import_files(
        project_root=str(tmp_path),
        source_files=(str(source),),
    )

    assert summary["copied"] == 1
    assert summary["failed"] == 0
    assert staged_files == [str(docs_dir / "entrada.xlsx")]
    assert (docs_dir / "entrada.xlsx").read_text(encoding="utf-8") == "original"
    assert source.read_text(encoding="utf-8") == "swapped"


def test_reserve_unique_path_in_set_reports_exhausted_attempts(
    tmp_path: Path,
) -> None:
    target = tmp_path / "entrada.xlsx"
    target.write_text("old", encoding="utf-8")
    (tmp_path / "entrada__1.xlsx").write_text("old", encoding="utf-8")
    reserved_paths = {
        str(target.resolve()),
        str((tmp_path / "entrada__1.xlsx").resolve()),
    }

    with pytest.raises(RuntimeError, match="Limpe duplicatas"):
        import_staging.reserve_unique_path(
            target, reserved_paths=reserved_paths, max_attempts=1
        )


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
    assert summary["failed"] == 0
    assert summary["staged"] == 0
    assert (docs_dir / "cancel.xlsx").exists()
    assert (docs_dir / "cancel.xlsx").read_text(encoding="utf-8") == "payload"
    assert any("Falha ao remover arquivo staged apos cancelamento" in error for error in errors)
