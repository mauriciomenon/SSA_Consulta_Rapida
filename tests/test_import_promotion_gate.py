"""Promotion gate contract tests (S4b, matrix from the stabilization plan).

Regression for IMP-01: a full-rescan candidate used to be promoted when at
least one file succeeded, even with non-deterministic (blocking) errors
from other files - the primary lost previously imported rows with
result=True. The gate now keeps the primary intact and preserves the
candidate whenever a blocking error exists.
"""

import os
import sqlite3
import sys
from pathlib import Path

import pandas as pd
import pytest

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from core import app_logic  # noqa: E402
from core import import_outcome  # noqa: E402
from core.app_logic import FileProcessAction  # noqa: E402
from core.app_logic import run_importer_logic  # noqa: E402


def make_xlsx(path: Path, numero: str) -> None:
    pd.DataFrame(
        {
            "numero_ssa": [numero],
            "descricao_ssa": [f"gate {numero}"],
            "data_cadastro": ["2026-09-01 08:00:00"],
        }
    ).to_excel(path, index=False)


def ssas(db_path: Path) -> list[str]:
    with sqlite3.connect(str(db_path)) as conn:
        return [
            r[0]
            for r in conn.execute(
                "SELECT numero_ssa FROM ssa_table ORDER BY numero_ssa"
            )
        ]


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


def run(
    docs: Path,
    data: Path,
    tmp: Path,
    *,
    force: bool = False,
    fail_suffix: str | None = None,
):
    original_step = app_logic._process_regular_file_step

    def patched_step(*, file_path, **kwargs):
        if fail_suffix and str(file_path).endswith(fail_suffix):
            kwargs["critical_errors"].append(
                ("unexpected", str(file_path), "simulated transient failure")
            )
            kwargs["file_reports"].append(
                {
                    "file": os.path.basename(str(file_path)),
                    "status": "unexpected_error",
                    "error": "simulated transient failure",
                }
            )
            return FileProcessAction.CONTINUE
        return original_step(file_path=file_path, **kwargs)

    if fail_suffix:
        app_logic._process_regular_file_step = patched_step
    try:
        result = run_importer_logic(
            docs_dir=str(docs),
            data_dir=str(data),
            force_import=force,
            extra_allowed_roots=[str(tmp)],
        )
    finally:
        app_logic._process_regular_file_step = original_step
    return result


def test_matrix_success_promotes(workspace):
    docs, data, tmp = workspace
    make_xlsx(docs / "a.xlsx", "202650001")
    result = run(docs, data, tmp, force=True)
    outcome = import_outcome.get_last_import_outcome()
    assert outcome is not None

    assert result is True
    assert outcome.status is import_outcome.ImportStatus.UPDATED
    assert ssas(data / "ssas.db") == ["202650001"]


def test_matrix_success_with_deterministic_rejection_promotes(workspace):
    docs, data, tmp = workspace
    make_xlsx(docs / "a.xlsx", "202650001")
    pd.DataFrame({"foo": ["bar"]}).to_excel(docs / "det.xlsx", index=False)
    result = run(docs, data, tmp, force=True)
    outcome = import_outcome.get_last_import_outcome()
    assert outcome is not None

    assert result is True
    assert outcome.status is import_outcome.ImportStatus.UPDATED
    assert ssas(data / "ssas.db") == ["202650001"]


def test_matrix_deterministic_only_keeps_rejections_only(workspace):
    docs, data, tmp = workspace
    pd.DataFrame({"foo": ["bar"]}).to_excel(docs / "det.xlsx", index=False)
    result = run(docs, data, tmp, force=True)
    outcome = import_outcome.get_last_import_outcome()
    assert outcome is not None

    # Rejeicao deterministica nao atualiza o banco: result=False no contrato.
    assert result is False
    assert outcome.status is import_outcome.ImportStatus.DETERMINISTIC_REJECTIONS_ONLY
    assert not (data / "ssas.db").exists() or not ssas(data / "ssas.db")


def test_matrix_blocking_error_preserves_primary_and_candidate(workspace):
    docs, data, tmp = workspace
    make_xlsx(docs / "a.xlsx", "202650001")
    make_xlsx(docs / "b.xlsx", "202650002")
    assert run(docs, data, tmp, force=False) is True
    seeded = ssas(data / "ssas.db")
    assert seeded == ["202650001", "202650002"]

    result = run(docs, data, tmp, force=True, fail_suffix="b.xlsx")
    outcome = import_outcome.get_last_import_outcome()
    assert outcome is not None
    final = ssas(data / "ssas.db")
    candidates = list(data.glob("ssas.db.full_rescan_candidate_*"))
    backups = list(data.glob("ssas.db.full_rescan_backup_*"))

    assert result is False
    assert outcome.status is import_outcome.ImportStatus.CANDIDATE_INCOMPLETE
    assert outcome.reason == "blocking_errors_present"
    assert final == seeded
    assert candidates, "candidate must be preserved for evidence"
    assert not backups, "primary must not be rotated when blocked"
