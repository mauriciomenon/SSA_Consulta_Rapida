"""Qt scenario tests for visual filter state and column headers."""

from __future__ import annotations

from PyQt6.QtWidgets import QApplication

from tests._helpers.gui_scenario_harness import GUIFilterScenarioHarness


class TestScenarioVisualFilterState(GUIFilterScenarioHarness):
    def test_ano_execucao_filter_marks_semana_executada_header(self):
        """Default advanced DF keeps all rows when filtering ano_execucao 2025.

        build_advanced_filter_contract_df sets semana_executada to 202501-202504.
        Year 2025 therefore matches every row while marking semana_executada [f].
        Row reduction with mixed years is covered by test_ano_execucao_filter_reduces_visible_rows.
        """
        self.load_advanced_contract_df()
        if "semana_executada" not in self.window.visible_columns:
            self.window.visible_columns.append("semana_executada")
        self.set_filter_panel_tab("advanced")

        self.toggle_advanced_multiselect_value(
            prefix="adv_year_execucao",
            value="2025",
        )
        self.window.display_current_page(1)
        QApplication.processEvents()

        assert "semana_executada" in self.window._get_visual_filter_columns()
        header_index = self.window._current_display_columns.index("semana_executada")
        header_text = str(
            self.window.table_widget.horizontalHeaderItem(header_index).text() or ""
        )
        assert header_text.startswith("[f] ")
        assert self.window._advanced_filters.get("ano_execucao_values") == ["2025"]
        assert set(self.window.df_exibido["numero_ssa"].astype(int).tolist()) == {
            202600001,
            202600002,
            202600003,
            202600004,
        }

    def test_column_filter_marks_matching_header(self):
        if "situacao" not in self.window.visible_columns:
            self.window.visible_columns.append("situacao")
        self.window._active_column_filters["situacao"] = "APV"
        self.window._refresh_after_filter_change()
        QApplication.processEvents()
        self.window.display_current_page(1)
        QApplication.processEvents()

        assert "situacao" in self.window._get_visual_filter_columns()
        header_index = self.window._current_display_columns.index("situacao")
        header_text = str(
            self.window.table_widget.horizontalHeaderItem(header_index).text() or ""
        )
        assert header_text.startswith("[f] ")

    def test_execucao_filter_does_not_mark_semana_programada_header(self):
        self.load_advanced_contract_df()
        if "semana_programada" not in self.window.visible_columns:
            self.window.visible_columns.append("semana_programada")
        if "semana_executada" not in self.window.visible_columns:
            self.window.visible_columns.append("semana_executada")
        self.set_filter_panel_tab("advanced")

        self.toggle_advanced_multiselect_value(
            prefix="adv_year_execucao",
            value="2025",
        )
        self.window.display_current_page(1)
        QApplication.processEvents()

        assert "semana_executada" in self.window._get_visual_filter_columns()
        programada_index = self.window._current_display_columns.index(
            "semana_programada"
        )
        programada_header = str(
            self.window.table_widget.horizontalHeaderItem(programada_index).text()
            or ""
        )
        assert not programada_header.startswith("[f] ")

    def test_ano_execucao_filter_reduces_visible_rows(self):
        """Mixed semana_executada years make ano_execucao 2025 return a strict subset."""
        df = self.load_advanced_contract_df()
        df.loc[0, "semana_executada"] = 202501
        df.loc[1, "semana_executada"] = 202602
        df.loc[2, "semana_executada"] = 202703
        df.loc[3, "semana_executada"] = 202804
        self.window.df_completo = df.copy()
        self.window.df_exibido = df.copy()
        self.window._df_last_search_filtered = df.copy()
        self.window.paginator.set_dataframe(df.copy())
        self.set_filter_panel_tab("advanced")

        self.toggle_advanced_multiselect_value(
            prefix="adv_year_execucao",
            value="2025",
        )
        self.window.display_current_page(1)
        QApplication.processEvents()

        visible = set(self.window.df_exibido["numero_ssa"].astype(int).tolist())
        assert visible == {202600001}
        assert len(visible) < len(df)
