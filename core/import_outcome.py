"""Typed outcome contract for the SSA import pipeline (S4a).

The importer historically returns a single bool whose meaning depends on
the path taken (updated, no-op, rejections-only, failure, cancellation).
This module gives every caller one structured result while the legacy
bool stays untouched as ``legacy_result``. Recording happens inside
``run_importer_logic``; the last outcome of the process is available via
``get_last_import_outcome``.
"""

from __future__ import annotations

import threading
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Optional


class ImportStatus(str, Enum):
    UPDATED = "updated"
    UPDATED_PARTIAL = "updated_partial"
    DERIVADAS_MATERIALIZED = "derivadas_materialized"
    NO_CHANGES = "no_changes"
    DETERMINISTIC_REJECTIONS_ONLY = "deterministic_rejections_only"
    CANDIDATE_INCOMPLETE = "candidate_incomplete"
    CANDIDATE_INVALID = "candidate_invalid"
    CANDIDATE_PROMOTION_FAILED = "candidate_promotion_failed"
    DERIVADAS_SYNC_ERROR = "derivadas_sync_error"
    NO_SUCCESS = "no_success"
    CANCELLED = "cancelled"
    BUSY = "import_busy"
    IMPORTER_ERROR = "importer_error"
    UNEXPECTED_EXCEPTION = "unexpected_exception"


_RAW_STATUS_MAP: Dict[str, ImportStatus] = {
    "cancelled_partial": ImportStatus.CANCELLED,
    "cancelled_preflight": ImportStatus.CANCELLED,
}

_PRIMARY_CHANGING_STATUSES = frozenset(
    {
        ImportStatus.UPDATED,
        ImportStatus.UPDATED_PARTIAL,
        ImportStatus.DERIVADAS_MATERIALIZED,
    }
)


@dataclass(frozen=True, slots=True)
class ImportOutcome:
    run_id: str
    status: ImportStatus
    reason: str
    legacy_result: bool
    primary_database_changed: bool
    primary_db_path: str
    working_db_path: str
    candidate_db_path: Optional[str]
    promoted_backup_path: Optional[str]
    total_candidates: int
    processed_file_count: int
    deterministic_failure_count: int
    blocking_error_count: int
    integrity_report: Dict[str, Any] = field(default_factory=dict)
    report_path: Optional[str] = None

    @property
    def reload_required(self) -> bool:
        return self.primary_database_changed


def resolve_import_status(raw_status: str) -> ImportStatus:
    normalized = str(raw_status or "").strip()
    mapped = _RAW_STATUS_MAP.get(normalized)
    if mapped is not None:
        return mapped
    try:
        return ImportStatus(normalized)
    except ValueError:
        return ImportStatus.IMPORTER_ERROR


def build_import_outcome(
    *,
    raw_status: str,
    legacy_result: bool,
    run_id: str,
    reason: str,
    primary_db_path: str,
    working_db_path: str,
    candidate_db_path: Optional[str] = None,
    promoted_backup_path: Optional[str] = None,
    total_candidates: int = 0,
    processed_file_count: int = 0,
    deterministic_failure_count: int = 0,
    blocking_error_count: int = 0,
    integrity_report: Optional[Dict[str, Any]] = None,
    report_path: Optional[str] = None,
) -> ImportOutcome:
    status = resolve_import_status(raw_status)
    return ImportOutcome(
        run_id=run_id,
        status=status,
        reason=str(reason or ""),
        legacy_result=bool(legacy_result),
        primary_database_changed=status in _PRIMARY_CHANGING_STATUSES,
        primary_db_path=str(primary_db_path),
        working_db_path=str(working_db_path),
        candidate_db_path=candidate_db_path,
        promoted_backup_path=promoted_backup_path,
        total_candidates=int(total_candidates),
        processed_file_count=int(processed_file_count),
        deterministic_failure_count=int(deterministic_failure_count),
        blocking_error_count=int(blocking_error_count),
        integrity_report=dict(integrity_report or {}),
        report_path=report_path,
    )


_LAST_OUTCOME_LOCK = threading.Lock()
_LAST_OUTCOME: Optional[ImportOutcome] = None


def record_import_outcome(outcome: ImportOutcome) -> None:
    global _LAST_OUTCOME
    with _LAST_OUTCOME_LOCK:
        _LAST_OUTCOME = outcome


def get_last_import_outcome() -> Optional[ImportOutcome]:
    with _LAST_OUTCOME_LOCK:
        return _LAST_OUTCOME
