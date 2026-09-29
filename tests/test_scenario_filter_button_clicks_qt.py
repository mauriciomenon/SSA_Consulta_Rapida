"""Qt scenario tests using real widget clicks for search bar actions.

Cross-ref: tests/_helpers/contract_data_builders.py (BASE_APV_* constants).
"""

from __future__ import annotations

from PyQt6.QtWidgets import QApplication

from gui.ssa.filter_search_undo_controller import safe_store_last_filter_state
from tests._helpers.contract_data_builders import BASE_APV_COUNT, BASE_APV_SSAS
from tests._helpers.gui_scenario_harness import GUIFilterScenarioHarness


class TestScenarioFilterButtonClicks(GUIFilterScenarioHarness):
    def test_search_apply_button_click_filters_display(self):
        ctx = self.set_filter_panel_tab("main")
        ctx["search_input"].setText("Teste A")
        self.mouse_click(ctx["search_button"])

        assert len(self.window.df_exibido) == 1
        assert self.window.df_exibido.iloc[0]["descricao_ssa"] == "Teste A"
        assert self.extract_table_column_texts("descricao_ssa") == ["Teste A"]
        assert self.window.table_widget.rowCount() == 1

    def test_search_apply_with_no_match_empties_display(self):
        ctx = self.set_filter_panel_tab("main")
        ctx["search_input"].setText("TermoInexistenteXYZ")
        self.mouse_click(ctx["search_button"])

        assert len(self.window.df_exibido) == 0
        assert self.extract_table_column_texts("descricao_ssa") == []
        assert self.window.table_widget.rowCount() == 0
        self.assert_count_status(0, len(self.base_df))

    def test_clear_search_button_click_clears_active_search(self):
        ctx = self.set_filter_panel_tab("main")
        ctx["search_input"].setText("Teste A")
        self.mouse_click(ctx["search_button"])
        assert len(self.window.df_exibido) == 1

        self.mouse_click(ctx["clear_filter_button"])

        assert ctx["search_input"].text().strip() == ""
        assert len(self.window.df_exibido) == len(self.base_df)
        assert ctx["clear_filter_button"].isEnabled() is False
        assert self.window.table_widget.rowCount() == len(self.base_df)
        assert set(self.extract_table_column_texts("descricao_ssa")) == set(
            self.base_df["descricao_ssa"].astype(str).tolist()
        )

    def test_undo_button_click_restores_prior_column_filter(self):
        self.window._active_column_filters = {"situacao": "APV"}
        self.window._refresh_after_filter_change()
        QApplication.processEvents()
        assert len(self.window.df_exibido) == BASE_APV_COUNT

        safe_store_last_filter_state(self.window, reason="button-click-test")

        self.window._active_column_filters = {"situacao": "STE"}
        self.window._refresh_after_filter_change()
        QApplication.processEvents()
        assert len(self.window.df_exibido) == 1

        self.mouse_click(self.window.undo_filter_btn)

        assert self.window._active_column_filters.get("situacao") == "APV"
        assert set(self.window.df_exibido["numero_ssa"].tolist()) == BASE_APV_SSAS
        self.assert_count_status(BASE_APV_COUNT, len(self.base_df))

    def test_filter_panel_tab_click_preserves_search_input(self):
        ctx = self.set_filter_panel_tab("main")
        ctx["search_input"].setText("Teste A")
        self.mouse_click(ctx["search_button"])
        assert len(self.window.df_exibido) == 1
        assert self.extract_table_column_texts("descricao_ssa") == ["Teste A"]

        filters_ctx = self.set_filter_panel_tab("filters")
        assert filters_ctx["search_input"].text() == "Teste A"

        main_ctx = self.set_filter_panel_tab("main")
        assert main_ctx["search_input"].text() == "Teste A"
        assert len(self.window.df_exibido) == 1
        assert self.extract_table_column_texts("descricao_ssa") == ["Teste A"]
