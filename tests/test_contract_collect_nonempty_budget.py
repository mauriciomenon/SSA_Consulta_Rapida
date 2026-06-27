"""Contract tests for collect_nonempty_column_values tolist budget."""

from __future__ import annotations

from unittest.mock import patch

import pandas as pd

from gui.ssa.filter_domain_rules import collect_nonempty_column_values
from tests._helpers.contract_data_builders import (
    build_base_filter_df,
    make_series_tolist_spy,
)


def test_collect_nonempty_calls_tolist_once_per_column():
    df = build_base_filter_df()
    tolist_calls, spy_tolist = make_series_tolist_spy()

    with patch.object(pd.Series, "tolist", spy_tolist):
        values = collect_nonempty_column_values(df, "setor_executor")

    assert values == ["IEE3", "OURO", "MEL4", "XYZ", "IEE2"]
    assert tolist_calls["count"] == 1


def test_collect_nonempty_skips_tolist_for_missing_column():
    df = build_base_filter_df()
    tolist_calls, spy_tolist = make_series_tolist_spy()

    with patch.object(pd.Series, "tolist", spy_tolist):
        values = collect_nonempty_column_values(df, "missing_column")

    assert values == []
    assert tolist_calls["count"] == 0


def test_collect_nonempty_dedupes_empty_strings_without_extra_tolist():
    df = pd.DataFrame({"situacao": ["APV", "", "  ", None, "STE"]})
    tolist_calls, spy_tolist = make_series_tolist_spy()

    with patch.object(pd.Series, "tolist", spy_tolist):
        values = collect_nonempty_column_values(df, "situacao")

    assert values == ["APV", "STE"]
    assert tolist_calls["count"] == 1


def test_collect_nonempty_unique_budget_at_10k_rows():
    df = pd.DataFrame({"setor_executor": [f"SEC{i:04d}" for i in range(10_000)]})
    tolist_calls, spy_tolist = make_series_tolist_spy()

    with patch.object(pd.Series, "tolist", spy_tolist):
        values = collect_nonempty_column_values(df, "setor_executor")

    assert len(values) == 10_000
    assert len(set(values)) == 10_000
    assert tolist_calls["count"] == 1


def test_collect_nonempty_returns_empty_for_empty_dataframe():
    df = pd.DataFrame({"setor_executor": pd.Series([], dtype=str)})
    tolist_calls, spy_tolist = make_series_tolist_spy()

    with patch.object(pd.Series, "tolist", spy_tolist):
        values = collect_nonempty_column_values(df, "setor_executor")

    assert values == []
    assert tolist_calls["count"] == 0
