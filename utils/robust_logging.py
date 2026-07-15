#!/usr/bin/env python3
"""
Sistema de logging robusto e configurável para SSA Consulta Rápida.

Funcionalidades:
- Múltiplos níveis de logging (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- Rotação automática de arquivos (tamanho e tempo)
- Formatação padronizada com contexto
- Logs estruturados em JSON para análise
- Configuração via arquivo JSON
- Integração com métricas de performance
- Filtragem por módulo/componente
"""

import json
import logging
import logging.handlers
import os
import sys
import threading
import time
from collections import deque
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional


class PerformanceMetrics:
    """Coleta e mantém métricas de performance para logging."""

    def __init__(self, max_samples=1000):
        self.max_samples = max_samples
        self._metrics: Dict[str, Any] = {
            "filter_times": deque(maxlen=max_samples),
            "import_times": deque(maxlen=max_samples),
            "query_times": deque(maxlen=max_samples),
            "cache_hits": 0,
            "cache_misses": 0,
            "errors_count": 0,
            "warnings_count": 0,
        }
        self._lock = threading.Lock()

    def add_filter_time(self, duration: float):
        """Adiciona tempo de filtro às métricas."""
        with self._lock:
            self._metrics["filter_times"].append(duration)

    def add_import_time(self, duration: float):
        """Adiciona tempo de importação às métricas."""
        with self._lock:
            self._metrics["import_times"].append(duration)

    def add_query_time(self, duration: float):
        """Adiciona tempo de query SQL às métricas."""
        with self._lock:
            self._metrics["query_times"].append(duration)

    def increment_cache_hit(self):
        """Incrementa contador de cache hits."""
        with self._lock:
            self._metrics["cache_hits"] += 1

    def increment_cache_miss(self):
        """Incrementa contador de cache misses."""
        with self._lock:
            self._metrics["cache_misses"] += 1

    def increment_error(self):
        """Incrementa contador de erros."""
        with self._lock:
            self._metrics["errors_count"] += 1

    def increment_warning(self):
        """Incrementa contador de warnings."""
        with self._lock:
            self._metrics["warnings_count"] += 1

    def get_stats(self) -> Dict[str, Any]:
        """Retorna estatísticas atuais das métricas."""
        with self._lock:
            stats = {}

            # Estatísticas de tempo
            for key in ["filter_times", "import_times", "query_times"]:
                times = list(self._metrics[key])
                if times:
                    avg = round(sum(times) / len(times), 6)
                    stats[key] = {
                        "count": len(times),
                        "avg": avg,
                        "min": min(times),
                        "max": max(times),
                        "last": times[-1] if times else 0,
                    }
                else:
                    stats[key] = {"count": 0, "avg": 0, "min": 0, "max": 0, "last": 0}

            # Contadores
            total_cache = self._metrics["cache_hits"] + self._metrics["cache_misses"]
            cache_rate = (
                (self._metrics["cache_hits"] / total_cache * 100)
                if total_cache > 0
                else 0
            )

            stats["cache"] = {
                "hits": self._metrics["cache_hits"],
                "misses": self._metrics["cache_misses"],
                "hit_rate": cache_rate,
            }

            stats["counters"] = {
                "errors": self._metrics["errors_count"],
                "warnings": self._metrics["warnings_count"],
            }

            return stats


