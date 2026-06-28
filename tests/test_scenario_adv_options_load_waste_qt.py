"""Qt scenario tests for wasted heavy loads in advanced filter options.

GUI wiring for cache invalidation contracts in
test_contract_cache_content_invalidation.py.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from PyQt6.QtWidgets import QApplication

from gui.ssa.gui_filters_advanced_refresh import (
    collect_advanced_filter_option_values,
    get_cached_advanced_filter_option_values,
)
from tests._helpers.contract_data_builders import patch_adv_options_cache_spies
from tests._helpers.gui_scenario_harness import GUIFilterScenarioHarness


class TestScenarioAdvOptionsLoadWaste(GUIFilterScenarioHarness):
    def test_clean_cache_skips_full_collect_scan_on_second_refresh(self):
        self.load_advanced_contract_df()
        self.window._adv_options_dirty = False
        self.window._refresh_advanced_filter_options()
        QApplication.processEvents()

        with patch_adv_options_cache_spies() as (get_cached_spy, collect_spy):
            self.window._refresh_advanced_filter_options()
            QApplication.processEvents()

        assert get_cached_spy.call_count == 0
        get_cached_spy.assert_not_called()
        assert collect_spy.call_count == 0
        collect_spy.assert_not_called()

    def test_dirty_refresh_recomputes_instead_of_reusing_stale_exec_vals(self):
        self.load_advanced_contract_df()
        self.window._adv_options_dirty = False
        self.window._refresh_advanced_filter_options()
        QApplication.processEvents()

        self.window._adv_values_cache["exec_vals"] = ["STALE_EXEC"]
        self.window.df_completo.loc[0, "setor_executor"] = "RACE_FRESH"
        self.window._adv_options_dirty = True

        with patch_adv_options_cache_spies() as (get_cached_spy, collect_spy):
            self.window._refresh_advanced_filter_options()
            QApplication.processEvents()

        assert get_cached_spy.call_count == 1
        assert get_cached_spy.call_args.kwargs.get("force_refresh") is True
        assert collect_spy.call_count == 1
        exec_vals = list(self.window._adv_values_cache.get("exec_vals") or [])
        assert "RACE_FRESH" in exec_vals
        assert "STALE_EXEC" not in exec_vals

    def test_get_cached_without_force_refresh_returns_stale_until_dirty(self):
        self.load_advanced_contract_df()
        cache = self.window._adv_values_cache
        df = self.window.df_completo
        first = get_cached_advanced_filter_option_values(
            cache,
            df,
            data_load_token=getattr(self.window, "_data_load_token", None),
            sort_sectors=lambda values: sorted(values),
        )
        df.loc[0, "setor_executor"] = "INVISIBLE_UNTIL_DIRTY"
        collect_spy = MagicMock(wraps=collect_advanced_filter_option_values)
        with patch(
            "gui.ssa.gui_filters_advanced_refresh.collect_advanced_filter_option_values",
            collect_spy,
        ):
            second = get_cached_advanced_filter_option_values(
                cache,
                df,
                data_load_token=getattr(self.window, "_data_load_token", None),
                sort_sectors=lambda values: sorted(values),
                force_refresh=False,
            )
        assert collect_spy.call_count == 0
        collect_spy.assert_not_called()
        assert "INVISIBLE_UNTIL_DIRTY" not in second.exec_vals
        assert second.exec_vals == first.exec_vals

        collect_spy.reset_mock()
        with patch(
            "gui.ssa.gui_filters_advanced_refresh.collect_advanced_filter_option_values",
            collect_spy,
        ):
            third = get_cached_advanced_filter_option_values(
                cache,
                df,
                data_load_token=getattr(self.window, "_data_load_token", None),
                sort_sectors=lambda values: sorted(values),
                force_refresh=True,
            )
        assert collect_spy.call_count == 1
        assert "INVISIBLE_UNTIL_DIRTY" in third.exec_vals
