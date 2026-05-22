"""Tests for database maintenance report rendering and orchestration."""

from __future__ import annotations

from pathlib import Path
from utils.db_maintenance import DatabaseAnalyzer, DatabaseMaintenanceReportService
from utils.db_maintenance_report import render_database_analysis_report


def test_database_analysis_report_renderer_keeps_existing_markdown_contract():
    content = render_database_analysis_report(
        db_path="data/ssas.db",
        backup_path="data/backups/ssas_backup.db",
        structure={
            "total_columns": 2,
            "column_counts": {"numero_ssa": 2, "legacy_numero": 1},
            "duplicated_groups": {
                "numero_ssa": [
                    {
                        "name": "numero_ssa",
                        "type": "TEXT",
                        "count": 2,
                        "is_legacy": False,
                    },
                    {
                        "name": "legacy_numero",
                        "type": "TEXT",
                        "count": 1,
                        "is_legacy": True,
                    },
                ]
            },
        },
        sanity={
            "total_records": 2,
            "summary": {
                "missing_numero_ssa": 1,
                "duplicate_numbers": 0,
            },
        },
    )

    assert "**Banco Analisado:** data/ssas.db" in content
    assert "**Backup Criado:** data/backups/ssas_backup.db" in content
    assert "**Total de Registros:** 2" in content
    assert "#### Numero Ssa" in content
    assert "| legacy_numero | TEXT | 1 | WARN Legado (com dados) |" in content
    assert "Corrigir 1 SSAs sem" in content


def test_database_report_service_writes_rendered_report(tmp_path, monkeypatch):
    output_file = tmp_path / "reports" / "database_analysis_report.md"
    analyzer = DatabaseAnalyzer("data/ssas.db")
    monkeypatch.setattr(analyzer, "create_backup", lambda: "data/backups/ssas_backup.db")
    monkeypatch.setattr(
        analyzer,
        "analyze_table_structure",
        lambda: {
            "total_columns": 1,
            "column_counts": {"numero_ssa": 1},
            "duplicated_groups": {},
        },
    )
    monkeypatch.setattr(
        analyzer,
        "perform_sanity_check",
        lambda: {
            "total_records": 1,
            "summary": {
                "missing_numero_ssa": 0,
                "duplicate_numbers": 0,
            },
        },
    )
    service = DatabaseMaintenanceReportService(analyzer)

    result = service.generate_report(output_file=str(output_file))

    assert result == str(output_file)
    content = Path(result).read_text(encoding="utf-8")
    assert "**Banco Analisado:** data/ssas.db" in content
    assert "**Backup Criado:** data/backups/ssas_backup.db" in content
    assert "**Total de Registros:** 1" in content
