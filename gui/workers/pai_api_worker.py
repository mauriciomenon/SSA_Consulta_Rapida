"""Worker for PAI API refresh through scrap_report."""

from __future__ import annotations

from dataclasses import dataclass
from dataclasses import replace
from pathlib import Path

from core.pai_api_options import PaiApiGuiOptions, pai_api_options_error
from core.pai_import_service import PaiImportResult, fetch_and_import_pai_xlsx
from core.pai_scrap_report_provider import (
    PAI_RUNNER_UV,
    PaiScrapReportRequest,
    run_pai_scrap_report_ca_export,
)
from gui.workers.qt_thread_shim import QThread, pyqtSignal


@dataclass(frozen=True)
class PaiApiWorkerConfig:
    project_root: Path
    docs_dir: Path
    db_path: Path
    output_dir: Path
    options: PaiApiGuiOptions


class PaiApiRefreshWorker(QThread):
    output_line = pyqtSignal(str)
    error_line = pyqtSignal(str)
    progress = pyqtSignal(int, str)
    finished_success = pyqtSignal()
    finished_error = pyqtSignal(str)

    def __init__(self, config: PaiApiWorkerConfig):
        super().__init__()
        self.config = config
        self.results: list[PaiImportResult] = []

    def run(self) -> None:
        self.results.clear()
        try:
            self._run_refresh()
        except Exception as exc:
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
            "Iniciando API PAI: setores=" + ", ".join(sectors)
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
        self.progress.emit(5, "API PAI: validando CA")
        certificate = run_pai_scrap_report_ca_export(base_request)
        self.progress.emit(10, "API PAI: baixando XLSX")
        result = fetch_and_import_pai_xlsx(
            replace(base_request, ca_file=certificate.ca_file),
            docs_dir=self.config.docs_dir,
            db_path=self.config.db_path,
        )
        self.results.append(result)
        self.output_line.emit(_format_refresh_result(result))

        self.progress.emit(100, "API PAI concluida")
        self.finished_success.emit()


def _format_refresh_result(result: PaiImportResult) -> str:
    rows = result.rows_after_import
    if result.imported:
        if rows == 0:
            return "[OK SEM LINHAS] API PAI importada sem registros no banco."
        return f"[OK] API PAI importada; linhas no banco={rows}"
    return "[NAO IMPORTADO] API PAI processada; importacao no banco nao confirmada."
