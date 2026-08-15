# tests/test_database.py
"""
Testes unitários para o módulo armazenamento.database.
"""

import concurrent.futures
from contextlib import closing
import os
import logging
import shutil
import sqlite3
import sys
import tempfile
import threading
from time import monotonic

import pandas as pd
import pytest

# Adiciona a raiz do projeto ao path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, project_root)

# Importa as funções a serem testadas
# Assumindo que database.py esteja em armazenamento/database.py
from armazenamento.database import count_table_rows  # noqa: E402
from armazenamento.database import count_distinct_derivada_edges  # noqa: E402
from armazenamento.database import get_db_connection  # noqa: E402
from armazenamento.database import initialize_database  # noqa: E402
from armazenamento.database import insert_dataframe_to_db  # noqa: E402
from armazenamento.database import query_db  # noqa: E402
from armazenamento.database import resolve_target_table  # noqa: E402
from armazenamento.database import vacuum_analyze_database  # noqa: E402

# --- Fixtures ---


@pytest.fixture
def temp_db_path():
    """Cria um caminho temporário para o banco de dados de teste."""
    temp_dir = tempfile.mkdtemp()
    db_path = os.path.join(temp_dir, "test_db.sqlite")
    yield db_path
    shutil.rmtree(temp_dir)


@pytest.fixture
def sample_dataframe():
    """Cria um DataFrame de exemplo para testes."""
    data = {"id": [1, 2, 3], "nome": ["Alice", "Bob", "Charlie"], "idade": [30, 25, 35]}
    return pd.DataFrame(data)


@pytest.fixture
def sample_schema_file():
    """Cria um arquivo de schema temporário para testes."""
    temp_dir = tempfile.mkdtemp()
    schema_path = os.path.join(temp_dir, "test_schema.sql")
    schema_content = """
    CREATE TABLE IF NOT EXISTS usuarios (
        id INTEGER PRIMARY KEY,
        nome TEXT NOT NULL,
        idade INTEGER
    );
    """
    with open(schema_path, "w") as f:
        f.write(schema_content)
    yield schema_path
    shutil.rmtree(temp_dir)


# --- Testes ---


def test_get_db_connection_context_manager(temp_db_path):
    """Testa o context manager get_db_connection."""
    with get_db_connection(temp_db_path) as conn:
        assert isinstance(conn, sqlite3.Connection)
        assert conn.total_changes == 0  # Nenhuma mudança ainda

    # Verifica se a conexão foi fechada implicitamente
    # (Difícil de testar diretamente, mas o contexto garante)


def test_get_db_connection_rolls_back_non_sqlite_exception(temp_db_path):
    """Runtime errors inside the context must not leave partial writes."""
    with get_db_connection(temp_db_path) as conn:
        conn.execute("CREATE TABLE events (id INTEGER PRIMARY KEY, value TEXT)")
        conn.commit()

    with pytest.raises(RuntimeError, match="forced runtime failure"):
        with get_db_connection(temp_db_path) as conn:
            conn.execute("INSERT INTO events (value) VALUES (?)", ("partial",))
            raise RuntimeError("forced runtime failure")

    with get_db_connection(temp_db_path) as conn:
        count = conn.execute("SELECT COUNT(*) FROM events").fetchone()[0]

    assert count == 0


def test_insert_dataframe_to_db_skips_closed_connection_rollback_noise(
    temp_db_path,
    sample_dataframe,
    monkeypatch,
    caplog,
):
    with get_db_connection(temp_db_path) as conn:
        conn.execute("""
            CREATE TABLE teste_rollback_noise (
                id INTEGER,
                nome TEXT,
                idade INTEGER
            );
        """)
        conn.commit()

    def _fail_insert(*_args, **_kwargs):
        raise RuntimeError("forced insert failure")

    monkeypatch.setattr("armazenamento.database._execute_simple_insert", _fail_insert)
    caplog.set_level(logging.WARNING)

    success = insert_dataframe_to_db(
        sample_dataframe,
        temp_db_path,
        "teste_rollback_noise",
    )

    assert success is False
    assert "Falha ao executar rollback explicito" not in caplog.text


