from __future__ import annotations

import builtins

import pandas as pd
import pytest


def test_start_cli_loop_does_not_crash_when_numero_ssa_column_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import interface.cli as cli

    df_without_numero = pd.DataFrame({"situacao": ["ABERTA"], "descricao_ssa": ["x"]})

    monkeypatch.setattr(
        cli,
        "load_settings",
        lambda: {"user_preferences": {"filter_mode_default": "contains"}},
    )
    monkeypatch.setattr(cli, "load_display_mappings_integrity", lambda: {})
    monkeypatch.setattr(
        cli, "_get_initial_state", lambda *_args, **_kwargs: (df_without_numero, [])
    )
    monkeypatch.setattr(cli, "_show_initial_help", lambda: None)
    monkeypatch.setattr(cli, "_render_single_page", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(cli, "_reset_pagination_state", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(cli, "filter_dataframe", lambda _df, _parsed: _df)
    monkeypatch.setattr(
        cli,
        "parse_search_terms",
        lambda _terms, default_mode="contains": [(default_mode, "noop")],
    )
    monkeypatch.setattr(cli, "_show_ssa_details", lambda *_args, **_kwargs: None)

    inputs = iter(["202500001"])

    def fake_input(_prompt: str) -> str:
        try:
            return next(inputs)
        except StopIteration:
            raise KeyboardInterrupt

    monkeypatch.setattr(builtins, "input", fake_input)

    with pytest.raises(SystemExit) as excinfo:
        cli.start_cli_loop("data/ssas.db", "ssa_table")

    assert excinfo.value.code == 0
