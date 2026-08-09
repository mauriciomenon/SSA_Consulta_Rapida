# gui/ssa/gui_filters_advanced_logic.py
# Relation: applies advanced filters to DataFrame (no UI layout).

from __future__ import annotations

import hashlib

import pandas as pd
from pandas.api import types as pd_types

from shared.date_utils import parse_datetime_series_mixed
from shared.numero_ssa import normalize_relation_id as normalize_numero_ssa_relation
from utils.robust_logging import get_robust_logger

from .gui_filters_advanced_state import (
    SECTOR_TO_DIV,
    AdvancedFilterState,
    prune_adv_cache,
)

logger = get_robust_logger().get_logger(__name__, "gui")
MAX_ADV_CACHE_ENTRIES = 16
_DERIVADA_TERMINAL_STATUSES = frozenset({"STE", "SES"})
RESPONSAVEL_FILTER_COLUMN_CANDIDATES = {
    "solicitante": ("solicitante", "responsavel_solicitante"),
    "responsavel_programacao": ("responsavel_programacao",),
    "responsavel_execucao": ("responsavel_execucao",),
}


def _to_int_set(values):
    result = set()
    for raw in values or []:
        text = str(raw).strip()
        if text.isdigit():
            result.add(int(text))
    return result


def _to_str_set(values):
    result = set()
    for raw in values or []:
        text = str(raw).strip()
        if text:
            result.add(text)
    return result


def _cache_token(
    data_load_request_seq, active_data_load_request_id, fallback_id
) -> int:
    token = (
        data_load_request_seq
        if data_load_request_seq is not None
        else active_data_load_request_id
    )
    payload = repr((token, fallback_id)).encode("utf-8")
    digest = hashlib.blake2b(payload, digest_size=8).hexdigest()
    return int(digest, 16)


def _cache_key(cache_token: int, df: pd.DataFrame, name: str) -> tuple:
    return (cache_token, id(df), df.shape, tuple(df.columns), name)


def _normalize_derivada_relation_series(raw_series: pd.Series) -> pd.Series:
    try:
        series_obj = raw_series.astype("object")
        codes, uniques = pd.factorize(series_obj, sort=False)
        normalized_uniques = [
            normalize_numero_ssa_relation(value) or "" for value in uniques
        ]
        lookup = pd.Series(
            normalized_uniques,
            index=pd.RangeIndex(len(normalized_uniques)),
            dtype="object",
        )
        resolved = pd.Series(codes, index=series_obj.index).map(lookup)
        return resolved.fillna("").astype("object")
    except Exception:
        return raw_series.map(lambda value: normalize_numero_ssa_relation(value) or "")


def _maybe_reset_adv_caches(state: AdvancedFilterState, cache_token: int) -> None:
    if state is None:
        return
    window = getattr(state, "_window", None)
    if window is None:
        return
    if not hasattr(window, "_adv_cache_token"):
        window._adv_cache_token = -1
    prev_token = getattr(window, "_adv_cache_token", None)
    if prev_token == cache_token:
        return
    try:
        state.clear_caches()
    except Exception as exc:
        logger.debug("Falha ao limpar caches avancados: %s", exc)
    setattr(window, "_adv_cache_token", cache_token)


class AdvancedFilterMaskError(RuntimeError):
    """Raised when advanced filter mask.any() evaluation fails."""


def _mask_any(mask, context: str) -> bool:
    try:
        return bool(mask.any())
    except Exception as exc:
        raise AdvancedFilterMaskError(
            f"Failed to evaluate advanced filter mask.any() {context}"
        ) from exc


