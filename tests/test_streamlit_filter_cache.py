from __future__ import annotations

import pandas as pd

from dev_env.streamlit_app import (
    MAIN_TAB_LABELS,
    MAX_RENDER_TELEMETRY_PROFILES,
    StreamlitFilterCache,
    _api_snapshot_available,
    _clear_recent_api_snapshot,
    _build_table_caption,
    _format_render_stats_line,
    _build_streamlit_column_config,
    _build_column_presets,
    _build_filter_options,
    _compute_df_cache_token,
    _default_visible_columns,
    _normalize_filter_selection,
    _apply_large_page_guard,
    _normalize_width_profile_memory,
    _paginate_dataframe,
    _remember_width_profile_for_bucket,
    _resolve_width_bucket,
    _resolve_width_profile_for_bucket,
    _update_render_telemetry,
    st,
)
from gui.simple_width_manager import SimpleWidthManager


def test_streamlit_filter_cache_compat_methods_work_in_local_fallback() -> None:
    cache = StreamlitFilterCache(max_size=2, ttl_seconds=30)
    cache._use_session_state = False
    cache._local_cache = {}
    cache._local_stats = {"hits": 0, "misses": 0, "evictions": 0, "skipped_large_entries": 0}

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
    cache._local_stats = {"hits": 0, "misses": 0, "evictions": 0, "skipped_large_entries": 0}

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


def test_streamlit_filter_cache_skips_large_entry_when_limit_is_set(monkeypatch) -> None:
    monkeypatch.setenv("SSA_CACHE_MAX_MB", "0.0001")
    cache = StreamlitFilterCache(max_size=2, ttl_seconds=30)
    cache._use_session_state = False
    cache._local_cache = {}
    cache._local_stats = {"hits": 0, "misses": 0, "evictions": 0, "skipped_large_entries": 0}

    large_df = pd.DataFrame({"descricao_ssa": ["x" * 4096, "y" * 4096]})
    cache.cache_filter_result("k_large", large_df)

    stats = cache.get_stats()
    assert stats["size"] == 0
    assert stats["skipped_large_entries"] == 1
    assert stats["max_entry_mb"] is not None


def test_streamlit_filter_cache_keeps_small_entry_when_limit_allows(monkeypatch) -> None:
    monkeypatch.setenv("SSA_CACHE_MAX_MB", "64")
    cache = StreamlitFilterCache(max_size=2, ttl_seconds=30)
    cache._use_session_state = False
    cache._local_cache = {}
    cache._local_stats = {"hits": 0, "misses": 0, "evictions": 0, "skipped_large_entries": 0}

    small_df = pd.DataFrame({"numero_ssa": ["202500001"], "situacao": ["ABERTO"]})
    cache.cache_filter_result("k_small", small_df, {"source": "test"})
    cached = cache.get_cached_filter("k_small")

    stats = cache.get_stats()
    assert cached is not None
    assert stats["skipped_large_entries"] == 0
    assert stats["hits"] >= 1


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


def test_apply_large_page_guard_disabled_by_default(monkeypatch) -> None:
    monkeypatch.delenv("SSA_STREAMLIT_LARGE_PAGE_GUARD", raising=False)
    page_size, changed = _apply_large_page_guard(page_size=2000, filtered_len=5000)
    assert page_size == 2000
    assert changed is False


def test_apply_large_page_guard_limits_page_size_when_enabled(monkeypatch) -> None:
    monkeypatch.setenv("SSA_STREAMLIT_LARGE_PAGE_GUARD", "1")
    page_size, changed = _apply_large_page_guard(page_size=2000, filtered_len=5000)
    assert page_size == 500
    assert changed is True


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


def test_build_table_caption_non_compact() -> None:
    caption = _build_table_caption(
        compact_mode=False,
        page_number=2,
        total_pages=5,
        page_len=250,
        filtered_len=1200,
        render_ms=12.3,
    )
    assert "Exibindo pagina 2/5" in caption
    assert "linhas nesta pagina: 250" in caption


def test_build_table_caption_compact() -> None:
    caption = _build_table_caption(
        compact_mode=True,
        page_number=2,
        total_pages=5,
        page_len=250,
        filtered_len=1200,
        render_ms=12.3,
    )
    assert "Pag 2/5" in caption
    assert "render: 12.3 ms" in caption


