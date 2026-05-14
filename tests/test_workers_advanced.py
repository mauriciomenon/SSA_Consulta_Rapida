"""
Testes Avancados para Workers Assincronos

Este modulo contem testes de unidade, integracao e regressao para os workers:
- DataLoaderWorker: Carregamento assincrono de dados do SQLite
- FilterWorker: Filtragem assincrona com cache LRU
- RescanWorker: Reescaneamento de dados

Arquitetura de Testes:
- Testes Unitarios: Testam metodos isolados
- Testes de Integracao: Testam workers com signals
- Testes de Regressao: Testam cenarios criticos identificados em producao
"""

import os
import sqlite3
import sys
import time
from contextlib import closing
from typing import Any, cast
from unittest.mock import patch

import pandas as pd
import pytest

# Skip se PyQt6 nao disponivel
pytest.importorskip(
    "PyQt6", reason="Dependencia PyQt6 indisponivel no ambiente de teste"
)
from PyQt6.QtCore import QThread
from PyQt6.QtWidgets import QApplication

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from gui.workers.data_loader_worker import DataLoaderWorker  # noqa: E402
from gui.workers.filter_worker import FilterWorker  # noqa: E402

# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture(scope="module", autouse=True)
def qapp():
    """Fixture para garantir QApplication disponivel."""
    app = QApplication.instance() or QApplication([])
    yield app


