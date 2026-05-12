from __future__ import annotations

import subprocess

from launchers.smoke_validation import SmokeValidationResult
from tests._helpers.fake_analyzer import fake_database_analyzer_type
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


def test_file_extraction_requires_every_excel_to_extract(monkeypatch, tmp_path) -> None:
    docs_entrada = tmp_path / "docs_entrada"
    docs_entrada.mkdir()
    (docs_entrada / "ok.xlsx").write_text("ok", encoding="utf-8")
    (docs_entrada / "empty.xlsx").write_text("empty", encoding="utf-8")
    tester = automated_system_tests.AutomatedSystemTester(str(tmp_path))

    def _fake_extract(file_path):
        if "ok.xlsx" in str(file_path):
            return automated_system_tests.pd.DataFrame({"numero_ssa": ["1"]})
        return automated_system_tests.pd.DataFrame()

    monkeypatch.setattr(automated_system_tests, "extract_data_from_file", _fake_extract)

    result = tester.test_file_extraction()

    assert result.success is False
    assert result.details["total_files"] == 2
    assert result.details["successful_extractions"] == 1
    assert result.details["success_rate"] == 0.5


def test_data_filtering_requires_every_filter_check(monkeypatch, tmp_path) -> None:
    tester = automated_system_tests.AutomatedSystemTester(str(tmp_path))
    monkeypatch.setattr(
        automated_system_tests.AutomatedSystemTester,
        "test_full_import_process",
        lambda _self: _system_result("full_import_process", True),
    )

    def _fake_filtered_data(*_args, **kwargs):
        filters = kwargs.get("filters") or {}
        if filters.get("setor_executor") == "MEDEIRO":
            return None
        return []

    monkeypatch.setattr(automated_system_tests, "get_filtered_data", _fake_filtered_data)

    result = tester.test_data_filtering()

    assert result.success is False
    assert result.details["total_tests"] == 3
    assert result.details["successful_tests"] == 2


def test_configuration_integrity_requires_every_present_config_file(tmp_path) -> None:
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    (config_dir / "column_mappings.json").write_text('{"a": "b"}', encoding="utf-8")
    (config_dir / "schema.sql").write_text("CREATE TABLE ssas (id INTEGER)", encoding="utf-8")
    (config_dir / "display_mappings.json").write_text("{broken", encoding="utf-8")
    tester = automated_system_tests.AutomatedSystemTester(str(tmp_path))

    result = tester.test_configuration_integrity()

    assert result.success is False
    assert result.details["total_tests"] == 3
    assert result.details["successful_tests"] == 2


def test_database_integrity_requires_zero_critical_issues(monkeypatch, tmp_path) -> None:
    tester = automated_system_tests.AutomatedSystemTester(str(tmp_path))
    monkeypatch.setattr(
        automated_system_tests.AutomatedSystemTester,
        "test_full_import_process",
        lambda _self: _system_result("full_import_process", True),
    )

    monkeypatch.setattr(
        automated_system_tests,
        "DatabaseAnalyzer",
        fake_database_analyzer_type(
            structure={"duplicated_groups": {}},
            sanity={
                "total_records": 10,
                "summary": {"missing_numero_ssa": 1, "empty_records": 0},
            },
        ),
    )

    result = tester.test_database_integrity()

    assert result.success is False
    assert result.details["critical_issues"] == 1


def test_database_integrity_reports_zero_score_for_empty_database(
    monkeypatch,
    tmp_path,
) -> None:
    tester = automated_system_tests.AutomatedSystemTester(str(tmp_path))
    monkeypatch.setattr(
        automated_system_tests.AutomatedSystemTester,
        "test_full_import_process",
        lambda _self: _system_result("full_import_process", True),
    )

    monkeypatch.setattr(
        automated_system_tests,
        "DatabaseAnalyzer",
        fake_database_analyzer_type(
            structure={"duplicated_groups": {}},
            sanity={"total_records": 0, "summary": {}},
        ),
    )

    result = tester.test_database_integrity()

    assert result.success is False
    assert result.details["integrity_score"] == 0.0


def test_run_all_tests_requires_every_noncritical_suite_to_pass(
    monkeypatch,
    tmp_path,
) -> None:
    tester = automated_system_tests.AutomatedSystemTester(str(tmp_path))
    results_by_method = {
        "test_database_creation": _system_result("database_creation", True),
        "test_file_extraction": _system_result("file_extraction", True),
        "test_full_import_process": _system_result("full_import_process", True),
        "test_cli_functionality": _system_result("cli_functionality", True),
        "test_gui_startup": _system_result("gui_startup", False),
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
    assert summary["critical_failures"] == []
