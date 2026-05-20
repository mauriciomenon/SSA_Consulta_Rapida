"""Streaming summary reader for normalized PAI XLSX files."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, TypedDict

from openpyxl import load_workbook

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
    return PaiXlsxSummary(
        ssa_examples=[],
        rows_by_executor_sector={},
        rows_by_emitter_sector={},
        rows_by_source_file={},
        ssa_examples_by_executor_sector={},
        summary_error=None,
    )


def read_pai_xlsx_summary(path: Path | None) -> PaiXlsxSummary:
    if path is None or not path.is_file():
        return empty_pai_xlsx_summary()
    try:
        workbook = load_workbook(path, read_only=True, data_only=True)
    except (OSError, ValueError) as exc:
        logger.warning("Failed to read PAI summary XLSX %s: %s", path, exc)
        return _summary_read_error(type(exc).__name__)
    try:
        sheet = workbook.active
        header_row = next(sheet.iter_rows(min_row=1, max_row=1, values_only=True), None)
        if header_row is None:
            return empty_pai_xlsx_summary()
        header_values = ["" if value is None else str(value).strip() for value in header_row]
        column_positions = {
            key: _column_position(header_values, aliases)
            for key, aliases in {
                "number": ("numero_ssa", "Numero da SSA", "ssa_number", "SSA"),
                "executor": ("setor_executor", "executor_sector", "Setor Executor"),
                "emitter": ("setor_emissor", "emitter_sector", "Setor Emissor"),
                "source_file": ("arquivo_origem", "source_file", "Arquivo Origem"),
            }.items()
        }
        if all(position is None for position in column_positions.values()):
            return empty_pai_xlsx_summary()
        ssa_examples: list[str] = []
        rows_by_executor_sector: dict[str, int] = {}
        rows_by_emitter_sector: dict[str, int] = {}
        rows_by_source_file: dict[str, int] = {}
        examples_by_executor: dict[str, list[str]] = {}
        for row in sheet.iter_rows(min_row=2, values_only=True):
            number = _row_value(row, column_positions["number"])
            executor = _row_value(row, column_positions["executor"])
            emitter = _row_value(row, column_positions["emitter"])
            source_file = _row_value(row, column_positions["source_file"])
            if number and len(ssa_examples) < SUMMARY_SSA_EXAMPLE_LIMIT:
                ssa_examples.append(number)
            if executor:
                rows_by_executor_sector[executor] = (
                    rows_by_executor_sector.get(executor, 0) + 1
                )
            if emitter:
                rows_by_emitter_sector[emitter] = (
                    rows_by_emitter_sector.get(emitter, 0) + 1
                )
            if source_file:
                rows_by_source_file[source_file] = (
                    rows_by_source_file.get(source_file, 0) + 1
                )
            if executor and number:
                bucket = examples_by_executor.setdefault(executor, [])
                if len(bucket) < SUMMARY_GROUP_EXAMPLE_LIMIT:
                    bucket.append(number)
        return PaiXlsxSummary(
            ssa_examples=ssa_examples,
            rows_by_executor_sector=rows_by_executor_sector,
            rows_by_emitter_sector=rows_by_emitter_sector,
            rows_by_source_file=rows_by_source_file,
            ssa_examples_by_executor_sector=examples_by_executor,
            summary_error=None,
        )
    finally:
        workbook.close()


def _summary_read_error(error_name: str) -> PaiXlsxSummary:
    summary = empty_pai_xlsx_summary()
    summary["summary_error"] = f"summary_read_error:{error_name}"
    return summary


def _column_position(header_values: list[str], candidates: tuple[str, ...]) -> int | None:
    existing = {value.casefold(): index for index, value in enumerate(header_values)}
    for candidate in candidates:
        found = existing.get(candidate.casefold())
        if found is not None:
            return found
    return None


def _row_value(row: tuple[Any, ...], position: int | None) -> str:
    if position is None or position >= len(row) or row[position] is None:
        return ""
    return str(row[position]).strip()
