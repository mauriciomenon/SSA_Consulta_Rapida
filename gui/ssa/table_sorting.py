"""Table sorting helpers for the main SSA table."""

from __future__ import annotations

from typing import Any, Callable

import pandas as pd


MAX_SORT_CACHE_ROWS = 120_000
PLAIN_TEXT_SORT_COLUMNS = frozenset(
    {
        "descricao_ssa",
        "descricao_execucao",
        "solicitante",
        "responsavel_programacao",
        "responsavel_execucao",
    }
)


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


def empty_sort_cache(*, column_name: str | None = None) -> dict[str, Any]:
    cache: dict[str, Any] = {
        "source_marker": None,
        "source_len": 0,
        "keys_df": None,
    }
    if column_name is not None:
        cache["column_name"] = column_name
    return cache


def sort_num_reprogramacoes_robust(
    source_df: pd.DataFrame | None,
    ascending: bool,
    cache_store: dict[str, Any] | None,
    builder: Callable[[pd.DataFrame], pd.DataFrame] | None = None,
) -> tuple[pd.DataFrame | None, dict[str, Any]]:
    if source_df is None or source_df.empty:
        return source_df, empty_sort_cache()
    if "num_reprogramacoes" not in source_df.columns:
        return source_df, empty_sort_cache()
    sort_keys_builder = builder or build_num_reprogramacoes_sort_keys

    sort_keys, _cached_store = get_num_reprogramacoes_sort_keys(
        source_df,
        cache_store,
        builder=sort_keys_builder,
    )
    sort_direction = bool(ascending)
    sorted_keys = _sort_keys_frame(
        sort_keys,
        by=["__reprog_is_nan", "__reprog_num", "__reprog_txt"],
        ascending=[True, sort_direction, sort_direction],
    )
    sorted_df = source_df.loc[sorted_keys.index]
    return (
        sorted_df,
        store_num_reprogramacoes_sort_cache(sorted_df, sorted_keys),
    )


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
    if column_name in PLAIN_TEXT_SORT_COLUMNS:
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
    is_numeric = normalized_numeric_text.str.fullmatch(r"[+-]?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?").fillna(False)
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
    source_df: pd.DataFrame,
    column_name: str,
    cache_store: dict[str, Any] | None,
    builder: Callable[[pd.Series], pd.DataFrame] | None = None,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    sort_keys_builder = builder or build_mixed_text_sort_keys
    return _resolve_sort_keys_with_cache(
        source_df=source_df,
        cache_store=cache_store,
        columns=(column_name,),
        column_name=column_name,
        builder=lambda frame: sort_keys_builder(frame[column_name]),
    )


def sort_mixed_text_column_robust(
    source_df: pd.DataFrame | None,
    column_name: str,
    ascending: bool,
    cache_store: dict[str, Any] | None,
    builder: Callable[[pd.Series], pd.DataFrame] | None = None,
) -> tuple[pd.DataFrame | None, dict[str, Any]]:
    if source_df is None or source_df.empty:
        return source_df, empty_sort_cache(column_name=column_name)
    if column_name not in source_df.columns:
        return source_df, empty_sort_cache(column_name=column_name)
    sort_keys_builder = builder or build_mixed_text_sort_keys

    sort_keys, next_cache = get_mixed_text_sort_keys(
        source_df,
        column_name,
        cache_store,
        builder=sort_keys_builder,
    )
    sort_direction = bool(ascending)
    sorted_keys = _sort_keys_frame(
        sort_keys,
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
    )
    sorted_df = source_df.loc[sorted_keys.index]
    return (
        sorted_df,
        _build_sort_cache(
            column_name=column_name,
            source_marker=_get_sort_cache_source_marker(sorted_df, (column_name,)),
            source_len=len(sorted_df.index),
            keys_df=sorted_keys,
        ),
    )


