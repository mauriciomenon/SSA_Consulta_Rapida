from __future__ import annotations

import json
from pathlib import Path


def test_default_settings_declares_import_settings_contract() -> None:
    settings_path = Path("config/default_settings.json")
    data = json.loads(settings_path.read_text(encoding="utf-8"))

    import_settings = data.get("import_settings")
    assert isinstance(import_settings, dict)

    expected_keys = {
        "include_processadas_in_full_rescan",
        "processadas_subdir",
        "ignore_nosurvivor_in_full_rescan",
        "nosurvivor_subdir",
        "move_processed_after_import",
        "route_zero_survivor_to_nosurvivor",
        "upsert_short_circuit_policy",
    }
    assert expected_keys.issubset(import_settings.keys())


def test_load_settings_merges_defaults_under_user_settings(tmp_path, monkeypatch) -> None:
    """CF-05: settings.json sobrepoe por chave; o que ele nao tem vem do default."""
    from core import config_manager

    cfg_dir = tmp_path / "cfg"
    cfg_dir.mkdir()
    (cfg_dir / "default_settings.json").write_text(
        json.dumps(
            {
                "user_preferences": {
                    "auto_scroll_to_end": False,
                    "filter_mode_default": "contains",
                },
                "import_settings": {"move_processed_after_import": True},
            }
        ),
        encoding="utf-8",
    )
    (cfg_dir / "settings.json").write_text(
        json.dumps({"user_preferences": {"auto_scroll_to_end": True}}),
        encoding="utf-8",
    )
    monkeypatch.setenv("SSA_CONFIG_DIR", str(cfg_dir))

    settings = config_manager.load_settings()

    assert settings["import_settings"] == {"move_processed_after_import": True}
    assert settings["user_preferences"] == {
        "auto_scroll_to_end": True,
        "filter_mode_default": "contains",
    }


def test_default_settings_file_matches_code_payload() -> None:
    """CF-05: o arquivo versionado e o payload de recriacao sao a mesma fonte."""
    from core.config_defaults import default_settings_payload

    data = json.loads(Path("config/default_settings.json").read_text(encoding="utf-8"))
    assert data == default_settings_payload()
