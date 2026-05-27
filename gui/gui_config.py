"""Centralized GUI configuration loader with defensive merge rules."""

from __future__ import annotations

import copy
import json
import os
import re
import sys
from typing import Any, Dict, Iterable, List

from core import config_manager as core_config_manager
from core.config_manager import atomic_write_json_file
from core.pai_api_options import default_pai_api_settings
from utils.robust_logging import get_robust_logger

logger = get_robust_logger().get_logger(__name__, "gui")

# gui/gui_config.py -> gui -> project root
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


def _resolve_gui_main_preferences_path() -> str:
    """Resolve GUI preferences path strictly via centralized config hierarchy."""
    return core_config_manager._resolve_config_path(  # noqa: SLF001
        os.path.join(core_config_manager.CONFIG_DIR, "gui_main_preferences.json")
    )


CONFIG_PATH = _resolve_gui_main_preferences_path()
GUI_MAIN_PREFERENCES_TEMPLATE_PATH = os.path.join(
    project_root,
    core_config_manager.CONFIG_DIR,
    "gui_main_preferences.json.example",
)


def get_gui_main_preferences_path() -> str:
    """Return current GUI preferences path resolved from active config hierarchy."""
    return _resolve_gui_main_preferences_path()


def get_gui_main_preferences_template_path() -> str:
    """Return versioned reference file path for GUI preferences."""
    return GUI_MAIN_PREFERENCES_TEMPLATE_PATH


# Contract: these columns must always be available in GUI defaults and mappings.
REQUIRED_DISPLAY_COLUMNS: List[str] = [
    "numero_ssa",
    "localizacao_codigo",
    "situacao",
    "setor_emissor",
    "setor_executor",
    "derivada_de",
    "data_cadastro",
    "grau_prioridade_emissao",
    "solicitante",
    "grau_prioridade_planejamento",
    "semana_programada",
    "total_de_reprogramacoes",
    "execucao_parcial",
    "descricao_execucao",
    "semana_executada",
    "responsavel_execucao",
]

DEFAULT_COLUMN_DISPLAY_NAMES: Dict[str, str] = {
    "numero_ssa": "Numero SSA",
    "setor_executor": "Set. Exec.",
    "situacao": "Sit.",
    "descricao_ssa": "Descricao da SSA",
    "data_cadastro": "Cadastro",
    "semana_cadastro": "Sem. Cad.",
    "localizacao_codigo": "Loc.",
    "grau_prioridade": "Prio.",
    "grau_prioridade_emissao": "Prio. Emissao",
    "grau_prioridade_planejamento": "Prio. Planej.",
    "setor_emissor": "Set. Emis.",
    "solicitante": "Solicitante",
    "derivada_de": "Derivada de",
    "semana_programada": "Sem. Prog.",
    "descricao_execucao": "Descricao Execucao",
    "descricao_localizacao": "Desc. Localizacao",
    "equipamento": "Equipamento",
    "origem": "Origem",
    "servico_origem": "Serv. Origem",
    "execucao_simples": "Exec. Simples",
    "responsavel_programacao": "Resp. Prog.",
    "responsavel_execucao": "Resp. Exec.",
    "arquivo_origem": "Arquivo Origem",
    "data_arquivo_origem": "Data do Arquivo de Origem",
    "total_de_reprogramacoes": "Tot. Reprog.",
    "execucao_parcial": "Exec. Parc.",
    "situacao_da_parcial": "Situacao da Parcial",
    "semana_executada": "Sem. Exec.",
}

