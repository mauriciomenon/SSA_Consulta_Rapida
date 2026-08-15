"""Qt scenario tests for basic label visibility and count consistency.

Cross-ref: tests/_helpers/contract_data_builders.py BASE_APV_COUNT.
Uses GUIFilterScenarioHarness.assert_count_status / extract_table_column_texts.
"""

from __future__ import annotations

from PyQt6.QtWidgets import QApplication

from tests._helpers.contract_data_builders import BASE_APV_COUNT
from tests._helpers.gui_scenario_harness import GUIFilterScenarioHarness


class TestScenarioVisualLabelsBasic(GUIFilterScenarioHarness):
    def test_filter_labels_visible_and_non_empty_after_apv_refresh(self):
        ctx = self.set_filter_panel_tab("main")
        self.window._active_column_filters = {"situacao": "APV"}
        self.window._refresh_after_filter_change()
        QApplication.processEvents()

        assert self.window.filtered_status_label.isVisible()
        assert self.window.status_label.isVisible()
        assert str(self.window.filtered_status_label.text() or "").strip() != ""
        assert ctx["search_button"].isVisible()
        assert ctx["clear_filter_button"].isVisible()
        self.assert_count_status(BASE_APV_COUNT, len(self.base_df))
        assert self.window.table_widget.rowCount() == BASE_APV_COUNT

    def test_count_label_matches_table_row_count_after_search_click(self):
        ctx = self.set_filter_panel_tab("main")
        ctx["search_input"].setText("Teste A")
        self.mouse_click(ctx["search_button"])

        filtered = len(self.window.df_exibido)
        total = len(self.window.df_completo)
        self.assert_count_status(filtered, total)
        assert self.window.table_widget.rowCount() == filtered
        assert self.extract_table_column_texts("descricao_ssa") == ["Teste A"]
