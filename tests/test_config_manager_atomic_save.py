import json
import os
import stat
import sys
import builtins

import pytest

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import core.config_manager as config_manager  # noqa: E402
from interface import config_command  # noqa: E402


def test_save_settings_is_atomic_and_does_not_corrupt_existing_file(
    tmp_path, monkeypatch
):
    cfg_dir = tmp_path / "cfg"
    cfg_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("SSA_CONFIG_DIR", str(cfg_dir))
    settings_path = cfg_dir / "settings.json"

    initial = {"a": 1}
    settings_path.write_text(
        json.dumps(initial, indent=4, ensure_ascii=False), encoding="utf-8"
    )
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
    leftovers = [p for p in cfg_dir.iterdir() if p.name.startswith(tmp_prefix)]
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


def test_handle_config_command_merges_with_latest_settings_before_save(monkeypatch):
    saved: list[dict] = []
    load_calls = {"count": 0}
    inputs = iter(["exact", ""])

    def _load_settings():
        load_calls["count"] += 1
        if load_calls["count"] == 1:
            return {
                "default_filters": ["old"],
                "user_preferences": {"filter_mode_default": "contains"},
            }
        return {
            "default_filters": ["external"],
            "user_preferences": {
                "filter_mode_default": "contains",
                "other_pref": "keep",
            },
            "external_key": "keep",
        }

    monkeypatch.setattr(config_command, "load_settings", _load_settings)
    monkeypatch.setattr(config_command, "save_settings", lambda data: saved.append(data))
    monkeypatch.setattr(builtins, "input", lambda _prompt: next(inputs))

    config_command.handle_config_command()

    assert load_calls["count"] == 2
    assert saved == [
        {
            "default_filters": ["external"],
            "user_preferences": {
                "filter_mode_default": "exact",
                "other_pref": "keep",
            },
            "external_key": "keep",
        }
    ]


def test_handle_config_command_skips_save_when_nothing_changed(monkeypatch):
    saved: list[dict] = []
    inputs = iter(["", ""])

    monkeypatch.setattr(
        config_command,
        "load_settings",
        lambda: {
            "default_filters": ["keep"],
            "user_preferences": {"filter_mode_default": "contains"},
        },
    )
    monkeypatch.setattr(config_command, "save_settings", lambda data: saved.append(data))
    monkeypatch.setattr(builtins, "input", lambda _prompt: next(inputs))

    config_command.handle_config_command()

    assert saved == []


def test_save_settings_creates_new_file_with_private_mode(tmp_path, monkeypatch):
    cfg_dir = tmp_path / "cfg"
    cfg_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("SSA_CONFIG_DIR", str(cfg_dir))
    settings_path = cfg_dir / "settings.json"

    config_manager.save_settings({"local_value": "local"})

    assert json.loads(settings_path.read_text(encoding="utf-8")) == {
        "local_value": "local"
    }
    if os.name == "nt":
        return
    assert stat.S_IMODE(settings_path.stat().st_mode) == 0o600


def test_save_settings_preserves_existing_file_mode(tmp_path, monkeypatch):
    cfg_dir = tmp_path / "cfg"
    cfg_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("SSA_CONFIG_DIR", str(cfg_dir))
    settings_path = cfg_dir / "settings.json"
    settings_path.write_text("{}", encoding="utf-8")
    settings_path.chmod(0o640)

    config_manager.save_settings({"mode": "preserved"})

    assert json.loads(settings_path.read_text(encoding="utf-8")) == {
        "mode": "preserved"
    }
    if os.name == "nt":
        return
    assert stat.S_IMODE(settings_path.stat().st_mode) == 0o640


def test_load_settings_reports_user_and_default_paths_when_missing(
    tmp_path, monkeypatch
):
    cfg_dir = tmp_path / "cfg"
    cfg_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("SSA_CONFIG_DIR", str(cfg_dir))

    with pytest.raises(FileNotFoundError) as exc_info:
        config_manager.load_settings()

    message = str(exc_info.value)
    assert str(cfg_dir / "settings.json") in message
    assert str(cfg_dir / "default_settings.json") in message


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
    assert any("falha ao copiar config padrao" in item for item in errors)


def test_ensure_default_settings_raises_in_fail_fast_mode(tmp_path, monkeypatch):
    cfg_dir = tmp_path / "cfg"
    cfg_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("SSA_CONFIG_DIR", str(cfg_dir))

    example = cfg_dir / "default_settings.json.example"
    example.write_text("{}", encoding="utf-8")

    monkeypatch.setattr(
        config_manager,
        "_atomic_copy_file",
        lambda _src, _dst: (_ for _ in ()).throw(IOError("copy boom")),
    )

    with pytest.raises(RuntimeError, match="ensure_default_settings failed"):
        config_manager.ensure_default_settings(fail_fast=True)


def test_ensure_default_settings_reports_generate_failure(tmp_path, monkeypatch):
    cfg_dir = tmp_path / "cfg"
    cfg_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("SSA_CONFIG_DIR", str(cfg_dir))

    monkeypatch.setattr(
        config_manager,
        "_atomic_copy_file",
        lambda _s, _d: (_ for _ in ()).throw(FileNotFoundError()),
    )

    def _fail_write(*_args, **_kwargs):
        raise IOError("write boom")

    monkeypatch.setattr(config_manager, "_atomic_write_json_file", _fail_write)

    errors = config_manager.ensure_default_settings(fail_fast=False)
    assert errors
    assert any("falha ao gerar config padrao" in item for item in errors)


def test_ensure_default_settings_generated_fallback_matches_default_contract(
    tmp_path, monkeypatch
):
    cfg_dir = tmp_path / "cfg"
    cfg_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("SSA_CONFIG_DIR", str(cfg_dir))
    monkeypatch.setattr(config_manager, "CONFIG_DIR", str(tmp_path / "missing_examples"))

    errors = config_manager.ensure_default_settings(fail_fast=True)

    assert errors == []
    generated = json.loads((cfg_dir / "default_settings.json").read_text("utf-8"))
    assert generated["version"] == "1.0.0"
    assert generated["description"] == "Default settings for SSA Consulta Rapida"
    assert generated["import_settings"]["processadas_subdir"] == "processadas"
    assert generated["import_settings"]["upsert_short_circuit_policy"] == "consulta_only"
