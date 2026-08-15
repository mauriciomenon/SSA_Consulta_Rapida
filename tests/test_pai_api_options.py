from __future__ import annotations

import pytest

from core.pai_api_options import (
    PAI_API_ALLOWED_SECTORS,
    PAI_API_AUTO_REFRESH_ENABLED_KEY,
    PAI_API_AUTO_REFRESH_INTERVAL_MINUTES_KEY,
    PAI_API_BASE_URL_KEY,
    PAI_API_DATA_SCOPES_KEY,
    PAI_API_ENABLED_KEY,
    PAI_API_ENABLED_DATA_SCOPES,
    PAI_API_EXTRA_SECTORS_KEY,
    PAI_API_LIMIT_KEY,
    PAI_API_MAX_AUTO_REFRESH_INTERVAL_MINUTES,
    PAI_API_MAX_LIMIT,
    PAI_API_MAX_NUMBER_OF_YEARS,
    PAI_API_NUMBER_OF_YEARS_KEY,
    PAI_API_DEFAULT_SECRET_SERVICE_ENV,
    PAI_API_SECRET_SERVICE_KEY,
    PAI_API_SECURE_REQUIRED_KEY,
    PAI_API_SCRAP_ENABLED_KEY,
    PAI_API_SECTORS_KEY,
    PAI_API_SETTINGS_KEY,
    PAI_API_USERNAME_KEY,
    default_pai_api_settings,
    normalize_pai_api_options,
    pai_api_options_error,
    update_pai_api_data_scope_setting,
    update_pai_api_sector_setting,
)


