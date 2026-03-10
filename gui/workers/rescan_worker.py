# gui/workers/rescan_worker.py
# Worker thread for database rescanning

import os
import sys
import logging
import threading
from PyQt6.QtCore import QThread, pyqtSignal

# Add project root to path for imports
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from core.app_logic import run_importer_logic  # noqa: E402

logger = logging.getLogger(__name__)

_LOGGER_LOCK = threading.Lock()
_LOGGER_REFCOUNT = 0
_LOGGER_PREV_LEVEL = None


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

    def __init__(self, main_py_path, project_root, force_import: bool = True):
        super().__init__()
        self.main_py_path = main_py_path  # Not used anymore but kept for compatibility
        self.project_root = project_root
        self.force_import = bool(force_import)
        self._should_stop = False

        # Set up logging to capture import messages
        self.log_handler = _LogHandler(self.output_line, self.error_line)
        self.logger = logging.getLogger('ssa')

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
                    logger.warning("Falha ao remover handler de logger do reescaneamento: %s", exc)
            if _LOGGER_REFCOUNT > 0:
                _LOGGER_REFCOUNT -= 1
            if _LOGGER_REFCOUNT == 0 and _LOGGER_PREV_LEVEL is not None:
                try:
                    self.logger.setLevel(_LOGGER_PREV_LEVEL)
                except Exception as exc:
                    logger.warning("Falha ao restaurar nivel de logger do reescaneamento: %s", exc)
                else:
                    _LOGGER_PREV_LEVEL = None
            self._logger_attached = False

    def _progress_callback(self, event_type, data):
        """Handle progress callbacks from run_importer_logic."""
        if self._should_stop:
            return

        if event_type == 'start':
            total = data.get('total', 0)
            self.output_line.emit(f"Total de {total} arquivos para processar")
            self.progress.emit(10, "Iniciando processamento...")

        elif event_type == 'file_start':
            filename = data.get('filename', '')
            current = data.get('current', 0)
            total = data.get('total', 1)
            percentage = int(10 + (current / total * 70))  # 10% to 80%
            self.output_line.emit(f"[{current}/{total}] Processando: {filename}")
            self.progress.emit(percentage, f"Arquivo {current}/{total}")

        elif event_type == 'file_success':
            filename = data.get('filename', '')
            records = data.get('records', 0)
            self.output_line.emit(f"[OK] {filename}: {records} registros")

        elif event_type == 'file_error':
            filename = data.get('filename', '')
            error = data.get('error', 'Unknown error')
            self.error_line.emit(f"[ERRO] {filename}: {error}")

        elif event_type == 'finish':
            total = data.get('total', 0)
            processed = data.get('processed', 0)
            errors = data.get('errors', [])
            self.output_line.emit("")
            self.output_line.emit(f"Processamento concluido: {processed}/{total} arquivos")
            if errors:
                self.output_line.emit(f"Erros: {len(errors)} arquivos falharam")
            self.progress.emit(90, "Finalizando...")

    def run(self):
        """Execute rescan in background thread using modular import."""
        try:
            mode_label = "FULL" if self.force_import else "DIFF"
            self.output_line.emit(f"=== Iniciando Reescaneamento ({mode_label}) ===")
            self.output_line.emit("")
            self.progress.emit(5, "Configurando...")

            # Add log handler to capture import messages
            self._attach_logger()

            # Call modular import function directly
            success = run_importer_logic(
                docs_dir='docs_entrada',
                data_dir='data',
                db_name='ssas.db',
                table_name='ssa_table',
                force_import=self.force_import,
                should_cancel=lambda: self._should_stop,
                progress_callback=self._progress_callback,
            )

            if self._should_stop:
                self.finished_error.emit("Processo cancelado pelo usuario")
                return

            if success:
                self.progress.emit(100, "Concluido com sucesso")
                self.output_line.emit("")
                self.output_line.emit("=== Reescaneamento Concluido ===")
                self.finished_success.emit()
            else:
                if not self.force_import:
                    self.progress.emit(100, "Concluido sem alteracoes")
                    self.output_line.emit("")
                    self.output_line.emit("=== Reescaneamento Concluido (sem alteracoes) ===")
                    self.output_line.emit("Nenhum arquivo novo ou alterado foi encontrado.")
                    self.finished_success.emit()
                else:
                    self.progress.emit(100, "Concluido sem alteracoes")
                    self.output_line.emit("")
                    self.output_line.emit("=== Reescaneamento Completo Concluido (sem alteracoes) ===")
                    self.output_line.emit("Importacao concluida sem dados atualizados.")
                    self.finished_success.emit()

        except Exception as exc:
            logger.exception("Erro inesperado no reescaneamento")
            message = f"Erro ao executar reescaneamento: {exc}"
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


class _LogHandler(logging.Handler):
    """Custom log handler to emit logs to Qt signals."""

    def __init__(self, output_signal, error_signal):
        super().__init__()
        self.output_signal = output_signal
        self.error_signal = error_signal

    def emit(self, record):
        """Emit log record to appropriate signal."""
        try:
            msg = self.format(record)
            if record.levelno >= logging.ERROR:
                self.error_signal.emit(msg)
            else:
                self.output_signal.emit(msg)
        except Exception as e:
            # Replaced silent pass (B110) with debug logging for traceability
            logging.getLogger(__name__).debug("LogHandler emit falhou: %s", e)
