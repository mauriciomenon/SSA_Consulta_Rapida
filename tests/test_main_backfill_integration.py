import json
import pathlib
import subprocess
import sys

BASE = pathlib.Path(__file__).resolve().parent.parent
MAIN = BASE / "main.py"


def run_main(args):
    result = subprocess.run(
        [sys.executable, str(MAIN), "--acao", "backfill", "--", *args],
        cwd=BASE,
        capture_output=True,
        text=True,
    )
    return result


def test_main_backfill_generates_report(tmp_path):
    report_path = tmp_path / "main_report.json"
    # Sem arquivos -> relatório vazio
    res = run_main(
        ["--dir", str(tmp_path), "--dry-run", "--report-path", str(report_path)]
    )
    assert res.returncode == 0, res.stderr
    assert report_path.exists()
    data = json.loads(report_path.read_text())
    assert data["summary"]["files_processed"] == 0


def test_main_backfill_propagates_failure_exit_code(tmp_path):
    missing_dir = tmp_path / "missing"

    res = run_main(["--dir", str(missing_dir), "--dry-run"])

    assert res.returncode != 0