def test_pai_api_default_secret_service_can_use_environment_override(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(PAI_API_DEFAULT_SECRET_SERVICE_ENV, "custom.service")

    assert default_pai_api_settings()[PAI_API_SECRET_SERVICE_KEY] == "custom.service"  # pragma: allowlist secret
    assert normalize_pai_api_options({}).secret_service == "custom.service"  # pragma: allowlist secret


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


def test_pai_api_options_include_extra_executor_sectors_for_sam_api_only() -> None:
    options = normalize_pai_api_options(
        {
            PAI_API_SECTORS_KEY: ["IEE3"],
            PAI_API_EXTRA_SECTORS_KEY: " ieq1 , MEL5 , ieq1 ",
        }
    )

    assert options.executor_sectors == ("IEE3",)
    assert options.executor_sectors_extra == ("IEQ1", "MEL5")
    assert options.all_executor_sectors == ("IEE3", "IEQ1", "MEL5")


def test_pai_api_auto_refresh_defaults_are_explicit() -> None:
    settings = default_pai_api_settings()
    options = normalize_pai_api_options(settings)

    assert settings[PAI_API_ENABLED_KEY] is False
    assert options.enabled is False
    assert settings[PAI_API_AUTO_REFRESH_ENABLED_KEY] is False
    assert (
        settings[PAI_API_AUTO_REFRESH_INTERVAL_MINUTES_KEY]
        == PAI_API_MAX_AUTO_REFRESH_INTERVAL_MINUTES
    )
    assert options.auto_refresh_enabled is False
    assert (
        options.auto_refresh_interval_minutes
        == PAI_API_MAX_AUTO_REFRESH_INTERVAL_MINUTES
    )
    assert options.data_scopes == ("consulta",)
    assert options.username == ""
    assert options.secret_service == "scrap_report.sam"  # pragma: allowlist secret
    assert options.secure_required is True


def test_pai_api_explicit_enabled_preference_is_preserved() -> None:
    assert normalize_pai_api_options({PAI_API_ENABLED_KEY: True}).enabled is True
    assert normalize_pai_api_options({PAI_API_ENABLED_KEY: False}).enabled is False


def test_pai_api_auth_options_trim_username_and_secret_service() -> None:
    options = normalize_pai_api_options(
        {
            PAI_API_USERNAME_KEY: " sam.user ",
            PAI_API_SECRET_SERVICE_KEY: " custom.sam ",
            PAI_API_SECURE_REQUIRED_KEY: False,
        }
    )

    assert options.username == "sam.user"
    assert options.secret_service == "custom.sam"  # pragma: allowlist secret
    assert options.secure_required is False


def test_pai_api_base_url_defaults_and_trims() -> None:
    default_options = normalize_pai_api_options({})
    custom_options = normalize_pai_api_options(
        {
            PAI_API_BASE_URL_KEY: " https://sam.internal/rest/SSA_API ",
        }
    )

    assert default_pai_api_settings()[PAI_API_BASE_URL_KEY].startswith("https://")
    assert default_options.base_url == default_pai_api_settings()[PAI_API_BASE_URL_KEY]
    assert custom_options.base_url == "https://sam.internal/rest/SSA_API"


def test_pai_api_data_scope_update_persists_canonical_value() -> None:
    preferences = {
        "gui_settings": {PAI_API_SETTINGS_KEY: {PAI_API_DATA_SCOPES_KEY: ["consulta"]}}
    }

    assert update_pai_api_data_scope_setting(preferences, "EXECUTADAS", True) is True
    assert update_pai_api_data_scope_setting(preferences, "unknown", True) is False

    settings = preferences["gui_settings"][PAI_API_SETTINGS_KEY]
    assert settings[PAI_API_DATA_SCOPES_KEY] == ["consulta", "executadas"]


def test_pai_api_data_scope_update_accepts_explicit_aprovacao_scopes() -> None:
    preferences = {
        "gui_settings": {PAI_API_SETTINGS_KEY: {PAI_API_DATA_SCOPES_KEY: ["consulta"]}}
    }

    assert update_pai_api_data_scope_setting(
        preferences,
        "APROVACAO_EMISSAO",
        True,
    ) is True
    assert update_pai_api_data_scope_setting(
        preferences,
        "aprovacao_cancelamento",
        True,
    ) is True

    settings = preferences["gui_settings"][PAI_API_SETTINGS_KEY]
    assert settings[PAI_API_DATA_SCOPES_KEY] == [
        "consulta",
        "aprovacao_emissao",
        "aprovacao_cancelamento",
    ]


def test_pai_api_options_reject_scope_without_gui_backend() -> None:
    options = normalize_pai_api_options(
        {
            PAI_API_ENABLED_KEY: True,
            PAI_API_DATA_SCOPES_KEY: ["executadas"],
        }
    )

    assert (
        pai_api_options_error(options)
        == "Usuario SAM obrigatorio para xpath/scrap_report."
    )


def test_pai_api_options_allow_consulta_and_executadas_with_username() -> None:
    options = normalize_pai_api_options(
        {
            PAI_API_ENABLED_KEY: True,
            PAI_API_DATA_SCOPES_KEY: ["consulta", "executadas"],
            PAI_API_USERNAME_KEY: "sam.user",
        }
    )

    assert pai_api_options_error(options) is None
    assert PAI_API_ENABLED_DATA_SCOPES == (
        "consulta",
        "executadas",
        "aprovacao_emissao",
        "aprovacao_cancelamento",
    )


def test_pai_api_options_allow_rest_consulta_when_scrap_report_disabled() -> None:
    options = normalize_pai_api_options(
        {
            PAI_API_ENABLED_KEY: True,
            PAI_API_SCRAP_ENABLED_KEY: False,
            PAI_API_DATA_SCOPES_KEY: ["consulta"],
        }
    )

    assert pai_api_options_error(options) is None


def test_pai_api_options_reject_scraper_scope_when_scrap_report_disabled() -> None:
    options = normalize_pai_api_options(
        {
            PAI_API_ENABLED_KEY: True,
            PAI_API_SCRAP_ENABLED_KEY: False,
            PAI_API_DATA_SCOPES_KEY: ["executadas"],
            PAI_API_USERNAME_KEY: "sam.user",
        }
    )

    assert (
        pai_api_options_error(options)
        == "Acesso via xpath/scrap_report desabilitado nas opcoes."
    )


def test_pai_api_options_keep_aprovacao_planned() -> None:
    options = normalize_pai_api_options(
        {
            PAI_API_ENABLED_KEY: True,
            PAI_API_DATA_SCOPES_KEY: ["aprovacao"],
            PAI_API_USERNAME_KEY: "sam.user",
        }
    )

    assert (
        pai_api_options_error(options)
        == "Tipo de dado ainda nao disponivel: Para aprovacao. Use Consulta."
    )


@pytest.mark.parametrize(
    ("scopes", "expected_message"),
    [
        (
            ["consulta", "aprovacao"],
            "Tipo de dado ainda nao disponivel: Para aprovacao. Use Consulta.",
        ),
        (
            ["consulta", "planejamento"],
            "Tipo de dado nao suportado: Para planejamento. Use Consulta.",
        ),
        (
            ["executadas", "programacao"],
            "Tipo de dado nao suportado: Para programacao. Use Consulta.",
        ),
    ],
)
def test_pai_api_options_reject_mixed_unavailable_scopes(
    scopes: list[str],
    expected_message: str,
) -> None:
    options = normalize_pai_api_options(
        {
            PAI_API_ENABLED_KEY: True,
            PAI_API_DATA_SCOPES_KEY: scopes,
            PAI_API_USERNAME_KEY: "sam.user",
        }
    )

    assert pai_api_options_error(options) == expected_message


def test_pai_api_options_allow_explicit_aprovacao_with_username() -> None:
    options = normalize_pai_api_options(
        {
            PAI_API_ENABLED_KEY: True,
            PAI_API_DATA_SCOPES_KEY: [
                "aprovacao_emissao",
                "aprovacao_cancelamento",
            ],
            PAI_API_USERNAME_KEY: "sam.user",
        }
    )

    assert pai_api_options_error(options) is None


def test_pai_api_options_clamp_excessive_numeric_values() -> None:
    options = normalize_pai_api_options(
        {
            PAI_API_AUTO_REFRESH_INTERVAL_MINUTES_KEY: 999999,
            PAI_API_LIMIT_KEY: 999999,
            PAI_API_NUMBER_OF_YEARS_KEY: 999999,
        }
    )

    assert options.auto_refresh_interval_minutes == PAI_API_MAX_AUTO_REFRESH_INTERVAL_MINUTES
    assert options.limit == PAI_API_MAX_LIMIT
    assert options.number_of_years == PAI_API_MAX_NUMBER_OF_YEARS


def test_pai_api_options_preserve_valid_numeric_values_within_range() -> None:
    options = normalize_pai_api_options(
        {
            PAI_API_AUTO_REFRESH_INTERVAL_MINUTES_KEY: 60,
            PAI_API_LIMIT_KEY: 500,
            PAI_API_NUMBER_OF_YEARS_KEY: 6,
        }
    )

    assert options.auto_refresh_interval_minutes == 60
    assert options.limit == 500
    assert options.number_of_years == 6


def test_pai_api_options_preserve_numeric_values_at_max() -> None:
    options = normalize_pai_api_options(
        {
            PAI_API_AUTO_REFRESH_INTERVAL_MINUTES_KEY: (
                PAI_API_MAX_AUTO_REFRESH_INTERVAL_MINUTES
            ),
            PAI_API_LIMIT_KEY: PAI_API_MAX_LIMIT,
            PAI_API_NUMBER_OF_YEARS_KEY: PAI_API_MAX_NUMBER_OF_YEARS,
        }
    )

    assert options.auto_refresh_interval_minutes == PAI_API_MAX_AUTO_REFRESH_INTERVAL_MINUTES
    assert options.limit == PAI_API_MAX_LIMIT
    assert options.number_of_years == PAI_API_MAX_NUMBER_OF_YEARS


def test_pai_api_options_clamp_numeric_values_above_max() -> None:
    options = normalize_pai_api_options(
        {
            PAI_API_AUTO_REFRESH_INTERVAL_MINUTES_KEY: (
                PAI_API_MAX_AUTO_REFRESH_INTERVAL_MINUTES + 1
            ),
            PAI_API_LIMIT_KEY: PAI_API_MAX_LIMIT + 1,
            PAI_API_NUMBER_OF_YEARS_KEY: PAI_API_MAX_NUMBER_OF_YEARS + 1,
        }
    )

    assert options.auto_refresh_interval_minutes == PAI_API_MAX_AUTO_REFRESH_INTERVAL_MINUTES
    assert options.limit == PAI_API_MAX_LIMIT
    assert options.number_of_years == PAI_API_MAX_NUMBER_OF_YEARS
