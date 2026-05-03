from __future__ import annotations

import json
from pathlib import Path

from tests.release_script_assertions import (
    PROJECT_ROOT,
    assert_no_unguarded_string_position_helpers,
    assert_before,
    read_repo_text,
    section_between,
)


SCRIPT = PROJECT_ROOT / "dev_env" / "build" / "release_windows.ps1"
SCORECARD_FILE = PROJECT_ROOT / "dev_env" / "build" / "backend_scorecards.json"
TARGETS_FILE = PROJECT_ROOT / "dev_env" / "build" / "release_targets.json"


def _script_text() -> str:
    return read_repo_text("dev_env", "build", "release_windows.ps1")


def test_release_windows_script_is_powershell_only_and_interactive() -> None:
    script = _script_text()

    assert "param(" in script
    assert "ValidateSet" not in script
    assert "Read-Host" in script
    assert "Assert-WindowsHost" in script
    assert "Assert-PowerShellHost" in script
    assert "[switch] $DryRun" in script
    assert "bash " not in script
    assert "wsl " not in script
    assert ".sh" not in script


def test_release_windows_script_has_deterministic_preflight_and_report() -> None:
    script = _script_text()

    assert "Assert-Tool" in script
    assert '$Command -notin @("git", "uv")' in script
    assert "Get-ReleaseTargetNames" in script
    assert "release-targets" in script
    assert "release_targets.json" not in script
    assert_before(script, 'Assert-Tool "git"', "$repoRoot = Resolve-RepoRoot")
    assert_before(script, 'Assert-Tool "uv"', "$repoRoot = Resolve-RepoRoot")
    assert '($selectedBackends -contains "pyoxidizer")' in script
    assert_before(
        script,
        "$selectedBackends = Get-SelectedBackends $Backend",
        'Assert-Tool "rcedit.exe"',
    )
    assert "Assert-CleanReleaseWorkspace" in script
    assert "AllowDirty" not in script
    assert "Get-GitHead" in script
    assert "Write-ReleaseReport" in script
    assert "release_report_windows_amd64.json" in script
    assert "$PSVersionTable" in script
    assert "[System.Diagnostics.FileVersionInfo]" in script
    assert "Dry-run Windows concluido sem build/pacote." in script
    assert_before(script, "if ($DryRun)", "if (-not $Yes)")
    assert "Invoke-CheckedProcess $repoRoot $config.build_script" in script
    assert_before(script, "if ($DryRun)", "foreach ($backendName in $selectedBackends)")
    assert_before(script, "if ($DryRun)", "Invoke-CheckedProcess $repoRoot $config.build_script")
    release_loop = section_between(
        script,
        "foreach ($backendName in $selectedBackends)",
        "Write-ReleaseReport",
    )
    assert "Invoke-DistributionPackage" in release_loop


def test_release_windows_script_normalizes_comma_separated_backend_tokens() -> None:
    script = _script_text()
    selected_backend_body = section_between(
        script,
        "function Get-SelectedBackends",
        "function Get-BackendScorecard",
    )

    assert 'foreach ($token in ($item -split ","))' in selected_backend_body
    assert "$value = $token.Trim().ToLowerInvariant()" in selected_backend_body
    assert "if ($normalized -contains \"all\")" in selected_backend_body
    assert "return @($normalized | Select-Object -Unique)" in selected_backend_body


def test_release_windows_script_calls_only_windows_build_wrappers() -> None:
    script = _script_text()

    assert "build_pyinstaller.bat" in script
    assert "build_nuitka.bat" in script
    assert "build_pyoxidizer.bat" in script
    assert "scripts\\create_distribution.py" in script
    assert "build_info.json" in script
    assert "GUIA_MIGRACAO_NOVA_INSTALACAO.md" in script
    assert "Get-FileHash" in script
    assert "[System.Security.Cryptography.SHA256]::Create()" in script
    assert "ComputeHash($stream)" in script
    assert "functional_cli_check" in script
    assert "gui_version_check" in script
    assert "Assert-SourceProtection" in script
    assert "dev_env\\build\\release_platform_report.py" in script
    assert "source-protection" in script
    assert '"--repo-root",' in script


def test_release_windows_smoke_uses_isolated_user_environment() -> None:
    script = _script_text()
    smoke_body = section_between(
        script,
        "function Invoke-Smoke",
        "function Write-BackendReleaseZips",
    )

    assert '$wrapperPath = Join-Path $smokeDir "smoke.cmd"' in smoke_body
    assert 'set `"APPDATA=$appDataDir`"' in smoke_body
    assert 'set `"LOCALAPPDATA=$localAppDataDir`"' in smoke_body
    assert 'set `"USERPROFILE=$userProfileDir`"' in smoke_body
    assert "set SSA_ 2^>nul" in smoke_body
    assert 'cd /d `"$smokeDir`"' in smoke_body
    assert "-FilePath $env:ComSpec" in smoke_body
    assert "-RedirectStandardInput $stdinPath" in smoke_body
    assert 'DADOS CARREGADOS:\\s+[1-9][0-9.,]*\\s+SSAs' in smoke_body
    assert "Smoke CLI contaminado por dados locais" in smoke_body


def test_release_windows_script_exposes_backend_scorecard() -> None:
    script = _script_text()
    scorecard = json.loads(SCORECARD_FILE.read_text(encoding="utf-8"))
    targets = json.loads(TARGETS_FILE.read_text(encoding="utf-8"))

    assert "Get-BackendScorecard" in script
    assert "backend_scorecards.json" in script
    assert [item["name"] for item in targets["backends"]] == [
        "pyinstaller",
        "nuitka",
        "pyoxidizer",
    ]
    assert [item["name"] for item in targets["packages"] if item.get("windows_amd64")] == [
        "zip",
    ]
    assert "security_score" in script
    assert "source_protection_score" in script
    assert "easy_user_dirs_score" in script
    assert "package_size_score" in script
    assert scorecard["nuitka"]["protected_release"] is True
    assert "codigo protegido por compilacao nativa" in scorecard["nuitka"]["note"]
    assert scorecard["pyinstaller"]["protected_release"] is False
    assert "compatibilidade; nao e artefato protegido" in scorecard["pyinstaller"]["note"]


def test_release_windows_backend_paths_are_grouped_expressions() -> None:
    script = _script_text()
    backend_block = section_between(
        script,
        "function Get-BackendConfig",
        "function Invoke-CheckedProcess",
    )

    for line in backend_block.splitlines():
        stripped = line.strip()
        if "Join-Path $RepoRoot" in stripped:
            assert stripped.startswith(
                ("(", "build_script = (", "cli_exe = (", "gui_exe = (", "source = (", "zip = (")
            )


def test_release_windows_tests_use_guarded_string_positions() -> None:
    test_source = Path(__file__).read_text(encoding="utf-8")

    assert_no_unguarded_string_position_helpers(test_source)
