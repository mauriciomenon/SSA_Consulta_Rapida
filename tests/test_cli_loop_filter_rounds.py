from __future__ import annotations

import builtins
import io
import os
import sqlite3
import subprocess
import sys
from contextlib import redirect_stdout
from pathlib import Path

import pandas as pd
import pytest

from interface import cli


def _build_cli_subprocess_env(repo_root: Path, tmp_path: Path) -> dict[str, str]:
    db_path = tmp_path / "cli_subprocess.db"
    schema_sql = (repo_root / "config" / "schema.sql").read_text(encoding="utf-8")
    conn = sqlite3.connect(db_path)
    try:
        conn.executescript(schema_sql)
        rows = [
            (f"2025{i:05d}", "ADM", f"SSA teste MEL4 {i:02d}", "MEL4")
            for i in range(1, 26)
        ]
        conn.executemany(
            "INSERT INTO ssa_table (numero_ssa, situacao, descricao_ssa, setor_executor) VALUES (?, ?, ?, ?)",
            rows,
        )
        conn.commit()
    finally:
        conn.close()

    env = os.environ.copy()
    env["SSA_NON_INTERACTIVE"] = "1"
    env["SSA_DB_PATH"] = str(db_path)
    env["SSA_CLI_ENHANCEMENTS_PATH"] = str(tmp_path / "cli_enhancements.test.json")
    return env


