"""Validação de DataFrames extraída de `database.py`."""

from __future__ import annotations

import logging
from typing import Any

import pandas as pd  # type: ignore[import-not-found]

from shared.date_utils import parse_any_date

from .numero_ssa_utils import _normalize_numero_ssa_value

logger = logging.getLogger(__name__)

MAX_TEXT_LEN = 1000


def validate_dataframe_before_insert(
    df: pd.DataFrame, table_name: str = "ssas"
) -> dict[str, Any]:  # noqa: PLR0912, PLR0915
    report: dict[str, Any] = {
        "is_valid": True,
        "issues": [],
        "warnings": [],
        "row_count": len(df),
        "invalid_rows": [],
        "fixed_rows": 0,
        "table_name": table_name,
        "violations": [],
        "invalid_by_column": {},
    }
    try:
        if df.empty:
            report["warnings"].append("DataFrame vazio - nada para validar")
            return report

        def _sample_ssas(mask) -> list[str]:
            if "numero_ssa" not in df.columns:
                return []
            return df.loc[mask, "numero_ssa"].astype(str).head(5).tolist()

        # Severidades:
        # - numero_ssa: warning (linhas sem/invalidas devem gerar aviso, nao invalidar o lote)
        # - data_cadastro: error (critico para ordenacao/relatorios)
        # - situacao: warning (ausencia nao impede insercao)
        required_columns = [
            ("numero_ssa", "warning"),
            ("data_cadastro", "error"),
            ("situacao", "warning"),
        ]
        for column, severity in required_columns:
            if column not in df.columns:
                continue
            series = df[column]
            missing_mask = series.isna() | (series.astype(str).str.strip() == "")
            missing_count = int(missing_mask.sum())
            if missing_count == 0:
                continue
            sample_ssas = _sample_ssas(missing_mask)
            violation = {
                "rule": f"missing_{column}",
                "column": column,
                "severity": severity,
                "count": missing_count,
                "sample_ssa": sample_ssas,
            }
            report["violations"].append(violation)
            target = report["issues"] if severity == "error" else report["warnings"]
            target.append(f"Coluna '{column}' possui {missing_count} valores ausentes")
            indices = df.index[missing_mask].tolist()
            report["invalid_by_column"][column] = indices
            for idx in indices:
                if idx not in report["invalid_rows"]:
                    report["invalid_rows"].append(idx)

        if "numero_ssa" in df.columns:
            invalid_ssa_mask = df["numero_ssa"].apply(
                lambda x: _normalize_numero_ssa_value(x) is None
                if pd.notna(x)
                else True
            )
            invalid_count = int(invalid_ssa_mask.sum())
            if invalid_count > 0:
                report["warnings"].append(
                    f"{invalid_count} números SSA inválidos encontrados"
                )
                report["invalid_rows"].extend(df[invalid_ssa_mask].index.tolist())
                report["violations"].append(
                    {
                        "rule": "invalid_numero_ssa",
                        "column": "numero_ssa",
                        "severity": "warning",
                        "count": invalid_count,
                        "sample_ssa": _sample_ssas(invalid_ssa_mask),
                    }
                )
        # Datas básicas
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
                parsed_text = series.apply(parse_any_date)
                parsed = pd.to_datetime(
                    parsed_text, errors="coerce", format="%Y-%m-%d %H:%M:%S"
                )
                invalid_mask = parsed.isna() & series.notna() & (series != "")
                invalid_dates = invalid_mask.sum()
                if invalid_dates:
                    report["warnings"].append(
                        f"Coluna '{col}' tem {invalid_dates} datas inválidas"
                    )
                    report["violations"].append(
                        {
                            "rule": f"invalid_{col}",
                            "column": col,
                            "severity": "warning",
                            "count": int(invalid_dates),
                            "sample_ssa": _sample_ssas(invalid_mask),
                        }
                    )
                    report["invalid_rows"].extend(
                        [
                            i
                            for i in df.index[invalid_mask]
                            if i not in report["invalid_rows"]
                        ]
                    )
            except Exception:  # pragma: no cover
                report["warnings"].append(f"Falha ao validar datas em '{col}'")
        if "numero_ssa" in df.columns:
            valid_ssa_df = df[df["numero_ssa"].notna()]
            if not valid_ssa_df.empty:
                duplicated_ssa = valid_ssa_df.duplicated(
                    subset=["numero_ssa"], keep=False
                )  # type: ignore[arg-type]
                duplicate_count = duplicated_ssa.sum()
                if duplicate_count > 0:
                    report["warnings"].append(
                        f"{duplicate_count} números SSA duplicados encontrados"
                    )
                    report["violations"].append(
                        {
                            "rule": "duplicate_numero_ssa",
                            "column": "numero_ssa",
                            "severity": "warning",
                            "count": int(duplicate_count),
                            "sample_ssa": _sample_ssas(duplicated_ssa),
                        }
                    )
        # Tamanho de texto
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
                        "sample_ssa": _sample_ssas(long_mask),
                    }
                )
        report["is_valid"] = not report["issues"]
        logger.info(
            "Validação concluída: %s linhas, %s problemas críticos, %s avisos",
            report["row_count"],
            len(report["issues"]),
            len(report["warnings"]),
        )
    except Exception as e:  # pragma: no cover
        report["issues"].append(f"Erro na validação: {e}")
        report["is_valid"] = False
        logger.error("Erro na validação do DataFrame: %s", e)
    return report
