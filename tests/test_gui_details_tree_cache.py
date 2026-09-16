from __future__ import annotations

import os
import sqlite3
import time
from types import SimpleNamespace
from typing import Any, cast

import pandas as pd

from gui.gui_ssa import SSAMainWindow
from gui.ssa import details_data_provider
from gui.ssa import gui_details
from tests._helpers.db_utils import make_sync_run_db


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


def test_collect_derivadas_tree_data_survives_db_mtime_change(
    tmp_path, monkeypatch
) -> None:
    db_path = tmp_path / "ssa-cache.db"
    make_sync_run_db(db_path, [(1, "ok", "fp-stable")])
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

    writer = sqlite3.connect(db_path)
    try:
        writer.execute("PRAGMA journal_mode=WAL")
        writer.execute("PRAGMA wal_autocheckpoint=0")
        previous_mtime = db_path.stat().st_mtime_ns
        writer.execute(
            "INSERT INTO ssa_derivada_sync_run VALUES (?, ?, ?)",
            (2, "ok", "fp-alterado"),
        )
        writer.commit()
        assert db_path.stat().st_mtime_ns == previous_mtime

        gui_details._collect_derivadas_tree_data(window, "202600100")

        assert calls["load"] == 2
    finally:
        writer.close()


def test_selection_debounces_graph_probe_and_cancels_pending_data_on_reload(
    tmp_path, monkeypatch
) -> None:
    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
    timers = []

    class _Timer:
        def __init__(self, _window):
            self.callback = lambda: None
            self.active = False
            self.timeout = SimpleNamespace(connect=self._connect)
            timers.append(self)

        def _connect(self, callback):
            self.callback = callback

        def setSingleShot(self, _value):
            return None

        def setInterval(self, _value):
            return None

        def start(self):
            self.active = True

        def stop(self):
            self.active = False

    monkeypatch.setattr(gui_details, "QTimer", _Timer)
    probes = []
    rendered = []
    graph_token = ["fp-1"]
    properties = {}
    series = pd.Series({"numero_ssa": "202600100", "descricao_ssa": "antes"})
    window = SimpleNamespace(
        db_path=str(tmp_path / "db.sqlite"),
        _data_uuid="d1",
        _data_revision=1,
        df_completo=pd.DataFrame([series]),
        _active_column_filters={},
        search_input=SimpleNamespace(text=lambda: ""),
        table_widget=SimpleNamespace(
            rowCount=lambda: 1,
            selectionModel=lambda: SimpleNamespace(
                selectedRows=lambda: [SimpleNamespace(row=lambda: 0)]
            ),
        ),
        _get_series_from_row=lambda _row: series,
        clear_filter_cache=lambda: None,
        details_text=SimpleNamespace(
            property=lambda key: properties.get(key),
            setProperty=lambda key, value: properties.update({key: value}),
            document=lambda: SimpleNamespace(isEmpty=lambda: not rendered),
        ),
        cache_manager=_Cache(),
    )

    def probe(path):
        probes.append(path)
        return "graph", graph_token[0]

    def render(_window, current, signature):
        gui_details._collect_derivadas_tree_data(window, current["numero_ssa"])
        rendered.append(current["descricao_ssa"])
        properties["details_render_signature"] = signature

    monkeypatch.setattr(details_data_provider, "get_derivadas_graph_cache_token", probe)
    monkeypatch.setattr(details_data_provider, "load_derivadas_snapshot", lambda *_a, **_k: None)
    monkeypatch.setattr(gui_details, "_get_series_for_ssa", lambda *_a: None)
    monkeypatch.setattr(gui_details, "_render_main_details_html", render)

    gui_details.update_details_from_selection(window)
    gui_details.update_details_from_selection(window)
    assert probes == []
    assert rendered == []
    assert len(timers) == 1

    timers[0].callback()
    assert len(probes) == 1
    assert rendered == ["antes"]
    assert getattr(window, "_details_render_payload_cache", {}) == {}
    assert window._details_active_db_signature is None

    gui_details.update_details_from_selection(window)
    timers[0].callback()
    assert len(probes) == 2
    assert rendered == ["antes"]

    graph_token[0] = "fp-2"
    gui_details.update_details_from_selection(window)
    timers[0].callback()
    assert len(probes) == 3
    assert rendered == ["antes", "antes"]

    gui_details.update_details_from_selection(window)
    SSAMainWindow._bump_data_revision(cast(Any, window), "reload")
    assert not timers[0].active
    assert window._pending_details_series is None
    series = pd.Series({"numero_ssa": "202600100", "descricao_ssa": "depois"})
    gui_details.update_details_from_selection(window)
    timers[0].callback()
    assert rendered == ["antes", "antes", "depois"]
