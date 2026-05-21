"""PAI API option defaults and normalization."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

PAI_API_SETTINGS_KEY = "pai_api"
PAI_API_ENABLED_KEY = "enabled"
PAI_API_SCRAP_ENABLED_KEY = "scrap_report_enabled"
PAI_API_SECTORS_KEY = "executor_sectors"
PAI_API_DATA_SCOPES_KEY = "data_scopes"
PAI_API_AUTO_REFRESH_ENABLED_KEY = "auto_refresh_enabled"
PAI_API_AUTO_REFRESH_INTERVAL_MINUTES_KEY = "auto_refresh_interval_minutes"
PAI_API_LIMIT_KEY = "limit"
PAI_API_NUMBER_OF_YEARS_KEY = "number_of_years"

PAI_API_ALLOWED_SECTORS = ("IEE3", "MEL4", "IEE1", "IEE4", "MEL3", "MEL1", "IEE2", "MEL2")
PAI_API_DEFAULT_SECTORS = PAI_API_ALLOWED_SECTORS
PAI_API_FOCUSED_SECTORS = ("IEE3", "MEL4", "MEL3")
PAI_API_DEFAULT_LIMIT = 200
PAI_API_DEFAULT_NUMBER_OF_YEARS = 4
PAI_API_DEFAULT_AUTO_REFRESH_INTERVAL_MINUTES = 10
PAI_API_MAX_AUTO_REFRESH_INTERVAL_MINUTES = 24 * 60
PAI_API_MAX_LIMIT = 1000
PAI_API_MAX_NUMBER_OF_YEARS = 10

PAI_API_DATA_SCOPE_LABELS = {
    "executadas": "Executadas",
    "consulta": "Consulta",
    "aprovacao": "Para aprovacao",
    "planejamento": "Para planejamento",
    "programacao": "Para programacao",
}
PAI_API_REST_DATA_SCOPES = ("consulta",)
PAI_API_PLANNED_SCRAPER_DATA_SCOPES = ("executadas", "aprovacao")
PAI_API_UNSUPPORTED_DATA_SCOPES = ("planejamento", "programacao")
PAI_API_ALLOWED_DATA_SCOPES = tuple(PAI_API_DATA_SCOPE_LABELS)
PAI_API_DEFAULT_DATA_SCOPES = PAI_API_REST_DATA_SCOPES


@dataclass(frozen=True)
class PaiApiGuiOptions:
    enabled: bool
    scrap_report_enabled: bool
    auto_refresh_enabled: bool
    auto_refresh_interval_minutes: int
    executor_sectors: tuple[str, ...]
    data_scopes: tuple[str, ...]
    limit: int
    number_of_years: int


def pai_api_options_error(options: PaiApiGuiOptions) -> str | None:
    if not options.enabled:
        return "API PAI desabilitada nas opcoes."
    if not options.scrap_report_enabled:
        return "Busca via scrap_report desabilitada nas opcoes."
    if not options.executor_sectors:
        return "Nenhum setor executor habilitado para API PAI."
    if not options.data_scopes:
        return "Nenhum tipo de dado habilitado para API PAI."
    planned = planned_scraper_pai_api_data_scopes(options.data_scopes)
    if planned:
        labels = ", ".join(pai_api_data_scope_label(value) for value in planned)
        return f"Tipo de dado ainda nao disponivel: {labels}. Use Consulta."
    unsupported = unsupported_pai_api_data_scopes(options.data_scopes)
    if unsupported:
        labels = ", ".join(pai_api_data_scope_label(value) for value in unsupported)
        return f"Tipo de dado ainda nao disponivel: {labels}. Use Consulta."
    return None


def default_pai_api_settings() -> dict[str, Any]:
    return {
        PAI_API_ENABLED_KEY: True,
        PAI_API_SCRAP_ENABLED_KEY: True,
        PAI_API_AUTO_REFRESH_ENABLED_KEY: False,
        PAI_API_AUTO_REFRESH_INTERVAL_MINUTES_KEY: (
            PAI_API_DEFAULT_AUTO_REFRESH_INTERVAL_MINUTES
        ),
        PAI_API_SECTORS_KEY: list(PAI_API_ALLOWED_SECTORS),
        PAI_API_DATA_SCOPES_KEY: list(PAI_API_DEFAULT_DATA_SCOPES),
        PAI_API_LIMIT_KEY: PAI_API_DEFAULT_LIMIT,
        PAI_API_NUMBER_OF_YEARS_KEY: PAI_API_DEFAULT_NUMBER_OF_YEARS,
    }


def update_pai_api_boolean_setting(
    preferences: dict[str, Any],
    key: str,
    enabled: bool,
) -> None:
    settings = _settings_dict(preferences)
    settings[key] = bool(enabled)


def update_pai_api_sector_setting(
    preferences: dict[str, Any],
    sector: str,
    enabled: bool,
) -> bool:
    settings = _settings_dict(preferences)
    options = normalize_pai_api_options(settings)
    return _update_ordered_setting(
        settings,
        PAI_API_SECTORS_KEY,
        current_values=options.executor_sectors,
        allowed_values=PAI_API_ALLOWED_SECTORS,
        raw_value=sector,
        enabled=enabled,
    )


def update_pai_api_data_scope_setting(
    preferences: dict[str, Any],
    scope: str,
    enabled: bool,
) -> bool:
    settings = _settings_dict(preferences)
    options = normalize_pai_api_options(settings)
    return _update_ordered_setting(
        settings,
        PAI_API_DATA_SCOPES_KEY,
        current_values=options.data_scopes,
        allowed_values=PAI_API_ALLOWED_DATA_SCOPES,
        raw_value=scope,
        enabled=enabled,
    )


def normalize_pai_api_options(raw_settings: Mapping[str, Any] | None) -> PaiApiGuiOptions:
    settings = dict(raw_settings or {})
    sectors = _normalize_ordered_values(
        settings.get(PAI_API_SECTORS_KEY),
        allowed=PAI_API_ALLOWED_SECTORS,
        missing_default=PAI_API_DEFAULT_SECTORS,
    )
    data_scopes = _normalize_ordered_values(
        settings.get(PAI_API_DATA_SCOPES_KEY),
        allowed=PAI_API_ALLOWED_DATA_SCOPES,
        missing_default=PAI_API_DEFAULT_DATA_SCOPES,
    )
    return PaiApiGuiOptions(
        enabled=bool(settings.get(PAI_API_ENABLED_KEY, True)),
        scrap_report_enabled=bool(settings.get(PAI_API_SCRAP_ENABLED_KEY, True)),
        auto_refresh_enabled=bool(
            settings.get(PAI_API_AUTO_REFRESH_ENABLED_KEY, False)
        ),
        auto_refresh_interval_minutes=_positive_int(
            settings.get(PAI_API_AUTO_REFRESH_INTERVAL_MINUTES_KEY),
            PAI_API_DEFAULT_AUTO_REFRESH_INTERVAL_MINUTES,
            max_value=PAI_API_MAX_AUTO_REFRESH_INTERVAL_MINUTES,
        ),
        executor_sectors=sectors,
        data_scopes=data_scopes,
        limit=_positive_int(
            settings.get(PAI_API_LIMIT_KEY),
            PAI_API_DEFAULT_LIMIT,
            max_value=PAI_API_MAX_LIMIT,
        ),
        number_of_years=_positive_int(
            settings.get(PAI_API_NUMBER_OF_YEARS_KEY),
            PAI_API_DEFAULT_NUMBER_OF_YEARS,
            max_value=PAI_API_MAX_NUMBER_OF_YEARS,
        ),
    )


def _normalize_ordered_values(
    raw_values: object,
    *,
    allowed: tuple[str, ...],
    missing_default: tuple[str, ...],
) -> tuple[str, ...]:
    allowed_by_key = {value.casefold(): value for value in allowed}
    if not isinstance(raw_values, (list, tuple)):
        return missing_default
    normalized: list[str] = []
    seen: set[str] = set()
    for raw_value in raw_values:
        key = str(raw_value).strip().casefold()
        if not key or key in seen or key not in allowed_by_key:
            continue
        seen.add(key)
        normalized.append(allowed_by_key[key])
    return tuple(normalized)


def _settings_dict(preferences: dict[str, Any]) -> dict[str, Any]:
    return preferences.setdefault("gui_settings", {}).setdefault(
        PAI_API_SETTINGS_KEY,
        {},
    )


def _allowed_by_key(allowed_values: tuple[str, ...]) -> dict[str, str]:
    return {str(value).casefold(): str(value) for value in allowed_values}


def _update_ordered_setting(
    settings: dict[str, Any],
    key: str,
    *,
    current_values: tuple[str, ...],
    allowed_values: tuple[str, ...],
    raw_value: str,
    enabled: bool,
) -> bool:
    allowed_by_key = _allowed_by_key(allowed_values)
    clean_key = str(raw_value or "").strip().casefold()
    canonical_value = allowed_by_key.get(clean_key)
    if canonical_value is None:
        return False
    values = list(current_values)
    value_keys = {value.casefold() for value in values}
    if enabled and canonical_value.casefold() not in value_keys:
        values.append(canonical_value)
    elif not enabled:
        values = [
            value for value in values if value.casefold() != canonical_value.casefold()
        ]
    settings[key] = list(
        _normalize_ordered_values(
            values,
            allowed=allowed_values,
            missing_default=(),
        )
    )
    return True


def pai_api_data_scope_label(scope: str) -> str:
    return PAI_API_DATA_SCOPE_LABELS.get(str(scope).casefold(), str(scope))


def planned_scraper_pai_api_data_scopes(scopes: tuple[str, ...]) -> tuple[str, ...]:
    planned = set(PAI_API_PLANNED_SCRAPER_DATA_SCOPES)
    return tuple(scope for scope in scopes if scope in planned)


def unsupported_pai_api_data_scopes(scopes: tuple[str, ...]) -> tuple[str, ...]:
    unsupported = set(PAI_API_UNSUPPORTED_DATA_SCOPES)
    return tuple(scope for scope in scopes if scope in unsupported)


def _positive_int(value: object, default: int, *, max_value: int | None = None) -> int:
    try:
        parsed = int(str(value))
    except (TypeError, ValueError):
        return default
    if parsed <= 0:
        return default
    if max_value is not None and parsed > max_value:
        return default
    return parsed
