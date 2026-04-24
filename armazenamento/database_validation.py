"""Validacao de DataFrames extraida de `database.py`."""

from __future__ import annotations

from typing import Any

import pandas as pd

from utils.robust_logging import get_robust_logger

from shared.date_utils import parse_any_date
from shared.db_names import CANONICAL_SSA_TABLE
from shared.import_contract import (
    ALLOWED_MISSING_DATA_CADASTRO_STATUSES,
    VALIDATION_REQUIRED_COLUMNS,
)

from .numero_ssa_utils import normalize_numero_ssa_storage

logger = get_robust_logger().get_logger(__name__, "core")

MAX_TEXT_LEN = 1000


def _sample_ssas(df: pd.DataFrame, mask: Any) -> list[str]:
    if "numero_ssa" not in df.columns:
        return []
    return df.loc[mask, "numero_ssa"].astype(str).head(5).tolist()


def _append_unique_invalid_rows(report: dict[str, Any], indices: list[Any]) -> None:
    seen_rows = report.setdefault("_invalid_row_seen", set())
    for idx in indices:
        if idx not in seen_rows:
            report["invalid_rows"].append(idx)
            seen_rows.add(idx)


def _rows_are_exact_duplicates(group: pd.DataFrame) -> bool:
    comparison_columns = [col for col in group.columns if col != "numero_ssa_canonical"]
    if not comparison_columns:
        return True
    base_row = group[comparison_columns].iloc[0]
    for row_idx in range(1, len(group)):
        if not group[comparison_columns].iloc[row_idx].equals(base_row):
            return False
    return True


def _validate_required_columns(df: pd.DataFrame, report: dict[str, Any]) -> None:
    # Severidades:
    # - numero_ssa: warning (linhas sem/invalidas devem gerar aviso, nao invalidar o lote)
    # - data_cadastro: error (critico para ordenacao/relatorios)
    # - situacao: warning (ausencia nao impede insercao)
    situacao_upper = None
    if "situacao" in df.columns:
        situacao_upper = df["situacao"].astype(str).str.strip().str.upper()
    for column, severity in VALIDATION_REQUIRED_COLUMNS:
        if column not in df.columns:
            all_rows_mask = pd.Series([True] * len(df), index=df.index)
            report["violations"].append(
                {
                    "rule": f"missing_column_{column}",
                    "column": column,
                    "severity": severity,
                    "count": int(len(df)),
                    "sample_ssa": _sample_ssas(df, all_rows_mask),
                }
            )
            target = report["issues"] if severity == "error" else report["warnings"]
            target.append(f"Coluna obrigatoria '{column}' ausente no DataFrame")
            continue
        series = df[column]
        missing_mask = series.isna() | (series.astype(str).str.strip() == "")
        # Business exception: these statuses can legitimately have no emit date.
        if column == "data_cadastro" and situacao_upper is not None:
            missing_mask = missing_mask & (
                ~situacao_upper.isin(ALLOWED_MISSING_DATA_CADASTRO_STATUSES)
            )
        missing_count = int(missing_mask.sum())
        if missing_count == 0:
            continue
        report["violations"].append(
            {
                "rule": f"missing_{column}",
                "column": column,
                "severity": severity,
                "count": missing_count,
                "sample_ssa": _sample_ssas(df, missing_mask),
            }
        )
        target = report["issues"] if severity == "error" else report["warnings"]
        target.append(f"Coluna '{column}' possui {missing_count} valores ausentes")
        indices = df.index[missing_mask].tolist()
        report["invalid_by_column"][column] = indices
        _append_unique_invalid_rows(report, indices)


def _validate_numero_ssa(df: pd.DataFrame, report: dict[str, Any]) -> None:
    if "numero_ssa" not in df.columns:
        return
    normalized_ssa = df["numero_ssa"].map(normalize_numero_ssa_storage)
    invalid_ssa_mask = normalized_ssa.isna()
    invalid_count = int(invalid_ssa_mask.sum())
    if invalid_count == 0:
        return
    report["warnings"].append(f"{invalid_count} numeros SSA invalidos encontrados")
    invalid_indices = df[invalid_ssa_mask].index.tolist()
    report["invalid_by_column"]["numero_ssa"] = invalid_indices
    _append_unique_invalid_rows(report, invalid_indices)
    report["violations"].append(
        {
            "rule": "invalid_numero_ssa",
            "column": "numero_ssa",
            "severity": "warning",
            "count": invalid_count,
            "sample_ssa": _sample_ssas(df, invalid_ssa_mask),
        }
    )


def _validate_date_columns(df: pd.DataFrame, report: dict[str, Any]) -> None:
    date_cols = [
        c
        for c in [
            "data_cadastro",
            "prazo_limite",
            "data_limite",
            "ate",
            "ate_1",
            "ate_2",
            "desde",
            "desde_1",
            "desde_2",
            "data_inicio_programada",
            "data_programacao",
            "data_inicio_reprogramada",
            "data_reprogramacao",
            "instalacao_estimada",
            "executado",
            "concluido",
        ]
        if c in df.columns
    ]
    for col in date_cols:
        try:
            series = df[col]
            parsed_text = series.map(parse_any_date)
            parsed = pd.to_datetime(parsed_text, errors="coerce")
            invalid_mask = parsed.isna() & series.notna() & (series != "")
            invalid_dates = invalid_mask.sum()
            if invalid_dates:
                report["warnings"].append(
                    f"Coluna '{col}' tem {invalid_dates} datas invalidas"
                )
                report["violations"].append(
                    {
                        "rule": f"invalid_{col}",
                        "column": col,
                        "severity": "warning",
                        "count": int(invalid_dates),
                        "sample_ssa": _sample_ssas(df, invalid_mask),
                    }
                )
                _append_unique_invalid_rows(report, df.index[invalid_mask].tolist())
        except Exception as e:  # pragma: no cover
            report["warnings"].append(
                f"Falha ao validar datas em '{col}' ({type(e).__name__}): {e}"
            )
            logger.warning(
                "Falha ao validar coluna de data '%s' (%s): %s",
                col,
                type(e).__name__,
                e,
            )