def test_initialize_database_success(temp_db_path, sample_schema_file, monkeypatch):
    """Testa a inicialização bem-sucedida do banco de dados."""
    assert initialize_database(temp_db_path, schema_file=sample_schema_file) is True

    with get_db_connection(temp_db_path) as conn:
        tables = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='usuarios'"
        ).fetchall()

    assert tables == [("usuarios",)]


def test_initialize_database_connection_clears_only_current_db_cache(
    temp_db_path, sample_schema_file
):
    from armazenamento import database as database_module

    try:
        with closing(sqlite3.connect(temp_db_path)) as conn:
            current_key = (database_module._get_connection_db_path(conn), "usuarios")
            other_key = (os.path.abspath(temp_db_path + ".other"), "usuarios")
            database_module._resolved_table_cache.clear()
            database_module._resolved_table_cache[current_key] = "stale_current"
            database_module._resolved_table_cache[other_key] = "other_db"
            assert initialize_database(conn, schema_file=sample_schema_file) is True

        assert current_key not in database_module._resolved_table_cache
        assert database_module._resolved_table_cache[other_key] == "other_db"
    finally:
        database_module._resolved_table_cache.clear()


def test_resolved_table_cache_prunes_oldest_entry():
    from armazenamento import database as database_module

    try:
        database_module._resolved_table_cache.clear()
        max_entries = database_module._RESOLVED_TABLE_CACHE_MAX_ENTRIES
        for index in range(max_entries + 1):
            database_module._store_resolved_table_cache(
                (f"cache-{index}.sqlite", "ssa_table"),
                f"table_{index}",
            )

        assert len(database_module._resolved_table_cache) == max_entries
        assert ("cache-0.sqlite", "ssa_table") not in (
            database_module._resolved_table_cache
        )
        assert (
            database_module._resolved_table_cache[
                (f"cache-{max_entries}.sqlite", "ssa_table")
            ]
            == f"table_{max_entries}"
        )
    finally:
        database_module._resolved_table_cache.clear()


def test_resolved_table_cache_handles_concurrent_resolve_and_clear(temp_db_path):
    from armazenamento import database as database_module

    with closing(sqlite3.connect(temp_db_path)) as conn:
        conn.execute("CREATE TABLE ssa_table (id INTEGER)")

    workers = 8
    iterations = 80
    barrier = threading.Barrier(workers)

    def resolve_worker():
        barrier.wait()
        with closing(sqlite3.connect(temp_db_path)) as conn:
            for _ in range(iterations):
                assert resolve_target_table(conn, "ssas") == "ssa_table"

    def cache_writer_worker():
        barrier.wait()
        manual_key = (os.path.abspath(temp_db_path), "manual")
        for _ in range(iterations):
            database_module._clear_resolved_table_cache(temp_db_path)
            database_module._store_resolved_table_cache(manual_key, "manual_table")

    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
            futures = [
                *(executor.submit(resolve_worker) for _ in range(workers - 2)),
                *(executor.submit(cache_writer_worker) for _ in range(2)),
            ]
            for future in futures:
                future.result(timeout=10)

        assert len(database_module._resolved_table_cache) <= (
            database_module._RESOLVED_TABLE_CACHE_MAX_ENTRIES
        )
    finally:
        database_module._resolved_table_cache.clear()


def test_insert_dataframe_to_db_success(temp_db_path, sample_dataframe):
    """Testa a inserção bem-sucedida de um DataFrame."""
    table_name = "teste_usuarios"

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
    expected_df = sample_dataframe.sort_values("id").reset_index(drop=True).copy()
    expected_df["id"] = expected_df["id"].astype("Int64")
    expected_df["nome"] = expected_df["nome"].astype("string")
    expected_df["idade"] = expected_df["idade"].astype("Int64")
    pd.testing.assert_frame_equal(
        df_from_db.sort_values("id").reset_index(drop=True),
        expected_df,
    )


def test_query_db_success(temp_db_path, sample_dataframe):
    """Testa uma consulta bem-sucedida."""
    table_name = "teste_consulta"

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
    df_result = query_db(
        temp_db_path, table_name, "SELECT * FROM teste_consulta WHERE idade > ?", (27,)
    )

    # 3. Verifica o resultado
    expected_result = sample_dataframe[sample_dataframe["idade"] > 27].copy()
    expected_result["id"] = expected_result["id"].astype("Int64")
    expected_result["nome"] = expected_result["nome"].astype("string")
    expected_result["idade"] = expected_result["idade"].astype("Int64")
    pd.testing.assert_frame_equal(
        df_result.sort_values("id").reset_index(drop=True),
        expected_result.sort_values("id").reset_index(drop=True),
    )


