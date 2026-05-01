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

    root_text = root_config.read_text(encoding="utf-8")

    assert not (PROJECT_ROOT / "dev_env" / "build" / "pyoxidizer.bzl").exists()
    assert 'PROJECT_ROOT in ("", ".")' in root_text
    assert '""\n    if PROJECT_ROOT in ("", ".")' in root_text
    assert 'strip_prefix=PROJECT_PREFIX' in root_text
    assert '"launchers/platforms/**/venv/**"' in root_text
    assert '"launchers/platforms/**/temp/**"' in root_text
    assert '"launchers/dist/**"' in root_text
    assert '"docs/GUIA_MIGRACAO_NOVA_INSTALACAO.md"' in root_text
    assert '"config/build_info.json"' in root_text


def test_pyoxidizer_config_embeds_app_code_without_filesystem_python_sources() -> None:
    root_config = PROJECT_ROOT / "pyoxidizer.bzl"

    root_text = root_config.read_text(encoding="utf-8")

    assert 'policy.resources_location = "in-memory"' in root_text
    assert 'policy.resources_location_fallback = "filesystem-relative:lib"' in root_text
    assert "python_config.oxidized_importer = True" in root_text
    assert "python_config.filesystem_importer = False" in root_text
    assert "exe.read_package_root(" in root_text
    assert '"core"' in root_text
    assert '"main"' in root_text
    assert '"core/*.py"' not in root_text
    assert '"main.py"' not in root_text


def test_pyoxidizer_debian_uses_root_config_kept_in_sync() -> None:
    for platform, script_name in (
        ("debian_amd64", "build_pyoxidizer_debian.sh"),
        ("debian_arm64", "build_pyoxidizer_debian_arm64.sh"),
    ):
        script = (PROJECT_ROOT / "dev_env" / "build" / script_name).read_text(
            encoding="utf-8"
        )
        assert 'PYOX_CONFIG="${REPO_ROOT}/pyoxidizer.bzl"' in script
        assert '--var SSA_PROJECT_ROOT "${REPO_ROOT}"' in script
        assert '--path "${REPO_ROOT}"' in script
        assert 'BUILD_INFO_FILE="${REPO_ROOT}/config/build_info.json"' in script
        assert "cleanup_build_info" in script
        assert f'"pyoxidizer" "{platform}"' in script


def test_nuitka_debian_serializes_patchelf_install() -> None:
    script = (PROJECT_ROOT / "dev_env" / "build" / "build_nuitka_debian.sh").read_text(
        encoding="utf-8"
    )

    assert 'APT_LOCK_DIR="${XDG_CACHE_HOME:-${HOME}/.cache}/ssa_consulta_rapida/build_locks"' in script
    assert 'APT_LOCK_FILE="${APT_LOCK_DIR}/patchelf_install.lock"' in script
    assert 'exec 9>"${APT_LOCK_FILE}"' in script
    assert "flock 9" in script
    assert script.count("if ! command -v patchelf >/dev/null 2>&1; then") >= 2


def test_nuitka_debian_uses_platform_venv_and_requirements() -> None:
    for platform, script_name in (
        ("debian_amd64", "build_nuitka_debian.sh"),
        ("debian_arm64", "build_nuitka_debian_arm64.sh"),
    ):
        script = (PROJECT_ROOT / "dev_env" / "build" / script_name).read_text(
            encoding="utf-8"
        )

        assert f'VENV_DIR="${{REPO_ROOT}}/launchers/platforms/{platform}/venv"' in script
        assert f'REQUIREMENTS_FILE="${{REPO_ROOT}}/launchers/platforms/{platform}/requirements.txt"' in script
        assert 'uv venv --python 3.13 "${VENV_DIR}"' in script
        assert 'uv pip install --python "${PYTHON_EXE}" -r "${REQUIREMENTS_FILE}"' in script
        assert '"${PYTHON_EXE}" -m nuitka' in script
        assert '--include-data-file=docs/GUIA_MIGRACAO_NOVA_INSTALACAO.md=docs/GUIA_MIGRACAO_NOVA_INSTALACAO.md' in script
        assert script.count('--include-data-file=docs/GUIA_MIGRACAO_NOVA_INSTALACAO.md=docs/GUIA_MIGRACAO_NOVA_INSTALACAO.md') >= 2
        assert '--include-data-file="${BUILD_INFO_FILE}=config/build_info.json"' in script
        assert 'NUITKA_OUTPUT_DIR=' in script
        assert 'trap cleanup_build_work_dir EXIT' in script
        assert 'SSA_NUITKA_WORK_ROOT' in script
        assert 'mktemp -d "${TMPDIR:-/tmp}/ssa_nuitka_' in script
        assert "ssa_nuitka_build" not in script


def test_nuitka_windows_and_pyoxidizer_stage_include_docs_and_build_info() -> None:
    nuitka_script = (PROJECT_ROOT / "dev_env" / "build" / "build_nuitka_clean.bat").read_text(
        encoding="utf-8"
    )
    pyoxidizer_script = (PROJECT_ROOT / "dev_env" / "build" / "build_pyoxidizer.bat").read_text(
        encoding="utf-8"
    )

    assert "--include-data-file=docs/GUIA_MIGRACAO_NOVA_INSTALACAO.md=docs/GUIA_MIGRACAO_NOVA_INSTALACAO.md" in nuitka_script
    assert "--include-data-file=%BUILD_INFO_FILE%=config/build_info.json" in nuitka_script
    assert "--format=%%cI" in nuitka_script
    assert "--format=%%s" in nuitka_script
    assert 'set "MSVC_LINK="' in pyoxidizer_script
    assert "if not defined MSVC_LINK" in pyoxidizer_script
    assert "where link.exe" in pyoxidizer_script
    assert 'set "APP_VERSION=%%A"' in pyoxidizer_script
    assert 'set "PYOX_RUNTIME_PYTHON=3.10"' in pyoxidizer_script
    assert "uv run --python %PYOX_RUNTIME_PYTHON%" in pyoxidizer_script
    assert "SSA_PYOXIDIZER_SMOKE_LOG" in pyoxidizer_script
    assert "Falha critica nas importacoes" in pyoxidizer_script
    assert "Error importing numpy" in pyoxidizer_script
    assert "rcedit.exe" in pyoxidizer_script
    assert "--set-icon" in pyoxidizer_script
    assert "--set-file-version" in pyoxidizer_script
    assert "--set-product-version" in pyoxidizer_script
    assert '--set-version-string "ProductName" "SSA Consulta Rapida"' in pyoxidizer_script
    assert r"config\version.json" in pyoxidizer_script
    assert "build_info.json" in pyoxidizer_script
    assert "GUIA_MIGRACAO_NOVA_INSTALACAO.md" in pyoxidizer_script
    assert "--format=%%cI" in pyoxidizer_script
    assert "--format=%%s" in pyoxidizer_script


def test_pyoxidizer_debian_runtime_includes_version_json() -> None:
    for script_name in (
        "build_pyoxidizer_debian.sh",
        "build_pyoxidizer_debian_arm64.sh",
    ):
        script = (PROJECT_ROOT / "dev_env" / "build" / script_name).read_text(
            encoding="utf-8"
        )
        assert 'VERSION_FILE="${REPO_ROOT}/config/version.json"' in script
        assert 'mkdir -p "${TARGET_BUILD_DIR}/config"' in script
        assert 'cp -f "${VERSION_FILE}" "${TARGET_BUILD_DIR}/config/version.json"' in script
