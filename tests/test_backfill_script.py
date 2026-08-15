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


def test_backfill_rejects_batch_limit_before_reset_or_import(tmp_path, monkeypatch):
    from scripts.migracao import backfill_reprocessar

    for index in range(2):
        (tmp_path / f"arq_{index}.xlsx").write_bytes(b"x")
    import_calls: list[str] = []
    reset_calls: list[str] = []
    monkeypatch.setattr("extracao.extractor.MAX_IMPORT_BATCH_FILES", 1)
    monkeypatch.setattr(
        backfill_reprocessar,
        "import_excel_robust",
        lambda path, **_kwargs: import_calls.append(path),
    )
    monkeypatch.setattr(
        backfill_reprocessar.database,
        "reset_database",
        lambda *_args, **_kwargs: reset_calls.append("reset"),
    )

    exit_code = backfill_reprocessar.main(
        ["--dir", str(tmp_path), "--dry-run", "--reset-db"]
    )

    assert exit_code == 2
    assert import_calls == []
    assert reset_calls == []
