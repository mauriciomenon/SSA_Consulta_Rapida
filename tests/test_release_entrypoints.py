from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

import pytest

from tests.release_script_assertions import (
    PROJECT_ROOT,
    assert_before,
    read_repo_text,
    section_between,
)


def test_root_release_powershell_exposes_simple_defaults() -> None:
    script = read_repo_text("release.ps1")

    assert '[string] $Target = "windows"' in script
    assert '$DefaultBackend = "nuitka"' in script
    assert "release_windows.ps1" in script
    assert "release_debian.sh" not in script
    assert "build_nuitka" not in script
    assert "build_pyinstaller" not in script
    assert "build_pyoxidizer" not in script
    assert "[switch] $SkipBuild" not in script
    assert "[switch] $SkipPackage" not in script
    assert "[switch] $IncludeRuntimeDb" in script
    assert "Target: windows" in script
    assert "Backend Windows: nuitka" in script
    assert "Instalador Windows: ativado por padrao" in script
    assert "Debian deve usar ./release.sh em clone Linux nativo" in script


def test_root_release_powershell_forwards_safe_defaults() -> None:
    script = read_repo_text("release.ps1")

    assert 'Normalize-Target $Target' in script
    assert "Assert-WindowsReleaseHost" in script
    assert "Release Windows deve rodar em Windows ou VM Windows" in script
    assert 'Join-ReleaseCsv $Backend $DefaultBackend' in script
    assert '"-Backend", $BackendCsv' in script
    assert '$releaseArgs += "-IncludeRuntimeDb"' in script
    assert "$releaseArgs = @(" in script
    assert "& powershell @releaseArgs" in script
    assert "Initialize-WindowsBuildExtra $RepoRoot $BackendCsv" in script
    assert "Backend Windows invalido" in script
    assert "pyoxidizer ou combinacoes" in script
    assert '$value -eq "pyoxidizer"' in script
    assert "$needsPyoxidizer = $true" in script
    assert "SSA_PYOXIDIZER_UV_PACKAGE" in script
    assert "pyoxidizer==0.24.0" in script
    assert '"pyoxidizer",' in script
    assert '"--version"' in script
    assert "uv tool run --python 3.13 --from pyoxidizer" not in script
    assert '"--extra"' in script
    assert '"build"' in script
    assert "$args = @(" not in script
    assert "& powershell @args" not in script
    assert "ConvertTo-WslPath" not in script
    assert "Invoke-DebianReleaseViaWsl" not in script
    assert "& wsl" not in script
    assert "/mnt/" not in script
    assert "Assert-SsaWindowsHost" in script
    assert "Assert-SsaWindowsVenv" in script
    assert "if (-not $DryRun)" in script
    execution_block = section_between(script, "$targetName = Normalize-Target", 'Write-Host "Release concluido."')
    assert "catch" not in execution_block
    assert_before(
        execution_block,
        "Assert-SsaWindowsHost -RepoRoot $repoRoot",
        "Invoke-WindowsRelease $repoRoot",
    )
    assert_before(
        execution_block,
        "Assert-SsaWindowsVenv -VenvDir",
        "Invoke-WindowsRelease $repoRoot",
    )
    assert_before(script, "Assert-WindowsReleaseHost", "& powershell @releaseArgs")


