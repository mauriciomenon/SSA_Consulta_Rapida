"""Search/filter logic shared by CLI and GUI."""

from __future__ import annotations

import logging
import re
import threading
import weakref
from collections import OrderedDict
from typing import Any, Callable, Dict, List, Optional, cast

import pandas as pd

from shared.numero_ssa import normalize_relation_id
from core.search_filter_constants import (
    FILTER_EXACT_IDENTIFIER_COLUMNS,
    FILTER_FIELD_SEPARATOR,
    FILTER_SEARCH_CACHE_ATTR,
    FILTER_SEARCH_MARKER_ATTR,
    FILTER_SEARCH_SIGNATURE_CACHE_ATTR,
)
from core.search_filter_defaults import DEFAULT_FILTER_SEARCH_COLUMNS
from core.regex_safety import safe_regex_contains

logger = logging.getLogger(__name__)
_NORMALIZED_SEARCH_CACHE_LOCK = threading.Lock()
_NORMALIZED_SEARCH_CACHE_MAX_ENTRIES = 2
_NORMALIZED_SEARCH_CACHE_MAX_BYTES = 64 * 1024 * 1024
_NORMALIZED_SEARCH_CACHE: OrderedDict[tuple[Any, ...], dict[str, Any]] = OrderedDict()

class GeneralSearchCancelled(Exception):
    """Internal cancellation signal for background general-search execution."""


def clear_filter_search_attrs(result_df: pd.DataFrame) -> pd.DataFrame:
    result_df.attrs.pop(FILTER_SEARCH_MARKER_ATTR, None)
    result_df.attrs.pop(FILTER_SEARCH_CACHE_ATTR, None)
    result_df.attrs.pop(FILTER_SEARCH_SIGNATURE_CACHE_ATTR, None)
    return result_df


def _single_exact_identifier_term(terms: list[dict[str, Any]]) -> str | None:
    if len(terms) != 1:
        return None
    term = terms[0]
    if term.get("negative") or term.get("mode") != "exact":
        return None
    # Programmatic/legacy terms can still carry OR-group metadata; the exact
    # identifier fast path is safe only for the default AND group.
    if int(term.get("group", 0) or 0) != 0:
        return None
    return normalize_relation_id(term.get("value", ""))


def _filter_exact_identifier_columns(
    df: pd.DataFrame,
    *,
    available_search_cols: list[str],
    identifier: str,
) -> pd.DataFrame | None:
    exact_columns = [
        column_name
        for column_name in FILTER_EXACT_IDENTIFIER_COLUMNS
        if column_name in available_search_cols and column_name in df.columns
    ]
    if not exact_columns:
        return None

    mask = pd.Series(False, index=df.index)
    try:
        numeric_identifier = int(identifier)
    except (TypeError, ValueError):
        numeric_identifier = None
    for column_name in exact_columns:
        column = df[column_name]
        column_mask = pd.Series(False, index=df.index)
        if numeric_identifier is not None and pd.api.types.is_numeric_dtype(
            column.dtype
        ):
            column_mask = column.eq(numeric_identifier)
        else:
            normalized = column.astype("string").fillna("").str.strip()
            column_mask = normalized.eq(identifier)
            if numeric_identifier is not None:
                # Excel/CSV imports can turn numeric SSA identifiers into
                # float-looking strings; only numeric search terms get this path.
                column_mask = column_mask | normalized.eq(f"{identifier}.0")
        mask = mask | column_mask
    return clear_filter_search_attrs(df[mask])


def _normalize_filter_search_series(series: pd.Series) -> pd.Series:
    if pd.api.types.is_string_dtype(series.dtype):
        string_series = series.fillna("")
    else:
        string_series = series.astype("string").fillna("")
    return (
        string_series.str.casefold().str.replace(FILTER_FIELD_SEPARATOR, " ", regex=False)
    )


