"""Qt scenario tests for reprogramacoes advanced filter.

GUI wiring for reprogramacoes domain contract in
test_contract_advanced_filter_domain.py.
"""

from __future__ import annotations

from PyQt6.QtWidgets import QApplication

from tests._helpers.contract_data_builders import ADV_REPROG_EQ2_SSAS
from tests._helpers.gui_scenario_harness import GUIFilterScenarioHarness


class TestScenarioAdvancedReprogramacoes(GUIFilterScenarioHarness):
    def test_reprogramacoes_filter_reduces_visible_rows(self):
        df = self.load_advanced_contract_df()
        total_rows = len(df)
        self.window._advanced_filters = {
            "num_reprogramacoes_mode": "eq",
            "num_reprogramacoes_values": ["2"],
        }
        self.window._advanced_filters_active = True
        self.window._refresh_after_filter_change()
        QApplication.processEvents()

        assert len(self.window.df_exibido) == 2
        assert len(self.window.df_exibido) < total_rows
        assert set(self.window.df_exibido["num_reprogramacoes"].tolist()) == {2}
        assert set(self.window.df_exibido["numero_ssa"].astype(int).tolist()) == ADV_REPROG_EQ2_SSAS
