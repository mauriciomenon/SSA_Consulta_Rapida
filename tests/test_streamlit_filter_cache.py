from __future__ import annotations

from datetime import datetime

import pandas as pd

from dev_env.streamlit_app import (
    APP_VERSION,
    DEFAULT_STREAMLIT_THEME,
    MAIN_TAB_LABELS,
    MAX_RENDER_TELEMETRY_PROFILES,
    STREAMLIT_APP_TITLE,
    STREAMLIT_THEME_PALETTES,
    StreamlitFilterCache,
    _api_snapshot_available,
    _apply_large_page_guard,
    _build_advanced_filter_options,
    _build_column_presets,
    _build_filter_options,
    _build_streamlit_column_config,
    _build_streamlit_theme_css,
    _build_table_caption,
    _clear_recent_api_snapshot,
    _columns_with_data,
    _compute_df_cache_token,
    _compute_sidebar_weekly_kpis,
    _compute_table_render_height,
    _default_visible_columns,
    _format_render_stats_line,
    _load_persisted_streamlit_state,
    _normalize_filter_selection,
    _normalize_streamlit_theme_name,
    _normalize_width_profile_memory,
    _paginate_dataframe,
    _persist_streamlit_state,
    _remember_width_profile_for_bucket,
    _resolve_situacao_quick_mode,
    _resolve_streamlit_ui_state_path,
    _resolve_width_bucket,
    _resolve_width_profile_for_bucket,
    _update_render_telemetry,
    apply_all_filters_cached,
    st,
)
from gui.gui_config import DEFAULT_COLUMN_WIDTHS
from gui.simple_width_manager import SimpleCacheManager, SimpleWidthManager


def test_streamlit_filter_cache_compat_methods_work_in_local_fallback() -> None:
    cache = StreamlitFilterCache(max_size=2, ttl_seconds=30)
    cache._use_session_state = False
    cache._local_cache = {}
    cache._local_stats = {
        "hits": 0,
        "misses": 0,
        "evictions": 0,
        "skipped_large_entries": 0,
    }

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
    cache._local_stats = {
        "hits": 0,
        "misses": 0,
        "evictions": 0,
        "skipped_large_entries": 0,
    }

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


def test_streamlit_filter_cache_stats_parity_between_main_and_compat_methods() -> None:
    cache = StreamlitFilterCache(max_size=1, ttl_seconds=30)
    cache._use_session_state = False
    cache._local_cache = {}
    cache._local_stats = {
        "hits": 0,
        "misses": 0,
        "evictions": 0,
        "skipped_large_entries": 0,
    }

    df1 = pd.DataFrame({"numero_ssa": ["202500001"]})
    df2 = pd.DataFrame({"numero_ssa": ["202500002"]})

    cache.put(df1.shape, "a", [], [], [], df1, df_token=("k1",))
    cache.cache_filter_result("compat_key", df2)

    stats = cache.get_stats()
    assert stats["evictions"] == 1
    assert stats["size"] == 1


def test_streamlit_filter_cache_skips_large_entry_when_limit_is_set(
    monkeypatch,
) -> None:
    monkeypatch.setenv("SSA_CACHE_MAX_MB", "0.0001")
    cache = StreamlitFilterCache(max_size=2, ttl_seconds=30)
    cache._use_session_state = False
    cache._local_cache = {}
    cache._local_stats = {
        "hits": 0,
        "misses": 0,
        "evictions": 0,
        "skipped_large_entries": 0,
    }

    large_df = pd.DataFrame({"descricao_ssa": ["x" * 4096, "y" * 4096]})
    cache.cache_filter_result("k_large", large_df)

    stats = cache.get_stats()
    assert stats["size"] == 0
    assert stats["skipped_large_entries"] == 1
    assert stats["max_entry_mb"] is not None


def test_streamlit_filter_cache_keeps_small_entry_when_limit_allows(
    monkeypatch,
) -> None:
    monkeypatch.setenv("SSA_CACHE_MAX_MB", "64")
    cache = StreamlitFilterCache(max_size=2, ttl_seconds=30)
    cache._use_session_state = False
    cache._local_cache = {}
    cache._local_stats = {
        "hits": 0,
        "misses": 0,
        "evictions": 0,
        "skipped_large_entries": 0,
    }

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


