"""PAI XLSX import orchestration."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable, ContextManager

from core.app_logic import import_explicit_files_to_database
from core.import_staging import empty_external_staging_summary
from core.import_staging import stage_external_import_files
from core.pai_scrap_report_provider import (
    PaiScrapReportExport,
    PaiScrapReportRequest,
    run_pai_scrap_report_export,
)
from core.pai_import_verifier import count_imported_ssa_rows
from core.pai_xlsx_normalizer import default_ssa_import_xlsx_path
from core.pai_xlsx_normalizer import ManagedPaiXlsxNormalization
from core.pai_xlsx_normalizer import managed_pai_xlsx_for_ssa_import
from utils.path_safety import reserve_unique_path

ImportFunction = Callable[..., bool]
RowCountFunction = Callable[[Path], int | None]
StageFunction = Callable[..., tuple[list[str], dict[str, int]]]


@dataclass(frozen=True)
class PaiImportResult:
    export: PaiScrapReportExport
    mode: str
    import_xlsx_path: Path | None
    staged_files: tuple[str, ...]
    staging_summary: dict[str, int]
    imported: bool
    normalized_rows: int | None
    rows_before_import: int | None
    rows_after_import: int | None


def fetch_and_import_pai_xlsx(
    request: PaiScrapReportRequest,
    *,
    docs_dir: Path,
    db_path: Path,
    fetch_only: bool = False,
    stage_files: StageFunction = stage_external_import_files,
    import_files: ImportFunction = import_explicit_files_to_database,
    count_rows: RowCountFunction = count_imported_ssa_rows,
) -> PaiImportResult:
    export = run_pai_scrap_report_export(request)
    if fetch_only:
        return PaiImportResult(
            export=export,
            mode="fetch_only",
            import_xlsx_path=None,
            staged_files=(),
            staging_summary=empty_external_staging_summary(),
            imported=False,
            normalized_rows=None,
            rows_before_import=None,
            rows_after_import=None,
        )

    with _normalize_for_import(export.xlsx_path, docs_dir) as normalized_result:
        import_xlsx_path = normalized_result.path
        staged_files, summary = stage_files(
            project_root=request.project_root,
            docs_dir=docs_dir,
            source_files=(str(import_xlsx_path),),
        )
        if not staged_files:
            return PaiImportResult(
                export=export,
                mode="import",
                import_xlsx_path=import_xlsx_path,
                staged_files=(),
                staging_summary=summary,
                imported=False,
                normalized_rows=normalized_result.row_count,
                rows_before_import=None,
                rows_after_import=None,
            )
        rows_before_import = count_rows(db_path)
        imported = import_files(
            staged_files,
            docs_dir=str(docs_dir),
            db_path=str(db_path),
            raise_on_error=False,
        )
        rows_after_import = count_rows(db_path) if imported else None
        if imported:
            normalized_result.preserve()
        return PaiImportResult(
            export=export,
            mode="import",
            import_xlsx_path=import_xlsx_path,
            staged_files=tuple(staged_files),
            staging_summary=summary,
            imported=bool(imported),
            normalized_rows=normalized_result.row_count,
            rows_before_import=rows_before_import,
            rows_after_import=rows_after_import,
        )


def _normalize_for_import(
    source_xlsx: Path,
    docs_dir: Path,
) -> ContextManager[ManagedPaiXlsxNormalization]:
    return managed_pai_xlsx_for_ssa_import(
        source_xlsx,
        _build_import_xlsx_path(docs_dir, source_xlsx),
    )


def _build_import_xlsx_path(docs_dir: Path, source_xlsx: Path) -> Path:
    target = docs_dir / default_ssa_import_xlsx_path(source_xlsx).name
    return Path(reserve_unique_path(target, reserved_paths=set()))
