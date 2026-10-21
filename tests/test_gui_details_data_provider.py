from __future__ import annotations

import os
import sqlite3
from types import SimpleNamespace

from gui.ssa import details_data_provider
from tests._helpers.db_utils import make_sync_run_db


def test_resolve_current_db_path_prefers_window_db_path() -> None:
    window = SimpleNamespace(db_path="/tmp/ssa-test.db")

    assert details_data_provider.resolve_current_db_path(window) == "/tmp/ssa-test.db"


def test_get_db_mtime_returns_none_for_missing_path(tmp_path) -> None:
    assert details_data_provider.get_db_mtime(None) is None
    assert details_data_provider.get_db_mtime(str(tmp_path / "missing.db")) is None


def test_load_derivadas_snapshot_returns_none_without_existing_db(tmp_path) -> None:
    snapshot = details_data_provider.load_derivadas_snapshot(
        str(tmp_path / "missing.db"),
        "202600001",
        max_nodes=10,
    )

    assert snapshot is None


def test_graph_cache_token_uses_latest_ok_fingerprint(tmp_path) -> None:
    db_path = tmp_path / "sync.db"
    make_sync_run_db(db_path, [(1, "ok", "fp-1"), (2, "ok", "fp-2")])

    token = details_data_provider.get_derivadas_graph_cache_token(str(db_path))

    assert token == ("graph", "fp-2")


def test_graph_cache_token_falls_back_when_latest_run_failed(tmp_path) -> None:
    db_path = tmp_path / "sync.db"
    make_sync_run_db(db_path, [(1, "ok", "fp-1"), (2, "error", "fp-2")])

    token = details_data_provider.get_derivadas_graph_cache_token(str(db_path))

    assert token == ("mtime", os.path.getmtime(str(db_path)))


def test_graph_cache_token_falls_back_without_sync_table(tmp_path) -> None:
    db_path = tmp_path / "empty.db"
    sqlite3.connect(str(db_path)).close()

    token = details_data_provider.get_derivadas_graph_cache_token(str(db_path))

    assert token == ("mtime", os.path.getmtime(str(db_path)))


def test_graph_cache_token_falls_back_on_null_fingerprint(tmp_path) -> None:
    db_path = tmp_path / "sync.db"
    make_sync_run_db(db_path, [(1, "ok", None)])

    token = details_data_provider.get_derivadas_graph_cache_token(str(db_path))

    assert token == ("mtime", os.path.getmtime(str(db_path)))


def test_graph_cache_token_for_missing_db(tmp_path) -> None:
    token = details_data_provider.get_derivadas_graph_cache_token(
        str(tmp_path / "missing.db")
    )

    assert token == ("mtime", None)


def test_graph_click_offset_follows_top_alignment() -> None:
    from PyQt6.QtCore import QPointF, Qt

    from gui.ssa.main_window_bottom_section import _event_position_in_graph_space

    class _Size:
        def width(self):
            return 100.0

        def height(self):
            return 50.0

    class _Pixmap:
        def isNull(self):
            return False

        def deviceIndependentSize(self):
            return _Size()

    class _Label:
        def pixmap(self):
            return _Pixmap()

        def width(self):
            return 300

        def height(self):
            return 250

        def alignment(self):
            return Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop

    event = SimpleNamespace(position=lambda: QPointF(110.0, 20.0))

    # Pixmap 100x50 centralizado na horizontal (offset 100) e no topo (offset 0).
    assert _event_position_in_graph_space(_Label(), event) == (10.0, 20.0)


def test_load_derivadas_snapshot_failure_is_logged_as_warning(
    tmp_path, monkeypatch, caplog
) -> None:
    db_path = tmp_path / "ssas.db"
    db_path.write_bytes(b"")
    from armazenamento import derivadas_queries

    def _boom(*_args, **_kwargs):
        raise RuntimeError("tabela ausente")

    monkeypatch.setattr(derivadas_queries, "get_ssa_hierarchy_snapshot", _boom)

    with caplog.at_level("WARNING", logger=details_data_provider.logger.name):
        result = details_data_provider.load_derivadas_snapshot(
            str(db_path), "202600001", max_nodes=10
        )

    assert result is None
    assert "202600001" in caplog.text and "tabela ausente" in caplog.text