class _IncludeExcludeSeriesCache:
    def __init__(
        self, df: pd.DataFrame, cache_token: int, state: AdvancedFilterState
    ) -> None:
        self._df = df
        self._cache_token = cache_token
        self._shared_cache = state.get_cache("_adv_str_cache")
        self._cache_enabled = len(df) <= 200000
        self._series_cache: dict[str, pd.Series | None] = {}
        self._numeric_cache: dict[str, pd.Series | None] = {}

    def _get_cached_series(self, col: str, prefix: str) -> pd.Series | None:
        cache_key = _cache_key(self._cache_token, self._df, f"{prefix}::{col}")
        cached = self._shared_cache.get(cache_key) if self._cache_enabled else None
        if isinstance(cached, pd.Series) and len(cached) == len(self._df):
            return cached
        if cached is not None:
            self._shared_cache.pop(cache_key, None)
            prune_adv_cache(self._shared_cache, MAX_ADV_CACHE_ENTRIES)
        return None

    def _store_cached_series(
        self, col: str, prefix: str, series: pd.Series | None
    ) -> None:
        if series is None or not self._cache_enabled:
            return
        cache_key = _cache_key(self._cache_token, self._df, f"{prefix}::{col}")
        self._shared_cache[cache_key] = series
        prune_adv_cache(self._shared_cache, MAX_ADV_CACHE_ENTRIES)

    def get_str(self, col: str) -> pd.Series | None:
        if col in self._series_cache:
            return self._series_cache[col]
        series = self._get_cached_series(col, "str")
        if series is None:
            try:
                series = self._df[col].astype("string").fillna("")
                self._store_cached_series(col, "str", series)
            except Exception as exc:
                logger.debug(
                    "Failed to coerce column %s to str for filters: %s", col, exc
                )
                series = None
        self._series_cache[col] = series
        return series

    def get_numeric(self, col: str) -> pd.Series | None:
        if col in self._numeric_cache:
            return self._numeric_cache[col]
        series = self._get_cached_series(col, "num")
        if series is None:
            try:
                series = pd.to_numeric(self._df[col], errors="coerce")
                self._store_cached_series(col, "num", series)
            except Exception as exc:
                logger.debug(
                    "Failed to coerce column %s to numeric for filters: %s", col, exc
                )
                series = None
        self._numeric_cache[col] = series
        return series

    def clear_local(self) -> None:
        self._series_cache.clear()
        self._numeric_cache.clear()


