"""Report and status builders for PAI import results."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, TypedDict, cast

from core.pai_import_service import PaiImportResult
from core.pai_scrap_report_provider import PaiScrapReportRequest


class PaiImportSummaryPayload(TypedDict):
    source_kind: str
    requested_filters: dict[str, object]
    requested_executor_sectors: list[str]
    requested_emitter_sectors: list[str]
    requested_ssa_numbers: list[str]
    mode: str
    source_xlsx: str | None
    xlsx_path: str
    import_xlsx_path: str | None
    manifest_path: str
    imported: bool
    normalized_rows: int | None
    rows_before_import: int | None
    rows_after_import: int | None
    staged_files: list[str]
    staging_summary: dict[str, int]
    ssa_examples: list[str]
    rows_by_executor_sector: dict[str, int]
    rows_by_emitter_sector: dict[str, int]
    rows_by_source_file: dict[str, int]
    ssa_examples_by_executor_sector: dict[str, list[str]]
    summary_error: str | None
    warnings: list[str]


@dataclass(frozen=True)
class PaiImportExitStatus:
    code: int
    message_key: str | None = None
    message_value: object | None = None
    stderr: bool = False


def build_pai_import_summary_payload(
    result: PaiImportResult,
    *,
    request: PaiScrapReportRequest,
    source_xlsx: Path | None,
) -> PaiImportSummaryPayload:
    xlsx_summary = result.xlsx_summary
    requested_filters: dict[str, object] = {
        "executor_sectors": list(request.executor_sectors),
        "emitter_sectors": list(request.emitter_sectors),
        "ssa_numbers": list(request.ssa_numbers),
        "number_of_years": request.number_of_years,
        "limit": request.limit,
    }
    return PaiImportSummaryPayload(
        source_kind="source-xlsx" if source_xlsx is not None else "api",
        requested_filters=requested_filters,
        requested_executor_sectors=list(request.executor_sectors),
        requested_emitter_sectors=list(request.emitter_sectors),
        requested_ssa_numbers=list(request.ssa_numbers),
        mode=result.mode,
        source_xlsx=str(source_xlsx) if source_xlsx is not None else None,
        xlsx_path=str(result.export.xlsx_path),
        import_xlsx_path=(
            str(result.import_xlsx_path) if result.import_xlsx_path else None
        ),
        manifest_path=str(result.export.manifest_path),
        imported=bool(result.imported),
        normalized_rows=result.normalized_rows,
        rows_before_import=result.rows_before_import,
        rows_after_import=result.rows_after_import,
        staged_files=list(result.staged_files),
        staging_summary=result.staging_summary,
        ssa_examples=xlsx_summary["ssa_examples"],
        rows_by_executor_sector=xlsx_summary["rows_by_executor_sector"],
        rows_by_emitter_sector=xlsx_summary["rows_by_emitter_sector"],
        rows_by_source_file=xlsx_summary["rows_by_source_file"],
        ssa_examples_by_executor_sector=xlsx_summary[
            "ssa_examples_by_executor_sector"
        ],
        summary_error=xlsx_summary["summary_error"],
        warnings=_extract_manifest_warnings(result.export.manifest),
    )


def evaluate_pai_import_exit_status(
    result: PaiImportResult,
    *,
    fetch_only: bool,
) -> PaiImportExitStatus:
    if result.import_xlsx_path is None:
        return PaiImportExitStatus(
            6,
            "missing_import_xlsx",
            stderr=True,
        )
    if result.normalized_rows is None:
        return PaiImportExitStatus(
            6,
            "missing_normalized_rows",
            stderr=True,
        )
    if fetch_only:
        return PaiImportExitStatus(0)
    if not result.staged_files:
        return PaiImportExitStatus(
            2,
            "staging_failed",
            result.staging_summary,
            stderr=True,
        )
    if not result.imported:
        return PaiImportExitStatus(
            3,
            "import_failed",
            stderr=True,
        )
    if result.rows_after_import is None:
        return PaiImportExitStatus(
            5,
            "missing_imported_rows",
            stderr=True,
        )
    if result.normalized_rows > 0 and result.rows_after_import == 0:
        return PaiImportExitStatus(
            4,
            "non_empty_xlsx_empty_db",
            stderr=True,
        )
    if result.rows_after_import == 0:
        source = result.staged_files[0] if result.staged_files else "sem arquivo"
        return PaiImportExitStatus(
            0,
            "empty_import_success",
            source,
        )
    return PaiImportExitStatus(
        0,
        "import_success",
        result.staged_files[0],
    )


def _extract_manifest_warnings(manifest: object) -> list[str]:
    if not isinstance(manifest, dict):
        return []
    manifest_mapping = cast(Mapping[str, object], manifest)
    warnings = manifest_mapping.get("warnings")
    if isinstance(warnings, list):
        return [str(item) for item in warnings]
    warning = manifest_mapping.get("warning")
    if warning:
        return [str(warning)]
    return []
