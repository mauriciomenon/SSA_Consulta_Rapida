import builtins
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


def test_save_settings_handler_reraises_save_errors(monkeypatch, capsys):
    def _fake_save_settings(_settings):
        raise OSError("disk full")

    monkeypatch.setattr(command_handlers, "save_settings", _fake_save_settings)

    try:
        command_handlers._save_settings_handler({"k": "v"})
        assert False, "expected OSError"
    except OSError:
        pass

    out = capsys.readouterr().out
    assert "Nao foi possivel salvar as configuracoes" in out


def test_column_visibility_loop_continues_when_save_fails(monkeypatch):
    settings = {
        "display_settings": {
            "column_visibility": {"numero_ssa": True},
        }
    }

    monkeypatch.setattr(
        command_handlers,
        "_load_mappings_handler",
        lambda _file: {"numero_ssa": "Numero SSA"},
    )

    def _raise_save(_settings):
        raise OSError("disk full")

    monkeypatch.setattr(command_handlers, "_save_settings_handler", _raise_save)

    answers = iter(["1", "0"])
    monkeypatch.setattr(builtins, "input", lambda _prompt="": next(answers))

    command_handlers._handle_column_visibility(settings)

    # Save falhou, entao a alteracao deve ser desfeita para estado original.
    assert settings["display_settings"]["column_visibility"]["numero_ssa"] is True


def test_save_settings_handler_clears_mapping_cache(monkeypatch):
    command_handlers._MAPPINGS_CACHE_MANAGER.clear()
    command_handlers._MAPPINGS_CACHE_MANAGER.set("display_mappings.json", {"k": "v"})

    monkeypatch.setattr(command_handlers, "save_settings", lambda _settings: None)

    command_handlers._save_settings_handler({"x": 1})

    assert command_handlers._MAPPINGS_CACHE_MANAGER.get("display_mappings.json") is None


def test_save_settings_handler_reports_resolved_settings_path(monkeypatch, capsys):
    monkeypatch.setattr(command_handlers, "save_settings", lambda _settings: None)
    monkeypatch.setattr(
        command_handlers,
        "_resolve_settings_path_for_message",
        lambda: "/tmp/custom/settings.json",
    )

    command_handlers._save_settings_handler({"x": 1})

    out = capsys.readouterr().out
    assert "/tmp/custom/settings.json" in out
