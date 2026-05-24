"""Worker for PAI API refresh through scrap_report."""

from __future__ import annotations

from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import dataclass
from dataclasses import replace
from pathlib import Path
from threading import Event, Lock
from typing import Sequence

from core.pai_api_options import PaiApiGuiOptions, pai_api_options_error
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
from gui.ssa.pai_api_status_text import trim_pai_api_status_detail
from gui.workers.qt_thread_shim import QThread, pyqtSignal


PAI_API_MAX_CONCURRENT_FETCHES = 3
PAI_API_IMPORT_CONFIRM_TIMEOUT_SECONDS = 300.0


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
        self._summary = PaiApiRefreshSummary(0, 0, 0, 0, 0, None, False, ())
        self._state_lock = Lock()
        self._import_decision_event = Event()
        self._import_decision = False
        self._import_decision_ready = False

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
            self._summary = PaiApiRefreshSummary(0, 0, 0, 0, 0, None, False, ())
            self._import_decision = False
            self._import_decision_ready = False
            self._import_decision_event.clear()

    def run(self) -> None:
        try:
            self._run_refresh()
        except Exception as exc:
            self._refresh_summary()
            self.finished_error.emit(str(exc))

    def _run_refresh(self) -> None:
        options = self.config.options
        sectors = tuple(options.executor_sectors)
        options_error = pai_api_options_error(options)
        if options_error is not None:
            self.finished_error.emit(options_error)
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
        )
        self.progress.emit(5, "SAM API: validando CA")
        certificate = self._validate_ca(base_request)
        if certificate is None:
            return

        previews = self._fetch_sector_previews(
            self._sector_requests(base_request, certificate.ca_file, sectors)
        )
        self._refresh_summary(previews=previews)
        if not previews:
            self.finished_error.emit(_format_total_failure(self._failures_snapshot()))
            return

        if self.config.fetch_only:
            self._mark_import_skipped(previews=previews)
            self.progress.emit(100, "SAM API preview concluido; DB inalterado")
            self.finished_success.emit()
            return

        if self.config.confirm_before_import and not self._confirm_import(previews):
            self._mark_import_skipped(previews=previews)
            self.progress.emit(100, "SAM API preview concluido; DB inalterado")
            self.finished_success.emit()
            return

        for preview in previews:
            self._import_sector_preview(preview)

        imported_count = sum(1 for result in self._results_snapshot() if result.imported)
        self._refresh_summary(previews=previews)
        if imported_count == 0:
            self.finished_error.emit(_format_total_failure(self._failures_snapshot()))
            return

        failed_count = len(self._failures_snapshot())
        self.progress.emit(
            100,
            f"SAM API concluida: {imported_count} setores importados; "
            f"{failed_count} falharam",
        )
        self.finished_success.emit()

    def _validate_ca(self, request: PaiScrapReportRequest):
        try:
            return run_pai_scrap_report_ca_export(request)
        except Exception as exc:
            failure = _format_ca_failure(exc)
            self._add_failure(failure)
            self._refresh_summary()
            self.finished_error.emit(failure)
            return None

    def _sector_requests(
        self,
        base_request: PaiScrapReportRequest,
        ca_file: Path,
        sectors: tuple[str, ...],
    ) -> list[_PaiSectorRequest]:
        total = max(len(sectors), 1)
        requests = []
        for index, sector in enumerate(sectors, start=1):
            progress_base = 10 + int((index - 1) * 80 / total)
            sector_request = self._sector_request(base_request, ca_file, sector)
            requests.append(
                _PaiSectorRequest(
                    sector=sector,
                    request=sector_request,
                    docs_dir=self.config.docs_dir / "pai_api" / sector,
                    progress_base=progress_base,
                )
            )
        return requests

    def _sector_request(
        self,
        base_request: PaiScrapReportRequest,
        ca_file: Path,
        sector: str,
    ) -> PaiScrapReportRequest:
        return replace(
            base_request,
            ca_file=ca_file,
            executor_sectors=(sector,),
            output_dir=self.config.output_dir / sector,
        )

    def _fetch_sector_previews(
        self,
        requests: list[_PaiSectorRequest],
    ) -> list[_PaiSectorPreview]:
        if not requests:
            return []
        previews: list[_PaiSectorPreview] = []
        for sector_request, future in self._collect_sector_previews(requests):
            preview = self._sector_preview_from_future(sector_request, future)
            if preview is not None:
                previews.append(preview)
        return previews

    def _collect_sector_previews(
        self,
        requests: list[_PaiSectorRequest],
    ):
        workers = min(PAI_API_MAX_CONCURRENT_FETCHES, len(requests))
        with ThreadPoolExecutor(max_workers=workers) as executor:
            futures = [
                executor.submit(self._fetch_sector_preview, request)
                for request in requests
            ]
            for sector_request, future in zip(requests, futures):
                yield sector_request, future

    def _sector_preview_from_future(
        self,
        sector_request: _PaiSectorRequest,
        future: Future[_PaiSectorPreview],
    ) -> _PaiSectorPreview | None:
        self.progress.emit(
            sector_request.progress_base,
            f"SAM API: setor {sector_request.sector}",
        )
        try:
            preview = future.result()
        except Exception as exc:
            failure = _format_sector_failure(sector_request.sector, exc)
            self._add_failure(failure)
            self.error_line.emit(failure)
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
        try:
            result = import_prepared_pai_xlsx(
                sector_preview.request,
                sector_preview.preview,
                docs_dir=sector_preview.docs_dir,
                db_path=self.config.db_path,
            )
        except Exception as exc:
            failure = _format_sector_failure(sector_preview.sector, exc)
            self._add_failure(failure)
            self.error_line.emit(failure)
            return
        self._add_result(result)
        self.output_line.emit(
            f"setor {sector_preview.sector}: {_format_refresh_result(result)}"
        )

    def _confirm_import(self, previews: list[_PaiSectorPreview]) -> bool:
        self.import_decision_required.emit(_decision_request(previews, self._failures_snapshot()))
        if not self._import_decision_event.wait(PAI_API_IMPORT_CONFIRM_TIMEOUT_SECONDS):
            self._add_failure("confirmacao de importacao nao recebida")
            return False
        with self._state_lock:
            if not self._import_decision_ready:
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
        self._set_summary(_summary_from_state(
            results=results,
            failures=failures,
            previews=tuple(previews or ()),
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
    detail = trim_pai_api_status_detail(str(exc or "") or type(exc).__name__)
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
    detail = trim_pai_api_status_detail(str(exc or "") or type(exc).__name__)
    return (
        "SAM API: falha ao validar CA; DB inalterado. "
        f"{detail}"
    )
