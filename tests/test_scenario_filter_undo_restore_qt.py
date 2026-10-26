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


class TestScenarioFilterUndoHistory(GUIFilterScenarioHarness):
    """BL-49: Desfazer guarda ate 10 estados anteriores (como o app C++)."""

    def _apply_situacao(self, value: str) -> None:
        self.window._safe_store_last_filter_state("test_history")
        self.window._active_column_filters["situacao"] = value
        self.window._refresh_after_filter_change()
        QApplication.processEvents()

    def _undo(self) -> None:
        self.window._restore_last_filter_state()
        QApplication.processEvents()

    def test_three_changes_undo_back_in_order_then_button_disables(self):
        self.window._last_filter_state = None
        self._apply_situacao("APV")
        self._apply_situacao("STE")
        self._apply_situacao("SCA")
        assert self.window.undo_filter_btn.isEnabled()

        self._undo()
        assert self.window._active_column_filters.get("situacao") == "STE"
        assert self.window.undo_filter_btn.isEnabled()
        self._undo()
        assert self.window._active_column_filters.get("situacao") == "APV"
        assert self.window.undo_filter_btn.isEnabled()
        self._undo()
        assert not str(self.window._active_column_filters.get("situacao", "")).strip()
        assert self.window._last_filter_state is None
        assert not self.window.undo_filter_btn.isEnabled()

    def test_eleventh_change_drops_oldest_state(self):
        self.window._last_filter_state = None
        for index in range(11):
            self._apply_situacao(f"V{index}")
        undone = 0
        while self.window._last_filter_state is not None:
            self._undo()
            undone += 1
        assert undone == 10
        # O estado inicial (sem filtro) foi descartado: o mais antigo restante e V0.
        assert self.window._active_column_filters.get("situacao") == "V0"

    def test_identical_consecutive_state_is_not_pushed_twice(self):
        self.window._last_filter_state = None
        self.window._safe_store_last_filter_state("test_repeat")
        self._apply_situacao("APV")
        self.window._safe_store_last_filter_state("test_repeat")
        self.window._active_column_filters["situacao"] = "STE"
        self.window._refresh_after_filter_change()
        QApplication.processEvents()

        self._undo()
        assert self.window._active_column_filters.get("situacao") == "APV"
        self._undo()
        assert not str(self.window._active_column_filters.get("situacao", "")).strip()
        assert self.window._last_filter_state is None

    def test_data_reload_reset_clears_history(self):
        self.window._last_filter_state = None
        self._apply_situacao("APV")
        self._apply_situacao("STE")
        self.window._hard_reset_filters_state()
        QApplication.processEvents()
        assert self.window._last_filter_state is None
        assert not self.window.undo_filter_btn.isEnabled()
