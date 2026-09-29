"""Contract tests for filter refresh cache deep-copy isolation."""

from __future__ import annotations

import pandas as pd

from gui.ssa.filter_refresh_pipeline import (
    FilterRefreshLastResult,
    apply_filter_refresh_pipeline,
)
from tests._helpers.contract_data_builders import pipeline_measure_timing


def test_cached_refresh_result_is_deep_copied_on_read():
    df = pd.DataFrame({"situacao": ["APV", "STE"]})
    cache_key = ("revision", "deep-copy-read")

    _, cache_update = apply_filter_refresh_pipeline(
        df,
        has_post_search_filters=True,
        has_excluded_terminal_status=False,
        cache_key=cache_key,
        cached=None,
        apply_advanced_filters=None,
        apply_column_filters=lambda frame: frame[frame["situacao"].eq("APV")],
        measure_timing=pipeline_measure_timing,
    )
    assert isinstance(cache_update, FilterRefreshLastResult)

    cached_filtered, _ = apply_filter_refresh_pipeline(
        df,
        has_post_search_filters=True,
        has_excluded_terminal_status=False,
        cache_key=cache_key,
        cached=cache_update,
        apply_advanced_filters=None,
        apply_column_filters=lambda frame: frame.iloc[0:0],
        measure_timing=pipeline_measure_timing,
    )

    cached_filtered.loc[cached_filtered.index[0], "situacao"] = "MUTATED"
    assert cache_update.dataframe["situacao"].tolist() == ["APV"]
    assert cached_filtered["situacao"].tolist() == ["MUTATED"]


def test_cached_refresh_store_uses_deep_copy():
    df = pd.DataFrame({"situacao": ["APV", "STE"]})
    cache_key = ("revision", "deep-copy-store")

    filtered, cache_update = apply_filter_refresh_pipeline(
        df,
        has_post_search_filters=True,
        has_excluded_terminal_status=False,
        cache_key=cache_key,
        cached=None,
        apply_advanced_filters=None,
        apply_column_filters=lambda frame: frame[frame["situacao"].eq("APV")],
        measure_timing=pipeline_measure_timing,
    )

    filtered.loc[filtered.index[0], "situacao"] = "MUTATED"
    assert cache_update is not None
    assert cache_update.dataframe["situacao"].tolist() == ["APV"]
