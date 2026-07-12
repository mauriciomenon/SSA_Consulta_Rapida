"""Worker for PAI API refresh through scrap_report."""

from __future__ import annotations

import logging
from concurrent.futures import Future, ThreadPoolExecutor, TimeoutError
from dataclasses import dataclass
from dataclasses import replace
from pathlib import Path
from threading import Event, Lock
from time import monotonic
from typing import Sequence

from core.pai_api_options import (
    PAI_API_ENABLED_DATA_SCOPES,
    PAI_API_REST_DATA_SCOPES,
    PaiApiGuiOptions,
    pai_api_options_error,
)
from core.pai_import_service import (
    PaiFetchedXlsxPreview,
    PaiImportResult,
    fetch_pai_xlsx_preview,
    import_prepared_pai_xlsx,
)
from core.pai_scrap_report_provider import (
    PAI_RUNNER_UV,
    PaiScrapReportRequest,
    run_pai_scrap_report_ca_export,
)
from extracao.extractor import ExtractionError, validate_excel_import_limits
from gui.ssa.pai_api_status_text import trim_pai_api_status_detail
from gui.workers.qt_thread_shim import QThread, pyqtSignal


PAI_API_MAX_CONCURRENT_FETCHES = 3
PAI_API_IMPORT_CONFIRM_TIMEOUT_SECONDS = 300.0
PAI_API_FETCH_FUTURE_GRACE_SECONDS = 30.0
PAI_API_FETCH_POLL_SECONDS = 0.1

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class PaiApiWorkerConfig:
    project_root: Path
    docs_dir: Path
    db_path: Path
    output_dir: Path
    options: PaiApiGuiOptions
    confirm_before_import: bool = False
    fetch_only: bool = False


@dataclass(frozen=True)
class PaiApiRefreshSummary:
    previewed_sectors: int
    imported_sectors: int
    failed_sectors: int
    normalized_rows: int
    imported_normalized_rows: int
    rows_after_import: int | None
    import_skipped: bool
    failures: tuple[str, ...]


@dataclass(frozen=True)
class PaiApiImportDecisionRequest:
    previewed_sectors: int
    failed_sectors: int
    normalized_rows: int
    failures: tuple[str, ...]


@dataclass(frozen=True)
class _PaiSectorPreview:
    sector: str
    request: PaiScrapReportRequest
    docs_dir: Path
    preview: PaiFetchedXlsxPreview
    progress_base: int


@dataclass(frozen=True)
class _PaiSectorRequest:
    sector: str
    request: PaiScrapReportRequest
    docs_dir: Path
    progress_base: int


