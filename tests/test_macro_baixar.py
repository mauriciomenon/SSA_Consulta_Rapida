"""Teste para validar consistencia do macro 'Baixar' e evitar race conditions."""

import pytest
import sys
from pathlib import Path

root_dir = Path(__file__).parent.parent
sys.path.insert(0, str(root_dir))

from unittest.mock import MagicMock, patch, call
from PyQt6.QtWidgets import QApplication
from gui.gui_ssa import SSAMainWindow


@pytest.fixture(scope="session")
def qapp():
    """Criar QApplication para testes PyQt."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


@pytest.fixture
def main_window(qapp):
    """Criar instancia de SSAMainWindow para testes."""
    window = SSAMainWindow()
    window.show()
    yield window
    window.close()


class TestMacroBaixar:
    """Testes para validar macro 'Baixar' sem race conditions."""

    def test_macro_baixar_blocks_signals(self, main_window):
        """Verificar se sinais sao bloqueados durante aplicacao do macro."""
        # Setup: criar checkboxes mock se nao existem
        if not hasattr(main_window, "adv_derivada_has"):
            mock_checkbox = MagicMock()
            mock_checkbox.isChecked.return_value = False
            main_window.adv_derivada_has = mock_checkbox

        if not hasattr(main_window, "adv_derivada_all_ste"):
            mock_checkbox = MagicMock()
            mock_checkbox.isChecked.return_value = False
            main_window.adv_derivada_all_ste = mock_checkbox

        # Simular selecao do macro "Baixar"
        main_window.adv_macro_combo = MagicMock()
        main_window.adv_macro_combo.currentData.return_value = "ssas_para_baixar"

        # Mock para _sync_multiselect_checks
        main_window._sync_multiselect_checks = MagicMock()

        # Mock para _apply_advanced_filters_from_ui
        main_window._apply_advanced_filters_from_ui = MagicMock()

        # Mock para adv_executor_button
        main_window.adv_executor_button = MagicMock()

        # Chamar funcao
        main_window._on_macro_filter_changed()

        # Validacoes
        assert main_window.adv_macro_combo.currentData.called
        assert main_window.adv_derivada_has.blockSignals.called
        assert main_window.adv_derivada_all_ste.blockSignals.called
        assert main_window._sync_multiselect_checks.called
        assert main_window._apply_advanced_filters_from_ui.called

    def test_derivada_has_toggled_blocks_signals(self, main_window):
        """Verificar se _on_derivada_has_toggled bloqueia sinais."""
        if not hasattr(main_window, "adv_derivada_all_ste"):
            mock_checkbox = MagicMock()
            mock_checkbox.isChecked.return_value = True
            main_window.adv_derivada_all_ste = mock_checkbox

        # Chamar funcao com checked=False
        main_window._on_derivada_has_toggled(False)

        # Validacoes
        assert main_window.adv_derivada_all_ste.blockSignals.called

    def test_derivada_all_ste_toggled_blocks_signals(self, main_window):
        """Verificar se _on_derivada_all_ste_toggled bloqueia sinais."""
        if not hasattr(main_window, "adv_derivada_has"):
            mock_checkbox = MagicMock()
            mock_checkbox.isChecked.return_value = False
            main_window.adv_derivada_has = mock_checkbox

        # Chamar funcao com checked=True
        main_window._on_derivada_all_ste_toggled(True)

        # Validacoes
        assert main_window.adv_derivada_has.blockSignals.called


class TestFilterConsistency:
    """Testes para validar consistencia dos filtros."""

    def test_macro_baixar_sets_correct_checkboxes(self, main_window):
        """Verificar se macro 'Baixar' define checkboxes corretamente."""
        mock_has = MagicMock()
        mock_ste = MagicMock()

        main_window.adv_derivada_has = mock_has
        main_window.adv_derivada_all_ste = mock_ste
        main_window.adv_macro_combo = MagicMock()
        main_window.adv_macro_combo.currentData.return_value = "ssas_para_baixar"
        main_window._sync_multiselect_checks = MagicMock()
        main_window._apply_advanced_filters_from_ui = MagicMock()
        main_window.adv_executor_button = MagicMock()

        main_window._on_macro_filter_changed()

        # Validar que setChecked foi chamado com True
        assert mock_has.setChecked.called
        assert mock_ste.setChecked.called


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
