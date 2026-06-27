"""Qt scenario tests for advanced options dirty gate and force_refresh."""

from __future__ import annotations

from unittest.mock import patch

from PyQt6.QtWidgets import QApplication

from gui.ssa.gui_filters_advanced_refresh import get_cached_advanced_filter_option_values
from tests._helpers.gui_scenario_harness import GUIFilterScenarioHarness


class TestScenarioAdvOptionsDirtyGate(GUIFilterScenarioHarness):
    def test_dirty_gate_forces_refresh_on_options_read(self):
        self.load_advanced_contract_df()
        self.window._adv_options_dirty = True
        self.window._adv_values_cache = {}

        with patch(
            "gui.ssa.gui_filters_advanced_ui.get_cached_advanced_filter_option_values",
            wraps=get_cached_advanced_filter_option_values,
        ) as wrapped:
            self.window._refresh_advanced_filter_options()
            QApplication.processEvents()

        assert wrapped.call_count >= 1
        assert wrapped.call_args.kwargs.get("force_refresh") is True
        assert self.window._adv_options_dirty is False

    def test_clean_gate_reuses_cached_option_values(self):
        self.load_advanced_contract_df()
        self.window._adv_options_dirty = False
        self.window._adv_values_cache = {}

        first_exec_vals = None
        with patch(
            "gui.ssa.gui_filters_advanced_ui.get_cached_advanced_filter_option_values",
            wraps=get_cached_advanced_filter_option_values,
        ) as wrapped:
            self.window._refresh_advanced_filter_options()
            QApplication.processEvents()
            first_exec_vals = list(self.window._adv_values_cache.get("exec_vals") or [])
            wrapped.reset_mock()
            self.window._refresh_advanced_filter_options()
            QApplication.processEvents()

        assert wrapped.call_count >= 1
        assert wrapped.call_args.kwargs.get("force_refresh") is False
        assert first_exec_vals

    def test_inplace_mutation_requires_dirty_for_fresh_options(self):
        self.load_advanced_contract_df()
        self.window._adv_options_dirty = False
        self.window._refresh_advanced_filter_options()
        QApplication.processEvents()
        before = list(self.window._adv_values_cache.get("exec_vals") or [])

        self.window.df_completo.loc[0, "setor_executor"] = "ZZZ9"
        self.window._adv_options_dirty = True
        self.window._refresh_advanced_filter_options()
        QApplication.processEvents()
        after = list(self.window._adv_values_cache.get("exec_vals") or [])

        assert before != after
        assert "ZZZ9" in after

    def test_advanced_options_under_active_search_use_df_completo(self):
        self.load_advanced_contract_df()
        self.window.df_completo.loc[3, "setor_executor"] = "ZZZ9"

        search_subset = self.window.df_completo.iloc[[0]].copy()
        self.window._df_last_search_filtered = search_subset
        self.window._active_filter_search_display = "Teste A"
        self.window.search_input.setText("Teste A")
        self.window.df_exibido = search_subset.copy()

        assert "ZZZ9" not in self.window.df_exibido["setor_executor"].tolist()
        assert "ZZZ9" in self.window.df_completo["setor_executor"].tolist()

        self.window._adv_options_dirty = True
        self.window._refresh_advanced_filter_options()
        QApplication.processEvents()

        exec_vals = list(self.window._adv_values_cache.get("exec_vals") or [])
        assert "ZZZ9" in exec_vals
