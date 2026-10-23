"""CF-02: sem SSA_CONFIG_DIR, config/ vem da raiz do codigo, nao da pasta corrente."""

import os

import core.config_manager as config_manager
from gui import gui_config
from interface import command_handlers

PROJECT_CONFIG = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config"
)


def test_config_paths_ignore_cwd_without_env(tmp_path, monkeypatch):
    monkeypatch.delenv("SSA_CONFIG_DIR", raising=False)
    monkeypatch.chdir(tmp_path)

    resolved = {
        "user": config_manager.resolve_user_settings_path(),
        "default": config_manager.resolve_default_settings_path(),
        "mapping_cli": command_handlers._resolve_mapping_path("column_mappings.json"),
        "settings_cli": command_handlers._resolve_settings_path_for_message(),
        "gui_prefs": gui_config.get_gui_main_preferences_path(),
    }

    for name, path in resolved.items():
        assert path is not None and os.path.dirname(path) == PROJECT_CONFIG, (name, path)
    config_manager.load_settings()
    assert list(tmp_path.iterdir()) == []


def test_config_paths_follow_env_when_set(tmp_path, monkeypatch):
    cfg_dir = tmp_path / "cfg"
    cfg_dir.mkdir()
    monkeypatch.setenv("SSA_CONFIG_DIR", str(cfg_dir))

    path = command_handlers._resolve_mapping_path("column_mappings.json")

    assert path is not None and os.path.dirname(path) == str(cfg_dir)
