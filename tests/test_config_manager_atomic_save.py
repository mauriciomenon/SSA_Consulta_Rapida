import json
import os
import sys

import pytest

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import core.config_manager as config_manager  # noqa: E402


def test_save_settings_is_atomic_and_does_not_corrupt_existing_file(tmp_path, monkeypatch):
    cfg_dir = tmp_path / "cfg"
    cfg_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("SSA_CONFIG_DIR", str(cfg_dir))
    settings_path = cfg_dir / "settings.json"

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
    cfg_dir = tmp_path / "cfg"
    cfg_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("SSA_CONFIG_DIR", str(cfg_dir))
    settings_path = cfg_dir / "settings.json"

    data = {"a": 1, "b": {"nested": True}}
    config_manager.save_settings(data)

    loaded = json.loads(settings_path.read_text(encoding="utf-8"))
    assert loaded == data


def test_ensure_default_settings_reports_copy_failure(tmp_path, monkeypatch):
    cfg_dir = tmp_path / "cfg"
    cfg_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("SSA_CONFIG_DIR", str(cfg_dir))

    example = cfg_dir / "default_settings.json.example"
    example.write_text("{}", encoding="utf-8")

    def _fail_copy(_src, _dst):
        raise IOError("copy boom")

    monkeypatch.setattr(config_manager, "_atomic_copy_file", _fail_copy)

    errors = config_manager.ensure_default_settings(fail_fast=False)
    assert errors
    assert any(item.startswith("copy_failed:") for item in errors)


def test_ensure_default_settings_reports_generate_failure(tmp_path, monkeypatch):
    cfg_dir = tmp_path / "cfg"
    cfg_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("SSA_CONFIG_DIR", str(cfg_dir))

    monkeypatch.setattr(config_manager, "_atomic_copy_file", lambda _s, _d: (_ for _ in ()).throw(FileNotFoundError()))

    def _fail_write(*_args, **_kwargs):
        raise IOError("write boom")

    monkeypatch.setattr(config_manager, "_atomic_write_json_file", _fail_write)

    errors = config_manager.ensure_default_settings(fail_fast=False)
    assert errors
    assert any(
        item.startswith("copy_failed:") or item.startswith("generate_failed:")
        for item in errors
    )
