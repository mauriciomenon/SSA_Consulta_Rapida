"""Table sorting helpers for the main SSA table."""

from __future__ import annotations

import uuid
from typing import Any

import pandas as pd


MAX_SORT_CACHE_ROWS = 120_000


def empty_num_reprogramacoes_sort_keys(index: pd.Index | None = None) -> pd.DataFrame:
    result_index = index if index is not None else pd.Index([])
    return pd.DataFrame(
        {
            "__reprog_is_nan": pd.Series(True, index=result_index, dtype="bool"),
            "__reprog_num": pd.Series(pd.NA, index=result_index, dtype="Float64"),
            "__reprog_txt": pd.Series("", index=result_index, dtype="string"),
        },
        index=result_index,
    )


def sort_num_reprogramacoes_robust(window: Any, ascending: bool) -> pd.DataFrame:
    source_df = window.df_exibido
    if source_df is None or source_df.empty:
        return source_df
    if "num_reprogramacoes" not in source_df.columns:
        return source_df

    sort_keys = get_num_reprogramacoes_sort_keys(window)
    sort_direction = bool(ascending)
    ordered_index = sort_keys.sort_values(
        by=["__reprog_is_nan", "__reprog_num", "__reprog_txt"],
        ascending=[True, sort_direction, sort_direction],
        na_position="last",
        kind="mergesort",
    ).index
    sorted_keys = sort_keys.loc[ordered_index]
    window._last_num_reprog_sorted_keys = sorted_keys
    return source_df.loc[ordered_index]


def build_num_reprogramacoes_sort_keys(source_df: pd.DataFrame) -> pd.DataFrame:
    raw_series = source_df["num_reprogramacoes"]
    raw_text = raw_series.astype("string").fillna("")
    numeric = pd.to_numeric(raw_series, errors="coerce").astype("Float64")
    missing_numeric_mask = numeric.isna()
    if bool(missing_numeric_mask.any()):
        extracted_source = raw_text[missing_numeric_mask]
        extracted = extracted_source.str.extract(r"(-?\d+)")[0]
        extracted_numeric = pd.to_numeric(extracted, errors="coerce").astype(
            "Float64"
        )
        numeric = numeric.copy()
        numeric.loc[missing_numeric_mask] = extracted_numeric
    return pd.DataFrame(
        {
            "__reprog_is_nan": numeric.isna(),
            "__reprog_num": numeric,
            "__reprog_txt": raw_text.str.casefold(),
        },
        index=source_df.index,
    )


def should_use_mixed_text_sort(source_df: pd.DataFrame, column_name: str) -> bool:
    if not isinstance(source_df, pd.DataFrame):
        return False
    if column_name not in source_df.columns:
        return False
    series = source_df[column_name]
    dtype = getattr(series, "dtype", None)
    return bool(
        pd.api.types.is_object_dtype(dtype) or pd.api.types.is_string_dtype(dtype)
    )


def build_mixed_text_sort_keys(source_series: pd.Series) -> pd.DataFrame:
    raw_text = source_series.astype("string").fillna("").str.strip()
    empty_mask = source_series.isna() | raw_text.eq("")
    normalized_numeric_text = raw_text.str.replace(",", ".", regex=False)
    is_numeric = normalized_numeric_text.str.fullmatch(
        r"[+-]?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?"
    ).fillna(False)
    numeric_values = pd.to_numeric(
        normalized_numeric_text.where(is_numeric), errors="coerce"
    ).astype("Float64")

    first_char = raw_text.str.slice(0, 1)
    starts_alpha = first_char.str.isalpha().fillna(False)
    starts_alnum = first_char.str.isalnum().fillna(False)
    alpha_mask = (~empty_mask) & (~is_numeric) & starts_alpha
    symbol_mask = (~empty_mask) & (~is_numeric) & (~starts_alpha) & (~starts_alnum)
    other_text_mask = (~empty_mask) & (~is_numeric) & (~alpha_mask) & (~symbol_mask)

    bucket_order = pd.Series(3, index=raw_text.index, dtype="Int64")
    bucket_order.loc[symbol_mask] = 0
    bucket_order.loc[is_numeric] = 1
    bucket_order.loc[alpha_mask] = 2
    bucket_order.loc[other_text_mask] = 3
    bucket_order.loc[empty_mask] = 9

    normalized_text = raw_text.str.casefold()
    return pd.DataFrame(
        {
            "__mixed_is_empty": empty_mask,
            "__mixed_bucket_order": bucket_order,
            "__mixed_symbol_txt": normalized_text.where(symbol_mask),
            "__mixed_num": numeric_values,
            "__mixed_alpha_txt": normalized_text.where(alpha_mask),
            "__mixed_other_txt": normalized_text.where(other_text_mask),
        },
        index=source_series.index,
    )


