#!/usr/bin/env python3
# ruff: noqa: E402
"""Fetch PAI data through scrap_report and optionally import the generated XLSX."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

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
    elif (
        (result.normalized_rows or 0) > 0
        and result.rows_after_import == 0
    ):
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
        _write_summary_json(_resolve_under_project(project_root, args.summary_json), result)
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


def _write_summary_json(path: Path, result) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "mode": result.mode,
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
    }
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


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
