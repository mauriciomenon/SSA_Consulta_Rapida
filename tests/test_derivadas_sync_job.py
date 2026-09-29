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


def test_derivadas_sync_job_merged_edges_uses_materialized_union(
    tmp_path: Path,
) -> None:
    """Aresta presente nas duas fontes conta uma vez: o total exibido
    deve ser a matriz materializada (active_edges), nao a soma por fase."""
    special_sheet = tmp_path / "SSAs Derivadas e Relacionadas_13-02-2026_0100PM.xlsx"

    def _sync_derivadas(**kwargs: Any) -> dict[str, Any]:
        if kwargs.get("include_db_source"):
            return {
                "merge_stats": {"merged_edges": 5},
                "active_edges": 5,
                "db_stats": {"accepted_edges": 5},
                "sheet_stats": {"accepted_edges": 0},
            }
        return {
            "sheet_files": [str(special_sheet)],
            "sheet_file_reports": [
                {
                    "sheet_file": str(special_sheet),
                    "has_parse_evidence": True,
                    "stats": {"accepted_edges": 3},
                }
            ],
            "merge_stats": {"merged_edges": 3},
            # 5 do DB + 3 da planilha, com 2 arestas sobrepostas -> 6 unicas
            "active_edges": 6,
            "db_stats": {"accepted_edges": 5},
            "sheet_stats": {"accepted_edges": 3},
        }

    result = execute_derivadas_sync_job(
        db_path=str(tmp_path / "ssas.db"),
        table_name="ssa_table",
        special_files=[str(special_sheet)],
        sync_derivadas_fn=_sync_derivadas,
        scan_derivadas_consistency_fn=lambda **_kwargs: {
            "schema_ready": True,
            "is_consistent": True,
            "issue_counts": {},
        },
    )

    assert result["ok"] is True
    assert result["merged_edges"] == 6


def test_derivadas_sync_job_forwards_extra_allowed_roots(
    tmp_path: Path,
) -> None:
    captured: list[dict[str, Any]] = []
    roots = [str(tmp_path)]
    sheet = str(tmp_path / "derivadas.xlsx")

    def _sync_derivadas(**kwargs: Any) -> dict[str, Any]:
        captured.append(kwargs)
        return {
            "merge_stats": {"merged_edges": 1},
            "db_stats": {"accepted_edges": 1},
            "sheet_stats": {"accepted_edges": 1},
            "sheet_files": [sheet] if not kwargs["include_db_source"] else [],
            "sheet_file_reports": [
                {"sheet_file": sheet, "has_parse_evidence": True}
            ],
        }

    def _scan_consistency(**kwargs: Any) -> dict[str, Any]:
        captured.append(kwargs)
        return {
            "schema_ready": True,
            "is_consistent": True,
            "issue_counts": {},
        }

    result = execute_derivadas_sync_job(
        db_path=str(tmp_path / "ssas.db"),
        table_name="ssa_table",
        special_files=[sheet],
        sync_derivadas_fn=_sync_derivadas,
        scan_derivadas_consistency_fn=_scan_consistency,
        extra_allowed_roots=roots,
    )

    assert result["ok"] is True
    assert len(captured) == 3
    assert captured[0]["include_db_source"] is True
    assert captured[1]["include_db_source"] is False
    assert captured[1]["sheet_files"] == [sheet]
    assert all(
        list(call.get("extra_allowed_roots") or []) == roots for call in captured
    )
