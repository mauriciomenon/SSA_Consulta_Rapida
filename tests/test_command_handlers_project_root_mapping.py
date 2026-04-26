from __future__ import annotations

import json

from interface import command_handlers as ch


def test_load_mappings_handler_uses_project_root(tmp_path, monkeypatch):
    cfg_dir = tmp_path / "config"
    cfg_dir.mkdir(parents=True, exist_ok=True)
    mapping_file = cfg_dir / "sample_mappings.json"
    mapping_file.write_text(json.dumps({"k": "v"}), encoding="utf-8")

    def _fake_resolve_config_path(path: str) -> str:
        if path == "config/sample_mappings.json":
            return str(mapping_file)
        return str(tmp_path / path)

    monkeypatch.setattr(ch, "_resolve_config_path", _fake_resolve_config_path)

    data = ch._load_mappings_handler("sample_mappings.json")
    assert data == {"k": "v"}


def test_load_mappings_handler_caches_display_mappings(monkeypatch):
    calls = {"count": 0}
    ch._MAPPINGS_CACHE_MANAGER.clear()

    def _fake_load_display():
        calls["count"] += 1
        return {"numero_ssa": "Numero SSA"}

    monkeypatch.setattr(ch, "load_display_mappings_integrity", _fake_load_display)

    first = ch._load_mappings_handler("display_mappings.json")
    second = ch._load_mappings_handler("display_mappings.json")

    assert first == {"numero_ssa": "Numero SSA"}
    assert second == {"numero_ssa": "Numero SSA"}
    assert calls["count"] == 1