COLUMN_HEADER_LABEL_VARIANTS: Dict[str, Dict[str, str]] = {
    "numero_ssa": {
        "short": "SSA",
        "medium": "Numero SSA",
        "long": "Numero da SSA",
    },
    "setor_executor": {
        "short": "Exec.",
        "medium": "Set. Exec.",
        "long": "Set. Exec.",
    },
    "situacao": {
        "short": "Sit.",
        "medium": "Situacao",
        "long": "Situacao",
    },
    "situacao_da_parcial": {
        "short": "Sit. Parc.",
        "medium": "Situacao Parcial",
        "long": "Situacao da Parcial",
    },
    "descricao_ssa": {
        "short": "Desc. SSA",
        "medium": "Descricao SSA",
        "long": "Descricao da SSA",
    },
    "data_cadastro": {
        "short": "Cadastro",
        "medium": "Data Cadastro",
        "long": "Data de Cadastro",
    },
    "semana_cadastro": {
        "short": "Sem. Cad.",
        "medium": "Semana Cad.",
        "long": "Semana de Cadastro",
    },
    "localizacao_codigo": {
        "short": "Loc.",
        "medium": "Localizacao",
        "long": "Localizacao",
    },
    "grau_prioridade": {
        "short": "Prio.",
        "medium": "Prioridade",
        "long": "Prioridade",
    },
    "grau_prioridade_emissao": {
        "short": "Prio. Emis.",
        "medium": "Prio. Emissao",
        "long": "Prio. Emissao",
    },
    "grau_prioridade_planejamento": {
        "short": "Prio. Planej.",
        "medium": "Prio. Planej.",
        "long": "Prio. Planej.",
    },
    "setor_emissor": {
        "short": "Emis.",
        "medium": "Set. Emis.",
        "long": "Set. Emis.",
    },
    "solicitante": {
        "short": "Solicit.",
        "medium": "Solicitante",
        "long": "Solicitante",
    },
    "derivada_de": {
        "short": "Deriv.",
        "medium": "Derivada de",
        "long": "Derivada de",
    },
    "semana_programada": {
        "short": "Sem. Prog.",
        "medium": "Semana Prog.",
        "long": "Semana Programada",
    },
    "descricao_execucao": {
        "short": "Desc. Exec.",
        "medium": "Descricao Execucao",
        "long": "Descricao da Execucao",
    },
    "descricao_localizacao": {
        "short": "Desc. Loc.",
        "medium": "Desc. Localizacao",
        "long": "Descricao da Localizacao",
    },
    "equipamento": {
        "short": "Equip.",
        "medium": "Equipamento",
        "long": "Equipamento",
    },
    "origem": {
        "short": "Origem",
        "medium": "Origem",
        "long": "Origem",
    },
    "servico_origem": {
        "short": "Serv. Origem",
        "medium": "Servico Origem",
        "long": "Servico de Origem",
    },
    "execucao_simples": {
        "short": "Exec. Simp.",
        "medium": "Exec. Simples",
        "long": "Execucao Simples",
    },
    "responsavel_programacao": {
        "short": "Resp. Prog.",
        "medium": "Resp. Program.",
        "long": "Responsavel Programacao",
    },
    "responsavel_execucao": {
        "short": "Resp. Exec.",
        "medium": "Resp. Execucao",
        "long": "Responsavel Execucao",
    },
    "arquivo_origem": {
        "short": "Arq. Origem",
        "medium": "Arquivo Origem",
        "long": "Arquivo de Origem",
    },
    "data_arquivo_origem": {
        "short": "Data Arq.",
        "medium": "Data Arq. Origem",
        "long": "Data do Arquivo de Origem",
    },
    "total_de_reprogramacoes": {
        "short": "Tot. Reprog.",
        "medium": "Total Reprog.",
        "long": "Total de Reprogramacoes",
    },
    "execucao_parcial": {
        "short": "Exec. Parc.",
        "medium": "Exec. Parcial",
        "long": "Execucao Parcial",
    },
    "semana_executada": {
        "short": "Sem. Exec.",
        "medium": "Semana Exec.",
        "long": "Semana Executada",
    },
}

DEFAULT_COLUMN_WIDTHS_WINDOWS: Dict[str, int] = {
    "#": 24,
    "numero_ssa": 93,
    "localizacao_codigo": 86,
    "setor_executor": 80,
    "situacao": 51,
    "descricao_ssa": 340,
    "data_cadastro": 84,
    "setor_emissor": 72,
    "derivada_de": 80,
    "semana_programada": 92,
    "descricao_execucao": 330,
    "semana_cadastro": 92,
    "grau_prioridade": 95,
    "grau_prioridade_emissao": 120,
    "grau_prioridade_planejamento": 128,
    "solicitante": 150,
    "data_arquivo_origem": 188,
    "total_de_reprogramacoes": 130,
    "execucao_parcial": 78,
    "semana_executada": 92,
    "responsavel_execucao": 150,
}

