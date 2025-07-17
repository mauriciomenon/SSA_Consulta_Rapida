# tests/test_interface.py
import pandas as pd
import sys
import os

# Adiciona a raiz do projeto ao path para que possamos importar os nossos módulos
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

from interface.cli import filter_dataframe

def test_filter_dataframe_single_term():
    """
    Testa se a filtragem com um único termo funciona corretamente.
    """
    # 1. Preparação (Arrange): Cria um DataFrame de exemplo em memória.
    data = {
        'col_texto': ['Relatório sobre o servidor A', 'Análise do sistema B', 'Servidor C com problemas'],
        'col_num': [10, 20, 30]
    }
    df = pd.DataFrame(data)

    # 2. Ação (Act): Executa a função que queremos testar.
    search_terms = ['servidor']
    filtered_df = filter_dataframe(df, search_terms)

    # 3. Verificação (Assert): Verifica se o resultado é o esperado.
    # Esperamos que encontre 2 linhas que contêm a palavra "servidor".
    assert len(filtered_df) == 2
    # Verificamos também se a linha que não contém o termo foi excluída.
    assert 'Análise do sistema B' not in filtered_df['col_texto'].values


def test_filter_dataframe_multiple_terms():
    """
    Testa se a filtragem com múltiplos termos (lógica 'E') funciona.
    """
    # 1. Preparação
    data = {
        'descricao_ssa': ['Falha no painel do servidor CISCO', 'Servidor CISCO está OK', 'Problema no painel de rede'],
        'localizacao': ['Sala A', 'Sala B', 'Sala A']
    }
    df = pd.DataFrame(data)

    # 2. Ação
    search_terms = ['cisco', 'painel'] # Note que a busca não é case-sensitive
    filtered_df = filter_dataframe(df, search_terms)

    # 3. Verificação
    # Esperamos encontrar apenas 1 linha que contém AMBOS os termos.
    assert len(filtered_df) == 1
    assert 'Falha no painel do servidor CISCO' in filtered_df['descricao_ssa'].values

def test_filter_dataframe_no_results():
    """
    Testa se a função retorna um DataFrame vazio quando nenhum resultado é encontrado.
    """
    # 1. Preparação
    data = {'col_texto': ['A', 'B', 'C']}
    df = pd.DataFrame(data)

    # 2. Ação
    search_terms = ['termo_inexistente']
    filtered_df = filter_dataframe(df, search_terms)

    # 3. Verificação
    # Esperamos um DataFrame vazio.
    assert filtered_df.empty