def test_build_advanced_filter_options_collects_new_filters() -> None:
    df = pd.DataFrame(
        {
            "responsavel_execucao": ["A", "B", "A"],
            "situacao": ["ABERTO", "EXECUTADA", "ABERTO"],
            "data_cadastro": ["2025-01-02", "2024-12-31", "2025-01-09"],
            "semana_executada": [202503, 202452, 202504],
            "num_reprogramacoes": [0, 2, 2],
        }
    )
    options = _build_advanced_filter_options(df)
    assert options["executor_resp"] == ["A", "B"]
    assert options["estado"] == ["ABERTO", "EXECUTADA"]
    assert 2025 in options["ano_emissao"]
    assert 2024 in options["ano_execucao"]
    assert 0 in options["num_reprogramacoes"]
    assert 2 in options["num_reprogramacoes"]


def test_apply_all_filters_cached_applies_advanced_executor_and_reprog() -> None:
    df = pd.DataFrame(
        {
            "numero_ssa": ["1", "2", "3"],
            "situacao": ["ABERTO", "ABERTO", "EXECUTADA"],
            "setor_executor": ["IEE3", "IEE4", "IEE3"],
            "setor_emissor": ["IEE3", "MEL1", "IEE3"],
            "responsavel_execucao": ["JOAO", "MARIA", "JOAO"],
            "num_reprogramacoes": [0, 2, 3],
        }
    )
    out = apply_all_filters_cached(
        df,
        "",
        [],
        [],
        [],
        advanced_filters={
            "executor_resp": ["JOAO"],
            "num_reprogramacoes": [3],
        },
    )
    assert out["numero_ssa"].tolist() == ["3"]


def test_apply_all_filters_cached_applies_derivada_structure_filters() -> None:
    df = pd.DataFrame(
        {
            "numero_ssa": ["10", "11", "12"],
            "situacao": ["ABERTO", "ABERTO", "ABERTO"],
            "setor_executor": ["IEE3", "IEE3", "IEE3"],
            "setor_emissor": ["IEE3", "IEE3", "IEE3"],
            "derivada_de": ["", "10", ""],
        }
    )
    out_has = apply_all_filters_cached(
        df,
        "",
        [],
        [],
        [],
        advanced_filters={"tem_derivada": "sim", "tem_derivadas": "todos"},
    )
    out_children = apply_all_filters_cached(
        df,
        "",
        [],
        [],
        [],
        advanced_filters={"tem_derivada": "todos", "tem_derivadas": "sim"},
    )
    assert out_has["numero_ssa"].tolist() == ["11"]
    assert out_children["numero_ssa"].tolist() == ["10"]


def test_apply_all_filters_cached_supports_manual_exclude_for_estado() -> None:
    df = pd.DataFrame(
        {
            "numero_ssa": ["1", "2", "3"],
            "situacao": ["STE", "ATE", "STE"],
            "setor_executor": ["IEE3", "IEE3", "IEE4"],
            "setor_emissor": ["IEE2", "IEE2", "IEE1"],
        }
    )
    out = apply_all_filters_cached(
        df,
        "",
        [],
        [],
        [],
        advanced_filters={
            "estado_exclude": ["STE"],
        },
    )
    assert out["numero_ssa"].tolist() == ["2"]


def test_apply_all_filters_cached_supports_manual_exclude_for_reprogramacoes() -> None:
    df = pd.DataFrame(
        {
            "numero_ssa": ["1", "2", "3"],
            "situacao": ["ABERTO", "ABERTO", "ABERTO"],
            "setor_executor": ["IEE3", "IEE3", "IEE3"],
            "setor_emissor": ["IEE2", "IEE2", "IEE2"],
            "num_reprogramacoes": [0, 1, 2],
        }
    )
    out = apply_all_filters_cached(
        df,
        "",
        [],
        [],
        [],
        advanced_filters={
            "num_reprogramacoes_exclude": [1],
        },
    )
    assert out["numero_ssa"].tolist() == ["1", "3"]


def test_apply_all_filters_cached_supports_manual_date_conditions_with_not() -> None:
    df = pd.DataFrame(
        {
            "numero_ssa": ["1", "2", "3"],
            "situacao": ["ABERTO", "ABERTO", "ABERTO"],
            "setor_executor": ["IEE3", "IEE3", "IEE3"],
            "setor_emissor": ["IEE2", "IEE2", "IEE2"],
            "data_cadastro": ["2024-01-10", "2024-01-15", "2024-01-25"],
            "semana_executada": [202402, 202403, 202404],
        }
    )
    out = apply_all_filters_cached(
        df,
        "",
        [],
        [],
        [],
        advanced_filters={
            "data_emissao_inicio": "2024-01-10",
            "data_emissao_fim": "!2024-01-25",
        },
    )
    assert out["numero_ssa"].tolist() == ["1", "2"]


