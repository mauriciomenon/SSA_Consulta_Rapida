from __future__ import annotations

import pandas as pd
import pytest

from gui.ssa.filter_mask_logic import build_column_mask


@pytest.mark.parametrize("mode", ["contains", "exact", "prefix", "suffix", "regex"])
@pytest.mark.parametrize("raw,expected", [("!alpha", ["beta"]), ("alpha,!alpha", [])])
def test_column_exclusions_apply_in_every_mode(mode, raw, expected):
    series = pd.Series(["alpha", "beta"])

    mask = build_column_mask(series, raw, default_mode=mode)

    assert series[mask].tolist() == expected


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
