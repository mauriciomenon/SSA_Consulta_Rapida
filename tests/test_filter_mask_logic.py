from __future__ import annotations

import pandas as pd

from gui.ssa.filter_mask_logic import build_column_mask


def test_build_column_mask_combines_plain_include_and_exclude_tokens():
    series = pd.Series(["alpha", "beta", "gamma", "alphabet"])

    mask = build_column_mask(series, "alpha,!alphabet", default_mode="contains")

    assert series[mask].tolist() == ["alpha"]


def test_build_column_mask_handles_null_operator():
    series = pd.Series(["", None, "-", "value"])

    mask = build_column_mask(series, "NULL", default_mode="contains")

    selected = series[mask]
    assert selected.index.tolist() == [0, 1, 2]
    assert selected.isna().tolist() == [False, True, False]
