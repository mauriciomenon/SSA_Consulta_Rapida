"""Qt scenario tests for paginator slice vs table cell order.

Uses build_base_filter_df() row order (descricao_ssa Teste A..E).
Cross-ref: GUIFilterScenarioHarness.refresh_table_page / extract_table_column_texts.
"""

from __future__ import annotations

from tests._helpers.gui_scenario_harness import GUIFilterScenarioHarness

# build_base_filter_df() sorted by numero_ssa DESC, page_size=2.
PAGE_ONE_DESC = ["Teste E", "Teste D"]
PAGE_TWO_DESC = ["Teste C", "Teste B"]


class TestScenarioGridPaginatorOrder(GUIFilterScenarioHarness):
    def _bind_sorted_desc_df(self):
        df = self.base_df.sort_values("numero_ssa", ascending=False).reset_index(
            drop=True
        )
        self.bind_window_dataframes(df)
        self.window.paginator.page_size = 2
        self.window.paginator.set_dataframe(self.window.df_exibido.copy())
        self.refresh_table_page(1)

    def test_table_descricao_column_matches_paginator_slice_on_page_one(self):
        self._bind_sorted_desc_df()
        slice_df = self.window.paginator.get_current_slice()
        slice_desc = [str(value) for value in slice_df["descricao_ssa"].tolist()]
        table_desc = self.extract_table_column_texts("descricao_ssa")
        assert table_desc == slice_desc == PAGE_ONE_DESC
        assert self.window.table_widget.rowCount() == len(slice_desc)
        assert self.window.paginator.current_page == 1

    def test_paginator_next_button_updates_table_descricao_order(self):
        self._bind_sorted_desc_df()
        self.mouse_click(self.window.paginator.next_button)

        slice_df = self.window.paginator.get_current_slice()
        slice_desc = [str(value) for value in slice_df["descricao_ssa"].tolist()]
        table_desc = self.extract_table_column_texts("descricao_ssa")
        assert table_desc == slice_desc == PAGE_TWO_DESC
        assert self.window.table_widget.rowCount() == len(slice_desc)
        assert self.window.paginator.current_page == 2