def get_mixed_text_sort_keys(
    window: Any, source_df: pd.DataFrame, column_name: str
) -> pd.DataFrame:
    source_marker = _get_sort_cache_source_marker(source_df, (column_name,))
    source_len = len(source_df.index)
    cache = getattr(window, "_mixed_text_sort_cache", None)
    keys_df = _get_valid_sort_cache_frame(
        cache,
        source_marker=source_marker,
        source_len=source_len,
        column_name=column_name,
    )
    if keys_df is None:
        keys_df = _build_mixed_text_sort_keys_for_window(window, source_df[column_name])
        _store_mixed_text_sort_cache(
            window, column_name, source_marker, source_len, keys_df
        )
    if not isinstance(keys_df, pd.DataFrame):
        keys_df = _build_mixed_text_sort_keys_for_window(window, source_df[column_name])
    return keys_df


def sort_mixed_text_column_robust(
    window: Any, column_name: str, ascending: bool
) -> pd.DataFrame:
    source_df = window.df_exibido
    if source_df is None or source_df.empty:
        return source_df
    if column_name not in source_df.columns:
        return source_df

    sort_keys = get_mixed_text_sort_keys(window, source_df, column_name)
    sort_direction = bool(ascending)
    ordered_index = sort_keys.sort_values(
        by=[
            "__mixed_is_empty",
            "__mixed_bucket_order",
            "__mixed_symbol_txt",
            "__mixed_num",
            "__mixed_alpha_txt",
            "__mixed_other_txt",
        ],
        ascending=[
            True,
            sort_direction,
            sort_direction,
            sort_direction,
            sort_direction,
            sort_direction,
        ],
        na_position="last",
        kind="mergesort",
    ).index
    sorted_df = source_df.loc[ordered_index]
    sorted_df.attrs["_ssa_sort_cache_base_token"] = _get_sort_cache_base_token(
        source_df
    )
    _store_mixed_text_sort_cache(
        window,
        column_name,
        _get_sort_cache_source_marker(sorted_df, (column_name,)),
        len(sorted_df.index),
        sort_keys.loc[ordered_index],
    )
    return sorted_df


def get_num_reprogramacoes_sort_keys(window: Any) -> pd.DataFrame:
    source_df = window.df_exibido
    if not isinstance(source_df, pd.DataFrame):
        return empty_num_reprogramacoes_sort_keys()
    if "num_reprogramacoes" not in source_df.columns:
        return empty_num_reprogramacoes_sort_keys(source_df.index)

    source_marker = _get_sort_cache_source_marker(source_df, ("num_reprogramacoes",))
    source_len = len(source_df.index)
    cache = getattr(window, "_num_reprog_sort_cache", None)
    keys_df = _get_valid_sort_cache_frame(
        cache,
        source_marker=source_marker,
        source_len=source_len,
    )
    if keys_df is None:
        keys_df = _build_num_reprogramacoes_sort_keys_for_window(window, source_df)
        _store_num_reprogramacoes_sort_cache(window, source_marker, source_len, keys_df)
    if not isinstance(keys_df, pd.DataFrame):
        keys_df = _build_num_reprogramacoes_sort_keys_for_window(window, source_df)
    return keys_df


def prime_num_reprogramacoes_sort_cache(window: Any) -> None:
    source_df = window.df_exibido
    if not isinstance(source_df, pd.DataFrame):
        window._reset_num_reprogramacoes_sort_cache()
        return
    if source_df.empty or "num_reprogramacoes" not in source_df.columns:
        window._reset_num_reprogramacoes_sort_cache()
        return
    keys_df = _build_num_reprogramacoes_sort_keys_for_window(window, source_df)
    _store_num_reprogramacoes_sort_cache(
        window,
        _get_sort_cache_source_marker(source_df, ("num_reprogramacoes",)),
        len(source_df.index),
        keys_df,
    )


