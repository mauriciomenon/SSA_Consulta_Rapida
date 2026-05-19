#!/usr/bin/env python3
# ruff: noqa: E402
"""Fetch PAI data through scrap_report and optionally import the generated XLSX."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any, Mapping, cast

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.pai_import_service import (
    fetch_and_import_pai_xlsx,
    import_prepared_pai_xlsx,
    preview_existing_pai_xlsx,
)
from core.pai_scrap_report_provider import (
    PAI_DEFAULT_API_TIMEOUT_SECONDS,
    PAI_DEFAULT_COMMAND_TIMEOUT_SECONDS,
    PAI_DEFAULT_LIMIT,
    PAI_DEFAULT_NUMBER_OF_YEARS,
    PAI_DEFAULT_PROFILE,
    PAI_RUNNER_UV,
    PAI_ALLOW_SIBLING_ROOT_ENV,
    PAI_SCRAP_REPORT_ROOT_ENV,
    PAI_SCRAP_REPORT_RUNNER_ENV,
    PaiScrapReportRequest,
)

SUMMARY_SSA_EXAMPLE_LIMIT = 20
SUMMARY_GROUP_EXAMPLE_LIMIT = 10


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Gera XLSX PAI via scrap_report e importa no banco SSA.",
    )
    parser.add_argument("--project-root", default=str(PROJECT_ROOT))
    parser.add_argument("--scrap-report-root", default=None)
    parser.add_argument("--output-dir", default=None)
    parser.add_argument(
        "--source-xlsx",
        default=None,
        help="valida/importa XLS/XLSX PAI ja existente, sem chamar API",
    )
    parser.add_argument("--profile", default=PAI_DEFAULT_PROFILE)
    parser.add_argument("--executor-sector", action="append", default=[])
    parser.add_argument("--emitter-sector", action="append", default=[])
    parser.add_argument("--ssa-number", action="append", default=[])
    parser.add_argument("--number-of-years", type=int, default=PAI_DEFAULT_NUMBER_OF_YEARS)
    parser.add_argument("--limit", type=int, default=PAI_DEFAULT_LIMIT)
    parser.add_argument("--ca-file", default=None)
    parser.add_argument("--include-details", action="store_true")
    parser.add_argument("--cleanup-manifest", action="store_true")
    parser.add_argument("--api-timeout-seconds", type=float, default=PAI_DEFAULT_API_TIMEOUT_SECONDS)
    parser.add_argument(
        "--command-timeout-seconds",
        type=float,
        default=PAI_DEFAULT_COMMAND_TIMEOUT_SECONDS,
    )
    parser.add_argument("--docs-dir", default="docs_entrada")
    parser.add_argument("--db-path", default="data/ssas.db")
    parser.add_argument("--summary-json", default=None)
    parser.add_argument(
        "--fetch-only",
        action="store_true",
        help="Gera XLSX/manifest sem importar no banco.",
    )
    return parser


def run(args: argparse.Namespace) -> int:
    project_root = Path(args.project_root).expanduser().resolve(strict=False)
    request = PaiScrapReportRequest(
        project_root=project_root,
        output_dir=_optional_path(args.output_dir),
        scrap_report_root=_optional_path(
            args.scrap_report_root or os.environ.get(PAI_SCRAP_REPORT_ROOT_ENV)
        ),
        allow_sibling_scrap_report=_env_truthy(PAI_ALLOW_SIBLING_ROOT_ENV),
        runner=str(os.environ.get(PAI_SCRAP_REPORT_RUNNER_ENV, PAI_RUNNER_UV)),
        profile=str(args.profile),
        executor_sectors=tuple(args.executor_sector),
        emitter_sectors=tuple(args.emitter_sector),
        ssa_numbers=tuple(args.ssa_number),
        number_of_years=int(args.number_of_years),
        limit=int(args.limit),
        ca_file=_optional_path(args.ca_file),
        include_details=bool(args.include_details),
        api_timeout_seconds=float(args.api_timeout_seconds),
        command_timeout_seconds=float(args.command_timeout_seconds),
    )
    docs_dir = _resolve_under_project(project_root, args.docs_dir)
    db_path = _resolve_under_project(project_root, args.db_path)
    source_xlsx = _optional_path(args.source_xlsx)
    if source_xlsx is not None:
        preview = preview_existing_pai_xlsx(request, source_xlsx, docs_dir=docs_dir)
        if args.fetch_only:
            result = _preview_only_result(preview)
        else:
            result = import_prepared_pai_xlsx(
                request,
                preview,
                docs_dir=docs_dir,
                db_path=db_path,
            )
    else:
        result = fetch_and_import_pai_xlsx(
            request,
            docs_dir=docs_dir,
            db_path=db_path,
            fetch_only=bool(args.fetch_only),
        )
    print(f"XLSX PAI: {result.export.xlsx_path}")
    if result.import_xlsx_path is not None:
        print(f"XLSX SSA importacao: {result.import_xlsx_path}")
    print(f"Manifest PAI: {result.export.manifest_path}")
    if result.normalized_rows is not None:
        print(f"Linhas normalizadas: {result.normalized_rows}")
    if result.rows_before_import is not None:
        print(f"Linhas antes da importacao: {result.rows_before_import}")
    if result.rows_after_import is not None:
        print(f"Linhas depois da importacao: {result.rows_after_import}")
    if args.fetch_only:
        exit_code = 0
    elif not result.staged_files:
        print(f"Falha no staging PAI: {result.staging_summary}", file=sys.stderr)
        exit_code = 2
    elif not result.imported:
        print("Falha ao importar XLSX PAI no banco.", file=sys.stderr)
        exit_code = 3
    elif result.rows_after_import is None:
        print("Falha ao verificar linhas importadas PAI.", file=sys.stderr)
        exit_code = 5
    elif result.normalized_rows is None:
        print("Falha ao verificar linhas normalizadas PAI.", file=sys.stderr)
        exit_code = 6
    elif result.normalized_rows > 0 and result.rows_after_import == 0:
        print(
            "Falha ao importar XLSX PAI: XLSX tinha dados, mas banco ficou sem linhas.",
            file=sys.stderr,
        )
        exit_code = 4
    elif result.rows_after_import == 0:
        print("Importacao PAI concluida sem registros.")
        exit_code = 0
    else:
        print(f"Importacao PAI concluida: {result.staged_files[0]}")
        exit_code = 0
    if exit_code == 0 and args.cleanup_manifest:
        result.export.manifest_path.unlink(missing_ok=True)
        print("Manifest PAI removido.")
    if args.summary_json:
        _write_summary_json(
            _resolve_under_project(project_root, args.summary_json),
            result,
            request=request,
            source_xlsx=source_xlsx,
        )
    return exit_code


def _preview_only_result(preview):
    from core.import_staging import empty_external_staging_summary
    from core.pai_import_service import PaiImportResult

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
    )


def _write_summary_json(
    path: Path,
    result,
    *,
    request: PaiScrapReportRequest,
    source_xlsx: Path | None,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    xlsx_summary = _read_xlsx_summary(result.import_xlsx_path)
    requested_filters = {
        "executor_sectors": list(request.executor_sectors),
        "emitter_sectors": list(request.emitter_sectors),
        "ssa_numbers": list(request.ssa_numbers),
        "number_of_years": request.number_of_years,
        "limit": request.limit,
    }
    payload = {
        "source_kind": "source-xlsx" if source_xlsx is not None else "api",
        "requested_filters": requested_filters,
        "requested_executor_sectors": requested_filters["executor_sectors"],
        "requested_emitter_sectors": requested_filters["emitter_sectors"],
        "requested_ssa_numbers": requested_filters["ssa_numbers"],
        "mode": result.mode,
        "source_xlsx": str(source_xlsx) if source_xlsx is not None else None,
        "xlsx_path": str(result.export.xlsx_path),
        "import_xlsx_path": (
            str(result.import_xlsx_path) if result.import_xlsx_path else None
        ),
        "manifest_path": str(result.export.manifest_path),
        "imported": bool(result.imported),
        "normalized_rows": result.normalized_rows,
        "rows_before_import": result.rows_before_import,
        "rows_after_import": result.rows_after_import,
        "staged_files": list(result.staged_files),
        "staging_summary": result.staging_summary,
        "ssa_examples": xlsx_summary["ssa_examples"],
        "rows_by_executor_sector": xlsx_summary["rows_by_executor_sector"],
        "rows_by_emitter_sector": xlsx_summary["rows_by_emitter_sector"],
        "rows_by_source_file": xlsx_summary["rows_by_source_file"],
        "ssa_examples_by_executor_sector": xlsx_summary[
            "ssa_examples_by_executor_sector"
        ],
        "warnings": _extract_manifest_warnings(result.export.manifest),
    }
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _read_xlsx_summary(path: Path | None) -> dict[str, object]:
    empty: dict[str, object] = {
        "ssa_examples": [],
        "rows_by_executor_sector": {},
        "rows_by_emitter_sector": {},
        "rows_by_source_file": {},
        "ssa_examples_by_executor_sector": {},
    }
    if path is None or not path.is_file():
        return empty
    try:
        frame = pd.read_excel(path, dtype=str)
    except (OSError, ValueError) as exc:
        return {**empty, "ssa_examples": [f"summary_read_error:{type(exc).__name__}"]}
    number_column = _first_existing_column(
        frame.columns,
        ("numero_ssa", "Numero da SSA", "ssa_number", "SSA"),
    )
    executor_column = _first_existing_column(
        frame.columns,
        ("setor_executor", "executor_sector", "Setor Executor"),
    )
    emitter_column = _first_existing_column(
        frame.columns,
        ("setor_emissor", "emitter_sector", "Setor Emissor"),
    )
    source_file_column = _first_existing_column(
        frame.columns,
        ("arquivo_origem", "source_file", "Arquivo Origem"),
    )
    if not any((number_column, executor_column, emitter_column, source_file_column)):
        return empty
    return _summarize_xlsx_frame(
        frame,
        number_column=number_column,
        executor_column=executor_column,
        emitter_column=emitter_column,
        source_file_column=source_file_column,
    )


def _summarize_xlsx_frame(
    frame: pd.DataFrame,
    *,
    number_column: str | None,
    executor_column: str | None,
    emitter_column: str | None,
    source_file_column: str | None,
) -> dict[str, object]:
    column_index = {str(column): index for index, column in enumerate(frame.columns)}
    number_index = _column_index(column_index, number_column)
    executor_index = _column_index(column_index, executor_column)
    emitter_index = _column_index(column_index, emitter_column)
    source_file_index = _column_index(column_index, source_file_column)
    ssa_examples: list[str] = []
    rows_by_executor_sector: dict[str, int] = {}
    rows_by_emitter_sector: dict[str, int] = {}
    rows_by_source_file: dict[str, int] = {}
    ssa_examples_by_executor_sector: dict[str, list[str]] = {}
    for row in frame.itertuples(index=False, name=None):
        number = _clean_row_value(row, number_index)
        executor = _clean_row_value(row, executor_index)
        emitter = _clean_row_value(row, emitter_index)
        source_file = _clean_row_value(row, source_file_index)
        if number and len(ssa_examples) < SUMMARY_SSA_EXAMPLE_LIMIT:
            ssa_examples.append(number)
        _increment_count(rows_by_executor_sector, executor)
        _increment_count(rows_by_emitter_sector, emitter)
        _increment_count(rows_by_source_file, source_file)
        if executor and number:
            bucket = ssa_examples_by_executor_sector.setdefault(executor, [])
            if len(bucket) < SUMMARY_GROUP_EXAMPLE_LIMIT:
                bucket.append(number)
    return {
        "ssa_examples": ssa_examples,
        "rows_by_executor_sector": rows_by_executor_sector,
        "rows_by_emitter_sector": rows_by_emitter_sector,
        "rows_by_source_file": rows_by_source_file,
        "ssa_examples_by_executor_sector": ssa_examples_by_executor_sector,
    }


def _column_index(column_index: dict[str, int], column: str | None) -> int | None:
    if column is None:
        return None
    return column_index.get(column)


def _clean_row_value(row: tuple[object, ...], index: int | None) -> str:
    if index is None:
        return ""
    value = row[index]
    if pd.isna(value):
        return ""
    return str(value).strip()


def _increment_count(target: dict[str, int], value: str) -> None:
    if value:
        target[value] = target.get(value, 0) + 1


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


def _first_existing_column(columns: Any, candidates: tuple[str, ...]) -> str | None:
    existing = {str(column).casefold(): str(column) for column in columns}
    for candidate in candidates:
        found = existing.get(candidate.casefold())
        if found is not None:
            return found
    return None


def _optional_path(raw_path: str | None) -> Path | None:
    if not raw_path:
        return None
    return Path(raw_path).expanduser()


def _env_truthy(name: str) -> bool:
    return str(os.environ.get(name, "")).strip().casefold() in {"1", "true", "yes", "on"}


def _resolve_under_project(project_root: Path, value: str | Path) -> Path:
    path = Path(value).expanduser()
    if path.is_absolute():
        return path
    return project_root / path


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    return run(parser.parse_args(argv))


if __name__ == "__main__":
    raise SystemExit(main())
