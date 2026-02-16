import json
import os
import sys

import pytest

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import core.config_manager as config_manager  # noqa: E402


def test_save_settings_is_atomic_and_does_not_corrupt_existing_file(tmp_path, monkeypatch):
    settings_path = tmp_path / "settings.json"
    monkeypatch.setattr(config_manager, "USER_SETTINGS_FILE", str(settings_path))

    initial = {"a": 1}
    settings_path.write_text(json.dumps(initial, indent=4, ensure_ascii=False), encoding="utf-8")
    original_text = settings_path.read_text(encoding="utf-8")

    tmp_prefix = f".{settings_path.name}.tmp."

    def bad_dump(obj, fh, indent=4, ensure_ascii=False):  # noqa: ARG001
        fh.write("{")
        fh.flush()
        raise RuntimeError("boom")

    monkeypatch.setattr(config_manager.json, "dump", bad_dump)

    with pytest.raises(RuntimeError):
        config_manager.save_settings({"b": 2})

    assert settings_path.read_text(encoding="utf-8") == original_text
    leftovers = [p for p in tmp_path.iterdir() if p.name.startswith(tmp_prefix)]
    assert leftovers == []


def test_save_settings_writes_valid_json(tmp_path, monkeypatch):
    settings_path = tmp_path / "settings.json"
    monkeypatch.setattr(config_manager, "USER_SETTINGS_FILE", str(settings_path))

    data = {"a": 1, "b": {"nested": True}}
    config_manager.save_settings(data)

    loaded = json.loads(settings_path.read_text(encoding="utf-8"))
    assert loaded == data

