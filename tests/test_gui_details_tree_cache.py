from __future__ import annotations

import os
import sqlite3
import time
from types import SimpleNamespace
from typing import Any, cast

import pandas as pd
import pytest

from armazenamento.derivadas_sync import scan_derivadas_consistency, sync_derivadas
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


@pytest.mark.parametrize("campo,novo", [("relation_type", 3), ("relation_raw_label", "Rotulo B")])
def test_external_sync_invalidates_relation_metadata_cache(
    temp_db, tmp_path, monkeypatch, campo, novo
):
    sheet = tmp_path / "derivadas.csv"
    sheet.write_text(
        "parent_ssa,child_ssa,relation_label\n202600100,202600101,Rotulo A\n",
        encoding="utf-8",
    )
    sync_derivadas(temp_db, include_db_source=False, sheet_file=str(sheet))
    window = SimpleNamespace(
        db_path=temp_db,
        cache_manager=_Cache(),
        _data_uuid="dados-estaveis",
        _data_revision=1,
        df_completo=pd.DataFrame(),
    )
    loads = []
    load = details_data_provider.load_derivadas_snapshot

    def record_load(*args, **kwargs):
        loads.append(args)
        return load(*args, **kwargs)

    monkeypatch.setattr(details_data_provider, "load_derivadas_snapshot", record_load)
    monkeypatch.setattr(gui_details, "_get_series_for_ssa", lambda *_args: None)
    first = gui_details._collect_derivadas_tree_data(window, "202600100")
    assert gui_details._collect_derivadas_tree_data(window, "202600100") is first
    assert len(loads) == 1
    first_token = details_data_provider.get_derivadas_graph_cache_token(temp_db)

    with sqlite3.connect(temp_db) as writer:
        writer.execute(f"UPDATE ssa_derivada_source SET {campo} = ?", (novo,))
    sync_derivadas(temp_db)
    second = gui_details._collect_derivadas_tree_data(window, "202600100")

    assert details_data_provider.get_derivadas_graph_cache_token(temp_db) != first_token
    assert second != first
    assert len(loads) == 2
    assert gui_details._collect_derivadas_tree_data(window, "202600100") is second
    assert len(loads) == 2
    assert scan_derivadas_consistency(temp_db)["is_consistent"]


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

    # Mesma geracao de arquivos e revisao: o token fica memoizado e a
    # selecao repetida nao reabre consulta SQLite.
    gui_details.update_details_from_selection(window)
    timers[0].callback()
    assert len(probes) == 1
    assert rendered == ["antes"]

    # Um token novo so e consultado quando a geracao/revisao muda.
    graph_token[0] = "fp-2"
    SSAMainWindow._bump_data_revision(cast(Any, window), "sync")
    gui_details.update_details_from_selection(window)
    timers[0].callback()
    assert len(probes) == 2
    assert rendered == ["antes", "antes"]

    gui_details.update_details_from_selection(window)
    SSAMainWindow._bump_data_revision(cast(Any, window), "reload")
    assert not timers[0].active
    assert window._pending_details_series is None
    series = pd.Series({"numero_ssa": "202600100", "descricao_ssa": "depois"})
    gui_details.update_details_from_selection(window)
    timers[0].callback()
    assert len(probes) == 3
    assert rendered == ["antes", "antes", "depois"]


def _details_signature_window(db_path, rendered, properties):
    series = pd.Series({"numero_ssa": "202600100", "descricao_ssa": "antes"})
    window = SimpleNamespace(
        db_path=str(db_path),
        _data_uuid="d1",
        _data_revision=1,
        df_completo=pd.DataFrame([series]),
        _active_column_filters={},
        search_input=SimpleNamespace(text=lambda: ""),
        clear_filter_cache=lambda: None,
        details_text=SimpleNamespace(
            property=lambda key: properties.get(key),
            setProperty=lambda key, value: properties.update({key: value}),
            document=lambda: SimpleNamespace(isEmpty=lambda: not rendered),
        ),
        cache_manager=_Cache(),
    )
    return window, series