@pytest.mark.parametrize("previous_environment", [None, "existing-environment"])
@pytest.mark.parametrize("stage,backend,failure", [
    ("preflight", "pyinstaller", None),
    ("preflight", "pyinstaller", "uv"),
    ("preflight", "pyinstaller", "powershell"),
    ("preflight", "pyinstaller,nuitka", None),
    ("preflight", "nuitka", None),
    ("preflight", "pyoxidizer", None),
    ("dry-run", "pyinstaller", None),
    ("package", "pyinstaller", None),
    ("package", "pyinstaller", "uv"),
    ("package", "nuitka", None),
    ("package", "pyoxidizer", None),
])
def test_windows_release_scopes_x64_environment_and_restores_caller(
    tmp_path: Path, previous_environment: str | None, stage: str, backend: str, failure: str | None,
) -> None:
    powershell = shutil.which("pwsh") or shutil.which("powershell")
    if powershell is None:
        pytest.skip("PowerShell necessario para validar selecao e restauracao de ambiente")
    probe = tmp_path / "probe.py"
    probe.write_text(
        "import json, os, pathlib, sys\n"
        "with pathlib.Path(os.environ['SSA_TEST_LOG']).open('a') as log:\n"
        "    log.write(json.dumps({'command': sys.argv[1], 'args': sys.argv[2:], "
        "'environment': os.environ.get('UV_PROJECT_ENVIRONMENT')}) + '\\n')\n"
        "raise SystemExit(42 if sys.argv[1] == os.environ['SSA_TEST_FAILURE'] else 0)\n",
        encoding="utf-8",
    )
    for name in ("uv", "powershell"):
        executable = tmp_path / (f"{name}.cmd" if sys.platform == "win32" else name)
        if sys.platform == "win32":
            content = f'@"%SSA_TEST_PYTHON%" "%SSA_TEST_PROBE%" {name} %*\n'
        else:
            content = f'#!/bin/sh\nexec "$SSA_TEST_PYTHON" "$SSA_TEST_PROBE" {name} "$@"\n'
        executable.write_text(content, encoding="utf-8")
        executable.chmod(0o755)
    env = os.environ | {
        "PATH": f"{tmp_path}{os.pathsep}{os.environ['PATH']}",
        "SSA_TEST_PYTHON": sys.executable,
        "SSA_TEST_PROBE": str(probe),
        "SSA_TEST_LOG": str(tmp_path / "calls.jsonl"),
        "SSA_TEST_FAILURE": failure or "",
        "SSA_TEST_REPO": str(tmp_path),
        "SSA_TEST_ROOT_SCRIPT": str(PROJECT_ROOT / "release.ps1"),
        "SSA_TEST_PACKAGE_SCRIPT": str(PROJECT_ROOT / "dev_env/build/release_windows.ps1"),
        "SSA_TEST_STAGE": stage,
        "SSA_TEST_BACKEND": backend,
    }
    env.pop("UV_PROJECT_ENVIRONMENT", None)
    if previous_environment is not None:
        env["UV_PROJECT_ENVIRONMENT"] = previous_environment
    # Executa o escopo real dos wrappers; o guard Windows completo e validado na VM.
    command = r"""
Set-StrictMode -Version 3.0
$ErrorActionPreference = 'Stop'
$RepoRoot = $env:SSA_TEST_REPO
$BackendCsv = $env:SSA_TEST_BACKEND
$DryRun = $env:SSA_TEST_STAGE -eq 'dry-run'
$Yes = $true
$SkipInstaller = $true
$IncludeRuntimeDb = $false
$DistributionModule = 'scripts.create_distribution'
$failure = $null
$rootAst = [Management.Automation.Language.Parser]::ParseFile($env:SSA_TEST_ROOT_SCRIPT, [ref]$null, [ref]$null)
$packageAst = [Management.Automation.Language.Parser]::ParseFile($env:SSA_TEST_PACKAGE_SCRIPT, [ref]$null, [ref]$null)
foreach ($ast in @($rootAst, $packageAst)) {
    foreach ($statement in $ast.EndBlock.Statements) {
        if ($statement -is [Management.Automation.Language.FunctionDefinitionAst] -and
            $statement.Name -in @('Initialize-WindowsBuildExtra', 'Invoke-DistributionPackage', 'Invoke-CheckedProcess')) {
            . ([scriptblock]::Create($statement.Extent.Text))
        }
    }
}
try {
    if ($env:SSA_TEST_STAGE -eq 'package') {
        Invoke-DistributionPackage $RepoRoot $BackendCsv $true $false
    } else {
        $scope = $rootAst.EndBlock.Statements | Where-Object {
            $_ -is [Management.Automation.Language.FunctionDefinitionAst] -and $_.Name -eq 'Invoke-WindowsRelease'
        }
        foreach ($statement in $scope.Body.EndBlock.Statements) {
            if ($statement -is [Management.Automation.Language.AssignmentStatementAst] -or
                $statement -is [Management.Automation.Language.TryStatementAst]) {
                . ([scriptblock]::Create($statement.Extent.Text))
            }
        }
    }
} catch { $failure = $_.Exception.Message }
@{environment=$env:UV_PROJECT_ENVIRONMENT; environment_present=(Test-Path Env:UV_PROJECT_ENVIRONMENT); error=$failure} | ConvertTo-Json -Compress
"""
    result = subprocess.run(
        [powershell, "-NoProfile", "-Command", command],
        cwd=tmp_path, env=env, capture_output=True, text=True, check=False, timeout=30,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    state = json.loads(result.stdout)
    assert state["environment"] == previous_environment
    assert state["environment_present"] is (previous_environment is not None)
    assert bool(state["error"]) is (failure is not None)
    calls = [json.loads(line) for line in (tmp_path / "calls.jsonl").read_text().splitlines()]
    use_x64 = "pyinstaller" in backend.split(",") and stage != "dry-run"
    expected_environment = str(tmp_path / ".venv-win") if use_x64 else previous_environment
    assert calls
    for call in calls:
        assert call["environment"] == expected_environment
        if call["command"] == "uv":
            expected_python = "cpython-3.13-windows-x86_64-none" if use_x64 else "3.13"
            assert call["args"][call["args"].index("--python") + 1] == expected_python
    if stage == "dry-run":
        assert [call["command"] for call in calls] == ["powershell"]
    if failure is None and stage == "preflight":
        assert calls[-1]["command"] == "powershell"


def test_root_release_bash_exposes_simple_defaults() -> None:
    script = read_repo_text("release.sh")

    assert script.startswith("#!/usr/bin/env bash\nset -euo pipefail")
    assert 'TARGET="auto"' in script
    assert 'DEFAULT_DEBIAN_BACKEND="nuitka"' in script
    assert 'DEFAULT_DEBIAN_PACKAGE="deb"' in script
    assert 'DEFAULT_DEBIAN_ARM64_BACKEND="nuitka"' in script
    assert 'DEFAULT_DEBIAN_ARM64_PACKAGE="deb"' in script
    assert 'DEFAULT_MACOS_BACKEND="pyinstaller"' in script
    assert 'DEFAULT_MACOS_PACKAGE="dmg"' in script
    assert "DMG esperado" in script
    assert "DMG macOS nao foi gerado" in script
    assert "smoke importacao" in script
    assert "scripts/smoke_cli.py" in script
    assert "--executable" in script
    assert "executavel CLI macOS ausente para smoke" in script
    assert "release_debian.sh" in script
    assert "release_debian_arm64.sh" in script
    assert "build_multiplatform.py" in script
    assert "build_nuitka" not in script
    assert "build_pyinstaller" not in script
    assert "build_pyoxidizer" not in script
    assert "--skip-build" not in script
    assert "--skip-package" not in script


def test_root_release_bash_routes_by_os_and_cleans_macos_before_build() -> None:
    script = read_repo_text("release.sh")

    assert "detect_target()" in script
    assert "Darwin)" in script
    assert "arm64 | aarch64) printf 'macos-arm64" in script
    assert "aarch64 | arm64) printf 'debian-arm64" in script
    assert "x86_64 | amd64) printf 'debian" in script
    assert "run_debian_arm64_release" in script
    assert "release_debian_arm64.sh" in script
    assert "detect_macos_platform" not in script
    assert "macOS x86_64 ainda nao tem alvo de release neste wrapper." in script
    assert "release macOS arm64 deve rodar em macOS arm64." in script
    assert "macos-arm64" in script
    assert "macos, macos-arm64" in script
    assert 'case "$(uname -m)" in' in script
    assert '--platform "${platform_name}" --clean' in script
    assert '--platform "${platform_name}" --apps cli gui' in script
    assert "SSA_CLI_v${version}_${platform_name}/SSA_CLI_v${version}_${platform_name}" in script
    assert '--backend "${backend}" --package "${package_kind}"' in script
    assert 'args+=(-y)' in script
    assert "--ssh-host" in script
    assert "--ssh-repo" in script
    assert "--allow-missing-remote" in script
    assert "macOS hoje suporta backend pyinstaller neste wrapper." in script
    target_case = section_between(script, 'case "${TARGET}" in', "printf '[release] concluido")
    all_block = section_between(target_case, "all)", ";;\nesac")
    assert 'if [[ "$(uname -s)" == "Darwin" ]]; then' in all_block
    assert_before(all_block, 'run_macos_release "${ROOT}"', 'run_debian_release "${ROOT}"')
    assert_before(all_block, 'run_debian_release "${ROOT}"', 'run_debian_arm64_release "${ROOT}"')
    assert_before(all_block, 'run_debian_arm64_release "${ROOT}"', 'elif [[ "$(uname -s)" == "Linux" ]]')
    assert 'aarch64 | arm64) run_debian_arm64_release "${ROOT}"' in all_block
    assert 'x86_64 | amd64) run_debian_release "${ROOT}"' in all_block
    assert "Debian amd64/arm64 remoto pulado" in all_block


def test_distribution_doc_prefers_simple_entrypoints() -> None:
    text = read_repo_text("docs", "GUIA_DISTRIBUICAO.md")
    current_truth = text.split("## HISTORICAL SNAPSHOT", 1)[0]

    assert "`release.ps1`" in current_truth
    assert "`release.sh`" in current_truth
    assert ".\\release.ps1" in current_truth
    assert "./release.sh" in current_truth
    assert "dev_env/build/release_windows.ps1" in current_truth


def test_release_entrypoint_files_are_tracked_contract_targets() -> None:
    assert (PROJECT_ROOT / "release.ps1").is_file()
    assert (PROJECT_ROOT / "release.sh").is_file()


def test_windows_release_workflow_runs_real_wrapper_and_uploads_artifacts() -> None:
    workflow = read_repo_text(".github", "workflows", "release-windows.yml")

    assert "workflow_dispatch:" in workflow
    assert "branches: [dev]" in workflow
    assert '".github/workflows/release-windows.yml"' in workflow
    assert "runs-on: windows-latest" in workflow
    assert 'default: "nuitka"' in workflow
    assert "choco install innosetup --no-progress -y" in workflow
    assert ".\\release.ps1" in workflow
    assert '"windows"' in workflow
    assert "Backend =" in workflow
    assert "RELEASE_BACKEND: ${{ inputs.backend || 'nuitka' }}" in workflow
    assert "RELEASE_INSTALLER_REQUIRED: ${{ !inputs.skip_installer }}" in workflow
    assert "$backend = $env:RELEASE_BACKEND" in workflow
    assert '[string]::IsNullOrWhiteSpace($backend)' in workflow
    assert '$releaseParams = @{' in workflow
    assert "Backend = @($backend)" in workflow
    assert "builds\\reports\\release_report_windows_amd64.json" in workflow
    assert "builds/packages/windows_amd64" in workflow
    assert 'Get-ChildItem -LiteralPath "builds\\packages\\windows_amd64" -Filter "*.zip"' in workflow
    assert 'Get-ChildItem -LiteralPath "dist_packages" -Filter "*.exe"' in workflow
    assert "Instalador Windows ausente em dist_packages" in workflow
    assert "dist_packages" in workflow
    assert "actions/upload-artifact@" in workflow
    assert "if-no-files-found: error" in workflow
    assert "Upload Windows release logs on failure" in workflow
    assert "if: failure()" in workflow
    assert "launchers/logs/*.log" in workflow
    assert "& powershell @args" not in workflow
    assert "$releaseArgs = @(" not in workflow
    assert "& .\\release.ps1 @releaseParams" in workflow
