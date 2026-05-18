"""Shared regex safety policy for local dataframe searches."""

from __future__ import annotations

import logging
import re

import pandas as pd

logger = logging.getLogger(__name__)

_UNSAFE_REGEX_QUANTIFIER_RE = re.compile(r"(?<!\\)[+*?{]")
_REGEX_META_CHAR_RE = re.compile(r"[*+?{}|()[\]]")
_MAX_REGEX_PATTERN_LENGTH = 120
_QUANTIFIER_START_CHARS = {"+", "*", "?", "{"}


def _true_mask(series: pd.Series) -> pd.Series:
    return pd.Series(True, index=series.index, name=series.name)


def _has_quantified_risky_group(pattern_text: str) -> bool:
    stack: list[tuple[bool, bool]] = []
    escaped = False
    for index, char in enumerate(pattern_text):
        if escaped:
            escaped = False
            continue
        if char == "\\":
            escaped = True
            continue
        if char == "(":
            stack.append((False, False))
            continue
        if not stack:
            continue
        has_quantifier, has_alternation = stack[-1]
        if char == "|":
            stack[-1] = (has_quantifier, True)
            continue
        if char == "?" and index > 0 and pattern_text[index - 1] == "(":
            continue
        if char in _QUANTIFIER_START_CHARS:
            stack[-1] = (True, has_alternation)
            continue
        if char != ")":
            continue
        stack.pop()
        next_char = pattern_text[index + 1] if index + 1 < len(pattern_text) else ""
        if not next_char and has_quantifier and has_alternation:
            return True
        if next_char in _QUANTIFIER_START_CHARS and (has_quantifier or has_alternation):
            return True
        if stack:
            parent_quantifier, parent_alternation = stack[-1]
            stack[-1] = (
                parent_quantifier or has_quantifier,
                parent_alternation or has_alternation,
            )
    return False


def _has_heavy_quantifier_chain(pattern_text: str) -> bool:
    chain = 0
    escaped = False
    for char in pattern_text:
        if escaped:
            escaped = False
            chain = 0
            continue
        if char == "\\":
            escaped = True
            chain = 0
            continue
        if char in _QUANTIFIER_START_CHARS:
            chain += 1
            if chain >= 3:
                return True
        else:
            chain = 0
    return False


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
        _has_quantified_risky_group(pattern_text)
        or _has_heavy_quantifier_chain(pattern_text)
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
