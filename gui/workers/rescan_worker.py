# gui/workers/rescan_worker.py
# Worker thread for database rescanning

import logging
import sqlite3
import sys
import threading
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Sequence, TypedDict, cast

try:
    from PyQt6.QtCore import QThread, pyqtSignal

    QT_AVAILABLE = True
except Exception:
    QT_AVAILABLE = False

    class _SignalInstance:
        def __init__(self) -> None:
            self._slots = []

        def connect(self, slot, *_args, **_kwargs):
            self._slots.append(slot)

        def emit(self, *args, **kwargs):
            for slot in list(self._slots):
                slot(*args, **kwargs)

    class _SignalDescriptor:
        def __set_name__(self, _owner, name):
            self._name = name

        def __get__(self, instance, _owner):
            if instance is None:
                return self
            signal = instance.__dict__.get(self._name)
            if signal is None:
                signal = _SignalInstance()
                instance.__dict__[self._name] = signal
            return signal

    def _fallback_pyqt_signal(*_args, **_kwargs):
        return _SignalDescriptor()

    class _FallbackQThread:
        def __init__(self, *_args, **_kwargs) -> None:
            return None

    pyqtSignal = cast(Any, _fallback_pyqt_signal)
    QThread = cast(Any, _FallbackQThread)


# Add project root to path for imports
def _get_project_root() -> str:
    return str(Path(__file__).resolve().parents[2])


project_root = _get_project_root()
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from utils.path_safety import ensure_path_is_allowed  # noqa: E402
from utils.robust_logging import get_robust_logger  # noqa: E402

logger = get_robust_logger().get_logger(__name__, "gui")


def run_importer_logic(*args, **kwargs):
    from core.app_logic import run_importer_logic as importer_impl

    return importer_impl(*args, **kwargs)


def consolidate_input_files(*args, **kwargs):
    from core.import_consolidation import consolidate_input_files as consolidate_impl

    return consolidate_impl(*args, **kwargs)


def stage_external_import_files(*args, **kwargs):
    from core.import_staging import stage_external_import_files as staging_impl

    return staging_impl(*args, **kwargs)


def count_table_rows(db_path: str, table_name: str) -> int:
    from armazenamento.database import count_table_rows as count_impl

    return count_impl(db_path, table_name)