def test_start_cli_loop_keeps_session_after_clear(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
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
        lambda: {
            "default_filters": [],
            "user_preferences": {"filter_mode_default": "contains"},
        },
    )
    monkeypatch.setattr(cli, "load_display_mappings_integrity", lambda: {})
    monkeypatch.setattr(cli, "_show_initial_help", lambda: None)
    monkeypatch.setattr(cli, "_reset_pagination_state", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(
        cli, "_prune_pagination_tracker_for_stack", lambda *_args, **_kwargs: None
    )

    def _fake_parse_search_terms(terms, default_mode="contains"):
        return [(default_mode, term) for term in terms]

    def _fake_filter_dataframe(df: pd.DataFrame, parsed_terms):
        values = [value for _mode, value in parsed_terms]
        if df is base_df and values == ["mel4"]:
            return filtered_df
        return df

    def _fake_render_single_page(
        df, _display_map, _settings, _print_cache, terms, **_kwargs
    ):
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


def test_render_cli_page_exits_when_printer_requests_app_exit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    df = pd.DataFrame({"numero_ssa": ["202500001"]})

    monkeypatch.setattr(
        cli,
        "_cached_pretty_print_df",
        lambda *_args, **_kwargs: {
            "next_page": None,
            "total_pages": 1,
            "rendered_pages": 1,
            "page_size": 20,
            "exit_requested": True,
        },
    )
    monkeypatch.setattr(cli, "_update_pagination_state", lambda *_args, **_kwargs: None)

    with pytest.raises(SystemExit) as excinfo:
        cli._render_cli_page(df, {}, {}, {}, [])

    assert excinfo.value.code == 0


def test_start_cli_loop_accumulates_literal_terms_without_rewriting(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
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
        lambda: {
            "default_filters": [],
            "user_preferences": {"filter_mode_default": "contains"},
        },
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

    def _fake_render_single_page(
        df, _display_map, _settings, _print_cache, terms, **_kwargs
    ):
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


def test_start_cli_loop_back_rerenders_previous_state(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    base_df = pd.DataFrame({"numero_ssa": ["202500001", "202500002"]})
    filtered_df = pd.DataFrame({"numero_ssa": ["202500002"]})
    render_calls: list[tuple[pd.DataFrame, list[str], int | None]] = []

    monkeypatch.setattr(
        cli, "_get_initial_state", lambda *_args, **_kwargs: (base_df, [])
    )
    monkeypatch.setattr(
        cli,
        "load_settings",
        lambda: {
            "default_filters": [],
            "user_preferences": {"filter_mode_default": "contains"},
        },
    )
    monkeypatch.setattr(cli, "load_display_mappings_integrity", lambda: {})
    monkeypatch.setattr(cli, "_show_initial_help", lambda: None)
    monkeypatch.setattr(cli, "_reset_pagination_state", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(
        cli, "_prune_pagination_tracker_for_stack", lambda *_args, **_kwargs: None
    )

    def _fake_parse_search_terms(terms, default_mode="contains"):
        return [(default_mode, term) for term in terms]

    def _fake_filter_dataframe(df: pd.DataFrame, parsed_terms):
        values = [value for _mode, value in parsed_terms]
        if df is base_df and values == ["mel4"]:
            return filtered_df
        return df

    def _fake_render_single_page(
        df, _display_map, _settings, _print_cache, terms, **kwargs
    ):
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


def test_start_cli_loop_treats_short_year_as_literal_search(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    base_df = pd.DataFrame({"numero_ssa": ["202500001", "202400001"]})
    parse_calls: list[list[str]] = []
    render_calls: list[tuple[pd.DataFrame, list[str]]] = []

    monkeypatch.setattr(
        cli, "_get_initial_state", lambda *_args, **_kwargs: (base_df, [])
    )
    monkeypatch.setattr(
        cli,
        "load_settings",
        lambda: {
            "default_filters": [],
            "user_preferences": {"filter_mode_default": "contains"},
        },
    )
    monkeypatch.setattr(cli, "load_display_mappings_integrity", lambda: {})
    monkeypatch.setattr(cli, "_show_initial_help", lambda: None)
    monkeypatch.setattr(cli, "_reset_pagination_state", lambda *_args, **_kwargs: None)

    def _fake_parse_search_terms(terms, default_mode="contains"):
        values = list(terms)
        parse_calls.append(values)
        return [(default_mode, term) for term in values]

    def _fake_render_single_page(
        df, _display_map, _settings, _print_cache, terms, **_kwargs
    ):
        render_calls.append((df, list(terms)))
        return None

    monkeypatch.setattr(cli, "parse_search_terms", _fake_parse_search_terms)
    monkeypatch.setattr(cli, "filter_dataframe", lambda df, _parsed_terms: df)
    monkeypatch.setattr(cli, "_render_single_page", _fake_render_single_page)
    monkeypatch.setattr(
        cli,
        "_show_ssa_details",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("nao deveria abrir detalhe")
        ),
    )

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


def test_start_cli_loop_opens_detail_for_exact_ssa_number(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    base_df = pd.DataFrame(
        {
            "numero_ssa": ["202500001"],
            "descricao_ssa": ["SSA de teste"],
        }
    )
    details_calls: list[str] = []

    monkeypatch.setattr(
        cli, "_get_initial_state", lambda *_args, **_kwargs: (base_df, [])
    )
    monkeypatch.setattr(
        cli,
        "load_settings",
        lambda: {
            "default_filters": [],
            "user_preferences": {"filter_mode_default": "contains"},
        },
    )
    monkeypatch.setattr(cli, "load_display_mappings_integrity", lambda: {})
    monkeypatch.setattr(cli, "_show_initial_help", lambda: None)
    monkeypatch.setattr(cli, "_render_single_page", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(cli, "_reset_pagination_state", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(
        cli,
        "filter_dataframe",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("nao deveria filtrar")
        ),
    )
    monkeypatch.setattr(
        cli,
        "parse_search_terms",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("nao deveria parsear")
        ),
    )
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


def test_handle_export_rejects_unsafe_filename(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    exporter_calls: list[tuple[pd.DataFrame, str, str, dict]] = []
    current_df = pd.DataFrame({"numero_ssa": ["202500001"]})

    monkeypatch.setattr(
        "exportacao.exporter.export_dataframe",
        lambda *args: exporter_calls.append(args),
    )

    cli._handle_export(["e", "../relatorio"], current_df, "docs_saida", {})

    out = capsys.readouterr().out
    assert "nome de exportacao invalido" in out.lower()
    assert exporter_calls == []


def test_handle_sort_rejects_zero_index(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    current_df = pd.DataFrame({"numero_ssa": ["202500001"], "situacao": ["ADM"]})
    results_stack = [(current_df, [])]

    monkeypatch.setattr(
        cli,
        "_render_single_page",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("nao deveria renderizar")
        ),
    )

    cli._handle_sort(["ord", "0"], results_stack, {}, {}, True, {})

    out = capsys.readouterr().out
    assert "coluna" in out.lower()
    assert "inv" in out.lower()
    assert results_stack == [(current_df, [])]


def test_cached_pretty_print_df_cache_key_includes_rendered_rows(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = {"user_preferences": {}, "display_settings": {}}
    display_map = {"numero_ssa": "Numero SSA"}
    cache: dict[str, tuple[str, dict]] = {}
    render_count = {"count": 0}

    df_a = pd.DataFrame({"numero_ssa": ["202500001", "202500002"]})
    df_b = pd.DataFrame({"numero_ssa": ["202500001", "202500999"]})

    monkeypatch.setattr(
        cli.enhancement_manager, "is_enhanced_printer_enabled", lambda: False
    )
    monkeypatch.setattr(
        cli.EnhancedTablePrinter, "get_terminal_size", lambda _self: (10, 120)
    )

    def _fake_pretty_print_df(
        df: pd.DataFrame, _display_map: dict, _settings: dict
    ) -> None:
        render_count["count"] += 1
        print("|".join(df["numero_ssa"].tolist()))

    monkeypatch.setattr(cli, "pretty_print_df", _fake_pretty_print_df)

    with redirect_stdout(io.StringIO()):
        cli._cached_pretty_print_df(df_a, display_map, settings, cache, ["mel4"])
        cli._cached_pretty_print_df(df_b, display_map, settings, cache, ["mel4"])

    assert render_count["count"] == 2


def test_cached_pretty_print_df_falls_back_to_default_page_size_on_terminal_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = {"user_preferences": {}, "display_settings": {}}
    df = pd.DataFrame({"numero_ssa": ["202500001"]})

    monkeypatch.setattr(
        cli.enhancement_manager, "is_enhanced_printer_enabled", lambda: False
    )
    monkeypatch.setattr(
        cli.EnhancedTablePrinter,
        "get_terminal_size",
        lambda _self: (_ for _ in ()).throw(ValueError("terminal invalido")),
    )
    monkeypatch.setattr(cli, "pretty_print_df", lambda *_args, **_kwargs: None)

    result = cli._cached_pretty_print_df(df, {}, settings, {}, [])

    assert result["page_size"] == 20


def test_is_cli_non_interactive_returns_true_when_stdin_isatty_breaks(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class _BrokenStdin:
        def isatty(self):
            raise ValueError("isatty indisponivel")

    monkeypatch.delenv("SSA_NON_INTERACTIVE", raising=False)
    monkeypatch.setattr(cli.sys, "stdin", _BrokenStdin())

    assert cli._is_cli_non_interactive() is True


def test_build_cli_plain_help_text_reflects_current_search_contract() -> None:
    help_text = cli._build_cli_plain_help_text()

    assert "Separe termos por virgula" in help_text
    assert "Exemplos: svp, !ste, mel4" in help_text
    assert "h ou ?    Ajuda completa" in help_text


def test_build_cli_prompt_hint_lines_disambiguates_detail_back_and_remove_term() -> (
    None
):
    prompt_line, help_line = cli._build_cli_prompt_hint_lines()

    assert "termos por virgula" in prompt_line
    assert "!termo exclui" in prompt_line
    assert "d # detalhe" in help_line
    assert "v voltar" in help_line
    assert "x <termo> remover" in help_line
    assert help_line.endswith("| h | q.")


def test_handle_remove_filter_without_term_shows_usage_and_keeps_stack(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    base_df = pd.DataFrame({"numero_ssa": ["202500001"]})
    filtered_df = pd.DataFrame({"numero_ssa": ["202500002"]})
    results_stack = [(base_df, []), (filtered_df, ["mel4"])]

    cli._handle_remove_filter(["x"], results_stack, {}, {}, {})

    out = capsys.readouterr().out
    assert "Erro: use x <termo>. Exemplo: x mel4" in out
    assert results_stack == [(base_df, []), (filtered_df, ["mel4"])]


def test_handle_remove_filter_last_term_reuses_last_rendered_page(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    base_df = pd.DataFrame({"numero_ssa": ["202500001"]})
    filtered_df = pd.DataFrame({"numero_ssa": ["202500002"]})
    results_stack = [(base_df, []), (filtered_df, ["mel4"])]
    render_calls: list[tuple[pd.DataFrame, list[str], int | None]] = []

    monkeypatch.setattr(cli, "_reset_pagination_state", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(
        cli, "_prune_pagination_tracker_for_stack", lambda *_args, **_kwargs: None
    )
    monkeypatch.setattr(cli, "_handle_back", lambda stack: stack.pop())
    monkeypatch.setattr(cli, "_last_rendered_page_for", lambda _df: 4)
    monkeypatch.setattr(
        cli,
        "_render_cli_page",
        lambda df,
        _display_map,
        _settings,
        _print_cache,
        terms,
        **kwargs: render_calls.append((df, list(terms), kwargs.get("start_page"))),
    )

    cli._handle_remove_filter(["x", "mel4"], results_stack, {}, {}, {})

    assert render_calls == [(base_df, [], 4)]


def test_build_cli_plain_help_text_detailed_includes_force_rescan_alias() -> None:
    help_text = cli._build_cli_plain_help_text(detailed=True)

    assert "force-rescan    Alias explicito para rescan" in help_text
    assert "OU/OR/AND/E/v continuam literais na busca" in help_text


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


def test_handle_help_normal_path_uses_plain_layout_without_box_art(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(builtins, "input", lambda _prompt="": "")

    cli._handle_help()

    out = capsys.readouterr().out
    lines = [line for line in out.splitlines() if line]
    assert "force-rescan    Alias explicito para rescan" in out
    assert all(
        "║" not in line and "╔" not in line and "╚" not in line for line in lines
    )
    assert max(len(line) for line in lines) <= 79


def test_handle_help_skips_pause_in_non_interactive_mode(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setenv("SSA_NON_INTERACTIVE", "1")
    monkeypatch.setattr(
        builtins,
        "input",
        lambda _prompt="": (_ for _ in ()).throw(AssertionError("nao deveria pausar")),
    )

    cli._handle_help()

    out = capsys.readouterr().out
    assert "Pressione Enter para continuar..." in out


def test_build_cli_plain_help_text_detailed_reuses_initial_search_contract() -> None:
    help_text = cli._build_cli_plain_help_text(detailed=True)

    assert "Mantem o mesmo contrato da busca inicial" in help_text
    assert "Exemplos: svp, !ste, mel4" in help_text
    assert "OU/OR/AND/E/v continuam literais na busca" in help_text


def test_prompt_hint_lines_stay_short_and_two_line_friendly() -> None:
    prompt_line, help_line = cli._build_cli_prompt_hint_lines()

    assert len(prompt_line) <= 79
    assert len(help_line) <= 79


def test_start_cli_loop_accepts_force_rescan_alias(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    base_df = pd.DataFrame({"numero_ssa": ["202500001"]})
    calls: list[str] = []

    monkeypatch.setattr(
        cli, "_get_initial_state", lambda *_args, **_kwargs: (base_df, [])
    )
    monkeypatch.setattr(
        cli,
        "load_settings",
        lambda: {
            "default_filters": [],
            "user_preferences": {"filter_mode_default": "contains"},
        },
    )
    monkeypatch.setattr(cli, "load_display_mappings_integrity", lambda: {})
    monkeypatch.setattr(cli, "_show_initial_help", lambda: None)
    monkeypatch.setattr(cli, "_render_single_page", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(cli, "_reset_pagination_state", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(
        cli,
        "_handle_rescan",
        lambda *_args, **_kwargs: calls.append("force-rescan"),
    )

    inputs = iter(["force-rescan", "q"])

    def _fake_input(_prompt: str) -> str:
        try:
            return next(inputs)
        except StopIteration:
            raise KeyboardInterrupt

    monkeypatch.setattr(builtins, "input", _fake_input)

    with pytest.raises(SystemExit) as excinfo:
        cli.start_cli_loop("dummy.db", "ssa_table")

    assert excinfo.value.code == 0
    assert calls == ["force-rescan"]


def test_cli_subprocess_help_then_quit_exits_cleanly(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    env = _build_cli_subprocess_env(repo_root, tmp_path)

    result = subprocess.run(
        [sys.executable, "launchers/cli_entry.py"],
        input="h\nq\n",
        text=True,
        capture_output=True,
        cwd=repo_root,
        env=env,
        timeout=45,
    )

    assert result.returncode == 0
    assert "EOF when reading a line" not in result.stdout
    assert "Saindo..." in result.stdout


def test_cli_subprocess_force_rescan_non_interactive_exits_cleanly(
    tmp_path: Path,
) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    env = _build_cli_subprocess_env(repo_root, tmp_path)

    result = subprocess.run(
        [sys.executable, "launchers/cli_entry.py"],
        input="force-rescan\nq\n",
        text=True,
        capture_output=True,
        cwd=repo_root,
        env=env,
        timeout=45,
    )

    assert result.returncode == 0
    assert "Rescan indisponivel em sessao non-interactive" in result.stdout
    assert "Saindo..." in result.stdout


def test_print_cli_status_report_normalizes_text_to_ascii(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(
        cli.enhancement_manager,
        "get_status_report",
        lambda: "Configuração Unificada\n• Word wrap inteligente",
    )

    cli._print_cli_status_report()

    out = capsys.readouterr().out
    assert "Configuracao Unificada" in out
    assert "Word wrap inteligente" in out
    assert "•" not in out


def test_toggle_and_enhanced_commands_use_compact_ascii_feedback(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(cli.enhancement_manager, "toggle_debug", lambda: True)
    monkeypatch.setattr(
        cli.enhancement_manager, "enable_enhanced_printer", lambda: None
    )
    monkeypatch.setattr(
        cli.enhancement_manager, "disable_enhanced_printer", lambda: None
    )

    cli._toggle_cli_debug_command()
    cli._set_enhanced_cli_enabled(False)
    cli._set_enhanced_cli_enabled(True)

    out = capsys.readouterr().out
    assert "Debug CLI ativado" in out
    assert "Enhanced Table Printer desativado" in out
    assert "Enhanced Table Printer ativado" in out
    assert "[Debug]" not in out


def test_cli_subprocess_status_cli_uses_ascii_output(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    env = _build_cli_subprocess_env(repo_root, tmp_path)

    result = subprocess.run(
        [sys.executable, "launchers/cli_entry.py"],
        input="status-cli\nq\n",
        text=True,
        capture_output=True,
        cwd=repo_root,
        env=env,
        timeout=45,
    )

    assert result.returncode == 0
    assert "STATUS DAS MELHORIAS CLI" in result.stdout
    assert "Configuracao Unificada" in result.stdout
    assert "•" not in result.stdout


def test_handle_show_more_rejects_show_all_in_non_interactive_mode(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    df = pd.DataFrame({"numero_ssa": ["202500001", "202500002"]})
    cli._PAGINATION_TRACKER_MANAGER.update(
        df,
        {
            "next_page": 1,
            "total_pages": 3,
            "rendered_pages": 1,
            "page_size": 1,
        },
    )
    monkeypatch.setenv("SSA_NON_INTERACTIVE", "1")
    monkeypatch.setattr(
        cli,
        "_render_single_page",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("nao deveria renderizar")
        ),
    )

    cli._handle_show_more([(df, ["mel4"])], {}, {}, {}, ["z"])

    out = capsys.readouterr().out
    assert "Comando 'm z' indisponivel em sessao non-interactive" in out


def test_cli_subprocess_more_all_non_interactive_exits_cleanly(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    env = _build_cli_subprocess_env(repo_root, tmp_path)

    result = subprocess.run(
        [sys.executable, "launchers/cli_entry.py"],
        input="mel4\nm z\nq\n",
        text=True,
        capture_output=True,
        cwd=repo_root,
        env=env,
        timeout=45,
    )

    assert result.returncode == 0
    assert "Comando 'm z' indisponivel em sessao non-interactive" in result.stdout
    assert "Saindo..." in result.stdout


def test_cli_subprocess_clear_then_quit_exits_cleanly(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    env = _build_cli_subprocess_env(repo_root, tmp_path)

    result = subprocess.run(
        [sys.executable, "launchers/cli_entry.py"],
        input="mel4\nclear\nq\n",
        text=True,
        capture_output=True,
        cwd=repo_root,
        env=env,
        timeout=45,
    )

    assert result.returncode == 0
    assert "Filtros do usuário limpos. Voltando ao estado base." in result.stdout
    assert "Saindo..." in result.stdout


def test_cli_subprocess_status_back_then_quit_exits_cleanly(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    env = _build_cli_subprocess_env(repo_root, tmp_path)

    result = subprocess.run(
        [sys.executable, "launchers/cli_entry.py"],
        input="mel4\nstatus-cli\nv\nq\n",
        text=True,
        capture_output=True,
        cwd=repo_root,
        env=env,
        timeout=45,
    )

    assert result.returncode == 0
    assert "STATUS DAS MELHORIAS CLI" in result.stdout
    assert "...filtro anterior restaurado." in result.stdout
    assert "Saindo..." in result.stdout


def test_cli_subprocess_more_then_double_quit_exits_cleanly(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    env = _build_cli_subprocess_env(repo_root, tmp_path)

    result = subprocess.run(
        [sys.executable, "launchers/cli_entry.py"],
        input="mel4\nm\nqq\n",
        text=True,
        capture_output=True,
        cwd=repo_root,
        env=env,
        timeout=45,
    )

    assert result.returncode == 0
    assert "Página 2 de" in result.stdout
    assert "Saindo..." in result.stdout
