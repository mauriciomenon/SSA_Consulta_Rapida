# tests/test_extracao.py
import pytest
import pandas as pd
import os
import sys
import json

# Adiciona a raiz do projeto ao path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

from extracao.extractor import read_report

# --- Fixtures: Preparando o Ambiente de Teste ---

@pytest.fixture
def temp_excel_file(tmp_path):
    """
    Fixture que cria um arquivo Excel temporário para os testes.
    'tmp_path' é uma fixture mágica do pytest que nos dá uma pasta temporária.
    """
    # Dados de exemplo que vamos colocar no Excel
    data = {
        'Nº SSA': [101, 102],
        'Local': ['Sala A', 'Sala B'],
        'Descrição da SSA': ['Problema no servidor', 'Falha na rede'],
        'Emitida Em': ['01/07/2025', '15/07/2025'],
        'Coluna Inutil': [None, None] # Coluna que deve ser ignorada
    }
    df = pd.DataFrame(data)
    
    # O cabeçalho está na segunda linha, então inserimos uma linha em branco no topo
    file_path = tmp_path / "relatorio_teste.xlsx"
    writer = pd.ExcelWriter(file_path, engine='openpyxl')
    df.to_excel(writer, index=False, startrow=1) 
    writer.close()
    
    return str(file_path)

@pytest.fixture
def setup_test_config(monkeypatch):
    """
    Fixture que simula o nosso arquivo de configuração, garantindo que o teste
    não dependa do arquivo real.
    'monkeypatch' é uma fixture do pytest que nos permite modificar o comportamento
    de funções, variáveis ou módulos durante os testes.
    """
    # Mapeamento de colunas de exemplo
    test_mappings = {
      "numero_ssa": ["Nº SSA"],
      "localizacao": ["Local"],
      "descricao_ssa": ["Descrição da SSA"],
      "data_cadastro": ["Emitida Em"]
    }

    # Função interna que irá substituir a _load_column_mappings original
    def mock_load_mappings():
        return {alias: canonical for canonical, aliases in test_mappings.items() for alias in aliases}

    # Diz ao pytest para usar a nossa função 'mock_load_mappings' sempre que
    # a função '_load_column_mappings' for chamada no módulo 'extractor'.
    monkeypatch.setattr('extracao.extractor._load_column_mappings', mock_load_mappings)


# --- Testes ---

def test_read_report_success(temp_excel_file, setup_test_config):
    """
    Testa o caminho feliz: ler um relatório, renomear colunas e normalizar tipos.
    Note que passamos as fixtures como argumentos para o teste.
    """
    # 1. Ação: Executa a função a ser testada com os arquivos temporários criados pelas fixtures.
    df, _ = read_report(temp_excel_file)

    # 2. Verificação
    assert df is not None
    assert not df.empty
    
    # Verifica se as colunas foram renomeadas para os nomes canônicos
    expected_columns = ['numero_ssa', 'localizacao', 'descricao_ssa', 'data_cadastro']
    assert all(col in df.columns for col in expected_columns)
    
    # Verifica se a coluna inútil (totalmente vazia) foi removida
    assert 'Coluna Inutil' not in df.columns
    
    # Verifica se o tipo de dado da data foi convertido corretamente
    assert pd.api.types.is_datetime64_any_dtype(df['data_cadastro'])
    
    # Verifica se os dados foram lidos corretamente
    assert df['numero_ssa'].iloc[0] == 101
    assert df['localizacao'].iloc[1] == 'Sala B'


