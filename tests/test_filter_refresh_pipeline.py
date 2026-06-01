from __future__ import annotations

import pandas as pd
import pytest

from gui.ssa.filter_refresh_pipeline import apply_filter_refresh_pipeline


class _Logger:
    def warning(self, *_args, **_kwargs):
        raise AssertionError("pipeline must not suppress filter errors")


def _measure(_name, callback):
    return callback()


def test_filter_refresh_pipeline_propagates_advanced_filter_error():
    df = pd.DataFrame({"situacao": ["APV"]})

    def _raise(_df):
        raise RuntimeError("advanced filter failed")

    with pytest.raises(RuntimeError, match="advanced filter failed"):
        apply_filter_refresh_pipeline(
            df,
            has_post_search_filters=True,
            has_excluded_terminal_status=False,
            cache_key=None,
            cached=None,
            apply_advanced_filters=_raise,
            apply_column_filters=lambda frame: frame,
            measure_timing=_measure,
            logger=_Logger(),
        )


def test_filter_refresh_pipeline_applies_column_filter_normally():
    df = pd.DataFrame({"situacao": ["APV", "STE"]})

    filtered, cache_update = apply_filter_refresh_pipeline(
        df,
        has_post_search_filters=True,
        has_excluded_terminal_status=False,
        cache_key=("revision", 1),
        cached=None,
        apply_advanced_filters=None,
        apply_column_filters=lambda frame: frame[frame["situacao"].eq("APV")],
        measure_timing=_measure,
        logger=_Logger(),
    )

    assert filtered["situacao"].tolist() == ["APV"]
    assert cache_update is not None


def test_filter_refresh_pipeline_applies_terminal_exclusion_without_post_filters():
    df = pd.DataFrame({"situacao": ["APV", "STE", "SCA", "SES"]})

    filtered, cache_update = apply_filter_refresh_pipeline(
        df,
        has_post_search_filters=False,
        has_excluded_terminal_status=True,
        cache_key=("revision", "terminal-only"),
        cached=None,
        apply_advanced_filters=None,
        apply_column_filters=lambda frame: frame,
        measure_timing=_measure,
        logger=_Logger(),
    )

    assert filtered["situacao"].tolist() == ["APV"]
    assert cache_update is not None