def _build_normalized_column_cache(
    df: pd.DataFrame,
    available_search_cols: list[str],
) -> dict[str, pd.Series]:
    revision = df.attrs.get("ssa_data_revision")
    if revision is None:
        return {
            column_name: _normalize_filter_search_series(df[column_name])
            for column_name in available_search_cols
        }

    cache_key = (
        id(df),
        tuple(available_search_cols),
        len(df.index),
        str(revision),
    )
    with _NORMALIZED_SEARCH_CACHE_LOCK:
        cached = _NORMALIZED_SEARCH_CACHE.get(cache_key)
        if (
            isinstance(cached, dict)
            and callable(cached.get("df_ref"))
            and cached["df_ref"]() is df
            and isinstance(cached.get("columns"), dict)
        ):
            _NORMALIZED_SEARCH_CACHE.move_to_end(cache_key)
            return dict(cached["columns"])

    normalized_columns = {
        column_name: _normalize_filter_search_series(df[column_name])
        for column_name in available_search_cols
    }
    estimated_bytes = sum(
        int(series.memory_usage(index=False, deep=False))
        for series in normalized_columns.values()
    )
    if estimated_bytes > _NORMALIZED_SEARCH_CACHE_MAX_BYTES:
        return normalized_columns
    with _NORMALIZED_SEARCH_CACHE_LOCK:
        _NORMALIZED_SEARCH_CACHE[cache_key] = {
            "df_ref": weakref.ref(df),
            "columns": normalized_columns,
        }
        while len(_NORMALIZED_SEARCH_CACHE) > _NORMALIZED_SEARCH_CACHE_MAX_ENTRIES:
            _NORMALIZED_SEARCH_CACHE.popitem(last=False)
    return dict(normalized_columns)


def parse_search_terms(
    search_terms: Any,
    default_mode: str = "contains",
) -> List[Dict[str, Any]]:
    """
    Converte termos brutos em uma estrutura padronizada com modo e polaridade.

    SIMPLIFIED RAW STRING CONTRACT:
    - Raw strings split only by commas before parsing.
    - General search applies implicit AND between terms (all raw terms stay in group=0).
    - Each term may match any searched field.
    - Pre-parsed dict terms may carry explicit group metadata for legacy
      grouped alternatives; raw user text never creates those groups.

    Only comma-separated terms and the markers below are supported:
    - contem (padrao): foo
    - comeca com: ^foo
    - termina com: foo$
    - igual: =foo
    - regex: ~foo.*bar
    - se o modo padrao for regex, ^ e $ sem ~ continuam parte do regex bruto
    Negativo: prefixar ! (ou -) antes do termo (ex.: !^adm, !=fechado, !$2025, !~regex)
    """
    parsed: List[Dict[str, Any]] = []
    if search_terms is None:
        return parsed
    if isinstance(search_terms, list):
        normalized_terms: list[Any] = search_terms
    elif isinstance(search_terms, tuple):
        normalized_terms = list(search_terms)
    elif isinstance(search_terms, str):
        normalized_terms = [search_terms]
    else:
        logger.warning(
            "parse_search_terms recebeu tipo invalido de search_terms: %s",
            type(search_terms).__name__,
        )
        return parsed
    if len(normalized_terms) == 0:
        return parsed

    allowed_modes = {"contains", "prefix", "suffix", "exact", "regex"}
    fallback_mode = default_mode if default_mode in allowed_modes else "contains"

    # Simplified: split only by commas, then process all terms with group=0 (AND logic)
    for raw in normalized_terms:
        if not isinstance(raw, str):
            continue
        raw_chunks = [chunk.strip() for chunk in raw.split(",")]
        for raw_chunk in raw_chunks:
            t = raw_chunk.strip()
            if not t:
                continue
            negative = False
            if (t.startswith("!") or t.startswith("-")) and len(t) > 1:
                negative = True
                t = t[1:]
            mode = fallback_mode
            value = t
            if t.startswith("~") and len(t) > 1:
                mode = "regex"
                value = t[1:]
            elif t.startswith("=") and len(t) > 1:
                mode = "exact"
                value = t[1:]
            elif t.startswith("$") and len(t) > 1:
                mode = "suffix"
                value = t[1:]
            elif fallback_mode != "regex" and t.startswith("^") and len(t) > 1:
                mode = "prefix"
                value = t[1:]
            elif fallback_mode != "regex" and t.endswith("$") and len(t) > 1:
                mode = "suffix"
                value = t[:-1]
            parsed.append(
                {
                    "raw": raw_chunk,
                    "mode": mode,
                    "value": value,
                    "negative": negative,
                    "group": 0,  # All terms in same group (AND logic)
                }
            )
    return parsed