def test_query_db_empty_result(temp_db_path, sample_dataframe):
    """Testa uma consulta que retorna resultado vazio."""
    table_name = "teste_consulta_vazia"

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

    df_result = query_db(
        temp_db_path,
        table_name,
        "SELECT * FROM teste_consulta_vazia WHERE idade > ?",
        (100,),
    )

    assert df_result.empty
    # Verifica se as colunas estão corretas mesmo com resultado vazio
    assert list(df_result.columns) == ["id", "nome", "idade"]


def test_query_db_interrupts_long_running_query(temp_db_path):
    callback_calls = 0

    def _cancel_query() -> bool:
        nonlocal callback_calls
        callback_calls += 1
        return callback_calls >= 2

    started = monotonic()
    with pytest.raises(InterruptedError, match="Database query cancelled"):
        query_db(
            temp_db_path,
            "",
            """
            WITH RECURSIVE numbers(value) AS (
                VALUES(1)
                UNION ALL
                SELECT value + 1 FROM numbers WHERE value < 1000000
            )
            SELECT sum(value) FROM numbers
            """,
            cancel_callback=_cancel_query,
        )

    assert callback_calls >= 2
    assert monotonic() - started < 2.0


def test_query_db_propagates_cancel_callback_failure(temp_db_path):
    def _broken_cancel_callback() -> bool:
        raise ValueError("cancel callback failed")

    with pytest.raises(RuntimeError, match="query_db cancel callback failed") as exc_info:
        query_db(
            temp_db_path,
            "",
            """
            WITH RECURSIVE numbers(value) AS (
                VALUES(1)
                UNION ALL
                SELECT value + 1 FROM numbers WHERE value < 1000000
            )
            SELECT sum(value) FROM numbers
            """,
            cancel_callback=_broken_cancel_callback,
        )

    assert isinstance(exc_info.value.__cause__, ValueError)


def test_query_db_rejects_non_read_only_custom_query(temp_db_path):
    """query_db must not execute write statements through the custom query path."""
    with get_db_connection(temp_db_path) as conn:
        conn.execute("CREATE TABLE teste_query_guard (id INTEGER);")
        conn.commit()

    with pytest.raises(ValueError, match="read-only"):
        query_db(
            temp_db_path,
            "teste_query_guard",
            "DELETE FROM teste_query_guard",
            raise_on_error=True,
        )


@pytest.mark.parametrize(
    "custom_query",
    [
        "WITH doomed AS (DELETE FROM teste_query_guard RETURNING id) SELECT * FROM doomed",
        "WITH doomed AS (UPDATE teste_query_guard SET id = 2 RETURNING id) SELECT * FROM doomed",
        "WITH doomed AS (INSERT INTO teste_query_guard VALUES (2) RETURNING id) SELECT * FROM doomed",
    ],
)
def test_query_db_rejects_cte_write_custom_query(temp_db_path, custom_query):
    """query_db must reject write tokens hidden behind a CTE start token."""
    with get_db_connection(temp_db_path) as conn:
        conn.execute("CREATE TABLE teste_query_guard (id INTEGER);")
        conn.execute("INSERT INTO teste_query_guard VALUES (1);")
        conn.commit()

    with pytest.raises(ValueError, match="read-only"):
        query_db(
            temp_db_path,
            "teste_query_guard",
            custom_query,
            raise_on_error=True,
        )


def test_query_db_accepts_read_only_cte_custom_query(temp_db_path):
    """query_db must continue to accept read-only CTEs."""
    with get_db_connection(temp_db_path) as conn:
        conn.execute("CREATE TABLE teste_query_guard (id INTEGER);")
        conn.execute("INSERT INTO teste_query_guard VALUES (1);")
        conn.commit()

    result = query_db(
        temp_db_path,
        "teste_query_guard",
        "WITH rows AS (SELECT id FROM teste_query_guard) SELECT id FROM rows",
        raise_on_error=True,
    )

    assert result["id"].tolist() == [1]


