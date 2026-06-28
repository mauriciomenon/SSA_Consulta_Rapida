"""Qt scenario tests for derivada filters via real checkbox mouseClick.

Cross-ref: build_base_filter_df() derivada_de column (empty by default).
Uses GUIFilterScenarioHarness.setup_derivada_advanced_panel / mouse_click.
"""

from __future__ import annotations

from tests._helpers.gui_scenario_harness import GUIFilterScenarioHarness


class TestScenarioDerivadaCheckboxClick(GUIFilterScenarioHarness):
    def _click_adv_checkbox(self, *, prefix: str, value: str):
        checks = getattr(self.window, f"{prefix}_checks", []) or []
        target = next(
            check for check in checks if str(check.property("value") or "") == value
        )
        assert target.isEnabled(), f"checkbox {value!r} disabled"
        self.mouse_click(target)
        assert target.isChecked() is True
        self.wait_until_timer_inactive(self.window._advanced_apply_timer)
        return target

    def test_derivada_has_checkbox_click_shows_empty_notice(self):
        assert (self.window.df_completo["derivada_de"].astype(str).str.strip() == "").all()
        self.setup_derivada_advanced_panel()
        self._click_adv_checkbox(prefix="adv_derivada", value="has")

        notice_text = str(self.window.status_label.text() or "")
        assert "Aviso: nenhuma derivada encontrada para o filtro." in notice_text
        assert len(self.window.df_exibido) == len(self.window.df_completo)
        assert self.window.table_widget.rowCount() == len(self.window.df_completo)

    def test_derivada_all_ste_checkbox_click_without_ste_derivadas(self):
        df = self.base_df.copy()
        df.loc[0, "derivada_de"] = "999900001"
        df.loc[0, "situacao"] = "APV"
        self.bind_window_dataframes(df)
        self.setup_derivada_advanced_panel()
        self._click_adv_checkbox(prefix="adv_derivada", value="all_ste")

        notice_text = str(self.window.status_label.text() or "")
        assert "Aviso: nenhuma derivada STE/SES encontrada para o filtro." in notice_text
        assert len(self.window.df_exibido) == len(df)
        assert self.window.table_widget.rowCount() == len(df)
