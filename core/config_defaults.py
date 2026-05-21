from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

from shared.table_display_defaults import DEFAULT_DISPLAY_MAPPINGS

# Column mappings source of truth lives in config/column_mappings.json.
_COLUMN_MAPPINGS_PATH = Path(__file__).resolve().parents[1] / "config" / "column_mappings.json"

_MINIMAL_COLUMN_MAPPINGS_FALLBACK: Dict[str, list] = {
    "numero_ssa": ["Nº SSA", "Numero SSA", "ssa_number"],
    "data_cadastro": ["Emitida Em", "Data Cadastro", "issue_datetime"],
    "descricao_ssa": ["Descrição da SSA", "Descricao", "description"],
    "setor_executor": ["Executor", "Setor Executor", "executor_sector"],
    "setor_emissor": ["Emissor", "Setor Emissor", "emitter_sector"],
    "atividade_especial": ["Atividade Especial", "Actividad Especial"],
}
_DEFAULT_COLUMN_MAPPINGS_CACHE: Dict[str, list] | None = None


def _copy_column_mappings(source: Dict[str, list]) -> Dict[str, list]:
    return {canonical: list(aliases) for canonical, aliases in source.items()}


def _load_default_column_mappings() -> Dict[str, list]:
    try:
        raw = json.loads(_COLUMN_MAPPINGS_PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return _copy_column_mappings(_MINIMAL_COLUMN_MAPPINGS_FALLBACK)
    if not isinstance(raw, dict) or not raw:
        return _copy_column_mappings(_MINIMAL_COLUMN_MAPPINGS_FALLBACK)
    cleaned: Dict[str, list] = {}
    for canonical, aliases in raw.items():
        if not isinstance(canonical, str) or not isinstance(aliases, list):
            continue
        valid_aliases = [alias for alias in aliases if isinstance(alias, str) and alias]
        if valid_aliases:
            cleaned[canonical] = valid_aliases
    return cleaned or _copy_column_mappings(_MINIMAL_COLUMN_MAPPINGS_FALLBACK)


def get_default_column_mappings() -> Dict[str, list]:
    global _DEFAULT_COLUMN_MAPPINGS_CACHE
    if _DEFAULT_COLUMN_MAPPINGS_CACHE is None:
        _DEFAULT_COLUMN_MAPPINGS_CACHE = _load_default_column_mappings()
    return _copy_column_mappings(_DEFAULT_COLUMN_MAPPINGS_CACHE)


def default_settings_payload() -> dict[str, Any]:
    return {
        "version": "1.0.0",
        "description": "Default settings for SSA Consulta Rapida",
        "display_settings": {
            "column_visibility": {},
            "column_widths": {
                "#": 4,
                "Nº SSA": 9,
                "Loc.": 10,
                "Emissor": 6,
                "Executor": 6,
            },
            "max_auto_scroll_pages": 3,
        },
        "user_preferences": {
            "auto_scroll_to_end": False,
            "filter_mode_default": "contains",
        },
        "default_filters": [],
        "import_settings": {
            "include_processadas_in_full_rescan": True,
            "processadas_subdir": "processadas",
            "ignore_nosurvivor_in_full_rescan": True,
            "nosurvivor_subdir": "nosurvivor",
            "move_processed_after_import": False,
            "route_zero_survivor_to_nosurvivor": True,
            "upsert_short_circuit_policy": "consulta_only",
        },
    }


def default_config_payload_for_filename(filename: str) -> dict[str, Any] | None:
    if filename == "default_settings.json":
        return default_settings_payload()
    if filename == "display_mappings.json":
        return DEFAULT_DISPLAY_MAPPINGS
    if filename == "column_mappings.json":
        return get_default_column_mappings()
    return None
