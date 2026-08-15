"""
utils/formatting.py

Regras de formatação compartilhadas entre CLI/GUI:
- Não exibir .0 (floats integrais viram inteiros)
- Não exibir NaN/NaT/None (vira string vazia, a CLI pode mapear para "-")
- Datas como dia/mês/ano (dd/mm/YYYY)
- Colunas de semana como inteiros
- numero_ssa como string canonica de 9 digitos somente quando valido
"""

from __future__ import annotations

import math
import re
from datetime import date, datetime
from typing import Optional

import pandas as pd

from armazenamento.numero_ssa_utils import normalize_numero_ssa as _normalize_ssa_str


def _is_nullish(v) -> bool:
    if v is None:
        return True
    if v is pd.NA:
        return True
    try:
        if pd.isna(v):
            return True
    except TypeError:
        return False
    except ValueError:
        return False
    if isinstance(v, float) and math.isnan(v):
        return True
    if isinstance(v, pd.Timestamp) and pd.isna(v):
        return True
    if isinstance(v, (pd.NaT.__class__,)):
        return True
    if isinstance(v, str) and v.strip().lower() in {"", "nan", "nat", "none", "null"}:
        return True
    return False


def _format_number(v) -> str:
    if _is_nullish(v):
        return ""
    # Inteiros
    if isinstance(v, (int,)) and not isinstance(v, bool):
        return str(v)
    # Floats
    if isinstance(v, float):
        # Se for integral, mostra como inteiro
        if abs(v - round(v)) < 1e-9:
            return str(int(round(v)))
        # Caso contrário, usa formato compacto sem zeros à direita excessivos
        s = "%g" % v
        return s
    return str(v)


def _format_date_like(v) -> str:
    if _is_nullish(v):
        return ""
    if isinstance(v, pd.Timestamp):
        return v.strftime("%d/%m/%Y")
    if isinstance(v, datetime):
        return v.strftime("%d/%m/%Y")
    if isinstance(v, date):
        return v.strftime("%d/%m/%Y")
    # Tenta converter strings comuns com heurística para evitar warnings
    try:
        if isinstance(v, str):
            s = v.strip()
            # ISO-like YYYY-MM-DD
            if re.match(r"^\d{4}-\d{2}-\d{2}$", s):
                ts = pd.to_datetime(s, format="%Y-%m-%d", errors="coerce")
            # ISO-like with time YYYY-MM-DD HH:MM:SS or with 'T'
            elif re.match(
                r"^\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}:\d{2}"
                r"(\.\d+)?(Z|[+-]\d{2}:?\d{2})?$",
                s,
            ):
                ts = pd.to_datetime(
                    s.replace("T", " "),
                    errors="coerce",
                )
            else:
                ts = pd.to_datetime(s, errors="coerce", dayfirst=True)
        else:
            ts = pd.to_datetime(v, errors="coerce", dayfirst=True)
        if pd.isna(ts):
            return ""
        return ts.strftime("%d/%m/%Y")
    except Exception:
        return str(v)


def format_cell(value, column: Optional[str] = None) -> str:
    """Formata um único valor seguindo as regras acima."""
    if _is_nullish(value):
        return ""

    # numero_ssa: exibe apenas o valor canonico valido
    if column == "numero_ssa":
        if _normalize_ssa_str is not None:
            try:
                s = _normalize_ssa_str(value)
                return s or ""
            except Exception:
                return str(value)
        return str(value)

    # Colunas que parecem data
    if column and ("data" in column.lower() or column.lower().startswith("dt_")):
        return _format_date_like(value)

    # Colunas de semana -> inteiros se possível
    if column and column.lower().startswith("semana"):
        try:
            if isinstance(value, float) and not math.isnan(value):
                value = int(round(value))
            return _format_number(value)
        except Exception:
            return _format_number(value)

    # Números em geral
    if isinstance(value, (int, float)):
        return _format_number(value)

    # Timestamps
    if isinstance(value, (pd.Timestamp, datetime, date)):
        return _format_date_like(value)

    # Strings genéricas: retorna como está (CLI pode higienizar)
    return str(value)


def _format_dataframe_with(df: pd.DataFrame, formatter) -> pd.DataFrame:
    if df is None or df.empty:
        return df.copy()
    out = df.copy()
    for col in out.columns:
        out[col] = out[col].apply(lambda v, c=col: formatter(v, c))
    return out


def format_dataframe_for_display(df: pd.DataFrame) -> pd.DataFrame:
    """Retorna uma cópia formatada pronta para exibição (valores já como strings)."""
    return _format_dataframe_with(df, format_cell)


def format_table_cell(value, column: Optional[str] = None) -> str:
    text = format_cell(value, column)
    if "\n" in text or "\r" in text:
        text = " ".join(text.split())
    return text.replace("\\n", " ").replace("\\r", " ")


def format_dataframe_for_table_display(df: pd.DataFrame) -> pd.DataFrame:
    """Retorna copia formatada e normalizada para celulas de tabela GUI."""
    return _format_dataframe_with(df, format_table_cell)
