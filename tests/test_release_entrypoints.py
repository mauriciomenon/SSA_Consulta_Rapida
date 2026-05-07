from __future__ import annotations

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
    assert '$DefaultDebianPackage = "deb"' in script
    assert "release_windows.ps1" in script
    assert "release_debian.sh" in script
    assert "build_nuitka" not in script
    assert "build_pyinstaller" not in script
    assert "build_pyoxidizer" not in script
    assert "[switch] $SkipBuild" not in script
    assert "[switch] $SkipPackage" not in script
    assert "Target: windows" in script
    assert "Backend Windows/Debian: nuitka" in script
    assert "Pacote Debian: deb" in script


def test_root_release_powershell_forwards_safe_defaults() -> None:
    script = read_repo_text("release.ps1")

    assert 'Normalize-Target $Target' in script
    assert "Assert-WindowsReleaseHost" in script
    assert "Release Windows deve rodar em Windows ou VM Windows" in script
    assert 'Join-ReleaseCsv $Backend $DefaultBackend' in script
    assert 'Join-ReleaseCsv $DebianPackage $DefaultDebianPackage' in script
    assert '"-Backend", $BackendCsv' in script
    assert '$yesFlag = if ($Yes) { " -y" } else { "" }' in script
    assert "--backend $backendQuoted --package $packageQuoted$yesFlag$dryRunFlag" in script
    assert 'Get-Command "wsl"' in script
    assert "-AllowMissingRemote" in script
    execution_block = section_between(script, "$targetName = Normalize-Target", 'Write-Host "Release concluido."')
    assert_before(
        execution_block,
        "Invoke-WindowsRelease $repoRoot",
        "Invoke-DebianReleaseViaWsl",
    )
    assert_before(script, "Assert-WindowsReleaseHost", '& powershell @args')


def test_root_release_bash_exposes_simple_defaults() -> None:
    script = read_repo_text("release.sh")

    assert script.startswith("#!/usr/bin/env bash\nset -euo pipefail")
    assert 'TARGET="auto"' in script
    assert 'DEFAULT_DEBIAN_BACKEND="nuitka"' in script
    assert 'DEFAULT_DEBIAN_PACKAGE="deb"' in script
    assert 'DEFAULT_MACOS_BACKEND="pyinstaller"' in script
    assert 'DEFAULT_MACOS_PACKAGE="dmg"' in script
    assert "DMG esperado" in script
    assert "DMG macOS nao foi gerado" in script
    assert "smoke importacao" in script
    assert "scripts/smoke_cli.py" in script
    assert "--executable" in script
    assert "executavel CLI macOS ausente para smoke" in script
    assert "release_debian.sh" in script
    assert "build_multiplatform.py" in script
    assert "build_nuitka" not in script
    assert "build_pyinstaller" not in script
    assert "build_pyoxidizer" not in script
    assert "--skip-build" not in script
    assert "--skip-package" not in script


def test_root_release_bash_routes_by_os_and_cleans_macos_before_build() -> None:
    script = read_repo_text("release.sh")

    assert "detect_target()" in script
    assert "Darwin) printf 'macos" in script
    assert "Linux) printf 'debian" in script
    assert "--platform macos_arm64 --clean" in script
    assert "--platform macos_arm64 --apps cli gui" in script
    assert "SSA_CLI_v${version}_macos_arm64/SSA_CLI_v${version}_macos_arm64" in script
    assert '--backend "${backend}" --package "${package_kind}"' in script
    assert 'args+=(-y)' in script
    assert "--ssh-host" in script
    assert "--ssh-repo" in script
    assert "--allow-missing-remote" in script
    assert "macOS hoje suporta backend pyinstaller neste wrapper." in script


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
    assert "${{ inputs.backend }}" in workflow
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
    assert "& powershell @args" not in workflow
    assert "$releaseArgs = @(" not in workflow
    assert "& .\\release.ps1 @releaseParams" in workflow
