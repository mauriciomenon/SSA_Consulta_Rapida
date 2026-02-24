from __future__ import annotations

import pandas as pd

from dev_env.streamlit_app import (
    StreamlitFilterCache,
    _build_filter_options,
    _compute_df_cache_token,
    _paginate_dataframe,
)


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


def test_paginate_dataframe_clamps_page_and_returns_total_pages() -> None:
    df = pd.DataFrame({"numero_ssa": [f"2025{i:05d}" for i in range(1, 16)]})
    page_df, total_pages = _paginate_dataframe(df, page=99, page_size=10)
    assert total_pages == 2
    assert len(page_df) == 5
    assert page_df.iloc[0]["numero_ssa"] == "202500011"
