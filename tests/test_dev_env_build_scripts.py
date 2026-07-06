from __future__ import annotations

import importlib.util

import pytest

from launchers.build_complete import _get_project_root
from tests.release_script_assertions import section_between


PROJECT_ROOT = _get_project_root()


def _load_version_info_from_root(tmp_path):
    module_path = tmp_path / "launchers" / "version_info.py"
    module_path.parent.mkdir(parents=True)
    module_path.write_text(
        (PROJECT_ROOT / "launchers" / "version_info.py").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    spec = importlib.util.spec_from_file_location("version_info_probe", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("falha ao carregar version_info de teste")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_launcher_version_info_rejects_invalid_json(tmp_path) -> None:
    module = _load_version_info_from_root(tmp_path)
    version_file = tmp_path / "config" / "version.json"
    version_file.parent.mkdir()
    version_file.write_text("{", encoding="utf-8")

    with pytest.raises(RuntimeError, match="Arquivo de versao invalido"):
        module.get_current_version()


def test_launcher_version_info_explicit_default_handles_invalid_json(tmp_path) -> None:
    module = _load_version_info_from_root(tmp_path)
    version_file = tmp_path / "config" / "version.json"
    version_file.parent.mkdir()
    version_file.write_text("{", encoding="utf-8")

    assert module.get_current_version("dev-local") == "dev-local"


def test_launcher_version_info_uses_explicit_version_fallback(tmp_path) -> None:
    module = _load_version_info_from_root(tmp_path)
    version_file = tmp_path / "config" / "version.json"
    version_file.parent.mkdir()
    version_file.write_text("{}", encoding="utf-8")
    (tmp_path / "VERSION").write_text("4.44", encoding="utf-8")

    assert module.get_current_version() == "4.44"


def test_launcher_version_info_does_not_return_implicit_zero_version(tmp_path) -> None:
    module = _load_version_info_from_root(tmp_path)

    with pytest.raises(RuntimeError, match="Arquivo de versao ausente"):
        module.get_current_version()

    assert module.get_current_version("dev-local") == "dev-local"


def test_bootstrap_uses_apt_get_update_without_invalid_yes_flag() -> None:
    script = (PROJECT_ROOT / "dev_env" / "bootstrap.sh").read_text(encoding="utf-8")

    assert "sudo apt update -y" not in script
    assert "sudo apt-get update" in script
    assert "sudo apt-get install -y" in script


def test_repository_line_ending_policy_covers_build_scripts() -> None:
    attributes = (PROJECT_ROOT / ".gitattributes").read_text(encoding="utf-8")

    assert "*.sh text eol=lf" in attributes
    assert "*.py text eol=lf" in attributes
    assert "*.bzl text eol=lf" in attributes
    assert "*.md text eol=lf" in attributes
    assert "*.bat text eol=crlf" in attributes
    assert "*.ps1 text eol=crlf" in attributes

    for relative_path in (
        "pyoxidizer.bzl",
        "docs/GUIA_DISTRIBUICAO.md",
    ):
        data = (PROJECT_ROOT / relative_path).read_bytes()
        assert b"\r\n" not in data


def test_pyoxidizer_config_defaults_and_paths() -> None:
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
        assert 'PYOXIDIZER_UV_PACKAGE="${SSA_PYOXIDIZER_UV_PACKAGE:-pyoxidizer==0.24.0}"' in script
        assert 'uv tool run --python 3.13 --from "${PYOXIDIZER_UV_PACKAGE}" pyoxidizer --version' in script
        assert '--from pyoxidizer pyoxidizer build' not in script
        assert '--var SSA_PROJECT_ROOT "${REPO_ROOT}"' in script
        assert '--path "${REPO_ROOT}"' in script
        assert 'BUILD_INFO_FILE="${REPO_ROOT}/config/build_info.json"' in script
        assert "cleanup_build_info" in script
        assert 'BUILD_INFO_BACKUP_CANDIDATE="$(mktemp "${BUILD_INFO_FILE}.XXXXXX")"' in script
        assert 'rm -f "${BUILD_INFO_BACKUP_CANDIDATE}"' in script
        assert 'BUILD_INFO_BACKUP="${BUILD_INFO_BACKUP_CANDIDATE}"' in script
        assert "write_build_info.py" in script
        assert "--build-system pyoxidizer" in script
        assert f"--platform {platform}" in script
        assert 'if [[ -z "${APP_VERSION}" ]]; then' in script
        assert 'if [[ ! -s "${BUILD_INFO_FILE}" ]]; then' in script


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
        assert "write_build_info.py" in script
        assert 'if [[ -z "${APP_VERSION}" ]]; then' in script
        assert 'if [[ ! -s "${BUILD_INFO_FILE}" ]]; then' in script
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
    assert "write_build_info.py" in nuitka_script
    assert "--build-system nuitka" in nuitka_script
    assert "--platform windows_amd64" in nuitka_script
    assert "version_short ausente" in nuitka_script
    assert 'if not defined APP_VERSION set "APP_VERSION=0.0"' not in nuitka_script
    assert 'if not defined FILE_VERSION set "FILE_VERSION=0.0.0.0"' not in nuitka_script
    assert 'set "MSVC_LINK="' in pyoxidizer_script
    assert "if not defined MSVC_LINK" in pyoxidizer_script
    assert "where link.exe" in pyoxidizer_script
    assert 'set "PYOXIDIZER_UV_PACKAGE=pyoxidizer==0.24.0"' in pyoxidizer_script
    assert 'uv tool run --python 3.13 --from "%PYOXIDIZER_UV_PACKAGE%" pyoxidizer --version' in pyoxidizer_script
    assert "--from pyoxidizer pyoxidizer build" not in pyoxidizer_script
    assert 'set "APP_VERSION=%%A"' in pyoxidizer_script
    assert "version_short ausente" in pyoxidizer_script
    assert 'if not defined APP_VERSION set "APP_VERSION=0.0"' not in pyoxidizer_script
    assert 'if not defined APP_VERSION_PE set "APP_VERSION_PE=0.0.0.0"' not in pyoxidizer_script
    assert 'set "PYOX_RUNTIME_PYTHON=3.10"' in pyoxidizer_script
    assert "uv run --python %PYOX_RUNTIME_PYTHON%" in pyoxidizer_script
    assert "SSA_PYOXIDIZER_SMOKE_LOG" in pyoxidizer_script
    assert "scripts\\smoke_cli.py" in pyoxidizer_script
    assert "--executable" in pyoxidizer_script
    assert "rcedit.exe" in pyoxidizer_script
    assert "--set-icon" in pyoxidizer_script
    assert "--set-file-version" in pyoxidizer_script
    assert "--set-product-version" in pyoxidizer_script
    assert '--set-version-string "ProductName" "SSA Consulta Rapida"' in pyoxidizer_script
    assert r"config\version.json" in pyoxidizer_script
    assert "build_info.json" in pyoxidizer_script
    assert "write_build_info.py" in pyoxidizer_script
    assert "GUIA_MIGRACAO_NOVA_INSTALACAO.md" in pyoxidizer_script
    assert "--build-system pyoxidizer" in pyoxidizer_script
    assert "--platform windows_amd64" in pyoxidizer_script


def test_pyinstaller_windows_checks_clean_errorlevel() -> None:
    script = (PROJECT_ROOT / "dev_env" / "build" / "build_pyinstaller.bat").read_text(
        encoding="utf-8"
    )

    assert "--platform windows_amd64 --clean" in script
    assert "if errorlevel 1 (" in script
    assert "Limpeza PyInstaller falhou." in script
    clean_block = section_between(
        script,
        "--platform windows_amd64 --clean",
        "--platform windows_amd64 --apps cli gui",
    )
    assert "if errorlevel 1 (" in clean_block


def test_nuitka_windows_cleanup_and_canonical_dist_names() -> None:
    script = (PROJECT_ROOT / "dev_env" / "build" / "build_nuitka_clean.bat").read_text(
        encoding="utf-8"
    )

    assert "gui_entry.dist" in script
    assert "cli_entry.dist" in script
    assert "gui_entry.build" in script
    assert "cli_entry.build" in script
    assert "ren " in script
    assert "gui_entry.dist canonico" in script
    assert "cli_entry.dist canonico" in script


def test_setup_msvc_path_is_session_only_diagnostic() -> None:
    script = (PROJECT_ROOT / "dev_env" / "setup_msvc_path.ps1").read_text(
        encoding="utf-8"
    )

    assert "[switch]$ApplyToCurrentSession" in script
    assert "vswhere.exe" in script
    assert "vcvars64.bat" in script
    assert "Import-VcVarsIntoCurrentSession" in script
    assert "This script does not modify the user PATH" in script
    assert "[Environment]::SetEnvironmentVariable" not in script
    assert 'Set-Item -Path "Env:$name"' in script


def test_windows_launchers_use_repo_relative_paths_and_distinct_modes() -> None:
    cli_cmd = (PROJECT_ROOT / "launchers" / "SSA_Consulta_Rapida_3.10_CLI.cmd").read_text(
        encoding="utf-8"
    )
    gui_cmd = (PROJECT_ROOT / "launchers" / "SSA_Consulta_Rapida_3.10_GUI.cmd").read_text(
        encoding="utf-8"
    )
    package_cli = (
        PROJECT_ROOT / "launchers" / "launcher_ssa_consulta_rapida_cli.bat"
    ).read_text(encoding="utf-8")
    package_gui = (
        PROJECT_ROOT / "launchers" / "launcher_ssa_consulta_rapida_gui.bat"
    ).read_text(encoding="utf-8")

    for script in (cli_cmd, gui_cmd, package_cli, package_gui):
        assert "C:\\Users\\menon" not in script
        assert 'for %%I in ("%~dp0..") do set "ROOT=%%~fI"' in script

    assert '"%PYEXE%" main.py %*' in cli_cmd
    assert "--gui" not in cli_cmd
    assert '"%PYEXE%" main.py --gui %*' in gui_cmd
    assert '"%EXE%" %*' in package_cli
    assert "--gui" not in package_cli
    assert 'start "PyInstaller GUI" "%EXE%" --gui %*' in package_gui
    assert "builds\\pyinstaller\\windows_amd64\\SSA_Consulta_Rapida.exe" in package_cli
    assert "builds\\pyinstaller\\windows_amd64\\SSA_Consulta_Rapida.exe" in package_gui


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
