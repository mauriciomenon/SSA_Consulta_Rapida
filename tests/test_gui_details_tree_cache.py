from __future__ import annotations

import os
import sqlite3
import time
from types import SimpleNamespace

import pandas as pd

from gui.ssa import details_data_provider
from gui.ssa import gui_details
from gui.ssa.details_dialog_presenter import DetailsDialogCallbacks


class _Cache:
    def __init__(self) -> None:
        self.values: dict[tuple[str, tuple[object, ...]], object] = {}

    def get_cached_value(self, namespace: str, key: tuple[object, ...]) -> object:
        return self.values.get((namespace, key))

    def cache_value(
        self, namespace: str, key: tuple[object, ...], value: object
    ) -> None:
        self.values[(namespace, key)] = value


def test_collect_derivadas_tree_data_uses_cache_for_same_db_state(monkeypatch) -> None:
    calls = {"load": 0}
    window = SimpleNamespace(
        cache_manager=_Cache(),
        _data_uuid="data-1",
        df_completo=pd.DataFrame(),
    )

    def fake_load_snapshot(db_path: str, target: str, *, max_nodes: int):
        calls["load"] += 1
        assert db_path == "/tmp/ssa-cache.db"
        assert target == "202600100"
        assert max_nodes > 0
        return {
            "parents": [],
            "children": [{"ssa": "202600101"}],
            "descendants": [{"ssa": "202600101", "parent": "202600100"}],
            "family_roots": ["202600100"],
            "family_descendants": [{"ssa": "202600101", "parent": "202600100"}],
        }

    monkeypatch.setattr(gui_details, "_resolve_current_db_path", lambda: "/tmp/ssa-cache.db")
    monkeypatch.setattr(details_data_provider, "get_db_mtime", lambda _path: 42.0)
    monkeypatch.setattr(details_data_provider, "load_derivadas_snapshot", fake_load_snapshot)
    monkeypatch.setattr(gui_details, "_get_series_for_ssa", lambda _window, _target: None)

    first = gui_details._collect_derivadas_tree_data(window, "202600100")
    second = gui_details._collect_derivadas_tree_data(window, "202600100")

    assert calls["load"] == 1
    assert second == first


def test_build_derivadas_link_state_uses_index_without_dataframe_scan(monkeypatch) -> None:
    window = SimpleNamespace(
        df_exibido=pd.DataFrame({"numero_ssa": ["202600101"]}),
        df_completo=pd.DataFrame({"numero_ssa": ["202600101"]}),
    )
    ssa_index = {
        "202600101": pd.Series({"numero_ssa": "202600101", "situacao": "ASE"}),
    }

    def fail_scan(*_args, **_kwargs):
        raise AssertionError("full dataframe scan should not run with ssa_index")

    monkeypatch.setattr(gui_details, "_get_cached_normalized_series", fail_scan)

    status_by_ssa, existing_tree_ssas = gui_details._build_derivadas_link_state(
        window,
        {
            "target": "202600101",
            "children": ["202600101"],
        },
        "202600101",
        ssa_index=ssa_index,
    )

    assert "202600101" in existing_tree_ssas
    assert status_by_ssa["202600101"] == "ASE"


def _make_sync_run_db(db_path, rows) -> None:
    conn = sqlite3.connect(str(db_path))
    conn.execute(
        "CREATE TABLE ssa_derivada_sync_run ("
        "sync_run_id INTEGER PRIMARY KEY, status TEXT, graph_fingerprint TEXT)"
    )
    conn.executemany(
        "INSERT INTO ssa_derivada_sync_run "
        "(sync_run_id, status, graph_fingerprint) VALUES (?, ?, ?)",
        rows,
    )
    conn.commit()
    conn.close()


