"""Search/filter logic shared by CLI and GUI."""

from __future__ import annotations

import hashlib
import logging
import math
import re
import uuid
from typing import Any, Dict, List, Optional, cast

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

FILTER_SEARCH_ROW_TEXT_CACHE_MAX_BYTES = 8 * 1024 * 1024
FILTER_SEARCH_SIGNATURE_SAMPLE_SIZE = 64


class FilterSearchCacheManager:
    """Manage per-DataFrame search cache attrs for filter_dataframe()."""

    @staticmethod
    def _compute_cache_signature(
        df: pd.DataFrame, available_search_cols: list[str]
    ) -> str | None:
        if not available_search_cols:
            return None
        search_df = df.loc[:, available_search_cols]
        row_count = len(search_df.index)
        revision = df.attrs.get("ssa_data_revision")
        signature_key = (
            tuple(str(col) for col in available_search_cols),
            tuple(str(dtype) for dtype in search_df.dtypes),
            row_count,
            str(revision) if revision is not None else "",
        )
        if revision is not None:
            cached_signature = df.attrs.get(FILTER_SEARCH_SIGNATURE_CACHE_ATTR)
            if (
                isinstance(cached_signature, dict)
                and cached_signature.get("key") == signature_key
                and isinstance(cached_signature.get("signature"), str)
            ):
                return str(cached_signature["signature"])
        if row_count == 0:
            data_digest = "empty"
        else:
            sample_size = min(FILTER_SEARCH_SIGNATURE_SAMPLE_SIZE, row_count)
            last_idx = row_count - 1
            if sample_size == 1:
                sample_positions = {0}
            else:
                sample_positions = {
                    int(round(i * last_idx / float(sample_size - 1)))
                    for i in range(sample_size)
                }
            sample_df = search_df.iloc[sorted(sample_positions)]
            hashed = pd.util.hash_pandas_object(
                sample_df, index=True, categorize=True
            )
            data_digest = hashlib.blake2b(
                hashed.to_numpy().tobytes(),
                digest_size=16,
            ).hexdigest()
        hasher = hashlib.blake2b(digest_size=16)
        hasher.update(str(row_count).encode("utf-8"))
        if revision is not None:
            hasher.update(b"\x00revision:")
            hasher.update(str(revision).encode("utf-8", errors="replace"))
        for column_name, dtype in zip(available_search_cols, search_df.dtypes):
            hasher.update(b"\x00col:")
            hasher.update(str(column_name).encode("utf-8", errors="replace"))
            hasher.update(b"\x00dtype:")
            hasher.update(str(dtype).encode("utf-8", errors="replace"))
        hasher.update(b"\x00data:")
        hasher.update(data_digest.encode("utf-8"))
        signature = hasher.hexdigest()
        if revision is not None:
            df.attrs[FILTER_SEARCH_SIGNATURE_CACHE_ATTR] = {
                "key": signature_key,
                "signature": signature,
            }
        return signature

    @staticmethod
    def build_token(
        df: pd.DataFrame, available_search_cols: list[str]
    ) -> tuple[str, tuple[str, ...], int, str | None]:
        data_token = df.attrs.setdefault(FILTER_SEARCH_MARKER_ATTR, uuid.uuid4().hex)
        fingerprint = FilterSearchCacheManager._compute_cache_signature(
            df, available_search_cols
        )
        return (data_token, tuple(available_search_cols), len(df.index), fingerprint)

    @staticmethod
    def get_cached_search_data(
        df: pd.DataFrame,
        search_cache_token: tuple[str, tuple[str, ...], int, str | None],
    ) -> Optional[dict[str, Any]]:
        cached_search_data = df.attrs.get(FILTER_SEARCH_CACHE_ATTR)
        if (
            isinstance(cached_search_data, dict)
            and isinstance(cached_search_data.get("token"), tuple)
            and cached_search_data["token"][:3] == search_cache_token[:3]
        ):
            if cached_search_data["token"][3] != search_cache_token[3]:
                return None
            return cast(dict[str, Any], cached_search_data)
        return None

    @staticmethod
    def store_cached_search_data(
        df: pd.DataFrame,
        search_cache_token: tuple[str, tuple[str, ...], int, str | None],
        base_lower_df_or_row_search_text: pd.DataFrame | pd.Series | None,
        row_search_text: pd.Series | None = None,
    ) -> None:
        if row_search_text is None:
            row_search_text = cast(pd.Series, base_lower_df_or_row_search_text)
        fingerprint = search_cache_token[3]
        payload: dict[str, Any] = {
            "token": (
                search_cache_token[0],
                search_cache_token[1],
                search_cache_token[2],
                fingerprint,
            ),
        }
        row_count = len(row_search_text.index)
        if row_count <= 0:
            row_search_text_bytes = 0
        else:
            sample_size = min(FILTER_SEARCH_SIGNATURE_SAMPLE_SIZE, row_count)
            sample = row_search_text.iloc[:sample_size].astype("string").fillna("")
            avg_chars = float(sample.str.len().mean() or 0.0)
            if not math.isfinite(avg_chars):
                avg_chars = 0.0
            row_search_text_bytes = int(avg_chars * row_count)
        if (
            row_search_text_bytes <= 0
            or row_search_text_bytes <= FILTER_SEARCH_ROW_TEXT_CACHE_MAX_BYTES
        ):
            payload["row_search_text"] = row_search_text
        df.attrs[FILTER_SEARCH_CACHE_ATTR] = payload

    @staticmethod
    def clear_result_attrs(result_df: pd.DataFrame) -> pd.DataFrame:
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
        normalized = (
            column.astype("string")
            .fillna("")
            .str.strip()
            .str.replace(r"\.0+$", "", regex=True)
        )
        column_mask = column_mask | normalized.eq(identifier)
        mask = mask | column_mask
    return FilterSearchCacheManager.clear_result_attrs(df[mask])


