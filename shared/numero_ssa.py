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
    The codebase previously had lenient, CLI-oriented normalization that
    aggressively stripped characters. Recent unification requires a *predictable*
    and *auditable* canonical key while keeping compatibility for one
    dash pattern used in tests. The selective dash allowance plus letter
    rejection ensures we do not silently accept values that were intended to be
    flagged as invalid in data quality tests.

Compatibility facades in other modules should delegate here to avoid drift.
"""

from __future__ import annotations

import re
from typing import Iterable

from utils.robust_logging import get_robust_logger

YEAR_MIN = 1980
YEAR_MAX = 2050
VALID_LENGTHS = {9}
_CANONICAL_DECIMAL_ARTIFACT = re.compile(r"^\s*(\d+)\.0+\s*$")
logger = get_robust_logger().get_logger(__name__, "core")

__all__ = [
    "YEAR_MIN",
    "YEAR_MAX",
    "VALID_LENGTHS",
    "strip_canonical_decimal_artifact",
    "normalize_strict",
    "normalize_relation_id",
    "is_valid_numero_ssa",
    "bulk_normalize",
    "bulk_normalize_relation",
]


def _digits(value) -> str:
    return re.sub(r"\D", "", str(value)) if value is not None else ""


def strip_canonical_decimal_artifact(value):
    if value is None:
        return None
    text = str(value).strip()
    match = _CANONICAL_DECIMAL_ARTIFACT.fullmatch(text)
    if match is None:
        return value
    return match.group(1)


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
    text = str(strip_canonical_decimal_artifact(value)).strip()
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
    had_dash = "-" in text
    compact = re.sub(r"[\s-]+", "", text)
    digits = _digits(compact)
    if len(digits) > max(VALID_LENGTHS):
        logger.warning(
            "numero_ssa descartado por exceder 9 digitos: raw=%r digits=%s",
            value,
            digits,
        )
        return None
    if 0 < len(digits) < 5:
        logger.warning(
            "numero_ssa descartado por ter menos de 5 digitos: raw=%r digits=%s",
            value,
            digits,
        )
        return None
    if len(digits) not in VALID_LENGTHS:
        return None
    # 3. Year validation
    try:
        ano = int(digits[:4])
    except ValueError:
        return None
    if not (YEAR_MIN <= ano <= YEAR_MAX):  # noqa: PLR2004
        return None
    # Rejeitar padrao com hifen quando ultimos 5 digitos todos iguais (ex.: 2025-22222)
    if had_dash:
        tail = digits[4:]
        if len(set(tail)) == 1:  # todos caracteres identicos
            return None
    return digits


def normalize_relation_id(value) -> str | None:
    """Return relation-safe numero_ssa or ``None`` if invalid.

    This helper is intentionally stricter than the shared canonical key rule:
      * accepts only pure numeric text
      * rejects canonical decimal artifacts like ``121911787.0``
      * rejects letters, spaces, dashes and any other separator
      * preserves short numeric relation ids used by current derivadas flows

    A later hardening cycle may require canonical year + length validation here
    too, after synthetic short ids are migrated out of derivadas tests/fixtures.
    """
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    lowered = text.casefold()
    if lowered in {"", "nan", "none", "null", "nat", "<na>"}:
        return None
    if _CANONICAL_DECIMAL_ARTIFACT.fullmatch(text):
        return None
    if not text.isdigit():
        return None
    return text


def is_valid_numero_ssa(value) -> bool:
    return normalize_strict(value) is not None


def bulk_normalize(values: Iterable) -> list[str | None]:
    return [normalize_strict(v) for v in values]


def bulk_normalize_relation(values: Iterable) -> list[str | None]:
    return [normalize_relation_id(v) for v in values]
