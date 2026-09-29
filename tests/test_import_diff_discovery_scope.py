"""Diff discovery scope contract tests (S4e, IMP-07).

The *_in_full_rescan settings (include_processadas, ignore_nosurvivor)
used to govern discovery in both modes. The diff mode now keeps its
differential contract: it scans the root without processadas/. The
scanner never enters nosurvivor/ in either mode. Full rescan retains
the configured processadas/ discovery policy.
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
from core.app_logic import run_importer_logic  # noqa: E402


def make_xlsx(path: Path, numero: str) -> None:
    pd.DataFrame(
        {
            "numero_ssa": [numero],
            "descricao_ssa": [f"s4e {numero}"],
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


def run(docs: Path, data: Path, tmp: Path, force: bool = False) -> bool:
    return run_importer_logic(
        docs_dir=str(docs),
        data_dir=str(data),
        force_import=force,
        extra_allowed_roots=[str(tmp)],
    )


def test_diff_does_not_import_from_processadas(workspace):
    """IMP-07 regression: diff mode must not scan processadas/."""
    docs, data, tmp = workspace
    make_xlsx(docs / "root.xlsx", "202670001")
    assert run(docs, data, tmp) is True  # seed via diff
    assert ssas(data / "ssas.db") == ["202670001"]

    processadas = docs / "processadas"
    processadas.mkdir()
    make_xlsx(processadas / "from_processadas.xlsx", "202670002")

    run(docs, data, tmp)  # diff again
    final = ssas(data / "ssas.db")

    assert "202670002" not in final, (
        "diff mode must not import files that only exist under processadas/"
    )


def test_full_rescan_still_imports_from_processadas(workspace):
    """Full rescan preserves include_processadas behavior."""
    docs, data, tmp = workspace
    make_xlsx(docs / "root.xlsx", "202670001")
    processadas = docs / "processadas"
    processadas.mkdir()
    make_xlsx(processadas / "from_processadas.xlsx", "202670002")

    run(docs, data, tmp, force=True)
    final = ssas(data / "ssas.db")

    assert "202670002" in final, (
        "full rescan must continue importing from processadas/ "
        "(include_processadas_in_full_rescan=true)"
    )


def test_nosurvivor_is_outside_scan_path(workspace):
    """nosurvivor/ is outside the scan path (root + processadas only).

    The scanner does not walk nosurvivor/ in any mode; this documents
    the contract so a future recursive walk that starts including
    nosurvivor/ in diff mode gets flagged.
    """
    docs, data, tmp = workspace
    make_xlsx(docs / "root.xlsx", "202670001")
    nosurvivor = docs / "nosurvivor"
    nosurvivor.mkdir()
    make_xlsx(nosurvivor / "from_nosurvivor.xlsx", "202670003")

    run(docs, data, tmp)  # diff
    final = ssas(data / "ssas.db")

    assert "202670003" not in final, (
        "nosurvivor/ is outside the scan path; if this changes, the diff "
        "discovery contract needs explicit review"
    )
