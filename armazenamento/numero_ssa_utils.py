"""Utilidades compartilhadas para normalização de numero_ssa.

Objetivos:
 - Centralizar a lógica (evitando divergências entre módulos de upsert, validação e integridade)
 - Reutilizar a função já consolidada em ``core.numero_ssa.normalize_strict``
 - Fornecer conversão para inteiro (quando aplicável) usada por caminhos legados

API Pública (estável):
 - normalize_numero_ssa_strict(value) -> str | None
 - normalize_numero_ssa_int(value) -> int | None  (legado: corta para 9 digitos e valida ano)
 - batch_normalize_series(series) -> pd.Series (str|None)  preservando índices

Motivação:
 Os arquivos gigantes introduzidos anteriormente duplicaram esta lógica várias vezes.
 Este módulo substitui essas cópias. Durante a refatoração, chamadas internas serão
 redirecionadas para cá.
"""
from __future__ import annotations
import re
from typing import Iterable

import pandas as pd

from shared.numero_ssa import \
    normalize_numero_ssa as _normalize_numero_ssa_legacy
from shared.numero_ssa import \
    normalize_strict as _strict  # fonte unica de verdade

NUMERO_SSA_LEN = 9
NUMERO_SSA_ANO_MIN = 1980
NUMERO_SSA_ANO_MAX = 2050
_CANONICAL_DECIMAL_ARTIFACT = re.compile(r"^\s*(\d{9})\.0+\s*$")

__all__ = [
    # núcleo strict
    "normalize_numero_ssa_strict",
    "normalize_numero_ssa_storage",
    "normalize_numero_ssa_int",
    # nomes legados expostos (valor inteiro e formato display)
    "_normalize_numero_ssa_value",
    "normalize_numero_ssa",
    "normalize_numero_ssa_dataframe",
    # util de lote
    "batch_normalize_series",
]


def normalize_numero_ssa_strict(value) -> str | None:
    """Wrapper explícito para clareza sem expor ``_strict`` direto fora do módulo.

    Mantém compatibilidade sem duplicar implementação.
    """
    return _strict(value)


def _strip_canonical_decimal_artifact(value):
    """Collapse legacy Excel float artifacts for canonical 9-digit identifiers only."""
    if value is None:
        return None
    text = str(value).strip()
    match = _CANONICAL_DECIMAL_ARTIFACT.fullmatch(text)
    if match is None:
        return value
    return match.group(1)


def _contains_letters(value) -> bool:
    if value is None:
        return False
    try:
        return any(char.isalpha() for char in str(value))
    except Exception:  # pragma: no cover
        return False


def _normalize_numero_ssa_value(value) -> int | None:
    """Versão numérica (legado) com regra de corte para >9 dígitos.

    Comportamento exigido pelos testes legados:
      * Remove não dígitos.
      * Se tiver mais que 9 dígitos, usa apenas os primeiros 9.
      * Exige exatamente 9 dígitos após o eventual corte.
      * Ano deve estar dentro do intervalo permitido.
    (Regras adicionais de rejeição mais complexas ficam a cargo da versão strict
     quando chamada diretamente nos testes específicos.)
    """
    if value is None:
        return None
    try:
        digits = re.sub(r"\D", "", str(value))
    except Exception:  # pragma: no cover
        return None
    if not digits:
        return None
    if len(digits) > NUMERO_SSA_LEN:
        digits = digits[:NUMERO_SSA_LEN]
    if len(digits) != NUMERO_SSA_LEN:
        return None
    try:
        ano = int(digits[:4])
        if not (NUMERO_SSA_ANO_MIN <= ano <= NUMERO_SSA_ANO_MAX):
            return None
        return int(digits)
    except Exception:  # pragma: no cover
        return None


def normalize_numero_ssa_int(value) -> int | None:
    return _normalize_numero_ssa_value(value)


def normalize_numero_ssa_storage(value) -> str | None:
    """Return canonical storage form for numero_ssa as text."""
    strict_value = normalize_numero_ssa_strict(value)
    if strict_value is not None:
        return strict_value
    if _contains_letters(value):
        return None
    legacy_value = normalize_numero_ssa(value)
    if legacy_value is None:
        return None
    return normalize_numero_ssa_strict(legacy_value)


def normalize_numero_ssa(value) -> str | None:
    """Legacy display/storage helper with minimal decimal-artifact tolerance."""
    return _normalize_numero_ssa_legacy(_strip_canonical_decimal_artifact(value))


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


def bulk_int_or_none(values: Iterable) -> list[int | None]:  # pragma: no cover (usado esporadicamente)
    return [_normalize_numero_ssa_value(v) for v in values]


def normalize_numero_ssa_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    if 'numero_ssa' not in df.columns:
        return df
    out = df.copy()
    out['numero_ssa'] = pd.Series([
        normalize_numero_ssa_storage(v)
        for v in out['numero_ssa']
    ], dtype='object')
    return out
