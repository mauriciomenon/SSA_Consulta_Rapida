from __future__ import annotations

import builtins

import pandas as pd
import pytest

from interface import cli


@pytest.mark.parametrize("change_mode_only", [False, True])
def test_config_command_reloads_initial_state_after_config(monkeypatch, change_mode_only):
    call_count = {"initial_state": 0}
    sample_df_before = pd.DataFrame({"numero_ssa": ["202500001"]})
    sample_df_after = pd.DataFrame({"numero_ssa": ["202500002"]})
    render_calls: list[tuple[pd.DataFrame, list[str]]] = []

    def _fake_get_initial_state(_db_path, _table_name, _settings):
        call_count["initial_state"] += 1
        if call_count["initial_state"] == 1:
            return sample_df_before, ["old_default"]
        return sample_df_after, ["old_default" if change_mode_only else "new_default"]

    input_state = {"called": False}

    def _fake_input(_prompt: str) -> str:
        if not input_state["called"]:
            input_state["called"] = True
            return "c"
        raise KeyboardInterrupt

    monkeypatch.setattr(cli, "_get_initial_state", _fake_get_initial_state)
    settings_call = {"count": 0}

    def _fake_load_settings():
        settings_call["count"] += 1
        if settings_call["count"] == 1:
            return {"default_filters": ["old_default"], "user_preferences": {}}
        return {
            "default_filters": ["old_default" if change_mode_only else "new_default"],
            "user_preferences": {"filter_mode_default": "exact"},
        }

    monkeypatch.setattr(cli, "load_settings", _fake_load_settings)
    monkeypatch.setattr(
        cli, "load_display_mappings_integrity", lambda: {"numero_ssa": "Numero SSA"}
    )

    def _fake_render_single_page(
        df, _display_map, _settings, _print_cache, terms, **_kwargs
    ):
        render_calls.append((df, list(terms)))
        return None

    monkeypatch.setattr(cli, "_render_single_page", _fake_render_single_page)
    monkeypatch.setattr(cli, "_reset_pagination_state", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(cli, "handle_config_command", lambda: None)
    monkeypatch.setattr(builtins, "input", _fake_input)

    with pytest.raises(SystemExit) as exc:
        cli.start_cli_loop("dummy.db", "ssas")

    assert exc.value.code == 0
    assert call_count["initial_state"] == 2
    assert render_calls
    last_df, last_terms = render_calls[-1]
    assert last_df is sample_df_after
    assert last_terms == ["old_default" if change_mode_only else "new_default"]


def test_config_command_without_default_filter_change_skips_requery(monkeypatch):
    call_count = {"initial_state": 0}
    sample_df = pd.DataFrame({"numero_ssa": ["202500001"]})
    render_calls: list[tuple[pd.DataFrame, list[str]]] = []

    def _fake_get_initial_state(_db_path, _table_name, _settings):
        call_count["initial_state"] += 1
        return sample_df, ["keep"]

    input_state = {"called": False}

    def _fake_input(_prompt: str) -> str:
        if not input_state["called"]:
            input_state["called"] = True
            return "c"
        raise KeyboardInterrupt

    def _fake_render_single_page(
        df, _display_map, _settings, _print_cache, terms, **_kwargs
    ):
        render_calls.append((df, list(terms)))
        return None

    monkeypatch.setattr(cli, "_get_initial_state", _fake_get_initial_state)
    monkeypatch.setattr(
        cli,
        "load_settings",
        lambda: {"default_filters": ["keep"], "user_preferences": {}},
    )
    monkeypatch.setattr(
        cli, "load_display_mappings_integrity", lambda: {"numero_ssa": "Numero SSA"}
    )
    monkeypatch.setattr(cli, "_render_single_page", _fake_render_single_page)
    monkeypatch.setattr(cli, "_reset_pagination_state", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(cli, "handle_config_command", lambda: None)
    monkeypatch.setattr(builtins, "input", _fake_input)

    with pytest.raises(SystemExit) as exc:
        cli.start_cli_loop("dummy.db", "ssas")

    assert exc.value.code == 0
    assert call_count["initial_state"] == 1
    assert render_calls
    last_df, last_terms = render_calls[-1]
    assert last_df is sample_df
    assert last_terms == ["keep"]


def test_config_mode_change_preserves_user_terms_parsed_in_new_mode(monkeypatch):
    """Alterar somente o modo de filtro reconstroi a pilha: os termos do
    usuario sao re-parseados com o modo novo e reaplicados sobre a base
    renovada, e os termos da base (default_filters) sao preservados."""
    base_before = pd.DataFrame({"numero_ssa": ["202500001"]})
    base_after = pd.DataFrame({"numero_ssa": ["202500002"]})
    user_hit = pd.DataFrame({"numero_ssa": ["202500003"]})
    refreshed_hit = pd.DataFrame({"numero_ssa": ["202500004"]})
    render_calls: list[list[str]] = []
    filter_calls: list[tuple[pd.DataFrame, list[dict]]] = []
    state = {"initial": 0, "filter": 0}

    def _fake_get_initial_state(_db_path, _table_name, _settings):
        state["initial"] += 1
        if state["initial"] == 1:
            return base_before, ["base"]
        return base_after, ["base"]

    inputs = iter(["usuario", "c"])

    def _fake_input(_prompt: str) -> str:
        try:
            return next(inputs)
        except StopIteration:
            raise KeyboardInterrupt

    def _fake_filter_dataframe(df, terms):
        filter_calls.append((df, terms))
        state["filter"] += 1
        if state["filter"] == 1:
            return user_hit
        return refreshed_hit

    settings_call = {"count": 0}

    def _fake_load_settings():
        settings_call["count"] += 1
        mode = "contains" if settings_call["count"] == 1 else "exact"
        return {
            "default_filters": ["base"],
            "user_preferences": {"filter_mode_default": mode},
        }

    def _fake_render_single_page(
        df, _display_map, _settings, _print_cache, terms, **_kwargs
    ):
        render_calls.append(list(terms))
        return None

    monkeypatch.setattr(cli, "_get_initial_state", _fake_get_initial_state)
    monkeypatch.setattr(cli, "load_settings", _fake_load_settings)
    monkeypatch.setattr(
        cli, "load_display_mappings_integrity", lambda: {"numero_ssa": "Numero SSA"}
    )
    monkeypatch.setattr(cli, "filter_dataframe", _fake_filter_dataframe)
    monkeypatch.setattr(cli, "_render_single_page", _fake_render_single_page)
    monkeypatch.setattr(cli, "_reset_pagination_state", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(cli, "handle_config_command", lambda: None)
    monkeypatch.setattr(builtins, "input", _fake_input)

    with pytest.raises(SystemExit) as exc:
        cli.start_cli_loop("dummy.db", "ssas")

    assert exc.value.code == 0
    # 1a chamada: busca do usuario sobre a base inicial; 2a: reparse dos
    # termos preservados sobre a base recarregada apos a troca de modo.
    assert len(filter_calls) == 2
    search_df, search_terms = filter_calls[0]
    assert search_df is base_before
    assert [term["raw"] for term in search_terms] == ["usuario"]
    refreshed_df, refreshed_terms = filter_calls[1]
    assert refreshed_df is base_after
    assert [term["raw"] for term in refreshed_terms] == ["usuario"]
    assert [term["mode"] for term in refreshed_terms] == ["exact"]
    assert render_calls[-1] == ["base", "usuario"]
