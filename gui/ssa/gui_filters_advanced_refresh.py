# gui/ssa/gui_filters_advanced_refresh.py
# Relation: prepares advanced-filter option payloads without touching widgets.

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

import pandas as pd
from pandas.api.types import is_datetime64_any_dtype, is_numeric_dtype

from .filter_domain_rules import collect_nonempty_column_values


@dataclass(frozen=True)
class AdvancedFilterOptionValues:
    exec_vals: list[str]
    emis_vals: list[str]
    status_vals: list[str]
    emissao_years: list[int]
    execucao_years: list[int]
    prio_emissao_vals: list[str]
    prio_planejamento_vals: list[str]
    reprog_vals: list[int]


@dataclass(frozen=True)
class AdvancedFilterUIState:
    filters: dict[str, Any]
    values: AdvancedFilterOptionValues


def build_advanced_values_cache_key(
    df: pd.DataFrame, data_load_token: Any
) -> tuple[int, int, tuple[str, ...], Any]:
    return (id(df), len(df), tuple(str(column) for column in df.columns), data_load_token)


def _unique_sorted(df: pd.DataFrame, column: str) -> list[str]:
    if column not in df.columns:
        return []
    vals = collect_nonempty_column_values(df, column)
    return sorted(set(vals), key=lambda value: value.casefold())


def _sort_sector_values(
    values: list[str], sort_sectors: Callable[[list[str]], list[str]]
) -> list[str]:
    try:
        return sort_sectors(values)
    except Exception:
        return sorted(set(values), key=lambda value: str(value).casefold())


def collect_years_from_dates(series: pd.Series) -> list[int]:
    try:
        ts = series if is_datetime64_any_dtype(series) else pd.to_datetime(
            series, errors="coerce"
        )
        years = ts.dt.year.dropna().astype(int).unique()
        return sorted(years, reverse=True)
    except Exception:
        return []


def collect_years_from_weeks(series: pd.Series) -> list[int]:
    try:
        nums = series if is_numeric_dtype(series) else pd.to_numeric(
            series, errors="coerce"
        )
        nums = nums.dropna().astype(int)
        nums = nums[(nums >= 199001) & (nums <= 210053)]
        weeks = nums % 100
        years_series = nums // 100
        years = years_series[
            years_series.between(1990, 2100) & weeks.between(1, 53)
        ].unique()
        return sorted(years, reverse=True)
    except Exception:
        return []


def collect_advanced_filter_option_values(
    df: pd.DataFrame,
    *,
    sort_sectors: Callable[[list[str]], list[str]],
) -> AdvancedFilterOptionValues:
    emissao_years: list[int] = []
    if "data_cadastro" in df.columns:
        emissao_years = collect_years_from_dates(df["data_cadastro"])
    elif "semana_cadastro" in df.columns:
        emissao_years = collect_years_from_weeks(df["semana_cadastro"])

    execucao_years: list[int] = []
    if "semana_executada" in df.columns:
        execucao_years = collect_years_from_weeks(df["semana_executada"])

    reprog_vals: list[int] = []
    if "num_reprogramacoes" in df.columns:
        try:
            reprog_series = pd.to_numeric(
                df["num_reprogramacoes"], errors="coerce"
            ).dropna()
            reprog_vals = sorted(reprog_series.astype(int).unique(), reverse=True)
        except Exception:
            reprog_vals = []

    return AdvancedFilterOptionValues(
        exec_vals=_sort_sector_values(_unique_sorted(df, "setor_executor"), sort_sectors),
        emis_vals=_sort_sector_values(_unique_sorted(df, "setor_emissor"), sort_sectors),
        status_vals=_unique_sorted(df, "situacao"),
        emissao_years=emissao_years,
        execucao_years=execucao_years,
        prio_emissao_vals=_unique_sorted(df, "grau_prioridade_emissao"),
        prio_planejamento_vals=_unique_sorted(df, "grau_prioridade_planejamento"),
        reprog_vals=reprog_vals,
    )


def get_cached_advanced_filter_option_values(
    cache: dict[str, Any],
    df: pd.DataFrame,
    *,
    data_load_token: Any,
    sort_sectors: Callable[[list[str]], list[str]],
) -> AdvancedFilterOptionValues:
    df_key = build_advanced_values_cache_key(df, data_load_token)
    cached_values = cache.get("values")
    if cache.get("df_key") == df_key and isinstance(
        cached_values, AdvancedFilterOptionValues
    ):
        return cached_values
    values = collect_advanced_filter_option_values(df, sort_sectors=sort_sectors)
    cache.clear()
    cache["df_id"] = id(df)
    cache["df_key"] = df_key
    cache["values"] = values
    cache["exec_vals"] = values.exec_vals
    cache["emis_vals"] = values.emis_vals
    cache["status_vals"] = values.status_vals
    cache["emissao_years"] = values.emissao_years
    cache["execucao_years"] = values.execucao_years
    cache["prio_emissao_vals"] = values.prio_emissao_vals
    cache["prio_planejamento_vals"] = values.prio_planejamento_vals
    cache["reprog_vals"] = values.reprog_vals
    return values
