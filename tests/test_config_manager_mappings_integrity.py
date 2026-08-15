from __future__ import annotations

import json

import pytest

import core.config_manager as config_manager


def test_load_display_mappings_integrity_restores_file_and_returns_restored(
    tmp_path, monkeypatch
):
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
    invalid_path.write_text(json.dumps({"numero_ssa": "Nº SSA"}), encoding="utf-8")

    result = config_manager.load_column_mappings_integrity()

    on_disk = json.loads(invalid_path.read_text(encoding="utf-8"))
    assert result == on_disk
    assert result == config_manager.get_default_column_mappings()


def test_default_column_mappings_include_portuguese_atividade_especial():
    aliases = config_manager.get_default_column_mappings()["atividade_especial"]

    assert "Atividade Especial" in aliases
    assert "Actividad Especial" in aliases


@pytest.mark.parametrize(
    ("loader_name", "expected_name", "filename"),
    [
        (
            "load_display_mappings_integrity",
            "DEFAULT_DISPLAY_MAPPINGS",
            "display_mappings.json",
        ),
        (
            "load_column_mappings_integrity",
            "get_default_column_mappings",
            "column_mappings.json",
        ),
    ],
)
def test_load_mappings_integrity_returns_defaults_when_restore_write_fails(
    tmp_path,
    monkeypatch,
    loader_name: str,
    expected_name: str,
    filename: str,
):
    cfg_dir = tmp_path / "cfg"
    monkeypatch.setenv("SSA_CONFIG_DIR", str(cfg_dir))

    def _fail_atomic_write(*args, **kwargs):  # noqa: ANN002,ANN003
        raise OSError("write blocked")

    monkeypatch.setattr(config_manager, "_atomic_write_json_file", _fail_atomic_write)
    loader = getattr(config_manager, loader_name)
    expected = (
        getattr(config_manager, expected_name)()
        if expected_name == "get_default_column_mappings"
        else getattr(config_manager, expected_name)
    )
    result = loader()
    assert result == expected
    assert not (cfg_dir / filename).exists()
