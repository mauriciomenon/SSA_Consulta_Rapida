"""Pure list export helpers for the main SSA table."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import pandas as pd

from utils.formatting import format_dataframe_for_display


@dataclass(frozen=True)
class ListExportResult:
    path: str
    rows: int
    columns: int


def resolve_export_columns(
    dataframe: pd.DataFrame,
    visible_columns: list[str] | tuple[str, ...],
) -> list[str]:
    columns = [column for column in visible_columns if column in dataframe.columns]
    if columns:
        return columns
    return list(dataframe.columns)


def write_current_list_tsv(
    dataframe: pd.DataFrame,
    visible_columns: list[str] | tuple[str, ...],
    path: str,
    *,
    formatter: Callable[[pd.DataFrame], pd.DataFrame] = format_dataframe_for_display,
) -> ListExportResult:
    if dataframe is None or dataframe.empty:
        raise ValueError("No data to export")
    export_path = str(Path(path).expanduser())
    columns = resolve_export_columns(dataframe, visible_columns)
    export_df = dataframe.loc[:, columns].copy()
    return write_prepared_list_tsv(export_df, export_path, formatter=formatter)


def write_prepared_list_tsv(
    dataframe: pd.DataFrame,
    path: str,
    *,
    formatter: Callable[[pd.DataFrame], pd.DataFrame] = format_dataframe_for_display,
) -> ListExportResult:
    if dataframe is None or dataframe.empty:
        raise ValueError("No data to export")
    export_path = str(Path(path).expanduser())
    formatted_df = formatter(dataframe)
    formatted_df.to_csv(export_path, sep="\t", index=False)
    return ListExportResult(
        path=export_path,
        rows=int(len(formatted_df.index)),
        columns=int(len(formatted_df.columns)),
    )
