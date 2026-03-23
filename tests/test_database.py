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
from armazenamento.database import get_db_connection, query_db, insert_dataframe_to_db  # noqa: E402

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
    # Captura a função original para evitar recursão ao chamar dentro do lambda
    _orig_join = os.path.join
    monkeypatch.setattr(
        "armazenamento.database.os.path.join",
        lambda *args: sample_schema_file if 'schema.sql' in args else _orig_join(*args)
    )

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
    expected_result = sample_dataframe[sample_dataframe['idade'] > 27].copy()
    expected_result["id"] = expected_result["id"].astype("Int64")
    expected_result["nome"] = expected_result["nome"].astype("string")
    expected_result["idade"] = expected_result["idade"].astype("Int64")
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


def test_query_db_keeps_nullable_integer_columns_without_float_promotion(temp_db_path):
    table_name = "teste_nullable_ints"

    with get_db_connection(temp_db_path) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS teste_nullable_ints (
                numero_ssa TEXT,
                semana_cadastro INTEGER,
                semana_programada INTEGER,
                num_reprogramacoes INTEGER,
                total_de_reprogramacoes INTEGER
            );
            """
        )
        conn.executemany(
            """
            INSERT INTO teste_nullable_ints (
                numero_ssa,
                semana_cadastro,
                semana_programada,
                num_reprogramacoes,
                total_de_reprogramacoes
            ) VALUES (?, ?, ?, ?, ?)
            """,
            [
                ("202500001", 202501, 202510, 2, 5),
                ("202500002", None, 202511, None, 6),
                ("202500003", 202503, None, 3, None),
            ],
        )
        conn.commit()

    df_result = query_db(temp_db_path, table_name)

    assert str(df_result["numero_ssa"].dtype) == "string"
    assert str(df_result["semana_cadastro"].dtype) == "Int64"
    assert str(df_result["semana_programada"].dtype) == "Int64"
    assert str(df_result["num_reprogramacoes"].dtype) == "Int64"
    assert str(df_result["total_de_reprogramacoes"].dtype) == "Int64"
    assert df_result["semana_cadastro"].tolist() == [202501, pd.NA, 202503]
    assert df_result["semana_programada"].tolist() == [202510, 202511, pd.NA]
    assert df_result["num_reprogramacoes"].tolist() == [2, pd.NA, 3]
    assert df_result["total_de_reprogramacoes"].tolist() == [5, 6, pd.NA]


def test_query_db_sql_error_returns_empty_df_when_raise_disabled(temp_db_path):
    """query_db should fail closed for SQL/database errors when raise_on_error is False."""
    with get_db_connection(temp_db_path) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS teste_erro_sql (
                id INTEGER
            );
            """
        )
        conn.commit()

    df_result = query_db(
        temp_db_path,
        "teste_erro_sql",
        "SELECT coluna_inexistente FROM teste_erro_sql",
        raise_on_error=False,
    )

    assert isinstance(df_result, pd.DataFrame)
    assert df_result.empty


def test_query_db_unexpected_error_is_not_suppressed(temp_db_path, monkeypatch):
    """Unexpected runtime errors must propagate even when raise_on_error is False."""
    with get_db_connection(temp_db_path) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS teste_erro_runtime (
                id INTEGER
            );
            """
        )
        conn.commit()

    def _raise_runtime(*_args, **_kwargs):
        raise RuntimeError("falha inesperada")

    monkeypatch.setattr("armazenamento.database.pd.read_sql_query", _raise_runtime)

    with pytest.raises(RuntimeError, match="falha inesperada"):
        query_db(temp_db_path, "teste_erro_runtime", raise_on_error=False)


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


def test_insert_dataframe_to_db_rejects_replace_for_canonical_ssa_table(temp_db_path):
    df = pd.DataFrame(
        [
            {"numero_ssa": "202500001", "descricao_ssa": "SSA 1"},
        ]
    )

    with get_db_connection(temp_db_path) as conn:
        conn.execute(
            """
            CREATE TABLE ssa_table (
                numero_ssa TEXT,
                descricao_ssa TEXT
            );
            """
        )
        conn.execute("CREATE VIEW ssas AS SELECT * FROM ssa_table;")
        conn.commit()

    with pytest.raises(ValueError, match="if_exists='replace' e proibido"):
        insert_dataframe_to_db(df, temp_db_path, "ssas", if_exists="replace")


def test_insert_dataframe_to_db_allows_replace_for_generic_table(temp_db_path):
    table_name = "teste_replace_generico"
    initial_df = pd.DataFrame([{"id": 1, "nome": "Alice"}])
    replacement_df = pd.DataFrame([{"id": 2, "nome": "Bob"}])

    with get_db_connection(temp_db_path) as conn:
        conn.execute(
            """
            CREATE TABLE teste_replace_generico (
                id INTEGER,
                nome TEXT
            );
            """
        )
        conn.commit()

    assert insert_dataframe_to_db(initial_df, temp_db_path, table_name) is True
    assert insert_dataframe_to_db(replacement_df, temp_db_path, table_name, if_exists="replace") is True

    result = query_db(temp_db_path, table_name)
    pd.testing.assert_frame_equal(result.reset_index(drop=True), replacement_df)


def test_insert_dataframe_to_db_rolls_back_partial_write_on_to_sql_failure(temp_db_path, monkeypatch):
    table_name = "teste_rollback"
    df = pd.DataFrame(
        [
            {"id": 1, "nome": "Alice"},
            {"id": 2, "nome": "Bob"},
        ]
    )

    with get_db_connection(temp_db_path) as conn:
        conn.execute(
            """
            CREATE TABLE teste_rollback (
                id INTEGER,
                nome TEXT
            );
            """
        )
        conn.commit()

    original_to_sql = pd.DataFrame.to_sql

    def _partial_insert_then_fail(self, name, conn, *args, **kwargs):
        conn.execute("INSERT INTO teste_rollback (id, nome) VALUES (?, ?)", (999, "parcial"))
        raise RuntimeError("falha simulada no to_sql")

    monkeypatch.setattr(pd.DataFrame, "to_sql", _partial_insert_then_fail)
    try:
        assert insert_dataframe_to_db(df, temp_db_path, table_name) is False
    finally:
        monkeypatch.setattr(pd.DataFrame, "to_sql", original_to_sql)

    result = query_db(temp_db_path, table_name)
    assert result.empty
