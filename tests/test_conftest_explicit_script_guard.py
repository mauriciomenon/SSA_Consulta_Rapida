"""SS-08: pytest recusa script de tests/ fora de python_files passado pelo nome."""

import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _collect(target: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-m", "pytest", "--collect-only", "-q", "-p", "no:cacheprovider", target],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        timeout=120,
    )


def test_script_fora_do_padrao_e_recusado():
    # reporting_utils.py e um helper inofensivo; o caso real e run_import_verification.py.
    res = _collect("tests/reporting_utils.py")
    assert res.returncode == 4, res.stdout + res.stderr
    assert "fora de python_files" in res.stderr


def test_arquivo_de_teste_continua_coletado():
    res = _collect("tests/test_config_dir_project_root.py::test_config_paths_follow_env_when_set")
    assert res.returncode == 0, res.stdout + res.stderr
