from __future__ import annotations

from types import SimpleNamespace

from gui.ssa import details_data_provider


def test_resolve_current_db_path_prefers_window_db_path() -> None:
    window = SimpleNamespace(db_path="/tmp/ssa-test.db")

    assert details_data_provider.resolve_current_db_path(window) == "/tmp/ssa-test.db"


def test_get_db_mtime_returns_none_for_missing_path() -> None:
    assert details_data_provider.get_db_mtime(None) is None
    assert details_data_provider.get_db_mtime("/tmp/ssa-missing-details.db") is None


def test_load_derivadas_snapshot_returns_none_without_existing_db() -> None:
    snapshot = details_data_provider.load_derivadas_snapshot(
        "/tmp/ssa-missing-details.db",
        "202600001",
        max_nodes=10,
    )

    assert snapshot is None
