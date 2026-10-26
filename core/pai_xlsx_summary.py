"""Streaming summary reader for normalized PAI XLSX files."""

from __future__ import annotations

import logging
from typing import TypedDict

import pandas as pd

SUMMARY_SSA_EXAMPLE_LIMIT = 20
SUMMARY_GROUP_EXAMPLE_LIMIT = 10
logger = logging.getLogger(__name__)


class PaiXlsxSummary(TypedDict):
    ssa_examples: list[str]
    rows_by_executor_sector: dict[str, int]
    rows_by_emitter_sector: dict[str, int]
    rows_by_source_file: dict[str, int]
    ssa_examples_by_executor_sector: dict[str, list[str]]
    summary_error: str | None


def empty_pai_xlsx_summary() -> PaiXlsxSummary:
    return _empty_pai_xlsx_summary(None)


def summarize_normalized_pai_frame(frame: pd.DataFrame) -> PaiXlsxSummary:
    number_values = _normalized_text_series(frame, "numero_ssa")
    executor_values = _normalized_text_series(frame, "setor_executor")
    emitter_values = _normalized_text_series(frame, "setor_emissor")
    source_file_values = _normalized_text_series(frame, "arquivo_origem")
    grouped_examples = pd.DataFrame(
        {"executor": executor_values, "number": number_values}
    )
    examples_by_executor: dict[str, list[str]] = {
        executor: group["number"].head(SUMMARY_GROUP_EXAMPLE_LIMIT).tolist()
        for executor, group in grouped_examples[
            (grouped_examples["executor"] != "") & (grouped_examples["number"] != "")
        ].groupby("executor", sort=False)
    }
    return PaiXlsxSummary(
        ssa_examples=number_values[number_values != ""]
        .head(SUMMARY_SSA_EXAMPLE_LIMIT)
        .tolist(),
        rows_by_executor_sector=executor_values[executor_values != ""]
        .value_counts(sort=False)
        .to_dict(),
        rows_by_emitter_sector=emitter_values[emitter_values != ""]
        .value_counts(sort=False)
        .to_dict(),
        rows_by_source_file=source_file_values[source_file_values != ""]
        .value_counts(sort=False)
        .to_dict(),
        ssa_examples_by_executor_sector=examples_by_executor,
        summary_error=None,
    )


def _empty_pai_xlsx_summary(summary_error: str | None) -> PaiXlsxSummary:
    return PaiXlsxSummary(
        ssa_examples=[],
        rows_by_executor_sector={},
        rows_by_emitter_sector={},
        rows_by_source_file={},
        ssa_examples_by_executor_sector={},
        summary_error=summary_error,
    )


def _normalized_text_series(frame: pd.DataFrame, column: str) -> pd.Series:
    if column not in frame.columns:
        return pd.Series("", index=frame.index)
    return frame[column].fillna("").astype("string").str.strip()


