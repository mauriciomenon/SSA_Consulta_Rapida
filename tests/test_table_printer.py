# tests/test_table_printer.py
"""
Testes unitários para o módulo interface.table_printer.
"""

import pytest
import pandas as pd
import os
import sys
from io import StringIO
from unittest.mock import patch, MagicMock

# Adiciona a raiz do projeto ao path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

from interface.table_printer import (
    get_terminal_size,
    _estimate_column_width,
    _select_columns_for_width,
    paginate_dataframe,
    pretty_print_df
)

# --- Fixtures ---

@pytest.fixture
def sample_dataframe():
    """Cria um DataFrame de exemplo para testes."""
    data = {
        'numero_ssa': [2025001, 2025002, 2025003],
        'setor_executor': ['IEE3', 'MEL3', 'IEQ1'],
        'situacao': ['APG', 'ADM', 'SCA'],
        'descricao_ssa': [
            'Descricao curta 1',
            'Descricao mais longa que precisa ser truncada para caber na tela',
            'Outra descricao'
        ],
        'data_cadastro': ['01/01/2025', '15/03/2025', '20/05/2025'],
        'semana_cadastro': [202501, 202511, 202520],
        'semana_programada': [202502, 202512, 202521],
        'descricao_execucao': [
            'Exec curta',
            'Execucao detalhada que tambem pode ser muito longa e precisa ser truncada',
            'Exec padrao'
        ],
        'setor_emissor': ['S1', 'S2', 'S3'],
        'derivada_de': ['-', '2024001', '-'],
        'valor_numerico': [100, 200.5, 300]
    }
    return pd.DataFrame(data)

@pytest.fixture
def display_map():
    """Mapa de exibição de exemplo."""
    return {
        'numero_ssa': 'Nº SSA',
        'setor_executor': 'Executor',
        'situacao': 'Situação',
        'descricao_ssa': 'Descrição da SSA',
        'data_cadastro': 'Data Cadastro',
        'semana_cadastro': 'Sem. Cadastro',
        'semana_programada': 'Sem. Programada',
        'descricao_execucao': 'Descrição Execução',
        'setor_emissor': 'Emissor',
        'derivada_de': 'Derivada de',
        'valor_numerico': 'Valor'
    }

@pytest.fixture
def sample_settings():
    """Configurações de exemplo."""
    return {
        "display_settings": {
            "column_visibility": {
                "#": True,
                "Nº SSA": True,
                "Executor": True,
                "Situação": True,
                "Descrição da SSA": True,
                "Data Cadastro": True,
                "Sem. Cadastro": True,
                "Sem. Programada": True,
                "Descrição Execução": True,
                "Emissor": True,
                "Derivada de": True,
                "Valor": True
            },
            "column_widths": {
                "Nº SSA": 9,
                "Executor": 8,
                "Situação": 10
            },
            "max_auto_scroll_pages": 2
        },
        "user_preferences": {
            "auto_scroll_to_end": False
        },
        "default_filters": []
    }

# --- Testes para funções auxiliares ---

def test_get_terminal_size():
    """Testa a função get_terminal_size."""
    lines, cols = get_terminal_size()
    assert isinstance(lines, int)
    assert isinstance(cols, int)
    assert lines > 0
    assert cols > 0

def test_estimate_column_width(sample_dataframe):
    """Testa a função _estimate_column_width."""
    # Teste com coluna de texto
    width = _estimate_column_width(sample_dataframe['descricao_ssa'], 'Descrição da SSA')
    assert isinstance(width, int)
    assert width > 0
    assert width <= 70  # Limite máximo definido na função

    # Teste com coluna numérica
    width_num = _estimate_column_width(sample_dataframe['numero_ssa'], 'Nº SSA')
    assert isinstance(width_num, int)
    assert width_num > 0

def test_select_columns_for_width(sample_dataframe, display_map):
    """Testa a função _select_columns_for_width."""
    essential_cols = ['numero_ssa', 'setor_executor', 'situacao']
    priority_order = ['descricao_ssa', 'data_cadastro']
    
    # Teste com largura suficiente para todas
    selected = _select_columns_for_width(
        sample_dataframe, display_map, 200, essential_cols, priority_order
    )
    # Deve incluir '#' e todas as colunas essenciais e prioritárias
    assert '#' in selected
    for col in essential_cols:
        assert col in selected

    # Teste com largura limitada
    selected_limited = _select_columns_for_width(
        sample_dataframe, display_map, 50, essential_cols, priority_order
    )
    # Deve incluir '#' e pelo menos uma coluna de dados
    assert '#' in selected_limited
    assert len(selected_limited) >= 2  # '#' + pelo menos 1 coluna de dados

def test_paginate_dataframe(sample_dataframe):
    """Testa a função paginate_dataframe."""
    pages = list(paginate_dataframe(sample_dataframe, 2))
    assert len(pages) == 2
    assert len(pages[0]) == 2
    assert len(pages[1]) == 1

    # Teste com DataFrame vazio
    empty_df = pd.DataFrame()
    empty_pages = list(paginate_dataframe(empty_df, 5))
    assert len(empty_pages) == 0

# --- Testes para pretty_print_df ---

@patch('interface.table_printer.get_terminal_size')
def test_pretty_print_df_empty_dataframe(mock_get_terminal_size, display_map, sample_settings):
    """Testa pretty_print_df com DataFrame vazio."""
    mock_get_terminal_size.return_value = (25, 80)
    empty_df = pd.DataFrame()
    
    # Captura a saída padrão
    with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
        pretty_print_df(empty_df, display_map, sample_settings)
        output = mock_stdout.getvalue()
    
    assert "Nenhum resultado para exibir." in output

@patch('interface.table_printer.get_terminal_size')
def test_pretty_print_df_normal_flow(mock_get_terminal_size, sample_dataframe, display_map, sample_settings):
    """Testa o fluxo normal de pretty_print_df."""
    mock_get_terminal_size.return_value = (10, 120)  # Terminal pequeno para forçar paginação
    
    # Configura input simulado para navegar pelas páginas
    with patch('builtins.input', side_effect=['', 'q']):  # Enter, depois 'q'
        with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
            pretty_print_df(sample_dataframe, display_map, sample_settings)
            output = mock_stdout.getvalue()
    
    # Verifica se a saída contém elementos esperados
    assert "Nº SSA" in output
    assert "IEE3" in output
    assert "Descricao curta" in output
    assert "Página 1 de" in output
    assert "...exibição interrompida." in output

@patch('interface.table_printer.get_terminal_size')
def test_pretty_print_df_auto_scroll(mock_get_terminal_size, sample_dataframe, display_map, sample_settings):
    """Testa pretty_print_df com auto_scroll habilitado."""
    mock_get_terminal_size.return_value = (10, 120)
    
    # Configurações com auto_scroll ativado
    settings_auto_scroll = sample_settings.copy()
    settings_auto_scroll["user_preferences"]["auto_scroll_to_end"] = True
    
    # Como o número de páginas será baixo (3 linhas / 5 linhas por página = 1 página),
    # o auto_scroll deve funcionar
    with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
        pretty_print_df(sample_dataframe, display_map, settings_auto_scroll)
        output = mock_stdout.getvalue()
    
    # Com auto_scroll e poucas páginas, não deve pedir input
    assert "Nº SSA" in output
    assert "Descricao curta" in output
    # Não deve ter prompts de paginação se couber em poucas páginas
    # (isso pode variar com base na lógica interna)
