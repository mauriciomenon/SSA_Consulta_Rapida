from __future__ import annotations

from types import SimpleNamespace

import pandas as pd

from gui.ssa import details_data_provider
from gui.ssa import gui_details


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
