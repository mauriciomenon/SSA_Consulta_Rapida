# tests/test_exporter.py
"""
Testes unitários para o módulo exportacao.exporter.
"""

import pytest
import pandas as pd
import os
import sys
import tempfile
import shutil
from unittest.mock import patch, MagicMock

# Adiciona a raiz do projeto ao path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

from exportacao.exporter import export_dataframe

# --- Fixtures ---

@pytest.fixture
def temp_output_dir():
    """Cria um diretório temporário para exportação."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir)

@pytest.fixture
def sample_dataframe():
    """Cria um DataFrame de exemplo para testes."""
    data = {
        'numero_ssa': [2025001, 2025002],
        'setor_executor': ['IEE3', 'MEL3'],
        'situacao': ['APG', 'ADM'],
        'descricao_ssa': ['Descricao 1', 'Descricao 2'],
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
    }

# --- Testes ---

def test_export_dataframe_success(temp_output_dir, sample_dataframe, display_map):
    """Testa a exportação bem-sucedida para os três formatos."""
    base_filename = "teste_exportacao"
    
    export_dataframe(sample_dataframe, base_filename, temp_output_dir, display_map)
    
    # Verifica se os arquivos foram criados
    expected_files = [
        os.path.join(temp_output_dir, f"{base_filename}.csv"),
        os.path.join(temp_output_dir, f"{base_filename}.xlsx"),
        os.path.join(temp_output_dir, f"{base_filename}.json")
    ]
    
    for file_path in expected_files:
        assert os.path.exists(file_path), f"Arquivo esperado não foi criado: {file_path}"
        
    # Verifica brevemente o conteúdo de um dos arquivos (CSV)
    csv_path = expected_files[0]
    df_from_csv = pd.read_csv(csv_path)
    assert len(df_from_csv) == len(sample_dataframe)
    assert 'Nº SSA' in df_from_csv.columns

def test_export_dataframe_empty_df(temp_output_dir, display_map, capsys):
    """Testa a exportação com um DataFrame vazio."""
    empty_df = pd.DataFrame()
    base_filename = "teste_vazio"
    
    export_dataframe(empty_df, base_filename, temp_output_dir, display_map)
    
    captured = capsys.readouterr()
    assert "Aviso: Nenhum dado para exportar." in captured.out
    
    # Nenhum arquivo deve ser criado
    assert not os.listdir(temp_output_dir)

@patch('exportacao.exporter.os.makedirs')
def test_export_dataframe_output_dir_error(mock_makedirs, temp_output_dir, sample_dataframe, display_map, capsys):
    """Testa erro na criação do diretório de saída."""
    mock_makedirs.side_effect = PermissionError("Permissão negada")
    
    base_filename = "teste_erro_dir"
    # Usa um subdiretório que falhará ao ser criado
    problematic_dir = os.path.join(temp_output_dir, "subdir_nao_autorizado")
    
    export_dataframe(sample_dataframe, base_filename, problematic_dir, display_map)
    
    captured = capsys.readouterr()
    assert "Erro: Não foi possível criar o diretório de saída" in captured.out

# Testes para falhas individuais de exportação seriam mais complexos
# e requereriam mocking mais específico de pd.DataFrame.to_csv, to_excel, to_json
# O teste acima cobre o fluxo principal e um erro crítico de setup.
