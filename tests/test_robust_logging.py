#!/usr/bin/env python3
"""
Testes do sistema de logging robusto.
"""

import json
import logging
import os

# Importar o módulo de logging robusto
import sys
import tempfile
import time
import unittest
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from utils.robust_logging import (
    ContextFilter,
    JSONFormatter,
    PerformanceMetrics,
    RobustLogger,
    get_robust_logger,
)


class TestRobustLogging(unittest.TestCase):
    """Testes do sistema de logging robusto."""

    def setUp(self):
        """Configuração inicial dos testes."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.config_file = self.temp_dir / "test_logging.json"
        self.logs_dir = self.temp_dir / "logs"
        self.logs_dir.mkdir(exist_ok=True)

        # Configuração de teste
        self.test_config = {
            "version": "1.0",
            "logging": {
                "level": "DEBUG",
                "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                "handlers": {
                    "console": {"level": "INFO", "format": "console"},
                    "file": {
                        "level": "DEBUG",
                        "rotation": {"max_bytes": 1048576, "backup_count": 2},
                    },
                    "json": {"level": "INFO", "include_metrics": True},
                },
                "components": {
                    "gui": "DEBUG",
                    "cli": "INFO",
                    "streamlit": "INFO",
                    "database": "WARNING",
                    "main": "INFO",
                },
            },
            "paths": {"logs_dir": str(self.logs_dir)},
        }

        # Salvar configuração de teste
        with open(self.config_file, "w", encoding="utf-8") as f:
            json.dump(self.test_config, f, indent=2)

    def tearDown(self):
        """Limpeza após os testes."""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_performance_metrics(self):
        """Testa coleta de métricas de performance."""
        metrics = PerformanceMetrics()

        # Testa métricas de tempo
        metrics.add_filter_time(0.1)
        metrics.add_filter_time(0.2)
        metrics.add_import_time(1.5)
        metrics.add_query_time(0.05)

        # Testa contadores de cache
        metrics.increment_cache_hit()
        metrics.increment_cache_hit()
        metrics.increment_cache_miss()

        # Testa contadores de eventos
        metrics.increment_error()
        metrics.increment_warning()

        stats = metrics.get_stats()

        # Verifica estatísticas de tempo
        self.assertEqual(stats["filter_times"]["count"], 2)
        self.assertEqual(stats["filter_times"]["avg"], 0.15)
        self.assertEqual(stats["import_times"]["count"], 1)
        self.assertEqual(stats["query_times"]["count"], 1)

        # Verifica cache
        self.assertEqual(stats["cache"]["hits"], 2)
        self.assertEqual(stats["cache"]["misses"], 1)
        self.assertAlmostEqual(stats["cache"]["hit_rate"], 66.67, places=1)

        # Verifica contadores
        self.assertEqual(stats["counters"]["errors"], 1)
        self.assertEqual(stats["counters"]["warnings"], 1)

    def test_json_formatter(self):
        """Testa formatação JSON dos logs."""
        formatter = JSONFormatter(include_metrics=True)

        # Criar um record de teste
        logging.getLogger("test")
        record = logging.LogRecord(
            name="test.module",
            level=logging.INFO,
            pathname="/test/file.py",
            lineno=42,
            msg="Test message %s",
            args=("arg1",),
            exc_info=None,
        )

        # Adicionar contexto extra
        record.component = "gui"
        record.operation = "filter_data"
        record.duration = 0.123

        formatted = formatter.format(record)
        log_data = json.loads(formatted)

        # Verificar estrutura JSON
        self.assertIn("timestamp", log_data)
        self.assertEqual(log_data["level"], "INFO")
        self.assertEqual(log_data["logger"], "test.module")
        self.assertEqual(log_data["message"], "Test message arg1")
        self.assertEqual(log_data["component"], "gui")
        self.assertEqual(log_data["operation"], "filter_data")
        self.assertEqual(log_data["duration_ms"], 123.0)
        self.assertIn("metrics", log_data)

    def test_context_filter(self):
        """Testa filtro de contexto automático."""
        context_filter = ContextFilter("test_component")

        # Criar record de teste
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="/test.py",
            lineno=1,
            msg="Test",
            args=(),
            exc_info=None,
        )

        # Aplicar filtro
        result = context_filter.filter(record)

        self.assertTrue(result)
        self.assertEqual(getattr(record, "component", None), "test_component")
        self.assertIn("session_", getattr(record, "session_id", ""))

    def test_robust_logger_creation(self):
        """Testa criação do logger robusto."""
        robust_logger = RobustLogger(str(self.config_file))

        # Verificar inicialização
        self.assertIsNotNone(robust_logger.config)
        self.assertEqual(robust_logger.config["version"], "1.0")

        # Obter logger configurado
        logger = robust_logger.get_logger("test_module", "gui")
        self.assertIsNotNone(logger)
        self.assertEqual(logger.name, "test_module")

    def test_get_robust_logger_function(self):
        """Testa função de conveniência get_robust_logger."""
        robust_logger_instance = get_robust_logger(str(self.config_file))

        self.assertIsNotNone(robust_logger_instance)
        # A função retorna a instância RobustLogger, não um Logger
        self.assertIsInstance(robust_logger_instance, RobustLogger)

        # Obter um logger real para teste
        logger = robust_logger_instance.get_logger("test_module")
        logger.info(
            "Test message", extra={"component": "test", "operation": "unit_test"}
        )

        # Verificar que não houve exceções
        self.assertTrue(True)

    def test_log_files_creation(self):
        """Testa criação de arquivos de log."""
        robust_logger = RobustLogger(str(self.config_file))
        logger = robust_logger.get_logger("test_file_creation")

        # Gerar alguns logs
        logger.info("Test info message")
        logger.warning("Test warning message")
        logger.error("Test error message")

        # Aguardar flush dos handlers
        for handler in logger.handlers:
            handler.flush()

        # Verificar arquivos criados
        log_files = list(self.logs_dir.glob("*.log"))
        json_files = list(self.logs_dir.glob("*.json"))

        self.assertTrue(
            len(log_files) > 0 or len(json_files) > 0,
            "Nenhum arquivo de log foi criado",
        )

    def test_component_specific_levels(self):
        """Testa níveis específicos por componente."""
        robust_logger = RobustLogger(str(self.config_file))

        # GUI deve estar em DEBUG
        gui_logger = robust_logger.get_logger("gui_module", "gui")
        self.assertEqual(gui_logger.level, logging.DEBUG)

        # Database deve estar em WARNING
        db_logger = robust_logger.get_logger("db_module", "database")
        self.assertEqual(db_logger.level, logging.WARNING)

    def test_error_handling(self):
        """Testa tratamento de erros de configuração."""
        # Arquivo inexistente - deve usar configuração padrão
        robust_logger = RobustLogger("/caminho/inexistente.json")
        self.assertIsNotNone(robust_logger.config)

        # Arquivo JSON inválido
        invalid_config = self.temp_dir / "invalid.json"
        with open(invalid_config, "w") as f:
            f.write("{ invalid json")

        robust_logger = RobustLogger(str(invalid_config))
        self.assertIsNotNone(robust_logger.config)

        # JSON valido, mas com raiz estruturalmente invalida.
        malformed_shape_config = self.temp_dir / "malformed_shape.json"
        malformed_shape_config.write_text("[]", encoding="utf-8")
        robust_logger = RobustLogger(str(malformed_shape_config))
        self.assertEqual(robust_logger.config["version"], "1.0")


def run_performance_test():
    """Executa teste de performance do sistema de logging."""
    print("\n=== Teste de Performance do Logging Robusto ===")

    with tempfile.TemporaryDirectory() as temp_dir:
        config_file = Path(temp_dir) / "perf_config.json"
        logs_dir = Path(temp_dir) / "logs"
        logs_dir.mkdir()

        config = {
            "version": "1.0",
            "logging": {
                "level": "INFO",
                "handlers": {
                    "console": {"level": "WARNING"},
                    "file": {
                        "level": "INFO",
                        "rotation": {"max_bytes": 1048576, "backup_count": 1},
                    },
                    "json": {"level": "INFO", "include_metrics": True},
                },
            },
            "paths": {"logs_dir": str(logs_dir)},
        }

        with open(config_file, "w") as f:
            json.dump(config, f)

        # Teste de performance
        robust_logger = get_robust_logger(str(config_file))
        logger = robust_logger.get_logger("performance_test")

        start_time = time.time()

        for i in range(1000):
            logger.info(
                f"Performance test message {i}",
                extra={"component": "test", "operation": "performance"},
            )

            if i % 100 == 0:
                logger.warning(f"Progress checkpoint: {i}")

        end_time = time.time()
        duration = end_time - start_time

        print(f"Tempo para 1000 logs: {duration:.3f}s")
        print(f"Logs por segundo: {1000 / duration:.1f}")

        # Verificar arquivos criados
        log_files = list(logs_dir.glob("*"))
        print(f"Arquivos criados: {len(log_files)}")
        for file in log_files:
            size_kb = file.stat().st_size / 1024
            print(f"  {file.name}: {size_kb:.1f} KB")


if __name__ == "__main__":
    # Executar testes unitários
    unittest.main(verbosity=2, exit=False)

    # Executar teste de performance
    run_performance_test()
