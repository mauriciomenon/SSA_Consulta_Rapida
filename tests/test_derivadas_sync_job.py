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


def test_derivadas_sync_job_reports_consistency_scan_failure(
    tmp_path: Path,
) -> None:
    def _sync_derivadas(**kwargs: Any) -> dict[str, Any]:
        if kwargs.get("include_db_source"):
            return {
                "merge_stats": {"merged_edges": 1},
                "db_stats": {"accepted_edges": 1},
                "sheet_stats": {"accepted_edges": 0},
            }
        raise AssertionError("sheet phase should not run without special files")

    def _scan_consistency(**_kwargs: Any) -> dict[str, Any]:
        raise OSError("database unavailable")

    result = execute_derivadas_sync_job(
        db_path=str(tmp_path / "ssas.db"),
        table_name="ssa_table",
        special_files=[],
        sync_derivadas_fn=_sync_derivadas,
        scan_derivadas_consistency_fn=_scan_consistency,
    )

    assert result["ok"] is False
    assert "Falha ao verificar consistencia de derivadas" in str(result["error"])
    assert "database unavailable" in str(result["error"])


def test_derivadas_sync_job_reports_schema_not_ready_separately(
    tmp_path: Path,
) -> None:
    result = execute_derivadas_sync_job(
        db_path=str(tmp_path / "ssas.db"),
        table_name="ssa_table",
        special_files=[],
        sync_derivadas_fn=lambda **_kwargs: {
            "merge_stats": {"merged_edges": 1},
            "db_stats": {"accepted_edges": 1},
            "sheet_stats": {"accepted_edges": 0},
        },
        scan_derivadas_consistency_fn=lambda **_kwargs: {
            "schema_ready": False,
            "is_consistent": True,
            "issue_counts": {"missing_table": 1},
        },
    )

    assert result["ok"] is False
    assert "Schema de derivadas indisponivel" in str(result["error"])
    assert "missing_table" in str(result["error"])
