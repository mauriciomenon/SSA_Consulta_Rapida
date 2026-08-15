#!/usr/bin/env python3
"""
Testes do sistema de configuração JSON da GUI PoC
Validação da separação de configurações entre GUI e CLI
"""

import importlib
import json
import sys
import unittest
from pathlib import Path

# Adiciona o diretório raiz ao path para importações
sys.path.insert(0, str(Path(__file__).parent.parent))


class TestGUIConfiguration(unittest.TestCase):
    """Testes para o sistema de configuração JSON da GUI PoC"""

    def setUp(self):
        """Configuração inicial dos testes"""
        self.config_path = Path("config/gui_poc_preferences.json")
        self.required_keys = [
            "display_columns",
            "hidden_columns",
            "column_display_names",
            "column_widths",
        ]
        self.critical_columns = ["numero_ssa", "cadastro", "prioridade"]
        self.unwanted_columns = ["equipamento", "origem"]

    def test_config_file_exists(self):
        """Testa se o arquivo de configuração existe"""
        self.assertTrue(
            self.config_path.exists(),
            f"Arquivo de configuração não encontrado: {self.config_path}",
        )

    def test_json_loading(self):
        """Testa se o JSON é válido e pode ser carregado"""
        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                config = json.load(f)
            self.assertIsInstance(config, dict, "Configuração deve ser um dicionário")
        except json.JSONDecodeError as e:
            self.fail(f"JSON inválido: {e}")
        except Exception as e:
            self.fail(f"Erro ao carregar arquivo: {e}")

    def test_required_keys_present(self):
        """Testa se todas as chaves necessárias estão presentes"""
        with open(self.config_path, "r", encoding="utf-8") as f:
            config = json.load(f)

        for key in self.required_keys:
            self.assertIn(
                key, config, f"Chave obrigatória '{key}' ausente na configuração"
            )

    def test_critical_columns_present(self):
        """Testa se as colunas críticas estão configuradas para exibição"""
        with open(self.config_path, "r", encoding="utf-8") as f:
            config = json.load(f)

        display_columns = config.get("display_columns", [])

        for col in self.critical_columns:
            self.assertIn(
                col,
                display_columns,
                f"Coluna crítica '{col}' não está na lista de exibição",
            )

    def test_unwanted_columns_hidden(self):
        """Testa se as colunas indesejadas estão ocultas"""
        with open(self.config_path, "r", encoding="utf-8") as f:
            config = json.load(f)

        hidden_columns = config.get("hidden_columns", [])

        for col in self.unwanted_columns:
            self.assertIn(
                col, hidden_columns, f"Coluna indesejada '{col}' deveria estar oculta"
            )

    def test_gui_module_loading(self):
        """Importação da GUI principal e carregamento de preferências."""
        try:
            from gui.gui_ssa import GUI_MAIN_PREFERENCES

            self.assertIsInstance(
                GUI_MAIN_PREFERENCES, dict, "GUI_MAIN_PREFERENCES deve ser dict"
            )
        except ImportError as e:
            self.skipTest(f"GUI principal indisponível: {e}")
        except Exception as e:
            self.fail(f"Erro ao validar GUI principal: {e}")

    def test_critical_columns_in_memory(self):
        """Verifica colunas críticas na GUI principal (quando aplicável)."""
        try:
            from gui.gui_ssa import GUI_MAIN_PREFERENCES

            loaded_display = GUI_MAIN_PREFERENCES.get("display_columns", [])
            for col in ["numero_ssa"]:
                self.assertIn(col, loaded_display, f"Coluna '{col}' não carregada")
        except ImportError:
            self.skipTest("GUI principal indisponível")

    def test_cli_independence(self):
        """Testa se o CLI permanece independente das configurações da GUI"""
        try:
            # Tenta importar o módulo principal sem erros
            importlib.import_module("main")

            # Verifica se o CLI não foi afetado pelas mudanças da GUI
            # (não deve gerar erros de importação)
            self.assertTrue(True, "CLI carregou sem problemas")

        except ImportError as e:
            self.fail(f"CLI foi afetado pelas mudanças da GUI: {e}")

    def test_configuration_structure(self):
        """Testa a estrutura detalhada da configuração"""
        with open(self.config_path, "r", encoding="utf-8") as f:
            config = json.load(f)

        # Testa tipos de dados
        self.assertIsInstance(
            config["display_columns"], list, "display_columns deve ser uma lista"
        )
        self.assertIsInstance(
            config["hidden_columns"], list, "hidden_columns deve ser uma lista"
        )
        self.assertIsInstance(
            config["column_display_names"],
            dict,
            "column_display_names deve ser um dicionário",
        )
        self.assertIsInstance(
            config["column_widths"], dict, "column_widths deve ser um dicionário"
        )

        # Testa se não há duplicatas
        display_set = set(config["display_columns"])
        self.assertEqual(
            len(display_set),
            len(config["display_columns"]),
            "display_columns não deve ter duplicatas",
        )

        hidden_set = set(config["hidden_columns"])
        self.assertEqual(
            len(hidden_set),
            len(config["hidden_columns"]),
            "hidden_columns não deve ter duplicatas",
        )

    def test_column_priorities(self):
        """Testa se as colunas críticas estão nas primeiras posições"""
        with open(self.config_path, "r", encoding="utf-8") as f:
            config = json.load(f)

        display_columns = config.get("display_columns", [])

        # numero_ssa deve ser a primeira coluna
        if display_columns:
            self.assertEqual(
                display_columns[0],
                "numero_ssa",
                "numero_ssa deve ser a primeira coluna",
            )

        # cadastro e prioridade devem estar nas primeiras posições
        for i, col in enumerate(["cadastro", "prioridade"]):
            if col in display_columns:
                position = display_columns.index(col)
                self.assertLess(
                    position, 5, f"Coluna '{col}' deve estar nas primeiras 5 posições"
                )


def print_test_summary():
    """Imprime um resumo visual dos testes"""
    print("\n" + "=" * 60)
    print("FIX TESTE DO SISTEMA DE CONFIGURAÇÃO GUI POC")
    print("=" * 60)

    config_path = Path("config/gui_poc_preferences.json")

    if config_path.exists():
        with open(config_path, "r", encoding="utf-8") as f:
            config = json.load(f)

        print(f"INFO Arquivo de configuração: {config_path}")
        print(f"INFO Colunas para exibir: {len(config.get('display_columns', []))}")
        print(f"NOTE Colunas ocultas: {len(config.get('hidden_columns', []))}")
        print(f"NOTE Larguras configuradas: {len(config.get('column_widths', {}))}")
        print(f"NOTE Nomes alternativos: {len(config.get('column_display_names', {}))}")
        print(f"NOTE Versão: {config.get('version', 'N/A')}")

        critical_columns = ["numero_ssa", "cadastro", "prioridade"]
        display_columns = config.get("display_columns", [])

        print("\nOK Colunas críticas presentes:")
        for col in critical_columns:
            status = "OK" if col in display_columns else "ERR"
            print(f"   {status} {col}")

    print("=" * 60)


if __name__ == "__main__":
    # Executa os testes
    unittest.main(verbosity=2, exit=False)

    # Imprime resumo visual
    print_test_summary()
