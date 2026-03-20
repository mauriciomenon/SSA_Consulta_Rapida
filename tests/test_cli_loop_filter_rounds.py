from __future__ import annotations

import builtins
import io
from contextlib import redirect_stdout

import pandas as pd
import pytest

from interface import cli


def test_start_cli_loop_keeps_session_after_clear(monkeypatch: pytest.MonkeyPatch) -> None:
    base_df = pd.DataFrame({"numero_ssa": ["202500001", "202500002"]})
    filtered_df = pd.DataFrame({"numero_ssa": ["202500002"]})
    render_calls: list[tuple[pd.DataFrame, list[str]]] = []

    monkeypatch.setattr(
        cli,
        "_get_initial_state",
        lambda *_args, **_kwargs: (base_df, []),
    )
    monkeypatch.setattr(
        cli,
        "load_settings",
        lambda: {"default_filters": [], "user_preferences": {"filter_mode_default": "contains"}},
    )
    monkeypatch.setattr(cli, "load_display_mappings_integrity", lambda: {})
    monkeypatch.setattr(cli, "_show_initial_help", lambda: None)
    monkeypatch.setattr(cli, "_reset_pagination_state", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(cli, "_prune_pagination_tracker_for_stack", lambda *_args, **_kwargs: None)

    def _fake_parse_search_terms(terms, default_mode="contains"):
        return [(default_mode, term) for term in terms]

    def _fake_filter_dataframe(df: pd.DataFrame, parsed_terms):
        values = [value for _mode, value in parsed_terms]
        if df is base_df and values == ["mel4"]:
            return filtered_df
        return df

    def _fake_render_single_page(df, _display_map, _settings, _print_cache, terms, **_kwargs):
        render_calls.append((df, list(terms)))
        return None

    inputs = iter(["mel4", "clear", "q"])

    def _fake_input(_prompt: str) -> str:
        try:
            return next(inputs)
        except StopIteration:
            raise KeyboardInterrupt

    monkeypatch.setattr(cli, "parse_search_terms", _fake_parse_search_terms)
    monkeypatch.setattr(cli, "filter_dataframe", _fake_filter_dataframe)
    monkeypatch.setattr(cli, "_render_single_page", _fake_render_single_page)
    monkeypatch.setattr(builtins, "input", _fake_input)

    with pytest.raises(SystemExit) as excinfo:
        cli.start_cli_loop("dummy.db", "ssa_table")

    assert excinfo.value.code == 0
    assert render_calls == [
        (filtered_df, ["mel4"]),
        (base_df, []),
    ]


def test_start_cli_loop_accumulates_literal_terms_without_rewriting(monkeypatch: pytest.MonkeyPatch) -> None:
    base_df = pd.DataFrame({"numero_ssa": ["202500001", "202500002", "202500003"]})
    after_first = pd.DataFrame({"numero_ssa": ["202500001", "202500003"]})
    after_second = pd.DataFrame({"numero_ssa": ["202500003"]})
    parse_calls: list[list[str]] = []
    render_calls: list[tuple[pd.DataFrame, list[str]]] = []

    monkeypatch.setattr(
        cli,
        "_get_initial_state",
        lambda *_args, **_kwargs: (base_df, []),
    )
    monkeypatch.setattr(
        cli,
        "load_settings",
        lambda: {"default_filters": [], "user_preferences": {"filter_mode_default": "contains"}},
    )
    monkeypatch.setattr(cli, "load_display_mappings_integrity", lambda: {})
    monkeypatch.setattr(cli, "_show_initial_help", lambda: None)
    monkeypatch.setattr(cli, "_reset_pagination_state", lambda *_args, **_kwargs: None)

    def _fake_parse_search_terms(terms, default_mode="contains"):
        values = list(terms)
        parse_calls.append(values)
        return [(default_mode, term) for term in values]

    def _fake_filter_dataframe(df: pd.DataFrame, parsed_terms):
        values = [value for _mode, value in parsed_terms]
        if df is base_df and values == ["mel4"]:
            return after_first
        if df is after_first and values == ["danilo", "OU", "svp", "!STE"]:
            return after_second
        raise AssertionError(f"unexpected filter call: {values!r}")

    def _fake_render_single_page(df, _display_map, _settings, _print_cache, terms, **_kwargs):
        render_calls.append((df, list(terms)))
        return None

    inputs = iter(["mel4", "danilo, OU, svp, !STE", "q"])

    def _fake_input(_prompt: str) -> str:
        try:
            return next(inputs)
        except StopIteration:
            raise KeyboardInterrupt

    monkeypatch.setattr(cli, "parse_search_terms", _fake_parse_search_terms)
    monkeypatch.setattr(cli, "filter_dataframe", _fake_filter_dataframe)
    monkeypatch.setattr(cli, "_render_single_page", _fake_render_single_page)
    monkeypatch.setattr(builtins, "input", _fake_input)

    with pytest.raises(SystemExit) as excinfo:
        cli.start_cli_loop("dummy.db", "ssa_table")

    assert excinfo.value.code == 0
    assert parse_calls == [
        ["mel4"],
        ["danilo", "OU", "svp", "!STE"],
    ]
    assert render_calls == [
        (after_first, ["mel4"]),
        (after_second, ["mel4", "danilo", "OU", "svp", "!STE"]),
    ]


def test_start_cli_loop_back_rerenders_previous_state(monkeypatch: pytest.MonkeyPatch) -> None:
    base_df = pd.DataFrame({"numero_ssa": ["202500001", "202500002"]})
    filtered_df = pd.DataFrame({"numero_ssa": ["202500002"]})
    render_calls: list[tuple[pd.DataFrame, list[str], int | None]] = []

    monkeypatch.setattr(cli, "_get_initial_state", lambda *_args, **_kwargs: (base_df, []))
    monkeypatch.setattr(
        cli,
        "load_settings",
        lambda: {"default_filters": [], "user_preferences": {"filter_mode_default": "contains"}},
    )
    monkeypatch.setattr(cli, "load_display_mappings_integrity", lambda: {})
    monkeypatch.setattr(cli, "_show_initial_help", lambda: None)
    monkeypatch.setattr(cli, "_reset_pagination_state", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(cli, "_prune_pagination_tracker_for_stack", lambda *_args, **_kwargs: None)

    def _fake_parse_search_terms(terms, default_mode="contains"):
        return [(default_mode, term) for term in terms]

    def _fake_filter_dataframe(df: pd.DataFrame, parsed_terms):
        values = [value for _mode, value in parsed_terms]
        if df is base_df and values == ["mel4"]:
            return filtered_df
        return df

    def _fake_render_single_page(df, _display_map, _settings, _print_cache, terms, **kwargs):
        render_calls.append((df, list(terms), kwargs.get("start_page")))
        return None

    inputs = iter(["mel4", "v", "q"])

    def _fake_input(_prompt: str) -> str:
        try:
            return next(inputs)
        except StopIteration:
            raise KeyboardInterrupt

    monkeypatch.setattr(cli, "parse_search_terms", _fake_parse_search_terms)
    monkeypatch.setattr(cli, "filter_dataframe", _fake_filter_dataframe)
    monkeypatch.setattr(cli, "_render_single_page", _fake_render_single_page)
    monkeypatch.setattr(builtins, "input", _fake_input)

    with pytest.raises(SystemExit) as excinfo:
        cli.start_cli_loop("dummy.db", "ssa_table")

    assert excinfo.value.code == 0
    assert render_calls == [
        (filtered_df, ["mel4"], 0),
        (base_df, [], 0),
    ]


def test_start_cli_loop_treats_short_year_as_literal_search(monkeypatch: pytest.MonkeyPatch) -> None:
    base_df = pd.DataFrame({"numero_ssa": ["202500001", "202400001"]})
    parse_calls: list[list[str]] = []
    render_calls: list[tuple[pd.DataFrame, list[str]]] = []

    monkeypatch.setattr(cli, "_get_initial_state", lambda *_args, **_kwargs: (base_df, []))
    monkeypatch.setattr(
        cli,
        "load_settings",
        lambda: {"default_filters": [], "user_preferences": {"filter_mode_default": "contains"}},
    )
    monkeypatch.setattr(cli, "load_display_mappings_integrity", lambda: {})
    monkeypatch.setattr(cli, "_show_initial_help", lambda: None)
    monkeypatch.setattr(cli, "_reset_pagination_state", lambda *_args, **_kwargs: None)

    def _fake_parse_search_terms(terms, default_mode="contains"):
        values = list(terms)
        parse_calls.append(values)
        return [(default_mode, term) for term in values]

    def _fake_render_single_page(df, _display_map, _settings, _print_cache, terms, **_kwargs):
        render_calls.append((df, list(terms)))
        return None

    monkeypatch.setattr(cli, "parse_search_terms", _fake_parse_search_terms)
    monkeypatch.setattr(cli, "filter_dataframe", lambda df, _parsed_terms: df)
    monkeypatch.setattr(cli, "_render_single_page", _fake_render_single_page)
    monkeypatch.setattr(cli, "_show_ssa_details", lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("nao deveria abrir detalhe")))

    inputs = iter(["2025", "q"])

    def _fake_input(_prompt: str) -> str:
        try:
            return next(inputs)
        except StopIteration:
            raise KeyboardInterrupt

    monkeypatch.setattr(builtins, "input", _fake_input)

    with pytest.raises(SystemExit) as excinfo:
        cli.start_cli_loop("dummy.db", "ssa_table")

    assert excinfo.value.code == 0
    assert parse_calls == [["2025"]]
    assert render_calls == [(base_df, ["2025"])]


def test_start_cli_loop_opens_detail_for_exact_ssa_number(monkeypatch: pytest.MonkeyPatch) -> None:
    base_df = pd.DataFrame(
        {
            "numero_ssa": ["202500001"],
            "descricao_ssa": ["SSA de teste"],
        }
    )
    details_calls: list[str] = []

    monkeypatch.setattr(cli, "_get_initial_state", lambda *_args, **_kwargs: (base_df, []))
    monkeypatch.setattr(
        cli,
        "load_settings",
        lambda: {"default_filters": [], "user_preferences": {"filter_mode_default": "contains"}},
    )
    monkeypatch.setattr(cli, "load_display_mappings_integrity", lambda: {})
    monkeypatch.setattr(cli, "_show_initial_help", lambda: None)
    monkeypatch.setattr(cli, "_render_single_page", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(cli, "_reset_pagination_state", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(cli, "filter_dataframe", lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("nao deveria filtrar")))
    monkeypatch.setattr(cli, "parse_search_terms", lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("nao deveria parsear")))
    monkeypatch.setattr(
        cli,
        "_show_ssa_details",
        lambda row, _display_map: details_calls.append(str(row["numero_ssa"])),
    )

    inputs = iter(["202500001", "q"])

    def _fake_input(_prompt: str) -> str:
        try:
            return next(inputs)
        except StopIteration:
            raise KeyboardInterrupt

    monkeypatch.setattr(builtins, "input", _fake_input)

    with pytest.raises(SystemExit) as excinfo:
        cli.start_cli_loop("dummy.db", "ssa_table")

    assert excinfo.value.code == 0
    assert details_calls == ["202500001"]


def test_handle_export_rejects_unsafe_filename(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    exporter_calls: list[tuple[pd.DataFrame, str, str, dict]] = []
    current_df = pd.DataFrame({"numero_ssa": ["202500001"]})

    monkeypatch.setattr("exportacao.exporter.export_dataframe", lambda *args: exporter_calls.append(args))

    cli._handle_export(["e", "../relatorio"], current_df, "docs_saida", {})

    out = capsys.readouterr().out
    assert "nome de exportacao invalido" in out.lower()
    assert exporter_calls == []


def test_handle_sort_rejects_zero_index(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    current_df = pd.DataFrame({"numero_ssa": ["202500001"], "situacao": ["ADM"]})
    results_stack = [(current_df, [])]

    monkeypatch.setattr(cli, "_render_single_page", lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("nao deveria renderizar")))

    cli._handle_sort(["ord", "0"], results_stack, {}, {}, True, {})

    out = capsys.readouterr().out
    assert "coluna" in out.lower()
    assert "inv" in out.lower()
    assert results_stack == [(current_df, [])]


def test_cached_pretty_print_df_cache_key_includes_rendered_rows(monkeypatch: pytest.MonkeyPatch) -> None:
    settings = {"user_preferences": {}, "display_settings": {}}
    display_map = {"numero_ssa": "Numero SSA"}
    cache: dict[str, tuple[str, dict]] = {}
    render_count = {"count": 0}

    df_a = pd.DataFrame({"numero_ssa": ["202500001", "202500002"]})
    df_b = pd.DataFrame({"numero_ssa": ["202500001", "202500999"]})

    monkeypatch.setattr(cli.enhancement_manager, "is_enhanced_printer_enabled", lambda: False)
    monkeypatch.setattr(cli.EnhancedTablePrinter, "get_terminal_size", lambda _self: (10, 120))

    def _fake_pretty_print_df(df: pd.DataFrame, _display_map: dict, _settings: dict) -> None:
        render_count["count"] += 1
        print("|".join(df["numero_ssa"].tolist()))

    monkeypatch.setattr(cli, "pretty_print_df", _fake_pretty_print_df)

    with redirect_stdout(io.StringIO()):
        cli._cached_pretty_print_df(df_a, display_map, settings, cache, ["mel4"])
        cli._cached_pretty_print_df(df_b, display_map, settings, cache, ["mel4"])

    assert render_count["count"] == 2


def test_build_cli_plain_help_text_reflects_current_search_contract() -> None:
    help_text = cli._build_cli_plain_help_text()

    assert "Separe termos por virgula" in help_text
    assert "Exemplos: svp, !ste, mel4" in help_text
    assert "h ou ?    Ajuda completa" in help_text


def test_handle_help_fallback_uses_shared_plain_help_text(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(builtins, "input", lambda _prompt="": "")

    original_print = builtins.print
    state = {"first": True}

    def _fake_print(*args, **kwargs):
        if state["first"]:
            state["first"] = False
            raise UnicodeEncodeError("ascii", "teste", 0, 1, "fail")
        return original_print(*args, **kwargs)

    monkeypatch.setattr(builtins, "print", _fake_print)

    cli._handle_help()

    out = capsys.readouterr().out
    assert "CONSULTA RAPIDA de SSAs" in out
    assert "Separe termos por virgula" in out
