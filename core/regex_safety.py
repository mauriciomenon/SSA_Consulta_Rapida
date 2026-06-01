"""Shared regex safety policy for local dataframe searches."""

from __future__ import annotations

import logging
import re
from typing import NamedTuple

import pandas as pd

logger = logging.getLogger(__name__)

_MAX_REGEX_PATTERN_LENGTH = 120
_QUANTIFIER_START_CHARS = {"+", "*", "?", "{"}
_REGEX_META_CHARS = frozenset("*+?{}|()[]")
_BACKREF_CHARS = frozenset("123456789")


class _RegexScanResult(NamedTuple):
    has_quantified_risky_group: bool
    has_heavy_quantifier_chain: bool
    has_lookaround: bool
    has_backref: bool
    has_quantifier: bool
    meta_char_count: int


def _true_mask(series: pd.Series) -> pd.Series:
    return pd.Series(True, index=series.index, name=series.name)


def _scan_regex_pattern(pattern_text: str) -> _RegexScanResult:
    stack: list[tuple[bool, bool, bool]] = []
    escaped = False
    quantifier_chain = 0
    has_quantified_risky_group = False
    has_heavy_quantifier_chain = False
    has_lookaround = False
    has_backref = False
    has_unescaped_quantifier = False
    meta_char_count = 0

    for index, char in enumerate(pattern_text):
        if (
            char == "\\"
            and index + 1 < len(pattern_text)
            and pattern_text[index + 1] in _BACKREF_CHARS
        ):
            has_backref = True
        if char in _REGEX_META_CHARS:
            meta_char_count += 1
        if escaped:
            escaped = False
            quantifier_chain = 0
            continue
        if char == "\\":
            escaped = True
            quantifier_chain = 0
            continue
        if (
            char == "("
            and index + 2 < len(pattern_text)
            and pattern_text[index + 1] == "?"
            and (
                pattern_text[index + 2] in {"=", "!"}
                or (
                    pattern_text[index + 2] == "<"
                    and index + 3 < len(pattern_text)
                    and pattern_text[index + 3] in {"=", "!"}
                )
            )
        ):
            has_lookaround = True
        if char in _QUANTIFIER_START_CHARS:
            has_unescaped_quantifier = True
            quantifier_chain += 1
            if quantifier_chain >= 3:
                has_heavy_quantifier_chain = True
        else:
            quantifier_chain = 0
        if char == "(":
            stack.append((False, False, False))
            continue
        if not stack:
            continue
        group_has_direct_quantifier, has_alternation, has_nested_quantifier = stack[-1]
        if char == "|":
            stack[-1] = (group_has_direct_quantifier, True, has_nested_quantifier)
            continue
        if char == "?" and index > 0 and pattern_text[index - 1] == "(":
            continue
        if char in _QUANTIFIER_START_CHARS:
            stack[-1] = (True, has_alternation, has_nested_quantifier)
            continue
        if char != ")":
            continue
        stack.pop()
        next_index = index + 1
        next_char = pattern_text[next_index] if next_index < len(pattern_text) else ""
        group_has_quantifier = group_has_direct_quantifier or has_nested_quantifier
        if next_char in _QUANTIFIER_START_CHARS and (
            group_has_quantifier or has_alternation
        ):
            has_quantified_risky_group = True
        if stack:
            parent_quantifier, parent_alternation, parent_nested_quantifier = stack[-1]
            stack[-1] = (
                parent_quantifier,
                parent_alternation,
                parent_nested_quantifier or group_has_quantifier,
            )
    return _RegexScanResult(
        has_quantified_risky_group=has_quantified_risky_group,
        has_heavy_quantifier_chain=has_heavy_quantifier_chain,
        has_lookaround=has_lookaround,
        has_backref=has_backref,
        has_quantifier=has_unescaped_quantifier,
        meta_char_count=meta_char_count,
    )


def is_safe_regex_pattern(pattern: str, *, reject_quantifiers: bool = False) -> bool:
    pattern_text = str(pattern or "")
    if not pattern_text:
        return True
    if len(pattern_text) > _MAX_REGEX_PATTERN_LENGTH:
        return False
    scan = _scan_regex_pattern(pattern_text)
    return not (
        scan.has_quantified_risky_group
        or scan.has_heavy_quantifier_chain
        or scan.has_lookaround
        or scan.has_backref
        or (reject_quantifiers and scan.has_quantifier)
        or scan.meta_char_count > 16
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
        compiled = re.compile(pattern_text, re.IGNORECASE)
        return series.str.contains(compiled, na=False, regex=True)
    except re.error as exc:
        logger.warning("Regex de filtro invalido: %s", exc)
        if not fallback_literal:
            return pd.Series(False, index=series.index, name=series.name)
        return series.str.contains(pattern_text, case=False, na=False, regex=False)
