"""
utils/formatting.py

Regras de formatação compartilhadas entre CLI/GUI:
- Não exibir .0 (floats integrais viram inteiros)
- Não exibir NaN/NaT/None (vira string vazia, a CLI pode mapear para "-")
- Datas como dia/mês/ano (dd/mm/YYYY)
- Colunas de semana como inteiros
- numero_ssa como string canônica de 9 dígitos quando possível
"""
from __future__ import annotations

import math
from datetime import date, datetime
import re
from typing import Optional

import pandas as pd

try:
    # Evita import circular em tempo de import; usado apenas quando necessário
    from armazenamento.database import normalize_numero_ssa as _normalize_ssa_str
except Exception:
    _normalize_ssa_str = None  # fallback seguro


def _is_nullish(v) -> bool:
    if v is None:
        return True
    try:
        # Trata NaN/NaT
        if isinstance(v, float) and math.isnan(v):
            return True
        if isinstance(v, pd.Timestamp) and pd.isna(v):
            return True
        if isinstance(v, (pd.NaT.__class__,)):
            return True
        if isinstance(v, str) and v.strip().lower() in {"", "nan", "nat", "none", "null"}:
            return True
    except Exception:
        pass
    return False


def _format_number(v) -> str:
    # Inteiros
    if isinstance(v, (int,)) and not isinstance(v, bool):
        return str(v)
    # Floats
    if isinstance(v, float):
        if math.isnan(v):
            return ""
        # Se for integral, mostra como inteiro
        if abs(v - round(v)) < 1e-9:
            return str(int(round(v)))
        # Caso contrário, usa formato compacto sem zeros à direita excessivos
        s = ("%g" % v)
        return s
    # Pandas tipos numéricos
    if isinstance(v, (pd.Int64Dtype, pd.Float64Dtype)):
        try:
            return _format_number(v.item())
        except Exception:
            return str(v)
    return str(v)


def _format_date_like(v) -> str:
    if isinstance(v, pd.Timestamp):
        if pd.isna(v):
            return ""
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
            elif re.match(r"^\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}:\d{2}$", s):
                ts = pd.to_datetime(s, format="%Y-%m-%d %H:%M:%S", errors="coerce")
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

    # numero_ssa: 9 dígitos para exibição, se possível
    if column == "numero_ssa":
        if _normalize_ssa_str is not None:
            try:
                s = _normalize_ssa_str(value)
                return s or ""
            except Exception:
                pass
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


def format_dataframe_for_display(df: pd.DataFrame) -> pd.DataFrame:
    """Retorna uma cópia formatada pronta para exibição (valores já como strings)."""
    if df is None or df.empty:
        return df.copy()
    out = df.copy()
    for col in out.columns:
        out[col] = out[col].apply(lambda v, c=col: format_cell(v, c))
    return out
