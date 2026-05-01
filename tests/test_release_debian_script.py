from __future__ import annotations

import importlib
import json
from pathlib import Path

import pytest

from main import _get_project_root


PROJECT_ROOT = Path(_get_project_root())
SCRIPT = PROJECT_ROOT / "dev_env" / "build" / "release_debian.sh"
REPORT_SCRIPT = PROJECT_ROOT / "dev_env" / "build" / "release_platform_report.py"
SCORECARD_FILE = PROJECT_ROOT / "dev_env" / "build" / "backend_scorecards.json"
TARGETS_FILE = PROJECT_ROOT / "dev_env" / "build" / "release_targets.json"
REPORT_MODULE = importlib.import_module("dev_env.build.release_platform_report")


def _script_text() -> str:
    if not SCRIPT.is_file():
        raise AssertionError(f"script ausente: {SCRIPT}")
    return SCRIPT.read_text(encoding="utf-8")


def test_release_debian_script_is_bash_only_and_interactive() -> None:
    script = _script_text()

    assert script.startswith("#!/usr/bin/env bash")
    assert "set -euo pipefail" in script
    assert "select_backend_interactively" in script
    assert "read -r -p" in script
    assert "--backend e obrigatorio em ambiente nao interativo" in script
    assert "powershell" not in script.lower()
    assert "pwsh" not in script.lower()
    assert ".bat" not in script.lower()
    assert "Compress-Archive" not in script
    assert "FileVersionInfo" not in script


def test_release_debian_script_has_local_and_ssh_modes() -> None:
    script = _script_text()

    assert "--ssh-host" in script
    assert "--ssh-repo" in script
    assert "caminho absoluto do repositorio no host remoto" in script
    assert "Use caminho absoluto sem espacos/metacaracteres" in script
    assert "run_remote_release" in script
    assert "ssh " in script
    assert "bash -s --" in script
    assert "REMOTE_RELEASE" in script
    assert "assert_ssh_host" in script
    assert "assert_ssh_repo" in script
    assert "*@*@*" in script
    assert "*[!A-Za-z0-9._@-]*" in script
    assert "*[!A-Za-z0-9._/@%+=:,~-]*" in script
    assert " =~ ^(" not in script
    assert "assert_debian_host" in script
    assert "assert_debian_amd64" in script
    assert "--with-local-data nao e suportado via SSH" in script


def test_release_debian_script_has_deterministic_preflight_and_report() -> None:
    script = _script_text()

    assert "assert_clean_release_workspace" in script
    assert "AllowDirty" not in script
    assert "rev-parse HEAD" in script
    assert "diff --cached --name-only" in script
    assert "diff --ignore-cr-at-eol --name-only" in script
    assert "ls-files --others --exclude-standard" in script
    assert "git.exe -C" in script
    assert "wslpath -w" in script
    assert "release_report_debian_amd64.json" in script
    assert "write_release_report" in script
    assert '--platform "debian_amd64"' in script
    assert "write_tar_packages" in script
    assert "validate_tar_payload" in script
    assert "build_info.json" in script
    assert "GUIA_MIGRACAO_NOVA_INSTALACAO.md" in script
    assert "validate_source_protection" in script
    assert "source-protection" in REPORT_SCRIPT.read_text(encoding="utf-8")
    assert '--repo-root "${root}"' in script
    assert "bundle_roots" in script
    assert "SSA_CLI_v${app_version}_debian_amd64" in script
    assert "SSA_GUI_v${app_version}_debian_amd64" in script
    assert "cli_entry.dist" in script
    assert "gui_entry.dist" in script
    assert 'if [[ "${DRY_RUN}" == "1" ]]; then' in script
    assert script.index('log "dry-run concluido sem build/pacote"') < script.index("run_package_phase()")
    assert script.index('if [[ "${DRY_RUN}" == "1" ]]; then') < script.index("run_package_phase")
    report_script = REPORT_SCRIPT.read_text(encoding="utf-8")
    assert "hashlib.sha256" in report_script