def _apply_include_exclude_filters(
    df: pd.DataFrame,
    filters: dict,
    mask: pd.Series,
    state: AdvancedFilterState,
    cache_token: int,
) -> pd.Series:
    numeric_columns = {
        "prioridade_emissao",
        "prioridade_planejamento",
        "grau_prioridade_emissao",
        "grau_prioridade_planejamento",
    }
    cache = _IncludeExcludeSeriesCache(df, cache_token, state)
    key_aliases = {
        "solicitante": "responsavel_solicitante",
        "solicitante_exclude_values": "responsavel_solicitante_exclude_values",
    }

    def _get_filter_values(key: str):
        values = filters.get(key)
        if values:
            return values
        alias_key = key_aliases.get(key)
        if alias_key:
            return filters.get(alias_key)
        return values

    column_groups = [
        (("setor_executor",), "setor_executor", "setor_executor_exclude_values"),
        (("setor_emissor",), "setor_emissor", "setor_emissor_exclude_values"),
        (("divisao",), "divisao", "divisao_exclude_values"),
        (("situacao",), "situacao", "situacao_exclude_values"),
        (
            ("grau_prioridade_emissao", "prioridade_emissao"),
            "prioridade_emissao_values",
            "prioridade_emissao_exclude_values",
        ),
        (
            ("grau_prioridade_planejamento", "prioridade_planejamento"),
            "prioridade_planejamento_values",
            "prioridade_planejamento_exclude_values",
        ),
        (
            ("solicitante", "responsavel_solicitante"),
            "solicitante",
            "solicitante_exclude_values",
        ),
        (
            ("responsavel_programacao",),
            "responsavel_programacao",
            "responsavel_programacao_exclude_values",
        ),
        (
            ("responsavel_execucao",),
            "responsavel_execucao",
            "responsavel_execucao_exclude_values",
        ),
    ]
    for candidate_cols, include_key, exclude_key in column_groups:
        col = next((name for name in candidate_cols if name in df.columns), None)
        include_values = _get_filter_values(include_key)
        exclude_values = _get_filter_values(exclude_key)
        if not include_values and not exclude_values:
            continue
        if include_key == "divisao":
            include_values = _to_str_set(include_values)
            exclude_values = _to_str_set(exclude_values)
            series = None
            if "divisao" in df.columns:
                try:
                    series = cache.get_str("divisao")
                    if series is not None:
                        invalid_tokens = {"", "nan", "none", "null"}
                        series = series.where(
                            ~series.str.strip().str.casefold().isin(invalid_tokens), ""
                        )
                except Exception as exc:
                    logger.debug("Failed to read divisao column values: %s", exc)
            try:
                exec_series = (
                    cache.get_str("setor_executor")
                    if "setor_executor" in df.columns
                    else None
                )
                emis_series = (
                    cache.get_str("setor_emissor")
                    if "setor_emissor" in df.columns
                    else None
                )
                if exec_series is not None or emis_series is not None:
                    if exec_series is None:
                        exec_series = pd.Series("", index=df.index)
                    if emis_series is None:
                        emis_series = pd.Series("", index=df.index)
                    div_exec = exec_series.map(SECTOR_TO_DIV).fillna("").astype(str)
                    div_emis = emis_series.map(SECTOR_TO_DIV).fillna("").astype(str)
                    derived_series = div_exec.where(div_exec != "", div_emis)
                    if series is None:
                        series = derived_series
                    else:
                        series = series.where(series != "", derived_series)
            except Exception as exc:
                logger.debug(
                    "Failed to derive divisao values from sector columns: %s", exc
                )
            if series is None:
                continue
        elif col in numeric_columns:
            series = cache.get_numeric(col)
            include_values = _to_int_set(include_values or [])
            exclude_values = _to_int_set(exclude_values or [])
        else:
            if col is None:
                continue
            series = cache.get_str(col)
        if series is None:
            continue
        if include_values:
            try:
                mask_include = series.isin(include_values)
                mask &= mask_include
            except Exception as exc:
                logger.debug("Failed to apply include filter for %s: %s", col, exc)
        if exclude_values:
            try:
                mask_exclude = series.isin(exclude_values)
                mask &= ~mask_exclude
            except Exception as exc:
                logger.debug("Failed to apply exclude filter for %s: %s", col, exc)

    cache.clear_local()
    return mask


def _apply_reprogramacoes_filter(
    df: pd.DataFrame, filters: dict, mask: pd.Series
) -> pd.Series:
    try:
        mode = filters.get("num_reprogramacoes_mode")
        values = filters.get("num_reprogramacoes_values")
        if mode and values:
            vals = [int(v) for v in values if str(v).isdigit()]
            if vals and "num_reprogramacoes" in df.columns:
                nums = (
                    pd.to_numeric(df["num_reprogramacoes"], errors="coerce")
                    .fillna(-1)
                    .astype(float)
                )
                vals_sorted = sorted(vals)
                if mode == "eq":
                    mask &= nums.isin(vals)
                elif mode == "lte":
                    threshold = max(vals_sorted)
                    mask &= nums <= threshold
                elif mode == "gte":
                    threshold = min(vals_sorted)
                    mask &= nums >= threshold
    except Exception as exc:
        logger.debug("Failed to apply reprogramacoes advanced filter: %s", exc)
    return mask


def _compute_years_from_data_cadastro(
    series: pd.Series,
) -> tuple[pd.Series, str | None]:
    notice = None
    if pd_types.is_numeric_dtype(series):
        ts = pd.to_datetime(series, errors="coerce", dayfirst=True)
    else:
        ts = parse_datetime_series_mixed(series)
    if pd_types.is_numeric_dtype(series):
        nums = pd.to_numeric(series, errors="coerce")
        num_mask = nums.notna() & nums.gt(0)
        if num_mask.any():
            base = pd.Timestamp("1899-12-30")
            replacement = base + pd.to_timedelta(nums, unit="D")
            ts = ts.where(~num_mask, replacement)
    if ts.isna().any():
        notice = "ano_emissao_parse_skipped"
        logger.debug(
            "Skipping non-vectorized ano emissao parsing for %s values",
            int(ts.isna().sum()),
        )
    valid_years = ts.dt.year
    valid_years = valid_years.where(valid_years.between(1980, 2100))
    return valid_years, notice


