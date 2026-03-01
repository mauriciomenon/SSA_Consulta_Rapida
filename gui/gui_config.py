"""Centralized GUI configuration loader with defensive merge rules."""

from __future__ import annotations

import copy
import json
import os
import re
from typing import Any, Dict, Iterable, List
from core import config_manager as core_config_manager
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


def get_gui_main_preferences_path() -> str:
    """Return current GUI preferences path resolved from active config hierarchy."""
    return _resolve_gui_main_preferences_path()

# Contract: these columns must always be available in GUI defaults and mappings.
REQUIRED_DISPLAY_COLUMNS: List[str] = [
    "numero_ssa",
    "situacao",
    "semana_cadastro",
    "semana_programada",
    "derivada_de",
    "localizacao_codigo",
    "data_cadastro",
    "descricao_ssa",
    "setor_executor",
    "setor_emissor",
    "solicitante",
    "descricao_execucao",
]

DEFAULT_COLUMN_DISPLAY_NAMES: Dict[str, str] = {
    "numero_ssa": "Numero SSA",
    "setor_executor": "Exec.",
    "situacao": "Sit.",
    "descricao_ssa": "Descricao da SSA",
    "data_cadastro": "Cadastro",
    "semana_cadastro": "Sem. Cad.",
    "localizacao_codigo": "Loc.",
    "grau_prioridade": "Prio.",
    "grau_prioridade_emissao": "Prio. Emissao",
    "grau_prioridade_planejamento": "Prio. Planej.",
    "setor_emissor": "Emis.",
    "solicitante": "Solicitante",
    "derivada_de": "Derivada de",
    "semana_programada": "Prog.",
    "descricao_execucao": "Descricao Execucao",
    "descricao_localizacao": "Desc. Localizacao",
    "equipamento": "Equipamento",
    "origem": "Origem",
    "servico_origem": "Serv. Origem",
    "execucao_simples": "Exec. Simples",
    "responsavel_programacao": "Resp. Prog.",
    "responsavel_execucao": "Resp. Exec.",
    "arquivo_origem": "Arquivo Origem",
}

DEFAULT_COLUMN_WIDTHS: Dict[str, int] = {
    "#": 30,
    "numero_ssa": 93,
    "localizacao_codigo": 86,
    "setor_executor": 65,
    "situacao": 51,
    "descricao_ssa": 296,
    "data_cadastro": 100,
    "setor_emissor": 58,
    "derivada_de": 93,
    "semana_programada": 86,
    "descricao_execucao": 280,
    "semana_cadastro": 72,
    "grau_prioridade": 95,
    "grau_prioridade_emissao": 95,
    "grau_prioridade_planejamento": 95,
    "solicitante": 121,
}

DEFAULT_GUI_SETTINGS: Dict[str, Any] = {
    "page_size": 50,
    "auto_load": False,
    "debounce_delay": 800,
    "default_filter_mode": "contains",
    "show_progress_bar": True,
    "enable_column_sorting": True,
    "show_details_panel": True,
    "enable_double_click_details": True,
    "theme": "classico",
    "filter_cache_size": 50,
    "cache_enabled": True,
    "cache_auto_clear": False,
    "theme_default": None,
}