def _normalize_search_terms_input(search_terms: Any) -> list[Any] | None:
    if isinstance(search_terms, list):
        return search_terms
    if isinstance(search_terms, tuple):
        return list(search_terms)
    if isinstance(search_terms, str):
        return [search_terms]
    logger.warning(
        "filter_dataframe recebeu search_terms invalido (%s); retornando DataFrame sem filtro",
        type(search_terms).__name__,
    )
    return None


def _resolve_available_search_columns(
    df: pd.DataFrame, search_columns: Optional[list]
) -> list[str]:
    if search_columns is None:
        search_columns = [col for col in DEFAULT_FILTER_SEARCH_COLUMNS if col in df.columns]
        if not search_columns:
            search_columns = df.select_dtypes(
                include=["object", "string"]
            ).columns.tolist()
    return [col for col in search_columns if col in df.columns]


def _coerce_filter_terms(
    normalized_search_terms: list[Any],
) -> List[Dict[str, Any]]:
    if isinstance(normalized_search_terms[0], dict):
        return [
            cast(Dict[str, Any], term)
            for term in normalized_search_terms
            if isinstance(term, dict)
        ]
    return parse_search_terms(normalized_search_terms)


def _combine_filter_term_masks(
    df: pd.DataFrame,
    terms: List[Dict[str, Any]],
    mask_for_term: Callable[[Dict[str, Any]], pd.Series],
) -> pd.Series:
    has_explicit_or_groups = any(
        int(term.get("group", 0) or 0) != 0 for term in terms
    )
    if not has_explicit_or_groups:
        final_mask = pd.Series(True, index=df.index)
        for term in terms:
            term_mask = mask_for_term(term)
            if term.get("negative"):
                final_mask = final_mask & (~term_mask)
            else:
                final_mask = final_mask & term_mask
        return final_mask

    grouped_terms: Dict[int, List[Dict[str, Any]]] = {}
    for term in terms:
        group_idx = term.get("group", 0)
        grouped_terms.setdefault(int(group_idx), []).append(term)

    final_mask = pd.Series(False, index=df.index)
    for group_terms in grouped_terms.values():
        group_mask = pd.Series(True, index=df.index)
        positives = [t for t in group_terms if not t.get("negative")]
        negatives = [t for t in group_terms if t.get("negative")]

        for term in positives:
            group_mask = group_mask & mask_for_term(term)

        for term in negatives:
            group_mask = group_mask & (~mask_for_term(term))

        final_mask = final_mask | group_mask
    return final_mask