def get_num_reprogramacoes_sort_keys(
    source_df: pd.DataFrame | None,
    cache_store: dict[str, Any] | None,
    builder: Callable[[pd.DataFrame], pd.DataFrame] | None = None,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    if not isinstance(source_df, pd.DataFrame):
        return empty_num_reprogramacoes_sort_keys(), empty_sort_cache()
    if "num_reprogramacoes" not in source_df.columns:
        return empty_num_reprogramacoes_sort_keys(source_df.index), empty_sort_cache()
    sort_keys_builder = builder or build_num_reprogramacoes_sort_keys
    return _resolve_sort_keys_with_cache(
        source_df=source_df,
        cache_store=cache_store,
        columns=("num_reprogramacoes",),
        builder=sort_keys_builder,
    )


def prime_num_reprogramacoes_sort_cache(
    source_df: pd.DataFrame | None,
    builder: Callable[[pd.DataFrame], pd.DataFrame] | None = None,
) -> dict[str, Any]:
    if not isinstance(source_df, pd.DataFrame):
        return empty_sort_cache()
    if source_df.empty or "num_reprogramacoes" not in source_df.columns:
        return empty_sort_cache()
    sort_keys_builder = builder or build_num_reprogramacoes_sort_keys
    keys_df = sort_keys_builder(source_df)
    return _build_sort_cache(
        source_marker=_get_sort_cache_source_marker(source_df, ("num_reprogramacoes",)),
        source_len=len(source_df.index),
        keys_df=keys_df,
    )


def store_num_reprogramacoes_sort_cache(source_df: pd.DataFrame, keys_df: pd.DataFrame) -> dict[str, Any]:
    return _build_sort_cache(
        source_marker=_get_sort_cache_source_marker(source_df, ("num_reprogramacoes",)),
        source_len=len(source_df.index),
        keys_df=keys_df,
    )


def _build_sort_cache(
    source_marker: tuple,
    source_len: int,
    keys_df: pd.DataFrame,
    *,
    column_name: str | None = None,
) -> dict[str, Any]:
    if source_len > MAX_SORT_CACHE_ROWS:
        return empty_sort_cache(column_name=column_name)
    payload = empty_sort_cache(column_name=column_name)
    payload.update(
        {
            "source_marker": source_marker,
            "source_len": source_len,
            "keys_df": keys_df,
        }
    )
    if column_name is None:
        payload.pop("column_name", None)
    return payload


def _get_cached_sort_keys_fast(
    source_df: pd.DataFrame,
    cache_store: dict[str, Any] | None,
    *,
    columns: tuple[str, ...],
    column_name: str | None = None,
) -> pd.DataFrame | None:
    if not isinstance(cache_store, dict):
        return None
    if column_name is not None and cache_store.get("column_name") != column_name:
        return None
    try:
        cache_source_len = int(cache_store.get("source_len", -1))
    except (TypeError, ValueError):
        return None
    keys_df = cache_store.get("keys_df")
    cache_marker = cache_store.get("source_marker")
    if not isinstance(keys_df, pd.DataFrame):
        return None
    if not isinstance(cache_marker, tuple) or len(cache_marker) != 4:
        return None
    fast_marker_prefix = (
        _get_sort_cache_index_signature(source_df),
        len(source_df.index),
        tuple(columns),
    )
    if cache_source_len != fast_marker_prefix[1]:
        return None
    if cache_marker[:3] != fast_marker_prefix:
        return None
    source_marker = _get_sort_cache_source_marker(source_df, columns)
    if cache_marker == source_marker:
        return keys_df
    return None


def _sort_keys_frame(
    sort_keys: pd.DataFrame,
    *,
    by: list[str],
    ascending: list[bool],
) -> pd.DataFrame:
    return sort_keys.sort_values(
        by=by,
        ascending=ascending,
        na_position="last",
        kind="mergesort",
    )


def _resolve_sort_keys_with_cache(
    *,
    source_df: pd.DataFrame,
    cache_store: dict[str, Any] | None,
    columns: tuple[str, ...],
    builder: Callable[[pd.DataFrame], pd.DataFrame],
    column_name: str | None = None,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    keys_df = _get_cached_sort_keys_fast(
        source_df,
        cache_store,
        columns=columns,
        column_name=column_name,
    )
    if keys_df is not None:
        return (
            keys_df,
            cache_store
            if isinstance(cache_store, dict)
            else empty_sort_cache(column_name=column_name),
        )
    keys_df = builder(source_df)
    return (
        keys_df,
        _build_sort_cache(
            column_name=column_name,
            source_marker=_get_sort_cache_source_marker(source_df, columns),
            source_len=len(source_df.index),
            keys_df=keys_df,
        ),
    )


def _get_sort_cache_source_marker(
    source_df: pd.DataFrame, columns: tuple[str, ...]
) -> tuple:
    return (
        _get_sort_cache_index_signature(source_df),
        len(source_df.index),
        tuple(columns),
        _sample_sort_cache_values(source_df, columns),
    )


def _get_sort_cache_index_signature(source_df: pd.DataFrame) -> int:
    return int(pd.util.hash_pandas_object(source_df.index, index=False).sum())


def _sample_sort_cache_values(
    source_df: pd.DataFrame, columns: tuple[str, ...]
) -> tuple[tuple[object | None, ...], ...]:
    if source_df.empty:
        return tuple()
    row_indexes = sorted({0, len(source_df.index) // 2, len(source_df.index) - 1})
    safe_columns = [column for column in columns if column in source_df.columns]
    sampled_rows = (
        source_df.iloc[row_indexes][safe_columns].itertuples(index=False, name=None)
        if safe_columns
        else ()
    )
    sampled_values = [tuple(row) for row in sampled_rows]
    values: list[tuple[object | None, ...]] = []
    for sample_pos in range(len(row_indexes)):
        row_map = (
            dict(zip(safe_columns, sampled_values[sample_pos], strict=False))
            if safe_columns
            else {}
        )
        row_values: list[object | None] = []
        for column in columns:
            if column not in row_map:
                row_values.append("")
                continue
            value = row_map[column]
            row_values.append(None if pd.isna(value) else value)
        values.append(tuple(row_values))
    return tuple(values)
