#!/usr/bin/env python3
"""
Testes de Estabilidade para GUI SSA PoC
=====================================

Este módulo contém testes específicos para monitorar travamentos e performance
da GUI SSA PoC conforme solicitado.

Data: 2025-08-18
"""

import os
import sys
import time
import unittest
from typing import Any, cast
from unittest.mock import patch

import pandas as pd

# Adiciona o projeto ao path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, project_root)

from PyQt6.QtCore import Qt  # noqa: E402
from PyQt6.QtTest import QTest  # noqa: E402

# Importações específicas
from PyQt6.QtWidgets import QApplication  # noqa: E402

from gui.gui_config import COLUMN_HEADER_LABEL_VARIANTS  # noqa: E402
from gui.gui_ssa import QT_AVAILABLE  # noqa: E402

try:
    from gui.gui_ssa import SSAMainWindow as _SSAMainWindow  # noqa: E402
except ImportError as exc:
    if "PyQt" not in str(exc):
        raise
    SSAMainWindow = cast(Any, None)
    QT_AVAILABLE = False
else:
    SSAMainWindow = cast(Any, _SSAMainWindow)


class TestGUIStability(unittest.TestCase):
    """Testes de estabilidade para a GUI."""

    @classmethod
    def setUpClass(cls):
        """Configuração inicial dos testes."""
        if not QT_AVAILABLE or SSAMainWindow is None:
            raise unittest.SkipTest("Qt/GUI principal indisponível – pulando testes")
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        """Configuração antes de cada teste."""
        if not QT_AVAILABLE or SSAMainWindow is None:
            self.skipTest("Qt/GUI principal indisponível")
        # Força modo de filtragem síncrono para evitar uso de QThread em ambiente de teste/headless
        self._ssa_sync_filter_was_set = "SSA_SYNC_FILTER" in os.environ
        self._ssa_sync_filter_snapshot = os.environ.get("SSA_SYNC_FILTER")
        os.environ["SSA_SYNC_FILTER"] = "1"
        self._load_patch = patch.object(SSAMainWindow, "load_data", lambda self: None)
        self._load_patch.start()
        self.window = SSAMainWindow()
        self.window.show()

        # Mock data para testes
        self.mock_data = pd.DataFrame(
            {
                "numero_ssa": [20251, 20252, 20253, 20254, 20255],
                "situacao": [
                    "Pendente",
                    "Executada",
                    "Em Execução",
                    "Cancelada",
                    "Pendente",
                ],
                "derivada_de": ["", "", "", "", ""],
                "localizacao_codigo": ["G076", "G077", "G078", "G079", "G080"],
                "equipamento": ["EQ001", "EQ002", "EQ003", "EQ004", "EQ005"],
                "semana_cadastro": [1, 2, 3, 4, 5],
                "data_cadastro": [
                    "2025-01-01",
                    "2025-01-02",
                    "2025-01-03",
                    "2025-01-04",
                    "2025-01-05",
                ],
                "descricao_ssa": [
                    "Teste 1",
                    "Teste 2",
                    "Teste 3",
                    "Teste 4",
                    "Teste 5",
                ],
                "setor_executor": ["MEL3", "MEL4", "MEL3", "MEL4", "MEL3"],
                "setor_emissor": ["IE3", "IE3", "IE4", "IE3", "IE4"],
                "solicitante": ["JOÃO", "MARIA", "PEDRO", "ANA", "CARLOS"],
                "servico_origem": ["SV1", "SV2", "SV3", "SV4", "SV5"],
                "grau_prioridade_emissao": [1, 2, 3, 4, 5],
                "execucao_simples": ["Sim", "Não", "Sim", "Não", "Sim"],
                "semana_programada": [10, 11, 12, 13, 14],
                "descricao_execucao": [
                    "Descrição 1",
                    "Descrição 2",
                    "Descrição 3",
                    "Descrição 4",
                    "Descrição 5",
                ],
            }
        )

        # Simula dados carregados
        self.window.df_completo = self.mock_data.copy()
        self.window.df_exibido = self.mock_data.copy()

    def tearDown(self):
        """Limpeza após cada teste."""
        try:
            self.window.close()
        finally:
            self._load_patch.stop()
            if self._ssa_sync_filter_was_set:
                os.environ["SSA_SYNC_FILTER"] = str(self._ssa_sync_filter_snapshot)
            else:
                os.environ.pop("SSA_SYNC_FILTER", None)

    def test_filtro_travamento_svp(self):
        """Testa especificamente o filtro 'svp' que causava travamento."""
        print("\nTEST Testando filtro 'svp' que causava travamento...")

        start_time = time.time()

        # Simula digitação do filtro problemático
        self.window.search_input.setText("svp")

        # Simula pressionar Enter
        cast(Any, QTest).keyPress(self.window.search_input, Qt.Key.Key_Return)

        # Permite processamento
        QApplication.processEvents()

        end_time = time.time()
        response_time = end_time - start_time

        # Verifica se não travou (resposta em menos de 2 segundos)
        self.assertLess(
            response_time,
            2.0,
            f"Filtro 'svp' demorou {response_time:.2f}s - possível travamento",
        )
        print(f"OK Filtro 'svp' processado em {response_time:.3f}s")

    def test_filtros_problematicos(self):
        """Testa filtros que podem causar problemas."""
        filtros_teste = [
            "svp",
            "mel",
            "g076",
            "pendente",
            "executada",
            "!",
            "!!!",
            "",
            "   ",
            ",,,",
            "mel,svp,g076",
        ]

        print(
            f"\nTEST Testando {len(filtros_teste)} filtros potencialmente problemáticos..."
        )

        for filtro in filtros_teste:
            with self.subTest(filtro=filtro):
                start_time = time.time()

                # Simula filtro
                self.window.search_input.setText(filtro)
                self.window.filter_data()
                QApplication.processEvents()

                end_time = time.time()
                response_time = end_time - start_time

                # Verifica se não travou
                self.assertLess(
                    response_time,
                    2.0,
                    f"Filtro '{filtro}' demorou {response_time:.2f}s - possível travamento",
                )
                print(f"  OK '{filtro}': {response_time:.3f}s")

    def test_carregamento_dados_grandes(self):
        """Testa performance com datasets grandes."""
        print("\nTEST Testando performance com dataset grande...")

        # Cria dataset grande (1000 registros)
        large_data = pd.concat([self.mock_data] * 200, ignore_index=True)
        large_data["numero_ssa"] = range(20001, 20001 + len(large_data))

        start_time = time.time()

        # Simula carregamento
        self.window.df_completo = large_data
        self.window.df_exibido = large_data.head(300)  # Limitação implementada
        self.window.display_data(self.window.df_exibido)
        QApplication.processEvents()

        end_time = time.time()
        load_time = end_time - start_time

        # Verifica se carregou em tempo aceitável
        self.assertLess(
            load_time,
            5.0,
            f"Carregamento de {len(large_data)} registros demorou {load_time:.2f}s",
        )
        print(
            f"OK Dataset de {len(large_data)} registros carregado em {load_time:.3f}s"
        )

    def test_colunas_obrigatorias(self):
        """Verifica se as colunas obrigatorias estao sendo exibidas."""
        print("\nTEST Testando exibicao de colunas obrigatorias...")

        # Forca exibicao dos dados
        self.window.display_data(self.window.df_exibido)
        QApplication.processEvents()

        # Verifica se a tabela foi populada
        self.assertGreater(
            self.window.table_widget.columnCount(), 0, "Nenhuma coluna foi exibida"
        )
        self.assertGreater(
            self.window.table_widget.rowCount(), 0, "Nenhuma linha foi exibida"
        )

        # Verifica colunas especificas mencionadas pelo usuario
        headers = []
        for i in range(self.window.table_widget.columnCount()):
            item = self.window.table_widget.horizontalHeaderItem(i)
            if item is not None:
                headers.append(item.text())

        # Contract: adaptive labels may shorten headers on Linux/offscreen.
        descricao_execucao_labels = set(
            COLUMN_HEADER_LABEL_VARIANTS["descricao_execucao"].values()
        )
        colunas_obrigatorias = ["Numero SSA"]
        for coluna in colunas_obrigatorias:
            self.assertIn(
                coluna,
                headers,
                f"Coluna obrigatoria '{coluna}' nao encontrada. Headers: {headers}",
            )
            print(f"  OK Coluna '{coluna}' presente")
        cadastro_labels = set(COLUMN_HEADER_LABEL_VARIANTS["data_cadastro"].values())
        self.assertTrue(
            cadastro_labels.intersection(headers),
            f"Coluna obrigatoria 'data_cadastro' nao encontrada. Headers: {headers}",
        )
        print("  OK Coluna 'data_cadastro' presente")
        self.assertIn("descricao_execucao", self.window._current_display_columns)
        self.assertTrue(
            descricao_execucao_labels.intersection(headers),
            f"Coluna obrigatoria 'descricao_execucao' nao encontrada. Headers: {headers}",
        )
        print("  OK Coluna 'descricao_execucao' presente")

    def test_menu_contexto(self):
        """Testa o menu de contexto sem travamento."""
        print("\nTEST Testando menu de contexto...")

        # Força exibição dos dados
        self.window.display_data(self.window.df_exibido)
        QApplication.processEvents()

        start_time = time.time()

        # Simula clique direito na primeira célula
        if self.window.table_widget.rowCount() > 0:
            item = self.window.table_widget.item(0, 0)
            if item:
                # Simula criação do menu (sem exibi-lo)
                try:
                    # Testa os métodos relacionados ao menu
                    self.window.copy_cell_value(item)
                    self.window.copy_row_data(0)
                    print("OK Funções do menu de contexto funcionaram")
                except Exception as e:
                    self.fail(f"Erro nas funções do menu: {e}")

        end_time = time.time()
        menu_time = end_time - start_time

        self.assertLess(menu_time, 1.0, f"Operações do menu demoraram {menu_time:.2f}s")
        print(f"OK Operações do menu executadas em {menu_time:.3f}s")

    def test_responsividade_ui(self):
        """Testa se a UI mantém responsividade durante operações."""
        print("\nTEST Testando responsividade da interface...")

        start_time = time.time()
        iterations = 0
        max_iterations = 100

        # Simula operações repetidas
        while time.time() - start_time < 2.0 and iterations < max_iterations:
            self.window.search_input.setText(f"teste{iterations % 5}")
            QApplication.processEvents()  # Permite UI responder
            iterations += 1

        end_time = time.time()
        total_time = end_time - start_time

        # Verifica se conseguiu processar um número razoável de iterações
        self.assertGreater(
            iterations,
            10,
            f"UI travou - apenas {iterations} iterações em {total_time:.2f}s",
        )
        print(f"OK UI responsiva: {iterations} iterações em {total_time:.3f}s")


def run_stability_tests():
    """Executa todos os testes de estabilidade."""
    print("=" * 60)
    print("FIX TESTES DE ESTABILIDADE DA GUI SSA POC")
    print("=" * 60)
    print("Objetivo: Monitorar travamentos e performance conforme solicitado")
    print("Data: 2025-08-18")
    print("=" * 60)

    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(TestGUIStability)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    print("\n" + "=" * 60)
    if result.wasSuccessful():
        print("OK TODOS OS TESTES DE ESTABILIDADE PASSARAM!")
        print("OK GUI está estável e sem travamentos detectados")
    else:
        print("WARN  ALGUNS TESTES FALHARAM!")
        print(f"ERR Falhas: {len(result.failures)}")
        print(f"ERR Erros: {len(result.errors)}")
    print("=" * 60)

    return result.wasSuccessful()


if __name__ == "__main__":
    run_stability_tests()
