from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from core.pai_import_report import build_pai_import_summary_payload
from core.pai_import_service import PaiImportResult
from core.pai_scrap_report_provider import PaiScrapReportExport, PaiScrapReportRequest
from scripts import import_pai_api_xlsx


def test_cli_source_xlsx_fetch_only_writes_summary(tmp_path: Path) -> None:
    source = tmp_path / "pai_cli.xlsx"
    summary = tmp_path / "summary.json"
    pd.DataFrame(
        {
            "ssa_number": [202600003],
            "description": ["CLI PAI"],
            "issue_datetime": ["2026-01-09T13:56:00Z"],
            "executor_sector": ["IEE3"],
            "emitter_sector": ["MEL4"],
        }
    ).to_excel(source, index=False)

    exit_code = import_pai_api_xlsx.main(
        [
            "--project-root",
            str(tmp_path),
            "--source-xlsx",
            str(source),
            "--docs-dir",
            str(tmp_path / "docs"),
            "--db-path",
            str(tmp_path / "ssas.db"),
            "--fetch-only",
            "--summary-json",
            str(summary),
        ]
    )

    assert exit_code == 0
    payload = json.loads(summary.read_text(encoding="utf-8"))
    assert payload["mode"] == "fetch_only"
    assert payload["source_kind"] == "source-xlsx"
    assert payload["source_xlsx"] == str(source)
    assert payload["requested_executor_sectors"] == []
    assert payload["requested_emitter_sectors"] == []
    assert payload["requested_ssa_numbers"] == []
    assert payload["requested_filters"]["executor_sectors"] == []
    assert payload["requested_filters"]["number_of_years"] == 4
    assert payload["requested_filters"]["limit"] == 200
    assert payload["normalized_rows"] == 1
    assert payload["imported"] is False
    assert Path(payload["import_xlsx_path"]).is_file()
    assert payload["ssa_examples"] == ["202600003"]
    assert payload["rows_by_executor_sector"] == {"IEE3": 1}
    assert payload["rows_by_emitter_sector"] == {"MEL4": 1}
    assert payload["rows_by_source_file"] == {"pai_cli.xlsx": 1}
    assert payload["ssa_examples_by_executor_sector"] == {"IEE3": ["202600003"]}
    assert payload["summary_error"] is None
    assert payload["warnings"] == []


def test_pai_import_summary_collects_manifest_warning_shapes(tmp_path: Path) -> None:
    source = tmp_path / "pai.xlsx"
    manifest = tmp_path / "manifest.json"
    recursive_warning: dict[str, object] = {}
    recursive_warning["warning"] = recursive_warning
    export = PaiScrapReportExport(
        command=("fake",),
        scrap_report_root=tmp_path,
        manifest_path=manifest,
        xlsx_path=source,
        manifest={
            "warnings": (
                {"message": "tuple mapped"},
                ["nested list"],
                {"raw set warning"},
                recursive_warning,
            ),
            "warning": {"text": "single mapped"},
        },
        stdout="",
        stderr="",
    )
    request = PaiScrapReportRequest(project_root=tmp_path)
    result = PaiImportResult(
        export=export,
        mode="fetch_only",
        import_xlsx_path=source,
        staged_files=(),
        staging_summary={},
        imported=False,
        normalized_rows=0,
        rows_before_import=None,
        rows_after_import=None,
    )

    payload = build_pai_import_summary_payload(
        result,
        request=request,
        source_xlsx=None,
    )

    assert payload["warnings"] == [
        "tuple mapped",
        "nested list",
        "raw set warning",
        "{'warning': {...}}",
        "single mapped",
    ]