def test_update_render_telemetry_updates_session_state(monkeypatch) -> None:
    session_state = {}
    monkeypatch.setattr(st, "session_state", session_state, raising=False)
    _update_render_telemetry("Padrao (1600)", 10.0)
    _update_render_telemetry("Padrao (1600)", 20.0)
    stats = session_state["streamlit_render_stats"]["Padrao (1600)"]
    assert stats["count"] == 2
    assert stats["last_ms"] == 20.0
    assert stats["total_ms"] == 30.0


def test_update_render_telemetry_keeps_profile_window(monkeypatch) -> None:
    session_state = {}
    monkeypatch.setattr(st, "session_state", session_state, raising=False)

    for idx in range(MAX_RENDER_TELEMETRY_PROFILES + 3):
        _update_render_telemetry(f"profile-{idx}", float(idx))

    stats = session_state["streamlit_render_stats"]
    assert len(stats) == MAX_RENDER_TELEMETRY_PROFILES
    assert "profile-0" not in stats
    assert f"profile-{MAX_RENDER_TELEMETRY_PROFILES + 2}" in stats


def test_width_bucket_resolution_thresholds() -> None:
    assert _resolve_width_bucket(1000) == "xs"
    assert _resolve_width_bucket(1400) == "sm"
    assert _resolve_width_bucket(1700) == "md"
    assert _resolve_width_bucket(2100) == "lg"
    assert _resolve_width_bucket(2600) == "xl"


def test_width_profile_memory_normalization_filters_invalid_values() -> None:
    memory = _normalize_width_profile_memory(
        {
            "xs": "Compacto (1200)",
            "md": "Padrao (1600)",
            "bad": "Nao existe",
            "bucket_invalido": "XL (2400)",
        }
    )
    assert memory == {
        "xs": "Compacto (1200)",
        "md": "Padrao (1600)",
    }


def test_width_profile_resolve_and_remember_by_bucket(monkeypatch) -> None:
    session_state = {"streamlit_viewport_width_px": 2100}
    monkeypatch.setattr(st, "session_state", session_state, raising=False)
    table_state = {
        "width_profile": "Padrao (1600)",
        "width_profile_by_bucket": {"lg": "XL (2400)"},
    }

    selected_profile, bucket = _resolve_width_profile_for_bucket(table_state)
    assert bucket == "lg"
    assert selected_profile == "XL (2400)"

    _remember_width_profile_for_bucket(table_state, bucket, "Largo (2000)")
    assert table_state["width_profile_by_bucket"]["lg"] == "Largo (2000)"


def test_width_profile_resolve_ignores_non_positive_viewport_hint(monkeypatch) -> None:
    session_state = {"streamlit_viewport_width_px": 0}
    monkeypatch.setattr(st, "session_state", session_state, raising=False)
    table_state = {"width_profile": "Padrao (1600)", "width_profile_by_bucket": {}}

    selected_profile, bucket = _resolve_width_profile_for_bucket(table_state)

    assert selected_profile == "Padrao (1600)"
    assert bucket == "md"


def test_main_tab_labels_kept_stable() -> None:
    assert MAIN_TAB_LABELS == ["Filtros", "Tabela", "Exportacao", "Cache e API"]


def test_api_snapshot_available_permutations() -> None:
    df = pd.DataFrame({"numero_ssa": ["1"]})
    assert _api_snapshot_available(True, df) is True
    assert _api_snapshot_available(False, df) is False
    assert _api_snapshot_available(True, pd.DataFrame()) is False
    assert _api_snapshot_available(True, None) is False


def test_clear_recent_api_snapshot_updates_session_state(monkeypatch) -> None:
    session_state = {"recent_api_df": pd.DataFrame({"numero_ssa": ["1"]})}
    monkeypatch.setattr(st, "session_state", session_state, raising=False)

    _clear_recent_api_snapshot()

    assert session_state["recent_api_df"] is None


def test_clear_recent_api_snapshot_is_idempotent_without_existing_key(monkeypatch) -> None:
    session_state = {}
    monkeypatch.setattr(st, "session_state", session_state, raising=False)

    _clear_recent_api_snapshot()

    assert "recent_api_df" in session_state
    assert session_state["recent_api_df"] is None


def test_format_render_stats_line_outputs_expected_values() -> None:
    line = _format_render_stats_line(
        "Padrao (1600)",
        {"count": 2, "total_ms": 30.0, "last_ms": 20.0},
    )
    assert "Render tabela (Padrao (1600))" in line
    assert "ultimo 20.0 ms" in line
    assert "media 15.0 ms" in line
