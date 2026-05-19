"""Normalize PAI XLSX exports into the SSA import schema."""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator

import pandas as pd

PAI_TO_SSA_COLUMN_MAP: tuple[tuple[str, str], ...] = (
    ("ssa_number", "numero_ssa"),
    ("localization", "localizacao_codigo"),
    ("description", "descricao_ssa"),
    ("year_week", "semana_cadastro"),
    ("emitter_sector", "setor_emissor"),
    ("executor_sector", "setor_executor"),
)
PAI_DATE_SOURCE_COLUMNS = ("emission_datetime", "issue_datetime")
PAI_SITUACAO_SOURCE_COLUMNS = ("situation_desc", "process_status")
PAI_SSA_IMPORT_SUFFIX = "_ssa_import"
PAI_SOURCE_SYSTEM = "PAI"
PAI_SUPPORTED_EXCEL_SUFFIXES = (".xls", ".xlsx", ".xlsm")
SSA_IMPORT_REQUIRED_COLUMNS = ("numero_ssa", "data_cadastro", "descricao_ssa")


@dataclass(frozen=True)
class PaiXlsxNormalizationResult:
    path: Path
    row_count: int


@dataclass
class ManagedPaiXlsxNormalization:
    path: Path
    row_count: int
    keep_file: bool = False

    def preserve(self) -> None:
        self.keep_file = True


@contextmanager
def managed_pai_xlsx_for_ssa_import(
    source_xlsx: Path,
    target_xlsx: Path,
) -> Iterator[ManagedPaiXlsxNormalization]:
    result = normalize_pai_xlsx_for_ssa_import(source_xlsx, target_xlsx)
    managed = ManagedPaiXlsxNormalization(
        path=result.path,
        row_count=result.row_count,
    )
    try:
        yield managed
    finally:
        if not managed.keep_file:
            _remove_normalized_xlsx(managed.path)


def normalize_pai_xlsx_for_ssa_import(
    source_xlsx: Path,
    target_xlsx: Path,
) -> PaiXlsxNormalizationResult:
    source_xlsx = Path(source_xlsx)
    target_xlsx = Path(target_xlsx)
    _validate_source_excel_path(source_xlsx)
    frame = pd.read_excel(source_xlsx)
    normalized = build_normalized_pai_dataframe(frame)
    _add_pai_origin_metadata(normalized, source_xlsx)
    target_xlsx.parent.mkdir(parents=True, exist_ok=True)
    normalized.to_excel(target_xlsx, index=False)
    return PaiXlsxNormalizationResult(path=target_xlsx, row_count=len(normalized))


def build_normalized_pai_dataframe(frame: pd.DataFrame) -> pd.DataFrame:
    normalized = pd.DataFrame()
    for source_column, target_column in PAI_TO_SSA_COLUMN_MAP:
        if source_column not in frame.columns:
            continue
        if target_column in normalized.columns:
            normalized[target_column] = normalized[target_column].combine_first(
                frame[source_column]
            )
        else:
            normalized[target_column] = frame[source_column]
    normalized["data_cadastro"] = _format_datetime_without_timezone_for_ssa_import(
        _first_available_column(frame, PAI_DATE_SOURCE_COLUMNS)
    )
    normalized["situacao"] = _first_available_column(frame, PAI_SITUACAO_SOURCE_COLUMNS)
    _clean_normalized_text_columns(normalized)
    missing_required = [
        column
        for column in SSA_IMPORT_REQUIRED_COLUMNS
        if column not in normalized.columns
    ]
    if missing_required:
        raise ValueError(
            "XLSX PAI sem colunas obrigatorias para importacao SSA: "
            + ", ".join(missing_required)
        )
    empty_required = [
        column
        for column in SSA_IMPORT_REQUIRED_COLUMNS
        if normalized[column].isna().all()
    ]
    if empty_required:
        raise ValueError(
            "XLSX PAI com colunas obrigatorias sem nenhum valor valido para "
            "importacao SSA: "
            + ", ".join(empty_required)
        )
    return normalized


def default_ssa_import_xlsx_path(source_xlsx: Path) -> Path:
    source_xlsx = Path(source_xlsx)
    return source_xlsx.with_name(f"{source_xlsx.stem}{PAI_SSA_IMPORT_SUFFIX}.xlsx")


def _first_available_column(frame: pd.DataFrame, columns: tuple[str, ...]) -> pd.Series:
    present_columns = [column for column in columns if column in frame.columns]
    if not present_columns:
        return pd.Series([pd.NA] * len(frame), index=frame.index)
    result = frame[present_columns[0]]
    for column in present_columns[1:]:
        result = result.combine_first(frame[column])
    return result


def _format_datetime_without_timezone_for_ssa_import(series: pd.Series) -> pd.Series:
    parsed = pd.to_datetime(series, errors="coerce", utc=True)
    formatted = parsed.dt.tz_convert(None).dt.strftime("%Y-%m-%d %H:%M:%S")
    return formatted.where(parsed.notna(), pd.NA)


def _clean_normalized_text_columns(frame: pd.DataFrame) -> None:
    for column in frame.columns:
        if frame[column].dtype != "object":
            continue
        text_mask = frame[column].map(lambda value: isinstance(value, str))
        if not bool(text_mask.any()):
            continue
        stripped = frame.loc[text_mask, column].str.strip()
        frame.loc[text_mask, column] = stripped.mask(stripped.eq(""), pd.NA)


def _validate_source_excel_path(path: Path) -> None:
    if not path.is_file():
        raise FileNotFoundError(f"XLS PAI nao encontrado: {path}")
    if path.suffix.casefold() not in PAI_SUPPORTED_EXCEL_SUFFIXES:
        supported = ", ".join(PAI_SUPPORTED_EXCEL_SUFFIXES)
        raise ValueError(f"Arquivo PAI deve ser Excel ({supported}): {path}")


def _add_pai_origin_metadata(frame: pd.DataFrame, source_xlsx: Path) -> None:
    frame["sistema_origem"] = PAI_SOURCE_SYSTEM
    frame["arquivo_origem"] = source_xlsx.name


def _remove_normalized_xlsx(path: Path) -> None:
    try:
        path.unlink(missing_ok=True)
    except OSError:
        return
