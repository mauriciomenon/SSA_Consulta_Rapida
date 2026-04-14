import pandas as pd
import pytest

pytest.importorskip(
    "PyQt6", reason="Dependencia PyQt6 indisponivel no ambiente de teste"
)

from gui.mixins.filter_gui_ssa_mixin import FilterGUISSAMixin


class _DummyFilterWindow(FilterGUISSAMixin):
    def __init__(self, mode: str) -> None:
        self._cached_default_mode = mode


def test_build_column_mask_invalid_explicit_regex_falls_back_to_literal():
    win = _DummyFilterWindow("contains")
    series = pd.Series(["abc[", "safe"], dtype="object")

    mask = win._build_column_mask(series, "~abc[")

    assert mask.tolist() == [True, False]


def test_build_column_mask_invalid_default_regex_falls_back_to_literal():
    win = _DummyFilterWindow("regex")
    series = pd.Series(["abc[", "safe"], dtype="object")

    mask = win._build_column_mask(series, "abc[")

    assert mask.tolist() == [True, False]


def test_build_column_mask_default_contains_treats_regex_metacharacters_as_literal():
    win = _DummyFilterWindow("contains")
    series = pd.Series(["a.b", "acb", "safe"], dtype="object")

    mask = win._build_column_mask(series, "a.b")

    assert mask.tolist() == [True, False, False]
