from __future__ import annotations

import json

import core.config_manager as config_manager


def test_load_display_mappings_integrity_restores_file_and_returns_restored(tmp_path, monkeypatch):
    cfg_dir = tmp_path / "cfg"
    monkeypatch.setenv("SSA_CONFIG_DIR", str(cfg_dir))

    result = config_manager.load_display_mappings_integrity()

    path = cfg_dir / "display_mappings.json"
    assert path.exists()
    on_disk = json.loads(path.read_text(encoding="utf-8"))
    assert result == on_disk
    assert result == config_manager.DEFAULT_DISPLAY_MAPPINGS


def test_load_column_mappings_integrity_restores_invalid_file(tmp_path, monkeypatch):
    cfg_dir = tmp_path / "cfg"
    cfg_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("SSA_CONFIG_DIR", str(cfg_dir))

    invalid_path = cfg_dir / "column_mappings.json"
    invalid_path.write_text(json.dumps({"numero_ssa": []}), encoding="utf-8")

    result = config_manager.load_column_mappings_integrity()

    on_disk = json.loads(invalid_path.read_text(encoding="utf-8"))
    assert result == on_disk
    assert result == config_manager.DEFAULT_COLUMN_MAPPINGS
