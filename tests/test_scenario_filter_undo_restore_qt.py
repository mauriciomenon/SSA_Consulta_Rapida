"""Qt scenario tests for filter undo restore.

GUI wiring for search source contracts in test_contract_search_undo_source.py.
"""

from __future__ import annotations

from PyQt6.QtWidgets import QApplication

from gui.ssa.filter_search_undo_controller import (
    render_restored_filter_state,
    restore_filter_column_state,
    restore_filter_search_state,
    snapshot_filter_state,
)
from tests._helpers.contract_data_builders import BASE_APV_COUNT, BASE_APV_SSAS
from tests._helpers.gui_scenario_harness import GUIFilterScenarioHarness


class TestScenarioFilterUndoRestore(GUIFilterScenarioHarness):
    def test_undo_restore_after_column_filter_recomputes_display(self):
        self.window._active_column_filters = {"situacao": "APV"}
        self.window._refresh_after_filter_change()
        QApplication.processEvents()
        apv_count = len(self.window.df_exibido)
        assert apv_count == BASE_APV_COUNT
        assert set(self.window.df_exibido["numero_ssa"].tolist()) == BASE_APV_SSAS

        saved = snapshot_filter_state(self.window)

        self.window._active_column_filters = {"situacao": "STE"}
        self.window._refresh_after_filter_change()
        QApplication.processEvents()
        assert len(self.window.df_exibido) < apv_count

        restore_filter_search_state(self.window, saved)
        restore_filter_column_state(self.window, saved)
        render_restored_filter_state(self.window, str(saved.get("search_text") or ""))
        QApplication.processEvents()

        assert self.window._active_column_filters.get("situacao") == "APV"
        assert len(self.window.df_exibido) == apv_count
        assert set(self.window.df_exibido["situacao"].tolist()) == {"APV"}
        assert all(
            str(value).strip() == "APV"
            for value in self.window.df_exibido["situacao"].tolist()
        )
