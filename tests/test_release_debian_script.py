from __future__ import annotations

import importlib
import argparse
import json
from pathlib import Path

import pytest

from tests.release_script_assertions import (
    PROJECT_ROOT,
    assert_no_unguarded_string_position_helpers,
    assert_before,
    read_repo_text,
    section_between,
)


SCRIPT = PROJECT_ROOT / "dev_env" / "build" / "release_debian.sh"
ARM64_SCRIPT = PROJECT_ROOT / "dev_env" / "build" / "release_debian_arm64.sh"
REPORT_SCRIPT = PROJECT_ROOT / "dev_env" / "build" / "release_platform_report.py"
SCORECARD_FILE = PROJECT_ROOT / "dev_env" / "build" / "backend_scorecards.json"
TARGETS_FILE = PROJECT_ROOT / "dev_env" / "build" / "release_targets.json"
REPORT_MODULE = importlib.import_module("dev_env.build.release_platform_report")


def _script_text() -> str:
    return read_repo_text("dev_env", "build", "release_debian.sh")


def _arm64_script_text() -> str:
    return read_repo_text("dev_env", "build", "release_debian_arm64.sh")


def test_release_debian_script_is_bash_only() -> None:
    script = _script_text()
    allowed_wsl_powershell = "/mnt/c/Windows/System32/WindowsPowerShell/v1.0/powershell.exe"

    assert script.startswith("#!/usr/bin/env bash")
    assert "set -euo pipefail" in script
    assert allowed_wsl_powershell in script
    script_without_allowed = script.replace(allowed_wsl_powershell, "")
    script_without_allowed = script_without_allowed.replace("Windows PowerShell", "")
    assert "powershell" not in script_without_allowed.lower()
    assert "pwsh" not in script.lower()
    assert ".bat" not in script.lower()
    assert "Compress-Archive" not in script
    assert "FileVersionInfo" not in script


def test_release_debian_script_keeps_interactive_contract() -> None:
    script = _script_text()

    assert "select_backend_interactively" in script
    assert "read -r -p" in script
    assert "--backend e obrigatorio em ambiente nao interativo" in script


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
    assert '""|-*|*@*@*|@*|*@|*[!A-Za-z0-9._@-]*)' in script
    assert "*@*@*" in script
    assert "*[!A-Za-z0-9._@-]*" in script
    assert "*[!A-Za-z0-9._/@%+=:,~-]*" in script
    assert " =~ ^(" not in script
    assert "assert_debian_host" in script
    assert "assert_debian_amd64" in script
    assert "--with-local-data nao e suportado via SSH" in script


def test_release_debian_script_has_deterministic_preflight() -> None:
    script = _script_text()

    assert "assert_clean_release_workspace" in script
    assert "AllowDirty" not in script
    assert "rev-parse HEAD" in script
    assert "diff --cached --name-only" in script
    assert "diff --ignore-cr-at-eol --quiet" in script
    assert "diff --ignore-cr-at-eol --name-only" in script
    assert "ls-files --others --exclude-standard" in script
    assert_before(script, "diff --ignore-cr-at-eol --quiet", "diff --ignore-cr-at-eol --name-only")
    assert "/mnt/c/Windows/System32/WindowsPowerShell/v1.0/powershell.exe" in script
    assert "-NoProfile -NonInteractive" in script
    assert "ps_win_root" in script
    assert "sed \"s/'/''/g\"" in script
    assert "\"& git -C '${ps_win_root}' status --porcelain=v1\"" in script
    assert "status --porcelain=v1" in script
    assert "tr -d '\\r'" in script
    assert "wslpath -w" in script
    assert "nao foi possivel validar git limpo via Windows." in script