def test_query_db_allows_write_words_inside_literals_and_comments(temp_db_path):
    """query_db must not reject harmless text while guarding executable SQL."""
    with get_db_connection(temp_db_path) as conn:
        conn.execute("CREATE TABLE teste_query_guard (id INTEGER);")
        conn.execute("INSERT INTO teste_query_guard VALUES (1);")
        conn.commit()

    result = query_db(
        temp_db_path,
        "teste_query_guard",
        """
        SELECT id, 'delete; drop' AS marker
        FROM teste_query_guard
        /* update teste_query_guard */
        -- insert into teste_query_guard
        """,
        raise_on_error=True,
    )

    assert result["id"].tolist() == [1]
    assert result["marker"].tolist() == ["delete; drop"]


def test_query_db_rejects_multi_statement_custom_query(temp_db_path):
    """query_db must reject appended statements in custom SQL."""
    with get_db_connection(temp_db_path) as conn:
        conn.execute("CREATE TABLE teste_query_guard (id INTEGER);")
        conn.commit()

    with pytest.raises(ValueError, match="single statement"):
        query_db(
            temp_db_path,
            "teste_query_guard",
            "SELECT * FROM teste_query_guard; DROP TABLE teste_query_guard",
            raise_on_error=True,
        )


def test_query_db_rejects_semicolon_only_custom_query(temp_db_path):
    """query_db must reject semicolon-only SQL with a clean validation error."""
    with get_db_connection(temp_db_path) as conn:
        conn.execute("CREATE TABLE teste_query_guard (id INTEGER);")
        conn.commit()

    with pytest.raises(ValueError, match="Custom SQL query must not be empty"):
        query_db(
            temp_db_path,
            "teste_query_guard",
            ";",
            raise_on_error=True,
        )


def test_query_db_rejects_params_without_custom_query(temp_db_path):
    """params without placeholders must fail before sqlite raises a generic error."""
    with get_db_connection(temp_db_path) as conn:
        conn.execute("CREATE TABLE teste_query_guard (id INTEGER);")
        conn.commit()

    with pytest.raises(ValueError, match="params require a custom SQL query"):
        query_db(
            temp_db_path,
            "teste_query_guard",
            params=(1,),
            raise_on_error=True,
        )


def test_count_table_rows_counts_resolved_table_and_rejects_invalid_identifier(
    temp_db_path,
    sample_dataframe,
):
    table_name = "teste_contagem"
    with get_db_connection(temp_db_path) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS teste_contagem (
                id INTEGER,
                nome TEXT,
                idade INTEGER
            );
        """)
        conn.commit()

    assert insert_dataframe_to_db(sample_dataframe, temp_db_path, table_name) is True

    assert count_table_rows(temp_db_path, table_name) == len(sample_dataframe)
    with pytest.raises(ValueError, match="Invalid SQL identifier"):
        count_table_rows(temp_db_path, "teste;drop")


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


def test_insert_dataframe_to_db_keeps_numero_ssa_as_canonical_string(temp_db_path):
    table_name = "teste_ssa_storage_text"
    source_df = pd.DataFrame(
        [
            {
                "numero_ssa": "202500777.0",
                "descricao_ssa": "SSA canonica",
            }
        ]
    )

    with get_db_connection(temp_db_path) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS teste_ssa_storage_text (
                numero_ssa TEXT,
                descricao_ssa TEXT
            );
            """
        )
        conn.commit()

    assert insert_dataframe_to_db(source_df, temp_db_path, table_name) is True

    df_result = query_db(temp_db_path, table_name)

    assert str(df_result["numero_ssa"].dtype) == "string"
    assert df_result["numero_ssa"].tolist() == ["202500777"]


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


