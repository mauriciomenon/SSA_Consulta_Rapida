from __future__ import annotations

from core.pai_api_options import (
    PAI_API_ALLOWED_SECTORS,
    PAI_API_SECTORS_KEY,
    PAI_API_SETTINGS_KEY,
    normalize_pai_api_options,
    update_pai_api_sector_setting,
)


def test_pai_api_options_preserve_configured_sector_priority() -> None:
    options = normalize_pai_api_options(
        {
            PAI_API_SECTORS_KEY: ["mel3", "IEE3", "invalid", "MEL3"],
        }
    )

    assert options.executor_sectors == ("MEL3", "IEE3")


def test_pai_api_sector_update_persists_canonical_allowed_value() -> None:
    preferences = {
        "gui_settings": {PAI_API_SETTINGS_KEY: {PAI_API_SECTORS_KEY: ["MEL4"]}}
    }

    assert update_pai_api_sector_setting(preferences, "iee3", True) is True
    assert update_pai_api_sector_setting(preferences, "unknown", True) is False

    settings = preferences["gui_settings"][PAI_API_SETTINGS_KEY]
    assert settings[PAI_API_SECTORS_KEY] == ["MEL4", "IEE3"]
    assert "IEE3" in PAI_API_ALLOWED_SECTORS
