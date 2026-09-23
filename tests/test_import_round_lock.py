"""Round lock contract tests (S4c, IMP-02).

The whole importer run now holds the primary writer lock, so a second
importer on the same primary (full rescan or diff) cannot commit inside
the candidate-build-to-promotion window: it waits the lock timeout and
returns BUSY with no side effects. Same-process reentrancy comes from
the filelock singleton (the inner per-connection locks reuse the same
instance).
"""

import os
import sqlite3
import sys
from pathlib import Path

import pandas as pd
import pytest
from filelock import FileLock

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from armazenamento.database_lock import _lock_path  # noqa: E402
from core import app_logic  # noqa: E402
from core import import_outcome  # noqa: E402
from core.app_logic import run_importer_logic  # noqa: E402


def make_xlsx(path: Path, numero: str) -> None:
    pd.DataFrame(
        {
            "numero_ssa": [numero],
            "descricao_ssa": [f"roundlock {numero}"],
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


def external_lock(primary_db: Path, timeout: float = 0.2):
    """Independent file-lock instance on the same lock file (cross-fd flock)."""
    return FileLock(
        str(_lock_path(str(primary_db))),
        timeout=timeout,
        mode=0o600,
        thread_local=True,
        is_singleton=False,
    )


@pytest.fixture()
def workspace(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(app_logic, "sync_derivadas", benign_sync)
    monkeypatch.setattr(app_logic, "scan_derivadas_consistency", consistent_scan)
    docs = tmp_path / "docs_entrada"
    data = tmp_path / "data"
    docs.mkdir()
    data.mkdir()
    make_xlsx(docs / "a.xlsx", "202660001")
    return docs, data, tmp_path


def run(docs: Path, data: Path, tmp: Path, force: bool = False) -> bool:
    return run_importer_logic(
        docs_dir=str(docs),
        data_dir=str(data),
        force_import=force,
        extra_allowed_roots=[str(tmp)],
    )


def test_busy_run_has_no_side_effects(workspace):
    docs, data, tmp = workspace
    primary = data / "ssas.db"
    assert run(docs, data, tmp) is True  # seed (also proves reentrancy works)
    seeded = primary.read_bytes()

    with external_lock(primary):
        result = run(docs, data, tmp, force=True)

    outcome = import_outcome.get_last_import_outcome()
    assert outcome is not None
    assert result is False
    assert outcome.status is import_outcome.ImportStatus.BUSY
    assert outcome.reason == "primary_locked_by_another_run"
    assert not list(data.glob("ssas.db.full_rescan_candidate_*"))
    assert not list(data.glob("ssas.db.full_rescan_backup_*"))
    assert primary.read_bytes() == seeded


def test_lock_released_after_successful_run(workspace):
    docs, data, tmp = workspace
    primary = data / "ssas.db"
    assert run(docs, data, tmp) is True

    with external_lock(primary, timeout=2.0):
        pass  # acquires immediately: the round lock was released

    with sqlite3.connect(str(primary)) as conn:
        count = conn.execute(
            "SELECT COUNT(*) FROM ssa_table WHERE numero_ssa='202660001'"
        ).fetchone()[0]
    assert count == 1


def test_second_run_after_release_succeeds(workspace):
    docs, data, tmp = workspace
    primary = data / "ssas.db"
    assert run(docs, data, tmp) is True

    with external_lock(primary, timeout=2.0):
        pass  # acquires immediately: the round lock was released after run 1

    result = run(docs, data, tmp, force=True)
    outcome = import_outcome.get_last_import_outcome()
    assert outcome is not None
    assert result is True
    assert outcome.status is import_outcome.ImportStatus.UPDATED
