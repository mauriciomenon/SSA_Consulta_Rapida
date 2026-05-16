"""Column filter dataframe operations for the SSA GUI."""

from __future__ import annotations

from dataclasses import dataclass, field
import re
from typing import Callable, TypedDict
import weakref
from uuid import uuid4

import numpy as np
import pandas as pd

from shared.date_utils import parse_datetime_series_mixed


_DATE_FILTER_PATTERN_RE = re.compile(
    r"(?:\d{1,2}[/-]\d{1,2}(?:[/-]\d{2,4})?|\d{4}[/-]\d{1,2}(?:[/-]\d{1,2})?)"
)


@dataclass
class ColumnFilterCaches:
    revision: int | None
    series: dict
    casefold: dict
    mask: dict
    date_scope: tuple[int, str] | None
    date_parsed: dict
    date: dict
    frame_tokens: dict[int, tuple[weakref.ReferenceType[pd.DataFrame], str]] = field(
        default_factory=dict
    )
    date_filter_terms: dict[tuple[str, bool], bool] = field(default_factory=dict)
    max_entries: int = 96


class OrFilterGroup(TypedDict, total=False):
    columns: list[str]
    values: list[str]


def _dataframe_cache_key(
    df: pd.DataFrame,
    revision: int,
    caches: ColumnFilterCaches,
) -> tuple[int, str]:
    df_id = id(df)
    cached = caches.frame_tokens.get(df_id)
    if cached is not None:
        cached_ref, cached_token = cached
        if cached_ref() is df:
            return revision, cached_token
    token = uuid4().hex
    caches.frame_tokens[df_id] = (weakref.ref(df), token)
    _trim_cache_dict(caches.frame_tokens, caches.max_entries)
    return revision, token


def should_match_date_display_filter(raw_filter: str, *, is_date_column: bool) -> bool:
    if not is_date_column:
        return False
    return bool(_DATE_FILTER_PATTERN_RE.search(str(raw_filter or "")))


def get_column_filter_date_display_series(
    df: pd.DataFrame,
    col: str,
    *,
    revision: int,
    caches: ColumnFilterCaches,
) -> pd.Series | None:
    if df is None or col not in df.columns:
        return None
    next_scope = _dataframe_cache_key(df, revision, caches)
    if caches.date_scope != next_scope:
        caches.date_scope = next_scope
        caches.date_parsed = {}
        caches.date = {}
    cached = caches.date.get(col)
    if isinstance(cached, pd.Series):
        return cached
    parsed_dates = parse_datetime_series_mixed(df[col])
    caches.date_parsed[col] = parsed_dates
    display_dates = parsed_dates.dt.strftime("%d/%m/%Y").fillna("").astype(str)
    caches.date[col] = display_dates
    _trim_date_caches(caches)
    return display_dates


def apply_column_filters(
    df: pd.DataFrame,
    active_column_filters: dict,
    column_to_or_group: dict[str, OrFilterGroup],
    *,
    revision: int,
    caches: ColumnFilterCaches,
    build_column_mask: Callable[..., pd.Series],
    date_display_columns: set[str] | frozenset[str] | None = None,
) -> pd.DataFrame:
    if df is None or df.empty or not active_column_filters:
        return df
    if caches.revision != revision:
        caches.revision = revision
        caches.series = {}
        caches.casefold = {}
        caches.mask = {}

    combined_mask = pd.Series(True, index=df.index)
    frame_key = _dataframe_cache_key(df, revision, caches)

    processed_or_groups: set[tuple[tuple[str, ...], tuple[str, ...]]] = set()
    for col, raw in active_column_filters.items():
        if not bool(combined_mask.any()):
            return df.iloc[0:0]
        raw_str = str(raw).strip()
        group = column_to_or_group.get(col)
        if isinstance(group, dict):
            group_key = _or_group_key(group)
            if group_key in processed_or_groups:
                continue
            processed_or_groups.add(group_key)
            group_mask = _build_or_group_mask(
                df,
                group,
                raw_str,
                frame_key=frame_key,
                revision=revision,
                caches=caches,
                build_column_mask=build_column_mask,
                date_display_columns=date_display_columns,
            )
            if group_mask is None:
                continue
            if not group_mask.all():
                combined_mask = combined_mask & group_mask
            continue
        if col not in df.columns or not raw_str:
            continue
        col_mask = _build_effective_column_mask(
            df,
            col,
            raw_str,
            frame_key=frame_key,
            revision=revision,
            caches=caches,
            build_column_mask=build_column_mask,
            date_display_columns=date_display_columns,
        )
        if not col_mask.all():
            combined_mask = combined_mask & col_mask
    if combined_mask.all():
        return df
    return df[combined_mask]


