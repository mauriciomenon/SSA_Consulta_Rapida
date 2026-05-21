"""Headless derivadas sync job used by the GUI controller."""

from __future__ import annotations

import json
import os
from typing import Any, Callable

DERIVADAS_SYNC_PHASE_DB = "db"
DERIVADAS_SYNC_PHASE_SHEETS = "sheets"


def execute_derivadas_sync_job(
    *,
    db_path: str,
    table_name: str,
    special_files: list[str],
    sync_derivadas_fn: Callable[..., dict[str, Any]],
    scan_derivadas_consistency_fn: Callable[..., dict[str, Any]],
    phase_callback: Callable[[str, dict[str, Any]], None] | None = None,
) -> dict[str, Any]:
    def _emit_phase(name: str, **payload: Any) -> None:
        if callable(phase_callback):
            phase_callback(name, payload)

    try:
        _emit_phase(DERIVADAS_SYNC_PHASE_DB)
        db_phase_report = sync_derivadas_fn(
            db_path=db_path,
            table_name=table_name,
            include_db_source=True,
            verify_only=False,
            actor="gui-derivadas-db-phase",
        )

        phase_reports = [db_phase_report]
        db_stats = db_phase_report.get("db_stats") or {}
        db_edges = int(db_stats.get("accepted_edges", 0) or 0)
        if special_files:
            _emit_phase(DERIVADAS_SYNC_PHASE_SHEETS, count=len(special_files))
            sheet_phase_report = sync_derivadas_fn(
                db_path=db_path,
                table_name=table_name,
                include_db_source=False,
                sheet_files=special_files,
                verify_only=False,
                actor="gui-derivadas-sheet-phase",
            )
            phase_reports.append(sheet_phase_report)
            _verify_special_sheet_coverage(sheet_phase_report, special_files)

        merged_edges = 0
        sheet_edges = 0
        for phase_report in phase_reports:
            merge_stats = phase_report.get("merge_stats") or {}
            sheet_stats = phase_report.get("sheet_stats") or {}
            merged_edges = max(
                merged_edges,
                int(merge_stats.get("merged_edges", 0) or 0),
            )
            sheet_edges += int(sheet_stats.get("accepted_edges", 0) or 0)
        consistency = scan_derivadas_consistency_fn(db_path=db_path)
        if not bool(consistency.get("schema_ready")) or not bool(
            consistency.get("is_consistent")
        ):
            issue_counts = consistency.get("issue_counts") or {}
            raise RuntimeError(
                "Derivadas inconsistente apos sync manual: "
                f"{json.dumps(issue_counts, ensure_ascii=True)}"
            )
        return {
            "ok": True,
            "db_edges": db_edges,
            "sheet_edges": sheet_edges,
            "merged_edges": merged_edges,
        }
    except Exception as exc:
        return {"ok": False, "error": repr(exc)}


def _verify_special_sheet_coverage(
    final_report: dict[str, Any], special_files: list[str]
) -> None:
    reported_files = _absolute_path_set(final_report.get("sheet_files") or [])
    expected_files = _absolute_path_set(special_files)
    missing_files = expected_files - reported_files
    if missing_files:
        raise RuntimeError(
            "Sync de planilhas especiais sem cobertura completa de arquivos "
            f"(esperado={len(expected_files)}, "
            f"recebido={len(reported_files)}, faltando={len(missing_files)})."
        )
    sheet_file_reports = final_report.get("sheet_file_reports") or []
    reports_by_file = {}
    for entry in sheet_file_reports:
        if not isinstance(entry, dict):
            continue
        current_file = str(entry.get("sheet_file") or "").strip()
        if current_file:
            reports_by_file[os.path.abspath(current_file)] = entry
    files_without_evidence = []
    for current_file in sorted(expected_files):
        current_entry = reports_by_file.get(current_file)
        if current_entry is None or not _has_sheet_parse_evidence(current_entry):
            files_without_evidence.append(os.path.basename(current_file))
    if files_without_evidence:
        raise RuntimeError(
            "Planilhas especiais sem evidencia individual: "
            + ", ".join(files_without_evidence)
        )


def _absolute_path_set(paths: list[Any]) -> set[str]:
    return {os.path.abspath(str(path)) for path in paths}


def _has_sheet_parse_evidence(entry: dict[str, Any]) -> bool:
    if not isinstance(entry, dict):
        return False
    raw_stats = entry.get("stats")
    stats = raw_stats if isinstance(raw_stats, dict) else {}
    has_flag = bool(entry.get("has_parse_evidence"))
    accepted = int(stats.get("accepted_edges", 0) or 0)
    special_layout = int(stats.get("special_layout_detected", 0) or 0)
    informational = int(stats.get("informational_rows_skipped", 0) or 0)
    return has_flag or accepted > 0 or special_layout > 0 or informational > 0
