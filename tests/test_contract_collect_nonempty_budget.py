"""Contract tests for collect_nonempty_column_values tolist budget."""

from __future__ import annotations

from unittest.mock import patch

import pandas as pd

from gui.ssa.filter_domain_rules import collect_nonempty_column_values
from tests._helpers.contract_data_builders import (
    EXPECTED_BASE_EXECUTORS,
    build_base_filter_df,
    make_series_tolist_spy,
)


def test_collect_nonempty_calls_tolist_once_per_column():
    df = build_base_filter_df()
    tolist_calls, spy_tolist = make_series_tolist_spy()

    with patch.object(pd.Series, "tolist", spy_tolist):
        values = collect_nonempty_column_values(df, "setor_executor")

    assert values == EXPECTED_BASE_EXECUTORS
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
    assert values[0] == "SEC0000"
    assert values[-1] == "SEC9999"
    assert tolist_calls["count"] == 1


def test_unique_sorted_matches_collect_nonempty_set_casefold_baseline():
    """M2: pd.unique path must match collect_nonempty + set + casefold sort."""
    from gui.ssa.gui_filters_advanced_refresh import _unique_sorted

    df = pd.DataFrame(
        {
            "situacao": ["APV", "STE", "APV", "", "  ", None, "STE", "Zeta", "alpha"],
            "setor_executor": [
                "IEE3",
                "IEE3",
                "SMIN",
                "SMIN",
                "",
                "X",
                "Y",
                "Y",
                None,
            ],
        }
    )

    def baseline(column: str) -> list[str]:
        raw = collect_nonempty_column_values(df, column)
        return sorted(set(raw), key=lambda value: value.casefold())

    for column in ("situacao", "setor_executor"):
        assert _unique_sorted(df, column) == baseline(column)


def test_collect_nonempty_returns_empty_for_empty_dataframe():
    df = pd.DataFrame({"setor_executor": pd.Series([], dtype=str)})
    tolist_calls, spy_tolist = make_series_tolist_spy()

    with patch.object(pd.Series, "tolist", spy_tolist):
        values = collect_nonempty_column_values(df, "setor_executor")

    assert values == []
    assert tolist_calls["count"] == 0