def _or_group_key(group: OrFilterGroup) -> tuple[tuple[str, ...], tuple[str, ...]]:
    columns = tuple(str(col) for col in group.get("columns", []))
    values = tuple(
        str(value).strip()
        for value in group.get("values", [])
        if str(value).strip()
    )
    return columns, values


def _build_or_group_mask(
    df: pd.DataFrame,
    group: OrFilterGroup,
    fallback_raw: str,
    *,
    frame_key: tuple[int, str],
    revision: int,
    caches: ColumnFilterCaches,
    build_column_mask: Callable[..., pd.Series],
    date_display_columns: set[str] | frozenset[str] | None,
) -> pd.Series | None:
    group_values = [
        str(value).strip() for value in group.get("values", []) if str(value).strip()
    ]
    group_raw = ", ".join(group_values) or fallback_raw
    if not group_raw:
        return None
    include_expr, exclude_expr = _split_positive_and_negative_terms(group_raw)
    if not include_expr and not exclude_expr:
        return None
    group_mask_values = (
        np.zeros(len(df.index), dtype=bool)
        if include_expr
        else np.ones(len(df.index), dtype=bool)
    )
    excluded_mask_values = np.zeros(len(df.index), dtype=bool)
    has_group_column = False
    for group_col in group.get("columns", []):
        col = str(group_col)
        if col not in df.columns:
            continue
        has_group_column = True
        if include_expr:
            include_mask = _build_effective_column_mask(
                df,
                col,
                include_expr,
                frame_key=frame_key,
                revision=revision,
                caches=caches,
                build_column_mask=build_column_mask,
                date_display_columns=date_display_columns,
            )
            np.logical_or(
                group_mask_values,
                include_mask.to_numpy(dtype=bool, copy=False),
                out=group_mask_values,
            )
        if exclude_expr:
            exclude_mask = _build_effective_column_mask(
                df,
                col,
                exclude_expr,
                frame_key=frame_key,
                revision=revision,
                caches=caches,
                build_column_mask=build_column_mask,
                date_display_columns=date_display_columns,
            )
            np.logical_or(
                excluded_mask_values,
                exclude_mask.to_numpy(dtype=bool, copy=False),
                out=excluded_mask_values,
            )
    if not has_group_column:
        return None
    if exclude_expr:
        np.logical_and(group_mask_values, ~excluded_mask_values, out=group_mask_values)
    return pd.Series(group_mask_values, index=df.index)


def _build_effective_column_mask(
    df: pd.DataFrame,
    col: str,
    raw_str: str,
    *,
    frame_key: tuple[int, str],
    revision: int,
    caches: ColumnFilterCaches,
    build_column_mask: Callable[..., pd.Series],
    date_display_columns: set[str] | frozenset[str] | None,
) -> pd.Series:
    mask_key = (frame_key, str(col), raw_str)
    cached_mask = caches.mask.get(mask_key)
    if isinstance(cached_mask, pd.Series):
        return cached_mask.reindex(df.index, fill_value=False)

    col_series, col_casefold = _get_cached_text_series(
        df,
        col,
        frame_key=frame_key,
        caches=caches,
    )
    col_mask = build_column_mask(
        col_series,
        raw_str,
        casefolded_series=col_casefold,
    )
    display_dates = None
    if _should_match_date_display_filter_cached(
        caches,
        raw_str,
        is_date_column=col in (date_display_columns or frozenset()),
    ):
        display_dates = get_column_filter_date_display_series(
            df,
            col,
            revision=revision,
            caches=caches,
        )
    if isinstance(display_dates, pd.Series) and not display_dates.empty:
        col_mask = _merge_date_display_mask(
            col_series,
            col_casefold,
            display_dates,
            raw_str,
            build_column_mask,
        )
    caches.mask[mask_key] = col_mask
    _trim_cache_dict(caches.mask, caches.max_entries)
    return col_mask.reindex(df.index, fill_value=False)


