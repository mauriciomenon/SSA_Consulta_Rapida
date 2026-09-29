"""Qt scenario tests for derivada filters via real checkbox mouseClick.

Cross-ref: build_derivada_positive_contract_df(), DERIVADA_POSITIVE_* constants,
GUIFilterScenarioHarness.click_adv_checkbox.
"""

from __future__ import annotations

import pytest

from tests._helpers.contract_data_builders import (
    DERIVADA_POSITIVE_VISIBLE_SSAS,
    build_derivada_positive_contract_df,
)
from tests._helpers.gui_scenario_harness import GUIFilterScenarioHarness

DERIVADA_EMPTY_NOTICE = "Aviso: nenhuma derivada encontrada para o filtro."
DERIVADA_STE_EMPTY_NOTICE = (
    "Aviso: nenhuma derivada STE/SES encontrada para o filtro."
)


class TestScenarioDerivadaCheckboxClick(GUIFilterScenarioHarness):
    @pytest.mark.parametrize(
        ("checkbox_value", "expected_notice"),
        [
            ("has", DERIVADA_EMPTY_NOTICE),
            ("all_ste", DERIVADA_STE_EMPTY_NOTICE),
        ],
    )
    def test_derivada_checkbox_click_shows_empty_notice_without_links(
        self, checkbox_value: str, expected_notice: str
    ):
        assert (self.window.df_completo["derivada_de"].astype(str).str.strip() == "").all()
        self.setup_derivada_advanced_panel()
        self.click_adv_checkbox(prefix="adv_derivada", value=checkbox_value)

        notice_text = str(self.window.status_label.text() or "")
        assert expected_notice in notice_text
        assert len(self.window.df_exibido) == len(self.window.df_completo)
        assert self.window.table_widget.rowCount() == len(self.window.df_completo)

    def test_derivada_all_ste_checkbox_click_without_ste_derivadas(self):
        df = self.base_df.copy()
        df.loc[0, "derivada_de"] = "999900001"
        df.loc[0, "situacao"] = "APV"
        self.bind_window_dataframes(df)
        self.setup_derivada_advanced_panel()
        self.click_adv_checkbox(prefix="adv_derivada", value="all_ste")

        notice_text = str(self.window.status_label.text() or "")
        assert DERIVADA_STE_EMPTY_NOTICE in notice_text
        assert len(self.window.df_exibido) == len(df)
        assert self.window.table_widget.rowCount() == len(df)

    def test_derivada_has_checkbox_click_reduces_rows_when_link_exists(self):
        df = build_derivada_positive_contract_df()
        self.bind_window_dataframes(df)
        self.setup_derivada_advanced_panel()
        self.click_adv_checkbox(prefix="adv_derivada", value="has")

        visible_ssas = set(self.window.df_exibido["numero_ssa"].tolist())
        assert visible_ssas == DERIVADA_POSITIVE_VISIBLE_SSAS
        assert len(self.window.df_exibido) == len(DERIVADA_POSITIVE_VISIBLE_SSAS)
        assert self.window.table_widget.rowCount() == len(DERIVADA_POSITIVE_VISIBLE_SSAS)
        assert DERIVADA_EMPTY_NOTICE not in str(self.window.status_label.text() or "")