def test_release_debian_script_writes_report_and_validates_payloads() -> None:
    script = _script_text()

    assert "release_report_debian_amd64.json" in script
    assert "write_release_report" in script
    assert '--platform "debian_amd64"' in script
    assert "write_tar_packages" in script
    assert "validate_tar_payload" in script
    assert "build_info.json" in script
    assert "GUIA_MIGRACAO_NOVA_INSTALACAO.md" in script
    assert "validate_source_protection" in script
    assert "resolve_import_smoke_executable" in script
    assert "run_functional_import_smoke" in script
    assert "run_validation_phase" in script
    assert "scripts/smoke_cli.py" in script
    assert "--executable" in script
    assert "builds/pyoxidizer/debian_amd64/SSA_Consulta_Rapida" in script
    assert "smoke importacao ignorado" not in script
    assert "source-protection" in REPORT_SCRIPT.read_text(encoding="utf-8")
    assert '--repo-root "${root}"' in script
    assert "bundle_roots" in script
    assert "SSA_CLI_v${app_version}_debian_amd64" in script
    assert "SSA_GUI_v${app_version}_debian_amd64" in script
    assert "cli_entry.dist" in script
    assert "gui_entry.dist" in script
    report_script = REPORT_SCRIPT.read_text(encoding="utf-8")
    assert "hashlib.sha256" in report_script


def test_pyoxidizer_debian_scripts_retry_preflight_without_rtk() -> None:
    for script in (
        read_repo_text("dev_env", "build", "build_pyoxidizer_debian.sh"),
        read_repo_text("dev_env", "build", "build_pyoxidizer_debian_arm64.sh"),
    ):
        assert "PYOXIDIZER_CHECK_RETRIES=3" in script
        assert "attempt <= PYOXIDIZER_CHECK_RETRIES" in script
        assert "nova tentativa ${attempt}/${PYOXIDIZER_CHECK_RETRIES}" in script
        assert 'rtk uv tool run --python 3.13 --from "${PYOXIDIZER_UV_PACKAGE}"' not in script


def test_release_targets_json_rejects_non_object_root(tmp_path, monkeypatch) -> None:
    invalid_targets = tmp_path / "release_targets.json"
    invalid_targets.write_text("[]", encoding="utf-8")
    monkeypatch.setattr(REPORT_MODULE, "TARGETS_FILE", invalid_targets)

    with pytest.raises(REPORT_MODULE.ReleaseReportError) as excinfo:
        REPORT_MODULE._load_release_targets()

    message = str(excinfo.value)
    assert str(invalid_targets) in message
    assert "raiz JSON deve ser objeto" in message


def test_release_debian_script_checks_dry_run_before_package_phase() -> None:
    script = _script_text()
    local_release_body = section_between(script, "run_local_release()", "\nmain()")

    assert 'if [[ "${DRY_RUN}" == "1" ]]; then' in script
    assert_before(
        script,
        'log "dry-run concluido sem build/pacote"',
        "run_package_phase()",
    )
    assert_before(script, 'if [[ "${DRY_RUN}" == "1" ]]; then', "run_package_phase")
    assert_before(
        local_release_body,
        'if [[ "${DRY_RUN}" == "1" ]]; then',
        "run_validation_phase",
    )


def test_release_debian_script_normalizes_csv_tokens() -> None:
    script = _script_text()

    assert 'release_targets_csv "${kind}"' in script
    assert "load_release_target_cache" in script
    assert "release-unsupported-pairs" in script
    assert "check-release-target" not in script
    assert "awk -F '\\t'" in script
    assert "grep -F \"${backend}${tab}${package_kind}${tab}\"" not in script
    assert "[![:space:]]" in script
    assert "join_csv" in script
    assert "normalize_release_targets()" in script
    assert 'while [[ "${csv}" == *, ]]' in script
    assert "local -n" not in script
    assert "<(split_csv" not in script
    assert 'for backend in $(split_csv "${csv}")' not in script
    assert 'for package_kind in $(split_csv "${csv}")' not in script
    assert 'normalize_release_targets "${csv}" "backends" "backend vazio" "--backend invalido"' in script
    assert 'normalize_release_targets "${csv}" "packages" "" "--package invalido"' in script
    assert 'BACKENDS_CSV="$(normalize_backends "${BACKENDS_CSV}")"' in script
    assert 'PACKAGES_CSV="$(normalize_packages "${PACKAGES_CSV}")"' in script
    assert 'printf \'%s\\n\' "pyinstaller,nuitka,pyoxidizer"' not in script


