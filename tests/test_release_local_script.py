from __future__ import annotations

import shutil
import subprocess

import pytest

from tests.release_script_assertions import (
    PROJECT_ROOT,
    assert_before,
    read_repo_text,
    section_between,
)


SCRIPT = PROJECT_ROOT / "dev_env" / "build" / "release_local.ps1"


def _script_text() -> str:
    return read_repo_text("dev_env", "build", "release_local.ps1")


def test_release_local_orchestrates_windows_and_debian_without_inline_build_logic() -> None:
    script = _script_text()

    assert "[switch] $DryRun" in script
    assert "[switch] $Yes" in script
    assert "[switch] $SkipWindows" in script
    assert "[switch] $SkipDebian" in script
    assert "[CmdletBinding(PositionalBinding = $false)]" in script
    assert "Normalize-Selection" in script
    assert "ValidateSet(" not in script
    assert "release_windows.ps1" in script
    assert "release_debian.sh" in script
    assert "build_pyinstaller" not in script
    assert "build_nuitka" not in script
    assert "build_pyoxidizer" not in script
    assert "create_distribution.py" not in script


def test_release_local_dry_run_is_forwarded_to_both_orchestrators() -> None:
    script = _script_text()

    assert "$windowsArgs += \"-DryRun\"" in script
    assert " --dry-run" in script
    assert_before(script, "$windowsArgs += \"-DryRun\"", "& powershell @windowsArgs")
    assert_before(script, " --dry-run", "& wsl @debianArgs")


def test_release_local_passes_windows_backends_as_argument_array() -> None:
    script = _script_text()

    assert "$backendItems = Normalize-Selection -Items $Backend" in script
    assert "$packageItems = Normalize-Selection -Items $DebianPackage" in script
    assert "$windowsArgs += $backendCsv" in script
    assert '"-Backend",\n        $backendCsv' not in script
    assert_before(script, '"-Backend"', "$windowsArgs += $backendCsv")
    assert_before(script, "$windowsArgs += $backendCsv", "& powershell @windowsArgs")


def test_release_local_quotes_wsl_bash_arguments() -> None:
    script = _script_text()

    assert "function ConvertTo-BashSingleQuoted" in script
    assert "$repoRootWslQuoted = ConvertTo-BashSingleQuoted $repoRootWsl" in script
    assert "cd $repoRootWslQuoted" in script
    assert "cd '$repoRootWsl'" not in script


def test_release_local_requires_wsl_only_for_debian_phase() -> None:
    script = _script_text()
    pre_resolution = section_between(
        script,
        'Assert-Tool "git"',
        "$repoRoot = Resolve-RepoRoot",
    )

    assert 'if (-not $SkipDebian) {\n    Assert-Tool "wsl"\n}' in pre_resolution
    assert_before(script, 'Assert-Tool "wsl"', "$repoRoot = Resolve-RepoRoot")


def test_release_local_skip_all_dry_run_executes_without_wsl_preflight() -> None:
    powershell = shutil.which("powershell") or shutil.which("pwsh")
    if powershell is None:
        pytest.skip("PowerShell ausente para validar release_local.ps1")

    result = subprocess.run(
        [
            powershell,
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(SCRIPT),
            "-SkipWindows",
            "-SkipDebian",
            "-DryRun",
            "-Yes",
        ],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        check=False,
        timeout=60,
    )

    assert result.returncode == 0, f"STDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
    assert "Release local concluido." in result.stdout


def test_release_local_accepts_comma_separated_tokens_from_external_shell() -> None:
    powershell = shutil.which("powershell") or shutil.which("pwsh")
    if powershell is None:
        pytest.skip("PowerShell ausente para validar release_local.ps1")

    result = subprocess.run(
        [
            powershell,
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(SCRIPT),
            "-Backend",
            "pyinstaller,nuitka",
            "-DebianPackage",
            "deb,tar",
            "-SkipWindows",
            "-SkipDebian",
            "-DryRun",
            "-Yes",
        ],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        check=False,
        timeout=60,
    )

    assert result.returncode == 0, f"STDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
    assert "Release local concluido." in result.stdout


def test_release_local_keeps_shells_separated() -> None:
    script = _script_text()

    assert "ConvertTo-WslPath" in script
    assert "& powershell @windowsArgs" in script
    assert "& wsl @debianArgs" in script
    assert "release_windows.ps1" in script
    assert "release_debian.sh" in script
    assert "Compress-Archive" not in script
    assert "tar -czf" not in script
    assert "dpkg-deb" not in script