def test_apply_all_filters_cached_supports_execucao_date_not_equal() -> None:
    df = pd.DataFrame(
        {
            "numero_ssa": ["1", "2", "3"],
            "situacao": ["ABERTO", "ABERTO", "ABERTO"],
            "setor_executor": ["IEE3", "IEE3", "IEE3"],
            "setor_emissor": ["IEE2", "IEE2", "IEE2"],
            "semana_executada": [202402, 202403, 202404],
        }
    )
    out = apply_all_filters_cached(
        df,
        "",
        [],
        [],
        [],
        advanced_filters={
            "data_execucao_inicio": "!2024-01-15",
        },
    )
    assert out["numero_ssa"].tolist() == ["1", "3"]


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


def test_resolve_situacao_quick_mode_options() -> None:
    situacoes = ["EXECUTADA", "ABERTO", "AAT"]
    assert _resolve_situacao_quick_mode(situacoes, [], "Todas") == situacoes
    assert _resolve_situacao_quick_mode(situacoes, [], "Executadas") == ["EXECUTADA"]
    assert _resolve_situacao_quick_mode(situacoes, [], "Abertas") == ["ABERTO", "AAT"]
    assert _resolve_situacao_quick_mode(situacoes, ["AAT"], "Manual") == ["AAT"]
    assert _resolve_situacao_quick_mode(situacoes, ["AAT"], "Nenhuma") == []


def test_columns_with_data_filters_empty_columns() -> None:
    df = pd.DataFrame(
        {
            "numero_ssa": ["1", "2"],
            "vazia": [None, None],
            "status": ["ABERTO", None],
        }
    )
    out = _columns_with_data(df, ["numero_ssa", "vazia", "status"])
    assert out == ["numero_ssa", "status"]


def test_compute_table_render_height_is_bounded() -> None:
    assert _compute_table_render_height(page_len=1, configured_height=600) == 220
    assert _compute_table_render_height(page_len=100, configured_height=300) == 300


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


def test_simple_width_manager_uses_canonical_baseline_for_fixed_columns() -> None:
    manager = SimpleWidthManager()
    df = pd.DataFrame(
        {
            "numero_ssa": ["202500001"],
            "situacao": ["ABERTO"],
            "data_cadastro": ["2025-01-01"],
        }
    )
    widths = manager.compute_optimal_widths(
        df,
        available_width=600,
        column_order=list(df.columns),
    )
    assert int(widths["numero_ssa"]) == DEFAULT_COLUMN_WIDTHS["numero_ssa"]
    assert int(widths["situacao"]) == DEFAULT_COLUMN_WIDTHS["situacao"]
    assert int(widths["data_cadastro"]) == DEFAULT_COLUMN_WIDTHS["data_cadastro"]


def test_simple_cache_manager_keeps_maximum_of_five_entries() -> None:
    cache = SimpleCacheManager()
    for idx in range(6):
        cache.cache_formatted_df(f"k{idx}", pd.DataFrame({"idx": [idx]}))

    assert len(cache._formatted_cache) == 5
    assert "k0" not in cache._formatted_cache
    assert "k5" in cache._formatted_cache


def test_simple_cache_manager_named_cache_honors_limit() -> None:
    cache = SimpleCacheManager()
    for idx in range(4):
        cache.cache_value("details", f"k{idx}", idx, max_entries=3)

    assert cache.get_cached_value("details", "k0") is None
    assert cache.get_cached_value("details", "k1") == 1
    assert cache.get_cached_value("details", "k3") == 3


def test_simple_cache_manager_named_cache_clamps_non_positive_limit() -> None:
    cache = SimpleCacheManager()
    cache.cache_value("details", "k0", 0, max_entries=0)
    cache.cache_value("details", "k1", 1, max_entries=0)

    assert cache.get_cached_value("details", "k0") is None
    assert cache.get_cached_value("details", "k1") == 1


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
    monkeypatch.setattr(
        "dev_env.streamlit_app._persist_streamlit_state", lambda **_kwargs: None
    )
    _update_render_telemetry("Padrao (1600)", 10.0)
    _update_render_telemetry("Padrao (1600)", 20.0)
    stats = session_state["streamlit_render_stats"]["Padrao (1600)"]
    assert stats["count"] == 2
    assert stats["last_ms"] == 20.0
    assert stats["total_ms"] == 30.0


