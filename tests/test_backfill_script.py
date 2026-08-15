import json
import os
import pathlib
import subprocess
import sys

import pandas as pd

BASE = pathlib.Path(__file__).resolve().parent.parent
SCRIPT = BASE / "scripts" / "migracao" / "backfill_reprocessar.py"


def _run(cmd: list[str]):
    os.environ.copy()
    result = subprocess.run(
        [sys.executable, *cmd], cwd=BASE, capture_output=True, text=True
    )
    return result


def test_backfill_no_files_creates_empty_report(tmp_path):
    report_path = tmp_path / "empty_report.json"
    res = _run(
        [
            str(SCRIPT),
            "--dir",
            str(tmp_path),
            "--db",
            "data/ssas.db",
            "--dry-run",
            "--report-path",
            str(report_path),
        ]
    )
    assert res.returncode == 0, res.stderr
    assert report_path.exists(), "Report file not created"
    data = json.loads(report_path.read_text())
    assert data["summary"]["files_processed"] == 0


def test_backfill_limit_and_report(tmp_path):
    # cria alguns arquivos xlsx válidos mínimos
    for i in range(3):
        df = pd.DataFrame({"numero_ssa": [f"20250000{i}"], "descricao_ssa": ["teste"]})
        df.to_excel(tmp_path / f"arq_{i}.xlsx", index=False)
    report_path = tmp_path / "report.json"
    res = _run(
        [
            str(SCRIPT),
            "--dir",
            str(tmp_path),
            "--db",
            "data/ssas.db",
            "--dry-run",
            "--limit",
            "2",
            "--report-path",
            str(report_path),
        ]
    )
    assert res.returncode == 0, res.stderr
    assert report_path.exists()
    data = json.loads(report_path.read_text())
    assert data["summary"]["files_processed"] <= 2
