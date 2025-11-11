"""Importador robusto para planilhas Excel focado no básico exigido pelos testes.

Funcionalidades implementadas:
- Colapso de sinônimos de cabeçalho para nomes canônicos: numero_ssa, situacao, data_cadastro
- Coalescência linha a linha quando existem múltiplas colunas sinônimas
- Normalização estrita de numero_ssa via core.numero_ssa.normalize_strict
- Parsing de datas (ISO, dia/mês/ano e serial Excel) retornando string YYYY-MM-DD
- Deduplicação por numero_ssa mantendo a linha com data mais recente

API: import_excel_robust(file_path: str) -> tuple[pandas.DataFrame, dict]
"""
from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional, Tuple
import math
import unicodedata

import pandas as pd  # type: ignore[import-not-found]

from core.numero_ssa import normalize_strict

__all__ = ["import_excel_robust", "_clean_numero_ssa_series"]


# -------------------------
# Helpers de normalização
# -------------------------

def _strip_accents(s: str) -> str:
    nfkd = unicodedata.normalize("NFKD", s)
    return "".join(c for c in nfkd if not unicodedata.combining(c))


def _norm_header(name: Any) -> str:
    if name is None:
        return ""
    s = str(name).strip().lower()
    s = _strip_accents(s)
    # substitui pontuação por espaço e compacta
    cleaned = []
    for ch in s:
        if ch.isalnum():
            cleaned.append(ch)
        else:
            cleaned.append(" ")
    s = "".join(cleaned)
    s = " ".join(part for part in s.split() if part)
    return s


# Sinônimos (normalizados) -> canônicos
HEADER_SYNONYMS: Dict[str, str] = {}
for alias in [
    "nº ssa", "n° ssa", "n ssa", "nssa", "numero ssa", "número ssa", "número da ssa", "nº da ssa", "ssa", "nº",
]:
    HEADER_SYNONYMS[_norm_header(alias)] = "numero_ssa"
for alias in [
    "situacao", "situação", "status", "situaçao", "situaçâo",
]:
    HEADER_SYNONYMS[_norm_header(alias)] = "situacao"
for alias in [
    "emitida em", "data de emissao", "data de emissão", "data de cadastro", "data", "emissao", "emissão",
]:
    HEADER_SYNONYMS[_norm_header(alias)] = "data_cadastro"


def _first_nonempty(values: Iterable[Any]) -> Optional[Any]:
    for v in values:
        if v is None:
            continue
        if isinstance(v, float) and math.isnan(v):
            continue
        if isinstance(v, str) and v.strip() == "":
            continue
        return v
    return None


def _coalesce_columns(df: pd.DataFrame, cols: List[str]) -> pd.Series:
    if not cols:
        return pd.Series([None] * len(df), dtype="object")
    vals = []
    rows = df.to_dict("records")
    for row in rows:
        vals.append(_first_nonempty([row.get(c) for c in cols]))
    return pd.Series(vals, dtype="object")


def _to_str_without_decimal(val: Any) -> Optional[str]:
    if val is None:
        return None
    if isinstance(val, float):
        if math.isnan(val):
            return None
        if val.is_integer():
            return str(int(val))
        # número com casas não deve acontecer para numero_ssa; trata como bruto
        return str(val)
    if isinstance(val, int):
        return str(val)
    s = str(val).strip()
    return s if s != "" else None


def _clean_numero_ssa(value: Any) -> Optional[str]:
    s = _to_str_without_decimal(value)
    if s is None or s == "":
        return None
    try:
        normalized = normalize_strict(s)
    except Exception:
        return None
    return normalized


def _clean_numero_ssa_series(series: pd.Series) -> Tuple[pd.Series, pd.Series]:
    """Return (cleaned_series, valid_mask) applying normalize_strict per value.

    Invalid or blank values are set to pd.NA and False in mask.
    """
    cleaned: List[Optional[str]] = []
    mask: List[bool] = []
    for v in series.tolist():
        c = _clean_numero_ssa(v)
        if c is None:
            cleaned.append(pd.NA)  # type: ignore[arg-type]
            mask.append(False)
        else:
            cleaned.append(c)
            mask.append(True)
    return pd.Series(cleaned, dtype="object"), pd.Series(mask, dtype=bool)


