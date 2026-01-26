"""
Testes especificos para lazy loading de filtros com buffer de 50 SSAs.
Testa as mudancas implementadas em 2026-01-13.
"""

import inspect
import sys
from pathlib import Path

import pandas as pd
import pytest

# Adicionar path do projeto
sys.path.insert(0, str(Path(__file__).parent.parent))

from gui.gui_ssa import SSAMainWindow


class TestFilterLazyLoadingMethods:
    """Testes para verificar existencia e assinatura dos novos metodos."""

    def test_new_methods_exist(self):
        """Verifica se os novos metodos existem na classe."""
        assert hasattr(SSAMainWindow, "_mark_filters_dirty")
        assert hasattr(SSAMainWindow, "_clear_filters_dirty")
        assert hasattr(SSAMainWindow, "_populate_filter_buffer")
        assert hasattr(SSAMainWindow, "_populate_full_filter_cache")

    def test_methods_are_callable(self):
        """Verifica se os metodos sao chamavel."""
        assert callable(getattr(SSAMainWindow, "_mark_filters_dirty"))
        assert callable(getattr(SSAMainWindow, "_clear_filters_dirty"))
        assert callable(getattr(SSAMainWindow, "_populate_filter_buffer"))
        assert callable(getattr(SSAMainWindow, "_populate_full_filter_cache"))

    def test_update_multiselect_button_has_suffix_param(self):
        """Verifica se _update_multiselect_button aceita parametro suffix."""
        sig = inspect.signature(SSAMainWindow._update_multiselect_button)
        params = list(sig.parameters.keys())

        assert "suffix" in params, (
            "Parametro 'suffix' deve existir em _update_multiselect_button"
        )

        # Verificar valor padrao
        assert sig.parameters["suffix"].default == "", (
            "Parametro 'suffix' deve ter default ''"
        )

    def test_populate_filter_buffer_signature(self):
        """Verifica assinatura do metodo _populate_filter_buffer."""
        sig = inspect.signature(SSAMainWindow._populate_filter_buffer)
        params = list(sig.parameters.keys())

        # Deve aceitar apenas self
        assert len(params) == 1
        assert params[0] == "self"

    def test_populate_full_filter_cache_signature(self):
        """Verifica assinatura do metodo _populate_full_filter_cache."""
        sig = inspect.signature(SSAMainWindow._populate_full_filter_cache)
        params = list(sig.parameters.keys())

        # Deve aceitar self e filter_type
        assert len(params) == 2
        assert params[0] == "self"
        assert params[1] == "filter_type"

        # filter_type deve ter type hint str
        assert sig.parameters["filter_type"].annotation == str


class TestFilterLogicIntegration:
    """Testes de integracao para logica de filtros."""

    def test_module_imports_successfully(self):
        """Verifica se modulo pode ser importado sem erros."""
        from gui import gui_ssa

        assert hasattr(gui_ssa, "SSAMainWindow")

    def test_class_can_be_referenced(self):
        """Verifica se classe pode ser referenciada."""
        assert SSAMainWindow is not None
        assert SSAMainWindow.__name__ == "SSAMainWindow"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
