"""Import run report payload and JSON writer."""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from utils.path_safety import PathSafetyError, ensure_path_is_allowed

project_root_path = Path(__file__).resolve().parents[1]
project_root = str(project_root_path)
logger = logging.getLogger(__name__)


def _write_import_run_report(payload: Dict[str, Any]) -> Optional[str]:
    """Grava resumo estruturado de uma execucao de importacao em JSON."""
    try:
        logs_dir = str(
            ensure_path_is_allowed(
                os.path.join(project_root, "logs"),
                purpose="import_report_logs_dir",
                base=project_root_path,
                must_exist=False,
                expect_directory=True,
            )
        )
        runtime_root = str(os.environ.get("SSA_RUNTIME_ROOT") or "").strip()
        if runtime_root:
            runtime_logs_dir = os.path.join(runtime_root, "logs")
            try:
                logs_dir = str(
                    ensure_path_is_allowed(
                        runtime_logs_dir,
                        purpose="import_report_logs_dir",
                        must_exist=False,
                        expect_directory=True,
                    )
                )
            except PathSafetyError as exc:
                logger.warning(
                    "Runtime logs dir rejeitado para relatorio de importacao: %s",
                    exc,
                )
        os.makedirs(logs_dir, exist_ok=True)
        run_id = str(
            payload.get("run_id") or datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        )
        report_path = os.path.join(logs_dir, f"import_run_{run_id}.json")
        with open(report_path, "w", encoding="utf-8") as fp:
            json.dump(payload, fp, ensure_ascii=False, indent=2, default=str)
        return report_path
    except (OSError, TypeError, ValueError) as exc:
        logger.warning("Falha ao gravar relatorio JSON de importacao: %s", exc)
        return None


def _build_import_run_payload(
    *,
    run_id: str,
    run_started_at: datetime,
    finished_at: datetime,
    result: bool,
    status: str,
    reason: str,
    force_import: bool,
    table_name: str,
    db_name: str,
    docs_dir: str,
    data_dir: str,
    primary_db_path: str,
    working_db_path: str,
    candidate_db_path: Optional[str],
    promoted_backup_path: Optional[str],
    cache_file: str,
    total_files: int,
    successfully_processed_files: List[str],
    critical_errors: List[tuple[str, str, str]],
    deterministic_failed_files: List[str],
    derivadas_sheet_files: List[str],
    db_only_derivadas_sync: bool,
    derivadas_sync_blocking_error: bool,
    sync_materialized: bool,
    files_to_process: List[str],
    ignored_legacy_excel_files: List[str],
    integrity_report: Dict[str, Any],
    file_reports: List[Dict[str, Any]],
    phase_durations: Dict[str, float],
) -> Dict[str, Any]:
    total_rows_extracted = 0
    total_rows_removed_invalid_identity = 0
    total_rows_ready_for_insert = 0
    total_rows_inserted = 0
    total_extraction_seconds = 0.0
    total_validation_seconds = 0.0
    total_insert_seconds = 0.0
    for entry in file_reports:
        counts = entry.get("counts") or {}
        durations = entry.get("durations") or {}
        total_rows_extracted += int(counts.get("rows_extracted", 0) or 0)
        total_rows_removed_invalid_identity += int(
            counts.get("rows_removed_invalid_identity", 0) or 0
        )
        total_rows_ready_for_insert += int(counts.get("rows_ready_for_insert", 0) or 0)
        total_rows_inserted += int(counts.get("rows_inserted", 0) or 0)
        total_extraction_seconds += float(durations.get("extraction_seconds", 0) or 0)
        total_validation_seconds += float(durations.get("validation_seconds", 0) or 0)
        total_insert_seconds += float(durations.get("insert_seconds", 0) or 0)
    normalized_phase_durations: Dict[str, float] = {}
    for key, value in phase_durations.items():
        try:
            normalized_phase_durations[key] = round(float(value), 3)
        except (TypeError, ValueError):
            continue
    return {
        "run_id": run_id,
        "started_at": run_started_at.isoformat(timespec="seconds"),
        "finished_at": finished_at.isoformat(timespec="seconds"),
        "duration_seconds": round((finished_at - run_started_at).total_seconds(), 3),
        "durations": {
            "sum_file_extraction_seconds": round(total_extraction_seconds, 3),
            "sum_file_validation_seconds": round(total_validation_seconds, 3),
            "sum_file_insert_seconds": round(total_insert_seconds, 3),
            **normalized_phase_durations,
        },
        "result": bool(result),
        "status": status,
        "reason": reason,
        "inputs": {
            "force_import": bool(force_import),
            "table_name": table_name,
            "db_name": db_name,
        },
        "paths": {
            "docs_dir": docs_dir,
            "data_dir": data_dir,
            "db_path": primary_db_path,
            "primary_db_path": primary_db_path,
            "working_db_path": working_db_path,
            "candidate_db_path": candidate_db_path,
            "promoted_backup_path": promoted_backup_path,
            "candidate_preserved": bool(
                candidate_db_path
                and os.path.exists(candidate_db_path)
                and candidate_db_path != primary_db_path
            ),
            "cache_file": cache_file,
        },
        "counts": {
            "total_candidates": int(total_files),
            "success_count": len(successfully_processed_files),
            "error_count": len(critical_errors),
            "deterministic_failure_count": len(deterministic_failed_files),
            "derivadas_sheet_count": len(derivadas_sheet_files),
            "db_only_derivadas_sync": bool(db_only_derivadas_sync),
            "derivadas_sync_blocking_error": bool(derivadas_sync_blocking_error),
            "sync_materialized": bool(sync_materialized),
            "ignored_legacy_excel_count": len(ignored_legacy_excel_files),
            "rows_extracted_total": total_rows_extracted,
            "rows_removed_invalid_identity_total": total_rows_removed_invalid_identity,
            "rows_ready_for_insert_total": total_rows_ready_for_insert,
            "rows_inserted_total": total_rows_inserted,
        },
        "files": {
            "candidates": [os.path.basename(p) for p in files_to_process],
            "success": [os.path.basename(p) for p in successfully_processed_files],
            "deterministic_failed": [
                os.path.basename(p) for p in deterministic_failed_files
            ],
            "derivadas_sheet_files": [
                os.path.basename(p) for p in derivadas_sheet_files
            ],
            "ignored_legacy_excel": [
                os.path.basename(p) for p in ignored_legacy_excel_files
            ],
        },
        "errors": [
            {
                "type": error_type,
                "file": os.path.basename(file_path),
                "message": message,
            }
            for error_type, file_path, message in critical_errors
        ],
        "integrity": {
            "is_valid": integrity_report.get("is_valid"),
            "issue_count": len(integrity_report.get("issues", [])),
            "warning_count": len(integrity_report.get("warnings", [])),
        },
        "file_reports": file_reports,
    }