class JSONFormatter(logging.Formatter):
    """Formatter que gera logs em formato JSON estruturado."""

    def __init__(self, include_metrics=True):
        super().__init__()
        self.include_metrics = include_metrics
        self.metrics = PerformanceMetrics()

    def format(self, record: logging.LogRecord) -> str:
        """Formata record como JSON estruturado."""
        log_obj: Dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Adiciona contexto extra se disponível
        if hasattr(record, "user_id"):
            log_obj["user_id"] = getattr(record, "user_id", None)
        if hasattr(record, "session_id"):
            log_obj["session_id"] = getattr(record, "session_id", None)
        if hasattr(record, "component"):
            log_obj["component"] = getattr(record, "component", None)
        if hasattr(record, "operation"):
            log_obj["operation"] = getattr(record, "operation", None)
        if hasattr(record, "duration"):
            duration = getattr(record, "duration", 0)
            log_obj["duration_ms"] = duration * 1000 if duration else 0

        # Adiciona métricas de performance se habilitado
        if self.include_metrics and record.levelname in ["INFO", "WARNING", "ERROR"]:
            log_obj["metrics"] = self.metrics.get_stats()

        # Adiciona exceção se presente
        if record.exc_info:
            log_obj["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_obj, ensure_ascii=False)


class ContextFilter(logging.Filter):
    """Filtro que adiciona contexto automático aos logs e garante campos esperados.

    Importante: Sempre define o atributo 'component' no record para evitar
    KeyError em format strings que incluam %(component)s.
    """

    def __init__(self, component_name: Optional[str] = None):
        super().__init__()
        self.component_name = component_name
        self.session_id = f"session_{int(time.time())}"

    def filter(self, record):
        """Adiciona contexto automático ao record e garante campos padrão."""
        # Garante 'component' mesmo quando não especificado
        try:
            if self.component_name:
                record.component = self.component_name
            else:
                # Usa existente, ou o nome do logger, ou '-'
                if not hasattr(record, "component") or getattr(
                    record, "component", None
                ) in (None, ""):
                    record.component = getattr(record, "name", "-") or "-"
        except Exception:
            # Último recurso
            record.component = "-"

        # IDs auxiliares
        record.session_id = self.session_id

        # Adiciona thread info
        try:
            record.thread_name = threading.current_thread().name
        except Exception:
            record.thread_name = "main"

        return True


class SafeFormatter(logging.Formatter):
    """Formatter tolerante a campos faltando em record.__dict__.

    Evita ValueError/KeyError quando algum campo opcional (ex.: component)
    não estiver presente por qualquer motivo.
    """

    def format(self, record: logging.LogRecord) -> str:
        # Garante chaves usadas no formato
        if not hasattr(record, "component"):
            setattr(record, "component", getattr(record, "name", "-") or "-")
        if not hasattr(record, "session_id"):
            setattr(record, "session_id", "-")
        if not hasattr(record, "thread_name"):
            setattr(record, "thread_name", threading.current_thread().name)
        try:
            return super().format(record)
        except Exception:
            # Fallback mínimo em caso de erro de formatação
            basic = f"{record.levelname} {record.name}: {record.getMessage()}"
            return basic


class RobustLogger:
    """Sistema de logging robusto e configurável."""

    def __init__(self, config_path: Optional[str] = None):
        self.config = self._load_config(config_path)
        self.metrics = PerformanceMetrics()
        self.loggers = {}
        self._setup_root_logger()

    def _load_config(self, config_path: Optional[str]) -> Dict:
        """Carrega configuração do logging."""
        base_config: dict[str, Any] = {
            "version": "1.0",
            "level": "INFO",
            "console_level": "WARNING",
            "file_level": "DEBUG",
            "json_level": "INFO",
            "max_file_size": 5242880,  # 5MB
            "backup_count": 5,
            "json_backup_count": 3,
            "enable_console": True,
            "enable_file": True,
            "enable_json": True,
            "enable_metrics": True,
            "log_dir": "logs",
            "filename": "ssa.log",
            "json_filename": "ssa.json",
            "format": "%(asctime)s - %(levelname)s - %(name)s - [%(component)s] - %(message)s",
            "date_format": "%Y-%m-%d %H:%M:%S",
            "components": {
                "gui": "DEBUG",
                "cli": "INFO",
                "streamlit": "INFO",
                "database": "WARNING",
                "import": "DEBUG",
                "cache": "DEBUG",
                "main": "INFO",
            },
        }

        if not (config_path and os.path.exists(config_path)):
            return base_config

        try:
            with open(config_path, "r", encoding="utf-8") as f:
                loaded_config = json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            print(f"Erro ao carregar config de logging: {e}. Usando padrão.")
            return base_config

        if not isinstance(loaded_config, dict):
            print(
                "Configuracao de logging deve ser um objeto JSON. "
                "Usando padrao."
            )
            return base_config

        # Configuração estruturada (logging/paths) ou chave/valor plana.
        if "logging" in loaded_config:
            logging_cfg = loaded_config.get("logging", {})
            handlers = logging_cfg.get("handlers", {})

            base_config["level"] = logging_cfg.get("level", base_config["level"])
            base_config["format"] = logging_cfg.get("format", base_config["format"])
            base_config["components"].update(logging_cfg.get("components", {}))

            base_config["console_level"] = handlers.get("console", {}).get(
                "level", base_config["console_level"]
            )
            base_config["file_level"] = handlers.get("file", {}).get(
                "level", base_config["file_level"]
            )
            json_handler = handlers.get("json", {})
            base_config["json_level"] = json_handler.get(
                "level", base_config["json_level"]
            )
            if "include_metrics" in json_handler:
                base_config["enable_metrics"] = json_handler["include_metrics"]

        else:
            # Fallback: sobrescreve chaves conhecidas diretamente
            for key in base_config.keys():
                if key in loaded_config:
                    base_config[key] = loaded_config[key]
            if "components" in loaded_config and isinstance(
                loaded_config["components"], dict
            ):
                base_config["components"].update(loaded_config["components"])

        if "paths" in loaded_config and isinstance(loaded_config["paths"], dict):
            log_dir_cfg = loaded_config["paths"].get("logs_dir")
            if log_dir_cfg:
                base_config["log_dir"] = log_dir_cfg

        return base_config

    def _setup_root_logger(self):
        """Configura o logger raiz."""
        root_logger = logging.getLogger()
        root_logger.setLevel(getattr(logging, self.config["level"]))

        # Remove handlers existentes para evitar duplicação
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)

        # Cria diretório de logs
        log_dir = Path(self.config["log_dir"])
        log_dir.mkdir(exist_ok=True)

        # Handler para console
        if self.config["enable_console"]:
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setLevel(getattr(logging, self.config["console_level"]))
            console_formatter = SafeFormatter(
                self.config["format"], datefmt=self.config["date_format"]
            )
            console_handler.setFormatter(console_formatter)
            console_handler.addFilter(ContextFilter())
            root_logger.addHandler(console_handler)

        # Handler para arquivo texto
        if self.config["enable_file"]:
            file_handler = logging.handlers.RotatingFileHandler(
                filename=log_dir / self.config["filename"],
                maxBytes=self.config["max_file_size"],
                backupCount=self.config["backup_count"],
                encoding="utf-8",
            )
            file_handler.setLevel(getattr(logging, self.config["file_level"]))
            file_formatter = SafeFormatter(
                self.config["format"], datefmt=self.config["date_format"]
            )
            file_handler.setFormatter(file_formatter)
            file_handler.addFilter(ContextFilter())
            root_logger.addHandler(file_handler)

        # Handler para JSON estruturado
        if self.config["enable_json"]:
            json_handler = logging.handlers.RotatingFileHandler(
                filename=log_dir / self.config["json_filename"],
                maxBytes=self.config["max_file_size"],
                backupCount=self.config["json_backup_count"],
                encoding="utf-8",
            )
            json_handler.setLevel(getattr(logging, self.config["json_level"]))
            json_formatter = JSONFormatter(
                include_metrics=self.config["enable_metrics"]
            )
            json_handler.setFormatter(json_formatter)
            json_handler.addFilter(ContextFilter())
            root_logger.addHandler(json_handler)

            # Compartilha métricas com JSONFormatter
            if self.config["enable_metrics"]:
                self.metrics = json_formatter.metrics

    def get_logger(self, name: str, component: Optional[str] = None) -> logging.Logger:
        """Retorna logger configurado para um componente específico."""
        if name in self.loggers:
            return self.loggers[name]

        logger = logging.getLogger(name)

        # Configura nível específico do componente se definido
        if component and component in self.config["components"]:
            level = self.config["components"][component]
            logger.setLevel(getattr(logging, level))

        # Adiciona filtro de contexto específico do componente
        if component:
            logger.addFilter(ContextFilter(component))

        self.loggers[name] = logger
        return logger

    def log_performance(
        self, operation: str, duration: float, component: str = "performance"
    ):
        """Log específico para métricas de performance."""
        logger = self.get_logger("ssa.performance", component)

        # Adiciona à métrica apropriada
        if "filter" in operation.lower():
            self.metrics.add_filter_time(duration)
        elif "import" in operation.lower():
            self.metrics.add_import_time(duration)
        elif "query" in operation.lower():
            self.metrics.add_query_time(duration)

        # Log com contexto
        logger.info(
            f"Performance: {operation} completed",
            extra={
                "operation": operation,
                "duration": duration,
                "component": component,
            },
        )

    def log_cache_hit(self, cache_type: str, key: str, component: str = "cache"):
        """Log específico para cache hits."""
        self.metrics.increment_cache_hit()
        logger = self.get_logger("ssa.cache", component)
        logger.debug(
            f"Cache HIT: {cache_type}",
            extra={
                "operation": "cache_hit",
                "cache_type": cache_type,
                "cache_key": key,
                "component": component,
            },
        )

    def log_cache_miss(self, cache_type: str, key: str, component: str = "cache"):
        """Log específico para cache misses."""
        self.metrics.increment_cache_miss()
        logger = self.get_logger("ssa.cache", component)
        logger.debug(
            f"Cache MISS: {cache_type}",
            extra={
                "operation": "cache_miss",
                "cache_type": cache_type,
                "cache_key": key,
                "component": component,
            },
        )

    def log_error(self, message: str, exc_info=None, component: str = "error"):
        """Log específico para erros."""
        self.metrics.increment_error()
        logger = self.get_logger("ssa.error", component)
        logger.error(message, exc_info=exc_info, extra={"component": component})

    def log_warning(self, message: str, component: str = "warning"):
        """Log específico para warnings."""
        self.metrics.increment_warning()
        logger = self.get_logger("ssa.warning", component)
        logger.warning(message, extra={"component": component})

    def get_metrics_summary(self) -> Dict[str, Any]:
        """Retorna resumo das métricas coletadas."""
        return self.metrics.get_stats()

    def export_logs_report(self, output_path: str):
        """Exporta relatório de logs e métricas."""
        report = {
            "generated_at": datetime.now(timezone.utc)
            .isoformat()
            .replace("+00:00", "Z"),
            "config": self.config,
            "metrics": self.get_metrics_summary(),
            "log_files": {
                "text": str(Path(self.config["log_dir"]) / self.config["filename"]),
                "json": str(
                    Path(self.config["log_dir"]) / self.config["json_filename"]
                ),
            },
        }

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)


# Instância global do sistema de logging
_robust_logger = None
_robust_logger_lock = threading.Lock()


def get_robust_logger(config_path: Optional[str] = None) -> RobustLogger:
    """Retorna instância global do sistema de logging robusto."""
    global _robust_logger
    if _robust_logger is None:
        # Protect lazy initialization to avoid races when called from multiple threads.
        with _robust_logger_lock:
            if _robust_logger is None:
                _robust_logger = RobustLogger(config_path)
    return _robust_logger


# Backwards-compatible alias esperado por imports legados
def setup_logging(config_path: Optional[str] = None) -> RobustLogger:
    """Alias compatível com implementações anteriores.

    Uso:
        from utils.robust_logging import setup_logging
        rl = setup_logging()
    """
    return get_robust_logger(config_path=config_path)


# Exports públicos do módulo
__all__ = [
    "get_robust_logger",
    "setup_logging",
    "RobustLogger",
    "PerformanceMetrics",
    "JSONFormatter",
    "ContextFilter",
]


def get_component_logger(name: str, component: str) -> logging.Logger:
    """Shortcut para obter logger de componente."""
    return get_robust_logger().get_logger(name, component)