DEFAULT_COLUMN_WIDTHS_DARWIN: Dict[str, int] = {
    **DEFAULT_COLUMN_WIDTHS_WINDOWS,
    "descricao_ssa": 340,
    "semana_programada": 72,
    "descricao_execucao": 330,
    "semana_cadastro": 60,
    "grau_prioridade_emissao": 96,
    "grau_prioridade_planejamento": 98,
    "solicitante": 150,
    "total_de_reprogramacoes": 82,
    "execucao_parcial": 78,
    "semana_executada": 60,
}

DEFAULT_COLUMN_WIDTHS_LINUX: Dict[str, int] = {
    "#": 24,
    "numero_ssa": 93,
    "localizacao_codigo": 86,
    "setor_executor": 65,
    "situacao": 51,
    "descricao_ssa": 298,
    "data_cadastro": 84,
    "setor_emissor": 58,
    "derivada_de": 76,
    "semana_programada": 88,
    "descricao_execucao": 282,
    "semana_cadastro": 74,
    "grau_prioridade": 95,
    "grau_prioridade_emissao": 122,
    "grau_prioridade_planejamento": 122,
    "solicitante": 123,
    "data_arquivo_origem": 188,
    "total_de_reprogramacoes": 130,
    "execucao_parcial": 130,
    "semana_executada": 96,
    "responsavel_execucao": 150,
}

DEFAULT_COLUMN_WIDTHS_BY_PLATFORM: Dict[str, Dict[str, int]] = {
    "darwin": copy.deepcopy(DEFAULT_COLUMN_WIDTHS_DARWIN),
    "win32": copy.deepcopy(DEFAULT_COLUMN_WIDTHS_WINDOWS),
    "linux": copy.deepcopy(DEFAULT_COLUMN_WIDTHS_LINUX),
}


def _normalize_platform_key(platform_name: str | None = None) -> str:
    current = str(platform_name or sys.platform).strip().lower()
    if current.startswith("win"):
        return "win32"
    if current == "darwin":
        return "darwin"
    return "linux"


def _sanitize_width_map(raw_widths: Any) -> Dict[str, int]:
    sanitized: Dict[str, int] = {}
    if not isinstance(raw_widths, dict):
        return sanitized
    for key, value in raw_widths.items():
        if not isinstance(key, str):
            continue
        if isinstance(value, (int, float)) and value > 0:
            sanitized[key.strip()] = min(int(value), 1200)
    return sanitized


def _resolve_platform_column_widths(
    platform_widths: Dict[str, Dict[str, int]] | None = None,
    fallback_widths: Dict[str, int] | None = None,
    *,
    platform_name: str | None = None,
) -> Dict[str, int]:
    platform_key = _normalize_platform_key(platform_name)
    source_platforms = (
        platform_widths
        if isinstance(platform_widths, dict)
        else DEFAULT_COLUMN_WIDTHS_BY_PLATFORM
    )
    base_widths = copy.deepcopy(
        source_platforms.get(platform_key, DEFAULT_COLUMN_WIDTHS_BY_PLATFORM["linux"])
    )
    if fallback_widths:
        for key, value in fallback_widths.items():
            if isinstance(key, str) and isinstance(value, int):
                base_widths[key] = value
    return base_widths


DEFAULT_COLUMN_WIDTHS: Dict[str, int] = _resolve_platform_column_widths()

DEFAULT_GUI_SETTINGS: Dict[str, Any] = {
    "page_size": 50,
    "auto_load": False,
    "debounce_delay": 800,
    "default_filter_mode": "contains",
    "show_progress_bar": True,
    "enable_column_sorting": True,
    "show_details_panel": True,
    "enable_double_click_details": True,
    "table_cell_alignment": "right",
    "theme": "classico",
    "filter_cache_size": 50,
    "cache_enabled": True,
    "cache_auto_clear": False,
    "theme_default": None,
    "pai_api": default_pai_api_settings(),
}

