# tests/test_display.py
"""
Testes unitários para o módulo interface.display.
"""

import pytest
import pandas as pd
import sys
import os
from io import StringIO
from unittest.mock import patch

# Adiciona a raiz do projeto ao path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

from interface.display import pretty_print_details

# --- Fixtures ---

@pytest.fixture
def sample_series():
    """Cria uma Series de exemplo para testes."""
    data = {
        'numero_ssa': 2025001,
        'setor_executor': 'IEE3',
        'situacao': 'APG',
        'descricao_ssa': 'Descricao curta 1',
        'data_cadastro': '01/01/2025',
        'valor_numerico': 100.5,
        'campo_nulo': None,
        'campo_nan_str': 'nan'
    }
    return pd.Series(data)

@pytest.fixture
def sample_dict():
    """Cria um dicionário de exemplo para testes."""
    return {
        'numero_ssa': 2025002,
        'setor_executor': 'MEL3',
        'situacao': 'ADM',
        'descricao_ssa': 'Descricao curta 2',
        'data_cadastro': '02/01/2025',
        'valor_numerico': 200,
        'campo_nulo': None
    }

@pytest.fixture
def display_map():
    """Mapa de exibição de exemplo."""
    return {
        'numero_ssa': 'Nº SSA',
        'setor_executor': 'Executor',
        'situacao': 'Situação',
        'descricao_ssa': 'Descrição da SSA',
        'data_cadastro': 'Data Cadastro',
        'valor_numerico': 'Valor',
        'campo_nulo': 'Campo Nulo',
        'campo_nan_str': 'Campo NaN Str'
    }

# --- Testes ---

def test_pretty_print_details_with_series(sample_series, display_map):
    """Testa pretty_print_details com uma pd.Series."""
    with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
        pretty_print_details(sample_series, display_map)
        output = mock_stdout.getvalue()
    
    assert "DETALHES DA SSA: 2025001" in output
    assert "Nº SSA:" in output
    assert "IEE3" in output
    assert "Descricao curta 1" in output
    assert "Campo Nulo:" in output
    assert "-" in output # Deve mostrar '-' para None
    assert "Campo NaN Str:" in output
    assert "-" in output # Deve mostrar '-' para 'nan' string

def test_pretty_print_details_with_dict(sample_dict, display_map):
    """Testa pretty_print_details com um dicionário."""
    with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
        pretty_print_details(sample_dict, display_map)
        output = mock_stdout.getvalue()
    
    assert "DETALHES DA SSA: 2025002" in output
    assert "Nº SSA:" in output
    assert "MEL3" in output
    assert "Descricao curta 2" in output

def test_pretty_print_details_invalid_series_type(display_map):
    """Testa pretty_print_details com um tipo inválido para series."""
    with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
        pretty_print_details("invalid_string", display_map)
        output = mock_stdout.getvalue()
    
    assert "Erro: Formato de dados da SSA inválido." in output

def test_pretty_print_details_invalid_display_map(sample_series):
    """Testa pretty_print_details com um display_map inválido."""
    with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
        pretty_print_details(sample_series, "invalid_dict")
        output = mock_stdout.getvalue()
    
    assert "Erro: Configuração de exibição inválida." in output

def test_pretty_print_details_empty_series(display_map):
    """Testa pretty_print_details com uma Series vazia."""
    empty_series = pd.Series(dtype=object)
    with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
        pretty_print_details(empty_series, display_map)
        output = mock_stdout.getvalue()
    
    assert "DETALHES DA SSA: N/A" in output
