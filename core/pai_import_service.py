"""PAI XLSX import orchestration."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from core.app_logic import import_explicit_files_to_database
from core.import_staging import empty_external_staging_summary
from core.import_staging import stage_external_import_files
from core.pai_scrap_report_provider import (
    PaiScrapReportExport,
    PaiScrapReportRequest,
    run_pai_scrap_report_export,
)

ImportFunction = Callable[..., bool]
StageFunction = Callable[..., tuple[list[str], dict[str, int]]]


@dataclass(frozen=True)
class PaiImportResult:
    export: PaiScrapReportExport
    staged_files: tuple[str, ...]
    staging_summary: dict[str, int]
    imported: bool


def fetch_and_import_pai_xlsx(
    request: PaiScrapReportRequest,
    *,
    docs_dir: Path,
    db_path: Path,
    fetch_only: bool = False,
    stage_files: StageFunction = stage_external_import_files,
    import_files: ImportFunction = import_explicit_files_to_database,
) -> PaiImportResult:
    export = run_pai_scrap_report_export(request)
    if fetch_only:
        return PaiImportResult(
            export=export,
            staged_files=(),
            staging_summary=empty_external_staging_summary(),
            imported=False,
        )

    staged_files, summary = stage_files(
        project_root=request.project_root,
        source_files=(str(export.xlsx_path),),
    )
    if not staged_files:
        return PaiImportResult(
            export=export,
            staged_files=(),
            staging_summary=summary,
            imported=False,
        )
    imported = import_files(
        staged_files,
        docs_dir=str(docs_dir),
        db_path=str(db_path),
        raise_on_error=False,
    )
    return PaiImportResult(
        export=export,
        staged_files=tuple(staged_files),
        staging_summary=summary,
        imported=bool(imported),
    )
