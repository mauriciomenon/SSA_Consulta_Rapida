"""Contract tests for discarded work in the filter refresh pipeline."""

from __future__ import annotations

from unittest.mock import MagicMock

import pandas as pd

from gui.ssa.filter_refresh_pipeline import (
    FilterRefreshLastResult,
    apply_filter_refresh_pipeline,
)


def test_pipeline_cache_hit_skips_heavy_post_search_stages():
    df = pd.DataFrame({"situacao": ["APV", "STE", "SCA"]})
    stage_calls: list[str] = []

    def _measure(name: str, callback):
        stage_calls.append(name)
        return callback()

    def _advanced(frame: pd.DataFrame) -> pd.DataFrame:
        stage_calls.append("advanced_body")
        return frame[frame["situacao"].eq("APV")]

    def _column(frame: pd.DataFrame) -> pd.DataFrame:
        stage_calls.append("column_body")
        return frame

    advanced_spy = MagicMock(side_effect=_advanced)
    column_spy = MagicMock(side_effect=_column)
    measure_spy = MagicMock(side_effect=_measure)

    cache_key = ("revision", "pipeline-waste")
    filtered, cached = apply_filter_refresh_pipeline(
        df,
        has_post_search_filters=True,
        has_excluded_terminal_status=False,
        cache_key=cache_key,
        cached=None,
        apply_advanced_filters=advanced_spy,
        apply_column_filters=column_spy,
        measure_timing=measure_spy,
    )
    assert filtered["situacao"].tolist() == ["APV"]
    assert cached is not None
    assert advanced_spy.call_count == 1
    assert column_spy.call_count == 1
    assert measure_spy.call_count == 2
    first_pass_stages = list(stage_calls)
    assert "advanced" in first_pass_stages
    assert "column" in first_pass_stages
    assert "exclude" not in first_pass_stages

    stage_calls.clear()
    advanced_spy.reset_mock()
    column_spy.reset_mock()
    measure_spy.reset_mock()
    second_filtered, second_cached = apply_filter_refresh_pipeline(
        df,
        has_post_search_filters=True,
        has_excluded_terminal_status=False,
        cache_key=cache_key,
        cached=cached,
        apply_advanced_filters=advanced_spy,
        apply_column_filters=column_spy,
        measure_timing=measure_spy,
    )

    assert second_cached is cached
    assert second_filtered["situacao"].tolist() == ["APV"]
    assert second_filtered is not filtered
    assert advanced_spy.call_count == 0
    assert column_spy.call_count == 0
    assert measure_spy.call_count == 0
    assert stage_calls == []


def test_pipeline_cache_hit_still_applies_terminal_stage_when_needed():
    df = pd.DataFrame({"situacao": ["APV", "STE", "SCA", "SES"]})
    stage_calls: list[str] = []

    def _measure(name: str, callback):
        stage_calls.append(name)
        return callback()

    advanced_spy = MagicMock()
    column_spy = MagicMock(side_effect=lambda frame: frame)
    measure_spy = MagicMock(side_effect=_measure)

    cache_key = ("revision", "terminal-cache-waste")
    cached = FilterRefreshLastResult(
        cache_key,
        False,
        False,
        df.copy(deep=True),
    )
    filtered, _update = apply_filter_refresh_pipeline(
        df,
        has_post_search_filters=False,
        has_excluded_terminal_status=True,
        cache_key=cache_key,
        cached=cached,
        apply_advanced_filters=advanced_spy,
        apply_column_filters=column_spy,
        measure_timing=measure_spy,
    )

    assert advanced_spy.call_count == 0
    assert column_spy.call_count == 0
    assert measure_spy.call_count == 1
    assert "exclude" in stage_calls
    assert "advanced" not in stage_calls
    assert "column" not in stage_calls
    assert filtered["situacao"].tolist() == ["APV"]
