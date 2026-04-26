# tests/performance_tests.py
"""
Testes de performance e carga para o sistema SSA Consulta Rápida.
"""

import concurrent.futures
import importlib
import os
import sys
import threading
import time
from datetime import datetime
from typing import Any, Dict, cast

import pandas as pd

try:
    psutil = cast(Any, importlib.import_module("psutil"))
    PSUTIL_AVAILABLE = True
except ImportError:
    psutil = None
    PSUTIL_AVAILABLE = False

# Verificar se memory_profiler está disponível
try:
    profile = getattr(importlib.import_module("memory_profiler"), "profile")
    MEMORY_PROFILER_AVAILABLE = True
except ImportError:
    MEMORY_PROFILER_AVAILABLE = False

    # Criar decorator dummy
    def profile(func):
        return func


# Adicionar diretório raiz ao path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from armazenamento.database import get_db_connection  # noqa: E402
from core.app_logic import get_filtered_data  # noqa: E402
from extracao.extractor import extract_data_from_excel as extract_data_from_file  # noqa: E402


class PerformanceMetrics:
    """Coletores de métricas de performance."""

    def __init__(self):
        self.start_time = None
        self.end_time = None
        self.peak_memory_mb = 0
        self.start_memory_mb = 0
        self.cpu_percent = []
        self.monitoring = False

    def start_monitoring(self):
        """Inicia monitoramento de recursos."""
        self.start_time = time.time()
        if PSUTIL_AVAILABLE and psutil is not None:
            self.start_memory_mb = psutil.Process().memory_info().rss / 1024 / 1024
        else:
            self.start_memory_mb = 0
        self.peak_memory_mb = self.start_memory_mb
        self.monitoring = True

        # Thread para monitoramento contínuo
        def monitor():
            while self.monitoring:
                if PSUTIL_AVAILABLE and psutil is not None:
                    current_memory = psutil.Process().memory_info().rss / 1024 / 1024
                    self.peak_memory_mb = max(self.peak_memory_mb, current_memory)
                    self.cpu_percent.append(psutil.cpu_percent())
                time.sleep(0.1)

        self.monitor_thread = threading.Thread(target=monitor)
        self.monitor_thread.daemon = True
        self.monitor_thread.start()

    def stop_monitoring(self):
        """Para monitoramento e calcula métricas finais."""
        self.monitoring = False
        self.end_time = time.time()
        if self.start_time is None:
            raise RuntimeError("start_monitoring nao foi chamado")
        if self.end_time is None:
            raise RuntimeError("end_time nao definido")
        cpu_samples = len(self.cpu_percent)
        avg_cpu_percent = (
            (sum(self.cpu_percent) / cpu_samples) if cpu_samples > 0 else 0.0
        )
        max_cpu_percent = max(self.cpu_percent) if cpu_samples > 0 else 0.0

        return {
            "duration_seconds": self.end_time - self.start_time,
            "memory_used_mb": self.peak_memory_mb - self.start_memory_mb,
            "peak_memory_mb": self.peak_memory_mb,
            "avg_cpu_percent": avg_cpu_percent,
            "max_cpu_percent": max_cpu_percent,
        }