def test_release_debian_script_calls_only_debian_build_wrappers() -> None:
    script = _script_text()

    assert "build_pyinstaller_debian.sh" in script
    assert "build_nuitka_debian.sh" in script
    assert "build_pyoxidizer_debian.sh" in script
    assert "package_debian_amd64_deb.sh" in script
    assert "package_debian_amd64_appimage.sh" in script
    assert "package_debian_arm64" not in script
    assert "release_windows.ps1" not in script


def test_release_debian_arm64_script_routes_arm64_build_and_package_wrappers() -> None:
    script = _arm64_script_text()
    backend_helper = read_repo_text("dev_env", "build", "release_debian_arm64_backend.sh")

    assert script.startswith("#!/usr/bin/env bash")
    assert "set -euo pipefail" in script
    assert 'PLATFORM="debian_arm64"' in script
    assert 'PACKAGE_ARCH="arm64"' in script
    assert 'DEFAULT_BACKENDS_CSV="nuitka"' in script
    assert 'DEFAULT_PACKAGES_CSV="deb"' in script
    assert "assert_debian_arm64" in script
    assert "release_report_${PLATFORM}.json" in script
    assert "release_debian_arm64_backend.sh" in script
    assert "build_pyinstaller_debian_arm64.sh" in backend_helper
    assert "build_nuitka_debian_arm64.sh" in backend_helper
    assert "build_pyoxidizer_debian_arm64.sh" in backend_helper
    assert "package_debian_arm64_deb.sh" in backend_helper
    assert "package_debian_arm64_appimage.sh" in backend_helper
    assert "package_debian_arm64_tar.sh" in backend_helper
    assert "scripts/smoke_cli.py" in backend_helper
    assert "--executable" in backend_helper
    assert "builds/nuitka/${PLATFORM}/cli_entry.dist" in backend_helper
    assert "SSA_CLI_v${app_version}_${PLATFORM}" in backend_helper
    assert "write_release_report" in script
    assert 'release-targets --platform "${PLATFORM}"' in script
    assert "write_tar_archive" not in script
    assert "write_tar_packages" not in script
    assert "release_debian.sh" not in script
    assert "release_windows.ps1" not in script


def test_release_debian_arm64_backend_helper_has_single_mandatory_file_contract() -> None:
    script = read_repo_text("dev_env", "build", "release_debian_arm64_backend.sh")

    assert "MANDATORY_RELEASE_FILES=(" in script
    assert '"config/build_info.json"' in script
    assert '"docs/GUIA_MIGRACAO_NOVA_INSTALACAO.md"' in script
    assert "assert_mandatory_release_files_exist" in script
    assert "assert_mandatory_release_files_listed" in script
    assert "grep -F \"build_info.json\"" not in script
    assert "grep -F \"GUIA_MIGRACAO_NOVA_INSTALACAO.md\"" not in script


def test_package_debian_arm64_tar_script_is_dedicated_packager() -> None:
    script = read_repo_text("dev_env", "build", "package_debian_arm64_tar.sh")

    assert script.startswith("#!/usr/bin/env bash")
    assert "set -Eeuo pipefail" in script
    assert 'PLATFORM="debian_arm64"' in script
    assert "assert_debian_arm64" in script
    assert "write_tar_archive" in script
    assert "--sort=name" in script
    assert '--mtime="UTC 1970-01-01"' in script
    assert "SSA_Consulta_Rapida_v${APP_VERSION}_${PLATFORM}_nuitka_cli.tar.gz" in script
    assert "release_debian_arm64.sh" not in script