def _normalize_filter_search_series(series: pd.Series) -> pd.Series:
    return (
        series.astype("string")
        .fillna("")
        .str.casefold()
        .str.replace(FILTER_FIELD_SEPARATOR, " ", regex=False)
    )


def _field_boundary_regex(pattern_text: str) -> str | None:
    if not pattern_text:
        return None
    has_prefix_anchor = pattern_text.startswith("^")
    has_suffix_anchor = pattern_text.endswith("$") and not pattern_text.endswith(r"\$")
    if not has_prefix_anchor and not has_suffix_anchor:
        return None
    inner = pattern_text
    if has_prefix_anchor:
        inner = inner[1:]
    if has_suffix_anchor:
        inner = inner[:-1]
    if not inner:
        return None
    left = rf"(?:^|{re.escape(FILTER_FIELD_SEPARATOR)})" if has_prefix_anchor else ""
    right = rf"(?:$|{re.escape(FILTER_FIELD_SEPARATOR)})" if has_suffix_anchor else ""
    return f"{left}{inner}{right}"


def _build_row_search_text(
    df: pd.DataFrame,
    available_search_cols: list[str],
) -> pd.Series:
    if not available_search_cols:
        return pd.Series([], index=df.index, dtype="string")

    normalized_series = [
        _normalize_filter_search_series(df[column_name])
        for column_name in available_search_cols
    ]
    if len(normalized_series) == 1:
        return normalized_series[0]
    return normalized_series[0].str.cat(
        normalized_series[1:],
        sep=FILTER_FIELD_SEPARATOR,
        na_rep="",
    )


