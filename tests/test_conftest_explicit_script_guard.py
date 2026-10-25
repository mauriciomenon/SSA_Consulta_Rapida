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


# BL-40: modulos de apoio importados por testes coletados; qualquer outro .py solto em tests/
# precisa casar com python_files, senao nunca roda (havia ~38 scripts assim).
_SUPPORT_MODULES = {
    "__init__.py",
    "conftest.py",
    "automated_system_tests.py",
    "gui_filters_advanced_contract_helpers.py",
    "historico_otimizacoes_cli.py",
    "historico_otimizacoes_execucao.py",
    "legacy_config_utils.py",
    "legacy_path_utils.py",
    "legacy_report_utils.py",
    "release_script_assertions.py",
    "reporting_utils.py",
    "run_import_detailed.py",
    "run_import_verification.py",
    "run_modular_import.py",
    "run_quick_import.py",
    "teste_simples_refinamentos.py",
}


def test_tests_dir_has_no_uncollected_scripts() -> None:
    stray = sorted(
        path.name
        for path in (PROJECT_ROOT / "tests").glob("*.py")
        if not (path.name.startswith("test_") or path.name.endswith("_test.py"))
        and path.name not in _SUPPORT_MODULES
    )
    assert stray == [], stray