def _parse_date(value: Any) -> Optional[str]:
    # retorna YYYY-MM-DD ou None
    if value is None:
        return None
    # strings vazias
    if isinstance(value, str):
        s = value.strip()
        if s == "":
            return None
        # Heurística: datas com '/' assumem dia/mês/ano (pt-BR)
        if "/" in s:
            ts = pd.to_datetime(s, errors="coerce", dayfirst=True)
        else:
            # Para ISO ou outros, tenta padrão e depois dia-first
            ts = pd.to_datetime(s, errors="coerce", dayfirst=False)
            if pd.isna(ts):
                ts = pd.to_datetime(s, errors="coerce", dayfirst=True)
        if pd.isna(ts):
            return None
        try:
            return ts.date().isoformat()
        except Exception:
            return None
    # Excel serial (float/int)
    if isinstance(value, (int, float)):
        if isinstance(value, float) and math.isnan(value):
            return None
        try:
            ts = pd.to_datetime(value, unit="D", origin="1899-12-30", errors="coerce")
            if pd.isna(ts):
                return None
            return ts.date().isoformat()
        except Exception:
            return None
    # qualquer outro tipo
    try:
        ts = pd.to_datetime(value, errors="coerce")
        if pd.isna(ts):
            return None
        return ts.date().isoformat()
    except Exception:
        return None


def import_excel_robust(file_path: str) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    # 1) carregar planilha
    df = pd.read_excel(file_path)

    # 2) mapear headers para canônicos
    groups: Dict[str, List[str]] = {}
    for col in df.columns:
        n = _norm_header(col)
        canonical = HEADER_SYNONYMS.get(n, n)
        groups.setdefault(canonical, []).append(col)

    # 3) coalescer colunas de interesse
    out_cols: Dict[str, pd.Series] = {}
    for canonical in ("numero_ssa", "situacao", "data_cadastro"):
        origs = groups.get(canonical, [])
        out_cols[canonical] = _coalesce_columns(df, origs)

    work = pd.DataFrame(out_cols)

    # 4) limpar numero_ssa e contar inválidos
    cleaned: List[Optional[str]] = []
    invalid_count = 0
    for v in work["numero_ssa"].tolist():
        c = _clean_numero_ssa(v)
        if c is None:
            invalid_count += 1
        cleaned.append(c)
    work["numero_ssa"] = pd.Series(cleaned, dtype="object")

    # remover linhas com numero_ssa vazio/None
    before_valid_filter = len(work)
    work = work[work["numero_ssa"].notna()].reset_index(drop=True)

    # 5) parse de datas + contagem de falhas
    parsed_dates: List[Optional[str]] = []
    date_failures = 0
    for v in work["data_cadastro"].tolist():
        parsed = _parse_date(v)
        # contabiliza falha quando havia valor não-vazio de fato
        had_value = not (
            v is None or (isinstance(v, str) and v.strip() == "") or (isinstance(v, float) and math.isnan(v))
        )
        if parsed is None and had_value:
            date_failures += 1
        parsed_dates.append(parsed)
    work["data_cadastro"] = pd.Series(parsed_dates, dtype="object")

    # 6) deduplicação por numero_ssa mantendo data mais recente
    before_dedup = len(work)
    if not work.empty:
        tmp = work.copy()
        tmp["_dt"] = pd.to_datetime(tmp["data_cadastro"], errors="coerce")
        tmp.sort_values(["numero_ssa", "_dt"], ascending=[True, False], inplace=True)
        tmp = tmp.drop_duplicates(subset=["numero_ssa"], keep="first").drop(columns=["_dt"])  # mantém data mais nova
        work = tmp.reset_index(drop=True)
    duplicate_rows_dropped = before_dedup - len(work)

    # garantir tipos coerentes (strings python ou None)
    work["numero_ssa"] = work["numero_ssa"].astype("string").where(work["numero_ssa"].notna(), None)
    work["situacao"] = work["situacao"].astype("string").where(work["situacao"].notna(), None)
    work["data_cadastro"] = work["data_cadastro"].astype("string").where(work["data_cadastro"].notna(), None)

    stats = {
        "duplicate_rows_dropped": int(duplicate_rows_dropped),
        "invalid_numero_ssa_rows": int(invalid_count),
        "date_parse_failures": {"data_cadastro": int(date_failures)},
    }

    return work, stats