class PerformanceTester:
    """Executor de testes de performance."""

    def __init__(self, db_path: str = "data/ssas.db"):
        self.db_path = db_path
        self.results = []

    def test_database_query_performance(self) -> Dict:
        """Testa performance de consultas ao banco."""
        print("INFO Testando performance de consultas ao banco...")

        queries = [
            ("SELECT COUNT(*) FROM ssas", "count_all"),
            ("SELECT * FROM ssas LIMIT 1000", "select_1000"),
            ("SELECT DISTINCT situacao FROM ssas", "distinct_situacao"),
            ("SELECT * FROM ssas WHERE situacao = 'EM EXECUÇÃO'", "filter_em_execucao"),
            (
                "SELECT numero_ssa, situacao, setor_executor FROM ssas ORDER BY numero_ssa DESC LIMIT 500",
                "ordered_select",
            ),
        ]

        query_results = []

        for query, query_name in queries:
            metrics = PerformanceMetrics()
            metrics.start_monitoring()

            try:
                with get_db_connection(self.db_path) as conn:
                    df = pd.read_sql_query(query, conn)
                    result_count = len(df)

                perf_metrics = metrics.stop_monitoring()
                perf_metrics.update(
                    {
                        "query_name": query_name,
                        "result_count": result_count,
                        "success": True,
                    }
                )

            except Exception as e:
                perf_metrics = metrics.stop_monitoring()
                perf_metrics.update(
                    {"query_name": query_name, "success": False, "error": str(e)}
                )

            query_results.append(perf_metrics)
            print(f"  {query_name}: {perf_metrics['duration_seconds']:.3f}s")

        return {
            "test_name": "database_query_performance",
            "query_results": query_results,
            "avg_duration": sum(r["duration_seconds"] for r in query_results)
            / len(query_results),
            "total_duration": sum(r["duration_seconds"] for r in query_results),
        }

    def test_concurrent_access(self, num_threads: int = 5) -> Dict:
        """Testa acesso concurrent ao banco."""
        print(f" Testando acesso concorrente ({num_threads} threads)...")

        def worker_query(thread_id: int) -> Dict:
            """Função executada por cada thread."""
            metrics = PerformanceMetrics()
            metrics.start_monitoring()

            try:
                # Cada thread faz múltiplas consultas
                queries_per_thread = 10
                results = []

                for i in range(queries_per_thread):
                    with get_db_connection(self.db_path) as conn:
                        # Alternar entre diferentes tipos de consulta
                        if i % 3 == 0:
                            df = pd.read_sql_query("SELECT COUNT(*) FROM ssas", conn)
                        elif i % 3 == 1:
                            df = pd.read_sql_query("SELECT * FROM ssas LIMIT 100", conn)
                        else:
                            df = pd.read_sql_query(
                                "SELECT DISTINCT situacao FROM ssas", conn
                            )

                        results.append(len(df))

                perf_metrics = metrics.stop_monitoring()
                perf_metrics.update(
                    {
                        "thread_id": thread_id,
                        "queries_executed": queries_per_thread,
                        "success": True,
                    }
                )

                return perf_metrics

            except Exception as e:
                perf_metrics = metrics.stop_monitoring()
                perf_metrics.update(
                    {"thread_id": thread_id, "success": False, "error": str(e)}
                )
                return perf_metrics

        # Executar threads concorrentes
        start_time = time.time()

        with concurrent.futures.ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [executor.submit(worker_query, i) for i in range(num_threads)]
            thread_results = [
                future.result() for future in concurrent.futures.as_completed(futures)
            ]

        total_time = time.time() - start_time
        successful_threads = sum(
            1 for result in thread_results if result.get("success", False)
        )

        return {
            "test_name": "concurrent_access",
            "num_threads": num_threads,
            "successful_threads": successful_threads,
            "total_time": total_time,
            "avg_thread_time": sum(r["duration_seconds"] for r in thread_results)
            / len(thread_results),
            "thread_results": thread_results,
        }

    def test_large_filter_performance(self) -> Dict:
        """Testa performance de filtros com grandes volumes de dados."""
        print("INFO Testando performance de filtros com grandes volumes...")

        filter_tests = [
            ({"situacao": "EM EXECUÇÃO"}, "filter_by_situacao"),
            ({"setor_executor": "MEDEIRO"}, "filter_by_setor"),
            ({}, "no_filter_all_data"),
            (
                {"situacao": "EM EXECUÇÃO", "setor_executor": "MEDEIRO"},
                "multiple_filters",
            ),
        ]

        filter_results = []

        for filters, test_name in filter_tests:
            metrics = PerformanceMetrics()
            metrics.start_monitoring()

            try:
                filtered_data = get_filtered_data(db_path=self.db_path, filters=filters)

                result_count = len(filtered_data) if filtered_data is not None else 0

                perf_metrics = metrics.stop_monitoring()
                perf_metrics.update(
                    {
                        "test_name": test_name,
                        "result_count": result_count,
                        "filters_applied": len(filters),
                        "success": True,
                    }
                )

            except Exception as e:
                perf_metrics = metrics.stop_monitoring()
                perf_metrics.update(
                    {"test_name": test_name, "success": False, "error": str(e)}
                )

            filter_results.append(perf_metrics)
            print(
                f"  {test_name}: {perf_metrics['duration_seconds']:.3f}s ({perf_metrics.get('result_count', 0)} registros)"
            )

        return {
            "test_name": "large_filter_performance",
            "filter_results": filter_results,
            "avg_duration": sum(r["duration_seconds"] for r in filter_results)
            / len(filter_results),
        }

    def test_file_extraction_performance(self) -> Dict:
        """Testa performance de extração de arquivos Excel."""
        print("IN Testando performance de extração de arquivos...")

        docs_entrada = "docs_entrada"
        if not os.path.exists(docs_entrada):
            return {
                "test_name": "file_extraction_performance",
                "success": False,
                "error": "Diretório docs_entrada não encontrado",
            }

        excel_files = [
            f
            for f in os.listdir(docs_entrada)
            if f.endswith((".xlsx", ".xls")) and not f.startswith("~$")
        ]

        if not excel_files:
            return {
                "test_name": "file_extraction_performance",
                "success": False,
                "error": "Nenhum arquivo Excel encontrado",
            }

        extraction_results = []
        total_rows = 0

        for file_name in excel_files[:10]:  # Limitar a 10 arquivos para performance
            file_path = os.path.join(docs_entrada, file_name)

            metrics = PerformanceMetrics()
            metrics.start_monitoring()

            try:
                df = extract_data_from_file(file_path)
                rows = len(df) if df is not None else 0
                total_rows += rows

                perf_metrics = metrics.stop_monitoring()
                perf_metrics.update(
                    {
                        "file_name": file_name,
                        "rows_extracted": rows,
                        "file_size_mb": os.path.getsize(file_path) / 1024 / 1024,
                        "success": True,
                    }
                )

            except Exception as e:
                perf_metrics = metrics.stop_monitoring()
                perf_metrics.update(
                    {"file_name": file_name, "success": False, "error": str(e)}
                )

            extraction_results.append(perf_metrics)
            print(
                f"  {file_name}: {perf_metrics['duration_seconds']:.3f}s ({perf_metrics.get('rows_extracted', 0)} linhas)"
            )

        return {
            "test_name": "file_extraction_performance",
            "extraction_results": extraction_results,
            "total_files_processed": len(extraction_results),
            "total_rows_extracted": total_rows,
            "avg_duration_per_file": sum(
                r["duration_seconds"] for r in extraction_results
            )
            / len(extraction_results),
            "total_duration": sum(r["duration_seconds"] for r in extraction_results),
        }

    def test_memory_usage_patterns(self) -> Dict:
        """Testa padrões de uso de memória."""
        print(" Testando padrões de uso de memória...")

        memory_tests = []

        # Teste 1: Carregamento de dados grandes
        metrics = PerformanceMetrics()
        metrics.start_monitoring()

        try:
            with get_db_connection(self.db_path) as conn:
                # Carregar todos os dados
                df = pd.read_sql_query("SELECT * FROM ssas", conn)

                # Fazer operações que consomem memória
                df_copy = df.copy()
                df_sorted = (
                    df.sort_values("numero_ssa") if "numero_ssa" in df.columns else df
                )
                df_grouped = (
                    df.groupby("situacao").size()
                    if "situacao" in df.columns
                    else pd.Series()
                )

                # Limpar objetos grandes
                del df_copy, df_sorted, df_grouped

            perf_metrics = metrics.stop_monitoring()
            perf_metrics.update(
                {
                    "test_name": "large_data_loading",
                    "records_processed": len(df),
                    "success": True,
                }
            )

        except Exception as e:
            perf_metrics = metrics.stop_monitoring()
            perf_metrics.update(
                {"test_name": "large_data_loading", "success": False, "error": str(e)}
            )

        memory_tests.append(perf_metrics)

        # Teste 2: Multiple operações
        metrics = PerformanceMetrics()
        metrics.start_monitoring()

        try:
            for i in range(10):
                _ = get_filtered_data(
                    db_path=self.db_path,
                    filters={"situacao": "EM EXECUÇÃO"} if i % 2 == 0 else {},
                )

            perf_metrics = metrics.stop_monitoring()
            perf_metrics.update(
                {
                    "test_name": "multiple_operations",
                    "operations_count": 10,
                    "success": True,
                }
            )

        except Exception as e:
            perf_metrics = metrics.stop_monitoring()
            perf_metrics.update(
                {"test_name": "multiple_operations", "success": False, "error": str(e)}
            )

        memory_tests.append(perf_metrics)

        return {
            "test_name": "memory_usage_patterns",
            "memory_tests": memory_tests,
            "peak_memory_mb": max(t["peak_memory_mb"] for t in memory_tests),
            "avg_memory_usage_mb": sum(t["memory_used_mb"] for t in memory_tests)
            / len(memory_tests),
        }

    def run_all_performance_tests(self) -> Dict:
        """Executa todos os testes de performance."""
        print("START Iniciando testes de performance do sistema SSA...")
        print("=" * 60)

        start_time = time.time()

        # Lista de testes de performance
        tests = [
            self.test_database_query_performance,
            self.test_concurrent_access,
            self.test_large_filter_performance,
            self.test_file_extraction_performance,
            self.test_memory_usage_patterns,
        ]

        test_results = []

        for test_func in tests:
            try:
                result = test_func()
                test_results.append(result)
            except Exception as e:
                test_results.append(
                    {"test_name": test_func.__name__, "success": False, "error": str(e)}
                )

            print()  # Linha em branco entre testes

        total_time = time.time() - start_time

        # Calcular estatísticas gerais
        successful_tests = sum(
            1 for result in test_results if result.get("success", True)
        )

        print("=" * 60)
        print("INFO RESULTADO DOS TESTES DE PERFORMANCE:")
        print(f"   Total de Testes: {len(test_results)}")
        print(f"   Testes Bem-sucedidos: {successful_tests}")
        print(f"   Duração Total: {total_time:.2f}s")

        return {
            "total_tests": len(test_results),
            "successful_tests": successful_tests,
            "total_duration_seconds": total_time,
            "test_results": test_results,
            "timestamp": datetime.now().isoformat(),
        }


def main():
    """Função principal para executar testes de performance."""
    tester = PerformanceTester()
    results = tester.run_all_performance_tests()

    # Salvar resultados
    import json

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = f"docs_saida/performance_tests_{timestamp}.json"

    os.makedirs("docs_saida", exist_ok=True)
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    print(f"\nFILE Resultados salvos em: {output_file}")

    return 0


if __name__ == "__main__":
    exit(main())