class PaiApiRefreshWorker(QThread):
    output_line = pyqtSignal(str)
    error_line = pyqtSignal(str)
    progress = pyqtSignal(int, str)
    preview_ready = pyqtSignal(object)
    import_decision_required = pyqtSignal(object)
    finished_success = pyqtSignal()
    finished_error = pyqtSignal(str)

    def __init__(self, config: PaiApiWorkerConfig):
        super().__init__()
        self.config = config
        self.results: list[PaiImportResult] = []
        self.failures: list[str] = []
        self.previews: list[_PaiSectorPreview] = []
        self._summary = PaiApiRefreshSummary(0, 0, 0, 0, 0, None, False, ())
        self._state_lock = Lock()
        self._import_decision_event = Event()
        self._import_decision = False
        self._import_decision_ready = False
        self._import_decision_timed_out = False
        self._cancel_requested = False
        self._terminal_emitted = False
        self._executor: ThreadPoolExecutor | None = None

    def cancel(self) -> None:
        """Request the worker to stop as soon as possible.

        Signals the import-decision wait (if blocked) and shuts down the
        internal ThreadPoolExecutor so pending fetches are cancelled.
        """
        with self._state_lock:
            if self._terminal_emitted:
                return
            self._cancel_requested = True
            executor = self._executor
        self._import_decision_event.set()
        if executor is not None:
            try:
                executor.shutdown(wait=False, cancel_futures=True)
            except RuntimeError as exc:
                logger.debug("Falha ao encerrar executor do PaiApi no cancel: %s", exc)

    def _is_cancelled(self) -> bool:
        with self._state_lock:
            return self._cancel_requested

    def summary(self) -> PaiApiRefreshSummary:
        with self._state_lock:
            return self._summary

    def set_import_decision(self, approved: bool) -> None:
        with self._state_lock:
            self._import_decision = bool(approved)
            self._import_decision_ready = True
        self._import_decision_event.set()

    def reset_for_start(self) -> None:
        with self._state_lock:
            self.results.clear()
            self.failures.clear()
            self.previews.clear()
            self._summary = PaiApiRefreshSummary(0, 0, 0, 0, 0, None, False, ())
            self._import_decision = False
            self._import_decision_ready = False
            self._import_decision_timed_out = False
            self._terminal_emitted = False
            self._import_decision_event.clear()

    def _finish(self, error: str | None = None) -> None:
        with self._state_lock:
            if self._cancel_requested or self._terminal_emitted:
                return
            self._terminal_emitted = True
        if error is None:
            self.finished_success.emit()
        else:
            self.finished_error.emit(error)

    def run(self) -> None:
        self.reset_for_start()
        if self._is_cancelled():
            return
        try:
            self._run_refresh()
        except Exception as exc:
            if self._is_cancelled():
                return
            message = trim_pai_api_status_detail(str(exc or "") or type(exc).__name__)
            self._add_failure(message)
            self._refresh_summary()
            self._finish(message)

    def _run_refresh(self) -> None:
        if self._is_cancelled():
            return
        options = self.config.options
        sectors = tuple(options.all_executor_sectors)
        data_scopes = tuple(
            scope for scope in options.data_scopes if scope in PAI_API_ENABLED_DATA_SCOPES
        )
        if (error_message := pai_api_options_error(options)) is not None:
            self._finish(error_message)
            return

        self.config.output_dir.mkdir(parents=True, exist_ok=True)
        self.output_line.emit(
            "Iniciando SAM API: setores=" + ", ".join(sectors)
        )

        base_request = PaiScrapReportRequest(
            project_root=self.config.project_root,
            output_dir=self.config.output_dir,
            allow_sibling_scrap_report=True,
            runner=PAI_RUNNER_UV,
            executor_sectors=sectors,
            limit=options.limit,
            number_of_years=options.number_of_years,
            base_url=options.base_url,
            username=options.username,
            secret_service=options.secret_service,
            secure_required=options.secure_required,
        )

        previews: list[_PaiSectorPreview] = []
        total_scope_runs = max(len(data_scopes) * len(sectors), 1)
        scope_run_index = 1
        for data_scope in data_scopes:
            if self._is_cancelled():
                return
            scoped_request = replace(
                base_request,
                data_scope=data_scope,
                report_kind=data_scope if data_scope.startswith("aprovacao_") else None,
                include_details=data_scope in PAI_API_REST_DATA_SCOPES,
            )
            ca_file: Path | None = None
            if data_scope in PAI_API_REST_DATA_SCOPES:
                self.progress.emit(5, "SAM API: validando CA")
                certificate = self._validate_ca(scoped_request)
                if certificate is None:
                    scope_run_index += len(sectors)
                    continue
                ca_file = certificate.ca_file
            previews.extend(
                self._fetch_sector_previews(
                    self._sector_requests(
                        scoped_request,
                        ca_file,
                        sectors,
                        progress_span=(scope_run_index, total_scope_runs),
                    )
                )
            )
            scope_run_index += len(sectors)
        if self._is_cancelled():
            return
        self._refresh_summary(previews=previews)
        if not previews:
            self._finish(_format_total_failure(self._failures_snapshot()))
            return

        try:
            validate_excel_import_limits(
                tuple(item.preview.import_xlsx_path for item in previews),
                ignore_unavailable=True,
                reject_invalid_archives=False,
            )
        except ExtractionError as exc:
            self._add_failure(f"lote XLSX PAI rejeitado: {exc}")
            self._refresh_summary(previews=previews)
            self._finish(_format_total_failure(self._failures_snapshot()))
            return

        if self.config.fetch_only:
            if self._is_cancelled():
                return
            self._mark_import_skipped(previews=previews)
            self.progress.emit(100, "SAM API preview concluido; DB inalterado")
            self._finish()
            return

        if self.config.confirm_before_import and not self._confirm_import(previews):
            if self._is_cancelled():
                return
            if self._import_decision_timed_out:
                self._refresh_summary(previews=previews)
                self._finish(_format_total_failure(self._failures_snapshot()))
                return
            self._mark_import_skipped(previews=previews)
            self.progress.emit(100, "SAM API preview concluido; DB inalterado")
            self._finish()
            return

        for preview in previews:
            if self._is_cancelled():
                return
            self._import_sector_preview(preview)

        if self._is_cancelled():
            return
        imported_count = sum(1 for result in self._results_snapshot() if result.imported)
        self._refresh_summary(previews=previews)
        if imported_count == 0:
            self._finish(_format_total_failure(self._failures_snapshot()))
            return

        self.progress.emit(
            100,
            f"SAM API concluida: {imported_count} setores importados; "
            f"{len(self._failures_snapshot())} falharam",
        )
        self._finish()

    def _validate_ca(self, request: PaiScrapReportRequest):
        try:
            return run_pai_scrap_report_ca_export(request)
        except Exception as exc:
            if self._is_cancelled():
                return None
            failure = _format_ca_failure(exc)
            self._add_failure(failure)
            self._refresh_summary()
            self.error_line.emit(failure)
            return None

    def _sector_requests(
        self,
        base_request: PaiScrapReportRequest,
        ca_file: Path | None,
        sectors: tuple[str, ...],
        *,
        progress_span: tuple[int, int],
    ) -> list[_PaiSectorRequest]:
        start_index, total_runs = progress_span
        total = max(int(total_runs), 1)
        requests = []
        for index, sector in enumerate(sectors, start=max(int(start_index), 1)):
            progress_base = 10 + int((index - 1) * 80 / total)
            sector_request = self._sector_request(base_request, ca_file, sector)
            requests.append(
                _PaiSectorRequest(
                    sector=sector,
                    request=sector_request,
                    docs_dir=self._sector_docs_dir(base_request.data_scope, sector),
                    progress_base=progress_base,
                )
            )
        return requests

    def _sector_docs_dir(self, data_scope: str, sector: str) -> Path:
        docs_root = self.config.docs_dir / "pai_api"
        if data_scope in PAI_API_REST_DATA_SCOPES:
            return docs_root / sector
        return docs_root / data_scope / sector

    def _sector_request(
        self,
        base_request: PaiScrapReportRequest,
        ca_file: Path | None,
        sector: str,
    ) -> PaiScrapReportRequest:
        output_root = self.config.output_dir
        if base_request.data_scope not in PAI_API_REST_DATA_SCOPES:
            output_root = output_root / base_request.data_scope
        return replace(
            base_request,
            ca_file=ca_file,
            executor_sectors=(sector,),
            output_dir=output_root / sector,
        )

    def _fetch_sector_previews(
        self,
        requests: list[_PaiSectorRequest],
    ) -> list[_PaiSectorPreview]:
        if not requests:
            return []
        previews: list[_PaiSectorPreview] = []
        for sector_request, future in self._collect_sector_previews(requests):
            if self._is_cancelled():
                break
            preview = self._sector_preview_from_future(sector_request, future)
            if preview is not None and not self._is_cancelled():
                previews.append(preview)
                with self._state_lock:
                    self.previews.append(preview)
        return previews

    def _collect_sector_previews(
        self,
        requests: list[_PaiSectorRequest],
    ):
        workers = min(PAI_API_MAX_CONCURRENT_FETCHES, len(requests))
        executor = ThreadPoolExecutor(max_workers=workers)
        try:
            with self._state_lock:
                if self._cancel_requested:
                    self._executor = None
                    return
                self._executor = executor
            futures = [
                executor.submit(self._fetch_sector_preview, request)
                for request in requests
            ]
            for sector_request, future in zip(requests, futures):
                if self._is_cancelled():
                    break
                yield sector_request, future
        finally:
            with self._state_lock:
                if self._executor is executor:
                    self._executor = None
            executor.shutdown(
                wait=True,
                cancel_futures=True,
            )

    def _sector_preview_from_future(
        self,
        sector_request: _PaiSectorRequest,
        future: Future[_PaiSectorPreview],
    ) -> _PaiSectorPreview | None:
        if self._is_cancelled():
            future.cancel()
            return None
        self.progress.emit(
            sector_request.progress_base,
            f"SAM API: setor {sector_request.sector}",
        )
        timeout_seconds = (
            float(sector_request.request.command_timeout_seconds)
            + PAI_API_FETCH_FUTURE_GRACE_SECONDS
        )
        deadline = monotonic() + timeout_seconds
        while True:
            if self._is_cancelled():
                future.cancel()
                return None
            remaining = deadline - monotonic()
            if remaining <= 0:
                future.cancel()
                failure = (
                    f"setor {sector_request.sector}: timeout ao obter preview "
                    f"({timeout_seconds:g}s)"
                )
                self._add_failure(failure)
                self._refresh_summary()
                self.error_line.emit(failure)
                return None
            try:
                preview = future.result(
                    timeout=min(PAI_API_FETCH_POLL_SECONDS, remaining)
                )
                break
            except TimeoutError:
                continue
            except Exception as exc:
                if self._is_cancelled():
                    return None
                failure = _format_sector_failure(sector_request.sector, exc)
                self._add_failure(failure)
                self._refresh_summary()
                self.error_line.emit(failure)
                return None
        if self._is_cancelled():
            return None
        self.preview_ready.emit(preview.preview)
        self.progress.emit(
            min(sector_request.progress_base + 5, 95),
            "SAM API: setor "
            f"{sector_request.sector}; "
            f"{preview.preview.normalized_rows} linhas",
        )
        return preview

    def _fetch_sector_preview(
        self,
        sector_request: _PaiSectorRequest,
    ) -> _PaiSectorPreview:
        preview = fetch_pai_xlsx_preview(
            sector_request.request,
            docs_dir=sector_request.docs_dir,
        )
        return _PaiSectorPreview(
            sector=sector_request.sector,
            request=sector_request.request,
            docs_dir=sector_request.docs_dir,
            preview=preview,
            progress_base=sector_request.progress_base,
        )

    def _import_sector_preview(self, sector_preview: _PaiSectorPreview) -> None:
        if self._is_cancelled():
            return
        try:
            result = import_prepared_pai_xlsx(
                sector_preview.request,
                sector_preview.preview,
                docs_dir=sector_preview.docs_dir,
                db_path=self.config.db_path,
                should_cancel=self._is_cancelled,
            )
        except Exception as exc:
            if self._is_cancelled():
                return
            failure = _format_sector_failure(sector_preview.sector, exc)
            self._add_failure(failure)
            self.error_line.emit(failure)
            return
        if self._is_cancelled():
            return
        self._add_result(result)
        self.output_line.emit(
            f"setor {sector_preview.sector}: {_format_refresh_result(result)}"
        )

    def _confirm_import(self, previews: list[_PaiSectorPreview]) -> bool:
        if self._is_cancelled():
            return False
        self.import_decision_required.emit(_decision_request(previews, self._failures_snapshot()))
        if not self._import_decision_event.wait(PAI_API_IMPORT_CONFIRM_TIMEOUT_SECONDS):
            with self._state_lock:
                self._import_decision_timed_out = True
            self._add_failure("confirmacao de importacao nao recebida")
            return False
        with self._state_lock:
            if self._cancel_requested:
                return False
            if not self._import_decision_ready:
                self._import_decision_timed_out = True
                self._add_failure("confirmacao de importacao nao recebida")
                return False
            return self._import_decision

    def _mark_import_skipped(self, previews: list[_PaiSectorPreview]) -> None:
        self._set_summary(_summary_from_state(
            results=self._results_snapshot(),
            failures=self._failures_snapshot(),
            previews=tuple(previews),
            import_skipped=True,
        ))

    def _refresh_summary(self, previews: list[_PaiSectorPreview] | None = None) -> None:
        results = self._results_snapshot()
        failures = self._failures_snapshot()
        preview_snapshot = tuple(previews) if previews is not None else self._previews_snapshot()
        self._set_summary(_summary_from_state(
            results=results,
            failures=failures,
            previews=preview_snapshot,
            import_skipped=False,
        ))

    def _set_summary(self, summary: PaiApiRefreshSummary) -> None:
        with self._state_lock:
            self._summary = summary

    def _add_result(self, result: PaiImportResult) -> None:
        with self._state_lock:
            self.results.append(result)

    def _add_failure(self, failure: str) -> None:
        with self._state_lock:
            self.failures.append(failure)

    def _results_snapshot(self) -> tuple[PaiImportResult, ...]:
        with self._state_lock:
            return tuple(self.results)

    def _failures_snapshot(self) -> tuple[str, ...]:
        with self._state_lock:
            return tuple(self.failures)

    def _previews_snapshot(self) -> tuple[_PaiSectorPreview, ...]:
        with self._state_lock:
            return tuple(self.previews)


