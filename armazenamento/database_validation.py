"""Validação de DataFrames extraída de `database.py`."""
from __future__ import annotations

from typing import Any
import logging
import pandas as pd  # type: ignore[import-not-found]

from .numero_ssa_utils import _normalize_numero_ssa_value

logger = logging.getLogger(__name__)

MAX_TEXT_LEN = 1000


def validate_dataframe_before_insert(df: pd.DataFrame, table_name: str = 'ssas') -> dict[str, Any]:  # noqa: PLR0912, PLR0915
    report: dict[str, Any] = {
        'is_valid': True,
        'issues': [],
        'warnings': [],
        'row_count': len(df),
        'invalid_rows': [],
        'fixed_rows': 0,
        'table_name': table_name,
    }
    try:
        if df.empty:
            report['warnings'].append("DataFrame vazio - nada para validar")
            return report
        # Checagem de nulos essenciais
        for col in [c for c in ['numero_ssa', 'situacao'] if c in df.columns]:
            null_count = df[col].isnull().sum()
            if null_count > 0:
                report['warnings'].append(f"Coluna '{col}' tem {null_count} valores nulos")
        if 'numero_ssa' in df.columns:
            invalid_ssa_mask = df['numero_ssa'].apply(lambda x: _normalize_numero_ssa_value(x) is None if pd.notna(x) else True)
            invalid_count = invalid_ssa_mask.sum()
            if invalid_count > 0:
                report['warnings'].append(f"{invalid_count} números SSA inválidos encontrados")
                report['invalid_rows'].extend(df[invalid_ssa_mask].index.tolist())
        # Datas básicas
        date_cols = [c for c in ['data_cadastro', 'prazo_limite', 'data_limite'] if c in df.columns]
        for col in date_cols:
            try:
                parsed = pd.to_datetime(df[col], errors='coerce', dayfirst=True)
                invalid_mask = parsed.isna() & df[col].notna() & (df[col] != '')
                invalid_dates = invalid_mask.sum()
                if invalid_dates:
                    report['warnings'].append(f"Coluna '{col}' tem {invalid_dates} datas inválidas")
                    report['invalid_rows'].extend([i for i in df.index[invalid_mask] if i not in report['invalid_rows']])
            except Exception:  # pragma: no cover
                report['warnings'].append(f"Falha ao validar datas em '{col}'")
        if 'numero_ssa' in df.columns:
            valid_ssa_df = df[df['numero_ssa'].notna()]
            if not valid_ssa_df.empty:
                duplicated_ssa = valid_ssa_df.duplicated(subset=['numero_ssa'], keep=False)  # type: ignore[arg-type]
                duplicate_count = duplicated_ssa.sum()
                if duplicate_count > 0:
                    report['warnings'].append(f"{duplicate_count} números SSA duplicados encontrados")
        # Tamanho de texto
        for col in [c for c in ['descricao_ssa', 'descricao_execucao', 'solicitante'] if c in df.columns]:
            long_mask = df[col].astype(str).str.len() > MAX_TEXT_LEN
            long_count = long_mask.sum()
            if long_count:
                report['warnings'].append(
                    f"Coluna '{col}' tem {long_count} valores muito longos (>{MAX_TEXT_LEN} chars)"
                )
        report['is_valid'] = not report['issues']
        logger.info(
            "Validação concluída: %s linhas, %s problemas críticos, %s avisos",
            report['row_count'],
            len(report['issues']),
            len(report['warnings']),
        )
    except Exception as e:  # pragma: no cover
        report['issues'].append(f"Erro na validação: {e}")
        report['is_valid'] = False
        logger.error("Erro na validação do DataFrame: %s", e)
    return report
