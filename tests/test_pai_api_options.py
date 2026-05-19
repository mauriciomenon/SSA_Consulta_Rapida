from __future__ import annotations

from core.pai_api_options import (
    PAI_API_ALLOWED_SECTORS,
    PAI_API_AUTO_REFRESH_ENABLED_KEY,
    PAI_API_AUTO_REFRESH_INTERVAL_MINUTES_KEY,
    PAI_API_DATA_SCOPES_KEY,
    PAI_API_SECTORS_KEY,
    PAI_API_SETTINGS_KEY,
    default_pai_api_settings,
    normalize_pai_api_options,
    pai_api_options_error,
    update_pai_api_data_scope_setting,
    update_pai_api_sector_setting,
)


def test_pai_api_options_canonicalize_and_filter_sector_order() -> None:
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


def test_pai_api_options_preserve_empty_sector_selection() -> None:
    options = normalize_pai_api_options({PAI_API_SECTORS_KEY: []})

    assert options.executor_sectors == ()


def test_pai_api_auto_refresh_defaults_are_explicit() -> None:
    settings = default_pai_api_settings()
    options = normalize_pai_api_options(settings)

    assert settings[PAI_API_AUTO_REFRESH_ENABLED_KEY] is False
    assert settings[PAI_API_AUTO_REFRESH_INTERVAL_MINUTES_KEY] == 10
    assert options.auto_refresh_enabled is False
    assert options.auto_refresh_interval_minutes == 10
    assert options.data_scopes == ("consulta",)


def test_pai_api_data_scope_update_persists_canonical_value() -> None:
    preferences = {
        "gui_settings": {PAI_API_SETTINGS_KEY: {PAI_API_DATA_SCOPES_KEY: ["consulta"]}}
    }

    assert update_pai_api_data_scope_setting(preferences, "EXECUTADAS", True) is True
    assert update_pai_api_data_scope_setting(preferences, "unknown", True) is False

    settings = preferences["gui_settings"][PAI_API_SETTINGS_KEY]
    assert settings[PAI_API_DATA_SCOPES_KEY] == ["consulta", "executadas"]


def test_pai_api_options_reject_scope_without_gui_backend() -> None:
    options = normalize_pai_api_options({PAI_API_DATA_SCOPES_KEY: ["executadas"]})

    assert pai_api_options_error(options) == (
        "Tipos de dado exigem backend scraper ainda nao habilitado "
        "neste fluxo: Executadas."
    )
