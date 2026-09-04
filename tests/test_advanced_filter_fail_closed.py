"""Advanced filters must fail closed when evaluation cannot run.

Regression for the 2026-09-03 laudo class R1: when a filter value is set
but the column is missing, coercion fails, or the mask computation
raises, the advanced stage used to leave the mask unchanged - the filter
became "no restriction" and the table displayed a wrong result set with
only a DEBUG log. The contract now is AdvancedFilterMaskError, which the
filter refresh already catches with a visible warning while preserving
the last dataframe (filter_gui_ssa_mixin._refresh_after_filter_change).
"""

import os
import sys

import pandas as pd
import pytest

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from gui.ssa.gui_filters_advanced_logic import (  # noqa: E402
    AdvancedFilterMaskError,
    _IncludeExcludeSeriesCache,
    _apply_derivada_filter,
    _apply_include_exclude_filters,
    _apply_reprogramacoes_filter,
    _apply_year_emissao_filter,
    _apply_year_execucao_filter,
)

CACHE_TOKEN = 1


class _CacheState:
    def __init__(self):
        self._caches: dict[str, dict] = {}

    def get_cache(self, name: str) -> dict:
        return self._caches.setdefault(name, {})

    def clear_caches(self) -> None:
        self._caches.clear()


def _frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "numero_ssa": [202600001, 202600002, 202600003],
            "setor_executor": ["IEE3", "MEL4", "IEE3"],
            "situacao": ["APV", "STE", "APV"],
            "data_cadastro": ["2026-01-01", "2026-01-02", "2026-01-03"],
            "semana_cadastro": [202601, 202601, 202602],
            "semana_executada": [202602, 202603, 202602],
            "num_reprogramacoes": [0, 1, 2],
            "derivada_de": ["", "202600001", ""],
        }
    )


def _mask(df: pd.DataFrame) -> pd.Series:
    return pd.Series(True, index=df.index)


def test_filter_with_missing_column_raises_instead_of_passing_all():
    df = _frame().drop(columns=["setor_executor"])
    filters = {"setor_executor": ["IEE3"]}
    with pytest.raises(AdvancedFilterMaskError, match="setor_executor"):
        _apply_include_exclude_filters(df, filters, _mask(df), _CacheState(), CACHE_TOKEN)


def test_broken_mask_computation_raises_instead_of_ignoring_filter():
    df = _frame()
    filters = {"setor_executor": ["IEE3"]}

    class _BrokenSeries(pd.Series):
        def isin(self, values):
            raise RuntimeError("boom")

    original_get_str = _IncludeExcludeSeriesCache.get_str

    def broken_get_str(self, col):
        if col == "setor_executor":
            return _BrokenSeries(df[col].values, index=df.index)
        return original_get_str(self, col)

    _IncludeExcludeSeriesCache.get_str = broken_get_str
    try:
        with pytest.raises(AdvancedFilterMaskError, match="include filter"):
            _apply_include_exclude_filters(
                df, filters, _mask(df), _CacheState(), CACHE_TOKEN
            )
    finally:
        _IncludeExcludeSeriesCache.get_str = original_get_str


def test_valid_filter_still_applies_unchanged():
    df = _frame()
    filters = {"setor_executor": ["IEE3"]}
    mask = _apply_include_exclude_filters(df, filters, _mask(df), _CacheState(), CACHE_TOKEN)
    assert mask.tolist() == [True, False, True]

    exclude_filters = {"setor_executor_exclude_values": ["IEE3"]}
    mask = _apply_include_exclude_filters(
        df, exclude_filters, _mask(df), _CacheState(), CACHE_TOKEN
    )
    assert mask.tolist() == [False, True, False]


def test_reprogramacoes_active_with_missing_column_raises():
    df = _frame().drop(columns=["num_reprogramacoes"])
    filters = {
        "num_reprogramacoes_mode": "eq",
        "num_reprogramacoes_values": ["1"],
    }
    with pytest.raises(AdvancedFilterMaskError, match="num_reprogramacoes"):
        _apply_reprogramacoes_filter(df, filters, _mask(df))


def test_ano_emissao_active_without_date_columns_raises():
    df = _frame().drop(columns=["data_cadastro", "semana_cadastro"])
    filters = {"ano_emissao_values": ["2026"]}
    with pytest.raises(AdvancedFilterMaskError, match="ano emissao"):
        _apply_year_emissao_filter(df, filters, _mask(df), _CacheState(), CACHE_TOKEN)


def test_ano_emissao_inactive_without_columns_is_valid():
    df = _frame().drop(columns=["data_cadastro", "semana_cadastro"])
    mask, _ = _apply_year_emissao_filter(
        df, {}, _mask(df), _CacheState(), CACHE_TOKEN
    )
    assert mask.tolist() == [True, True, True]


def test_ano_execucao_active_with_missing_column_raises():
    df = _frame().drop(columns=["semana_executada"])
    filters = {"ano_execucao_values": ["2026"]}
    with pytest.raises(AdvancedFilterMaskError, match="ano execucao"):
        _apply_year_execucao_filter(df, filters, _mask(df))


def test_derivada_active_without_numero_ssa_raises():
    df = _frame().drop(columns=["numero_ssa"])
    filters = {"derivada_has": True}
    with pytest.raises(AdvancedFilterMaskError, match="numero_ssa"):
        _apply_derivada_filter(
            df, filters, _mask(df), _CacheState(), CACHE_TOKEN, lambda series: series
        )


def test_derivada_all_ste_without_situacao_raises():
    df = _frame().drop(columns=["situacao"])
    filters = {"derivada_all_ste": True}
    with pytest.raises(AdvancedFilterMaskError, match="situacao"):
        _apply_derivada_filter(
            df, filters, _mask(df), _CacheState(), CACHE_TOKEN, lambda series: series
        )
