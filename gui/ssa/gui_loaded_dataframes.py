"""Loaded DataFrame preparation for GUI data-load flow."""

from __future__ import annotations

import pandas as pd

from gui.workers.data_loader_processing import (
    LoadedDataFrames,
    build_non_null_columns,
    prepare_legacy_loaded_payload,
)


def prepare_loaded_dataframes(df: pd.DataFrame | LoadedDataFrames) -> LoadedDataFrames:
    if isinstance(df, LoadedDataFrames):
        return df
    return prepare_legacy_loaded_payload(df)


def resolve_loaded_columns_with_values(loaded: LoadedDataFrames) -> set[str]:
    """Return columns with at least one non-null value in the loaded frame."""

    non_null_cols_attr = loaded.attrs.get("ssa_non_null_cols")
    if isinstance(non_null_cols_attr, list):
        return {str(col) for col in non_null_cols_attr if str(col)}
    return set(build_non_null_columns(loaded.complete))