DEFAULT_GUI_MAIN_PREFERENCES: Dict[str, Any] = {
    "display_columns": list(REQUIRED_DISPLAY_COLUMNS),
    "hidden_columns": [
        "descricao_localizacao",
        "equipamento",
        "origem",
        "servico_origem",
        "execucao_simples",
        "grau_prioridade_emissao",
        "arquivo_origem",
    ],
    "column_display_names": copy.deepcopy(DEFAULT_COLUMN_DISPLAY_NAMES),
    "column_widths": copy.deepcopy(DEFAULT_COLUMN_WIDTHS),
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
DEFAULT_GUI_MAIN_PREFERENCES["required_display_columns"] = list(REQUIRED_DISPLAY_COLUMNS)

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

_MERGE_KEYS = {"display_columns", "hidden_columns", "column_display_names", "column_widths", "gui_settings"}
_LEGACY_INVALID_COLUMN_KEYS = {"Número da SSA", "Numero da SSA", "No SSA", "Data Cadastro"}


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


def _merge_preferences(loaded_config: Dict[str, Any]) -> Dict[str, Any]:
    merged = copy.deepcopy(DEFAULT_GUI_MAIN_PREFERENCES)

    # Preserve unknown top-level keys to avoid breaking custom features.
    for key, value in loaded_config.items():
        if key in _MERGE_KEYS:
            continue
        merged[key] = copy.deepcopy(value)

    loaded_display = loaded_config.get("display_columns")
    if isinstance(loaded_display, list):
        display_columns = _unique_str_list(loaded_display)
    else:
        display_columns = list(DEFAULT_GUI_MAIN_PREFERENCES["display_columns"])
    if not display_columns:
        display_columns = list(DEFAULT_GUI_MAIN_PREFERENCES["display_columns"])
    for required in REQUIRED_DISPLAY_COLUMNS:
        if required not in display_columns:
            display_columns.append(required)
    merged["display_columns"] = display_columns

    loaded_hidden = loaded_config.get("hidden_columns")
    if isinstance(loaded_hidden, list):
        hidden_columns = _unique_str_list(loaded_hidden)
    else:
        hidden_columns = list(DEFAULT_GUI_MAIN_PREFERENCES["hidden_columns"])
    hidden_columns = [column for column in hidden_columns if column not in display_columns]
    merged["hidden_columns"] = hidden_columns

    names = copy.deepcopy(DEFAULT_COLUMN_DISPLAY_NAMES)
    allowed_name_keys = set(DEFAULT_COLUMN_DISPLAY_NAMES.keys())
    allowed_name_keys.update(display_columns)
    allowed_name_keys.update(hidden_columns)
    allowed_name_keys.update(REQUIRED_DISPLAY_COLUMNS)
    loaded_names = loaded_config.get("column_display_names")
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
            column, DEFAULT_COLUMN_DISPLAY_NAMES.get(column, _build_fallback_label(column))
        )
    merged["column_display_names"] = names
    merged["display_mappings"] = copy.deepcopy(names)

    widths = copy.deepcopy(DEFAULT_COLUMN_WIDTHS)
    loaded_widths = loaded_config.get("column_widths")
    if isinstance(loaded_widths, dict):
        for key, value in loaded_widths.items():
            if not isinstance(key, str):
                continue
            if isinstance(value, (int, float)) and value > 0:
                widths[key.strip()] = int(value)
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
    merged["gui_settings"] = settings

    merged["required_display_columns"] = list(REQUIRED_DISPLAY_COLUMNS)
    return merged


def load_gui_main_preferences(config_path: str | None = None) -> Dict[str, Any]:
    """Load GUI main preferences and defensively merge with full defaults."""
    if not config_path:
        config_path = get_gui_main_preferences_path()
    if not os.path.exists(config_path):
        logger.warning("GUI main preferences not found at %s, recreating defaults.", config_path)
        try:
            os.makedirs(os.path.dirname(config_path), exist_ok=True)
            with open(config_path, "w", encoding="utf-8") as handle:
                json.dump(DEFAULT_GUI_MAIN_PREFERENCES, handle, ensure_ascii=False, indent=2)
        except OSError as exc:
            logger.error("Unable to recreate GUI preferences at %s: %s", config_path, exc)
        return copy.deepcopy(DEFAULT_GUI_MAIN_PREFERENCES)

    try:
        with open(config_path, "r", encoding="utf-8") as handle:
            loaded_config = json.load(handle)
    except json.JSONDecodeError as exc:
        logger.error("Unable to parse GUI preferences at %s: %s", config_path, exc)
        return copy.deepcopy(DEFAULT_GUI_MAIN_PREFERENCES)
    except OSError as exc:
        logger.error("Unable to read GUI preferences at %s: %s", config_path, exc)
        return copy.deepcopy(DEFAULT_GUI_MAIN_PREFERENCES)

    if not isinstance(loaded_config, dict):
        logger.warning("Invalid GUI preference structure at %s, using defaults.", config_path)
        return copy.deepcopy(DEFAULT_GUI_MAIN_PREFERENCES)

    return _merge_preferences(loaded_config)


# Loaded once for runtime usage in GUI module.
GUI_MAIN_PREFERENCES = load_gui_main_preferences()