class _LoggerAttachmentManager:
    class _State(TypedDict):
        refcount: int
        previous_level: int

    _lock = threading.Lock()
    _state: dict[int, _State] = {}

    @classmethod
    def attach(cls, logger_obj: logging.Logger, handler: logging.Handler) -> None:
        key = id(logger_obj)
        with cls._lock:
            state = cls._state.get(key)
            if state is None:
                state = cast(
                    _LoggerAttachmentManager._State,
                    {
                        "refcount": 0,
                        "previous_level": int(logger_obj.level),
                    },
                )
                cls._state[key] = state
            if int(state["refcount"]) == 0:
                state["previous_level"] = int(logger_obj.level)
                if logger_obj.level > logging.INFO:
                    logger_obj.setLevel(logging.INFO)
            if handler not in logger_obj.handlers:
                logger_obj.addHandler(handler)
            state["refcount"] = int(state["refcount"]) + 1

    @classmethod
    def detach(cls, logger_obj: logging.Logger, handler: logging.Handler) -> None:
        key = id(logger_obj)
        with cls._lock:
            state = cls._state.get(key)
            if handler in logger_obj.handlers:
                try:
                    logger_obj.removeHandler(handler)
                except Exception as exc:
                    logger.warning(
                        "Falha ao remover handler de logger do reescaneamento: %s", exc
                    )
            if state is None:
                return
            refcount = max(int(state["refcount"]) - 1, 0)
            state["refcount"] = refcount
            if refcount == 0:
                try:
                    logger_obj.setLevel(int(state["previous_level"]))
                except Exception as exc:
                    logger.warning(
                        "Falha ao restaurar nivel de logger do reescaneamento: %s",
                        exc,
                    )
                finally:
                    cls._state.pop(key, None)


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
    batch_completed = pyqtSignal(int, int)  # current batch, total batches
    finished_success = pyqtSignal()
    finished_error = pyqtSignal(str)

    def __init__(
        self,
        main_py_path,
        project_root,
        force_import: bool = True,
        explicit_files: Sequence[str] | None = None,
        source_files: Sequence[str] | None = None,
        db_path: str | None = None,
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
        self.db_path = str(db_path) if db_path else None
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
        self._last_runtime_error_detail = ""
        self._batch_file_offset = 0
        self._batch_index = 1
        self._batch_total = 1
        self._overall_total_files = 0
        self._last_ssa_inserted = 0
        self._last_ssa_updated = 0
        self._database_rows_before: int | None = 0
        self._database_rows_after: int | None = 0
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
        _LoggerAttachmentManager.attach(self.logger, self.log_handler)
        self._logger_attached = True

    def _detach_logger(self) -> None:
        if not self._logger_attached:
            return
        _LoggerAttachmentManager.detach(self.logger, self.log_handler)
        self._logger_attached = False

    def _remember_runtime_error(self, filename: object, error: object) -> None:
        filename_text = str(filename or "").strip()
        error_text = str(error or "").strip() or "erro desconhecido"
        if filename_text:
            self._last_runtime_error_detail = f"{filename_text}: {error_text}"
        else:
            self._last_runtime_error_detail = error_text

    def _runtime_failure_message(self, base_message: str) -> str:
        detail = self._last_runtime_error_detail.strip()
        if not detail or detail in base_message:
            return base_message
        return f"{base_message}. Causa: {detail}"

    def _progress_callback(self, event_type, data):
        """Handle progress callbacks from run_importer_logic."""
        if self._should_stop:
            return

        if event_type == "start":
            total = data.get("total", 0)
            overall_total = self._overall_total_files or int(total)
            self._last_total_files = overall_total
            if self._batch_file_offset == 0:
                self._last_processed_files = 0
                self.output_line.emit(
                    f"Total de {overall_total} arquivos para processar"
                )
            percentage = int(
                10 + (self._batch_file_offset / max(overall_total, 1) * 70)
            )
            self.progress.emit(
                percentage,
                f"[{datetime.now():%H:%M:%S}] Iniciando processamento...",
            )

        elif event_type == "file_start":
            filename = data.get("filename", "")
            current = data.get("current", 0)
            total = data.get("total", 1)
            overall_total = self._overall_total_files or int(total)
            overall_current = self._batch_file_offset + int(current)
            percentage = int(
                10 + (overall_current / max(overall_total, 1) * 70)
            )
            self.output_line.emit(
                f"[{overall_current}/{overall_total}] Processando: {filename}"
            )
            self.progress.emit(
                percentage, f"Arquivo {overall_current}/{overall_total}"
            )

        elif event_type == "file_success":
            filename = data.get("filename", "")
            records = data.get("records", 0)
            ssa_inserted = int(data.get("ssa_inserted", 0) or 0)
            ssa_updated = int(data.get("ssa_updated", 0) or 0)
            self._last_ssa_inserted += ssa_inserted
            self._last_ssa_updated += ssa_updated
            suffix = (
                f" | {ssa_updated} SSAs atualizadas" if ssa_updated > 0 else ""
            )
            self.output_line.emit(
                f"[OK] {filename}: {records} registros{suffix}"
            )

        elif event_type == "file_error":
            filename = data.get("filename", "")
            error = data.get("error", "Unknown error")
            deterministic = bool(data.get("deterministic")) or (
                data.get("error_code") == "MISSING_REQUIRED_COLUMNS"
            )
            if deterministic:
                self.error_line.emit(f"[AVISO] {filename}: {error}")
            else:
                self._mark_runtime_error()
                self._remember_runtime_error(filename, error)
                self.error_line.emit(f"[ERRO] {filename}: {error}")

        elif event_type == "finish":
            total = data.get("total", 0)
            processed = data.get("processed", 0)
            errors = data.get("errors", [])
            if self._batch_total > 1:
                self._last_total_files = self._overall_total_files
                self._last_processed_files += int(processed)
            else:
                self._last_total_files = int(total)
                self._last_processed_files = int(processed)
            self._last_deterministic_failure_count = int(
                data.get("deterministic_failure_count", 0)
            )
            self._last_rejection_only = bool(data.get("rejection_only", False))
            self.output_line.emit("")
            if self._batch_total > 1:
                self.output_line.emit(
                    f"Bloco {self._batch_index}/{self._batch_total} concluido: "
                    f"{processed}/{total} arquivos"
                )
            else:
                self.output_line.emit(
                    f"Processamento concluido: {processed}/{total} arquivos"
                )
            if errors:
                self.output_line.emit(f"Erros: {len(errors)} arquivos falharam")
                if not self._last_runtime_error_detail:
                    first_error = errors[0]
                    if isinstance(first_error, (tuple, list)) and len(first_error) >= 3:
                        self._remember_runtime_error(first_error[1], first_error[2])
                    else:
                        self._remember_runtime_error("", first_error)
            completed = self._batch_file_offset + int(total)
            percentage = (
                int(10 + (completed / max(self._overall_total_files, 1) * 70))
                if self._batch_total > 1
                else 90
            )
            self.progress.emit(percentage, "Finalizando...")

    def _reset_run_state(self) -> None:
        self.last_outcome = RescanOutcome.NO_CHANGES
        self._has_runtime_errors = False
        self._last_total_files = 0
        self._last_processed_files = 0
        self._last_deterministic_failure_count = 0
        self._last_rejection_only = False
        self._last_runtime_error_detail = ""
        self._batch_file_offset = 0
        self._batch_index = 1
        self._batch_total = 1
        self._overall_total_files = 0
        self._last_ssa_inserted = 0
        self._last_ssa_updated = 0
        self._database_rows_before = 0
        self._database_rows_after = 0

    def _resolve_source_files(self) -> tuple[str, ...] | None:
        if not self.source_files:
            return None
        return self.source_files

    def _resolve_explicit_files(self) -> tuple[str, ...] | None:
        if not self.explicit_files:
            return None
        docs_dir = ensure_path_is_allowed(
            Path(self.project_root) / "docs_entrada",
            purpose="explicit_import_docs_dir",
            base=Path(self.project_root),
            must_exist=False,
            expect_directory=True,
        )
        resolved: list[str] = []
        for raw_path in self.explicit_files:
            candidate = ensure_path_is_allowed(
                raw_path,
                purpose="explicit_import_file",
                base=docs_dir,
                must_exist=True,
                expect_directory=False,
            )
            resolved.append(str(candidate))
        self.explicit_files = tuple(resolved)
        return self.explicit_files

    def _prepare_import_inputs(self) -> tuple[bool, dict[str, int]]:
        summary = {
            "copied": 0,
            "skipped": 0,
            "failed": 0,
            "unsupported": 0,
            "staged": 0,
        }
        self._resolve_explicit_files()
        resolved_sources = self._resolve_source_files()
        if resolved_sources:
            overall_total = self._overall_total_files or len(resolved_sources)
            stage_start = self._batch_file_offset + 1
            stage_end = self._batch_file_offset + len(resolved_sources)
            self.output_line.emit(
                f"[{datetime.now():%H:%M:%S}] Etapa: preparando ciclo "
                f"{self._batch_index}/{self._batch_total} "
                f"({stage_start}-{stage_end}/{overall_total})"
            )
            self.progress.emit(
                int(10 + (self._batch_file_offset / max(overall_total, 1) * 70)),
                f"Preparando arquivos {self._batch_file_offset}/{overall_total}",
            )
            staged_files, summary = stage_external_import_files(
                project_root=self.project_root,
                source_files=resolved_sources,
                progress_offset=self._batch_file_offset,
                progress_total=overall_total,
                should_cancel=lambda: self._should_stop,
                output_callback=self.output_line.emit,
                error_callback=self.error_line.emit,
            )
            self.explicit_files = tuple(staged_files) if staged_files else None
        if self._should_stop:
            self.last_outcome = RescanOutcome.CANCELLED
            self.finished_error.emit("Processo cancelado pelo usuario")
            return False, summary
        if self.source_files and not self.explicit_files:
            if summary["failed"] > 0:
                self.last_outcome = RescanOutcome.ERROR
                self.finished_error.emit(
                    "Importacao externa sem arquivos validos apos staging"
                )
            else:
                self.last_outcome = RescanOutcome.NO_CHANGES
                self.finished_success.emit()
            return False, summary
        return True, summary

    def _run_import_operation(self) -> bool:
        project_root_path = Path(self.project_root).expanduser().resolve()
        docs_dir = str(project_root_path / "docs_entrada")
        data_dir = str(project_root_path / "data")
        db_name = "ssas.db"
        extra_allowed_roots = [str(project_root_path)]
        if self.db_path:
            db_path = Path(self.db_path).expanduser().resolve()
            data_dir = str(db_path.parent)
            db_name = db_path.name
            db_parent = str(db_path.parent)
            if db_parent not in extra_allowed_roots:
                extra_allowed_roots.append(db_parent)
        return run_importer_logic(
            docs_dir=docs_dir,
            data_dir=data_dir,
            db_name=db_name,
            table_name="ssa_table",
            force_import=self.force_import,
            explicit_files=self.explicit_files,
            extra_allowed_roots=tuple(extra_allowed_roots),
            should_cancel=lambda: self._should_stop,
            progress_callback=self._progress_callback,
        )

    def _count_database_rows(self) -> int | None:
        db_path = self.db_path or str(
            Path(self.project_root).expanduser().resolve() / "data" / "ssas.db"
        )
        if not Path(db_path).exists():
            return 0
        try:
            return count_table_rows(db_path, "ssa_table")
        except (OSError, ValueError, sqlite3.Error) as exc:
            self.logger.warning(
                "Falha ao contar SSAs no banco '%s': %s",
                db_path,
                exc,
            )
            return None

    def _run_explicit_import_batches(self) -> bool | None:
        from extracao.extractor import MAX_IMPORT_BATCH_FILES

        source_mode = bool(self.source_files)
        work_items = tuple(self.source_files or self.explicit_files or ())
        self._overall_total_files = len(work_items)
        self._batch_total = max(
            1,
            (len(work_items) + MAX_IMPORT_BATCH_FILES - 1)
            // MAX_IMPORT_BATCH_FILES,
        )
        self.output_line.emit(
            f"[{datetime.now():%H:%M:%S}] Importacao externa: "
            f"{self._overall_total_files} arquivos selecionados; "
            f"serao processados em {self._batch_total} ciclos de ate "
            f"{MAX_IMPORT_BATCH_FILES} arquivos."
        )
        self.progress.emit(
            5,
            f"Preparando importacao externa: 0/{self._overall_total_files} arquivos",
        )
        self._database_rows_before = self._count_database_rows()
        self._database_rows_after = self._database_rows_before
        any_success = False
        had_runtime_failure = False
        had_rejection_only = False
        initial_force_import = self.force_import

        try:
            for batch_index, start in enumerate(
                range(0, len(work_items), MAX_IMPORT_BATCH_FILES),
                start=1,
            ):
                batch = work_items[start : start + MAX_IMPORT_BATCH_FILES]
                self._batch_index = batch_index
                self._batch_file_offset = start
                self.force_import = initial_force_import and batch_index == 1
                if source_mode:
                    self.source_files = batch
                    self.explicit_files = None
                else:
                    self.source_files = None
                    self.explicit_files = batch

                should_continue, _summary = self._prepare_import_inputs()
                if not should_continue:
                    return None
                batch_success = self._run_import_operation()
                any_success = batch_success or any_success
                had_runtime_failure = had_runtime_failure or self._has_runtime_errors
                had_rejection_only = had_rejection_only or self._last_rejection_only
                if self._should_stop:
                    return any_success
                self._database_rows_after = self._count_database_rows()
                self.batch_completed.emit(batch_index, self._batch_total)
        finally:
            self.force_import = initial_force_import

        self._last_rejection_only = had_rejection_only and not had_runtime_failure
        return False if had_runtime_failure else any_success

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

    def _finish_success(
        self, outcome: RescanOutcome, banner: str, message: str
    ) -> None:
        self.last_outcome = outcome
        self.progress.emit(100, message)
        self.output_line.emit("")
        self.output_line.emit(banner)
        self.finished_success.emit()

    def _finish_error(self, banner: str, message: str) -> None:
        self.last_outcome = RescanOutcome.ERROR
        self.progress.emit(100, message)
        self.output_line.emit("")
        self.output_line.emit(banner)
        self.finished_error.emit(message)

    def run(self):
        """Execute rescan in background thread using modular import."""
        try:
            self._reset_run_state()
            if self.operation_kind == "consolidate":
                mode_label = "CONSOLIDATE"
            elif self.explicit_files or self.source_files:
                mode_label = ""
            else:
                mode_label = "FULL" if self.force_import else "DIFF"
            mode_suffix = f" ({mode_label})" if mode_label else ""
            self.output_line.emit(
                f"[{datetime.now():%H:%M:%S}] === Iniciando "
                f"{self.operation_label}{mode_suffix} ==="
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
                    self._finish_success(
                        self.last_outcome,
                        "=== Operacao Concluida ===",
                        "Concluido com sucesso",
                    )
                else:
                    self._finish_error(
                        "=== Consolidacao Falhou ===",
                        "Falha na consolidacao",
                    )
                return

            if self.explicit_files or self.source_files:
                batch_success = self._run_explicit_import_batches()
                if batch_success is None:
                    return
                if self._should_stop:
                    self.last_outcome = RescanOutcome.CANCELLED
                    self.finished_error.emit("Processo cancelado pelo usuario")
                    return
                success = batch_success
                new_ssas = self._last_ssa_inserted
                self.output_line.emit("")
                if (
                    self._database_rows_before is not None
                    and self._database_rows_after is not None
                ):
                    database_summary = (
                        f"{self._database_rows_before} -> "
                        f"{self._database_rows_after} SSAs no total"
                    )
                else:
                    database_summary = "contagem total indisponivel"
                self.output_line.emit(
                    f"Banco de dados: {database_summary}; "
                    f"{self._last_ssa_updated} SSAs atualizadas; "
                    f"{new_ssas} SSAs novas."
                )
            else:
                should_continue, _summary = self._prepare_import_inputs()
                if not should_continue:
                    return
                success = self._run_import_operation()

            if self._should_stop:
                self.last_outcome = RescanOutcome.CANCELLED
                self.finished_error.emit("Processo cancelado pelo usuario")
                return

            if success:
                self._finish_success(
                    (
                        RescanOutcome.UPDATED
                        if self._last_processed_files > 0
                        else RescanOutcome.NO_CHANGES
                    ),
                    "=== Operacao Concluida ===",
                    "Concluido com sucesso",
                )
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
                    if self._has_runtime_errors:
                        self.last_outcome = RescanOutcome.ERROR
                        self.progress.emit(100, "Falha no reescaneamento diferencial")
                        self.output_line.emit("")
                        self.output_line.emit(
                            "=== Reescaneamento Diferencial Falhou ==="
                        )
                        self.output_line.emit(
                            "Importacao diferencial falhou com erros durante o processamento."
                        )
                        self.finished_error.emit(
                            self._runtime_failure_message(
                                "Importacao diferencial falhou com erros"
                            )
                        )
                        return
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
                    if self._has_runtime_errors:
                        self.last_outcome = RescanOutcome.ERROR
                        self.progress.emit(100, "Falha no reescaneamento completo")
                        self.output_line.emit("")
                        self.output_line.emit("=== Reescaneamento Completo Falhou ===")
                        self.output_line.emit(
                            "Importacao falhou com erros durante o processamento."
                        )
                        self.finished_error.emit(
                            self._runtime_failure_message(
                                "Importacao completa falhou com erros"
                            )
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
            details = str(exc).strip() or exc.__class__.__name__
            cause = exc.__cause__
            if cause is not None:
                cause_text = str(cause).strip() or cause.__class__.__name__
                cause_details = f"{cause.__class__.__name__}: {cause_text}"
                if cause_text not in details:
                    details = f"{details} | Causa raiz: {cause_details}"
            message = f"Erro ao executar operacao de importacao: {details}"
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
            logger.debug("LogHandler emit falhou: %s", e)
