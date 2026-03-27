from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Any, cast

import pytest

from utils.path_safety import PathSafetyError, ensure_path_is_allowed


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