def test_details_db_signature_memoized_by_db_and_wal_generation(
    tmp_path, monkeypatch
) -> None:
    """O token de assinatura consulta o SQLite uma vez por geracao do
    conjunto .db/-wal/-journal: renders repetidos nao reabrem o banco;
    commit externo em WAL (sem mexer no .db), troca de banco e reload de
    revisao invalidam. O spy delega ao provider real para observar o
    fingerprint fp-1 -> fp-2."""
    db_path = tmp_path / "sig.db"
    other_db = tmp_path / "other.db"
    make_sync_run_db(db_path, [(1, "ok", "fp-1")])
    make_sync_run_db(other_db, [(1, "ok", "fp-x")])

    rendered: list[str] = []
    properties: dict[str, object] = {}
    window, series = _details_signature_window(db_path, rendered, properties)

    probes: list[tuple[str, object]] = []
    real_token = details_data_provider.get_derivadas_graph_cache_token

    def spy(path):
        token = real_token(path)
        probes.append(token)
        return token

    def render(_window, current, signature):
        rendered.append(current["numero_ssa"])
        properties["details_render_signature"] = signature

    monkeypatch.setattr(
        details_data_provider, "get_derivadas_graph_cache_token", spy
    )
    monkeypatch.setattr(gui_details, "_render_main_details_html", render)

    # WAL configurado e writer externo mantido aberto ANTES de popular o
    # cache: a invalidacao do commit seguinte so pode vir do -wal. A
    # escrita neutra de warmup cria o -wal de uma vez - a primeira
    # consulta read-only tambem criaria um -wal vazio e mudaria a
    # geracao entre as duas primeiras chamadas.
    writer = sqlite3.connect(db_path)
    try:
        writer.execute("PRAGMA journal_mode=WAL")
        writer.execute("PRAGMA wal_autocheckpoint=0")
        writer.execute("CREATE TABLE IF NOT EXISTS _wal_warmup (x INTEGER)")
        writer.commit()

        gui_details._update_details_from_series(window, series)
        gui_details._update_details_from_series(window, series)
        assert [token for _kind, token in probes] == ["fp-1"]
        assert rendered == ["202600100"]

        main_before = db_path.stat()
        writer.execute(
            "INSERT INTO ssa_derivada_sync_run VALUES (?, ?, ?)",
            (2, "ok", "fp-2"),
        )
        writer.commit()
        main_after = db_path.stat()
        # O commit externo foi para o WAL: identidade, tamanho e
        # timestamps do .db principal nao mudam.
        assert (
            main_after.st_dev,
            main_after.st_ino,
            main_after.st_size,
            main_after.st_mtime_ns,
            main_after.st_ctime_ns,
        ) == (
            main_before.st_dev,
            main_before.st_ino,
            main_before.st_size,
            main_before.st_mtime_ns,
            main_before.st_ctime_ns,
        )

        gui_details._update_details_from_series(window, series)
        assert [token for _kind, token in probes] == ["fp-1", "fp-2"]
        assert rendered == ["202600100", "202600100"]

        # Troca de banco invalida mesmo com conteudo equivalente; voltar
        # ao primeiro tambem (outra geracao canonica).
        window.db_path = str(other_db)
        gui_details._update_details_from_series(window, series)
        assert len(probes) == 3
        window.db_path = str(db_path)
        gui_details._update_details_from_series(window, series)
        assert len(probes) == 4

        # Reload local (nova revisao) invalida e forca re-render: o bump
        # tambem limpa a assinatura de render armazenada.
        SSAMainWindow._bump_data_revision(cast(Any, window), "reload")
        gui_details._update_details_from_series(window, series)
        assert len(probes) == 5
        assert len(rendered) == 5
    finally:
        writer.close()


def test_details_db_signature_does_not_memoize_fallback_token(
    tmp_path, monkeypatch
) -> None:
    """Token 'mtime' (falha transitoria ou ausencia de fingerprint) nao
    fica memoizado: a chamada seguinte consulta de novo e recupera o
    token real quando a leitura volta."""
    db_path = tmp_path / "sig.db"
    make_sync_run_db(db_path, [(1, "ok", "fp-1")])

    calls: list[str] = []

    def flaky_fingerprint(path):
        calls.append(str(path))
        if len(calls) == 1:
            return None
        return "fp-1"

    monkeypatch.setattr(
        details_data_provider,
        "_latest_derivadas_graph_fingerprint",
        flaky_fingerprint,
    )
    window = SimpleNamespace(
        db_path=str(db_path), _data_uuid="d1", _data_revision=1
    )

    first = gui_details._get_details_db_signature(window)
    second = gui_details._get_details_db_signature(window)
    third = gui_details._get_details_db_signature(window)

    assert first[1][0] == "mtime"
    assert second == (str(db_path), ("graph", "fp-1"))
    assert third == second
    assert len(calls) == 2


def test_details_db_signature_no_reuse_when_generation_stat_fails(
    tmp_path, monkeypatch
) -> None:
    """OSError que nao FileNotFoundError no stat de sidecar nao e
    'arquivo ausente': a geracao falha e o cache nao e reutilizado."""
    db_path = tmp_path / "sig.db"
    make_sync_run_db(db_path, [(1, "ok", "fp-1")])
    wal_path = f"{db_path}-wal"
    with open(wal_path, "wb") as handle:
        handle.write(b"wal")

    real_stat = os.stat

    def flaky_stat(path, *args, **kwargs):
        if str(path) == wal_path:
            raise PermissionError("stat recusado")
        return real_stat(path, *args, **kwargs)

    calls: list[str] = []

    def spy(path):
        calls.append(str(path))
        return ("graph", "fp-1")

    monkeypatch.setattr(os, "stat", flaky_stat)
    monkeypatch.setattr(
        details_data_provider, "get_derivadas_graph_cache_token", spy
    )
    window = SimpleNamespace(
        db_path=str(db_path), _data_uuid="d1", _data_revision=1
    )

    gui_details._get_details_db_signature(window)
    gui_details._get_details_db_signature(window)

    assert len(calls) == 2
