#!/usr/bin/env python3
"""
Teste de integridade da integracao do FilterGUISSAMixin.

Verifica:
1. Imports funcionam corretamente
2. Classe SSAMainWindow herda do mixin
3. Metodos do mixin estao acessiveis
4. Nao ha conflitos de metodos
"""

import sys
import os

import pytest

# Adiciona o diretorio raiz ao path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)


def test_imports():
    """Testa se todos os imports necessarios funcionam."""
    from gui.mixins import FilterGUISSAMixin
    assert FilterGUISSAMixin is not None, "FilterGUISSAMixin deve ser importavel"

    import gui.gui_ssa as gui_module
    assert gui_module is not None, "gui.gui_ssa deve ser importavel"


def test_inheritance():
    """Testa se SSAMainWindow herda corretamente do mixin."""
    from gui.gui_ssa import SSAMainWindow
    from gui.mixins import FilterGUISSAMixin

    # Verifica se FilterGUISSAMixin esta na MRO (Method Resolution Order)
    mro = SSAMainWindow.__mro__
    assert FilterGUISSAMixin in mro, "SSAMainWindow deve herdar de FilterGUISSAMixin"


def test_mixin_methods():
    """Testa se os metodos do mixin estao acessiveis."""
    from gui.gui_ssa import SSAMainWindow

    # Lista de metodos que devem estar presentes (do FilterGUISSAMixin)
    expected_methods = [
        'initiate_filtering',
        'on_filter_finished',
        'on_filter_error',
        'clear_filter',
        '_apply_column_filters',
        '_build_column_filters_panel',
        '_prepare_search_chunks',
        '_normalize_chunk_for_parse',
        '_format_search_display',
    ]

    missing_methods = []
    for method_name in expected_methods:
        if not hasattr(SSAMainWindow, method_name):
            missing_methods.append(method_name)

    assert not missing_methods, f"Metodos faltando: {', '.join(missing_methods)}"


def test_no_duplicates():
    """Verifica se nao ha metodos duplicados."""
    from gui.gui_ssa import SSAMainWindow
    from gui.mixins import FilterGUISSAMixin

    # Obtem todos os metodos do mixin
    mixin_methods = set()
    for name in dir(FilterGUISSAMixin):
        if not name.startswith('__'):
            attr = getattr(FilterGUISSAMixin, name)
            if callable(attr):
                mixin_methods.add(name)

    # Obtem todos os metodos da classe SSAMainWindow
    ssa_methods = set()
    for name in dir(SSAMainWindow):
        if not name.startswith('_') or (name.startswith('_') and not name.startswith('__')):
            attr = getattr(SSAMainWindow, name)
            if callable(attr):
                ssa_methods.add(name)

    # Verifica se os metodos do mixin estao presentes
    inherited_methods = ssa_methods.intersection(mixin_methods)
    assert len(inherited_methods) > 0, "Mixin deve ter metodos herdados por SSAMainWindow"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
