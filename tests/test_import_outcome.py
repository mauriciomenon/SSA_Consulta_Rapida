"""Contract tests for the typed import outcome (S4a).

run_importer_logic keeps returning the legacy bool unchanged; the same
finalize path now records an ImportOutcome retrievable via
get_last_import_outcome with status, primary_database_changed and
counts for every ending of the run.
"""

import os
import sys
from pathlib import Path

import pandas as pd
import pytest

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from core import app_logic  # noqa: E402
from core import import_outcome  # noqa: E402
from core.app_logic import run_importer_logic  # noqa: E402

WORK = Path("/tmp/ssa_test_import_outcome")


def make_xlsx(path: Path, numero: str) -> None:
    pd.DataFrame(
        {
            "numero_ssa": [numero],
            "descricao_ssa": [f"outcome {numero}"],
            "data_cadastro": ["2026-09-01 08:00:00"],
        }
    ).to_excel(path, index=False)


def benign_sync(*args, **kwargs):
    return {
        "sheet_stats": {},
        "sheet_files": [],
        "sheet_file_reports": [],
        "sheet_evidence": {},
        "db_stats": {"accepted_edges": 0},
        "merge_stats": {"merged_edges": 0},
        "consistency_scan": {"schema_ready": True, "is_consistent": True, "issue_counts": {}},
    }


def consistent_scan(*args, **kwargs):
    return {
        "schema_ready": True,
        "is_consistent": True,
        "issue_counts": {
            "missing_source_pairs": 0,
            "source_without_matrix_pairs": 0,
            "flag_mismatch_pairs": 0,
            "invalid_matrix_pairs": 0,
            "closure_self_rows": 0,
            "summary_missing_nodes": 0,
            "summary_extra_nodes": 0,
            "fingerprint_mismatch": 0,
        },
    }


@pytest.fixture()
def workspace(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(app_logic, "sync_derivadas", benign_sync)
    monkeypatch.setattr(app_logic, "scan_derivadas_consistency", consistent_scan)
    docs = tmp_path / "docs_entrada"
    data = tmp_path / "data"
    docs.mkdir()
    data.mkdir()
    return docs, data, tmp_path


def run(docs: Path, data: Path, tmp: Path, force: bool = False) -> bool:
    import_outcome.record_import_outcome  # ensure import
    return run_importer_logic(
        docs_dir=str(docs),
        data_dir=str(data),
        force_import=force,
        extra_allowed_roots=[str(tmp)],
    )


def test_status_mapping_for_known_raw_values():
    assert import_outcome.resolve_import_status("updated") is import_outcome.ImportStatus.UPDATED
    assert import_outcome.resolve_import_status("cancelled_partial") is import_outcome.ImportStatus.CANCELLED
    assert import_outcome.resolve_import_status("cancelled_preflight") is import_outcome.ImportStatus.CANCELLED
    assert import_outcome.resolve_import_status("candidate_invalid") is import_outcome.ImportStatus.CANDIDATE_INVALID
    assert import_outcome.resolve_import_status("whatever_new") is import_outcome.ImportStatus.IMPORTER_ERROR


def test_outcome_flags_reload_only_for_primary_changing_statuses():
    changed = import_outcome.build_import_outcome(
        raw_status="updated", legacy_result=True, run_id="r",
        reason="", primary_db_path="p", working_db_path="w",
    )
    assert changed.primary_database_changed is True
    assert changed.reload_required is True

    noop = import_outcome.build_import_outcome(
        raw_status="deterministic_rejections_only", legacy_result=True, run_id="r",
        reason="", primary_db_path="p", working_db_path="w",
    )
    assert noop.primary_database_changed is False
    assert noop.reload_required is False


def test_updated_run_records_outcome_and_keeps_bool(workspace):
    docs, data, tmp = workspace
    make_xlsx(docs / "a.xlsx", "202640001")
    result = run(docs, data, tmp)
    outcome = import_outcome.get_last_import_outcome()
    assert outcome is not None

    assert result is True
    assert outcome is not None
    assert outcome.status is import_outcome.ImportStatus.UPDATED
    assert outcome.legacy_result is True
    assert outcome.primary_database_changed is True
    assert outcome.processed_file_count == 1
    assert outcome.total_candidates == 1
    assert outcome.report_path


def test_rejections_only_run_records_outcome_true_bool(workspace):
    docs, data, tmp = workspace
    pd.DataFrame({"foo": ["bar"]}).to_excel(docs / "bad.xlsx", index=False)
    result = run(docs, data, tmp)
    outcome = import_outcome.get_last_import_outcome()
    assert outcome is not None

    assert result is True
    assert outcome is not None
    assert outcome.status is import_outcome.ImportStatus.DETERMINISTIC_REJECTIONS_ONLY
    assert outcome.primary_database_changed is False
    assert outcome.deterministic_failure_count >= 1


def test_no_changes_run_records_outcome(workspace):
    docs, data, tmp = workspace
    make_xlsx(docs / "a.xlsx", "202640001")
    assert run(docs, data, tmp) is True
    outcome_first = import_outcome.get_last_import_outcome()
    result = run(docs, data, tmp)
    outcome = import_outcome.get_last_import_outcome()
    assert outcome is not None

    assert result is False
    assert outcome is not outcome_first
    assert outcome.status is import_outcome.ImportStatus.NO_CHANGES
    assert outcome.legacy_result is False
    assert outcome.primary_database_changed is False