@pytest.fixture
def temp_db(tmp_path):
    """Cria banco de dados SQLite temporario com tabela ssa_table."""
    db_path = tmp_path / "test.db"
    with closing(sqlite3.connect(db_path)) as conn:
        conn.execute("""
            CREATE TABLE ssa_table (
                numero_ssa TEXT,
                situacao TEXT,
                data_cadastro TEXT,
                setor_emissor TEXT,
                setor_executor TEXT,
                descricao_ssa TEXT,
                localizacao_codigo TEXT,
                solicitante TEXT,
                derivada_de TEXT
            )
        """)
        # Inserir dados de teste
        for i in range(100):
            conn.execute(
                """
                INSERT INTO ssa_table VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    f"SSA-{i:04d}",
                    "APV" if i % 2 == 0 else "STE",
                    "2024-01-01",
                    "SETOR-A" if i % 3 == 0 else "SETOR-B",
                    "EXEC-01" if i % 4 == 0 else "EXEC-02",
                    f"Descricao da SSA {i}",
                    f"LOC-{i:03d}",
                    f"User-{i}",
                    None if i % 5 != 0 else f"SSA-{i - 5:04d}",
                ),
            )
        conn.commit()
    return str(db_path)


@pytest.fixture
def sample_dataframe():
    """Cria DataFrame de exemplo para testes de filtragem."""
    return pd.DataFrame(
        {
            "numero_ssa": [f"SSA-{i:04d}" for i in range(50)],
            "situacao": ["APV" if i % 2 == 0 else "STE" for i in range(50)],
            "setor_emissor": [
                "SETOR-A" if i % 3 == 0 else "SETOR-B" for i in range(50)
            ],
            "descricao_ssa": [f"Descricao {i}" for i in range(50)],
            "solicitante": [f"User-{i}" for i in range(50)],
        }
    )


@pytest.fixture
def empty_dataframe():
    """Cria DataFrame vazio para testes de edge case."""
    return pd.DataFrame(columns=["numero_ssa", "situacao", "descricao_ssa"])


# =============================================================================
# Testes Unitarios - DataLoaderWorker
# =============================================================================


class TestDataLoaderWorkerUnit:
    """Testes unitarios para DataLoaderWorker."""

    def test_sanitize_identifier_valid(self):
        """Testa sanitizacao de identificadores validos."""
        worker = DataLoaderWorker(":memory:", "test")

        assert worker._sanitize_identifier("valid_name") == "valid_name"
        assert worker._sanitize_identifier("_underscore") == "_underscore"
        assert worker._sanitize_identifier("name123") == "name123"
        assert worker._sanitize_identifier("  spaces  ") == "spaces"

    def test_sanitize_identifier_invalid(self):
        """Testa sanitizacao de identificadores invalidos (SQL injection)."""
        worker = DataLoaderWorker(":memory:", "test")

        assert worker._sanitize_identifier("drop table") == ""
        assert worker._sanitize_identifier("1numeric") == ""
        assert worker._sanitize_identifier("name;delete") == ""
        assert worker._sanitize_identifier("") == ""
        assert worker._sanitize_identifier(cast(Any, None)) == ""

    def test_quote_identifier(self):
        """Testa escaping de identificadores SQL."""
        worker = DataLoaderWorker(":memory:", "test")

        assert worker._quote_identifier("ssa_table") == '"ssa_table"'
        assert worker._quote_identifier('ssa"table') == '"ssa""table"'
        assert worker._quote_identifier("") == '""'

    def test_normalize_order_by_single_column(self):
        """Testa normalizacao de ORDER BY com uma coluna."""
        worker = DataLoaderWorker(":memory:", "test")

        result = worker._normalize_order_by("numero_ssa")
        assert result == '"numero_ssa" ASC'

        result = worker._normalize_order_by("numero_ssa DESC")
        assert result == '"numero_ssa" DESC'

    def test_normalize_order_by_multiple_columns(self):
        """Testa normalizacao de ORDER BY com multiplas colunas."""
        worker = DataLoaderWorker(":memory:", "test")

        result = worker._normalize_order_by("numero_ssa DESC, situacao ASC")
        assert result == '"numero_ssa" DESC, "situacao" ASC'

        result = worker._normalize_order_by("data_cadastro, setor_executor desc")
        assert result == '"data_cadastro" ASC, "setor_executor" DESC'

    def test_normalize_order_by_invalid_columns(self):
        """Testa rejeicao de colunas nao permitidas (protecao SQL injection)."""
        worker = DataLoaderWorker(":memory:", "test")

        with pytest.raises(ValueError, match="Coluna ORDER BY nao permitida"):
            worker._normalize_order_by("drop_table DESC")

        # SQL injection com multiplos tokens e detectado como ORDER BY invalido
        with pytest.raises(ValueError, match="ORDER BY invalido"):
            worker._normalize_order_by("numero_ssa; DELETE FROM ssa_table")

        with pytest.raises(ValueError, match="Direcao ORDER BY invalida"):
            worker._normalize_order_by("numero_ssa INVALID")

    def test_resolve_target_table_explicit(self, tmp_path):
        """Testa resolucao de tabela quando tabela solicitada existe."""
        db_path = tmp_path / "test.db"
        with closing(sqlite3.connect(db_path)) as conn:
            conn.execute("CREATE TABLE custom_table (id TEXT)")
            conn.commit()

        worker = DataLoaderWorker(str(db_path), "custom_table")
        assert worker._resolve_target_table() == "custom_table"

    def test_resolve_target_table_fallback(self, tmp_path):
        """Testa fallback para ssa_table quando tabela solicitada nao existe."""
        db_path = tmp_path / "test.db"
        with closing(sqlite3.connect(db_path)) as conn:
            conn.execute("CREATE TABLE ssa_table (id TEXT)")
            conn.commit()

        worker = DataLoaderWorker(str(db_path), "nonexistent_table")
        assert worker._resolve_target_table() == "ssa_table"

    def test_resolve_target_table_no_tables(self, tmp_path):
        """Testa comportamento quando nenhuma tabela existe."""
        db_path = tmp_path / "test.db"
        # Criar DB vazio
        with closing(sqlite3.connect(db_path)):
            pass

        worker = DataLoaderWorker(str(db_path), "test_table")
        # Deve retornar tabela solicitada como fallback
        assert worker._resolve_target_table() == "test_table"

    def test_resolve_target_table_rejects_invalid_identifier_and_falls_back_to_canonical(
        self, tmp_path
    ):
        """Testa que tabela invalida nao reaproveita politica local divergente."""
        db_path = tmp_path / "test.db"
        with closing(sqlite3.connect(db_path)):
            pass

        worker = DataLoaderWorker(str(db_path), "ssa_table; DROP TABLE ssa_table")
        assert worker._resolve_target_table() == "ssa_table"

    def test_sanitize_identifier_uses_central_identifier_policy(self):
        """Testa aderencia do worker ao utilitario central de identificadores."""
        worker = DataLoaderWorker(":memory:", "test")

        assert worker._sanitize_identifier("ssa_table") == "ssa_table"
        assert worker._sanitize_identifier(" numero_ssa ") == "numero_ssa"
        assert worker._sanitize_identifier("1numero_ssa") == ""
        assert worker._sanitize_identifier("numero-ssa") == ""
        assert worker._sanitize_identifier("numero_ssa;DROP") == ""


# =============================================================================
# Testes de Integracao - DataLoaderWorker
# =============================================================================


class TestDataLoaderWorkerIntegration:
    """Testes de integracao para DataLoaderWorker com signals."""

    def test_worker_emits_data_loaded(self, temp_db):
        """Testa emissao de signal data_loaded com dados reais."""
        emitted_data = []
        emitted_errors = []

        worker = DataLoaderWorker(temp_db, "ssa_table")
        worker.data_loaded.connect(lambda df: emitted_data.append(df))
        worker.error_occurred.connect(lambda msg: emitted_errors.append(msg))

        # Mock query_db para retornar dados reais
        def mock_query(db_path, table_name, query, **kwargs):
            conn = sqlite3.connect(db_path)
            return pd.read_sql_query(query, conn)

        with patch("gui.workers.data_loader_worker.query_db", side_effect=mock_query):
            worker.run()

        assert len(emitted_data) == 1
        assert len(emitted_errors) == 0
        assert len(emitted_data[0]) == 100
        assert "numero_ssa" in emitted_data[0].columns

    def test_worker_emits_error_on_db_failure(self):
        """Testa emissao de signal error_occurred em falha de DB."""
        emitted_errors = []
        emitted_data = []

        worker = DataLoaderWorker("/invalid/path/to/db.db", "ssa_table")
        worker.error_occurred.connect(lambda msg: emitted_errors.append(msg))
        worker.data_loaded.connect(lambda df: emitted_data.append(df))

        with patch(
            "gui.workers.data_loader_worker.query_db",
            side_effect=sqlite3.Error("Database error"),
        ):
            worker.run()

        assert len(emitted_errors) == 1
        assert len(emitted_data) == 0
        assert "Falha ao carregar" in emitted_errors[0]

    def test_worker_respects_limit_and_offset(self, temp_db):
        """Testa que worker respeita parametros de paginacao."""
        captured_query = {}

        def mock_query(db_path, table_name, query, **kwargs):
            captured_query["sql"] = query
            return pd.DataFrame()

        worker = DataLoaderWorker(temp_db, "ssa_table", limit=10, offset=20)
        with patch("gui.workers.data_loader_worker.query_db", side_effect=mock_query):
            worker.run()

        assert "LIMIT 10" in captured_query["sql"]
        assert "OFFSET 20" in captured_query["sql"]

    def test_worker_cancellation_before_start(self):
        """Testa cancelamento antes do inicio da execucao."""
        emitted_data = []
        emitted_errors = []

        worker = DataLoaderWorker(":memory:", "ssa_table")
        worker.data_loaded.connect(lambda df: emitted_data.append(df))
        worker.error_occurred.connect(lambda msg: emitted_errors.append(msg))

        # Cancelar antes de executar
        worker.cancel()

        with patch("gui.workers.data_loader_worker.query_db") as mock_query:
            worker.run()
            mock_query.assert_not_called()

        assert len(emitted_data) == 0
        assert len(emitted_errors) == 0

    def test_worker_cancellation_during_execution(self):
        """Testa cancelamento durante execucao."""
        emitted_data = []

        worker = DataLoaderWorker(":memory:", "ssa_table")
        worker.data_loaded.connect(lambda df: emitted_data.append(df))

        def mock_query_with_cancel(*args, **kwargs):
            # Simular cancelamento durante query
            worker.cancel()
            return pd.DataFrame({"test": [1]})

        with patch(
            "gui.workers.data_loader_worker.query_db",
            side_effect=mock_query_with_cancel,
        ):
            worker.run()

        # Nao deve emitir dados se cancelado
        assert len(emitted_data) == 0


# =============================================================================
# Testes Unitarios - FilterWorker
# =============================================================================


class TestFilterWorkerUnit:
    """Testes unitarios para FilterWorker."""

    def test_build_df_hash_empty_dataframe(self):
        """Testa hash de DataFrame vazio."""
        df = pd.DataFrame()
        hash_val = FilterWorker._build_df_hash(df)

        assert isinstance(hash_val, str)
        assert len(hash_val) == 16
        assert hash_val != ""

    def test_build_df_hash_none(self):
        """Testa hash quando DataFrame e None."""
        hash_val = FilterWorker._build_df_hash(cast(Any, None))

        assert isinstance(hash_val, str)
        assert len(hash_val) == 16

    def test_build_df_hash_small_dataframe(self):
        """Testa hash de DataFrame pequeno (< 24 linhas)."""
        df = pd.DataFrame({"col1": ["a", "b", "c"], "col2": [1, 2, 3]})

        hash1 = FilterWorker._build_df_hash(df)
        hash2 = FilterWorker._build_df_hash(df.copy())

        # Mesmo conteudo = mesmo hash
        assert hash1 == hash2
        assert len(hash1) == 16

    def test_build_df_hash_large_dataframe(self):
        """Testa hash de DataFrame grande (> 24 linhas) com amostragem."""
        # Criar DataFrame com 100 linhas
        df = pd.DataFrame(
            {"col1": [f"val_{i}" for i in range(100)], "col2": range(100)}
        )

        hash1 = FilterWorker._build_df_hash(df)
        hash2 = FilterWorker._build_df_hash(df.copy())

        # Mesmo conteudo = mesmo hash (mesmo com amostragem)
        assert hash1 == hash2

        # Alterar uma linha na amostra do meio (indice 35 esta na amostra)
        # Amostragem: head(8) + mid(8) + tail(8)
        # Para 100 linhas: mid comeca em 8, step ~12, indices: 8, 20, 32, 44, 56, 68, 80, 92
        df2 = df.copy()
        df2.loc[32, "col1"] = "altered_value"
        hash3 = FilterWorker._build_df_hash(df2)

        assert hash1 != hash3

    def test_build_df_hash_different_columns(self):
        """Testa que colunas diferentes produzem hashes diferentes."""
        df1 = pd.DataFrame({"col1": ["a", "b"], "col2": [1, 2]})
        df2 = pd.DataFrame({"col1": ["a", "b"], "col3": [1, 2]})

        hash1 = FilterWorker._build_df_hash(df1)
        hash2 = FilterWorker._build_df_hash(df2)

        assert hash1 != hash2

    def test_build_df_hash_different_types(self):
        """Testa que tipos diferentes produzem hashes diferentes."""
        df1 = pd.DataFrame({"col": [1, 2, 3]})  # int
        df2 = pd.DataFrame({"col": ["1", "2", "3"]})  # string

        hash1 = FilterWorker._build_df_hash(df1)
        hash2 = FilterWorker._build_df_hash(df2)

        assert hash1 != hash2

    def test_cache_is_class_level(self):
        """Testa que cache e compartilhado entre instancias."""
        cache1 = FilterWorker._cache
        cache2 = FilterWorker._cache

        assert cache1 is cache2

    def test_cancel_sets_flag(self):
        """Testa que cancel() seta flag de cancelamento."""
        worker = FilterWorker(pd.DataFrame(), [])

        assert not worker._cancel_requested
        worker.cancel()
        assert worker._cancel_requested


# =============================================================================
# Testes de Integracao - FilterWorker
# =============================================================================


class TestFilterWorkerIntegration:
    """Testes de integracao para FilterWorker com signals e cache."""

    def setup_method(self):
        """Limpa cache antes de cada teste."""
        cache = getattr(FilterWorker, "_cache", None)
        if cache and hasattr(cache, "clear"):
            cache.clear()

    def test_worker_emits_filter_finished(self, sample_dataframe):
        """Testa emissao de signal filter_finished com dados filtrados."""
        emitted = []
        errors = []

        worker = FilterWorker(sample_dataframe, [["APV"]])
        worker.filter_finished.connect(lambda df: emitted.append(df))
        worker.error_occurred.connect(lambda msg: errors.append(msg))

        with patch("gui.workers.filter_worker.parse_search_terms") as mock_parse:
            mock_parse.return_value = {"terms": ["APV"], "mode": "contains"}

            with patch("gui.workers.filter_worker.filter_dataframe") as mock_filter:
                mock_filter.return_value = sample_dataframe[
                    sample_dataframe["situacao"] == "APV"
                ]
                worker.run()

        assert len(emitted) == 1
        assert len(errors) == 0
        assert len(emitted[0]) == 25  # Metade e APV

    def test_worker_uses_cache_for_same_query(self, sample_dataframe):
        """Testa que worker usa cache para queries identicas."""
        call_count = [0]

        def mock_filter(df, parsed):
            call_count[0] += 1
            return df.head(5)

        # Primeira execucao
        worker1 = FilterWorker(sample_dataframe, [["test"]])
        with patch(
            "gui.workers.filter_worker.filter_dataframe", side_effect=mock_filter
        ):
            worker1.run()

        # Segunda execucao com mesmos parametros
        worker2 = FilterWorker(sample_dataframe, [["test"]])
        with patch(
            "gui.workers.filter_worker.filter_dataframe", side_effect=mock_filter
        ):
            worker2.run()

        # Deve usar cache na segunda vez
        assert call_count[0] == 1

    def test_worker_different_cache_context_misses_cache(self, sample_dataframe):
        """Testa que contextos diferentes nao compartilham cache."""
        call_count = [0]

        def mock_filter(df, parsed):
            call_count[0] += 1
            return df.head(5)

        # Mesmos parametros, contextos diferentes
        worker1 = FilterWorker(
            sample_dataframe, [["test"]], cache_context='{"adv":"A"}'
        )
        worker2 = FilterWorker(
            sample_dataframe, [["test"]], cache_context='{"adv":"B"}'
        )

        with patch(
            "gui.workers.filter_worker.filter_dataframe", side_effect=mock_filter
        ):
            worker1.run()
            worker2.run()

        # Deve executar filtro duas vezes (cache miss)
        assert call_count[0] == 2

    def test_worker_emits_empty_for_none_dataframe(self):
        """Testa comportamento quando df_completo e None."""
        emitted = []
        errors = []

        worker = FilterWorker(None, [["test"]])
        worker.filter_finished.connect(lambda df: emitted.append(df))
        worker.error_occurred.connect(lambda msg: errors.append(msg))

        worker.run()

        assert len(emitted) == 1
        assert emitted[0].empty
        assert len(errors) == 0

    def test_worker_handles_empty_chunks(self, sample_dataframe):
        """Testa comportamento com chunks vazios."""
        emitted = []

        worker = FilterWorker(sample_dataframe, [[]])  # Chunk vazio
        worker.filter_finished.connect(lambda df: emitted.append(df))

        worker.run()

        assert len(emitted) == 1
        # Deve retornar copia completa quando chunk esta vazio
        assert len(emitted[0]) == len(sample_dataframe)

    def test_worker_cancellation_before_processing(self, sample_dataframe):
        """Testa cancelamento antes do processamento."""
        emitted = []

        worker = FilterWorker(sample_dataframe, [["test"]])
        worker.filter_finished.connect(lambda df: emitted.append(df))

        worker.cancel()

        with patch("gui.workers.filter_worker.filter_dataframe") as mock_filter:
            worker.run()
            mock_filter.assert_not_called()

        assert len(emitted) == 0

    def test_worker_cancellation_between_chunks(self, sample_dataframe):
        """Testa cancelamento entre chunks."""
        call_count = [0]
        emitted = []

        def mock_filter_with_cancel(df, parsed):
            call_count[0] += 1
            if call_count[0] == 1:
                worker.cancel()  # Cancelar apos primeiro chunk
            return df.head(1)

        worker = FilterWorker(sample_dataframe, [["chunk1"], ["chunk2"]])
        worker.filter_finished.connect(lambda df: emitted.append(df))

        with patch(
            "gui.workers.filter_worker.filter_dataframe",
            side_effect=mock_filter_with_cancel,
        ):
            worker.run()

        assert call_count[0] == 1
        assert len(emitted) == 0  # Nao deve emitir se cancelado

    def test_worker_emits_error_on_exception(self, sample_dataframe):
        """Testa emissao de erro em excecao."""
        emitted = []
        errors = []

        worker = FilterWorker(sample_dataframe, [["test"]])
        worker.filter_finished.connect(lambda df: emitted.append(df))
        worker.error_occurred.connect(lambda msg: errors.append(msg))

        with patch(
            "gui.workers.filter_worker.parse_search_terms",
            side_effect=Exception("Parse error"),
        ):
            worker.run()

        assert len(emitted) == 0
        assert len(errors) == 1
        assert "Erro ao filtrar" in errors[0]


# =============================================================================
# Testes de Performance
# =============================================================================


class TestWorkerPerformance:
    """Testes de performance para workers."""

    def test_filter_worker_cache_performance(self):
        """Testa que cache melhora performance significativamente."""
        # Criar DataFrame grande
        df = pd.DataFrame(
            {"col1": [f"val_{i}" for i in range(10000)], "col2": range(10000)}
        )
        cache_context = f"perf-{time.perf_counter_ns()}"

        # Primeira execucao (sem cache)
        worker1 = FilterWorker(df, [["val_5000"]], cache_context=cache_context)
        start1 = time.perf_counter()

        def slow_filter(df, parsed):
            time.sleep(0.01)  # Simular processamento lento
            return df.head(100)

        with patch(
            "gui.workers.filter_worker.filter_dataframe", side_effect=slow_filter
        ):
            worker1.run()

        time_no_cache = time.perf_counter() - start1

        # Segunda execucao (com cache)
        worker2 = FilterWorker(df, [["val_5000"]], cache_context=cache_context)
        start2 = time.perf_counter()

        with patch(
            "gui.workers.filter_worker.filter_dataframe", side_effect=slow_filter
        ):
            worker2.run()

        time_with_cache = time.perf_counter() - start2

        # Com cache deve ser claramente mais rapido, mas sem threshold irreal.
        assert time_with_cache < time_no_cache * 0.5
        assert (time_no_cache - time_with_cache) > 0.005

    def test_build_df_hash_performance(self):
        """Testa performance do hash com DataFrames grandes."""
        # Criar DataFrame com 100.000 linhas
        df = pd.DataFrame(
            {
                "col1": [f"val_{i}" for i in range(100000)],
                "col2": range(100000),
                "col3": [f"desc_{i}" for i in range(100000)],
            }
        )

        start = time.time()
        hash_val = FilterWorker._build_df_hash(df)
        elapsed = time.time() - start

        # Deve completar em menos de 1 segundo mesmo com 100k linhas
        assert elapsed < 1.0
        assert isinstance(hash_val, str)


# =============================================================================
# Testes de Regressao
# =============================================================================


class TestWorkerRegression:
    """Testes de regressao para bugs identificados em producao."""

    def test_data_loader_sql_injection_protection(self):
        """Testa protecao contra SQL injection em ORDER BY."""
        worker = DataLoaderWorker(":memory:", "ssa_table")

        # Tentativas de SQL injection devem ser rejeitadas
        malicious_inputs = [
            "numero_ssa; DROP TABLE ssa_table",
            "numero_ssa -- comment",
            "numero_ssa UNION SELECT * FROM passwords",
            "(SELECT password FROM users)",
            "numero_ssa DESC; INSERT INTO ...",
        ]

        for malicious in malicious_inputs:
            with pytest.raises(ValueError):
                worker._normalize_order_by(malicious)

    def test_filter_worker_handles_special_characters_in_data(self):
        """Testa que worker lida com caracteres especiais nos dados."""
        df = pd.DataFrame(
            {
                "texto": [
                    "normal",
                    "com acentuacao: cao",
                    "emojis: ",
                    "html: <script>alert(1)</script>",
                    "sql: '; DROP TABLE --",
                    "novas\nlinhas",
                    "tabs\taqui",
                    "unicode: TMR",
                ]
            }
        )

        # Deve conseguir criar hash sem erro
        hash_val = FilterWorker._build_df_hash(df)
        assert isinstance(hash_val, str)

        # Deve executar sem erro
        worker = FilterWorker(df, [["test"]])
        emitted = []
        worker.filter_finished.connect(lambda df: emitted.append(df))

        worker.run()

        assert len(emitted) == 1

    def test_workers_handle_concurrent_access(self):
        """Testa comportamento com acesso concorrente ao cache."""
        import threading

        df = pd.DataFrame({"col": range(100)})
        results = []
        errors = []

        def run_worker(thread_id):
            try:
                worker = FilterWorker(df, [[f"thread_{thread_id}"]])

                def mock_filter(df, parsed):
                    return df.head(10)

                with patch(
                    "gui.workers.filter_worker.filter_dataframe",
                    side_effect=mock_filter,
                ):
                    worker.run()
                    results.append(thread_id)
            except Exception as e:
                errors.append((thread_id, str(e)))

        # Executar 10 workers em paralelo
        threads = []
        for i in range(10):
            t = threading.Thread(target=run_worker, args=(i,))
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        # Todos devem completar sem erro
        assert len(results) == 10
        assert len(errors) == 0


# =============================================================================
# Fixtures e Helpers Adicionais
# =============================================================================


@pytest.fixture
def mock_qt_thread():
    """Fixture para mock de QThread quando necessario."""
    with patch.object(QThread, "start") as mock_start:
        with patch.object(QThread, "wait") as mock_wait:
            yield {"start": mock_start, "wait": mock_wait}


@pytest.fixture
def signal_collector():
    """Helper para coletar signals emitidos."""

    class SignalCollector:
        def __init__(self):
            self.data = []
            self.errors = []

        def on_data(self, df):
            self.data.append(df)

        def on_error(self, msg):
            self.errors.append(msg)

    return SignalCollector()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