DEFAULT_GUI_MAIN_PREFERENCES: Dict[str, Any] = {
    "display_columns": [
        "numero_ssa",
        "localizacao_codigo",
        "situacao",
        "setor_emissor",
        "setor_executor",
        "derivada_de",
        "data_cadastro",
        "semana_cadastro",
        "descricao_ssa",
        "grau_prioridade_emissao",
        "solicitante",
        "grau_prioridade_planejamento",
        "semana_programada",
        "total_de_reprogramacoes",
        "execucao_parcial",
        "descricao_execucao",
        "semana_executada",
        "responsavel_execucao",
    ],
    "hidden_columns": [
        "descricao_localizacao",
        "equipamento",
        "origem",
        "servico_origem",
        "execucao_simples",
        "arquivo_origem",
        "responsavel_programacao",
    ],
    "column_display_names": copy.deepcopy(DEFAULT_COLUMN_DISPLAY_NAMES),
    "column_widths": copy.deepcopy(DEFAULT_COLUMN_WIDTHS_WINDOWS),
    "column_widths_by_platform": copy.deepcopy(DEFAULT_COLUMN_WIDTHS_BY_PLATFORM),
    "gui_settings": copy.deepcopy(DEFAULT_GUI_SETTINGS),
    "version": "1.0.0",
    "created_for": "GUI Main (main.py --gui)",
    "description": (
        "Configuracoes especificas para a GUI principal do sistema "
        "SSA_Consulta_Rapida, isolada do CLI e da GUI PoC"
    ),
}
DEFAULT_GUI_MAIN_PREFERENCES["display_mappings"] = copy.deepcopy(
    DEFAULT_GUI_MAIN_PREFERENCES["column_display_names"]
)
DEFAULT_GUI_MAIN_PREFERENCES["required_display_columns"] = list(
    REQUIRED_DISPLAY_COLUMNS
)
HARD_DEFAULT_GUI_MAIN_PREFERENCES: Dict[str, Any] = copy.deepcopy(
    DEFAULT_GUI_MAIN_PREFERENCES
)


def _hard_default_preferences_copy() -> Dict[str, Any]:
    defaults = copy.deepcopy(HARD_DEFAULT_GUI_MAIN_PREFERENCES)
    defaults["column_widths"] = _resolve_platform_column_widths(
        defaults.get("column_widths_by_platform"),
        None,
    )
    defaults["display_mappings"] = copy.deepcopy(defaults["column_display_names"])
    defaults["required_display_columns"] = list(REQUIRED_DISPLAY_COLUMNS)
    return defaults


# Columns kept in DB for compatibility only; do not offer in interactive GUI selectors.
COMPATIBILITY_NULL_UI_COLUMNS = {
    "registros_espera",
    "num_reprobaciones",
    "situacao_espera",
    "numero_desvios",
    "ate",
    "justificativa",
    "parciais",
    "situacao_da_parcial",
}

_MERGE_KEYS = {
    "display_columns",
    "hidden_columns",
    "column_display_names",
    "column_widths",
    "column_widths_by_platform",
    "gui_settings",
}
_LEGACY_INVALID_COLUMN_KEYS = {
    "Número da SSA",
    "Numero da SSA",
    "No SSA",
    "Data Cadastro",
}
_MANAGED_LEGACY_COLUMN_LABELS = {
    "setor_executor": "Exec.",
    "setor_emissor": "Emis.",
    "semana_programada": "Sem. Prog.",
    "responsavel_execucao": "Resp. Exec.",
    "total_de_reprogramacoes": "Total Reprog.",
    "execucao_parcial": "Exec. Parcial",
    "semana_executada": "Sem. Exec.",
}
_MANAGED_LEGACY_WIDTH_KEYS = {
    "descricao_ssa",
    "semana_programada",
    "descricao_execucao",
    "grau_prioridade_emissao",
    "grau_prioridade_planejamento",
    "solicitante",
    "total_de_reprogramacoes",
    "execucao_parcial",
    "semana_executada",
    "responsavel_execucao",
}
_VALID_TABLE_CELL_ALIGNMENTS = {"left", "center", "right"}


def _unique_str_list(values: Iterable[Any]) -> List[str]:
    result: List[str] = []
    seen = set()
    for value in values:
        if not isinstance(value, str):
            continue
        cleaned = value.strip()
        if not cleaned or cleaned in seen:
            continue
        seen.add(cleaned)
        result.append(cleaned)
    return result


def _build_fallback_label(column_name: str) -> str:
    return column_name.replace("_", " ").strip().title()


