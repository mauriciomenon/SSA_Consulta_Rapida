"""Qt scenario tests for responsavel advanced-filter menu population.

GUI wiring for responsavel ranking contracts in
test_contract_responsavel_options_budget.py.
"""

from __future__ import annotations

from PyQt6.QtWidgets import QApplication, QLabel

from tests._helpers.contract_data_builders import EXPECTED_RESP_EXEC_ORDER
from tests._helpers.gui_scenario_harness import GUIFilterScenarioHarness


def _check_values(window, attr_name: str) -> list[str]:
    checks = getattr(window, attr_name, []) or []
    return [str(check.property("value") or "") for check in checks]


class TestScenarioResponsavelOptions(GUIFilterScenarioHarness):
    def _refresh_responsavel_execucao_menu(self) -> None:
        self.load_advanced_contract_df()
        self.set_filter_panel_tab("advanced")
        self.window._refresh_responsavel_options(
            target_prefixes={"adv_responsavel_execucao"}
        )
        QApplication.processEvents()

    def test_responsavel_execucao_checks_follow_sector_rank_in_gui(self):
        self._refresh_responsavel_execucao_menu()

        menu = getattr(self.window, "adv_responsavel_execucao_menu", None)
        checks_attr = "adv_responsavel_execucao_checks"
        assert menu is not None
        ordered_persons = _check_values(self.window, checks_attr)
        assert ordered_persons == EXPECTED_RESP_EXEC_ORDER

    def test_responsavel_execucao_menu_displays_sector_prefixed_labels(self):
        self._refresh_responsavel_execucao_menu()

        menu = getattr(self.window, "adv_responsavel_execucao_menu", None)
        assert menu is not None
        label_texts = [
            str(label.text() or "")
            for label in menu.findChildren(QLabel)
            if str(label.text() or "").strip()
        ]

        assert label_texts == [
            "Responsavel Execucao",
            "Incluir",
            "Excluir",
            "IEE3 - Exec B",
            "MEL4 - Exec C",
            "ABC - Exec A",
            "Selecionar tudo",
            "Limpar tudo",
        ]
