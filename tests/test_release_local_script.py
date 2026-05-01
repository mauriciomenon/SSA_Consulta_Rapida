from __future__ import annotations

from pathlib import Path

from main import _get_project_root


PROJECT_ROOT = Path(_get_project_root())
SCRIPT = PROJECT_ROOT / "dev_env" / "build" / "release_local.ps1"


def _script_text() -> str:
    if not SCRIPT.is_file():
        raise AssertionError(f"script ausente: {SCRIPT}")
    return SCRIPT.read_text(encoding="utf-8")


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
    assert script.index("$windowsArgs += \"-DryRun\"") < script.index("& powershell @windowsArgs")
    assert script.index(" --dry-run") < script.index("& wsl @debianArgs")


def test_release_local_keeps_shell_boundaries_explicit() -> None:
    script = _script_text()

    assert "ConvertTo-WslPath" in script
    assert "cd '$repoRootWsl' && bash dev_env/build/release_debian.sh" in script
    assert "& powershell @windowsArgs" in script
    assert "& wsl @debianArgs" in script
    assert "Compress-Archive" not in script
    assert "tar -czf" not in script
    assert "dpkg-deb" not in script