def _migrate_managed_legacy_column_labels(
    loaded_names: Dict[str, Any] | None,
) -> Dict[str, str]:
    migrated: Dict[str, str] = {}
    if not isinstance(loaded_names, dict):
        return migrated
    for key, value in loaded_names.items():
        if not isinstance(key, str) or not isinstance(value, str):
            continue
        key_clean = key.strip()
        value_clean = value.strip()
        if not key_clean or not value_clean:
            continue
        if key_clean in _MANAGED_LEGACY_COLUMN_LABELS:
            legacy_value = _MANAGED_LEGACY_COLUMN_LABELS[key_clean]
            if value_clean == legacy_value:
                migrated[key_clean] = DEFAULT_COLUMN_DISPLAY_NAMES[key_clean]
                continue
        migrated[key_clean] = value_clean
    return migrated


def _migrate_managed_legacy_widths(
    loaded_widths: Dict[str, Any] | None,
    target_widths: Dict[str, int],
) -> Dict[str, int]:
    migrated = _sanitize_width_map(loaded_widths)
    previous_defaults = HARD_DEFAULT_GUI_MAIN_PREFERENCES["column_widths"]
    previous_platform_defaults = HARD_DEFAULT_GUI_MAIN_PREFERENCES[
        "column_widths_by_platform"
    ]
    for key in _MANAGED_LEGACY_WIDTH_KEYS:
        if key not in migrated:
            continue
        previous_default_candidates = {
            previous_defaults.get(key),
            *(
                width_map.get(key)
                for width_map in previous_platform_defaults.values()
                if isinstance(width_map, dict)
            ),
        }
        previous_default_candidates.discard(None)
        if not previous_default_candidates:
            continue
        if migrated[key] in previous_default_candidates:
            target_width = target_widths.get(key)
            if target_width is None:
                continue
            migrated[key] = target_width
    return migrated


def _migrate_managed_legacy_platform_widths(
    loaded_platform_widths: Dict[str, Any] | None,
) -> Dict[str, Dict[str, int]]:
    migrated: Dict[str, Dict[str, int]] = {}
    if not isinstance(loaded_platform_widths, dict):
        return migrated
    for platform_name, width_map in loaded_platform_widths.items():
        if not isinstance(platform_name, str):
            continue
        platform_key = _normalize_platform_key(platform_name)
        platform_reference_widths = DEFAULT_COLUMN_WIDTHS_BY_PLATFORM.get(
            platform_key,
            DEFAULT_COLUMN_WIDTHS_BY_PLATFORM["linux"],
        )
        migrated[platform_key] = _migrate_managed_legacy_widths(
            width_map,
            platform_reference_widths,
        )
    return migrated