def store_num_reprogramacoes_sort_cache(
    window: Any, source_df: pd.DataFrame, keys_df: pd.DataFrame
) -> None:
    _store_num_reprogramacoes_sort_cache(
        window,
        _get_sort_cache_source_marker(source_df, ("num_reprogramacoes",)),
        len(source_df.index),
        keys_df,
    )


def _store_mixed_text_sort_cache(
    window: Any,
    column_name: str,
    source_marker: tuple,
    source_len: int,
    keys_df: pd.DataFrame,
) -> None:
    _store_sort_cache(
        window,
        cache_attr="_mixed_text_sort_cache",
        reset_method="_reset_mixed_text_sort_cache",
        source_len=source_len,
        payload={
            "column_name": column_name,
            "source_marker": source_marker,
            "source_len": source_len,
            "keys_df": keys_df,
        },
    )


def _store_num_reprogramacoes_sort_cache(
    window: Any,
    source_marker: tuple,
    source_len: int,
    keys_df: pd.DataFrame,
) -> None:
    _store_sort_cache(
        window,
        cache_attr="_num_reprog_sort_cache",
        reset_method="_reset_num_reprogramacoes_sort_cache",
        source_len=source_len,
        payload={
            "source_marker": source_marker,
            "source_len": source_len,
            "keys_df": keys_df,
        },
    )


def _store_sort_cache(
    window: Any,
    *,
    cache_attr: str,
    reset_method: str,
    source_len: int,
    payload: dict[str, Any],
) -> None:
    if source_len > MAX_SORT_CACHE_ROWS:
        reset_cache = getattr(window, reset_method)
        reset_cache()
        return
    setattr(window, cache_attr, payload)


def _get_sort_cache_source_marker(
    source_df: pd.DataFrame, columns: tuple[str, ...]
) -> tuple:
    return (
        _get_sort_cache_base_token(source_df),
        len(source_df.index),
        tuple(columns),
        _sample_sort_cache_values(source_df, columns),
    )


def _get_sort_cache_base_token(source_df: pd.DataFrame) -> str:
    token = source_df.attrs.get("_ssa_sort_cache_base_token")
    if isinstance(token, str) and token:
        return token
    token = uuid.uuid4().hex
    source_df.attrs["_ssa_sort_cache_base_token"] = token
    return token


def _sample_sort_cache_values(
    source_df: pd.DataFrame, columns: tuple[str, ...]
) -> tuple[tuple[str, ...], ...]:
    if source_df.empty:
        return tuple()
    row_indexes = sorted({0, len(source_df.index) // 2, len(source_df.index) - 1})
    values: list[tuple[str, ...]] = []
    for row_index in row_indexes:
        row_values: list[str] = []
        for column in columns:
            if column not in source_df.columns:
                row_values.append("")
                continue
            value = source_df.iloc[row_index][column]
            row_values.append("" if pd.isna(value) else str(value))
        values.append(tuple(row_values))
    return tuple(values)


def _build_mixed_text_sort_keys_for_window(
    window: Any, source_series: pd.Series
) -> pd.DataFrame:
    builder = getattr(window, "_build_mixed_text_sort_keys", None)
    if callable(builder):
        return builder(source_series)
    return build_mixed_text_sort_keys(source_series)


def _build_num_reprogramacoes_sort_keys_for_window(
    window: Any, source_df: pd.DataFrame
) -> pd.DataFrame:
    builder = getattr(window, "_build_num_reprogramacoes_sort_keys", None)
    if callable(builder):
        return builder(source_df)
    return build_num_reprogramacoes_sort_keys(source_df)


def _get_valid_sort_cache_frame(
    cache: Any,
    *,
    source_marker: tuple,
    source_len: int,
    column_name: str | None = None,
) -> pd.DataFrame | None:
    if not isinstance(cache, dict):
        return None
    if column_name is not None and cache.get("column_name") != column_name:
        return None
    try:
        cache_source_len = int(cache.get("source_len", -1))
    except (TypeError, ValueError):
        return None
    keys_df = cache.get("keys_df")
    if (
        cache.get("source_marker") == source_marker
        and cache_source_len == source_len
        and isinstance(keys_df, pd.DataFrame)
    ):
        return keys_df
    return None
