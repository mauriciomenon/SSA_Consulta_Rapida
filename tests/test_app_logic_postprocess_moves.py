from __future__ import annotations

import errno
import os
from pathlib import Path

from core import import_postprocess
from core.app_logic import _apply_postprocess_file_moves
from core.import_postprocess import move_file_after_import


def test_apply_postprocess_file_moves_routes_regular_and_nosurvivor(
    tmp_path: Path,
) -> None:
    docs_dir = tmp_path / "docs_entrada"
    docs_dir.mkdir()
    regular = docs_dir / "ok.xlsx"
    zero_rows = docs_dir / "empty.xlsx"
    regular.write_text("ok", encoding="utf-8")
    zero_rows.write_text("empty", encoding="utf-8")

    moved = _apply_postprocess_file_moves(
        successful_files_with_records=[
            (str(regular), 10),
            (str(zero_rows), 0),
        ],
        docs_dir=str(docs_dir),
        processadas_subdir="processadas",
        nosurvivor_subdir="nosurvivor",
        route_zero_survivor_to_nosurvivor=True,
    )

    regular_dest = Path(moved[str(regular)])
    zero_dest = Path(moved[str(zero_rows)])

    assert regular_dest.exists()
    assert regular_dest.parent == docs_dir / "processadas"
    assert regular_dest.name == "ok.xlsx"

    assert zero_dest.exists()
    assert zero_dest.parent == docs_dir / "processadas" / "nosurvivor"
    assert zero_dest.name == "empty.xlsx"

    assert not regular.exists()
    assert not zero_rows.exists()


def test_apply_postprocess_file_moves_keeps_zero_rows_in_processadas_when_disabled(
    tmp_path: Path,
) -> None:
    docs_dir = tmp_path / "docs_entrada"
    docs_dir.mkdir()
    zero_rows = docs_dir / "empty.xlsx"
    zero_rows.write_text("empty", encoding="utf-8")

    moved = _apply_postprocess_file_moves(
        successful_files_with_records=[(str(zero_rows), 0)],
        docs_dir=str(docs_dir),
        processadas_subdir="processadas",
        nosurvivor_subdir="nosurvivor",
        route_zero_survivor_to_nosurvivor=False,
    )

    destination = Path(moved[str(zero_rows)])
    assert destination.exists()
    assert destination.parent == docs_dir / "processadas"
    assert destination.name == "empty.xlsx"
    assert not zero_rows.exists()


def test_apply_postprocess_file_moves_rejects_destination_escape(
    tmp_path: Path,
) -> None:
    docs_dir = tmp_path / "docs_entrada"
    docs_dir.mkdir()
    source = docs_dir / "escape.xlsx"
    source.write_text("keep", encoding="utf-8")

    moved = _apply_postprocess_file_moves(
        successful_files_with_records=[(str(source), 1)],
        docs_dir=str(docs_dir),
        processadas_subdir="../escaped",
        nosurvivor_subdir="nosurvivor",
        route_zero_survivor_to_nosurvivor=False,
    )

    assert moved[str(source)] == str(source)
    assert source.exists()
    assert not (tmp_path / "escaped").exists()


def test_apply_postprocess_file_moves_does_not_overwrite_collision(
    tmp_path: Path,
) -> None:
    docs_dir = tmp_path / "docs_entrada"
    processadas = docs_dir / "processadas"
    processadas.mkdir(parents=True)
    source = docs_dir / "same.xlsx"
    destination = processadas / "same.xlsx"
    source.write_text("new", encoding="utf-8")
    destination.write_text("old", encoding="utf-8")

    moved = _apply_postprocess_file_moves(
        successful_files_with_records=[(str(source), 1)],
        docs_dir=str(docs_dir),
        processadas_subdir="processadas",
        nosurvivor_subdir="nosurvivor",
        route_zero_survivor_to_nosurvivor=False,
    )

    final_path = Path(moved[str(source)])
    assert destination.read_text(encoding="utf-8") == "old"
    assert final_path.name == "same__1.xlsx"
    assert final_path.read_text(encoding="utf-8") == "new"
    assert not source.exists()


def test_move_file_after_import_rejects_destination_outside_docs_dir(
    tmp_path: Path,
) -> None:
    docs_dir = tmp_path / "docs_entrada"
    docs_dir.mkdir()
    source = docs_dir / "source.xlsx"
    source.write_text("data", encoding="utf-8")

    result = move_file_after_import(
        file_path=str(source),
        docs_dir=str(docs_dir),
        destination_root=tmp_path / "outside",
    )

    assert result is None
    assert source.exists()


def test_move_file_after_import_copy_fallback_syncs_open_destination_fd(
    tmp_path: Path, monkeypatch
) -> None:
    docs_dir = tmp_path / "docs_entrada"
    destination_root = docs_dir / "processadas"
    docs_dir.mkdir()
    source = docs_dir / "source.xlsx"
    source.write_text("data", encoding="utf-8")

    def _raise_cross_device_link(src, dst):
        raise OSError(errno.EXDEV, "cross-device link")

    def _checked_fsync(fd: int) -> None:
        os.fstat(fd)

    monkeypatch.setattr(import_postprocess.os, "link", _raise_cross_device_link)
    monkeypatch.setattr(import_postprocess.os, "fsync", _checked_fsync)

    result = move_file_after_import(
        file_path=str(source),
        docs_dir=str(docs_dir),
        destination_root=destination_root,
    )

    assert result == str((destination_root / "source.xlsx").resolve())
    assert not source.exists()
    assert (destination_root / "source.xlsx").read_text(encoding="utf-8") == "data"


def test_move_file_after_import_retries_distinct_names_after_runtime_collision(
    tmp_path: Path, monkeypatch
) -> None:
    docs_dir = tmp_path / "docs_entrada"
    destination_root = docs_dir / "processadas"
    docs_dir.mkdir()
    source = docs_dir / "same.xlsx"
    source.write_text("new", encoding="utf-8")
    attempted: list[str] = []
    real_move = import_postprocess._move_without_overwrite

    def _collide_once(src: Path, dst: Path) -> None:
        attempted.append(dst.name)
        if len(attempted) == 1:
            raise FileExistsError(dst)
        real_move(src, dst)

    monkeypatch.setattr(import_postprocess, "_move_without_overwrite", _collide_once)

    result = move_file_after_import(
        file_path=str(source),
        docs_dir=str(docs_dir),
        destination_root=destination_root,
    )

    assert attempted == ["same.xlsx", "same__1.xlsx"]
    assert result == str((destination_root / "same__1.xlsx").resolve())
    assert not source.exists()
