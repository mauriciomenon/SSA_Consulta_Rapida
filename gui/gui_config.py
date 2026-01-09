# gui/gui_config.py
# Configuration loader for GUI

import os
import sys
import json
import logging

logger = logging.getLogger(__name__)

# Calculate project root (assuming this file is in gui/)
# gui/gui_config.py -> gui/ -> project_root
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

def load_gui_main_preferences():
    """Carrega configuracoes especificas da GUI Principal do arquivo JSON."""
    config_path = os.path.join(project_root, 'config', 'gui_main_preferences.json')

    default_config = {
        "display_columns": [
            "numero_ssa", "setor_executor", "situacao", "descricao_ssa",
            "data_cadastro", "semana_cadastro", "localizacao_codigo", "grau_prioridade_emissao"
        ],
        "hidden_columns": ["descricao_localizacao", "equipamento", "servico_origem"],
        "column_display_names": {
            "numero_ssa": "Numero SSA", "setor_executor": "Exec.",
            "situacao": "Sit.", "descricao_ssa": "Desc.",
            "data_cadastro": "Data Cad.", "semana_cadastro": "Sem.Cad.",
            "localizacao_codigo": "Loc.", "grau_prioridade_emissao": "Prio.Emis."
        },
        "column_widths": {
            "#": 35, "numero_ssa": 120, "setor_executor": 150, "situacao": 120,
            "descricao_ssa": 300, "data_cadastro": 110, "semana_cadastro": 100
        },
        "gui_settings": {
            "page_size": 50, "auto_load": False, "debounce_delay": 250,
            "default_filter_mode": "contains", "show_progress_bar": True,
            "theme": "gruvbox", "theme_default": None
        },
        "version": "1.0.0"
    }

    if not os.path.exists(config_path):
        logger.warning("Gui main preferences not found at %s, using defaults.", config_path)
        return default_config

    try:
        with open(config_path, 'r', encoding='utf-8') as handle:
            loaded_config = json.load(handle)
    except json.JSONDecodeError as exc:
        logger.error("Unable to parse gui main preferences at %s: %s", config_path, exc)
        return default_config
    except OSError as exc:
        logger.error("Unable to read gui main preferences at %s: %s", config_path, exc)
        return default_config

    if not isinstance(loaded_config, dict) or 'display_columns' not in loaded_config:
        logger.warning("Invalid gui main preferences structure at %s, using defaults.", config_path)
        return default_config

    return loaded_config

# Carrega as configurações globalmente
GUI_MAIN_PREFERENCES = load_gui_main_preferences()
