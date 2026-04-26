from __future__ import annotations

from pathlib import Path

from core.app_logic import _apply_postprocess_file_moves


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
