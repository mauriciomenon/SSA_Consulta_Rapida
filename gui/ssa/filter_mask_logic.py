"""Pure column filter mask logic used by the GUI filter mixin."""

from __future__ import annotations

import re

import pandas as pd

from utils.robust_logging import get_robust_logger

logger = get_robust_logger().get_logger(__name__, "gui")

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


def _to_text_series(series: pd.Series) -> pd.Series:
    if pd.api.types.is_string_dtype(series.dtype):
        return series.fillna("") if series.hasnans else series
    return series.astype("string").fillna("")


def _safe_regex_contains(series: pd.Series, pattern: str) -> pd.Series:
    pattern_text = str(pattern or "")
    if not pattern_text:
        return _true_mask(series)
    if len(pattern_text) > _MAX_REGEX_PATTERN_LENGTH:
        logger.warning("Regex de filtro bloqueado por tamanho; usando busca literal.")
        return series.str.contains(pattern_text, case=False, na=False, regex=False)
    has_lookaround = (
        "(?=" in pattern_text
        or "(?!" in pattern_text
        or "(?<=" in pattern_text
        or "(?<!" in pattern_text
    )
    has_backref = bool(re.search(r"\\[1-9]", pattern_text))
    has_quantifier = bool(_UNSAFE_REGEX_QUANTIFIER_RE.search(pattern_text))
    meta_char_count = len(_REGEX_META_CHAR_RE.findall(pattern_text))
    has_alternation_with_quantifier = "|" in pattern_text and bool(
        re.search(r"[+*?{]", pattern_text)
    )
    if (
        _NESTED_QUANTIFIER_RE.search(pattern_text)
        or _HEAVY_QUANTIFIER_CHAIN_RE.search(pattern_text)
        or _GROUP_ALTERNATION_WITH_QUANTIFIER_RE.search(pattern_text)
        or has_lookaround
        or has_backref
        or has_quantifier
        or meta_char_count > 16
        or has_alternation_with_quantifier
    ):
        logger.warning("Regex de filtro bloqueado por seguranca; usando busca literal.")
        return series.str.contains(pattern_text, case=False, na=False, regex=False)
    try:
        re.compile(pattern_text)
        return series.str.contains(pattern_text, case=False, na=False, regex=True)
    except re.error:
        return series.str.contains(pattern_text, case=False, na=False, regex=False)


def _is_plain_token(token: str) -> bool:
    if token.upper() in ("NULL", "=NULL"):
        return False
    return not (
        token.startswith("!")
        or token.startswith("~")
        or token.startswith("=")
        or token.startswith("^")
        or token.endswith("$")
    )


def _match_plain_tokens(
    text_series: pd.Series,
    casefolded_series: pd.Series,
    tokens: list[str],
    *,
    mode: str,
) -> pd.Series | None:
    values = [token for token in tokens if token]
    if not values:
        return None
    folded_values = tuple(value.casefold() for value in values)
    if mode == "exact":
        return casefolded_series.isin(folded_values)
    if mode == "prefix":
        return casefolded_series.str.startswith(folded_values, na=False)
    if mode == "suffix":
        return casefolded_series.str.endswith(folded_values, na=False)
    if mode == "contains":
        pattern = "|".join(re.escape(value) for value in folded_values)
        return casefolded_series.str.contains(pattern, na=False, regex=True)
    return None


def _match_column_token(
    text_series: pd.Series,
    casefolded_series: pd.Series,
    original_series: pd.Series,
    token: str,
    *,
    default_mode: str,
) -> pd.Series:
    negated = token.startswith("!")
    value = token[1:] if negated else token
    mode = str(default_mode or "contains").casefold()
    if value.upper() in ("NULL", "=NULL"):
        stripped = text_series.str.strip()
        result = original_series.isna() | stripped.eq("") | text_series.eq("-")
        return ~result if negated else result
    if value.startswith("~") and len(value) > 1:
        result = _safe_regex_contains(text_series, value[1:])
    elif value.startswith("="):
        result = casefolded_series.eq(value[1:].casefold())
    elif value.startswith("^"):
        result = casefolded_series.str.startswith(value[1:].casefold(), na=False)
    elif value.endswith("$"):
        result = casefolded_series.str.endswith(value[:-1].casefold(), na=False)
    elif mode == "prefix":
        result = casefolded_series.str.startswith(value.casefold(), na=False)
    elif mode == "suffix":
        result = casefolded_series.str.endswith(value.casefold(), na=False)
    elif mode == "exact":
        result = casefolded_series.eq(value.casefold())
    elif mode == "regex":
        result = _safe_regex_contains(text_series, value)
    else:
        result = text_series.str.contains(value, case=False, na=False, regex=False)
    return ~result if negated else result


def build_column_mask(
    series: pd.Series,
    raw: str,
    *,
    default_mode: str,
    casefolded_series: pd.Series | None = None,
) -> pd.Series:
    """Build a boolean mask for one column.

    NULL and =NULL are explicit empty-value operators and intentionally override
    default_mode.
    """
    text_series = _to_text_series(series)
    if casefolded_series is None or not casefolded_series.index.equals(
        text_series.index
    ):
        casefolded_series = text_series.str.casefold()
    tokens = [token.strip() for token in str(raw).split(",") if token.strip()]
    if not tokens:
        return _true_mask(text_series)

    includes = [token for token in tokens if not token.startswith("!")]
    excludes = [token for token in tokens if token.startswith("!")]
    mode = str(default_mode or "contains").casefold()

    plain_include_mask = (
        _match_plain_tokens(
            text_series,
            casefolded_series,
            includes,
            mode=mode,
        )
        if includes and all(_is_plain_token(token) for token in includes)
        else None
    )
    if plain_include_mask is not None:
        mask = plain_include_mask
    elif includes:
        mask = _match_column_token(
            text_series,
            casefolded_series,
            series,
            includes[0],
            default_mode=default_mode,
        )
        for token in includes[1:]:
            mask = mask | _match_column_token(
                text_series,
                casefolded_series,
                series,
                token,
                default_mode=default_mode,
            )
    else:
        mask = _true_mask(text_series)
    plain_excludes = [
        token[1:].strip()
        for token in excludes
        if _is_plain_token(token[1:].strip())
    ]
    complex_excludes = [
        token for token in excludes if not _is_plain_token(token[1:].strip())
    ]
    plain_exclude_mask = _match_plain_tokens(
        text_series,
        casefolded_series,
        plain_excludes,
        mode=mode,
    )
    if plain_exclude_mask is not None:
        mask = mask & ~plain_exclude_mask
    for token in complex_excludes:
        mask = mask & _match_column_token(
            text_series,
            casefolded_series,
            series,
            token,
            default_mode=default_mode,
        )
    return mask