def _format_refresh_result(result: PaiImportResult) -> str:
    rows = result.rows_after_import
    if result.imported:
        if rows == 0:
            return "[OK SEM LINHAS] SAM API importada sem registros no banco."
        return f"[OK] SAM API importada; linhas no banco={rows}"
    return "[NAO IMPORTADO] SAM API processada; importacao no banco nao confirmada."


def format_preview_status(preview: PaiFetchedXlsxPreview) -> str:
    return (
        "SAM API: "
        f"{preview.normalized_rows} linhas validadas em "
        f"{preview.import_xlsx_path.name}"
    )


def format_decision_request_status(request: PaiApiImportDecisionRequest) -> str:
    return (
        "SAM API: "
        f"{request.normalized_rows} linhas em {request.previewed_sectors} setores; "
        "aguardando confirmacao"
    )


def _decision_request(
    previews: list[_PaiSectorPreview],
    failures: Sequence[str],
) -> PaiApiImportDecisionRequest:
    return PaiApiImportDecisionRequest(
        previewed_sectors=len(previews),
        failed_sectors=len(failures),
        normalized_rows=sum(preview.preview.normalized_rows for preview in previews),
        failures=tuple(failures),
    )


def _summary_from_state(
    *,
    results: Sequence[PaiImportResult],
    failures: Sequence[str],
    previews: Sequence[_PaiSectorPreview],
    import_skipped: bool,
) -> PaiApiRefreshSummary:
    imported_results = tuple(result for result in results if result.imported)
    rows_after_import = next(
        (
            result.rows_after_import
            for result in reversed(imported_results)
            if result.rows_after_import is not None
        ),
        None,
    )
    return PaiApiRefreshSummary(
        previewed_sectors=len(previews),
        imported_sectors=len(imported_results),
        failed_sectors=len(failures),
        normalized_rows=sum(preview.preview.normalized_rows for preview in previews),
        imported_normalized_rows=sum(
            int(result.normalized_rows or 0) for result in imported_results
        ),
        rows_after_import=rows_after_import,
        import_skipped=import_skipped,
        failures=tuple(failures),
    )


def _format_sector_failure(sector: str, exc: Exception) -> str:
    detail = " ".join(str(exc or "").split())
    if not detail:
        detail = type(exc).__name__
    return (
        f"setor {sector}: "
        f"{detail}"
    )


def _format_total_failure(failures: Sequence[str]) -> str:
    if not failures:
        return "SAM API: nenhum setor importado; DB inalterado."
    detail = "; ".join(failures[:3])
    if len(failures) > 3:
        detail += f"; +{len(failures) - 3} setores"
    return f"SAM API: todos setores falharam; DB inalterado. {detail}"


def _format_ca_failure(exc: Exception) -> str:
    detail = " ".join(str(exc or "").split())
    if not detail:
        detail = type(exc).__name__
    return (
        "SAM API: falha ao validar CA; DB inalterado. "
        f"{detail}"
    )
