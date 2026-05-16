"""Column filter runtime state and dataframe adapter."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

import pandas as pd

from gui.ssa.column_filter_engine import (
    ColumnFilterCaches,
    OrFilterGroup,
    apply_column_filters,
    get_column_filter_date_display_series,
    should_match_date_display_filter,
)


@dataclass
class ColumnFilterRuntimeState:
    caches: ColumnFilterCaches


def is_column_filter_date_display_column(
    column_name: str, df: pd.DataFrame | None = None
) -> bool:
    col_lower = str(column_name or "").casefold()
    if "data" in col_lower or "date" in col_lower or col_lower.startswith("dt_"):
        return True
    if df is not None and column_name in df:
        return bool(pd.api.types.is_datetime64_any_dtype(df[column_name]))
    return False


def get_column_filter_date_display_columns(df: pd.DataFrame) -> frozenset[str]:
    if df is None or df.empty:
        return frozenset()
    date_columns: set[str] = set()
    for col in df.columns:
        column_name = str(col)
        if is_column_filter_date_display_column(column_name, df):
            date_columns.add(column_name)
    return frozenset(date_columns)


def should_match_date_filter(
    column_name: str, raw_filter: str, df: pd.DataFrame | None = None
) -> bool:
    return should_match_date_display_filter(
        raw_filter,
        is_date_column=is_column_filter_date_display_column(column_name, df),
    )


def get_date_display_series(
    state: ColumnFilterRuntimeState,
    df: pd.DataFrame,
    column_name: str,
    *,
    revision: int,
) -> pd.Series | None:
    return get_column_filter_date_display_series(
        df,
        column_name,
        revision=revision,
        caches=state.caches,
    )


def apply_column_filters_with_state(
    state: ColumnFilterRuntimeState,
    df: pd.DataFrame,
    active_column_filters: dict,
    column_to_or_group: dict[str, OrFilterGroup],
    *,
    revision: int,
    build_column_mask: Callable[..., pd.Series],
) -> pd.DataFrame:
    return apply_column_filters(
        df,
        active_column_filters,
        column_to_or_group,
        revision=revision,
        caches=state.caches,
        build_column_mask=build_column_mask,
        date_display_columns=get_column_filter_date_display_columns(df),
    )