def _merge_preferences(loaded_config: Dict[str, Any]) -> Dict[str, Any]:
    merged = copy.deepcopy(DEFAULT_GUI_MAIN_PREFERENCES)

    # Preserve unknown top-level keys to avoid breaking custom features.
    for key, value in loaded_config.items():
        if key in _MERGE_KEYS:
            continue
        merged[key] = copy.deepcopy(value)

    loaded_hidden = loaded_config.get("hidden_columns")
    explicit_hidden_columns = set()
    if isinstance(loaded_hidden, list):
        explicit_hidden_columns = set(_unique_str_list(loaded_hidden))

    loaded_display = loaded_config.get("display_columns")
    if isinstance(loaded_display, list):
        display_columns = _unique_str_list(loaded_display)
    else:
        display_columns = list(DEFAULT_GUI_MAIN_PREFERENCES["display_columns"])
    if not display_columns:
        display_columns = list(DEFAULT_GUI_MAIN_PREFERENCES["display_columns"])
    for required in REQUIRED_DISPLAY_COLUMNS:
        if required in explicit_hidden_columns:
            continue
        if required not in display_columns:
            display_columns.append(required)
    merged["display_columns"] = display_columns

    if isinstance(loaded_hidden, list):
        hidden_columns = _unique_str_list(loaded_hidden)
    else:
        hidden_columns = list(DEFAULT_GUI_MAIN_PREFERENCES["hidden_columns"])
    hidden_columns = [
        column for column in hidden_columns if column not in display_columns
    ]
    merged["hidden_columns"] = hidden_columns

    names = copy.deepcopy(DEFAULT_COLUMN_DISPLAY_NAMES)
    allowed_name_keys = set(DEFAULT_COLUMN_DISPLAY_NAMES.keys())
    allowed_name_keys.update(display_columns)
    allowed_name_keys.update(hidden_columns)
    allowed_name_keys.update(REQUIRED_DISPLAY_COLUMNS)
    loaded_names = _migrate_managed_legacy_column_labels(
        loaded_config.get("column_display_names")
    )
    if isinstance(loaded_names, dict):
        for key, value in loaded_names.items():
            if not isinstance(key, str) or not isinstance(value, str):
                continue
            key_clean = key.strip()
            value_clean = value.strip()
            if not key_clean or not value_clean:
                continue
            if key_clean in _LEGACY_INVALID_COLUMN_KEYS:
                continue
            if (
                key_clean != "#"
                and key_clean not in allowed_name_keys
                and not re.fullmatch(r"[a-z][a-z0-9_]*", key_clean)
            ):
                logger.warning(
                    "Ignoring invalid column_display_names key '%s' (expected internal key format).",
                    key_clean,
                )
                continue
            names[key_clean] = value_clean
    for required in REQUIRED_DISPLAY_COLUMNS:
        names.setdefault(
            required,
            DEFAULT_COLUMN_DISPLAY_NAMES.get(required, _build_fallback_label(required)),
        )
    for column in display_columns:
        names.setdefault(
            column,
            DEFAULT_COLUMN_DISPLAY_NAMES.get(column, _build_fallback_label(column)),
        )
    merged["column_display_names"] = names
    merged["display_mappings"] = copy.deepcopy(names)

    platform_widths = copy.deepcopy(DEFAULT_COLUMN_WIDTHS_BY_PLATFORM)
    loaded_platform_widths = _migrate_managed_legacy_platform_widths(
        loaded_config.get("column_widths_by_platform")
    )
    if isinstance(loaded_platform_widths, dict):
        for platform_key, raw_widths in loaded_platform_widths.items():
            if not isinstance(platform_key, str):
                continue
            normalized_key = _normalize_platform_key(platform_key)
            if normalized_key not in platform_widths:
                continue
            platform_widths[normalized_key].update(raw_widths)
    merged["column_widths_by_platform"] = platform_widths

    loaded_widths = _migrate_managed_legacy_widths(
        loaded_config.get("column_widths"),
        _resolve_platform_column_widths(platform_widths),
    )
    widths = _resolve_platform_column_widths(
        platform_widths,
        None if loaded_platform_widths else loaded_widths,
    )
    widths.setdefault("#", DEFAULT_COLUMN_WIDTHS["#"])
    for column in display_columns:
        if column not in widths:
            widths[column] = DEFAULT_COLUMN_WIDTHS.get(column, 120)
    merged["column_widths"] = widths

    settings = copy.deepcopy(DEFAULT_GUI_SETTINGS)
    loaded_settings = loaded_config.get("gui_settings")
    if isinstance(loaded_settings, dict):
        for key, value in loaded_settings.items():
            if not isinstance(key, str):
                continue
            key_clean = key.strip()
            if not key_clean:
                continue

            # Keep unknown keys for forward compatibility.
            if key_clean not in DEFAULT_GUI_SETTINGS:
                settings[key_clean] = copy.deepcopy(value)
                continue

            expected = DEFAULT_GUI_SETTINGS[key_clean]
            is_valid_type = True

            if isinstance(expected, bool):
                is_valid_type = isinstance(value, bool)
            elif isinstance(expected, int):
                is_valid_type = isinstance(value, int) and not isinstance(value, bool)
            elif isinstance(expected, float):
                is_valid_type = isinstance(value, (int, float))
            elif isinstance(expected, str):
                is_valid_type = isinstance(value, str)
            elif isinstance(expected, dict):
                is_valid_type = isinstance(value, dict)
            elif isinstance(expected, list):
                is_valid_type = isinstance(value, list)
            elif expected is None:
                is_valid_type = value is None or isinstance(value, str)

            if not is_valid_type:
                logger.warning(
                    "Ignoring invalid gui_settings type for key '%s': expected %s got %s",
                    key_clean,
                    type(expected).__name__,
                    type(value).__name__,
                )
                continue

            settings[key_clean] = copy.deepcopy(value)
    table_cell_alignment = (
        str(
            settings.get(
                "table_cell_alignment",
                DEFAULT_GUI_SETTINGS["table_cell_alignment"],
            )
        )
        .strip()
        .lower()
    )
    if table_cell_alignment not in _VALID_TABLE_CELL_ALIGNMENTS:
        logger.warning(
            "Ignoring invalid gui_settings value for key 'table_cell_alignment': %r",
            settings.get("table_cell_alignment"),
        )
        table_cell_alignment = DEFAULT_GUI_SETTINGS["table_cell_alignment"]
    settings["table_cell_alignment"] = table_cell_alignment

    merged["gui_settings"] = settings

    merged["required_display_columns"] = list(REQUIRED_DISPLAY_COLUMNS)
    return merged


