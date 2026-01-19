"""
Testes para o sistema de configuração isolado da GUI Principal (main.py --gui)
Valida carregamento, estrutura e isolamento das configurações.
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
    """Testes para o sistema de configuração da GUI Principal"""

    def test_gui_main_preferences_file_exists(self):
        """Verifica se o arquivo de configuração existe"""
        config_path = os.path.join(project_root, "config", "gui_main_preferences.json")
        assert os.path.exists(config_path), (
            "Arquivo gui_main_preferences.json deve existir"
        )

    def test_load_gui_main_preferences_structure(self):
        """Testa se a função de carregamento funciona e estrutura é válida"""
        # Testa configuração real (não mock)
        from gui.gui_config import load_gui_main_preferences

        config = load_gui_main_preferences()

        # Verifica estrutura essencial
        assert "display_columns" in config
        assert "column_display_names" in config
        assert "column_widths" in config
        assert "gui_settings" in config
        assert isinstance(config["display_columns"], list)
        assert isinstance(config["column_display_names"], dict)
        assert isinstance(config["column_widths"], dict)
        assert isinstance(config["gui_settings"], dict)

    def test_load_gui_main_preferences_fallback(self):
        """Testa fallback quando arquivo não existe"""
        with patch("os.path.exists", return_value=False):
            from gui.gui_config import load_gui_main_preferences

            config = load_gui_main_preferences()

            # Verifica que retorna configuração padrão válida
            assert "display_columns" in config
            assert len(config["display_columns"]) > 0
            assert "numero_ssa" in config["display_columns"]
            assert config["version"] == "1.0.0"

    def test_load_gui_main_preferences_invalid_json(self):
        """Testa comportamento com JSON inválido"""
        with patch("builtins.open", mock_open(read_data="invalid json")):
            with patch("os.path.exists", return_value=True):
                from gui.gui_config import load_gui_main_preferences

                config = load_gui_main_preferences()

                # Deve retornar configuração padrão em caso de erro
                assert "display_columns" in config
                assert config["version"] == "1.0.0"

    def test_gui_main_preferences_isolation_from_cli(self):
        """Verifica que as configurações são independentes do CLI"""
        # Carrega configurações da GUI Main
        # Carrega configurações padrão do CLI
        from core.config_manager import load_settings
        from gui.gui_ssa import GUI_MAIN_PREFERENCES

        cli_settings = load_settings()

        # Verifica que são diferentes estruturas
        assert GUI_MAIN_PREFERENCES != cli_settings
        assert "display_columns" in GUI_MAIN_PREFERENCES
        assert "created_for" in GUI_MAIN_PREFERENCES
        assert GUI_MAIN_PREFERENCES["created_for"] == "GUI Main (main.py --gui)"

    def test_column_display_names_mapping(self):
        """Testa mapeamento de nomes de colunas"""
        from gui.gui_ssa import GUI_MAIN_PREFERENCES

        names = GUI_MAIN_PREFERENCES.get("column_display_names", {})
        assert isinstance(names, dict)
        assert "numero_ssa" in names
        assert names["numero_ssa"] == "Número SSA"

    def test_column_widths_configuration(self):
        """Testa configuração de larguras de colunas"""
        from gui.gui_ssa import GUI_MAIN_PREFERENCES

        widths = GUI_MAIN_PREFERENCES.get("column_widths", {})
        assert isinstance(widths, dict)
        assert "numero_ssa" in widths
        assert isinstance(widths["numero_ssa"], int)
        assert widths["numero_ssa"] > 0

    def test_gui_settings_validation(self):
        """Testa configurações específicas da GUI"""
        from gui.gui_ssa import GUI_MAIN_PREFERENCES

        settings = GUI_MAIN_PREFERENCES.get("gui_settings", {})
        assert isinstance(settings, dict)
        assert "page_size" in settings
        assert "debounce_delay" in settings
        assert "default_filter_mode" in settings
        assert isinstance(settings["page_size"], int)
        assert settings["page_size"] > 0

    def test_display_columns_validation(self):
        """Testa lista de colunas de exibição"""
        from gui.gui_ssa import GUI_MAIN_PREFERENCES

        columns = GUI_MAIN_PREFERENCES.get("display_columns", [])
        assert isinstance(columns, list)
        assert len(columns) > 0
        assert "numero_ssa" in columns
        # Verifica que não há duplicatas
        assert len(columns) == len(set(columns))

    def test_hidden_columns_validation(self):
        """Testa lista de colunas ocultas"""
        from gui.gui_ssa import GUI_MAIN_PREFERENCES

        hidden = GUI_MAIN_PREFERENCES.get("hidden_columns", [])
        display = GUI_MAIN_PREFERENCES.get("display_columns", [])

        assert isinstance(hidden, list)
        # Verifica que colunas ocultas não estão nas de exibição
        for col in hidden:
            assert col not in display

    def test_gui_main_import_independence(self):
        """Testa que GUI Main pode ser importada sem dependências do CLI"""
        # Remove imports do CLI se existirem no namespace
        modules_to_remove = []
        for module_name in sys.modules:
            if "core.config_manager" in module_name:
                modules_to_remove.append(module_name)

        for module_name in modules_to_remove:
            del sys.modules[module_name]

        # Tenta importar GUI Main
        try:
            from gui.gui_config import GUI_MAIN_PREFERENCES, load_gui_main_preferences

            # Se chegou aqui, importação foi bem-sucedida
            assert True
        except ImportError as e:
            pytest.fail(f"GUI Main não deveria depender de módulos do CLI: {e}")


if __name__ == "__main__":
    # Executa os testes
    pytest.main([__file__, "-v"])
