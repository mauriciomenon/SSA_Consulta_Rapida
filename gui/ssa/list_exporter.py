"""Pure list export helpers for the main SSA table."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import pandas as pd

from exportacao.exporter import sanitize_spreadsheet_dataframe
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
    numeric_origins = dataframe.map(pd.api.types.is_number)
    formatted_df = formatter(dataframe.copy())
    safe_df = sanitize_spreadsheet_dataframe(formatted_df)
    if formatted_df.index.equals(dataframe.index) and formatted_df.columns.equals(dataframe.columns):
        for position in range(len(formatted_df.columns)):
            rendered = formatted_df.iloc[:, position]
            numeric_text = rendered.astype(str).str.fullmatch(
                r"[+-]?(?:[0-9]+(?:[.,][0-9]+)*|[.,][0-9]+)(?:[eE][+-]?[0-9]+)?"
            )
            preserve_number = numeric_origins.iloc[:, position] & numeric_text
            safe_df.iloc[:, position] = safe_df.iloc[:, position].where(
                ~preserve_number, rendered
            )
    safe_df.to_csv(export_path, sep="\t", index=False)
    return ListExportResult(
        path=export_path,
        rows=int(len(formatted_df.index)),
        columns=int(len(formatted_df.columns)),
    )