def _has_minimum_preferences_integrity(raw_config: Any) -> bool:
    """Validate minimum expected schema before merge."""
    if not isinstance(raw_config, dict):
        return False
    expected_types: Dict[str, type] = {
        "display_columns": list,
        "column_display_names": dict,
        "display_mappings": dict,
        "column_widths": dict,
        "column_widths_by_platform": dict,
        "gui_settings": dict,
    }
    if not raw_config:
        return False
    for key, value in raw_config.items():
        expected_type = expected_types.get(key)
        if expected_type is None:
            continue
        if not isinstance(value, expected_type):
            return False
    return True


def _create_gui_main_preferences_file(config_path: str) -> None:
    """Create default GUI preferences file atomically from code defaults."""
    config_dir = os.path.dirname(config_path)
    if config_dir:
        os.makedirs(config_dir, exist_ok=True)
    atomic_write_json_file(
        config_path,
        _hard_default_preferences_copy(),
        indent=2,
        ensure_ascii=False,
    )


def ensure_gui_main_preferences_file(config_path: str | None = None) -> bool:
    """Ensure GUI preferences file exists, creating it atomically when missing."""
    if not config_path:
        config_path = get_gui_main_preferences_path()
    if os.path.exists(config_path):
        return True
    try:
        _create_gui_main_preferences_file(config_path)
        return True
    except Exception as exc:
        logger.error(
            "Unable to ensure GUI preferences file at %s: %s", config_path, exc
        )
        return False


def reload_gui_main_preferences_in_place(
    *, auto_create: bool = False
) -> Dict[str, Any]:
    """Reload GUI preferences from disk into shared in-memory dict."""
    loaded = load_gui_main_preferences(auto_create=auto_create)
    GUI_MAIN_PREFERENCES.clear()
    GUI_MAIN_PREFERENCES.update(loaded)
    return GUI_MAIN_PREFERENCES


def load_gui_main_preferences(
    config_path: str | None = None,
    *,
    auto_create: bool = False,
) -> Dict[str, Any]:
    """Load valid GUI preferences or fall back to code defaults."""
    if not config_path:
        config_path = get_gui_main_preferences_path()
    if not os.path.exists(config_path):
        logger.warning(
            "GUI main preferences not found at %s, using defaults.", config_path
        )
        if auto_create:
            try:
                _create_gui_main_preferences_file(config_path)
            except OSError as exc:
                logger.error(
                    "Unable to create GUI preferences at %s: %s", config_path, exc
                )
            except Exception as exc:
                logger.error(
                    "Unexpected error creating GUI preferences at %s: %s",
                    config_path,
                    exc,
                )
        return _merge_preferences({})

    try:
        with open(config_path, "r", encoding="utf-8") as handle:
            loaded_config = json.load(handle)
    except json.JSONDecodeError as exc:
        logger.error("Unable to parse GUI preferences at %s: %s", config_path, exc)
        return _merge_preferences({})
    except OSError as exc:
        logger.error("Unable to read GUI preferences at %s: %s", config_path, exc)
        return _merge_preferences({})

    if not isinstance(loaded_config, dict):
        logger.warning(
            "Invalid GUI preference structure at %s, using defaults.", config_path
        )
        return _merge_preferences({})
    if not _has_minimum_preferences_integrity(loaded_config):
        logger.warning(
            "GUI preferences integrity check failed at %s, using defaults.", config_path
        )
        if auto_create:
            try:
                _create_gui_main_preferences_file(config_path)
            except OSError as exc:
                logger.error(
                    "Unable to recreate GUI preferences at %s: %s", config_path, exc
                )
            except Exception as exc:
                logger.error(
                    "Unexpected error recreating GUI preferences at %s: %s",
                    config_path,
                    exc,
                )
        return _merge_preferences({})

    return _merge_preferences(loaded_config)


GUI_MAIN_PREFERENCES: Dict[str, Any] = load_gui_main_preferences()
