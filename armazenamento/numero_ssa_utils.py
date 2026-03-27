"""Utilidades compartilhadas para normalizacao de numero_ssa.

Objetivos:
 - Centralizar a logica (evitando divergencias entre modulos de upsert, validacao e integridade)
 - Reutilizar a funcao ja consolidada em ``shared.numero_ssa.normalize_strict``
 - Fornecer conversao para inteiro e fachada retrocompativel para a API publica atual

API Publica (estavel):
 - normalize_numero_ssa_strict(value) -> str | None
 - normalize_numero_ssa_int(value) -> int | None
 - batch_normalize_series(series) -> pd.Series (str|None)  preservando índices

Motivacao:
 Os arquivos gigantes introduzidos anteriormente duplicaram esta logica varias vezes.
 Este modulo substitui essas copias. As facades publicas de compatibilidade
 continuam delegando para ca para evitar drift entre runtime, upsert e testes.
"""

from __future__ import annotations

import logging
import re
from typing import Iterable

import pandas as pd

from shared.numero_ssa import normalize_strict as _strict

NUMERO_SSA_LEN = 9
logger = logging.getLogger(__name__)

__all__ = [
    # núcleo strict
    "normalize_numero_ssa_strict",
    "normalize_numero_ssa_storage",
    "normalize_numero_ssa_int",
    # nomes publicos de compatibilidade
    "normalize_numero_ssa",
    "normalize_numero_ssa_dataframe",
    # util de lote
    "batch_normalize_series",
]


def normalize_numero_ssa_strict(value) -> str | None:
    """Wrapper explicito para clareza sem expor ``_strict`` direto fora do modulo.

    Mantem compatibilidade sem duplicar implementacao.
    """
    return _strict(value)


def normalize_numero_ssa_int(value) -> int | None:
    """Public integer normalization aligned with strict canonical validation."""
    if value is None:
        return None
    strict_value = normalize_numero_ssa_strict(value)
    if strict_value is None:
        return None
    try:
        return int(strict_value)
    except Exception:  # pragma: no cover
        return None


def normalize_numero_ssa_storage(value) -> str | None:
    """Return canonical storage form for numero_ssa as text."""
    return normalize_numero_ssa_strict(value)


def normalize_numero_ssa(value) -> str | None:
    """Compat wrapper alinhado ao mesmo contrato canonico de storage."""
    return normalize_numero_ssa_strict(value)


def batch_normalize_series(series: pd.Series) -> pd.Series:
    """Normaliza série de valores heterogêneos em representação strict (ou None).

    Preserva índice; retorna dtype=object para manter None sem conversão para NaN float.
    """
    normalized: list[str | None] = [normalize_numero_ssa_strict(v) for v in series]
    return pd.Series(normalized, index=series.index, dtype="object")


def extract_candidate_digits(value) -> str:
    """Extrai somente dígitos (uso eventual em heurísticas de limpeza prévia).

    Mantido separado para evitar micro duplicações se necessário em validação.
    """
    if value is None:
        return ""
    return re.sub(r"\D", "", str(value))


def bulk_int_or_none(
    values: Iterable,
) -> list[int | None]:  # pragma: no cover (usado esporadicamente)
    return [normalize_numero_ssa_int(v) for v in values]


def normalize_numero_ssa_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    if "numero_ssa" not in df.columns:
        return df
    out = df.copy()
    mapped = out["numero_ssa"].map(normalize_numero_ssa_storage)
    out["numero_ssa"] = mapped.astype("object").where(mapped.notna(), None)
    return out
