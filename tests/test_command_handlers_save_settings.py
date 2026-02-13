import os
import sys

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import interface.command_handlers as command_handlers  # noqa: E402


def test_save_settings_handler_delegates_to_config_manager(monkeypatch, capsys):
    called = {"settings": None}

    def _fake_save_settings(settings):
        called["settings"] = settings

    monkeypatch.setattr(command_handlers, "save_settings", _fake_save_settings)

    payload = {"k": "v"}
    command_handlers._save_settings_handler(payload)

    assert called["settings"] == payload
    out = capsys.readouterr().out
    assert "Configuracoes salvas" in out

