"""Normalize PAI XLSX exports into the SSA import schema."""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
import errno
import logging
import os
from pathlib import Path
import time
from typing import Iterator

import pandas as pd
from core.pai_xlsx_summary import PaiXlsxSummary
from core.pai_xlsx_summary import summarize_normalized_pai_frame

PAI_TO_SSA_COLUMN_CANDIDATES: dict[str, tuple[str, ...]] = {
    "numero_ssa": ("ssa_number", "numero_ssa"),
    "localizacao_codigo": ("localization", "localizacao_codigo"),
    "descricao_ssa": ("description", "descricao_ssa"),
    "semana_cadastro": ("year_week", "semana_cadastro"),
    "setor_emissor": ("emitter_sector", "setor_emissor"),
    "setor_executor": ("executor_sector", "setor_executor"),
}
PAI_DATE_SOURCE_COLUMNS = ("emission_datetime", "issue_datetime")
PAI_SITUACAO_SOURCE_COLUMNS = ("situation_desc", "process_status")
PAI_SSA_IMPORT_SUFFIX = "_ssa_import"
PAI_SOURCE_SYSTEM = "PAI"
_WINDOWS_REPLACE_XLSX_ATTEMPTS = 8
_WINDOWS_REPLACE_RETRY_ERRNOS = {errno.EACCES, errno.EPERM}
PAI_SUPPORTED_EXCEL_SUFFIXES = (".xls", ".xlsx", ".xlsm")
SSA_IMPORT_REQUIRED_COLUMNS = ("numero_ssa", "data_cadastro", "descricao_ssa")
logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class PaiXlsxNormalizationResult:
    path: Path
    row_count: int
    summary: PaiXlsxSummary


@dataclass
class ManagedPaiXlsxNormalization:
    """Data yielded by managed_pai_xlsx_for_ssa_import."""

    path: Path
    row_count: int
    summary: PaiXlsxSummary
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
        summary=result.summary,
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
    try:
        frame = pd.read_excel(source_xlsx)
    except (OSError, ValueError) as exc:
        raise ValueError(f"Falha ao ler XLSX PAI '{source_xlsx}': {exc}") from exc
    normalized = build_normalized_pai_dataframe(frame)
    _add_pai_origin_metadata(normalized, source_xlsx)
    summary = summarize_normalized_pai_frame(normalized)
    target_xlsx.parent.mkdir(parents=True, exist_ok=True)
    temp_xlsx = target_xlsx.with_name(f".{target_xlsx.name}.tmp")
    try:
        if temp_xlsx.exists():
            temp_xlsx.unlink()
        normalized.to_excel(temp_xlsx, index=False)
        _replace_xlsx_with_retry(temp_xlsx, target_xlsx)
    except Exception:
        if temp_xlsx.exists():
            temp_xlsx.unlink()
        raise
    return PaiXlsxNormalizationResult(
        path=target_xlsx,
        row_count=len(normalized),
        summary=summary,
    )


def _replace_xlsx_with_retry(source: Path, target: Path) -> None:
    if os.name != "nt":
        os.replace(source, target)
        return

    for attempt in range(_WINDOWS_REPLACE_XLSX_ATTEMPTS):
        try:
            os.replace(source, target)
            return
        except OSError as exc:
            retry_locked_target = (
                exc.errno in _WINDOWS_REPLACE_RETRY_ERRNOS
                and attempt < _WINDOWS_REPLACE_XLSX_ATTEMPTS - 1
            )
            if not retry_locked_target:
                raise
            logger.debug(
                "Retrying locked PAI XLSX replace attempt %s/%s for '%s' -> '%s': errno=%s error=%s",
                attempt + 1,
                _WINDOWS_REPLACE_XLSX_ATTEMPTS,
                source,
                target,
                exc.errno,
                exc,
            )
            time.sleep(min(1.0, 0.1 * (2**attempt)))


def build_normalized_pai_dataframe(frame: pd.DataFrame) -> pd.DataFrame:
    normalized_columns: dict[str, pd.Series] = {}
    for target_column, source_columns in PAI_TO_SSA_COLUMN_CANDIDATES.items():
        present_columns = tuple(column for column in source_columns if column in frame.columns)
        if present_columns:
            source = _coalesce_columns(frame, present_columns)
            normalized_columns[target_column] = source
    normalized_columns["data_cadastro"] = _format_datetime_as_utc_naive_for_ssa_import(
        _coalesce_columns(frame, PAI_DATE_SOURCE_COLUMNS)
    )
    normalized_columns["situacao"] = _coalesce_columns(
        frame, PAI_SITUACAO_SOURCE_COLUMNS
    )
    normalized = pd.DataFrame(normalized_columns, index=frame.index)
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
        if column in normalized.columns and normalized[column].isna().all()
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


def _coalesce_columns(frame: pd.DataFrame, columns: tuple[str, ...]) -> pd.Series:
    present_columns = [column for column in columns if column in frame.columns]
    if not present_columns:
        return pd.Series([pd.NA] * len(frame), index=frame.index)
    return frame[present_columns].bfill(axis=1).iloc[:, 0]


def _format_datetime_as_utc_naive_for_ssa_import(series: pd.Series) -> pd.Series:
    """Normalize PAI timestamps to UTC and emit SSA-compatible naive text."""
    parsed = pd.to_datetime(series, errors="coerce", utc=True)
    formatted = parsed.dt.tz_convert(None).dt.strftime("%Y-%m-%d %H:%M:%S")
    return formatted.where(parsed.notna(), pd.NA)


def _clean_normalized_text_columns(frame: pd.DataFrame) -> None:
    for column in frame.select_dtypes(include=("object", "string")).columns:
        series = frame[column]
        if str(series.dtype) != "string":
            series = series.astype("string")
        stripped = series.str.strip()
        frame[column] = stripped.mask(stripped.eq(""), pd.NA)


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
    except OSError as exc:
        logger.warning("Falha ao remover XLSX PAI temporario '%s': %s", path, exc)
