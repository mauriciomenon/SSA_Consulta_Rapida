from __future__ import annotations

from pathlib import Path

from main import _get_project_root


PROJECT_ROOT = Path(_get_project_root())
SCRIPT = PROJECT_ROOT / "dev_env" / "build" / "release_windows.ps1"


def _script_text() -> str:
    assert SCRIPT.is_file()
    return SCRIPT.read_text(encoding="utf-8")


def test_release_windows_script_is_powershell_only_and_interactive() -> None:
    script = _script_text()

    assert "param(" in script
    assert '[ValidateSet("pyinstaller", "nuitka", "pyoxidizer", "all")]' in script
    assert "Read-Host" in script
    assert "Assert-WindowsHost" in script
    assert "Assert-PowerShellHost" in script
    assert "bash " not in script
    assert "wsl " not in script
    assert ".sh" not in script


def test_release_windows_script_has_deterministic_preflight_and_report() -> None:
    script = _script_text()

    assert "Assert-Tool" in script
    assert "Assert-CleanReleaseWorkspace" in script
    assert "AllowDirty" not in script
    assert "Get-GitHead" in script
    assert "Write-ReleaseReport" in script
    assert "release_report_windows_amd64.json" in script
    assert "$PSVersionTable" in script
    assert "[System.Diagnostics.FileVersionInfo]" in script


def test_release_windows_script_calls_only_windows_build_wrappers() -> None:
    script = _script_text()

    assert "build_pyinstaller.bat" in script
    assert "build_nuitka.bat" in script
    assert "build_pyoxidizer.bat" in script
    assert "scripts\\create_distribution.py" in script
    assert "build_info.json" in script
    assert "GUIA_MIGRACAO_NOVA_INSTALACAO.md" in script
    assert "Get-FileHash" in script
    assert "functional_cli_check" in script
    assert "version_check" in script


def test_release_windows_script_exposes_backend_scorecard() -> None:
    script = _script_text()

    assert "Get-BackendScorecard" in script
    assert "security_score" in script
    assert "python_source_exposure_score" in script
    assert "easy_user_dirs_score" in script
    assert "package_size_score" in script
