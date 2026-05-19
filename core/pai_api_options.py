"""PAI API option defaults and normalization."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

PAI_API_SETTINGS_KEY = "pai_api"
PAI_API_ENABLED_KEY = "enabled"
PAI_API_SCRAP_ENABLED_KEY = "scrap_report_enabled"
PAI_API_SECTORS_KEY = "executor_sectors"

PAI_API_ALLOWED_SECTORS = ("IEE3", "MEL4", "IEE1", "IEE4", "MEL3", "MEL1", "IEE2", "MEL2")
PAI_API_PRIORITY_SECTORS = PAI_API_ALLOWED_SECTORS
PAI_API_FOCUSED_SECTORS = ("IEE3", "MEL4", "MEL3")
PAI_API_DEFAULT_LIMIT = 200
PAI_API_DEFAULT_NUMBER_OF_YEARS = 4

PAI_API_DATA_SCOPE_LABELS = {
    "executadas": "Executadas",
    "consulta": "Consulta",
    "aprovacao": "Para aprovacao",
    "planejamento": "Para planejamento",
    "programacao": "Para programacao",
}
PAI_API_DEFAULT_DATA_SCOPES = tuple(PAI_API_DATA_SCOPE_LABELS)


@dataclass(frozen=True)
class PaiApiGuiOptions:
    enabled: bool
    scrap_report_enabled: bool
    executor_sectors: tuple[str, ...]
    limit: int
    number_of_years: int


def pai_api_options_error(options: PaiApiGuiOptions) -> str | None:
    if not options.enabled:
        return "API PAI desabilitada nas opcoes."
    if not options.scrap_report_enabled:
        return "Busca via scrap_report desabilitada nas opcoes."
    if not options.executor_sectors:
        return "Nenhum setor executor habilitado para API PAI."
    return None


def default_pai_api_settings() -> dict[str, Any]:
    return {
        PAI_API_ENABLED_KEY: True,
        PAI_API_SCRAP_ENABLED_KEY: True,
        PAI_API_SECTORS_KEY: list(PAI_API_ALLOWED_SECTORS),
        "limit": PAI_API_DEFAULT_LIMIT,
        "number_of_years": PAI_API_DEFAULT_NUMBER_OF_YEARS,
    }


def update_pai_api_boolean_setting(
    preferences: dict[str, Any],
    key: str,
    enabled: bool,
) -> None:
    settings = preferences.setdefault("gui_settings", {}).setdefault(
        PAI_API_SETTINGS_KEY,
        {},
    )
    settings[key] = bool(enabled)


def update_pai_api_sector_setting(
    preferences: dict[str, Any],
    sector: str,
    enabled: bool,
) -> bool:
    settings = preferences.setdefault("gui_settings", {}).setdefault(
        PAI_API_SETTINGS_KEY,
        {},
    )
    options = normalize_pai_api_options(settings)
    sectors = list(options.executor_sectors)
    clean_sector = str(sector or "").strip().upper()
    allowed_by_key: dict[str, str] = {
        str(value).casefold(): str(value) for value in PAI_API_ALLOWED_SECTORS
    }
    canonical_sector = allowed_by_key.get(clean_sector.casefold())
    if canonical_sector is None:
        return False
    sector_keys = {value.casefold() for value in sectors}
    if enabled and clean_sector.casefold() not in sector_keys:
        sectors.append(canonical_sector)
    elif not enabled:
        sectors = [value for value in sectors if value.casefold() != clean_sector.casefold()]
    settings[PAI_API_SECTORS_KEY] = sectors
    return True


def normalize_pai_api_options(raw_settings: Mapping[str, Any] | None) -> PaiApiGuiOptions:
    settings = dict(raw_settings or {})
    sectors = _normalize_ordered_values(
        settings.get(PAI_API_SECTORS_KEY),
        allowed=PAI_API_ALLOWED_SECTORS,
        missing_default=PAI_API_PRIORITY_SECTORS,
    )
    return PaiApiGuiOptions(
        enabled=bool(settings.get(PAI_API_ENABLED_KEY, True)),
        scrap_report_enabled=bool(settings.get(PAI_API_SCRAP_ENABLED_KEY, True)),
        executor_sectors=sectors,
        limit=_positive_int(settings.get("limit"), PAI_API_DEFAULT_LIMIT),
        number_of_years=_positive_int(
            settings.get("number_of_years"),
            PAI_API_DEFAULT_NUMBER_OF_YEARS,
        ),
    )


def _normalize_ordered_values(
    raw_values: object,
    *,
    allowed: tuple[str, ...],
    missing_default: tuple[str, ...],
) -> tuple[str, ...]:
    allowed_by_key = {value.casefold(): value for value in allowed}
    if not isinstance(raw_values, (list, tuple, set)):
        return missing_default
    normalized: list[str] = []
    seen: set[str] = set()
    for raw_value in raw_values:
        key = str(raw_value).strip().casefold()
        if not key or key in seen or key not in allowed_by_key:
            continue
        seen.add(key)
        normalized.append(allowed_by_key[key])
    return tuple(normalized) or missing_default


def _positive_int(value: object, default: int) -> int:
    try:
        parsed = int(str(value))
    except (TypeError, ValueError):
        return default
    return parsed if parsed > 0 else default
