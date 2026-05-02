from __future__ import annotations

import shutil
import subprocess

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
    assert 'ValidateSet("pyinstaller", "nuitka", "pyoxidizer", "all")' in script
    assert 'ValidateSet("deb", "appimage", "tar", "all")' in script
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


def test_release_local_quotes_wsl_bash_arguments() -> None:
    script = _script_text()

    assert "function ConvertTo-BashSingleQuoted" in script
    assert "$repoRootWslQuoted = ConvertTo-BashSingleQuoted $repoRootWsl" in script
    assert "cd $repoRootWslQuoted" in script
    assert "cd '$repoRootWsl'" not in script


def test_release_local_requires_wsl_only_for_debian_phase() -> None:
    script = _script_text()
    debian_phase = section_between(
        script,
        "if (-not $SkipDebian) {",
        "Write-Host \"Release local concluido.\"",
    )

    assert 'Assert-Tool "wsl"' in debian_phase
    assert_before(script, "if (-not $SkipDebian) {", 'Assert-Tool "wsl"')


def test_release_local_skip_all_dry_run_executes_without_wsl_preflight() -> None:
    powershell = shutil.which("powershell") or shutil.which("pwsh")
    if powershell is None:
        raise AssertionError("PowerShell ausente para validar release_local.ps1")

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
    )

    assert result.returncode == 0, result.stderr
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
