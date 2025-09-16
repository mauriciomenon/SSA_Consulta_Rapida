"""Utilidades compartilhadas para normalização de numero_ssa.

Objetivos:
 - Centralizar a lógica (evitando divergências entre módulos de upsert, validação e integridade)
 - Reutilizar a função já consolidada em ``core.numero_ssa.normalize_strict``
 - Fornecer conversão para inteiro (quando aplicável) usada por caminhos legados

API Pública (estável):
 - normalize_numero_ssa_strict(value) -> str | None
 - normalize_numero_ssa_int(value) -> int | None  (apenas se exatamente 9 dígitos e ano válido)
 - batch_normalize_series(series) -> pd.Series (str|None)  preservando índices

Motivação:
 Os arquivos gigantes introduzidos anteriormente duplicaram esta lógica várias vezes.
 Este módulo substitui essas cópias. Durante a refatoração, chamadas internas serão
 redirecionadas para cá.
"""
from __future__ import annotations

from typing import Iterable
import re
import pandas as pd  # type: ignore[import-not-found]

from core.numero_ssa import normalize_strict as _strict  # fonte única de verdade

NUMERO_SSA_LEN = 9
NUMERO_SSA_ANO_MIN = 1980
NUMERO_SSA_ANO_MAX = 2050

__all__ = [
    # núcleo strict
    "normalize_numero_ssa_strict",
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


def normalize_numero_ssa(value) -> str | None:  # noqa: PLR0911
    """Replica regra legacy de exibição (padding / prefixos).

    Mantida aqui para centralizar e permitir que `database.py` apenas reexporte.
    """
    if value is None:
        return None
    raw = re.sub(r"\D", "", str(value))
    if not raw:
        return None
    trimmed = raw.lstrip('0')
    if not trimmed:
        return None
    n_trim = len(trimmed)
    if n_trim <= 5:
        return "2025" + trimmed.zfill(5)
    if n_trim == 7 and trimmed.startswith(("21", "22", "23", "24", "25")):
        return "20" + trimmed
    if len(raw) < 9:
        return raw.zfill(9)
    if len(raw) > 9:
        return raw[:9]
    return raw


def normalize_numero_ssa_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    if 'numero_ssa' not in df.columns:
        return df
    out = df.copy()
    out['numero_ssa'] = pd.Series([
        _normalize_numero_ssa_value(v) for v in out['numero_ssa']
    ], dtype='object')
    return out
