from __future__ import annotations

import builtins
import io
import json

import core.app_logic as app_logic


def test_get_filter_alias_map_returns_empty_on_invalid_json(monkeypatch, caplog):
    monkeypatch.setattr(app_logic.os.path, "exists", lambda _path: True)

    def _fake_open(*_args, **_kwargs):
        return io.StringIO("{")

    monkeypatch.setattr(builtins, "open", _fake_open)

    with caplog.at_level("WARNING"):
        result = app_logic.get_filter_alias_map()

    assert result == {}
    assert "Falha ao carregar aliases de filtro" in caplog.text


def test_get_filter_alias_map_returns_dict_when_valid(monkeypatch):
    monkeypatch.setattr(app_logic.os.path, "exists", lambda _path: True)

    payload = {"_global": {"em andamento": "andamento"}}

    def _fake_open(*_args, **_kwargs):
        return io.StringIO(json.dumps(payload))

    monkeypatch.setattr(builtins, "open", _fake_open)

    result = app_logic.get_filter_alias_map()

    assert result == payload
