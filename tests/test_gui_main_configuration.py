"""
Testes para o sistema de configuracao isolado da GUI Principal (main.py --gui)
Valida carregamento, estrutura e isolamento das configuracoes.
"""

import json
import os
import sys
from unittest.mock import mock_open, patch

import pytest

# Adiciona o projeto ao path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)


class TestGUIMainConfiguration:
    """Testes para o sistema de configuracao da GUI Principal."""

    def test_gui_main_preferences_contract_available_without_file(self):
        """Contrato de configuracao deve existir mesmo sem arquivo local versionado."""
        from gui.gui_config import load_gui_main_preferences
        with patch("gui.gui_config.os.path.exists", return_value=False):
            config = load_gui_main_preferences()

        assert "display_columns" in config
        assert "column_display_names" in config
        assert "display_mappings" in config
        assert "column_widths" in config

    def test_load_gui_main_preferences_structure(self):
        """Testa se a funcao de carregamento funciona e estrutura e valida."""
        from gui.gui_config import load_gui_main_preferences

        config = load_gui_main_preferences()

        assert "display_columns" in config
        assert "column_display_names" in config
        assert "display_mappings" in config
        assert "column_widths" in config
        assert "gui_settings" in config
        assert isinstance(config["display_columns"], list)
        assert isinstance(config["column_display_names"], dict)
        assert isinstance(config["display_mappings"], dict)
        assert isinstance(config["column_widths"], dict)
        assert isinstance(config["gui_settings"], dict)

    def test_load_gui_main_preferences_fallback(self):
        """Testa fallback quando arquivo nao existe."""
        from gui.gui_config import load_gui_main_preferences
        with patch("gui.gui_config.os.path.exists", return_value=False):
            config = load_gui_main_preferences()
            assert "display_columns" in config
            assert len(config["display_columns"]) > 0
            assert "numero_ssa" in config["display_columns"]
            assert "derivada_de" in config["display_columns"]
            assert config["version"] == "1.0.0"

    def test_load_gui_main_preferences_invalid_json(self):
        """Testa comportamento com JSON invalido."""
        from gui.gui_config import load_gui_main_preferences
        with patch("gui.gui_config.open", mock_open(read_data="invalid json")):
            with patch("gui.gui_config.os.path.exists", return_value=True):
                config = load_gui_main_preferences()
                assert "display_columns" in config
                assert config["version"] == "1.0.0"

    def test_partial_config_is_merged_with_contract(self):
        """JSON parcial deve preservar contrato minimo de colunas e mapeamentos."""
        partial_config = {
            "display_columns": ["numero_ssa", "situacao"],
            "column_display_names": {"numero_ssa": "No SSA"},
            "column_widths": {"numero_ssa": 10},
            "gui_settings": {"page_size": 25},
        }

        from gui.gui_config import REQUIRED_DISPLAY_COLUMNS, load_gui_main_preferences
        with patch("gui.gui_config.open", mock_open(read_data=json.dumps(partial_config))):
            with patch("gui.gui_config.os.path.exists", return_value=True):
                config = load_gui_main_preferences()

        for required in REQUIRED_DISPLAY_COLUMNS:
            assert required in config["display_columns"]
            assert required in config["column_display_names"]
            assert required in config["display_mappings"]

        assert config["column_display_names"]["numero_ssa"] == "No SSA"
        assert config["gui_settings"]["page_size"] == 25
        assert config["column_widths"]["numero_ssa"] == 10

    def test_gui_main_preferences_isolation_from_cli(self):
        """Verifica que as configuracoes sao independentes do CLI."""
        from gui.gui_config import GUI_MAIN_PREFERENCES
        from core.config_manager import load_settings

        try:
            cli_settings = load_settings()
        except Exception:
            cli_settings = {}

        assert GUI_MAIN_PREFERENCES != cli_settings
        assert "display_columns" in GUI_MAIN_PREFERENCES
        assert "created_for" in GUI_MAIN_PREFERENCES
        assert GUI_MAIN_PREFERENCES["created_for"] == "GUI Main (main.py --gui)"

    def test_column_display_names_mapping(self):
        """Testa mapeamento de nomes de colunas."""
        from gui.gui_config import GUI_MAIN_PREFERENCES

        names = GUI_MAIN_PREFERENCES.get("column_display_names", {})
        assert isinstance(names, dict)
        assert "numero_ssa" in names
        assert isinstance(names["numero_ssa"], str)
        assert names["numero_ssa"].strip()

    def test_column_widths_configuration(self):
        """Testa configuracao de larguras de colunas."""
        from gui.gui_config import GUI_MAIN_PREFERENCES

        widths = GUI_MAIN_PREFERENCES.get("column_widths", {})
        assert isinstance(widths, dict)
        assert "numero_ssa" in widths
        assert isinstance(widths["numero_ssa"], int)
        assert widths["numero_ssa"] > 0

    def test_gui_settings_validation(self):
        """Testa configuracoes especificas da GUI."""
        from gui.gui_config import GUI_MAIN_PREFERENCES

        settings = GUI_MAIN_PREFERENCES.get("gui_settings", {})
        assert isinstance(settings, dict)
        assert "page_size" in settings
        assert "debounce_delay" in settings
        assert "default_filter_mode" in settings
        assert isinstance(settings["page_size"], int)
        assert settings["page_size"] > 0

    def test_display_columns_validation(self):
        """Testa lista de colunas de exibicao."""
        from gui.gui_config import GUI_MAIN_PREFERENCES, REQUIRED_DISPLAY_COLUMNS

        columns = GUI_MAIN_PREFERENCES.get("display_columns", [])
        assert isinstance(columns, list)
        assert len(columns) > 0
        assert "numero_ssa" in columns
        assert len(columns) == len(set(columns))
        for required in REQUIRED_DISPLAY_COLUMNS:
            assert required in columns

    def test_hidden_columns_validation(self):
        """Testa lista de colunas ocultas."""
        from gui.gui_config import GUI_MAIN_PREFERENCES

        hidden = GUI_MAIN_PREFERENCES.get("hidden_columns", [])
        display = GUI_MAIN_PREFERENCES.get("display_columns", [])

        assert isinstance(hidden, list)
        for col in hidden:
            assert col not in display

    def test_gui_main_import_independence(self):
        """Testa que GUI Main pode ser importada sem dependencias do CLI."""
        modules_to_restore = {}
        for module_name in list(sys.modules):
            if "core.config_manager" in module_name:
                modules_to_restore[module_name] = sys.modules[module_name]
                del sys.modules[module_name]

        try:
            from gui.gui_config import GUI_MAIN_PREFERENCES, load_gui_main_preferences

            assert isinstance(GUI_MAIN_PREFERENCES, dict)
            assert callable(load_gui_main_preferences)
        except ImportError as e:
            pytest.fail(f"GUI Main nao deveria depender de modulos do CLI: {e}")
        finally:
            for module_name, module_obj in modules_to_restore.items():
                sys.modules[module_name] = module_obj


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