def test_query_db_does_not_log_parameter_values(temp_db_path, caplog):
    """query_db must not expose bound parameter values in diagnostic logs."""
    sensitive_param = "private-bound-param-for-log-test"
    with get_db_connection(temp_db_path) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS teste_log_params (
                nome TEXT
            );
            """
        )
        conn.execute("INSERT INTO teste_log_params (nome) VALUES (?)", (sensitive_param,))
        conn.commit()

    caplog.set_level(logging.DEBUG, logger="armazenamento.database")

    df_result = query_db(
        temp_db_path,
        "teste_log_params",
        "SELECT * FROM teste_log_params WHERE nome = ?",
        params=(sensitive_param,),
    )

    assert len(df_result) == 1
    success_messages = [record.getMessage() for record in caplog.records]
    assert all(sensitive_param not in message for message in success_messages)
    assert any("1 parametros" in message for message in success_messages)

    caplog.clear()
    df_error = query_db(
        temp_db_path,
        "teste_log_params",
        "SELECT coluna_inexistente FROM teste_log_params WHERE nome = ?",
        params=(sensitive_param,),
        raise_on_error=False,
    )

    assert df_error.empty
    error_messages = [record.getMessage() for record in caplog.records]
    assert all(sensitive_param not in message for message in error_messages)
    assert any("1 parametros" in message for message in error_messages)


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


def test_resolve_target_table_keeps_unrelated_view_when_canonical_exists(temp_db_path):
    with get_db_connection(temp_db_path) as conn:
        conn.execute("CREATE TABLE ssa_table (numero_ssa TEXT)")
        conn.execute("CREATE TABLE unrelated_source (id INTEGER)")
        conn.execute("CREATE VIEW unrelated_view AS SELECT id FROM unrelated_source")
        conn.commit()

        resolved = resolve_target_table(conn, "unrelated_view")

    assert resolved == "unrelated_view"


def test_resolve_target_table_returns_actual_database_identifier_casing(temp_db_path):
    with get_db_connection(temp_db_path) as conn:
        conn.execute("CREATE TABLE SSA_TABLE (numero_ssa TEXT)")
        conn.commit()

        resolved = resolve_target_table(conn, "ssa_table")

    assert resolved == "SSA_TABLE"


def test_resolve_target_table_rejects_multiple_physical_ssa_tables(temp_db_path):
    with get_db_connection(temp_db_path) as conn:
        conn.execute("CREATE TABLE ssa_table (numero_ssa TEXT)")
        conn.execute("CREATE TABLE ssas (numero_ssa TEXT)")
        conn.commit()

        with pytest.raises(ValueError, match="Ambiguous SSA storage tables"):
            resolve_target_table(conn, "ssas")


def test_resolve_target_table_rechecks_ssa_schema_after_cached_resolution(temp_db_path):
    with get_db_connection(temp_db_path) as conn:
        conn.execute("CREATE TABLE ssa_table (numero_ssa TEXT)")
        conn.commit()
        assert resolve_target_table(conn, "ssas") == "ssa_table"

        conn.execute("CREATE TABLE ssas (numero_ssa TEXT)")
        conn.commit()

        with pytest.raises(ValueError, match="Ambiguous SSA storage tables"):
            resolve_target_table(conn, "ssas")


def test_resolve_target_table_reuses_single_legacy_for_canonical_request(temp_db_path):
    with get_db_connection(temp_db_path) as conn:
        conn.execute("CREATE TABLE ssas (numero_ssa TEXT)")
        conn.commit()

        resolved = resolve_target_table(conn, "ssa_table")

    assert resolved == "ssas"


def test_standard_insert_canonical_request_does_not_create_second_ssa_table(
    temp_db_path,
):
    with get_db_connection(temp_db_path) as conn:
        conn.execute("CREATE TABLE ssas (numero_ssa TEXT, situacao TEXT)")
        conn.commit()
    frame = pd.DataFrame({"numero_ssa": ["202500113"], "situacao": ["STE"]})

    assert insert_dataframe_to_db(frame, temp_db_path, "ssa_table") is True

    with get_db_connection(temp_db_path) as conn:
        assert conn.execute("SELECT numero_ssa FROM ssas").fetchone() == (
            "202500113",
        )
        assert conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='ssa_table'"
        ).fetchone() is None


def test_resolve_target_table_ignores_indexes_when_matching_identifier(temp_db_path):
    with get_db_connection(temp_db_path) as conn:
        conn.execute("CREATE TABLE indexed_source (id INTEGER)")
        conn.execute("CREATE INDEX IDX_INDEXED_SOURCE_ID ON indexed_source (id)")
        conn.commit()

        resolved = resolve_target_table(conn, "idx_indexed_source_id")

    assert resolved == "idx_indexed_source_id"


def test_resolve_target_table_cache_is_connection_specific_for_memory_db():
    conn_a = sqlite3.connect(":memory:")
    conn_b = sqlite3.connect(":memory:")
    try:
        conn_a.execute("CREATE TABLE ssa_table (numero_ssa TEXT)")
        conn_a.execute("CREATE VIEW ssas AS SELECT * FROM ssa_table")
        conn_a.commit()

        conn_b.execute("CREATE TABLE ssas (numero_ssa TEXT)")
        conn_b.commit()

        assert resolve_target_table(conn_a, "ssas") == "ssa_table"
        assert resolve_target_table(conn_b, "ssas") == "ssas"
    finally:
        conn_a.close()
        conn_b.close()


def test_vacuum_analyze_database_runs_sqlite_maintenance(temp_db_path):
    with closing(sqlite3.connect(temp_db_path)) as conn:
        conn.execute("CREATE TABLE maint(a INTEGER)")
        conn.execute("INSERT INTO maint(a) VALUES (1)")
        conn.commit()

    result = vacuum_analyze_database(temp_db_path)

    assert result == {"ok": True, "db_path": temp_db_path}
    with closing(sqlite3.connect(temp_db_path)) as conn:
        rows = conn.execute("SELECT a FROM maint").fetchall()
    assert rows == [(1,)]


def test_vacuum_analyze_database_rejects_missing_file(tmp_path):
    missing_db = tmp_path / "missing.sqlite"

    result = vacuum_analyze_database(str(missing_db))

    assert result["ok"] is False
    assert "nao encontrado" in result["error"]
    assert not missing_db.exists()


def test_count_distinct_derivada_edges_rejects_invalid_table_identifier(temp_db_path):
    with get_db_connection(temp_db_path) as conn:
        with pytest.raises(ValueError):
            count_distinct_derivada_edges(conn, 'ssas"; DROP TABLE maint; --')


def test_insert_dataframe_to_db_empty_df(temp_db_path):
    """Testa a inserção de um DataFrame vazio."""
    empty_df = pd.DataFrame()
    table_name = "tabela_vazia"

    # Cria a tabela
    with get_db_connection(temp_db_path) as conn:
        conn.execute("CREATE TABLE IF NOT EXISTS tabela_vazia (id INTEGER);")
        conn.commit()

    success = insert_dataframe_to_db(empty_df, temp_db_path, table_name)

    assert success is True  # Deve retornar True mesmo para DF vazio

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


def test_insert_dataframe_to_db_rejects_replace_for_canonical_ssa_table_casing(
    temp_db_path,
):
    df = pd.DataFrame(
        [
            {"numero_ssa": "202500001", "descricao_ssa": "SSA 1"},
        ]
    )

    with get_db_connection(temp_db_path) as conn:
        conn.execute(
            """
            CREATE TABLE SSA_TABLE (
                numero_ssa TEXT,
                descricao_ssa TEXT
            );
            """
        )
        conn.commit()

    with pytest.raises(ValueError, match="if_exists='replace' e proibido"):
        insert_dataframe_to_db(df, temp_db_path, "ssa_table", if_exists="replace")


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
    initial_result = query_db(temp_db_path, table_name)
    expected_initial_df = initial_df.copy()
    expected_initial_df["id"] = expected_initial_df["id"].astype("Int64")
    expected_initial_df["nome"] = expected_initial_df["nome"].astype("string")
    pd.testing.assert_frame_equal(
        initial_result.reset_index(drop=True),
        expected_initial_df,
    )

    assert (
        insert_dataframe_to_db(
            replacement_df, temp_db_path, table_name, if_exists="replace"
        )
        is True
    )

    result = query_db(temp_db_path, table_name)
    expected_df = replacement_df.copy()
    expected_df["id"] = expected_df["id"].astype("Int64")
    expected_df["nome"] = expected_df["nome"].astype("string")
    pd.testing.assert_frame_equal(result.reset_index(drop=True), expected_df)


def test_insert_dataframe_to_db_rolls_back_partial_write_on_to_sql_failure(
    temp_db_path, monkeypatch
):
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
        conn.execute(
            "INSERT INTO teste_rollback (id, nome) VALUES (?, ?)", (999, "parcial")
        )
        raise RuntimeError("falha simulada no to_sql")

    monkeypatch.setattr(pd.DataFrame, "to_sql", _partial_insert_then_fail)
    try:
        assert insert_dataframe_to_db(df, temp_db_path, table_name) is False
    finally:
        monkeypatch.setattr(pd.DataFrame, "to_sql", original_to_sql)

    result = query_db(temp_db_path, table_name)
    assert result.empty
