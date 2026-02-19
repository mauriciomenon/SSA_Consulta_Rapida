"""Regression tests for gui table render resilience."""

import os
import sys
from unittest.mock import patch

import pandas as pd
import pytest

pytest.importorskip("PyQt6", reason="PyQt6 dependency unavailable in test environment")

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from PyQt6.QtWidgets import QApplication  # noqa: E402

from gui import gui_ssa  # noqa: E402
from gui.gui_ssa import SSAMainWindow  # noqa: E402
from gui.mixins import filter_gui_ssa_mixin as filter_mixin  # noqa: E402


class TestGUITableRenderResilience:
    @classmethod
    def setup_class(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setup_method(self):
        self._load_patch = patch.object(SSAMainWindow, "load_data", lambda self: None)
        self._load_patch.start()
        self.window = SSAMainWindow()
        self.window.show()

        self.base_df = pd.DataFrame(
            {
                "numero_ssa": [1, 2, 3],
                "situacao": ["APV", "STE", "AMP"],
                "derivada_de": ["", "", ""],
                "localizacao_codigo": ["LOC1", "LOC2", "LOC3"],
                "descricao_localizacao": ["Desc"] * 3,
                "equipamento": ["EQ1"] * 3,
                "semana_cadastro": [202501, 202501, 202501],
                "semana_programada": [202503, 202503, 202503],
                "data_cadastro": ["2025-01-01", "2025-01-01", "2025-01-01"],
                "descricao_ssa": ["Teste A", "Teste B", "Teste C"],
                "setor_executor": ["IEE3", "MEL4", "XYZ"],
                "setor_emissor": ["ABC", "MEL4", "XYZ"],
                "descricao_execucao": ["Exec A", "Exec B", "Exec C"],
                "solicitante": ["User1", "User2", "User3"],
            }
        )

        self.window.df_completo = self.base_df.copy()
        self.window.df_exibido = self.base_df.copy()
        self.window._df_last_search_filtered = self.base_df.copy()
        self.window.paginator.page_size = 10
        self.window.paginator.set_dataframe(self.base_df.copy())

    def teardown_method(self):
        self._load_patch.stop()
        self.window.close()
        try:
            gui_ssa.GLOBAL_RETIRED_DATA_LOADER_WORKERS.clear()
        except Exception:
            gui_ssa.GLOBAL_RETIRED_DATA_LOADER_WORKERS[:] = []
        try:
            filter_mixin.GLOBAL_RETIRED_FILTER_WORKERS.clear()
        except Exception:
            filter_mixin.GLOBAL_RETIRED_FILTER_WORKERS[:] = []

    def test_display_current_page_continues_when_first_cell_item_creation_fails(self):
        from gui.ssa import gui_table

        original_qtable_item = gui_table.QTableWidgetItem
        calls = {"count": 0}

        def flaky_qtable_item(text):
            calls["count"] += 1
            if calls["count"] == 1:
                raise RuntimeError("forced cell construction failure")
            return original_qtable_item(text)

        with patch("gui.ssa.gui_table.QTableWidgetItem", side_effect=flaky_qtable_item):
            self.window.display_current_page(1)
            QApplication.processEvents()

        assert calls["count"] > 1
        assert self.window.table_widget.rowCount() == len(self.base_df)
        assert self.window.table_widget.item(0, 0) is not None