def test_release_debian_script_normalizes_csv_tokens() -> None:
    script = _script_text()

    assert "release_targets_csv backends" in script
    assert "release_targets_csv packages" in script
    assert "load_release_target_cache" in script
    assert "release-unsupported-pairs" in script
    assert "check-release-target" in script
    assert "[![:space:]]" in script
    assert "join_csv" in script
    assert 'while [[ "${csv}" == *, ]]' in script
    assert "local -n" not in script
    assert "<(split_csv" not in script
    assert 'for backend in $(split_csv "${csv}")' in script
    assert 'for package_kind in $(split_csv "${csv}")' in script
    assert 'BACKENDS_CSV="$(normalize_backends "${BACKENDS_CSV}")"' in script
    assert 'PACKAGES_CSV="$(normalize_packages "${PACKAGES_CSV}")"' in script
    assert 'printf \'%s\\n\' "pyinstaller,nuitka,pyoxidizer"' not in script


def test_release_debian_script_calls_only_debian_wrappers() -> None:
    script = _script_text()

    assert "build_pyinstaller_debian.sh" in script
    assert "build_nuitka_debian.sh" in script
    assert "build_pyoxidizer_debian.sh" in script
    assert "package_debian_amd64_deb.sh" in script
    assert "package_debian_amd64_appimage.sh" in script
    assert "SSA_Consulta_Rapida_v${app_version}_debian_amd64_pyinstaller_cli.tar.gz" in script
    assert "SSA_Consulta_Rapida_v${app_version}_debian_amd64_nuitka_cli.tar.gz" in script
    assert "SSA_Consulta_Rapida_v${app_version}_debian_amd64_pyoxidizer.tar.gz" in script
    assert "release_target_reason" in script
    assert "is_supported_package_pair" in script
    assert 'pacote ignorado ${package_kind} ${backend}: $(release_target_reason' in script
    assert script.index("log_package_matrix") < script.index("run_build_phase")
    assert "package_debian_arm64" not in script
    assert "release_windows.ps1" not in script


def test_release_debian_script_exposes_backend_scorecard() -> None:
    script = _script_text()
    report_script = REPORT_SCRIPT.read_text(encoding="utf-8")
    scorecard_text = SCORECARD_FILE.read_text(encoding="utf-8")

    assert "get_backend_scorecard" in script
    assert "security_score" in report_script
    assert "source_protection_score" in report_script
    assert "easy_user_dirs_score" in report_script
    assert "package_size_score" in report_script
    assert "backend_scorecards.json" in report_script
    assert '"protected_release": true' in scorecard_text
    assert '"protected_release": false' in scorecard_text
    assert 'path.name.endswith(".tar.gz")' in report_script


def test_release_targets_json_defines_validated_targets() -> None:
    payload = json.loads(TARGETS_FILE.read_text(encoding="utf-8"))

    assert payload["schema_version"] == 1
    assert [item["name"] for item in payload["backends"]] == [
        "pyinstaller",
        "nuitka",
        "pyoxidizer",
    ]
    assert [item["name"] for item in payload["packages"]] == [
        "deb",
        "appimage",
        "tar",
        "zip",
    ]
    assert REPORT_MODULE._enabled_target_names(
        REPORT_MODULE._load_release_targets(),
        "backends",
        "debian_amd64",
    ) == ["pyinstaller", "nuitka", "pyoxidizer"]
    assert REPORT_MODULE._enabled_target_names(
        REPORT_MODULE._load_release_targets(),
        "packages",
        "debian_amd64",
    ) == ["deb", "appimage", "tar"]
    assert REPORT_MODULE._unsupported_pair_reason(
        REPORT_MODULE._load_release_targets(),
        "debian_amd64",
        "pyoxidizer",
        "appimage",
    )


def test_release_debian_report_read_json_errors_include_path(tmp_path) -> None:
    missing = tmp_path / "missing.json"
    with pytest.raises(REPORT_MODULE.ReleaseReportError, match="missing.json"):
        REPORT_MODULE._read_json(missing)

    invalid = tmp_path / "invalid.json"
    invalid.write_text("{", encoding="utf-8")
    with pytest.raises(REPORT_MODULE.ReleaseReportError, match="JSON invalido"):
        REPORT_MODULE._read_json(invalid)


def test_release_debian_report_asset_payload_errors_include_path(
    tmp_path,
    monkeypatch,
) -> None:
    asset = tmp_path / "package.deb"
    asset.write_bytes(b"payload")

    def fail_sha256(_path):
        raise OSError("blocked")

    monkeypatch.setattr(REPORT_MODULE, "_sha256", fail_sha256)

    with pytest.raises(REPORT_MODULE.ReleaseReportError, match="package.deb"):
        REPORT_MODULE._asset_payload(asset)
