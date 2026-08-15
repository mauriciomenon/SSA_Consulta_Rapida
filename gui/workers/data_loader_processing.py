"""Data loading query and DataFrame preparation helpers."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import Any

import pandas as pd

logger = logging.getLogger(__name__)

DEFAULT_UI_STATUS_LAST = "STE"
SQLITE_OFFSET_WITHOUT_LIMIT = 9223372036854775807
SQLITE_INTEGER_PREFIX_RE = re.compile(r"^\s*([+-]?\d+)")
SSA_IDENTIFIER_TEXT_RE = re.compile(r"^(?:SSA[\s:_-]*)?\d[\d\s._-]*$", re.IGNORECASE)
DEFAULT_UI_SORT_SPEC = (
    {
        "column": "situacao",
        "kind": "status_last",
        "last_value": "STE",
        "ascending": True,
        "temp_column": "__sort_situacao",
    },
    {
        "column": "numero_ssa",
        "kind": "sqlite_integer_prefix",
        "ascending": False,
        "temp_column": "__sort_numero_ssa",
    },
)
SSA_LIKE_COLUMNS = ("numero_ssa", "derivada_de")


@dataclass(frozen=True)
class LoadedDataFrames:
    """Prepared data-load payload.

    complete and display may reference the same DataFrame when the worker already
    emitted the canonical initial display order and no GUI filter was applied.
    """

    complete: pd.DataFrame
    display: pd.DataFrame
    preprocessed_for_gui: bool
    attrs: dict[str, Any]


def sanitize_ssa_like_value(value) -> str:
    try:
        return str(sanitize_ssa_like_series(pd.Series([value], dtype="object")).iloc[0])
    except Exception:
        return ""


def coerce_sqlite_integer_prefix_series(values: pd.Series) -> pd.Series:
    return (
        values.astype(str)
        .str.extract(SQLITE_INTEGER_PREFIX_RE, expand=False)
        .pipe(pd.to_numeric, errors="coerce")
        .fillna(0)
        .astype("int64")
    )


def build_initial_sorted_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    try:
        sort_columns = []
        ascending = []
        sort_keys = pd.DataFrame(index=df.index)
        for rule in DEFAULT_UI_SORT_SPEC:
            source_column = str(rule["column"])
            temp_column = str(rule["temp_column"])
            sort_columns.append(temp_column)
            ascending.append(bool(rule["ascending"]))
            if source_column not in df.columns:
                default_value = False if rule["kind"] == "status_last" else 0
                sort_keys[temp_column] = default_value
                continue
            source_series = df[source_column]
            if rule["kind"] == "status_last":
                sort_keys[temp_column] = (
                    source_series.astype(str).str.upper().eq(str(rule["last_value"]))
                )
            elif rule["kind"] == "sqlite_integer_prefix":
                sort_keys[temp_column] = coerce_sqlite_integer_prefix_series(
                    source_series
                )
            else:
                raise ValueError(f"Regra de ordenacao default desconhecida: {rule}")
        sorted_index = sort_keys.sort_values(
            by=sort_columns,
            ascending=ascending,
            na_position="last",
        ).index
        return df.loc[sorted_index].copy()
    except (KeyError, TypeError, ValueError, AttributeError) as exc:
        logger.warning(
            "Falha na ordenacao inicial durante preprocessamento do DataLoaderWorker: %s",
            exc,
        )
    return df


def build_non_null_columns(df: pd.DataFrame) -> list[str]:
    try:
        non_null_mask = df.notna().any(axis=0)
        return [str(col) for col in non_null_mask[non_null_mask].index.tolist()]
    except (TypeError, ValueError, AttributeError, KeyError) as exc:
        logger.debug(
            "Falha no calculo vetorizado de colunas nao nulas no DataLoaderWorker: %s",
            exc,
        )
        return []


def _normalize_null_tokens(values: pd.Series) -> pd.Series:
    sanitized_series = values.astype("string").fillna("").str.strip()
    null_token_mask = sanitized_series.str.lower().isin({"nan", "none", "nat", "<na>"})
    if bool(null_token_mask.any()):
        sanitized_series.loc[null_token_mask] = ""
    return sanitized_series


def _strip_decimal_artifacts(values: pd.Series) -> pd.Series:
    sanitized_series = values
    decimal_mask = sanitized_series.str.fullmatch(r"\d+\.0+", na=False)
    if bool(decimal_mask.any()):
        sanitized_series.loc[decimal_mask] = sanitized_series.loc[
            decimal_mask
        ].str.replace(r"\.0+$", "", regex=True)
    return sanitized_series


def _fold_identifier_digits(values: pd.Series) -> pd.Series:
    sanitized_series = values
    identifier_like_mask = sanitized_series.str.fullmatch(
        SSA_IDENTIFIER_TEXT_RE, na=False
    )
    if bool(identifier_like_mask.any()):
        digit_folds = sanitized_series.loc[identifier_like_mask].str.replace(
            r"\D+", "", regex=True
        )
        folded_ssa_mask = digit_folds.str.len().eq(9)
        if bool(folded_ssa_mask.any()):
            folded_index = digit_folds.loc[folded_ssa_mask].index
            sanitized_series.loc[folded_index] = digit_folds.loc[folded_index]
    return sanitized_series


def sanitize_ssa_like_series(values: pd.Series) -> pd.Series:
    sanitized_series = _normalize_null_tokens(values)
    sanitized_series = _strip_decimal_artifacts(sanitized_series)
    sanitized_series = _fold_identifier_digits(sanitized_series)
    return sanitized_series.fillna("")


def sanitize_ssa_columns(df: pd.DataFrame) -> pd.DataFrame:
    for ssa_col in SSA_LIKE_COLUMNS:
        if ssa_col in df.columns:
            df[ssa_col] = sanitize_ssa_like_series(df[ssa_col])
    return df


def prepare_dataframe_for_ui(
    df: pd.DataFrame,
    *,
    order_by: str | None = None,
    already_sorted_for_ui: bool = False,
) -> pd.DataFrame:
    if order_by or already_sorted_for_ui:
        working_df = df.copy(deep=False)
    else:
        working_df = build_initial_sorted_dataframe(df)
    sanitized_df = sanitize_ssa_columns(working_df)
    try:
        sanitized_df.attrs["ssa_preprocessed_for_gui"] = True
        sanitized_df.attrs["ssa_non_null_cols"] = build_non_null_columns(sanitized_df)
    except (AttributeError, TypeError, ValueError) as exc:
        logger.debug(
            "Falha ao anexar attrs de preprocessamento no DataLoaderWorker: %s", exc
        )
    return sanitized_df


def prepare_loaded_payload(
    df: pd.DataFrame,
    *,
    order_by: str | None = None,
    already_sorted_for_ui: bool = False,
) -> LoadedDataFrames:
    prepared_df = prepare_dataframe_for_ui(
        df, order_by=order_by, already_sorted_for_ui=already_sorted_for_ui
    )
    return LoadedDataFrames(
        complete=prepared_df,
        display=prepared_df,
        preprocessed_for_gui=True,
        attrs=dict(getattr(prepared_df, "attrs", {}) or {}),
    )


def prepare_legacy_loaded_payload(df: pd.DataFrame) -> LoadedDataFrames:
    attrs = dict(getattr(df, "attrs", {}) or {})
    preprocessed_for_gui = bool(attrs.get("ssa_preprocessed_for_gui"))
    if preprocessed_for_gui:
        complete_df = df
    else:
        complete_df = df.copy()
        complete_df = sanitize_ssa_columns(complete_df)
    display_df = (
        complete_df if preprocessed_for_gui else build_initial_sorted_dataframe(complete_df)
    )
    try:
        complete_df.attrs["ssa_preprocessed_for_gui"] = True
        complete_df.attrs["ssa_non_null_cols"] = build_non_null_columns(complete_df)
    except (AttributeError, TypeError, ValueError) as exc:
        logger.debug(
            "Falha ao anexar attrs no payload legado do DataLoaderWorker: %s", exc
        )
    return LoadedDataFrames(
        complete=complete_df,
        display=display_df,
        preprocessed_for_gui=preprocessed_for_gui,
        attrs=dict(getattr(complete_df, "attrs", {}) or attrs),
    )
