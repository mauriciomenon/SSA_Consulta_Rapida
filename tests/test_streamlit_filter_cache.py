from __future__ import annotations

import pandas as pd

from dev_env.streamlit_app import (
    StreamlitFilterCache,
    _build_streamlit_column_config,
    _build_column_presets,
    _build_filter_options,
    _compute_df_cache_token,
    _default_visible_columns,
    _normalize_filter_selection,
    _paginate_dataframe,
    st,
)
from gui.simple_width_manager import SimpleWidthManager


def test_streamlit_filter_cache_compat_methods_work_in_local_fallback() -> None:
    cache = StreamlitFilterCache(max_size=2, ttl_seconds=30)
    cache._use_session_state = False
    cache._local_cache = {}
    cache._local_stats = {"hits": 0, "misses": 0, "evictions": 0}

    data = pd.DataFrame({"numero_ssa": ["202500001"], "situacao": ["ABERTO"]})
    cache.cache_filter_result("k1", data, {"source": "test"})
    cached = cache.get_cached_filter("k1")

    assert cached is not None
    assert cached.equals(data)
    stats = cache.get_stats()
    assert stats["hits"] == 1
    assert stats["misses"] == 0


def test_streamlit_filter_cache_key_token_distinguishes_same_shape_data() -> None:
    cache = StreamlitFilterCache(max_size=2, ttl_seconds=30)
    cache._use_session_state = False
    cache._local_cache = {}
    cache._local_stats = {"hits": 0, "misses": 0, "evictions": 0}

    df1 = pd.DataFrame(
        {
            "numero_ssa": ["202500001", "202500002"],
            "situacao": ["ABERTO", "ABERTO"],
        }
    )
    df2 = pd.DataFrame(
        {
            "numero_ssa": ["202599991", "202599992"],
            "situacao": ["ABERTO", "ABERTO"],
        }
    )

    token1 = _compute_df_cache_token(df1)
    token2 = _compute_df_cache_token(df2)
    assert token1 != token2

    cache.put(df1.shape, "", [], [], [], df1, df_token=token1)
    assert cache.get(df1.shape, "", [], [], [], df_token=token1) is not None
    assert cache.get(df2.shape, "", [], [], [], df_token=token2) is None


def test_build_filter_options_handles_missing_columns() -> None:
    df = pd.DataFrame({"numero_ssa": ["202500001"]})
    situacoes, executores, emissores = _build_filter_options(df)
    assert situacoes == []
    assert executores == []
    assert emissores == []


def test_build_filter_options_allows_mixed_types() -> None:
    df = pd.DataFrame(
        {
            "situacao": ["ABERTO", 100, "EM_EXECUCAO"],
            "setor_executor": ["IEE3", 7, "MEL4"],
            "setor_emissor": ["IEE3", 8, "MEL5"],
        }
    )
    situacoes, executores, emissores = _build_filter_options(df)
    assert len(situacoes) == 3
    assert len(executores) == 3
    assert len(emissores) == 3


def test_paginate_dataframe_clamps_page_and_returns_total_pages() -> None:
    df = pd.DataFrame({"numero_ssa": [f"2025{i:05d}" for i in range(1, 16)]})
    page_df, total_pages = _paginate_dataframe(df, page=99, page_size=10)
    assert total_pages == 2
    assert len(page_df) == 5
    assert page_df.iloc[0]["numero_ssa"] == "202500011"


def test_normalize_filter_selection_collapses_full_selection() -> None:
    options = ["A", "B", "C"]
    assert _normalize_filter_selection(["A", "B", "C"], options) == []
    assert _normalize_filter_selection(["A"], options) == ["A"]


def test_default_visible_columns_prefers_core_columns() -> None:
    columns = ["id", "numero_ssa", "situacao", "descricao_ssa", "outro"]
    out = _default_visible_columns(columns)
    assert out == ["numero_ssa", "situacao", "descricao_ssa"]


def test_build_column_presets_contains_core_and_all() -> None:
    columns = ["numero_ssa", "situacao", "descricao_ssa", "x"]
    presets = _build_column_presets(columns)
    assert presets["all"] == columns
    assert presets["core"] == ["numero_ssa", "situacao", "descricao_ssa"]


def test_compute_df_cache_token_handles_rows_without_columns() -> None:
    df = pd.DataFrame(index=[0, 1, 2])
    token = _compute_df_cache_token(df)
    assert token == (3, tuple(), None, None)


def test_build_streamlit_column_config_uses_rename_map() -> None:
    df = pd.DataFrame(
        {
            "numero_ssa": ["202500001"],
            "situacao": ["ABERTO"],
            "data_cadastro": ["2025-01-01"],
        }
    )
    rename_map = {
        "numero_ssa": "Numero SSA",
        "situacao": "Situacao",
        "data_cadastro": "Data Cadastro",
    }
    config = _build_streamlit_column_config(df, rename_map, available_width=1200)
    if getattr(st, "column_config", None) is None:
        assert config == {}
    else:
        assert set(config.keys()) == {"Numero SSA", "Situacao", "Data Cadastro"}


def test_simple_width_manager_prioritizes_descricao_columns() -> None:
    manager = SimpleWidthManager()
    df = pd.DataFrame(
        {
            "descricao_ssa": ["texto curto"],
            "descricao_execucao": ["texto curto"],
            "situacao": ["ABERTO"],
        }
    )
    buckets = manager.compute_streamlit_width_buckets(
        df,
        available_width=1200,
        column_order=list(df.columns),
    )
    assert buckets["descricao_ssa"] == "large"
    assert buckets["descricao_execucao"] == "large"
