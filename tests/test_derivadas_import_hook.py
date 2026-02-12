from __future__ import annotations

import types

from core import app_logic


def test_optional_derivadas_sync_disabled_by_default(monkeypatch):
    monkeypatch.delenv("SSA_DERIVADAS_SYNC", raising=False)
    result = app_logic._run_optional_derivadas_sync("data/ssas.db", "ssa_table")
    assert result is None


def test_optional_derivadas_sync_enabled_passes_expected_args(monkeypatch):
    monkeypatch.setenv("SSA_DERIVADAS_SYNC", "1")
    monkeypatch.setenv("SSA_DERIVADAS_SHEET_FILE", "docs_entrada/derivadas.csv")
    monkeypatch.setenv("SSA_DERIVADAS_SHEET_NAME", "Relacoes")
    monkeypatch.setenv("SSA_DERIVADAS_SHEET_PARENT_COL", "mae")
    monkeypatch.setenv("SSA_DERIVADAS_SHEET_CHILD_COL", "filha")
    monkeypatch.setenv("SSA_DERIVADAS_SHEET_LABEL_COL", "rotulo")
    monkeypatch.setenv("SSA_DERIVADAS_FULL_REBUILD", "1")
    monkeypatch.setenv("SSA_DERIVADAS_VERIFY_ONLY", "1")
    monkeypatch.setenv("SSA_DERIVADAS_NO_DB_SOURCE", "1")

    captured: dict[str, object] = {}

    def fake_sync_derivadas(**kwargs):
        captured.update(kwargs)
        return {"merge_stats": {"merged_edges": 1}, "reconciliation": {}}

    fake_module = types.SimpleNamespace(sync_derivadas=fake_sync_derivadas)
    monkeypatch.setitem(__import__("sys").modules, "armazenamento.derivadas_sync", fake_module)

    out = app_logic._run_optional_derivadas_sync("data/ssas.db", "ssa_table")
    assert out is not None
    assert captured["db_path"] == "data/ssas.db"
    assert captured["table_name"] == "ssa_table"
    assert captured["sheet_file"] == "docs_entrada/derivadas.csv"
    assert captured["sheet_name"] == "Relacoes"
    assert captured["sheet_parent_col"] == "mae"
    assert captured["sheet_child_col"] == "filha"
    assert captured["sheet_label_col"] == "rotulo"
    assert captured["full_rebuild"] is True
    assert captured["verify_only"] is True
    assert captured["include_db_source"] is False


def test_optional_derivadas_sync_errors_do_not_break_flow(monkeypatch):
    monkeypatch.setenv("SSA_DERIVADAS_SYNC", "1")

    def fake_sync_derivadas(**_kwargs):
        raise RuntimeError("boom")

    fake_module = types.SimpleNamespace(sync_derivadas=fake_sync_derivadas)
    monkeypatch.setitem(__import__("sys").modules, "armazenamento.derivadas_sync", fake_module)

    out = app_logic._run_optional_derivadas_sync("data/ssas.db", "ssa_table")
    assert out is None

