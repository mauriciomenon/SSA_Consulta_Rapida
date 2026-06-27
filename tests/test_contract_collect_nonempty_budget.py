"""Contract tests for collect_nonempty_column_values tolist budget."""

from __future__ import annotations

from unittest.mock import patch

import pandas as pd

from gui.ssa.filter_domain_rules import collect_nonempty_column_values
from tests._helpers.contract_data_builders import build_base_filter_df


def test_collect_nonempty_calls_tolist_once_per_column():
    df = build_base_filter_df()
    tolist_calls = {"count": 0}
    original_tolist = pd.Series.tolist

    def _spy_tolist(self, *args, **kwargs):
        tolist_calls["count"] += 1
        return original_tolist(self, *args, **kwargs)

    with patch.object(pd.Series, "tolist", _spy_tolist):
        values = collect_nonempty_column_values(df, "setor_executor")

    assert values == ["IEE3", "OURO", "MEL4", "XYZ", "IEE2"]
    assert tolist_calls["count"] == 1


def test_collect_nonempty_skips_tolist_for_missing_column():
    df = build_base_filter_df()
    tolist_calls = {"count": 0}
    original_tolist = pd.Series.tolist

    def _spy_tolist(self, *args, **kwargs):
        tolist_calls["count"] += 1
        return original_tolist(self, *args, **kwargs)

    with patch.object(pd.Series, "tolist", _spy_tolist):
        values = collect_nonempty_column_values(df, "missing_column")

    assert values == []
    assert tolist_calls["count"] == 0


def test_collect_nonempty_dedupes_empty_strings_without_extra_tolist():
    df = pd.DataFrame({"situacao": ["APV", "", "  ", None, "STE"]})
    tolist_calls = {"count": 0}
    original_tolist = pd.Series.tolist

    def _spy_tolist(self, *args, **kwargs):
        tolist_calls["count"] += 1
        return original_tolist(self, *args, **kwargs)

    with patch.object(pd.Series, "tolist", _spy_tolist):
        values = collect_nonempty_column_values(df, "situacao")

    assert values == ["APV", "STE"]
    assert tolist_calls["count"] == 1


def test_collect_nonempty_unique_budget_at_10k_rows():
    df = pd.DataFrame({"setor_executor": [f"SEC{i:04d}" for i in range(10_000)]})
    tolist_calls = {"count": 0}
    original_tolist = pd.Series.tolist

    def _spy_tolist(self, *args, **kwargs):
        tolist_calls["count"] += 1
        return original_tolist(self, *args, **kwargs)

    with patch.object(pd.Series, "tolist", _spy_tolist):
        values = collect_nonempty_column_values(df, "setor_executor")

    assert len(values) == 10_000
    assert tolist_calls["count"] == 1
