"""PAI XLSX import orchestration."""

from __future__ import annotations

from dataclasses import dataclass, field
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
from core.pai_xlsx_summary import PaiXlsxSummary
from core.pai_xlsx_summary import empty_pai_xlsx_summary
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
    xlsx_summary: PaiXlsxSummary = field(default_factory=empty_pai_xlsx_summary)


@dataclass(frozen=True)
class PaiFetchedXlsxPreview:
    export: PaiScrapReportExport
    import_xlsx_path: Path
    normalized_rows: int
    xlsx_summary: PaiXlsxSummary = field(default_factory=empty_pai_xlsx_summary)


def preview_only_pai_import_result(preview: PaiFetchedXlsxPreview) -> PaiImportResult:
    return PaiImportResult(
        export=preview.export,
        mode="fetch_only",
        import_xlsx_path=preview.import_xlsx_path,
        staged_files=(),
        staging_summary=empty_external_staging_summary(),
        imported=False,
        normalized_rows=preview.normalized_rows,
        rows_before_import=None,
        rows_after_import=None,
        xlsx_summary=preview.xlsx_summary,
    )


def fetch_pai_xlsx_preview(
    request: PaiScrapReportRequest,
    *,
    docs_dir: Path,
) -> PaiFetchedXlsxPreview:
    return _fetch_and_normalize_pai_xlsx(request, docs_dir=docs_dir)


def preview_existing_pai_xlsx(
    request: PaiScrapReportRequest,
    source_xlsx: Path,
    *,
    docs_dir: Path,
) -> PaiFetchedXlsxPreview:
    source_xlsx = Path(source_xlsx).expanduser().resolve(strict=False)
    if not source_xlsx.is_file():
        raise FileNotFoundError(f"XLS PAI nao encontrado: {source_xlsx}")
    export = PaiScrapReportExport(
        command=("source-xlsx", str(source_xlsx)),
        scrap_report_root=request.project_root,
        manifest_path=source_xlsx,
        xlsx_path=source_xlsx,
        manifest={"source": "local_xlsx"},
        stdout="",
        stderr="",
    )
    return _normalize_export_for_preview(export, docs_dir=docs_dir)


def import_prepared_pai_xlsx(
    request: PaiScrapReportRequest,
    preview: PaiFetchedXlsxPreview,
    *,
    docs_dir: Path,
    db_path: Path,
    stage_files: StageFunction = stage_external_import_files,
    import_files: ImportFunction = import_explicit_files_to_database,
    count_rows: RowCountFunction = count_imported_ssa_rows,
) -> PaiImportResult:
    rows_before_import = count_rows(db_path)
    staged_files, summary = stage_files(
        project_root=request.project_root,
        docs_dir=docs_dir,
        source_files=(str(preview.import_xlsx_path),),
    )
    if not staged_files:
        return PaiImportResult(
            export=preview.export,
            mode="import",
            import_xlsx_path=preview.import_xlsx_path,
            staged_files=(),
            staging_summary=summary,
            imported=False,
            normalized_rows=preview.normalized_rows,
            rows_before_import=rows_before_import,
            rows_after_import=None,
            xlsx_summary=preview.xlsx_summary,
        )
    imported = import_files(
        staged_files,
        docs_dir=str(docs_dir),
        db_path=str(db_path),
        raise_on_error=False,
    )
    rows_after_import = count_rows(db_path)
    return PaiImportResult(
        export=preview.export,
        mode="import",
        import_xlsx_path=preview.import_xlsx_path,
        staged_files=tuple(staged_files),
        staging_summary=summary,
        imported=bool(imported),
        normalized_rows=preview.normalized_rows,
        rows_before_import=rows_before_import,
        rows_after_import=rows_after_import,
        xlsx_summary=preview.xlsx_summary,
    )


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
    preview = _fetch_and_normalize_pai_xlsx(request, docs_dir=docs_dir)
    if fetch_only:
        return preview_only_pai_import_result(preview)

    return import_prepared_pai_xlsx(
        request,
        preview,
        docs_dir=docs_dir,
        db_path=db_path,
        stage_files=stage_files,
        import_files=import_files,
        count_rows=count_rows,
    )


def _fetch_and_normalize_pai_xlsx(
    request: PaiScrapReportRequest,
    *,
    docs_dir: Path,
) -> PaiFetchedXlsxPreview:
    export = run_pai_scrap_report_export(request)
    return _normalize_export_for_preview(export, docs_dir=docs_dir)


def _normalize_export_for_preview(
    export: PaiScrapReportExport,
    *,
    docs_dir: Path,
) -> PaiFetchedXlsxPreview:
    with _normalize_for_import(export.xlsx_path, docs_dir) as normalized_result:
        normalized_result.preserve()
        return PaiFetchedXlsxPreview(
            export=export,
            import_xlsx_path=normalized_result.path,
            normalized_rows=normalized_result.row_count,
            xlsx_summary=normalized_result.summary,
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
    target.parent.mkdir(parents=True, exist_ok=True)
    return Path(reserve_unique_path(target, touch=True))
