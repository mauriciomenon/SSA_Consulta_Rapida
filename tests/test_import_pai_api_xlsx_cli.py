from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

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
    assert payload["normalized_rows"] == 1
    assert payload["imported"] is False
    assert Path(payload["import_xlsx_path"]).is_file()
    assert payload["ssa_examples"] == ["202600003"]
    assert payload["warnings"] == []