def test_update_render_telemetry_keeps_profile_window(monkeypatch) -> None:
    session_state = {}
    monkeypatch.setattr(st, "session_state", session_state, raising=False)
    monkeypatch.setattr(
        "dev_env.streamlit_app._persist_streamlit_state", lambda **_kwargs: None
    )

    for idx in range(MAX_RENDER_TELEMETRY_PROFILES + 3):
        _update_render_telemetry(f"profile-{idx}", float(idx))

    stats = session_state["streamlit_render_stats"]
    assert len(stats) == MAX_RENDER_TELEMETRY_PROFILES
    assert "profile-0" not in stats
    assert f"profile-{MAX_RENDER_TELEMETRY_PROFILES + 2}" in stats


def test_streamlit_state_persistence_roundtrip(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("SSA_CONFIG_DIR", str(tmp_path))
    monkeypatch.setenv("SSA_STREAMLIT_UI_STATE_FILE", "streamlit_ui_state_test.json")

    _persist_streamlit_state(
        theme_name="Solar",
        width_profile="Largo (2000)",
        width_profile_by_bucket={"lg": "XL (2400)", "bad": "valor-invalido"},
        streamlit_render_stats={
            "Largo (2000)": {
                "count": 2,
                "total_ms": 32.5,
                "last_ms": 15.0,
                "updated_at": 123.0,
            }
        },
    )
    loaded = _load_persisted_streamlit_state()

    assert loaded["theme_name"] == "Solar"
    assert loaded["width_profile"] == "Largo (2000)"
    assert loaded["width_profile_by_bucket"] == {"lg": "XL (2400)"}
    assert loaded["streamlit_render_stats"]["Largo (2000)"]["count"] == 2


def test_streamlit_state_persistence_invalid_json_returns_empty(
    tmp_path, monkeypatch
) -> None:
    monkeypatch.setenv("SSA_CONFIG_DIR", str(tmp_path))
    monkeypatch.setenv("SSA_STREAMLIT_UI_STATE_FILE", "streamlit_ui_state_test.json")
    state_path = _resolve_streamlit_ui_state_path()
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text("{invalid", encoding="utf-8")

    loaded = _load_persisted_streamlit_state()

    assert loaded == {}


def test_normalize_streamlit_theme_name_falls_back_to_default() -> None:
    assert _normalize_streamlit_theme_name("Solar") == "Solar"
    assert _normalize_streamlit_theme_name("invalido") == DEFAULT_STREAMLIT_THEME


def test_build_streamlit_theme_css_contains_palette_tokens() -> None:
    css = _build_streamlit_theme_css("Grafite")
    assert "<style>" in css
    assert "--ssa-bg" in css
    assert STREAMLIT_THEME_PALETTES["Grafite"]["bg"] in css


def test_compute_sidebar_weekly_kpis_uses_exec_and_emission_fields() -> None:
    df = pd.DataFrame(
        {
            "data_execucao": [
                "2026-03-01",
                "2026-02-28",
                "2026-02-22",
                "2026-02-15",
            ],
            "data_cadastro": [
                "2026-03-01",
                "2026-02-27",
                "2026-02-20",
                "2026-02-14",
            ],
        }
    )
    metrics = _compute_sidebar_weekly_kpis(df, reference_dt=datetime(2026, 3, 1))
    assert metrics["executadas_semana_atual"] == 2
    assert metrics["executadas_semana_anterior"] == 1
    assert metrics["emitidas_semana_atual"] == 2
    assert metrics["emitidas_semana_anterior"] == 1


def test_compute_sidebar_weekly_kpis_falls_back_to_semana_executada() -> None:
    df = pd.DataFrame(
        {
            "semana_executada": [202609, 202609, 202608, 202607],
            "data_emissao": ["2026-03-01", "2026-02-25", "2026-02-17", ""],
        }
    )
    metrics = _compute_sidebar_weekly_kpis(df, reference_dt=datetime(2026, 3, 1))
    assert metrics["executadas_semana_atual"] == 2
    assert metrics["executadas_semana_anterior"] == 1
    assert metrics["emitidas_semana_atual"] == 2
    assert metrics["emitidas_semana_anterior"] == 1


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


def test_streamlit_app_title_matches_active_version() -> None:
    assert STREAMLIT_APP_TITLE == f"SSA Consulta Rapida v{APP_VERSION}"


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


def test_clear_recent_api_snapshot_is_idempotent_without_existing_key(
    monkeypatch,
) -> None:
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
