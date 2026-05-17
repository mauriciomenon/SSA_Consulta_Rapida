"""Shared regex safety policy for local dataframe searches."""

from __future__ import annotations

import logging
import re

import pandas as pd

logger = logging.getLogger(__name__)

_NESTED_QUANTIFIER_RE = re.compile(r"\((?:[^()]*[+*][^()]*)\)\s*[+*{]")
_HEAVY_QUANTIFIER_CHAIN_RE = re.compile(r"(?:[+*]|\{[^}]*\}){3,}")
_GROUP_ALTERNATION_WITH_QUANTIFIER_RE = re.compile(
    r"\([^)]*\|[^)]*\)\s*(?:[+*?]|\{[^}]*\})"
)
_UNSAFE_REGEX_QUANTIFIER_RE = re.compile(r"(?<!\\)[+*?{]")
_REGEX_META_CHAR_RE = re.compile(r"[*+?{}|()[\]]")
_MAX_REGEX_PATTERN_LENGTH = 120


def _true_mask(series: pd.Series) -> pd.Series:
    return pd.Series(True, index=series.index, name=series.name)


def is_safe_regex_pattern(pattern: str, *, reject_quantifiers: bool = False) -> bool:
    pattern_text = str(pattern or "")
    if not pattern_text:
        return True
    if len(pattern_text) > _MAX_REGEX_PATTERN_LENGTH:
        return False
    has_lookaround = (
        "(?=" in pattern_text
        or "(?!" in pattern_text
        or "(?<=" in pattern_text
        or "(?<!" in pattern_text
    )
    has_backref = bool(re.search(r"\\[1-9]", pattern_text))
    has_quantifier = bool(_UNSAFE_REGEX_QUANTIFIER_RE.search(pattern_text))
    meta_char_count = len(_REGEX_META_CHAR_RE.findall(pattern_text))
    return not (
        bool(_NESTED_QUANTIFIER_RE.search(pattern_text))
        or bool(_HEAVY_QUANTIFIER_CHAIN_RE.search(pattern_text))
        or bool(_GROUP_ALTERNATION_WITH_QUANTIFIER_RE.search(pattern_text))
        or has_lookaround
        or has_backref
        or (reject_quantifiers and has_quantifier)
        or meta_char_count > 16
    )


def safe_regex_contains(
    series: pd.Series,
    pattern: str,
    *,
    reject_quantifiers: bool = False,
    fallback_literal: bool = False,
) -> pd.Series:
    pattern_text = str(pattern or "")
    if not pattern_text:
        return _true_mask(series)
    if len(pattern_text) > _MAX_REGEX_PATTERN_LENGTH:
        if not fallback_literal:
            logger.warning("Regex de filtro bloqueado por tamanho.")
            return pd.Series(False, index=series.index, name=series.name)
        logger.warning("Regex de filtro bloqueado por tamanho; usando busca literal.")
        return series.str.contains(pattern_text, case=False, na=False, regex=False)
    if not is_safe_regex_pattern(
        pattern_text, reject_quantifiers=reject_quantifiers
    ):
        if not fallback_literal:
            logger.warning("Regex de filtro bloqueado por seguranca.")
            return pd.Series(False, index=series.index, name=series.name)
        logger.warning("Regex de filtro bloqueado por seguranca; usando busca literal.")
        return series.str.contains(pattern_text, case=False, na=False, regex=False)
    try:
        re.compile(pattern_text)
        return series.str.contains(pattern_text, case=False, na=False, regex=True)
    except re.error:
        if not fallback_literal:
            return pd.Series(False, index=series.index, name=series.name)
        return series.str.contains(pattern_text, case=False, na=False, regex=False)
