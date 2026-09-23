from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess

import pytest

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


@pytest.mark.parametrize(
    "command,answer,expected",
    [
        (
            "@(Get-SelectedBackends @() @('pyinstaller'))",
            "pyinstaller\n",
            ["pyinstaller"],
        ),
        (
            "@(Get-SelectedBackends @() @('pyinstaller', 'nuitka'))",
            "all\n",
            ["pyinstaller", "nuitka"],
        ),
        (
            "$Platform='windows_arm64'; $SkipInstaller=$false; $SkipPackage=$false; "
            "try { Assert-WindowsReleasePlatform; 'ok' } catch { $_.Exception.Message }",
            "",
            "Instalador Windows ARM64 indisponivel. Use -SkipInstaller para gerar ZIP.",
        ),
        (
            "$Platform='windows_arm64'; $SkipInstaller=$true; $SkipPackage=$false; "
            "Assert-WindowsReleasePlatform; 'ok'",
            "",
            "ok",
        ),
        (
            "$Platform='windows_arm64'; $SkipInstaller=$false; $SkipPackage=$true; "
            "Assert-WindowsReleasePlatform; 'ok'",
            "",
            "ok",
        ),
        (
            "$Platform='windows_amd64'; $SkipInstaller=$false; $SkipPackage=$false; "
            "Assert-WindowsReleasePlatform; 'ok'",
            "",
            "ok",
        ),
    ],
    ids=["backend", "all", "arm-installer", "arm-zip", "arm-no-package", "amd-installer"],
)
def test_release_windows_preflight_executes_real_functions(
    command: str, answer: str, expected: object,
) -> None:
    powershell = shutil.which("pwsh") or shutil.which("powershell")
    if powershell is None:
        pytest.skip("PowerShell necessario para validar selecao e preflight")
    script = r"""
Set-StrictMode -Version 3.0
$ErrorActionPreference = 'Stop'
$ast = [Management.Automation.Language.Parser]::ParseFile($env:SSA_TEST_SCRIPT, [ref]$null, [ref]$null)
foreach ($statement in $ast.EndBlock.Statements) {
    if ($statement -is [Management.Automation.Language.FunctionDefinitionAst] -and
        $statement.Name -in @('Get-SelectedBackends', 'Assert-WindowsReleasePlatform')) {
        . ([scriptblock]::Create($statement.Extent.Text))
    }
}
$result = & ([scriptblock]::Create($env:SSA_TEST_COMMAND))
Write-Output ('RESULT:' + (ConvertTo-Json -InputObject $result -Compress))
"""
    result = subprocess.run(
        [powershell, "-NoProfile", "-Command", script],
        env=os.environ | {"SSA_TEST_SCRIPT": str(SCRIPT), "SSA_TEST_COMMAND": command},
        input=answer, capture_output=True, text=True, check=False, timeout=30,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    result_line = next(line for line in result.stdout.splitlines() if line.startswith("RESULT:"))
    value = json.loads(result_line.removeprefix("RESULT:"))
    if isinstance(expected, list) and isinstance(value, str):
        value = [value]
    assert value == expected


def test_release_arm64_checks_native_python_before_bootstrap() -> None:
    script = read_repo_text("release.ps1")
    assert_before(
        script,
        "sysconfig.get_platform() == 'win-arm64'",
        "Initialize-WindowsBuildExtra $RepoRoot",
    )
    assert '$env:SSA_WINDOWS_ARM64_PYTHON = $armPython' in script
    assert '$env:UV_MANAGED_PYTHON = "false"' in script
    assert '$env:SSA_WINDOWS_ARM64_PYTHON = $previousArmPython' in script
    assert '$env:UV_MANAGED_PYTHON = $previousManagedPython' in script


@pytest.mark.parametrize("wrapper", ["build_pyinstaller.bat", "build_pyinstaller_windows_arm64.bat"])
def test_windows_pyinstaller_wrappers_do_not_update_project_lock(wrapper: str) -> None:
    script = read_repo_text("dev_env", "build", wrapper)
    project_commands = [line.strip() for line in script.splitlines() if line.strip().startswith(("uv run ", "uv sync "))]
    assert project_commands
    for command in project_commands:
        assert "--frozen" in command or "--no-sync" in command, command


def _script_text() -> str:
    return read_repo_text("dev_env", "build", "release_windows.ps1")


def test_release_windows_script_is_powershell_only_and_interactive() -> None:
    script = _script_text()

    assert "param(" in script
    assert "ValidateSet" not in script
    assert "Read-Host" in script
    assert "Write-Host" not in script
    assert "Assert-WindowsHost" in script
    assert "Assert-PowerShellHost" in script
    assert "[switch] $DryRun" in script
    assert "[switch] $IncludeRuntimeDb" in script
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
    assert "SSA_PYOXIDIZER_UV_PACKAGE" in script
    assert "pyoxidizer==0.24.0" in script
    assert '"pyoxidizer",' in script
    assert '"--version"' in script
    assert_before(
        script,
        "$selectedBackends = Get-SelectedBackends $Backend",
        'Assert-Tool "rcedit.exe"',
    )
    assert "Assert-CleanReleaseWorkspace" in script
    assert '"diff", "--cached", "--name-only"' in script
    assert '"diff", "--ignore-cr-at-eol", "--name-only"' in script
    assert '"ls-files", "--others", "--exclude-standard"' in script
    assert "AllowDirty" not in script
    assert "Get-GitHead" in script
    assert "Write-ReleaseReport" in script
    assert "release_report_windows_amd64.json" in script
    assert "$PSVersionTable" in script
    assert "[System.Diagnostics.FileVersionInfo]" in script
    assert "Dry-run Windows concluido sem build/pacote." in script
    assert_before(script, "if ($DryRun)", "if (-not $Yes)")
    assert "Invoke-CheckedProcess $repoRoot $config.build_script" in script
    assert '@("run", "--python", $pythonRequest, "python", "-m", $DistributionModule' in script
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
    nuitka_wrapper = read_repo_text("dev_env", "build", "build_nuitka.bat")
    assert "build_nuitka_clean.bat" in nuitka_wrapper
    nuitka_script = read_repo_text("dev_env", "build", "build_nuitka_clean.bat")
    assert "uv run --python 3.13 --extra build python -m nuitka" in nuitka_script
    assert "build_pyoxidizer.bat" in script
    assert "scripts.create_distribution" in script
    assert "build_info.json" in script
    assert "GUIA_MIGRACAO_NOVA_INSTALACAO.md" in script
    assert "Get-FileHash" in script
    assert "Compress-Archive" not in script
    assert "[System.IO.Compression.ZipFile]::CreateFromDirectory" in script
    assert_before(
        script,
        '$hashCommand = Get-Command -Name "Get-FileHash"',
        "foreach ($path in $Paths)",
    )
    assert "[System.Security.Cryptography.SHA256]::Create()" in script
    assert "$sha256 = $null" in script
    assert "ComputeHash($stream)" in script
    assert "functional_import_check" in script
    assert "gui_version_check" not in script
    assert "Assert-SourceProtection" in script
    assert "dev_env\\build\\release_platform_report.py" in script
    assert "source-protection" in script
    assert '"--repo-root",' in script


def test_release_windows_declares_native_arm64_target() -> None:
    script = _script_text()
    targets = json.loads(TARGETS_FILE.read_text(encoding="utf-8"))

    assert "windows_arm64" in script
    assert "build_pyinstaller_windows_arm64.bat" in script
    assert [item["name"] for item in targets["backends"] if item.get("windows_arm64")] == [
        "pyinstaller"
    ]
    assert [item["name"] for item in targets["packages"] if item.get("windows_arm64")] == [
        "zip"
    ]


def test_release_windows_runtime_db_hash_compares_sqlite_snapshots_between_bundles() -> None:
    script = _script_text()
    runtime_body = section_between(
        script,
        "function Assert-RuntimeDatabase",
        "function Invoke-DistributionPackage",
    )

    assert "$sourceHash" in runtime_body
    assert "$runtimeHash['sha256'] -ne $sourceHash" in runtime_body
    assert "Hash do banco de runtime diverge da origem" in runtime_body


def test_release_windows_smoke_uses_isolated_user_environment() -> None:
    script = _script_text()
    smoke_body = section_between(
        script,
        "function Invoke-Smoke",
        "function Write-BackendReleaseZips",
    )

    assert "function New-SmokeImportExcel" not in script
    assert "function Assert-SmokeImportDb" not in script
    assert "scripts\\smoke_cli.py" in smoke_body
    assert "--executable" in smoke_body
    assert "--force-rescan" in smoke_body
    assert "Start-Process -FilePath \"uv\"" in smoke_body
    assert "-RedirectStandardOutput $smokeJsonPath" in smoke_body
    assert "-RedirectStandardError $smokeErrPath" in smoke_body
    assert "Smoke importacao gerou JSON invalido" in smoke_body
    assert "Smoke importacao sem summary JSON" in smoke_body
    assert "[string]::Join([Environment]::NewLine" in smoke_body
    assert "ConvertFrom-Json" in smoke_body
    assert "imported_rows" in smoke_body
    assert "imported_rows = $smokeImportedRows" in smoke_body
    assert "executable = $smokeExePath" in smoke_body
    assert 'command = "$smokeExePath --force-rescan"' in smoke_body
    assert "$smokeExe = $Config.cli_exe" in smoke_body
    assert "$smokeExe = $Config.gui_exe" in smoke_body
    assert "Smoke importacao falhou" in smoke_body


def test_release_windows_report_is_utf8_without_bom() -> None:
    script = _script_text()
    report_body = section_between(
        script,
        "function Write-ReleaseReport",
        "Assert-WindowsHost",
    )

    assert "ConvertTo-Json -Depth 12" in report_body
    assert "Set-Content -Path $reportPath -Encoding UTF8" not in report_body
    assert "New-Object System.Text.UTF8Encoding $false" in report_body
    assert "[System.IO.File]::WriteAllText(" in report_body


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
        "function Get-UserWorkspaceRelativeDirectory",
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


def test_release_windows_script_has_backend_cleanup_allowlist() -> None:
    script = _script_text()
    release_loop = section_between(
        script,
        "foreach ($backendName in $selectedBackends)",
        "Write-ReleaseReport",
    )

    assert "function Get-BackendCleanupPath" in script
    assert "function Invoke-BackendCleanup" in script
    assert "Invoke-BackendCleanup -RepoRoot $repoRoot -BackendName $backendName -Version $version" in release_loop
    assert_before(
        release_loop,
        "Invoke-BackendCleanup -RepoRoot $repoRoot -BackendName $backendName -Version $version",
        "Invoke-CheckedProcess $repoRoot $config.build_script",
    )
    assert 'launchers\\dist\\windows_amd64' in script
    assert 'builds\\pyinstaller\\windows_amd64' in script
    assert "gui_entry.dist" in script
    assert "cli_entry.build" in script
    assert "cleanup_removed" in release_loop


def test_release_windows_script_ensures_user_workspace_dirs_before_zip() -> None:
    script = _script_text()
    release_loop = section_between(
        script,
        "foreach ($backendName in $selectedBackends)",
        "Write-ReleaseReport",
    )

    assert "function Get-UserWorkspaceRelativeDirectory" in script
    assert "function Initialize-UserWorkspaceDirectory" in script
    assert "docs_entrada" in script
    assert "historico_backups" in script
    assert "exportacao" in script
    assert ".gitkeep" in script
    assert "user_dirs_created" in release_loop
    assert_before(
        release_loop,
        "Initialize-UserWorkspaceDirectory -RuntimeRoot $runtimeRoots",
        "Write-BackendReleaseZips $config.release_zips",
    )


def test_release_windows_script_protects_runtime_before_zip() -> None:
    script = _script_text()
    release_loop = section_between(
        script,
        "foreach ($backendName in $selectedBackends)",
        "Write-ReleaseReport",
    )

    assert "function Get-RuntimeBundleRoot" in script
    assert "runtime_source_protection" in release_loop
    assert_before(
        release_loop,
        "Get-RuntimeBundleRoot -Config $config",
        "Initialize-UserWorkspaceDirectory -RuntimeRoot $runtimeRoots",
    )
    assert_before(
        release_loop,
        "Assert-SourceProtection $repoRoot $runtimeRoots",
        "Write-BackendReleaseZips $config.release_zips",
    )


def test_release_windows_script_skips_zip_validation_when_package_is_skipped() -> None:
    script = _script_text()
    release_loop = section_between(
        script,
        "foreach ($backendName in $selectedBackends)",
        "Write-ReleaseReport",
    )

    package_block = section_between(
        release_loop,
        "if (-not $SkipPackage) {",
        "\n    }\n\n    $results += [ordered]@{",
    )

    assert "$zipRecords = @()" in release_loop
    assert "$zipProtectionRecords = @()" in release_loop
    assert "$hashRecords = @()" in release_loop
    assert "Assert-ZipContents $zipPaths" in package_block
    assert "Assert-SourceProtection $repoRoot $zipPaths" in package_block
    assert "Get-ArtifactHash $zipPaths" in package_block


def test_release_windows_requires_exact_runtime_database_in_bundles_and_zips() -> None:
    script = _script_text()
    release_loop = section_between(
        script,
        "foreach ($backendName in $selectedBackends)",
        "Write-ReleaseReport",
    )
    runtime_check = section_between(
        script,
        "function Assert-RuntimeDatabase",
        "function Invoke-DistributionPackage",
    )
    zip_check = section_between(
        script,
        "function Assert-ZipContents",
        "function Assert-SourceProtection",
    )

    assert 'Join-Path $RepoRoot "data\\ssas.db"' in runtime_check
    assert 'Join-Path $root "data\\ssas.db"' in runtime_check
    assert '".xlsm"' in runtime_check
    assert "Hash do banco de runtime diverge" in runtime_check
    assert '$normalized -eq "data/ssas.db"' in zip_check
    assert 'EndsWith("/data/ssas.db")' in zip_check
    assert 'Contains("/_internal/")' in zip_check
    assert "ComputeHash($runtimeStream)" in zip_check
    assert "ZIP deve conter somente data/ssas.db externo" in zip_check
    assert '"--with-runtime-db"' in release_loop
    assert '"--include-runtime-db"' in script
    assert "runtime_database = $runtimeDatabaseRecords" in release_loop
    assert_before(
        release_loop,
        "Assert-RuntimeDatabase -RepoRoot $repoRoot -RuntimeRoot $runtimeRoots",
        "Write-BackendReleaseZips $config.release_zips",
    )
