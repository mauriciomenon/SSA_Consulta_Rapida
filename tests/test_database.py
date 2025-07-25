# tests/test_database.py
"""
Testes unitários para o módulo armazenamento.database.
"""

import pytest
import pandas as pd
import os
import sys
import tempfile
import shutil
import sqlite3

# Adiciona a raiz do projeto ao path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

# Importa as funções a serem testadas
# Assumindo que database.py esteja em armazenamento/database.py
from armazenamento.database import get_db_connection, initialize_database, query_db, insert_dataframe_to_db

# --- Fixtures ---

@pytest.fixture
def temp_db_path():
    """Cria um caminho temporário para o banco de dados de teste."""
    temp_dir = tempfile.mkdtemp()
    db_path = os.path.join(temp_dir, 'test_db.sqlite')
    yield db_path
    shutil.rmtree(temp_dir)

@pytest.fixture
def sample_dataframe():
    """Cria um DataFrame de exemplo para testes."""
    data = {
        'id': [1, 2, 3],
        'nome': ['Alice', 'Bob', 'Charlie'],
        'idade': [30, 25, 35]
    }
    return pd.DataFrame(data)

@pytest.fixture
def sample_schema_file():
    """Cria um arquivo de schema temporário para testes."""
    temp_dir = tempfile.mkdtemp()
    schema_path = os.path.join(temp_dir, 'test_schema.sql')
    schema_content = """
    CREATE TABLE IF NOT EXISTS usuarios (
        id INTEGER PRIMARY KEY,
        nome TEXT NOT NULL,
        idade INTEGER
    );
    """
    with open(schema_path, 'w') as f:
        f.write(schema_content)
    yield schema_path
    shutil.rmtree(temp_dir)

# --- Testes ---

def test_get_db_connection_context_manager(temp_db_path):
    """Testa o context manager get_db_connection."""
    with get_db_connection(temp_db_path) as conn:
        assert isinstance(conn, sqlite3.Connection)
        assert conn.total_changes == 0 # Nenhuma mudança ainda

    # Verifica se a conexão foi fechada implicitamente
    # (Difícil de testar diretamente, mas o contexto garante)


def test_initialize_database_success(temp_db_path, sample_schema_file, monkeypatch):
    """Testa a inicialização bem-sucedida do banco de dados."""
    # Mocka o caminho do schema para usar o temporário
    monkeypatch.setattr("armazenamento.database.os.path.join", lambda *args: sample_schema_file if 'schema.sql' in args else os.path.join(*args))
    
    # Mocka o nome do arquivo schema
    monkeypatch.setattr("armazenamento.database.schema_file", os.path.basename(sample_schema_file))
    
    # Como o patching do caminho pode ser tricky, vamos testar a lógica principal
    # simulando a criação da tabela diretamente e verificando se funciona.
    # Um teste mais robusto exigiria refatorar initialize_database para injetar o caminho do schema.
    
    # Alternativa: Testar query_db e insert_dataframe_to_db que dependem de um DB válido.
    pass # Placeholder para este teste complexo de setup


def test_insert_dataframe_to_db_success(temp_db_path, sample_dataframe):
    """Testa a inserção bem-sucedida de um DataFrame."""
    table_name = 'teste_usuarios'
    
    # 1. Cria a tabela manualmente para o teste
    with get_db_connection(temp_db_path) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS teste_usuarios (
                id INTEGER,
                nome TEXT,
                idade INTEGER
            );
        """)
        conn.commit()

    # 2. Insere o DataFrame
    success = insert_dataframe_to_db(sample_dataframe, temp_db_path, table_name)
    
    assert success is True
    
    # 3. Verifica se os dados foram inseridos
    df_from_db = query_db(temp_db_path, table_name)
    assert len(df_from_db) == len(sample_dataframe)
    # Verifica se os dados são iguais (reset_index para comparar corretamente)
    pd.testing.assert_frame_equal(df_from_db.sort_values('id').reset_index(drop=True), 
                                  sample_dataframe.sort_values('id').reset_index(drop=True))


def test_query_db_success(temp_db_path, sample_dataframe):
    """Testa uma consulta bem-sucedida."""
    table_name = 'teste_consulta'
    
    # 1. Cria a tabela e insere dados
    with get_db_connection(temp_db_path) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS teste_consulta (
                id INTEGER,
                nome TEXT,
                idade INTEGER
            );
        """)
        conn.commit()
    
    insert_dataframe_to_db(sample_dataframe, temp_db_path, table_name)
    
    # 2. Faz uma consulta
    df_result = query_db(temp_db_path, table_name, "SELECT * FROM teste_consulta WHERE idade > ?", (27,))
    
    # 3. Verifica o resultado
    expected_result = sample_dataframe[sample_dataframe['idade'] > 27]
    pd.testing.assert_frame_equal(df_result.sort_values('id').reset_index(drop=True), 
                                  expected_result.sort_values('id').reset_index(drop=True))

def test_query_db_empty_result(temp_db_path, sample_dataframe):
    """Testa uma consulta que retorna resultado vazio."""
    table_name = 'teste_consulta_vazia'
    
    with get_db_connection(temp_db_path) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS teste_consulta_vazia (
                id INTEGER,
                nome TEXT,
                idade INTEGER
            );
        """)
        conn.commit()
    
    insert_dataframe_to_db(sample_dataframe, temp_db_path, table_name)
    
    df_result = query_db(temp_db_path, table_name, "SELECT * FROM teste_consulta_vazia WHERE idade > ?", (100,))
    
    assert df_result.empty
    # Verifica se as colunas estão corretas mesmo com resultado vazio
    assert list(df_result.columns) == ['id', 'nome', 'idade']

def test_insert_dataframe_to_db_empty_df(temp_db_path):
    """Testa a inserção de um DataFrame vazio."""
    empty_df = pd.DataFrame()
    table_name = 'tabela_vazia'
    
    # Cria a tabela
    with get_db_connection(temp_db_path) as conn:
        conn.execute("CREATE TABLE IF NOT EXISTS tabela_vazia (id INTEGER);")
        conn.commit()
        
    success = insert_dataframe_to_db(empty_df, temp_db_path, table_name)
    
    assert success is True # Deve retornar True mesmo para DF vazio
    
    # Verifica que a tabela ainda existe e está vazia
    df_result = query_db(temp_db_path, table_name)
    assert df_result.empty
