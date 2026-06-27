"""Qt scenario tests for derivada filter notice visibility."""

from __future__ import annotations

from unittest.mock import patch

from PyQt6.QtWidgets import QApplication

from tests._helpers.gui_scenario_harness import GUIFilterScenarioHarness


class TestScenarioDerivadaNotice(GUIFilterScenarioHarness):
    def test_derivada_empty_notice_shows_on_status_label(self):
        assert (self.window.df_completo["derivada_de"].astype(str).str.strip() == "").all()

        with patch(
            "gui.ssa.gui_filters_advanced_ui._read_advanced_filters_from_ui",
            lambda _self, _previous: {"derivada_has": True},
        ):
            self.window._apply_advanced_filters_from_ui(store_only=False)
        QApplication.processEvents()

        notice_text = self.window.status_label.text()
        count_text = self.window.filtered_status_label.text()

        assert "Aviso: nenhuma derivada encontrada para o filtro." in notice_text
        assert "SSA" in count_text
        assert "Aviso" not in count_text
        assert len(self.window.df_exibido) == len(self.window.df_completo)

    def test_derivada_all_ste_empty_notice_shows_without_mask_failure(self):
        df = self.base_df.copy()
        df.loc[0, "derivada_de"] = "999900001"
        df.loc[0, "situacao"] = "APV"
        self.window.df_completo = df.copy()
        self.window.df_exibido = df.copy()
        self.window._df_last_search_filtered = df.copy()
        self.window.paginator.set_dataframe(df.copy())

        with patch(
            "gui.ssa.gui_filters_advanced_ui._read_advanced_filters_from_ui",
            lambda _self, _previous: {"derivada_all_ste": True},
        ):
            self.window._apply_advanced_filters_from_ui(store_only=False)
        QApplication.processEvents()

        notice_text = self.window.status_label.text()
        assert "Aviso: nenhuma derivada STE/SES encontrada para o filtro." in notice_text
        assert len(self.window.df_exibido) == len(df)