def _compute_years_from_semana(series: pd.Series) -> pd.Series:
    nums = pd.to_numeric(series, errors="coerce").astype("Int64")
    return (nums // 100).astype("Int64")


def _apply_year_emissao_filter(
    df: pd.DataFrame,
    filters: dict,
    mask: pd.Series,
    state: AdvancedFilterState,
    cache_token: int,
) -> tuple[pd.Series, str | None]:
    notice = None
    emissao_inc = _to_int_set(filters.get("ano_emissao_values") or [])
    emissao_exc = _to_int_set(filters.get("ano_emissao_exclude_values") or [])
    exclude_value = filters.get("ano_emissao_exclude")
    exclude_flag = exclude_value is True
    if exclude_value not in (None, False, True):
        emissao_exc = _to_int_set([exclude_value])
        exclude_flag = False
    # Precedence: explicit exclude values > exclude flag with ano_emissao > include values.
    if not emissao_exc and exclude_flag and filters.get("ano_emissao") is not None:
        emissao_exc = _to_int_set([filters.get("ano_emissao")])
    if (
        not emissao_inc
        and not emissao_exc
        and filters.get("ano_emissao") is not None
        and exclude_value in (None, False, True)
    ):
        emissao_inc = _to_int_set([filters.get("ano_emissao")])

    if emissao_inc or emissao_exc:
        if "data_cadastro" in df.columns:
            try:
                cache_key = _cache_key(cache_token, df, "data_cadastro")
                cache = state.get_cache("_adv_year_emissao_cache")
                years = None
                cached = cache.get(cache_key)
                if isinstance(cached, pd.Series) and len(cached) == len(df):
                    years = cached
                elif cached is not None:
                    cache.pop(cache_key, None)
                if years is None:
                    years, notice = _compute_years_from_data_cadastro(
                        df["data_cadastro"]
                    )
                    cache[cache_key] = years
                    prune_adv_cache(cache, MAX_ADV_CACHE_ENTRIES)
                if emissao_inc:
                    mask &= years.isin(emissao_inc)
                if emissao_exc:
                    mask &= ~years.isin(emissao_exc)
            except Exception as exc:
                logger.debug(
                    "Failed to apply ano emissao filter from data_cadastro: %s", exc
                )
        elif "semana_cadastro" in df.columns:
            try:
                years = _compute_years_from_semana(df["semana_cadastro"])
                if emissao_inc:
                    mask &= years.isin(emissao_inc)
                if emissao_exc:
                    mask &= ~years.isin(emissao_exc)
            except Exception as exc:
                logger.debug(
                    "Failed to apply ano emissao filter from semana_cadastro: %s", exc
                )

    return mask, notice


def _apply_year_execucao_filter(
    df: pd.DataFrame, filters: dict, mask: pd.Series
) -> pd.Series:
    execucao_inc = _to_int_set(filters.get("ano_execucao_values") or [])
    execucao_exc = _to_int_set(filters.get("ano_execucao_exclude_values") or [])
    exclude_value = filters.get("ano_execucao_exclude")
    exclude_flag = exclude_value is True
    if exclude_value not in (None, False, True):
        execucao_exc = _to_int_set([exclude_value])
        exclude_flag = False
    # Precedence: explicit exclude values > exclude flag with ano_execucao > include values.
    if not execucao_exc and exclude_flag and filters.get("ano_execucao") is not None:
        execucao_exc = _to_int_set([filters.get("ano_execucao")])
    if (
        not execucao_inc
        and not execucao_exc
        and filters.get("ano_execucao") is not None
        and exclude_value in (None, False, True)
    ):
        execucao_inc = _to_int_set([filters.get("ano_execucao")])

    if execucao_inc or execucao_exc:
        if "semana_executada" in df.columns:
            try:
                nums = pd.to_numeric(df["semana_executada"], errors="coerce").astype(
                    "Int64"
                )
                years = (nums // 100).astype("Int64")
                if execucao_inc:
                    mask &= years.isin(execucao_inc)
                if execucao_exc:
                    mask &= ~years.isin(execucao_exc)
            except Exception as exc:
                logger.debug(
                    "Failed to apply ano execucao filter from semana_executada: %s", exc
                )

    return mask


def _apply_week_range_filters(
    df: pd.DataFrame, filters: dict, mask: pd.Series
) -> pd.Series:
    def _apply_week_range(col: str, start_key: str, end_key: str, exclude_key: str):
        nonlocal mask
        start = filters.get(start_key)
        end = filters.get(end_key)
        if start is None and end is None:
            return
        try:
            nums = pd.to_numeric(df[col], errors="coerce")
            range_mask = pd.Series(True, index=df.index)
            start_val = (
                pd.to_numeric(start, errors="coerce") if start is not None else None
            )
            end_val = pd.to_numeric(end, errors="coerce") if end is not None else None
            if start_val is not None and not pd.isna(start_val):
                range_mask &= nums.ge(int(start_val))
            if end_val is not None and not pd.isna(end_val):
                range_mask &= nums.le(int(end_val))
            range_mask = range_mask.fillna(False).astype(bool)
            if filters.get(exclude_key):
                mask &= ~range_mask
            else:
                mask &= range_mask
        except Exception as exc:
            logger.debug("Failed to apply week range filter '%s': %s", col, exc)

    _apply_week_range(
        "semana_cadastro",
        "semana_emissao_inicio",
        "semana_emissao_fim",
        "semana_emissao_exclude",
    )
    _apply_week_range(
        "semana_executada",
        "semana_execucao_inicio",
        "semana_execucao_fim",
        "semana_execucao_exclude",
    )

    return mask


def _compute_derivada_all_ste_origins(
    df: pd.DataFrame, series_derivada: pd.Series, has_derivada: pd.Series
) -> set:
    # Compatibilidade: mantemos o nome legado "all_ste", mas SES agora entra
    # na mesma classe funcional de derivada terminal para este filtro.
    situacao_series = df.loc[has_derivada, "situacao"].astype("string").fillna("")
    derivada_series = (
        series_derivada[has_derivada].astype("string").fillna("").str.strip()
    )
    valid_derivada = derivada_series != ""
    if not bool(valid_derivada.any()):
        return set()
    situacao = (
        situacao_series[valid_derivada].str.upper().isin(_DERIVADA_TERMINAL_STATUSES)
    )
    grouped = situacao.groupby(derivada_series[valid_derivada]).all()
    return set(grouped[grouped].index.tolist())


def _build_derivadas_tree(
    window,
    df: pd.DataFrame,
    numero_col: str,
    derivada_col: str,
    *,
    cache_token: int,
    normalize_ssa_series,
):
    """Constroi arvore de derivadas com normalizacao robusta de SSA."""
    if not callable(normalize_ssa_series):
        return {}, {}
    state = AdvancedFilterState(window)
    return _build_derivadas_tree_core(
        df, numero_col, derivada_col, state, cache_token, normalize_ssa_series
    )


def _build_derivadas_tree_core(
    df: pd.DataFrame,
    numero_col: str,
    derivada_col: str,
    state: AdvancedFilterState,
    cache_token: int,
    normalize_ssa_series,
):
    mae_filhas_set: dict[str, set[str]] = {}
    mae_filhas: dict[str, list[str]] = {}
    filha_mae: dict[str, str] = {}
    if df is None or df.empty:
        return mae_filhas, filha_mae
    if numero_col not in df.columns or derivada_col not in df.columns:
        return mae_filhas, filha_mae

    try:
        norm_cache = state.get_cache("_adv_norm_cache")
        num_key = _cache_key(cache_token, df, "numero_ssa")
        deriv_key = _cache_key(cache_token, df, "derivada_de")
        numero_series = norm_cache.get(num_key)
        derivada_series = norm_cache.get(deriv_key)
        if not isinstance(numero_series, pd.Series) or len(numero_series) != len(df):
            numero_series = _normalize_derivada_relation_series(df[numero_col])
            norm_cache[num_key] = numero_series
        if not isinstance(derivada_series, pd.Series) or len(derivada_series) != len(
            df
        ):
            derivada_series = _normalize_derivada_relation_series(df[derivada_col])
            norm_cache[deriv_key] = derivada_series
        prune_adv_cache(norm_cache, MAX_ADV_CACHE_ENTRIES)
    except Exception:
        return mae_filhas, filha_mae

    try:
        clean_cache = state.get_cache("_adv_clean_cache")
        clean_num_key = _cache_key(cache_token, df, "clean_numero")
        clean_deriv_key = _cache_key(cache_token, df, "clean_derivada")
        numero_clean = clean_cache.get(clean_num_key)
        derivada_clean = clean_cache.get(clean_deriv_key)
        if not isinstance(numero_clean, pd.Series) or len(numero_clean) != len(df):
            numero_clean = numero_series.astype("string").fillna("").str.strip()
            clean_cache[clean_num_key] = numero_clean
        if not isinstance(derivada_clean, pd.Series) or len(derivada_clean) != len(df):
            derivada_clean = derivada_series.astype("string").fillna("").str.strip()
            clean_cache[clean_deriv_key] = derivada_clean
        prune_adv_cache(clean_cache, MAX_ADV_CACHE_ENTRIES)
        pairs = pd.DataFrame(
            {
                "numero": numero_clean,
                "derivada": derivada_clean,
            }
        )
        invalid_tokens = {"", "nan", "none", "null"}
        numero_cf = pairs["numero"].fillna("").str.casefold()
        derivada_cf = pairs["derivada"].fillna("").str.casefold()
        valid_mask = ~numero_cf.isin(invalid_tokens) & ~derivada_cf.isin(invalid_tokens)
        pairs = pairs[valid_mask]
    except Exception:
        return mae_filhas, filha_mae

    try:
        for numero, derivada in pairs[["numero", "derivada"]].itertuples(
            index=False,
            name=None,
        ):
            numero_key = str(numero)
            derivada_key = str(derivada)
            previous = filha_mae.get(numero_key)
            if previous is not None and previous != derivada_key:
                logger.warning(
                    "Duplicate derivada child %s has conflicting parents %s and %s; "
                    "keeping first parent",
                    numero_key,
                    previous,
                    derivada_key,
                )
                continue
            filha_mae.setdefault(numero_key, derivada_key)
    except Exception:
        filha_mae = {}

    try:
        for numero, derivada in filha_mae.items():
            mae_filhas_set.setdefault(derivada, set()).add(numero)
    except Exception:
        mae_filhas_set = {}

    def _casefold_sort_key(value) -> str:
        return str(value).casefold()

    for mae, filhas in list(mae_filhas_set.items()):
        if len(filhas) <= 1:
            mae_filhas[mae] = list(filhas)
        else:
            mae_filhas[mae] = sorted(filhas, key=_casefold_sort_key)

    return mae_filhas, filha_mae


def _apply_derivada_filter(
    df: pd.DataFrame,
    filters: dict,
    mask: pd.Series,
    state: AdvancedFilterState,
    cache_token: int,
    normalize_ssa_series,
):
    if not callable(normalize_ssa_series):
        logger.debug(
            "Skipping derivada filters because normalize_ssa_series is unavailable."
        )
        return mask, None

    derivada_has = bool(filters.get("derivada_has"))
    derivada_all_ste = bool(filters.get("derivada_all_ste"))
    derivada_is = bool(filters.get("derivada_is"))

    if "derivada_de" not in df.columns:
        return mask, None

    norm_cache = state.get_cache("_adv_norm_cache")
    deriv_key = _cache_key(cache_token, df, "derivada_de")
    series_derivada = norm_cache.get(deriv_key)
    if not isinstance(series_derivada, pd.Series) or len(series_derivada) != len(df):
        series_derivada = _normalize_derivada_relation_series(df["derivada_de"])
        norm_cache[deriv_key] = series_derivada
        prune_adv_cache(norm_cache, MAX_ADV_CACHE_ENTRIES)
    has_derivada = series_derivada.ne("")
    if derivada_is:
        mask &= has_derivada

    if (derivada_has or derivada_all_ste) and not bool(has_derivada.any()):
        if derivada_all_ste:
            return mask, "derivada_all_ste_empty"
        if derivada_has:
            return mask, "derivada_empty"

    if (derivada_has or derivada_all_ste) and "numero_ssa" in df.columns:
        origins_error = False
        origins = set()
        if derivada_all_ste and "situacao" in df.columns:
            cache = state.get_cache("_adv_values_cache")
            cache_key = _cache_key(cache_token, df, "derivada_all_ste_origins")
            cached = cache.get(cache_key)
            if isinstance(cached, set):
                origins = cached
            else:
                try:
                    origins = _compute_derivada_all_ste_origins(
                        df, series_derivada, has_derivada
                    )
                    cache[cache_key] = origins
                    prune_adv_cache(cache, MAX_ADV_CACHE_ENTRIES)
                except Exception as exc:
                    logger.debug(
                        "Failed to compute derivada_all_ste origin set: %s", exc
                    )
                    origins_error = True
                    origins = set()
        else:
            try:
                origins = set(series_derivada[has_derivada].unique())
            except Exception:
                origins_error = True
                origins = set()

        if origins:
            try:
                origin_norm = {str(o) for o in origins if str(o).strip()}
                num_key = _cache_key(cache_token, df, "numero_ssa")
                numero_norm = norm_cache.get(num_key)
                if not isinstance(numero_norm, pd.Series) or len(numero_norm) != len(
                    df
                ):
                    numero_norm = _normalize_derivada_relation_series(df["numero_ssa"])
                    norm_cache[num_key] = numero_norm
                    prune_adv_cache(norm_cache, MAX_ADV_CACHE_ENTRIES)
                mask &= numero_norm.isin(origin_norm)
            except Exception as exc:
                logger.debug(
                    "Failed to apply derivada origin filter to numero_ssa: %s", exc
                )
        elif origins_error:
            logger.debug("Skipping derivada filter due to origin calculation failure.")
        else:
            if derivada_all_ste:
                return mask, "derivada_all_ste_empty"
            if derivada_has:
                return mask, "derivada_empty"

    return mask, None


def _emit_notice(callback, notice: str | None) -> None:
    if not notice:
        return
    if callable(callback):
        try:
            callback(notice)
        except Exception as exc:
            logger.debug("Failed to notify advanced filter notice: %s", exc)


def _apply_advanced_filters(
    window,
    df: pd.DataFrame,
    *,
    cache_token: int,
    normalize_ssa_series,
    notice_callback=None,
) -> pd.DataFrame:
    if df is None or df.empty:
        return df

    state = AdvancedFilterState(window)
    _maybe_reset_adv_caches(state, cache_token)
    if not callable(normalize_ssa_series):
        normalize_ssa_series = None
    filters = state.filters
    if not filters:
        return df

    mask = pd.Series(True, index=df.index)
    mask = _apply_include_exclude_filters(df, filters, mask, state, cache_token)
    mask = _apply_reprogramacoes_filter(df, filters, mask)

    if not _mask_any(mask, "after reprogramacoes"):
        return df.iloc[0:0]

    mask, year_notice = _apply_year_emissao_filter(
        df, filters, mask, state, cache_token
    )
    _emit_notice(notice_callback, year_notice)
    mask = _apply_year_execucao_filter(df, filters, mask)
    mask = _apply_week_range_filters(df, filters, mask)

    if not _mask_any(mask, "after week ranges"):
        return df.iloc[0:0]

    mask, notice = _apply_derivada_filter(
        df, filters, mask, state, cache_token, normalize_ssa_series
    )
    _emit_notice(notice_callback, notice)

    if mask.all():
        return df
    return df[mask]