def test_release_debian_script_declares_tar_packages_and_supported_pairs() -> None:
    script = _script_text()

    assert "--sort=name" in script
    assert '--mtime="UTC 1970-01-01"' in script
    assert "--owner=0" in script
    assert "--group=0" in script
    assert "--numeric-owner" in script
    assert "gzip -n" in script
    assert 'mv -f -- "${tmp_file}" "${output_file}"' in script
    assert "SSA_Consulta_Rapida_v${app_version}_debian_amd64_pyinstaller_cli.tar.gz" in script
    assert "SSA_Consulta_Rapida_v${app_version}_debian_amd64_nuitka_cli.tar.gz" in script
    assert "SSA_Consulta_Rapida_v${app_version}_debian_amd64_pyoxidizer.tar.gz" in script
    assert "release_target_reason" in script
    assert "is_supported_package_pair" in script
    assert "appimage:pyoxidizer)" not in script
    assert 'pacote ignorado ${package_kind} ${backend}: $(release_target_reason' in script
    package_backend_body = section_between(
        script,
        "run_package_backend()",
        "\nis_supported_package_pair()",
    )
    assert 'if ! is_supported_package_pair "${backend}" "${package_kind}"; then' in package_backend_body
    assert_before(script, "log_package_matrix", "run_build_phase")