def parse_search_terms(
    search_terms: Any,
    default_mode: str = "contains",
) -> List[Dict[str, Any]]:
    """
    Converte termos brutos em uma estrutura padronizada com modo e polaridade.

    SIMPLIFIED RAW STRING CONTRACT:
    - Raw strings split only by commas before parsing.
    - Boolean words such as OU/OR/AND/E are treated as plain text.
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
    com suporte a negativos (! ou -).

    Contrato atual:
    - termos brutos (str) seguem o parser simplificado atual: AND implicito entre termos
    - cada termo e satisfeito quando qualquer campo pesquisavel da linha corresponder
    - termos ja parseados (dict) ainda podem carregar grupos legados de alternativas
    """
    if df is None or df.empty:
        return df
    if isinstance(search_terms, list):
        normalized_search_terms: list[Any] = search_terms
    elif isinstance(search_terms, tuple):
        normalized_search_terms = list(search_terms)
    elif isinstance(search_terms, str):
        normalized_search_terms = [search_terms]
    else:
        logger.warning(
            "filter_dataframe recebeu search_terms invalido (%s); retornando DataFrame sem filtro",
            type(search_terms).__name__,
        )
        return df
    if len(normalized_search_terms) == 0:
        return df

    #  OTIMIZACAO: Usar apenas colunas prioritarias se nao especificado
    if search_columns is None:
        search_columns = [
            col for col in DEFAULT_FILTER_SEARCH_COLUMNS if col in df.columns
        ]

        # Se nenhuma coluna prioritaria existe, usar todas as de texto como fallback
        if not search_columns:
            search_columns = df.select_dtypes(
                include=["object", "string"]
            ).columns.tolist()

    # Criar DataFrame base apenas com colunas de busca
    available_search_cols = [col for col in search_columns if col in df.columns]
    if not available_search_cols:
        logger.warning("Nenhuma coluna de busca valida encontrada")
        return df

    # Permite tanto termos brutos (str) quanto parseados (dict)
    terms: List[Dict[str, Any]]
    if isinstance(normalized_search_terms[0], dict):
        terms = [
            cast(Dict[str, Any], term)
            for term in normalized_search_terms
            if isinstance(term, dict)
        ]
    else:
        terms = parse_search_terms(normalized_search_terms)

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

    # Cache de patterns: pre-compila patterns para evitar re.escape repetido
    pattern_cache = {}
    for term in terms:
        mode = term.get("mode", "contains")
        value = term.get("value", "") or ""
        lowered_value = str(value).casefold()
        cache_key_value = lowered_value if mode == "contains" else value
        cache_key = (mode, cache_key_value)

        if cache_key not in pattern_cache:
            if mode == "contains":
                pattern_cache[cache_key] = (lowered_value, False, lowered_value)
            elif mode == "prefix":
                pattern_cache[cache_key] = (
                    rf"(?:^|{re.escape(FILTER_FIELD_SEPARATOR)})"
                    rf"{re.escape(lowered_value)}",
                    True,
                    lowered_value,
                )
            elif mode == "suffix":
                pattern_cache[cache_key] = (
                    rf"{re.escape(lowered_value)}"
                    rf"(?:$|{re.escape(FILTER_FIELD_SEPARATOR)})",
                    True,
                    lowered_value,
                )
            elif mode == "exact":
                pattern_cache[cache_key] = (
                    rf"(?:^|{re.escape(FILTER_FIELD_SEPARATOR)})"
                    rf"{re.escape(lowered_value)}"
                    rf"(?:$|{re.escape(FILTER_FIELD_SEPARATOR)})",
                    True,
                    lowered_value,
                )
            elif mode == "regex":
                pattern_cache[cache_key] = (value, True, lowered_value)
            else:
                pattern_cache[cache_key] = (lowered_value, False, lowered_value)

    search_cache_token = FilterSearchCacheManager.build_token(df, available_search_cols)
    cached_search_data = FilterSearchCacheManager.get_cached_search_data(
        df, search_cache_token
    )
    row_search_text: pd.Series | None = None

    if cached_search_data is not None:
        cached_rows = cached_search_data.get("row_search_text")
        if isinstance(cached_rows, pd.Series) and len(cached_rows.index) == len(df.index):
            row_search_text = cached_rows

    if row_search_text is None:
        if len(available_search_cols) == 0:
            return FilterSearchCacheManager.clear_result_attrs(df.iloc[0:0])
        row_search_text = _build_row_search_text(df, available_search_cols)
        FilterSearchCacheManager.store_cached_search_data(
            df, search_cache_token, None, row_search_text
        )
        cached_search_data = FilterSearchCacheManager.get_cached_search_data(
            df, search_cache_token
        )

    if row_search_text is None:
        logger.warning("Falha ao preparar texto de busca; retornando resultado vazio.")
        return FilterSearchCacheManager.clear_result_attrs(df.iloc[0:0])
    if not isinstance(row_search_text, pd.Series):
        logger.warning(
            "Cache de busca invalido (%s); retornando resultado vazio.",
            type(row_search_text).__name__,
        )
        return FilterSearchCacheManager.clear_result_attrs(df.iloc[0:0])

    logger.debug(
        "Buscando em %s colunas: %s",
        len(available_search_cols),
        list(available_search_cols),
    )

    def _mask_for_term(term: Dict[str, Any]) -> pd.Series:
        mode = term.get("mode", "contains")
        value = term.get("value", "") or ""
        lowered_value = str(value).casefold()
        cache_key_value = lowered_value if mode == "contains" else value
        cache_key = (mode, cache_key_value)

        pattern, use_regex, lowered = pattern_cache.get(
            cache_key, (lowered_value, False, lowered_value)
        )

        def _contains(pattern: str, *, regex: bool) -> pd.Series:
            if regex:
                return row_search_text.str.contains(
                    pattern, case=False, na=False, regex=True
                )

            return row_search_text.str.contains(pattern, regex=False, na=False)

        if mode == "regex":
            try:
                if "^" in pattern or "$" in pattern:
                    field_boundary_pattern = _field_boundary_regex(pattern)
                    if field_boundary_pattern:
                        return safe_regex_contains(
                            row_search_text,
                            field_boundary_pattern,
                            fallback_literal=False,
                        )
                return safe_regex_contains(
                    row_search_text, pattern, fallback_literal=False
                )
            except re.error:
                return pd.Series(False, index=df.index)

        if mode == "prefix":
            return row_search_text.str.contains(pattern, na=False, regex=True)
        if mode == "suffix":
            return row_search_text.str.contains(pattern, na=False, regex=True)
        if mode == "exact":
            return row_search_text.str.contains(pattern, na=False, regex=True)

        return _contains(pattern, regex=use_regex)

    has_explicit_or_groups = any(
        int(term.get("group", 0) or 0) != 0 for term in terms
    )
    if not has_explicit_or_groups:
        final_mask = pd.Series(True, index=df.index)
        for term in terms:
            term_mask = _mask_for_term(term)
            if term.get("negative"):
                final_mask = final_mask & (~term_mask)
            else:
                final_mask = final_mask & term_mask
        if final_mask.any():
            return FilterSearchCacheManager.clear_result_attrs(df[final_mask])
        return FilterSearchCacheManager.clear_result_attrs(df.iloc[0:0])

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
            group_mask = group_mask & _mask_for_term(term)

        for term in negatives:
            group_mask = group_mask & (~_mask_for_term(term))

        final_mask = final_mask | group_mask

    if final_mask.any():
        return FilterSearchCacheManager.clear_result_attrs(df[final_mask])
    return FilterSearchCacheManager.clear_result_attrs(df.iloc[0:0])
