# gui/workers/rescan_worker.py
# Worker thread for database rescanning

import logging
import os
import shutil
import sys
import threading
from enum import Enum
from pathlib import Path
from typing import Sequence

from PyQt6.QtCore import QThread, pyqtSignal

# Add project root to path for imports
project_root = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from core.app_logic import run_importer_logic  # noqa: E402
from core.import_consolidation import consolidate_input_files  # noqa: E402
from utils.robust_logging import get_robust_logger  # noqa: E402
from utils.path_safety import PathSafetyError, ensure_path_is_allowed  # noqa: E402

logger = get_robust_logger().get_logger(__name__, "gui")

_LOGGER_LOCK = threading.Lock()
_LOGGER_REFCOUNT = 0
_LOGGER_PREV_LEVEL = None


class RescanOutcome(str, Enum):
    UPDATED = "updated"
    NO_CHANGES = "no_changes"
    REJECTIONS_ONLY = "rejections_only"
    CANCELLED = "cancelled"
    ERROR = "error"


class RescanWorker(QThread):
    """
    Worker thread to execute database rescan without blocking UI.

    Calls run_importer_logic directly (modular approach) instead of subprocess.

    Signals:
        output_line: Emitted for each line of output
        error_line: Emitted for each line of errors
        progress: Emitted with progress updates
        finished_success: Emitted when completed successfully
        finished_error: Emitted when an error occurs
    """

    output_line = pyqtSignal(str)
    error_line = pyqtSignal(str)
    progress = pyqtSignal(int, str)  # percentage, message
    finished_success = pyqtSignal()
    finished_error = pyqtSignal(str)

    def __init__(
        self,
        main_py_path,
        project_root,
        force_import: bool = True,
        explicit_files: Sequence[str] | None = None,
        source_files: Sequence[str] | None = None,
        operation_label: str = "Reescaneamento",
        operation_kind: str = "import",
    ):
        super().__init__()
        self.main_py_path = main_py_path  # Not used anymore but kept for compatibility
        self.project_root = project_root
        self.force_import = bool(force_import)
        self.explicit_files = (
            tuple(str(path) for path in explicit_files) if explicit_files else None
        )
        self.source_files = (
            tuple(str(path) for path in source_files) if source_files else None
        )
        normalized_label = str(operation_label or "").strip()
        self.operation_label = normalized_label or "Reescaneamento"
        normalized_kind = str(operation_kind or "").strip().lower()
        self.operation_kind = normalized_kind or "import"
        self._should_stop = False
        self._has_runtime_errors = False
        self._last_total_files = 0
        self._last_processed_files = 0
        self._last_deterministic_failure_count = 0
        self._last_rejection_only = False
        self.last_outcome = RescanOutcome.NO_CHANGES

        # Set up logging to capture import messages
        self.log_handler = _LogHandler(
            self.output_line,
            self.error_line,
            error_observer=self._mark_runtime_error,
        )
        self.logger = get_robust_logger().get_logger("ssa", "gui")

        self._logger_attached = False

    def _attach_logger(self) -> None:
        global _LOGGER_REFCOUNT, _LOGGER_PREV_LEVEL
        with _LOGGER_LOCK:
            if _LOGGER_REFCOUNT == 0:
                _LOGGER_PREV_LEVEL = self.logger.level
                if _LOGGER_PREV_LEVEL > logging.INFO:
                    self.logger.setLevel(logging.INFO)
            if self.log_handler not in self.logger.handlers:
                self.logger.addHandler(self.log_handler)
            _LOGGER_REFCOUNT += 1
            self._logger_attached = True

    def _detach_logger(self) -> None:
        global _LOGGER_REFCOUNT, _LOGGER_PREV_LEVEL
        with _LOGGER_LOCK:
            if not self._logger_attached:
                return
            if self.log_handler in self.logger.handlers:
                try:
                    self.logger.removeHandler(self.log_handler)
                except Exception as exc:
                    logger.warning(
                        "Falha ao remover handler de logger do reescaneamento: %s", exc
                    )
            if _LOGGER_REFCOUNT > 0:
                _LOGGER_REFCOUNT -= 1
            if _LOGGER_REFCOUNT == 0 and _LOGGER_PREV_LEVEL is not None:
                try:
                    self.logger.setLevel(_LOGGER_PREV_LEVEL)
                except Exception as exc:
                    logger.warning(
                        "Falha ao restaurar nivel de logger do reescaneamento: %s", exc
                    )
                else:
                    _LOGGER_PREV_LEVEL = None
            self._logger_attached = False

    def _progress_callback(self, event_type, data):
        """Handle progress callbacks from run_importer_logic."""
        if self._should_stop:
            return

        if event_type == "start":
            total = data.get("total", 0)
            self._last_total_files = int(total)
            self._last_processed_files = 0
            self.output_line.emit(f"Total de {total} arquivos para processar")
            self.progress.emit(10, "Iniciando processamento...")

        elif event_type == "file_start":
            filename = data.get("filename", "")
            current = data.get("current", 0)
            total = data.get("total", 1)
            percentage = int(10 + (current / total * 70))  # 10% to 80%
            self.output_line.emit(f"[{current}/{total}] Processando: {filename}")
            self.progress.emit(percentage, f"Arquivo {current}/{total}")

        elif event_type == "file_success":
            filename = data.get("filename", "")
            records = data.get("records", 0)
            self.output_line.emit(f"[OK] {filename}: {records} registros")

        elif event_type == "file_error":
            filename = data.get("filename", "")
            error = data.get("error", "Unknown error")
            self._mark_runtime_error()
            self.error_line.emit(f"[ERRO] {filename}: {error}")

        elif event_type == "finish":
            total = data.get("total", 0)
            processed = data.get("processed", 0)
            errors = data.get("errors", [])
            self._last_total_files = int(total)
            self._last_processed_files = int(processed)
            self._last_deterministic_failure_count = int(
                data.get("deterministic_failure_count", 0)
            )
            self._last_rejection_only = bool(data.get("rejection_only", False))
            self.output_line.emit("")
            self.output_line.emit(
                f"Processamento concluido: {processed}/{total} arquivos"
            )
            if errors:
                self.output_line.emit(f"Erros: {len(errors)} arquivos falharam")
            self.progress.emit(90, "Finalizando...")

    def run(self):
        """Execute rescan in background thread using modular import."""
        try:
            self.last_outcome = RescanOutcome.NO_CHANGES
            self._has_runtime_errors = False
            self._last_total_files = 0
            self._last_processed_files = 0
            self._last_deterministic_failure_count = 0
            self._last_rejection_only = False
            if self.operation_kind == "consolidate":
                mode_label = "CONSOLIDATE"
            elif self.explicit_files or self.source_files:
                mode_label = "EXPLICITA"
            else:
                mode_label = "FULL" if self.force_import else "DIFF"
            self.output_line.emit(
                f"=== Iniciando {self.operation_label} ({mode_label}) ==="
            )
            self.output_line.emit("")
            self.progress.emit(5, "Configurando...")

            # Add log handler to capture import messages
            self._attach_logger()

            if self.operation_kind == "consolidate":
                success = self._run_consolidation_operation()
                if self._should_stop:
                    self.last_outcome = RescanOutcome.CANCELLED
                    self.finished_error.emit("Processo cancelado pelo usuario")
                    return
                if success:
                    self.progress.emit(100, "Concluido com sucesso")
                    self.output_line.emit("")
                    self.output_line.emit("=== Operacao Concluida ===")
                    self.finished_success.emit()
                else:
                    self.last_outcome = RescanOutcome.ERROR
                    self.progress.emit(100, "Falha na consolidacao")
                    self.output_line.emit("")
                    self.output_line.emit("=== Consolidacao Falhou ===")
                    self.finished_error.emit("Consolidacao falhou")
                return

            if self.source_files:
                staged_files, summary = self._stage_source_files()
                self.explicit_files = tuple(staged_files) if staged_files else None
                if self._should_stop:
                    self.last_outcome = RescanOutcome.CANCELLED
                    self.finished_error.emit("Processo cancelado pelo usuario")
                    return
                if not self.explicit_files:
                    if summary["failed"] > 0:
                        self.last_outcome = RescanOutcome.ERROR
                        self.finished_error.emit(
                            "Importacao externa sem arquivos validos apos staging"
                        )
                    else:
                        self.last_outcome = RescanOutcome.NO_CHANGES
                        self.finished_success.emit()
                    return

            # Call modular import function directly
            success = run_importer_logic(
                docs_dir="docs_entrada",
                data_dir="data",
                db_name="ssas.db",
                table_name="ssa_table",
                force_import=self.force_import,
                explicit_files=self.explicit_files,
                should_cancel=lambda: self._should_stop,
                progress_callback=self._progress_callback,
            )

            if self._should_stop:
                self.last_outcome = RescanOutcome.CANCELLED
                self.finished_error.emit("Processo cancelado pelo usuario")
                return

            if success:
                self.last_outcome = RescanOutcome.UPDATED
                self.progress.emit(100, "Concluido com sucesso")
                self.output_line.emit("")
                self.output_line.emit("=== Operacao Concluida ===")
                self.finished_success.emit()
            elif self._last_rejection_only:
                self.last_outcome = RescanOutcome.REJECTIONS_ONLY
                self.progress.emit(100, "Concluido com arquivos rejeitados por regra")
                self.output_line.emit("")
                self.output_line.emit(
                    "=== Reescaneamento Concluido com Rejeicoes Deterministicas ==="
                )
                self.output_line.emit(
                    "Arquivos fora do padrao esperado foram ignorados sem bloquear o banco atual."
                )
                self.finished_success.emit()
            else:
                if not self.force_import:
                    self.last_outcome = RescanOutcome.NO_CHANGES
                    self.progress.emit(100, "Concluido sem alteracoes")
                    self.output_line.emit("")
                    self.output_line.emit(
                        "=== Reescaneamento Concluido (sem alteracoes) ==="
                    )
                    self.output_line.emit(
                        "Nenhum arquivo novo ou alterado foi encontrado."
                    )
                    self.finished_success.emit()
                else:
                    if self._has_runtime_errors or self._last_total_files > 0:
                        self.last_outcome = RescanOutcome.ERROR
                        self.progress.emit(100, "Falha no reescaneamento completo")
                        self.output_line.emit("")
                        self.output_line.emit("=== Reescaneamento Completo Falhou ===")
                        if self._has_runtime_errors:
                            self.output_line.emit(
                                "Importacao falhou com erros durante o processamento."
                            )
                            self.finished_error.emit(
                                "Importacao completa falhou com erros"
                            )
                        else:
                            self.output_line.emit(
                                "Importacao concluida mas nenhum dado foi atualizado."
                            )
                            self.finished_error.emit(
                                "Importacao completa sem atualizacoes"
                            )
                    else:
                        self.last_outcome = RescanOutcome.NO_CHANGES
                        self.progress.emit(100, "Concluido sem alteracoes")
                        self.output_line.emit("")
                        self.output_line.emit(
                            "=== Reescaneamento Completo Concluido (sem alteracoes) ==="
                        )
                        self.output_line.emit(
                            "Importacao concluida sem dados atualizados."
                        )
                        self.finished_success.emit()

        except Exception as exc:
            self.last_outcome = RescanOutcome.ERROR
            logger.exception("Erro inesperado na operacao de importacao")
            message = f"Erro ao executar operacao de importacao: {exc}"
            self.error_line.emit(message)
            self.finished_error.emit(message)
        finally:
            # Keep cleanup best-effort but never silence a real detach failure.
            if self._logger_attached:
                try:
                    self._detach_logger()
                except Exception as exc:
                    logger.warning("Falha ao limpar logger do reescaneamento: %s", exc)

    def stop(self):
        """Request thread to stop."""
        self._should_stop = True

    def _mark_runtime_error(self, _message: str = "") -> None:
        """Mark that runtime emitted at least one error signal."""
        self._has_runtime_errors = True

    def _build_unique_destination_path(self, destination_path: str) -> str:
        if not os.path.exists(destination_path):
            return destination_path
        base, ext = os.path.splitext(destination_path)
        idx = 1
        max_attempts = 10000
        while idx <= max_attempts:
            candidate = f"{base}__{idx}{ext}"
            if not os.path.exists(candidate):
                return candidate
            idx += 1
        raise RuntimeError(
            f"Nao foi possivel gerar nome unico apos {max_attempts} tentativas: {destination_path}"
        )

    @staticmethod
    def _validate_selected_source_path(raw_source: str) -> str:
        source = str(raw_source or "").strip()
        if not source:
            raise ValueError("Caminho vazio para staging externo.")
        if any(ch in source for ch in ("\x00", "\n", "\r")):
            raise ValueError("Caminho externo contem caracteres invalidos.")
        normalized = os.path.abspath(os.path.normpath(source))
        if os.path.basename(normalized).startswith("-"):
            raise ValueError("Caminho externo inicia com '-' e nao e permitido.")
        source_path = Path(normalized)
        if source_path.exists():
            try:
                ensure_path_is_allowed(
                    source_path,
                    purpose="explicit_import_source",
                    must_exist=True,
                    expect_directory=False,
                )
            except PathSafetyError as exc:
                logger.debug(
                    "Arquivo externo fora da allowlist padrao; validando por selecao explicita: %s",
                    exc,
                )
        if not source_path.is_file():
            raise FileNotFoundError(f"Arquivo inexistente: {normalized}")
        if source_path.suffix.casefold() not in {".xlsx", ".xls"}:
            raise ValueError(
                f"Arquivo nao suportado pelo pipeline: {source_path.name}"
            )
        return str(source_path)

    def _stage_source_files(self) -> tuple[list[str], dict[str, int]]:
        docs_path = ensure_path_is_allowed(
            Path(self.project_root) / "docs_entrada",
            purpose="explicit_import_docs_dir",
            base=Path(self.project_root),
            must_exist=False,
            expect_directory=True,
        )
        os.makedirs(docs_path, exist_ok=True)

        copied = 0
        skipped = 0
        failed = 0
        unsupported = 0
        staged_files: list[str] = []
        source_files = tuple(self.source_files or ())
        total_sources = len(source_files)

        for index, raw_source in enumerate(source_files, start=1):
            if self._should_stop:
                break
            source = str(raw_source or "").strip()
            self.output_line.emit(
                f"[STAGE {index}/{total_sources}] Preparando: {os.path.basename(source) or source}"
            )
            try:
                validated_source = self._validate_selected_source_path(source)
            except FileNotFoundError:
                failed += 1
                self.error_line.emit(f"[ERRO] Arquivo inexistente: {source}")
                continue
            except ValueError as exc:
                unsupported += 1
                self.output_line.emit(
                    f"[IGNORADO] {exc}"
                )
                continue
            except Exception as exc:
                failed += 1
                self.error_line.emit(
                    f"[ERRO] Falha ao validar arquivo externo '{source}': {exc}"
                )
                continue

            base_name = os.path.basename(validated_source)
            base_destination = os.path.join(docs_path, base_name)
            source_abs = os.path.abspath(validated_source)
            destination_abs = os.path.abspath(base_destination)
            if source_abs == destination_abs:
                staged_files.append(destination_abs)
                continue

            destination = self._build_unique_destination_path(base_destination)
            try:
                shutil.copy2(validated_source, destination)
                copied += 1
                staged_files.append(destination)
            except Exception as exc:
                failed += 1
                self.error_line.emit(
                    f"[ERRO] Falha ao copiar arquivo externo '{validated_source}': {exc}"
                )

        summary = {
            "copied": copied,
            "skipped": skipped,
            "failed": failed,
            "unsupported": unsupported,
            "staged": len(staged_files),
        }
        self.output_line.emit(
            "Staging concluido: "
            f"copiados={copied}, ignorados={skipped}, "
            f"nao_suportados={unsupported}, falhas={failed}, staged={len(staged_files)}"
        )
        return staged_files, summary

    def _run_consolidation_operation(self) -> bool:
        result = consolidate_input_files(
            project_root=self.project_root,
            should_cancel=lambda: self._should_stop,
            progress_callback=lambda pct, message: self.progress.emit(pct, message),
            output_callback=self.output_line.emit,
            error_callback=self.error_line.emit,
        )
        self.last_outcome = (
            RescanOutcome.UPDATED
            if int(result.get("moved", 0) or 0) > 0
            else RescanOutcome.NO_CHANGES
        )
        return int(result.get("failed", 0) or 0) == 0


class _LogHandler(logging.Handler):
    """Custom log handler to emit logs to Qt signals."""

    def __init__(self, output_signal, error_signal, error_observer=None):
        super().__init__()
        self.output_signal = output_signal
        self.error_signal = error_signal
        self.error_observer = error_observer

    def emit(self, record):
        """Emit log record to appropriate signal."""
        try:
            msg = self.format(record)
            if record.levelno >= logging.ERROR:
                if callable(self.error_observer):
                    self.error_observer(msg)
                self.error_signal.emit(msg)
            else:
                self.output_signal.emit(msg)
        except Exception as e:
            # Replaced silent pass (B110) with debug logging for traceability
            logging.getLogger(__name__).debug("LogHandler emit falhou: %s", e)
