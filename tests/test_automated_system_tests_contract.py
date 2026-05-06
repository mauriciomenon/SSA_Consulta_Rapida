from __future__ import annotations

import subprocess

from launchers.smoke_validation import SmokeValidationResult
from tests import automated_system_tests


def _system_result(test_name: str, success: bool):
    result = automated_system_tests.SystemTestResult(test_name)
    result.complete(success)
    return result


def test_cli_functionality_requires_all_cli_checks(monkeypatch, tmp_path) -> None:
    tester = automated_system_tests.AutomatedSystemTester(str(tmp_path))

    monkeypatch.setattr(
        automated_system_tests.AutomatedSystemTester,
        "test_full_import_process",
        lambda _self: _system_result("full_import_process", True),
    )
    monkeypatch.setattr(
        automated_system_tests,
        "run_cli_import_smoke",
        lambda repo_root: SmokeValidationResult(
            ok=True,
            imported_rows=1,
            returncode=0,
        ),
    )

    def _fake_run(*_args, **_kwargs):
        return subprocess.CompletedProcess(
            args=[],
            returncode=1,
            stdout="SSA Consulta",
            stderr="erro real",
        )

    monkeypatch.setattr(automated_system_tests.subprocess, "run", _fake_run)

    result = tester.test_cli_functionality()

    assert result.success is False
    assert result.details["total_tests"] == 2
    assert result.details["successful_tests"] == 1


def test_run_all_tests_blocks_critical_failure_despite_high_success_rate(
    monkeypatch,
    tmp_path,
) -> None:
    tester = automated_system_tests.AutomatedSystemTester(str(tmp_path))
    results_by_method = {
        "test_database_creation": _system_result("database_creation", True),
        "test_file_extraction": _system_result("file_extraction", True),
        "test_full_import_process": _system_result("full_import_process", True),
        "test_cli_functionality": _system_result("cli_functionality", False),
        "test_gui_startup": _system_result("gui_startup", True),
        "test_data_filtering": _system_result("data_filtering", True),
        "test_database_integrity": _system_result("database_integrity", True),
        "test_configuration_integrity": _system_result(
            "configuration_integrity",
            True,
        ),
    }

    monkeypatch.setattr(tester, "setup_test_environment", lambda: True)
    monkeypatch.setattr(tester, "cleanup_test_environment", lambda: None)
    for method_name, result in results_by_method.items():
        monkeypatch.setattr(tester, method_name, lambda result=result: result)

    summary = tester.run_all_tests()

    assert summary["success"] is False
    assert summary["success_rate"] == 0.875
    assert summary["critical_failures"] == ["cli_functionality"]