def _get_cached_text_series(
    df: pd.DataFrame,
    col: str,
    *,
    frame_key: tuple[int, str],
    caches: ColumnFilterCaches,
) -> tuple[pd.Series, pd.Series]:
    cache_key = (frame_key, str(col))
    cached_series = caches.series.get(cache_key)
    cached_casefold = caches.casefold.get(cache_key)
    if isinstance(cached_series, pd.Series):
        col_series = cached_series
        col_casefold = (
            cached_casefold
            if isinstance(cached_casefold, pd.Series)
            else col_series.str.casefold()
        )
        return col_series, col_casefold
    col_series = df[col].astype("string").fillna("")
    col_casefold = col_series.str.casefold()
    caches.series[cache_key] = col_series
    caches.casefold[cache_key] = col_casefold
    _trim_cache_dict(caches.series, caches.max_entries)
    _trim_cache_dict(caches.casefold, caches.max_entries)
    return col_series, col_casefold


def _trim_cache_dict(cache: dict, max_entries: int) -> None:
    limit = max(1, int(max_entries))
    while len(cache) > limit:
        first_key = next(iter(cache), None)
        if first_key is None:
            return
        cache.pop(first_key, None)


def _trim_date_caches(caches: ColumnFilterCaches) -> None:
    limit = max(1, int(caches.max_entries))
    while len(caches.date) > limit:
        first_key = next(iter(caches.date), None)
        if first_key is None:
            break
        caches.date.pop(first_key, None)
        caches.date_parsed.pop(first_key, None)
    while len(caches.date_parsed) > limit:
        first_key = next(iter(caches.date_parsed), None)
        if first_key is None:
            break
        caches.date_parsed.pop(first_key, None)
        caches.date.pop(first_key, None)


def _should_match_date_display_filter_cached(
    caches: ColumnFilterCaches,
    raw_filter: str,
    *,
    is_date_column: bool,
) -> bool:
    cache_key = (str(raw_filter or ""), bool(is_date_column))
    cached = caches.date_filter_terms.get(cache_key)
    if isinstance(cached, bool):
        return cached
    result = should_match_date_display_filter(
        raw_filter,
        is_date_column=is_date_column,
    )
    caches.date_filter_terms[cache_key] = result
    _trim_cache_dict(caches.date_filter_terms, caches.max_entries)
    return result


def _merge_date_display_mask(
    col_series: pd.Series,
    col_casefold: pd.Series,
    display_dates: pd.Series,
    raw_str: str,
    build_column_mask: Callable[..., pd.Series],
) -> pd.Series:
    include_expr, exclude_expr = _split_positive_and_negative_terms(raw_str)
    if include_expr:
        raw_include = build_column_mask(
            col_series,
            include_expr,
            casefolded_series=col_casefold,
        )
        display_include = build_column_mask(display_dates, include_expr)
        col_mask = raw_include | display_include.reindex(
            raw_include.index,
            fill_value=False,
        )
    else:
        col_mask = pd.Series(True, index=col_series.index)
    if exclude_expr:
        raw_excluded = build_column_mask(
            col_series,
            exclude_expr,
            casefolded_series=col_casefold,
        )
        display_excluded = build_column_mask(display_dates, exclude_expr)
        excluded_mask = raw_excluded | display_excluded.reindex(
            raw_excluded.index,
            fill_value=False,
        )
        col_mask = col_mask & ~excluded_mask
    return col_mask


def _split_positive_and_negative_terms(raw_str: str) -> tuple[str, str]:
    include_terms: list[str] = []
    exclude_terms: list[str] = []
    for token in (term.strip() for term in str(raw_str).split(",")):
        if not token:
            continue
        if token.startswith("!"):
            value = token[1:].strip()
            if value:
                exclude_terms.append(value)
            continue
        include_terms.append(token)
    return ", ".join(include_terms), ", ".join(exclude_terms)
