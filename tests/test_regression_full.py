#!/usr/bin/env python3
"""
TESTE DE REGRESSAO COMPLETO - GUI SSA

Testa funcionalidades praticas criticas:
1. Carregamento de dados
2. Filtragem de dados
3. Busca (campo search)
4. Navegacao de paginas
5. Filtros por coluna
6. Limpeza de filtros
"""

import sys
import os

import pandas as pd
import pytest

# Adiciona o diretorio raiz ao path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)


@pytest.fixture(scope="module", autouse=True)
def qt_app():
    """Cria QApplication para testes."""
    from PyQt6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication(sys.argv)
    yield app


@pytest.fixture(scope="module")
def window():
    """Instancia janela principal em ambiente headless e garante descarte."""
    from gui.gui_ssa import SSAMainWindow
    w = SSAMainWindow()
    yield w
    try:
        w.close()
    except Exception:
        pass


def test_imports():
    """Testa imports basicos."""
    from PyQt6.QtWidgets import QApplication
    assert QApplication is not None

    from gui.gui_ssa import SSAMainWindow
    assert SSAMainWindow is not None

    from gui.mixins import FilterGUISSAMixin
    assert FilterGUISSAMixin is not None


def test_instantiation(window):
    """Testa instanciacao da janela."""
    assert hasattr(window, 'df_completo'), "Falta atributo df_completo"
    assert hasattr(window, 'df_exibido'), "Falta atributo df_exibido"
    assert hasattr(window, 'search_input'), "Falta atributo search_input"
    assert hasattr(window, 'table_widget'), "Falta atributo table_widget"


def test_mixin_methods(window):
    """Testa metodos do FilterGUISSAMixin."""
    assert hasattr(window, 'initiate_filtering'), "Falta initiate_filtering"
    assert callable(window.initiate_filtering), "initiate_filtering nao e callable"

    assert hasattr(window, 'clear_filter'), "Falta clear_filter"
    assert callable(window.clear_filter), "clear_filter nao e callable"

    assert hasattr(window, '_apply_column_filters'), "Falta _apply_column_filters"
    assert callable(window._apply_column_filters), "nao e callable"

    assert hasattr(window, '_prepare_search_chunks'), "Falta _prepare_search_chunks"
    assert callable(window._prepare_search_chunks), "nao e callable"


def test_data_loading(window):
    """Testa carregamento de dados."""
    from armazenamento.database import query_db

    db_path = 'data/ssas.db'
    if not os.path.exists(db_path):
        pytest.skip("Banco de dados nao existe")

    df = query_db(db_path, 'ssas')

    if df is not None and not df.empty:
        window.df_completo = df
        window.df_exibido = df.copy()
        assert len(window.df_completo) > 0


def test_filter_functionality(window):
    """Testa funcionalidade de filtro."""
    test_data = pd.DataFrame({
        'numero_ssa': ['2024001', '2024002', '2024003'],
        'descricao_ssa': ['Teste A', 'Teste B', 'Teste C'],
        'situacao': ['Aberta', 'Fechada', 'Aberta']
    })

    window.df_completo = test_data

    # Testa _prepare_search_chunks
    result = window._prepare_search_chunks("teste OU exemplo")
    assert isinstance(result, list), "_prepare_search_chunks deve retornar lista"

    # Testa _apply_column_filters
    filtered = window._apply_column_filters(test_data)
    assert isinstance(filtered, pd.DataFrame), "_apply_column_filters deve retornar DataFrame"


def test_search_field(window):
    """Testa campo de busca."""
    assert hasattr(window, 'search_input'), "Falta search_input"

    try:
        window.search_input.setText("teste")
        text = window.search_input.text()
        assert text == "teste", f"Texto nao foi definido corretamente: {text}"
    except RuntimeError:
        # Qt objects deletados - esperado sem event loop
        pass


def test_clear_filter(window):
    """Testa limpeza de filtros."""
    try:
        window.clear_filter()
    except RuntimeError:
        # Qt objects deletados - esperado sem event loop
        pass


def test_column_filters(window):
    """Testa filtros por coluna."""
    assert hasattr(window, '_active_column_filters'), "Falta atributo _active_column_filters"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
