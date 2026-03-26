from __future__ import annotations

import builtins
import io
import json

import interface.command_handlers as command_handlers


def test_load_mappings_handler_delegates_display_mappings(monkeypatch):
    payload = {"numero_ssa": "N SSA"}
    monkeypatch.setattr(
        command_handlers, "load_display_mappings_integrity", lambda: payload
    )

    result = command_handlers._load_mappings_handler("display_mappings.json")

    assert result == payload


def test_load_mappings_handler_returns_empty_on_invalid_json(monkeypatch, caplog):
    def _fake_open(*_args, **_kwargs):
        return io.StringIO("{")

    monkeypatch.setattr(builtins, "open", _fake_open)

    with caplog.at_level("WARNING"):
        result = command_handlers._load_mappings_handler("column_mappings.json")

    assert result == {}
    assert "Falha ao carregar mapping" in caplog.text


def test_load_mappings_handler_returns_dict_when_json_is_valid(monkeypatch):
    payload = {"a": ["x", "y"]}

    def _fake_open(*_args, **_kwargs):
        return io.StringIO(json.dumps(payload))

    monkeypatch.setattr(builtins, "open", _fake_open)

    result = command_handlers._load_mappings_handler("column_mappings.json")

    assert result == payload


def test_load_mappings_handler_returns_empty_when_display_loader_raises(
    monkeypatch, caplog
):
    command_handlers._MAPPINGS_CACHE_MANAGER.clear()

    def _boom():
        raise RuntimeError("fail")

    monkeypatch.setattr(command_handlers, "load_display_mappings_integrity", _boom)

    with caplog.at_level("WARNING"):
        result = command_handlers._load_mappings_handler("display_mappings.json")

    assert result == {}
    assert "Falha ao carregar display mappings por integridade" in caplog.text


def test_load_mappings_handler_rejects_path_traversal_name(caplog):
    with caplog.at_level("WARNING"):
        result = command_handlers._load_mappings_handler("../escape.json")

    assert result == {}
    assert "Mapping fora do escopo permitido" in caplog.text
