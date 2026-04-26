from __future__ import annotations

from launchers.build_complete import _get_project_root


PROJECT_ROOT = _get_project_root()


def test_bootstrap_uses_apt_get_update_without_invalid_yes_flag() -> None:
    script = (PROJECT_ROOT / "dev_env" / "bootstrap.sh").read_text(encoding="utf-8")

    assert "sudo apt update -y" not in script
    assert "sudo apt-get update" in script
    assert "sudo apt-get install -y" in script


def test_pyoxidizer_default_project_root_uses_empty_strip_prefix() -> None:
    root_config = PROJECT_ROOT / "pyoxidizer.bzl"
    build_config = PROJECT_ROOT / "dev_env" / "build" / "pyoxidizer.bzl"

    root_text = root_config.read_text(encoding="utf-8")
    build_text = build_config.read_text(encoding="utf-8")

    assert root_text == build_text
    assert 'PROJECT_ROOT in ("", ".")' in root_text
    assert '""\n    if PROJECT_ROOT in ("", ".")' in root_text
    assert 'strip_prefix=PROJECT_PREFIX' in root_text


def test_pyoxidizer_debian_uses_root_config_kept_in_sync() -> None:
    script = (PROJECT_ROOT / "dev_env" / "build" / "build_pyoxidizer_debian.sh").read_text(
        encoding="utf-8"
    )
    assert 'PYOX_CONFIG="${REPO_ROOT}/pyoxidizer.bzl"' in script
    assert '--var SSA_PROJECT_ROOT "${REPO_ROOT}"' in script
    assert '--path "${REPO_ROOT}"' in script


def test_nuitka_debian_serializes_patchelf_install() -> None:
    script = (PROJECT_ROOT / "dev_env" / "build" / "build_nuitka_debian.sh").read_text(
        encoding="utf-8"
    )

    assert 'APT_LOCK_FILE="${TMPDIR:-/tmp}/ssa_build_locks/patchelf_install.lock"' in script
    assert 'exec 9>"${APT_LOCK_FILE}"' in script
    assert "flock 9" in script
    assert script.count("if ! command -v patchelf >/dev/null 2>&1; then") >= 2
