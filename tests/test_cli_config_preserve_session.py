from __future__ import annotations

import builtins

import pandas as pd
import pytest

from interface import cli


def test_config_command_reloads_initial_state_after_config(monkeypatch):
    call_count = {"initial_state": 0}
    sample_df_before = pd.DataFrame({"numero_ssa": ["202500001"]})
    sample_df_after = pd.DataFrame({"numero_ssa": ["202500002"]})
    render_calls: list[tuple[pd.DataFrame, list[str]]] = []

    def _fake_get_initial_state(_db_path, _table_name, _settings):
        call_count["initial_state"] += 1
        if call_count["initial_state"] == 1:
            return sample_df_before, ["old_default"]
        return sample_df_after, ["new_default"]

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
        return {"default_filters": ["new_default"], "user_preferences": {}}

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
    assert last_terms == ["new_default"]


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