def filter_dataframe(
    df: pd.DataFrame, search_terms: Any, search_columns: Optional[list] = None
) -> pd.DataFrame:
    """
    Filtra um DataFrame com base em uma lista de termos de busca (strings) ou
    termos ja parseados por parse_search_terms().

     OTIMIZACAO: Agora permite especificar colunas de busca para melhor performance.

    Args:
        df: DataFrame para filtrar
        search_terms: Lista de termos de busca ou termos parseados
        search_columns: Lista de colunas especificas para buscar. Se None, busca nas
                       colunas prioritarias disponiveis para busca geral, incluindo
                       numero, situacao, setores, descricoes e campos humanos como
                       solicitante e responsavel_*.

    Modos por termo: contem (padrao), comeca (^), termina ($), igual (=), regex (~),
    com suporte a negativos (! ou -). Regex sem ancora busca no texto combinado da
    linha; regex com ^ ou $ busca por campo pesquisavel individual.

    Contrato atual:
    - termos brutos (str) seguem o parser simplificado atual: AND implicito entre termos
    - cada termo e satisfeito quando qualquer campo pesquisavel da linha corresponder
    - termos ja parseados (dict) ainda podem carregar grupos legados de alternativas
    """
    if df is None or df.empty:
        return df
    normalized_search_terms = _normalize_search_terms_input(search_terms)
    if normalized_search_terms is None:
        return df
    if len(normalized_search_terms) == 0:
        return df

    available_search_cols = _resolve_available_search_columns(df, search_columns)
    if not available_search_cols:
        logger.warning("Nenhuma coluna de busca valida encontrada")
        return df

    terms = _coerce_filter_terms(normalized_search_terms)
    if not terms:
        return df

    exact_identifier = _single_exact_identifier_term(terms)
    if exact_identifier:
        exact_identifier_result = _filter_exact_identifier_columns(
            df,
            available_search_cols=available_search_cols,
            identifier=exact_identifier,
        )
        if exact_identifier_result is not None:
            return exact_identifier_result

    normalized_column_cache = _build_normalized_column_cache(df, available_search_cols)

    def _column_match_mask(mode: str, lowered_value: str) -> pd.Series:
        mask = pd.Series(False, index=df.index)
        for column_name in available_search_cols:
            column_text = normalized_column_cache[column_name]
            if mode == "prefix":
                column_mask = column_text.str.startswith(lowered_value, na=False)
            elif mode == "suffix":
                column_mask = column_text.str.endswith(lowered_value, na=False)
            elif mode == "exact":
                column_mask = column_text.eq(lowered_value)
            else:
                column_mask = column_text.str.contains(
                    lowered_value, regex=False, na=False
                )
            mask = mask | column_mask
        return mask

    def _regex_column_match_mask(
        pattern: str,
        *,
        reject_quantifiers: bool = False,
    ) -> pd.Series:
        mask = pd.Series(False, index=df.index)
        reject_complex_quantifiers = (
            reject_quantifiers and len(df.index) * max(len(available_search_cols), 1) > 50_000
        )
        for column_name in available_search_cols:
            column_text = normalized_column_cache[column_name]
            mask = mask | safe_regex_contains(
                column_text,
                pattern,
                reject_quantifiers=reject_complex_quantifiers,
                fallback_literal=False,
            )
        return mask

    logger.debug(
        "Buscando em %s colunas: %s",
        len(available_search_cols),
        list(available_search_cols),
    )
    def _mask_for_term(term: Dict[str, Any]) -> pd.Series:
        mode = term.get("mode", "contains")
        value = term.get("value", "") or ""
        lowered_value = str(value).casefold()

        if mode == "regex":
            try:
                pattern = str(value)
                if "^" in pattern or "$" in pattern:
                    return _regex_column_match_mask(pattern, reject_quantifiers=True)
                return _regex_column_match_mask(pattern)
            except re.error:
                return pd.Series(False, index=df.index)

        if mode in {"prefix", "suffix", "exact"}:
            return _column_match_mask(mode, lowered_value)
        return _column_match_mask("contains", lowered_value)

    final_mask = _combine_filter_term_masks(df, terms, _mask_for_term)
    if final_mask.any():
        return clear_filter_search_attrs(df[final_mask])
    return clear_filter_search_attrs(df.iloc[0:0])


def apply_general_search_terms(
    filter_source: pd.DataFrame,
    unique_chunk_terms_lists: list[list[str]],
    *,
    default_mode: str,
    general_search_columns: list[str] | None,
    parse_terms_func: Callable[..., List[Dict[str, Any]]] = parse_search_terms,
    filter_dataframe_func: Callable[..., pd.DataFrame] = filter_dataframe,
    should_cancel: Callable[[], bool] | None = None,
) -> pd.DataFrame:
    if not unique_chunk_terms_lists:
        return clear_filter_search_attrs(filter_source.copy(deep=False))

    if len(unique_chunk_terms_lists) == 1:
        if should_cancel is not None and should_cancel():
            raise GeneralSearchCancelled
        parsed = parse_terms_func(unique_chunk_terms_lists[0], default_mode)
        if should_cancel is not None and should_cancel():
            raise GeneralSearchCancelled
        if general_search_columns is None:
            return filter_dataframe_func(filter_source, parsed)
        return filter_dataframe_func(
            filter_source,
            parsed,
            search_columns=general_search_columns,
        )

    if len(unique_chunk_terms_lists) > 1:
        grouped_terms: list[Dict[str, Any]] = []
        for group_idx, terms in enumerate(unique_chunk_terms_lists, start=1):
            if should_cancel is not None and should_cancel():
                raise GeneralSearchCancelled
            parsed_group = parse_terms_func(terms, default_mode)
            for term in parsed_group:
                term["group"] = group_idx
            grouped_terms.extend(parsed_group)
        if should_cancel is not None and should_cancel():
            raise GeneralSearchCancelled
        if not grouped_terms:
            return filter_source.iloc[0:0].copy()
        if general_search_columns is None:
            return filter_dataframe_func(filter_source, grouped_terms)
        return filter_dataframe_func(
            filter_source,
            grouped_terms,
            search_columns=general_search_columns,
        )

    return filter_source.iloc[0:0].copy()
