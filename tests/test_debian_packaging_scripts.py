from __future__ import annotations

import subprocess
from pathlib import Path

from main import _get_project_root


REPO_ROOT = Path(_get_project_root())
BUILD_DIR = REPO_ROOT / "dev_env/build"
COMMON_SCRIPT = BUILD_DIR / "package_debian_common.sh"
DEB_ENGINE_SCRIPT = BUILD_DIR / "package_debian_deb.sh"
APPIMAGE_ENGINE_SCRIPT = BUILD_DIR / "package_debian_appimage.sh"
ARM64_DEB_SCRIPT = BUILD_DIR / "package_debian_arm64_deb.sh"
ARM64_APPIMAGE_SCRIPT = BUILD_DIR / "package_debian_arm64_appimage.sh"
AMD64_DEB_SCRIPT = BUILD_DIR / "package_debian_amd64_deb.sh"
AMD64_APPIMAGE_SCRIPT = BUILD_DIR / "package_debian_amd64_appimage.sh"


ARCH_WRAPPERS = (
    (
        ARM64_DEB_SCRIPT,
        ARM64_APPIMAGE_SCRIPT,
        "debian_arm64",
        "arm64",
        "^(aarch64|arm64)$",
        "aarch64",
    ),
    (
        AMD64_DEB_SCRIPT,
        AMD64_APPIMAGE_SCRIPT,
        "debian_amd64",
        "amd64",
        "^(x86_64|amd64)$",
        "x86_64",
    ),
)


def _run_help(script: Path) -> str:
    result = subprocess.run(
        ["bash", str(script), "--help"],
        capture_output=True,
        text=True,
        check=False,
        timeout=10,
    )
    assert result.returncode == 0, result.stderr
    return result.stdout


def test_debian_package_scripts_exist_for_both_architectures() -> None:
    for deb_script, appimage_script, *_ in ARCH_WRAPPERS:
        assert deb_script.is_file()
        assert appimage_script.is_file()

    assert COMMON_SCRIPT.is_file()
    assert DEB_ENGINE_SCRIPT.is_file()
    assert APPIMAGE_ENGINE_SCRIPT.is_file()


def test_debian_arch_wrappers_only_set_arch_policy() -> None:
    for deb_script, appimage_script, platform, package_arch, machine_regex, appimage_arch in ARCH_WRAPPERS:
        for script in (deb_script, appimage_script):
            content = script.read_text(encoding="utf-8")
            assert f'export DEBIAN_PLATFORM="{platform}"' in content
            assert f'export DEBIAN_PACKAGE_ARCH="{package_arch}"' in content
            assert f"export DEBIAN_MACHINE_REGEX='{machine_regex}'" in content
            assert f'export DEBIAN_APPIMAGE_ARCH="{appimage_arch}"' in content
            assert "exec \"${SCRIPT_DIR}/package_debian_" in content
            assert "copy_dir_checked" not in content
            assert "dpkg-deb --build" not in content
            assert "appimagetool" not in content


def test_debian_package_scripts_expose_arch_specific_help_contract() -> None:
    arm_deb_help = _run_help(ARM64_DEB_SCRIPT)
    arm_appimage_help = _run_help(ARM64_APPIMAGE_SCRIPT)
    amd_deb_help = _run_help(AMD64_DEB_SCRIPT)
    amd_appimage_help = _run_help(AMD64_APPIMAGE_SCRIPT)

    assert ".deb Debian arm64/aarch64" in arm_deb_help
    assert "AppImage Debian arm64/aarch64" in arm_appimage_help
    assert "builds/packages/debian_arm64" in arm_deb_help
    assert "appimagetool aarch64" in arm_appimage_help

    assert ".deb Debian amd64/x86_64" in amd_deb_help
    assert "AppImage Debian amd64/x86_64" in amd_appimage_help
    assert "builds/packages/debian_amd64" in amd_deb_help
    assert "appimagetool x86_64" in amd_appimage_help


def test_debian_deb_engine_is_arch_aware_without_hardcoded_target() -> None:
    content = DEB_ENGINE_SCRIPT.read_text(encoding="utf-8")

    assert "Architecture: ${DEBIAN_PACKAGE_ARCH}" in content
    assert "${DEBIAN_PLATFORM}" in content
    assert "${DEBIAN_ARCH_LABEL}" in content
    assert "SSA_CLI_v${APP_VERSION}_${DEBIAN_PLATFORM}" in content
    assert "SSA_GUI_v${APP_VERSION}_${DEBIAN_PLATFORM}" in content
    assert "pyinstaller | nuitka | pyoxidizer" in content
    assert "--gui" in content
    assert "default_package_staging_dir deb" in content
    assert '${CLI_TARGET#"${PACKAGE_ROOT}"}' in content
    assert "${CLI_TARGET#${PACKAGE_ROOT}}" not in content
    assert "${CLI_TARGET/${PACKAGE_ROOT}/}" not in content
    assert "debian_arm64" not in content
    assert "debian_amd64" not in content
    assert "aarch64" not in content
    assert "x86_64" not in content


def test_debian_appimage_engine_is_arch_aware_without_hardcoded_target() -> None:
    content = APPIMAGE_ENGINE_SCRIPT.read_text(encoding="utf-8")

    assert 'ARCH="${DEBIAN_APPIMAGE_ARCH}"' in content
    assert "Exec=AppRun" in content
    assert "Desktop Entry" in content
    assert "SSA_GUI_v${APP_VERSION}_${DEBIAN_PLATFORM}" in content
    assert "--prepare-only" in content
    assert "pyinstaller | nuitka" in content
    assert "default_package_staging_dir appimage" in content
    assert '${APP_EXEC#"${APPDIR}"}' in content
    assert "${APP_EXEC#${APPDIR}}" not in content
    assert "${APP_EXEC/${APPDIR}/}" not in content
    assert "sed -i" not in content
    assert "debian_arm64" not in content
    assert "debian_amd64" not in content
    assert "aarch64" not in content
    assert "x86_64" not in content


def test_debian_package_common_removes_local_data_and_build_residue() -> None:
    content = COMMON_SCRIPT.read_text(encoding="utf-8")
    assert "-name venv" in content
    assert "-name .git" in content
    assert "-name .ssh" in content
    assert "-name '*.bak'" in content
    assert "-name '*.bak.*'" in content
    assert "-name '*.db'" in content
    assert "-name '*.sqlite3'" in content
    assert "-name '*.xlsx'" in content
    assert "-name '.env'" in content
    assert "realpath -m" in content
    assert "jq -er" in content
    assert "${REPO_ROOT}/build" in content
    assert "${REPO_ROOT}/builds/packages" in content
    assert "default_package_staging_dir" in content
    assert '[[ "${REPO_ROOT}" == /mnt/* ]]' in content
    assert "ssa_consulta_rapida_package" in content
    assert "chmod 700" in content

    assert "clean_release_tree" in DEB_ENGINE_SCRIPT.read_text(encoding="utf-8")
    assert "clean_release_tree" in APPIMAGE_ENGINE_SCRIPT.read_text(encoding="utf-8")
