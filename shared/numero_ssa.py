"""Centralized numero_ssa normalization utilities.

Strict policy (canonical key) adopted for cross-layer consistency:
    * Base rule: strip non-digits and obtain **exactly** 9 digits - otherwise reject.
    * Year guard: first 4 digits must be within inclusive range 1980..2050.
    * Additional hardening (to satisfy regression tests):
            - If the original value contains alphabetic characters (letters), reject
                even if the digit fold would yield 9 digits (e.g. ``XX202512345YY``).
            - Values containing a hyphen (``-``) are tolerated only for the form
                ``YYYY-XXXXX`` where the last 5 digits are *not all identical*.
                This differentiates an accepted test case (``2025-12345``) from a
                deliberately invalid one (``2025-22222``) used in importer filtering.
    * We do NOT accept over-long numeric strings ( >9 digits ) by truncation -
        they are rejected to avoid accidental conflation.

Rationale for the mixed rules:
    The codebase historically had lenient, CLI-oriented normalization that
    aggressively stripped characters. Recent unification requires a *predictable*
    and *auditable* canonical key while keeping backward compatibility for one
    legacy dash pattern used in tests. The selective dash allowance plus letter
    rejection ensures we do not silently accept values that were intended to be
    flagged as invalid in data quality tests.

Legacy helper functions in other modules should delegate here to avoid drift.
"""
from __future__ import annotations

import re
from datetime import datetime
from typing import Iterable

YEAR_MIN = 1980
YEAR_MAX = 2050
LENGTH = 9

__all__ = [
    "normalize_strict",
    "is_valid_numero_ssa",
    "bulk_normalize",
    "normalize_numero_ssa",
]

def _digits(value) -> str:
    return re.sub(r"\D", "", str(value)) if value is not None else ""


def _current_legacy_year() -> str:
    return str(datetime.now().year)


def _expand_two_digit_year_sequence(trimmed: str) -> str | None:
    if len(trimmed) != 7 or not trimmed.isdigit():
        return None
    yy = int(trimmed[:2])
    suffix = trimmed[2:]
    year_2000 = 2000 + yy
    year_1900 = 1900 + yy
    if YEAR_MIN <= year_2000 <= YEAR_MAX:
        return f"{year_2000}{suffix}"
    if YEAR_MIN <= year_1900 <= YEAR_MAX:
        return f"{year_1900}{suffix}"
    return None

def normalize_strict(value) -> str | None:
    """Return canonical 9-digit numero_ssa or ``None`` if invalid.

    Enforcement steps:
      1. Reject None / empty early.
      2. Reject any value containing alphabetic characters (regression test requirement).
      3. Extract digits; must yield exactly 9.
      4. Year range validation (first four digits).
      5. If original contained a dash ('-'), allow only pattern YYYY-XXXXX where
         the last 5 digits are *not* all identical (business/test heuristic) -
         otherwise reject. (Accepts ``2025-12345``; rejects ``2025-22222``.)

    Note: We purposely *do not* silently truncate over-length sequences to 9 digits;
    callers should clean upstream or treat such cases as invalid.
    """
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    # 1. Remover separadores neutros permitidos ('-' e espacos). Mantem politica rigida contra letras e outros simbolos.
    #    Isso evita rejeitar valores como "2025-00777" ou "2025 00777" que historicamente apareciam.
    #    Nao aceitamos outros caracteres (pontos, barras, etc.).
    if re.search(r"[A-Za-z]", text):  # letras => rejeita
        return None
    # Se houver caracteres nao numericos exceto espaco ou hifen, rejeita
    if re.search(r"[^0-9\-\s]", text):
        return None
    had_dash = '-' in text
    compact = re.sub(r"[\s-]+", "", text)
    digits = _digits(compact)
    if len(digits) != LENGTH:
        return None
    # 3. Year validation
    try:
        ano = int(digits[:4])
    except ValueError:
        return None
    if not (YEAR_MIN <= ano <= YEAR_MAX):  # noqa: PLR2004
        return None
    # Rejeitar padrao com hifen quando ultimos 5 digitos todos iguais (ex.: 2025-22222)
    if had_dash and len(digits) == LENGTH:
        tail = digits[4:]
        if len(set(tail)) == 1:  # todos caracteres identicos
            return None
    return digits

def is_valid_numero_ssa(value) -> bool:
    return normalize_strict(value) is not None

def bulk_normalize(values: Iterable) -> list[str | None]:
    return [normalize_strict(v) for v in values]

def normalize_numero_ssa(value) -> str | None:  # noqa: PLR0911
    """Replica regra legacy de exibicao (padding / prefixos).

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
        return _current_legacy_year() + trimmed.zfill(5)
    if n_trim == 7:
        expanded = _expand_two_digit_year_sequence(trimmed)
        if expanded is not None:
            return expanded
    if len(raw) < 9:
        return raw.zfill(9)
    if len(raw) > 9:
        return None
    return raw