def _validate_duplicate_ssa(df: pd.DataFrame, report: dict[str, Any]) -> None:
    if "numero_ssa" not in df.columns:
        return
    canonical_ssa = df["numero_ssa"].map(normalize_numero_ssa_storage)
    valid_ssa_df = df.loc[canonical_ssa.notna()].copy()
    if valid_ssa_df.empty:
        return
    valid_ssa_df["numero_ssa_canonical"] = canonical_ssa.loc[valid_ssa_df.index]
    duplicated_ssa = valid_ssa_df.duplicated(
        subset=["numero_ssa_canonical"], keep=False
    )
    duplicate_count = int(duplicated_ssa.sum())
    if duplicate_count == 0:
        return

    exact_duplicate_indices: list[int] = []
    conflicting_duplicate_indices: list[int] = []
    duplicate_groups = valid_ssa_df.loc[duplicated_ssa].groupby(
        "numero_ssa_canonical", sort=False, dropna=False
    )
    for _, group in duplicate_groups:
        if _rows_are_exact_duplicates(group):
            exact_duplicate_indices.extend(group.index.tolist())
        else:
            conflicting_duplicate_indices.extend(group.index.tolist())

    if exact_duplicate_indices:
        exact_mask = valid_ssa_df.index.isin(exact_duplicate_indices)
        exact_count = int(exact_mask.sum())
        report["warnings"].append(
            f"{exact_count} numeros SSA duplicados identicos encontrados"
        )
        report["violations"].append(
            {
                "rule": "duplicate_numero_ssa_exact",
                "column": "numero_ssa",
                "severity": "warning",
                "count": exact_count,
                "sample_ssa": _sample_ssas(valid_ssa_df, exact_mask),
            }
        )

    if conflicting_duplicate_indices:
        conflicting_mask = valid_ssa_df.index.isin(conflicting_duplicate_indices)
        conflicting_count = int(conflicting_mask.sum())
        report["warnings"].append(
            f"{conflicting_count} numeros SSA duplicados conflitantes encontrados"
        )
        report["violations"].append(
            {
                "rule": "duplicate_numero_ssa_conflict",
                "column": "numero_ssa",
                "severity": "warning",
                "count": conflicting_count,
                "sample_ssa": _sample_ssas(valid_ssa_df, conflicting_mask),
            }
        )


def _validate_text_columns(df: pd.DataFrame, report: dict[str, Any]) -> None:
    for col in [
        c
        for c in ["descricao_ssa", "descricao_execucao", "solicitante"]
        if c in df.columns
    ]:
        long_mask = df[col].astype(str).str.len() > MAX_TEXT_LEN
        long_count = long_mask.sum()
        if long_count:
            report["warnings"].append(
                f"Coluna '{col}' tem {long_count} valores muito longos (>{MAX_TEXT_LEN} chars)"
            )
            report["violations"].append(
                {
                    "rule": f"text_too_long_{col}",
                    "column": col,
                    "severity": "warning",
                    "count": int(long_count),
                    "sample_ssa": _sample_ssas(df, long_mask),
                }
            )


def validate_dataframe_before_insert(
    df: pd.DataFrame,
    table_name: str = CANONICAL_SSA_TABLE,
) -> dict[str, Any]:
    report: dict[str, Any] = {
        "is_valid": True,
        "issues": [],
        "warnings": [],
        "row_count": len(df),
        "invalid_rows": [],
        "_invalid_row_seen": set(),
        "fixed_rows": 0,
        "table_name": table_name,
        "violations": [],
        "invalid_by_column": {},
    }
    try:
        if df.empty:
            report["warnings"].append("DataFrame vazio - nada para validar")
            report.pop("_invalid_row_seen", None)
            return report

        _validate_required_columns(df, report)
        _validate_numero_ssa(df, report)
        _validate_date_columns(df, report)
        _validate_duplicate_ssa(df, report)
        _validate_text_columns(df, report)
        report["is_valid"] = not report["issues"]
        logger.info(
            "Validacao concluida: %s linhas, %s problemas criticos, %s avisos",
            report["row_count"],
            len(report["issues"]),
            len(report["warnings"]),
        )
        report.pop("_invalid_row_seen", None)
    except Exception as e:  # pragma: no cover
        report.pop("_invalid_row_seen", None)
        report["issues"].append(f"Erro na validacao ({type(e).__name__}): {e}")
        report["error_details"] = {
            "type": type(e).__name__,
            "message": str(e),
        }
        report["is_valid"] = False
        logger.exception("Erro na validacao do DataFrame: %s", e)
    return report
