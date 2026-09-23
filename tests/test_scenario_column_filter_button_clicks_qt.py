"""Qt scenario tests for column filter row apply/clear button clicks.

Cross-ref: GUIFilterScenarioHarness.setup_column_filters_panel / mouse_click.
"""

from __future__ import annotations

from unittest.mock import patch

from gui.ssa import column_filter_panel
from tests._helpers.contract_data_builders import EXPECTED_BASE_EXECUTORS
from tests._helpers.gui_scenario_harness import GUIFilterScenarioHarness


class TestScenarioColumnFilterButtonClicks(GUIFilterScenarioHarness):
    def test_column_apply_button_click_filters_by_setor_executor(self):
        self.setup_column_filters_panel()
        term_box, apply_btn, _clear_btn = self.get_column_filter_row("setor_executor")
        term_box.setText("IEE3")
        self.mouse_click(apply_btn)

        assert self.window._active_column_filters.get("setor_executor") == "IEE3"
        assert len(self.window.df_exibido) == 1
        assert self.window.df_exibido.iloc[0]["setor_executor"] == "IEE3"
        assert self.window.table_widget.rowCount() == 1
        assert self.extract_table_column_texts("setor_executor") == ["IEE3"]

    def test_column_apply_no_match_empties_display(self):
        self.setup_column_filters_panel()
        term_box, apply_btn, _clear_btn = self.get_column_filter_row("setor_executor")
        term_box.setText("INEXISTENTE_XYZ")
        self.mouse_click(apply_btn)

        assert self.window._active_column_filters.get("setor_executor") == "INEXISTENTE_XYZ"
        assert len(self.window.df_exibido) == 0
        assert self.window.table_widget.rowCount() == 0
        assert self.extract_table_column_texts("setor_executor") == []

    def test_column_clear_button_click_removes_active_filter(self):
        self.window._active_column_filters = {"setor_executor": "IEE3"}
        self.window._refresh_after_filter_change()
        self.setup_column_filters_panel()

        term_box, _apply_btn, clear_btn = self.get_column_filter_row("setor_executor")
        assert str(term_box.text() or "").strip() == "IEE3"
        self.mouse_click(clear_btn)

        assert self.window._active_column_filters.get("setor_executor", "") == ""
        assert len(self.window.df_exibido) == len(self.base_df)
        assert self.window.table_widget.rowCount() == len(self.base_df)
        slice_exec = self.extract_slice_column_texts("setor_executor")
        assert self.extract_table_column_texts("setor_executor") == slice_exec
        assert set(slice_exec) == set(EXPECTED_BASE_EXECUTORS)

    def test_column_clear_when_already_empty_is_noop(self):
        self.setup_column_filters_panel()
        _term_box, _apply_btn, clear_btn = self.get_column_filter_row("setor_executor")
        count_before = len(self.window.df_exibido)
        table_before = self.extract_table_column_texts("setor_executor")

        self.mouse_click(clear_btn)

        assert len(self.window.df_exibido) == count_before
        assert self.extract_table_column_texts("setor_executor") == table_before

    def test_column_apply_click_rebuilds_panel_once_per_action(self):
        self.setup_column_filters_panel()
        with patch.object(
            column_filter_panel,
            "build_column_filters_panel",
            wraps=column_filter_panel.build_column_filters_panel,
        ) as rebuild_spy:
            term_box, apply_btn, _clear_btn = self.get_column_filter_row("setor_executor")
            term_box.setText("IEE3")
            self.mouse_click(apply_btn)

        assert rebuild_spy.call_count == 1
