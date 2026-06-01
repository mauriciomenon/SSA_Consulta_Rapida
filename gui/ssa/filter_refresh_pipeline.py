"""Post-search filter refresh pipeline for the SSA GUI."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

import pandas as pd

from gui.ssa.filter_domain_rules import exclude_terminal_status_rows


@dataclass(frozen=True)
class FilterRefreshLastResult:
    key: tuple
    has_post_search_filters: bool
    has_excluded_terminal_status: bool
    dataframe: pd.DataFrame


def apply_filter_refresh_pipeline(
    filtered: pd.DataFrame,
    *,
    has_post_search_filters: bool,
    has_excluded_terminal_status: bool,
    cache_key: tuple | None,
    cached: FilterRefreshLastResult | None,
    apply_advanced_filters: Callable[[pd.DataFrame], pd.DataFrame] | None,
    apply_column_filters: Callable[[pd.DataFrame], pd.DataFrame],
    measure_timing: Callable[[str, Callable[[], pd.DataFrame]], pd.DataFrame],
    logger: Any,
) -> tuple[pd.DataFrame, FilterRefreshLastResult | None]:
    cached_result = _get_cached_refresh_result(
        cached,
        cache_key=cache_key,
        has_post_search_filters=has_post_search_filters,
        has_excluded_terminal_status=has_excluded_terminal_status,
    )
    if cached_result is not None:
        return cached_result.dataframe, cached_result
    if has_post_search_filters:
        filtered = _apply_post_search_stages(
            filtered,
            apply_advanced_filters=apply_advanced_filters,
            apply_column_filters=apply_column_filters,
            measure_timing=measure_timing,
            logger=logger,
        )
    filtered = _apply_terminal_status_stage(
        filtered,
        has_post_search_filters=has_post_search_filters,
        has_excluded_terminal_status=has_excluded_terminal_status,
        measure_timing=measure_timing,
        logger=logger,
    )
    if (
        has_post_search_filters or has_excluded_terminal_status
    ) and cache_key is not None:
        return filtered, FilterRefreshLastResult(
            cache_key,
            has_post_search_filters,
            has_excluded_terminal_status,
            filtered,
        )
    return filtered, None


def _get_cached_refresh_result(
    cached: FilterRefreshLastResult | None,
    *,
    cache_key: tuple | None,
    has_post_search_filters: bool,
    has_excluded_terminal_status: bool,
) -> FilterRefreshLastResult | None:
    if cache_key is None:
        return None
    if (
        isinstance(cached, FilterRefreshLastResult)
        and cached.key == cache_key
        and cached.has_post_search_filters == has_post_search_filters
        and cached.has_excluded_terminal_status == has_excluded_terminal_status
        and isinstance(cached.dataframe, pd.DataFrame)
    ):
        return cached
    return None


def _apply_post_search_stages(
    filtered: pd.DataFrame,
    *,
    apply_advanced_filters: Callable[[pd.DataFrame], pd.DataFrame] | None,
    apply_column_filters: Callable[[pd.DataFrame], pd.DataFrame],
    measure_timing: Callable[[str, Callable[[], pd.DataFrame]], pd.DataFrame],
    logger: Any,
) -> pd.DataFrame:
    if callable(apply_advanced_filters):
        filtered = measure_timing("advanced", lambda: apply_advanced_filters(filtered))
    filtered = measure_timing("column", lambda: apply_column_filters(filtered))
    return filtered


def _apply_terminal_status_stage(
    filtered: pd.DataFrame,
    *,
    has_post_search_filters: bool,
    has_excluded_terminal_status: bool,
    measure_timing: Callable[[str, Callable[[], pd.DataFrame]], pd.DataFrame],
    logger: Any,
) -> pd.DataFrame:
    if (
        has_excluded_terminal_status
        and not filtered.empty
        and "situacao" in filtered.columns
    ):
        filtered = measure_timing(
            "exclude",
            lambda: exclude_terminal_status_rows(filtered),
        )
    return filtered
