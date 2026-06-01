from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Any, cast

import pytest

from utils.path_safety import PathSafetyError, ensure_path_is_allowed, reserve_unique_path


@pytest.mark.parametrize("value", ["", "   ", b"", b"   "])
def test_ensure_path_is_allowed_rejects_empty_text(value: str) -> None:
    with pytest.raises(PathSafetyError, match="caminho vazio nao permitido"):
        ensure_path_is_allowed(value)


def test_ensure_path_is_allowed_accepts_bytes_path() -> None:
    raw = tempfile.gettempdir().encode()
    result = ensure_path_is_allowed(cast(Any, raw))
    assert result == Path(tempfile.gettempdir()).resolve()


def test_ensure_path_is_allowed_accepts_explicit_extra_root(tmp_path: Path) -> None:
    external_root = tmp_path / "external"
    external_root.mkdir()
    external_file = external_root / "planilha.xlsx"
    external_file.write_text("ok", encoding="utf-8")

    result = ensure_path_is_allowed(
        external_file,
        purpose="explicit_import_source",
        must_exist=True,
        expect_directory=False,
        extra_allowed_roots=[external_root],
    )

    assert result == external_file.resolve()


def test_ensure_path_is_allowed_uses_extra_roots_set_after_import(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    external_root = tmp_path / "runtime"
    external_root.mkdir()
    external_file = external_root / "ssas.db"
    external_file.write_text("ok", encoding="utf-8")
    monkeypatch.setenv("SSA_EXTRA_ALLOWED_PATHS", str(external_root))

    result = ensure_path_is_allowed(
        external_file,
        purpose="runtime_db",
        must_exist=True,
        expect_directory=False,
    )

    assert result == external_file.resolve()


def test_reserve_unique_path_with_reserved_set_and_touch_reserves_on_disk(
    tmp_path: Path,
) -> None:
    target = tmp_path / "entrada.xlsx"
    reserved_paths: set[str] = set()

    result = reserve_unique_path(target, reserved_paths=reserved_paths, touch=True)

    assert result == str(target)
    assert target.exists()
    assert str(target.resolve()) in reserved_paths


def test_reserve_unique_path_with_reserved_set_and_touch_reserves_next_candidate(
    tmp_path: Path,
) -> None:
    target = tmp_path / "entrada.xlsx"
    target.write_text("old", encoding="utf-8")
    reserved_paths = {str(target.resolve())}
    expected = tmp_path / "entrada__1.xlsx"

    result = reserve_unique_path(target, reserved_paths=reserved_paths, touch=True)

    assert result == str(expected)
    assert expected.exists()
    assert str(expected.resolve()) in reserved_paths
