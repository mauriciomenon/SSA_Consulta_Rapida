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
from gui.ssa import gui_details as ssa_gui_details  # noqa: E402
from utils.formatting import format_dataframe_for_display  # noqa: E402


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

        self._set_window_dataframe(self.base_df.copy(), page_size=10)

    def _set_window_dataframe(self, dataframe: pd.DataFrame, *, page_size: int) -> None:
        self.window.df_completo = dataframe.copy()
        self.window.df_exibido = dataframe.copy()
        self.window._df_last_search_filtered = dataframe.copy()
        self.window.paginator.page_size = page_size
        self.window.paginator.set_dataframe(dataframe.copy())

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

    def test_display_current_page_skips_redundant_detail_refresh_for_same_signature(self):
        with patch.object(ssa_gui_details, "_update_details_from_series", wraps=ssa_gui_details._update_details_from_series) as update_details:
            self.window.display_current_page(1)
            QApplication.processEvents()
            self.window.display_current_page(1)
            QApplication.processEvents()

        assert update_details.call_count == 1

    def test_display_current_page_refreshes_details_when_search_terms_change(self):
        with patch.object(ssa_gui_details, "_update_details_from_series", wraps=ssa_gui_details._update_details_from_series) as update_details:
            self.window.display_current_page(1)
            QApplication.processEvents()
            self.window.search_input.setText("Teste A")
            self.window.display_current_page(1)
            QApplication.processEvents()

        assert update_details.call_count == 2

    def test_display_current_page_rebuilds_when_page_changes(self):
        extra_rows = self.base_df.iloc[:2].copy()
        extra_rows.loc[:, "numero_ssa"] = [4, 5]
        extra_rows.loc[:, "situacao"] = ["NOV", "NOV"]
        extra_rows.loc[:, "localizacao_codigo"] = ["LOC4", "LOC5"]
        extra_rows.loc[:, "descricao_ssa"] = ["Teste D", "Teste E"]
        extra_rows.loc[:, "setor_executor"] = ["MEL4", "MEL4"]
        extra_rows.loc[:, "descricao_execucao"] = ["Exec D", "Exec E"]
        extra_rows.loc[:, "solicitante"] = ["User4", "User5"]
        paged_df = pd.concat([self.base_df, extra_rows], ignore_index=True)
        self._set_window_dataframe(paged_df, page_size=2)

        with patch.object(ssa_gui_details, "_update_details_from_series", wraps=ssa_gui_details._update_details_from_series) as update_details:
            self.window.display_current_page(1)
            QApplication.processEvents()
            self.window.display_current_page(2)
            QApplication.processEvents()

        expected_page = format_dataframe_for_display(paged_df.iloc[2:4][self.window.visible_columns].copy())
        assert update_details.call_count == 2
        assert self.window.table_widget.rowCount() == 2
        numero_ssa_col = self.window._current_display_columns.index("numero_ssa")
        assert self.window.table_widget.item(0, numero_ssa_col).text() == expected_page.iloc[0]["numero_ssa"]

    def test_display_current_page_restores_widget_batch_state_after_render(self):
        header = self.window.table_widget.horizontalHeader()
        self.window.table_widget.setSortingEnabled(True)
        self.window.table_widget.blockSignals(False)
        header.blockSignals(False)

        self.window.display_current_page(1)
        QApplication.processEvents()

        assert self.window.table_widget.isSortingEnabled() is True
        assert self.window.table_widget.signalsBlocked() is False
        assert header.signalsBlocked() is False
        assert self.window.table_widget.updatesEnabled() is True
        assert header.updatesEnabled() is True

    def test_display_current_page_updates_details_without_forcing_selection(self):
        self.window.display_current_page(1)
        QApplication.processEvents()

        assert self.window.table_widget.selectionModel().selectedRows() == []
        assert self.window._details_current_ssa == 1
        details_html = str(self.window.details_text.toHtml() or "")
        assert "Teste A" in details_html

    def test_display_current_page_can_skip_initial_details_update(self):
        with patch.object(ssa_gui_details, "_update_details_from_series", wraps=ssa_gui_details._update_details_from_series) as update_details:
            self.window.display_current_page(1, update_details=False)
            QApplication.processEvents()

        assert update_details.call_count == 0
        assert self.window.table_widget.rowCount() == len(self.base_df)
        assert self.window._details_current_ssa is None
