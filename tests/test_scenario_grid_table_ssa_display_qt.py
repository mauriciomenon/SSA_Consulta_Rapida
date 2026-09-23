"""Qt scenario tests for numero_ssa cells in table vs paginator slice.

Cross-ref: contract_data_builders ADV_SSA_* constants,
GUIFilterScenarioHarness.assert_table_matches_paginator_slice.
"""

from __future__ import annotations

import pytest

from tests._helpers.contract_data_builders import (
    ADV_SSA_PAGE1_TEXTS,
    ADV_SSA_PAGE2_TEXTS,
    build_advanced_filter_contract_df,
)
from tests._helpers.gui_scenario_harness import GUIFilterScenarioHarness


class TestScenarioGridTableSsaDisplay(GUIFilterScenarioHarness):
    def _bind_adv_desc_sorted(self):
        df = build_advanced_filter_contract_df().sort_values(
            "numero_ssa", ascending=False
        ).reset_index(drop=True)
        self.bind_window_dataframes(df)
        self.window.paginator.page_size = 2
        self.window.paginator.set_dataframe(self.window.df_exibido.copy())

    @pytest.mark.parametrize(
        ("page", "expected_ssas"),
        [
            (1, ADV_SSA_PAGE1_TEXTS),
            (2, ADV_SSA_PAGE2_TEXTS),
        ],
    )
    def test_table_numero_ssa_matches_paginator_slice_per_page(
        self, page: int, expected_ssas: list[str]
    ):
        self._bind_adv_desc_sorted()
        self.go_to_paginator_page(page)

        table_ssas = self.assert_table_matches_paginator_slice("numero_ssa")
        assert table_ssas == expected_ssas
        assert all(len(value) >= 5 for value in table_ssas)

    def test_table_numero_ssa_mismatch_would_fail_slice_contract(self):
        """Regression guard: table must not show page-1 SSAs while on page 2."""
        self._bind_adv_desc_sorted()
        self.go_to_paginator_page(2)

        table_ssas = self.assert_table_matches_paginator_slice("numero_ssa")
        assert table_ssas == ADV_SSA_PAGE2_TEXTS
        assert ADV_SSA_PAGE1_TEXTS[0] not in table_ssas
