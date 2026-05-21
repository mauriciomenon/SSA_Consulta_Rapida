from __future__ import annotations

from pathlib import Path
from typing import Any

from gui.ssa.derivadas_sync_job import execute_derivadas_sync_job


def test_derivadas_sync_job_rejects_extra_reported_sheet_files(
    tmp_path: Path,
) -> None:
    expected_sheet = tmp_path / "expected.xlsx"
    extra_sheet = tmp_path / "extra.xlsx"

    def _sync_derivadas(**kwargs: Any) -> dict[str, Any]:
        if kwargs.get("include_db_source"):
            return {
                "merge_stats": {"merged_edges": 0},
                "db_stats": {"accepted_edges": 2},
                "sheet_stats": {"accepted_edges": 0},
            }
        return {
            "sheet_files": [str(expected_sheet), str(extra_sheet)],
            "sheet_file_reports": [
                {
                    "sheet_file": str(expected_sheet),
                    "has_parse_evidence": True,
                    "stats": {"accepted_edges": 1},
                },
                {
                    "sheet_file": str(extra_sheet),
                    "has_parse_evidence": True,
                    "stats": {"accepted_edges": 1},
                },
            ],
            "merge_stats": {"merged_edges": 0},
            "db_stats": {"accepted_edges": 2},
            "sheet_stats": {"accepted_edges": 2},
        }

    result = execute_derivadas_sync_job(
        db_path=str(tmp_path / "ssas.db"),
        table_name="ssa_table",
        special_files=[str(expected_sheet)],
        sync_derivadas_fn=_sync_derivadas,
        scan_derivadas_consistency_fn=lambda **_kwargs: {
            "schema_ready": True,
            "is_consistent": True,
            "issue_counts": {},
        },
    )

    assert result["ok"] is False
    assert "arquivos nao solicitados" in str(result["error"])
    assert "extra.xlsx" in str(result["error"])
