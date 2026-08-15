"""Qt scenario tests for paginator slice vs table cell order.

Uses build_base_filter_df() row order (descricao_ssa Teste A..E).
Cross-ref: GUIFilterScenarioHarness.assert_table_matches_paginator_slice.
"""

from __future__ import annotations

import pytest

from tests._helpers.gui_scenario_harness import GUIFilterScenarioHarness

# build_base_filter_df() sorted by numero_ssa DESC, page_size=2.
PAGE_ONE_DESC = ["Teste E", "Teste D"]
PAGE_TWO_DESC = ["Teste C", "Teste B"]
PAGE_THREE_DESC = ["Teste A"]


class TestScenarioGridPaginatorOrder(GUIFilterScenarioHarness):
    def _bind_sorted_desc_df(self):
        df = self.base_df.sort_values("numero_ssa", ascending=False).reset_index(
            drop=True
        )
        self.bind_window_dataframes(df)
        self.window.paginator.page_size = 2
        self.window.paginator.set_dataframe(self.window.df_exibido.copy())
        self.refresh_table_page(1)

    @pytest.mark.parametrize(
        ("page", "expected_desc", "expected_row_count"),
        [
            (1, PAGE_ONE_DESC, 2),
            (2, PAGE_TWO_DESC, 2),
            (3, PAGE_THREE_DESC, 1),
        ],
    )
    def test_table_descricao_matches_paginator_slice_per_page(
        self, page: int, expected_desc: list[str], expected_row_count: int
    ):
        self._bind_sorted_desc_df()
        self.go_to_paginator_page(page)

        table_desc = self.assert_table_matches_paginator_slice("descricao_ssa")
        assert table_desc == expected_desc
        assert self.window.table_widget.rowCount() == expected_row_count
        assert self.window.paginator.current_page == page

    def test_paginator_next_button_updates_table_descricao_order(self):
        self._bind_sorted_desc_df()
        self.mouse_click(self.window.paginator.next_button)

        table_desc = self.assert_table_matches_paginator_slice("descricao_ssa")
        assert table_desc == PAGE_TWO_DESC
        assert self.window.table_widget.rowCount() == len(PAGE_TWO_DESC)
        assert self.window.paginator.current_page == 2

    def test_paginator_prev_button_returns_to_page_one(self):
        self._bind_sorted_desc_df()
        self.mouse_click(self.window.paginator.next_button)
        assert self.window.paginator.current_page == 2
        self.mouse_click(self.window.paginator.prev_button)

        table_desc = self.assert_table_matches_paginator_slice("descricao_ssa")
        assert table_desc == PAGE_ONE_DESC
        assert self.window.paginator.current_page == 1

    def test_paginator_third_page_shows_remaining_row(self):
        self._bind_sorted_desc_df()
        self.mouse_click(self.window.paginator.next_button)
        self.mouse_click(self.window.paginator.next_button)

        table_desc = self.assert_table_matches_paginator_slice("descricao_ssa")
        assert table_desc == PAGE_THREE_DESC
        assert self.window.paginator.current_page == 3
        assert self.window.table_widget.rowCount() == 1