def test_release_debian_script_exposes_backend_scorecard() -> None:
    script = _script_text()
    report_script = REPORT_SCRIPT.read_text(encoding="utf-8")
    scorecard_text = SCORECARD_FILE.read_text(encoding="utf-8")

    assert "get_backend_scorecard" in script
    assert "scorecards[backend]" in report_script
    assert "backend_scorecards.json" in report_script
    assert "security_score" in scorecard_text
    assert "source_protection_score" in scorecard_text
    assert "easy_user_dirs_score" in scorecard_text
    assert "package_size_score" in scorecard_text
    assert '"protected_release": true' in scorecard_text
    assert '"protected_release": false' in scorecard_text
    assert "PACKAGE_ASSET_SUFFIXES" in report_script
    assert "path.name.lower().endswith(asset_suffixes)" in report_script


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
        "dmg",
    ]
    assert REPORT_MODULE._enabled_target_names(
        REPORT_MODULE._load_release_targets(),
        "backends",
        "debian_amd64",
    ) == ["pyinstaller", "nuitka", "pyoxidizer"]
    assert REPORT_MODULE._enabled_target_names(
        REPORT_MODULE._load_release_targets(),
        "backends",
        "debian_arm64",
    ) == ["pyinstaller", "nuitka", "pyoxidizer"]
    assert REPORT_MODULE._enabled_target_names(
        REPORT_MODULE._load_release_targets(),
        "packages",
        "debian_amd64",
    ) == ["deb", "appimage", "tar"]
    assert REPORT_MODULE._enabled_target_names(
        REPORT_MODULE._load_release_targets(),
        "packages",
        "debian_arm64",
    ) == ["deb", "appimage", "tar"]
    assert REPORT_MODULE._enabled_target_names(
        REPORT_MODULE._load_release_targets(),
        "backends",
        "macos_arm64",
    ) == ["pyinstaller"]
    assert REPORT_MODULE._enabled_target_names(
        REPORT_MODULE._load_release_targets(),
        "packages",
        "macos_arm64",
    ) == ["dmg"]
    assert REPORT_MODULE._unsupported_pair_reason(
        REPORT_MODULE._load_release_targets(),
        "debian_amd64",
        "pyoxidizer",
        "appimage",
    )
    assert REPORT_MODULE._unsupported_pair_reason(
        REPORT_MODULE._load_release_targets(),
        "debian_arm64",
        "pyoxidizer",
        "appimage",
    )
    assert payload["asset_name_templates"]["debian_arm64"]["deb"] == (
        "ssa-consulta-rapida-{backend}-arm64_{app_version}_arm64.deb"
    )
    assert payload["asset_name_templates"]["macos_arm64"]["dmg"] == (
        "SSA_Consulta_Rapida_v{app_version}_macos_arm64.dmg"
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


def test_release_debian_report_filters_stale_assets_from_other_backends(
    tmp_path,
    monkeypatch,
) -> None:
    package_dir = tmp_path / "builds" / "packages" / "debian_amd64"
    package_dir.mkdir(parents=True)
    current = package_dir / "SSA_Consulta_Rapida_v4.43_debian_amd64_nuitka_cli.tar.gz"
    stale = package_dir / "SSA_Consulta_Rapida_v4.43_debian_amd64_pyoxidizer.tar.gz"
    current.write_bytes(b"current")
    stale.write_bytes(b"stale")

    monkeypatch.setattr(REPORT_MODULE, "_sha256", lambda _path: "0" * 64)
    report_file = tmp_path / "report.json"

    result = REPORT_MODULE.write_report(
        argparse.Namespace(
            repo_root=tmp_path,
            report_file=report_file,
            platform="debian_amd64",
            backends="nuitka",
            packages="tar",
            app_version="4.43",
            git_commit="abc",
        )
    )

    payload = json.loads(report_file.read_text(encoding="utf-8"))
    assert result == 0
    assert [asset["name"] for asset in payload["assets"]] == [current.name]


def test_release_debian_report_fails_when_package_dir_is_missing(tmp_path) -> None:
    report_file = tmp_path / "report.json"

    with pytest.raises(
        REPORT_MODULE.ReleaseReportError,
        match="diretorio de pacotes ausente",
    ):
        REPORT_MODULE.write_report(
            argparse.Namespace(
                repo_root=tmp_path,
                report_file=report_file,
                platform="debian_amd64",
                backends="nuitka",
                packages="tar",
                app_version="4.43",
                git_commit="abc",
            )
        )


def test_release_target_reason_rejects_disabled_target_pair() -> None:
    with pytest.raises(REPORT_MODULE.ReleaseReportError, match="package invalido"):
        REPORT_MODULE.print_release_target_reason(
            argparse.Namespace(
                platform="debian_arm64",
                backend="nuitka",
                package="zip",
            )
        )

    with pytest.raises(REPORT_MODULE.ReleaseReportError, match="backend invalido"):
        REPORT_MODULE.print_release_target_reason(
            argparse.Namespace(
                platform="macos_arm64",
                backend="nuitka",
                package="dmg",
            )
        )


def test_release_debian_expected_asset_names_cover_supported_package_matrix() -> None:
    names = REPORT_MODULE._expected_debian_asset_names(
        ["pyinstaller", "nuitka", "pyoxidizer"],
        ["deb", "appimage", "tar"],
        "4.43",
    )

    assert names == {
        "ssa-consulta-rapida-pyinstaller-amd64_4.43_amd64.deb",
        "ssa-consulta-rapida-nuitka-amd64_4.43_amd64.deb",
        "ssa-consulta-rapida-pyoxidizer-amd64_4.43_amd64.deb",
        "SSA_Consulta_Rapida_v4.43_debian_amd64_pyinstaller.AppImage",
        "SSA_Consulta_Rapida_v4.43_debian_amd64_nuitka.AppImage",
        "SSA_Consulta_Rapida_v4.43_debian_amd64_pyinstaller_cli.tar.gz",
        "SSA_Consulta_Rapida_v4.43_debian_amd64_pyinstaller_gui.tar.gz",
        "SSA_Consulta_Rapida_v4.43_debian_amd64_nuitka_cli.tar.gz",
        "SSA_Consulta_Rapida_v4.43_debian_amd64_nuitka_gui.tar.gz",
        "SSA_Consulta_Rapida_v4.43_debian_amd64_pyoxidizer.tar.gz",
    }


def test_release_debian_arm64_expected_asset_names_cover_supported_package_matrix() -> None:
    names = REPORT_MODULE._expected_debian_asset_names(
        ["pyinstaller", "nuitka", "pyoxidizer"],
        ["deb", "appimage", "tar"],
        "4.43",
        "debian_arm64",
        "arm64",
    )

    assert names == {
        "ssa-consulta-rapida-pyinstaller-arm64_4.43_arm64.deb",
        "ssa-consulta-rapida-nuitka-arm64_4.43_arm64.deb",
        "ssa-consulta-rapida-pyoxidizer-arm64_4.43_arm64.deb",
        "SSA_Consulta_Rapida_v4.43_debian_arm64_pyinstaller.AppImage",
        "SSA_Consulta_Rapida_v4.43_debian_arm64_nuitka.AppImage",
        "SSA_Consulta_Rapida_v4.43_debian_arm64_pyinstaller_cli.tar.gz",
        "SSA_Consulta_Rapida_v4.43_debian_arm64_pyinstaller_gui.tar.gz",
        "SSA_Consulta_Rapida_v4.43_debian_arm64_nuitka_cli.tar.gz",
        "SSA_Consulta_Rapida_v4.43_debian_arm64_nuitka_gui.tar.gz",
        "SSA_Consulta_Rapida_v4.43_debian_arm64_pyoxidizer.tar.gz",
    }


def test_release_macos_expected_asset_names_cover_dmg_package() -> None:
    names = REPORT_MODULE._expected_macos_asset_names(
        ["pyinstaller"],
        ["dmg"],
        "4.43",
    )

    assert names == {"SSA_Consulta_Rapida_v4.43_macos_arm64.dmg"}


def test_release_report_rejects_unknown_platform_for_expected_assets() -> None:
    with pytest.raises(REPORT_MODULE.ReleaseReportError) as excinfo:
        REPORT_MODULE._expected_asset_names(
            "linux_s390x",
            ["nuitka"],
            ["tar"],
            "4.43",
        )

    assert "platform desconhecido no report: linux_s390x" in str(excinfo.value)


def test_release_macos_report_filters_stale_dmg_assets(tmp_path, monkeypatch) -> None:
    package_dir = tmp_path / "builds" / "packages" / "macos_arm64"
    package_dir.mkdir(parents=True)
    current = package_dir / "SSA_Consulta_Rapida_v4.43_macos_arm64.dmg"
    stale = package_dir / "SSA_Consulta_Rapida_v4.41_macos_arm64.dmg"
    current.write_bytes(b"current")
    stale.write_bytes(b"stale")

    monkeypatch.setattr(REPORT_MODULE, "_sha256", lambda _path: "0" * 64)
    report_file = tmp_path / "report.json"

    result = REPORT_MODULE.write_report(
        argparse.Namespace(
            repo_root=tmp_path,
            report_file=report_file,
            platform="macos_arm64",
            backends="pyinstaller",
            packages="dmg",
            app_version="4.43",
            git_commit="abc",
        )
    )

    payload = json.loads(report_file.read_text(encoding="utf-8"))
    assert result == 0
    assert [asset["name"] for asset in payload["assets"]] == [current.name]


def test_release_report_normalizes_csv_arguments() -> None:
    assert REPORT_MODULE._split_csv(" nuitka, pyinstaller,,PYoxidizer ") == [
        "nuitka",
        "pyinstaller",
        "pyoxidizer",
    ]


def test_release_debian_tests_use_guarded_string_positions() -> None:
    test_source = Path(__file__).read_text(encoding="utf-8")

    assert_no_unguarded_string_position_helpers(test_source)


def test_release_string_position_guard_rejects_fragile_patterns() -> None:
    with pytest.raises(AssertionError, match="index"):
        assert_no_unguarded_string_position_helpers("def test_x():\n    text.index('x')\n")

    with pytest.raises(AssertionError, match="split"):
        assert_no_unguarded_string_position_helpers(
            "def test_x():\n    text.split('x', 1)[1]\n"
        )
