"""CF-08: todo JSON de config/ sai da mesma pasta (SSA_CONFIG_DIR valido ou raiz)."""

from __future__ import annotations

import json
from typing import Any, cast

from gui.ssa import filter_aliases
from interface import table_printer
from interface.cli_enhancement_manager import CLIEnhancementManager
from interface.cli_width_manager import CLIWidthManager


def _config_dir_with_markers(tmp_path, monkeypatch):
    cfg_dir = tmp_path / "cfg"
    cfg_dir.mkdir()
    payloads = {
        "column_priority.json": {"marker": "priority"},
        "display_mappings.json": {"marker": "display"},
        "gui_main_preferences.json": {"marker": "gui"},
        "filter_aliases.json": {"marker": ["alias"]},
        "cli_enhancements.json": {"marker": "cli"},
    }
    for name, payload in payloads.items():
        (cfg_dir / name).write_text(json.dumps(payload), encoding="utf-8")
    monkeypatch.setenv("SSA_CONFIG_DIR", str(cfg_dir))
    monkeypatch.chdir(tmp_path)
    return cfg_dir


def test_cli_loaders_read_active_config_dir(tmp_path, monkeypatch):
    _config_dir_with_markers(tmp_path, monkeypatch)

    width_manager = CLIWidthManager()

    assert table_printer._load_priority_config() == {"marker": "priority"}
    assert width_manager.cli_priority == {"marker": "priority"}
    assert width_manager.display_mappings == {"marker": "display"}
    assert width_manager.gui_config == {"marker": "gui"}


def test_filter_aliases_read_active_config_dir(tmp_path, monkeypatch):
    _config_dir_with_markers(tmp_path, monkeypatch)
    cast(Any, filter_aliases.load_filter_alias_map_once).cache_clear()
    try:
        assert filter_aliases.load_filter_alias_map_once() == {"marker": ["alias"]}
    finally:
        cast(Any, filter_aliases.load_filter_alias_map_once).cache_clear()


def test_cli_enhancements_file_in_active_config_dir(tmp_path, monkeypatch):
    cfg_dir = _config_dir_with_markers(tmp_path, monkeypatch)
    monkeypatch.delenv("SSA_CLI_ENHANCEMENTS_PATH", raising=False)

    manager = CLIEnhancementManager()

    assert manager.settings_file == str(cfg_dir / "cli_enhancements.json")
