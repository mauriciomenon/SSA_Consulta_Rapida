from __future__ import annotations

import pandas as pd

from interface import cli


def test_remove_filter_non_lifo_reapplies_from_base(monkeypatch):
    base_df = pd.DataFrame({"col": ["base"]})
    mid_df = pd.DataFrame({"col": ["mid"]})
    top_df = pd.DataFrame({"col": ["top"]})
    target_df = pd.DataFrame({"col": ["target"]})

    results_stack = [
        (base_df, []),
        (mid_df, ["a"]),
        (top_df, ["a", "b", "c"]),
    ]

    calls: dict[str, object] = {}

    def _fake_filter_dataframe(df: pd.DataFrame, terms):
        calls["df"] = df
        calls["terms"] = list(terms)
        return target_df

    monkeypatch.setattr(cli, "filter_dataframe", _fake_filter_dataframe)
    monkeypatch.setattr(cli, "_render_single_page", lambda *args, **kwargs: None)
    monkeypatch.setattr(cli, "_reset_pagination_state", lambda *_args, **_kwargs: None)

    cli._handle_remove_filter(["-x", "b"], results_stack, {}, {}, {})

    assert calls["df"] is base_df
    assert calls["terms"] == ["a", "c"]
    assert results_stack[-1][0] is target_df
    assert results_stack[-1][1] == ["a", "c"]


def test_remove_filter_lifo_reapplies_from_previous_state(monkeypatch):
    base_df = pd.DataFrame({"col": ["base"]})
    mid_df = pd.DataFrame({"col": ["mid"]})
    top_df = pd.DataFrame({"col": ["top"]})
    target_df = pd.DataFrame({"col": ["target"]})

    results_stack = [
        (base_df, []),
        (mid_df, ["a"]),
        (top_df, ["a", "b"]),
    ]

    calls: dict[str, object] = {}

    def _fake_filter_dataframe(df: pd.DataFrame, terms):
        calls["df"] = df
        calls["terms"] = list(terms)
        return target_df

    monkeypatch.setattr(cli, "filter_dataframe", _fake_filter_dataframe)
    monkeypatch.setattr(cli, "_render_single_page", lambda *args, **kwargs: None)
    monkeypatch.setattr(cli, "_reset_pagination_state", lambda *_args, **_kwargs: None)

    cli._handle_remove_filter(["-x", "b"], results_stack, {}, {}, {})

    assert calls["df"] is mid_df
    assert calls["terms"] == ["a"]
