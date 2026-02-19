from __future__ import annotations

import pytest

from utils.path_safety import PathSafetyError, ensure_path_is_allowed


@pytest.mark.parametrize("value", ["", "   "])
def test_ensure_path_is_allowed_rejects_empty_text(value: str) -> None:
    with pytest.raises(PathSafetyError, match="caminho vazio nao permitido"):
        ensure_path_is_allowed(value)
