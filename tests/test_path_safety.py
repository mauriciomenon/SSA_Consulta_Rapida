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