def test_collect_derivadas_tree_data_survives_db_mtime_change(
    tmp_path, monkeypatch
) -> None:
    db_path = tmp_path / "ssa-cache.db"
    _make_sync_run_db(db_path, [(1, "ok", "fp-stable")])
    calls = {"load": 0}
    window = SimpleNamespace(
        cache_manager=_Cache(),
        _data_uuid="data-1",
        df_completo=pd.DataFrame(),
    )

    def fake_load_snapshot(db, target: str, *, max_nodes: int):
        calls["load"] += 1
        assert db == str(db_path)
        assert target == "202600100"
        return {
            "parents": [],
            "children": [{"ssa": "202600101"}],
            "descendants": [{"ssa": "202600101", "parent": "202600100"}],
            "family_roots": ["202600100"],
            "family_descendants": [{"ssa": "202600101", "parent": "202600100"}],
        }

    monkeypatch.setattr(
        gui_details, "_resolve_current_db_path", lambda: str(db_path)
    )
    monkeypatch.setattr(
        details_data_provider, "load_derivadas_snapshot", fake_load_snapshot
    )
    monkeypatch.setattr(
        gui_details, "_get_series_for_ssa", lambda _window, _target: None
    )

    first = gui_details._collect_derivadas_tree_data(window, "202600100")
    future = time.time() + 10
    os.utime(db_path, (future, future))
    second = gui_details._collect_derivadas_tree_data(window, "202600100")

    assert calls["load"] == 1
    assert second == first


def _prefetch_window() -> SimpleNamespace:
    return SimpleNamespace(
        _data_uuid="data-1",
        _data_revision=1,
        df_completo=pd.DataFrame({"numero_ssa": ["202600100"]}),
        df_exibido=pd.DataFrame({"numero_ssa": ["202600100"]}),
        _active_column_filters={},
        search_input=SimpleNamespace(text=lambda: ""),
        db_path="/tmp/ssa-prefetch-missing.db",
    )


def _prefetch_callbacks(builds: dict) -> DetailsDialogCallbacks:
    def _format(*_args, **_kwargs) -> str:
        builds["count"] += 1
        return "details"

    return DetailsDialogCallbacks(
        apply_geometry=lambda *_args, **_kwargs: None,
        build_graph_html=lambda *_args, **_kwargs: "graph",
        build_mermaid_text=lambda *_args, **_kwargs: "mermaid",
        build_tree_html=lambda *_args, **_kwargs: "tree",
        collect_tree_data=lambda *_args, **_kwargs: {"children": []},
        copy_ssa_to_clipboard=lambda *_args, **_kwargs: None,
        extract_svg_markup=lambda *_args, **_kwargs: "svg",
        format_details_html=_format,
        get_series_for_ssa=lambda *_args, **_kwargs: None,
        logger=gui_details.logger,
        normalize_ssa_value=gui_details._normalize_ssa_value,
        resolve_style=lambda *_args, **_kwargs: (
            "#000",
            10.0,
            10.0,
            10.0,
            "monospace",
        ),
        render_payload_context=gui_details._details_render_payload_context,
    )


def test_prefetch_warms_payload_cache_once_per_ssa(monkeypatch) -> None:
    builds = {"count": 0}
    window = _prefetch_window()
    callbacks = _prefetch_callbacks(builds)
    monkeypatch.setattr(
        gui_details, "_build_details_dialog_callbacks", lambda _w: callbacks
    )
    series = pd.Series({"numero_ssa": "202600100"})

    gui_details._schedule_details_prefetch(window, series)
    gui_details._schedule_details_prefetch(window, series)

    normalized = gui_details._normalize_ssa_value(window, "202600100")
    cache = getattr(window, "_details_render_payload_cache", {})
    assert builds["count"] == 1
    assert normalized in cache


def test_prefetch_ignores_missing_series() -> None:
    window = _prefetch_window()

    gui_details._schedule_details_prefetch(window, None)

    assert getattr(window, "_details_render_payload_cache", None) is None


def test_prefetch_swallows_builder_errors(monkeypatch) -> None:
    window = _prefetch_window()

    def _raise(**_kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(gui_details, "warm_details_render_payload", _raise)

    gui_details._schedule_details_prefetch(
        window, pd.Series({"numero_ssa": "202600100"})
    )

    assert getattr(window, "_details_render_payload_cache", None) is None


def test_prefetch_does_not_warm_invalid_ssa(monkeypatch) -> None:
    builds = {"count": 0}
    window = _prefetch_window()
    monkeypatch.setattr(
        gui_details,
        "_build_details_dialog_callbacks",
        lambda _w: _prefetch_callbacks(builds),
    )

    gui_details._schedule_details_prefetch(
        window, pd.Series({"numero_ssa": "   "})
    )

    assert builds["count"] == 0
    assert getattr(window, "_details_render_payload_cache", None) is None
