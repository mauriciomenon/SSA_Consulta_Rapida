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


def test_bootstrap_and_build_never_fall_back_below_minimum_python() -> None:
    """MEM-15: requires-python >=3.11; o fallback nao pode escolher 3.10."""
    import tomllib

    minimum = tomllib.loads((PROJECT_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    assert minimum["project"]["requires-python"] == ">=3.11"
    sh = (PROJECT_ROOT / "dev_env" / "bootstrap.sh").read_text(encoding="utf-8")
    ps1 = (PROJECT_ROOT / "dev_env" / "bootstrap.ps1").read_text(encoding="utf-8")
    builder = (PROJECT_ROOT / "launchers" / "build_multiplatform.py").read_text(encoding="utf-8")
    assert "for MAJOR in 3.13 3.12 3.11; do" in sh
    assert "@('3.13', '3.12', '3.11')" in ps1
    assert builder.count('"3.13", "3.12", "3.11")') == 1
    assert builder.count('"3.13", "3.12", "3.11"]') == 1
    for text in (sh, ps1, builder):
        assert "3.10" not in text


def test_repository_line_ending_policy_covers_build_scripts() -> None:
    attributes = (PROJECT_ROOT / ".gitattributes").read_text(encoding="utf-8")

    assert "*.sh text eol=lf" in attributes
    assert "*.py text eol=lf" in attributes
    assert "*.bzl text eol=lf" in attributes
    assert "*.md text eol=lf" in attributes
    assert "*.bat text eol=crlf" in attributes
    assert "*.ps1 text eol=crlf" in attributes

    for relative_path in ("docs/GUIA_DISTRIBUICAO.md",):
        data = (PROJECT_ROOT / relative_path).read_bytes()
        assert b"\r\n" not in data


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
    for script_name in ("build_nuitka_debian.sh",):
        script = (PROJECT_ROOT / "dev_env" / "build" / script_name).read_text(
            encoding="utf-8"
        )

        assert 'VENV_DIR="${REPO_ROOT}/launchers/platforms/${PLATFORM}/venv"' in script
        assert 'REQUIREMENTS_FILE="${REPO_ROOT}/launchers/platforms/${PLATFORM}/requirements.txt"' in script
        assert 'uv venv --python 3.13 "${VENV_DIR}"' in script
        assert 'uv pip install --python "${PYTHON_EXE}" -r "${REQUIREMENTS_FILE}"' in script
        assert '"${PYTHON_EXE}" -m nuitka' in script
        assert "write_build_info.py" in script
        assert 'if [[ -z "${APP_VERSION}" ]]; then' in script
        assert 'if [[ ! -s "${BUILD_INFO_FILE}" ]]; then' in script
        assert '--include-data-file=docs/GUIA_MIGRACAO_NOVA_INSTALACAO.md=docs/GUIA_MIGRACAO_NOVA_INSTALACAO.md' in script
        assert script.count('--include-data-file=docs/GUIA_MIGRACAO_NOVA_INSTALACAO.md=docs/GUIA_MIGRACAO_NOVA_INSTALACAO.md') >= 2
        assert '--include-data-file="${BUILD_INFO_FILE}=config/build_info.json"' in script
        # BL-10: a guarda nativa bloqueia /mnt/* antes; os ramos e o diretorio de trabalho sairam.
        assert "/mnt/" not in script
        assert "SSA_NUITKA_" not in script
        assert "NUITKA_OUTPUT_DIR" not in script
        assert script.count('--output-dir="${FINAL_BUILD_DIR}"') == 2


DEBIAN_BACKENDS = ("pyinstaller", "nuitka")


@pytest.mark.parametrize("backend", DEBIAN_BACKENDS)
def test_debian_build_single_script_for_both_architectures(backend: str) -> None:
    """E-23/BL-31: um script Debian por backend; o arm64 chega por --platform debian_arm64."""
    build_dir = PROJECT_ROOT / "dev_env" / "build"
    assert not (build_dir / f"build_{backend}_debian_arm64.sh").exists()
    helper = (build_dir / "release_debian_arm64_backend.sh").read_text(encoding="utf-8")
    assert f'build_{backend}_debian.sh" --platform debian_arm64 "${{args[@]}}"' in helper
    script = (build_dir / f"build_{backend}_debian.sh").read_text(encoding="utf-8")
    # Nenhum nome de alvo fixo fora do default e da validacao do --platform.
    body = script.split("esac\n", 2)[2]
    assert "debian_amd64" not in body
    assert "debian_arm64" not in body


@pytest.mark.parametrize("backend", DEBIAN_BACKENDS)
@pytest.mark.parametrize("args", [["--platform", "windows_amd64"], ["--platform"]])
def test_debian_build_rejects_unknown_platform_before_building(backend: str, args: list[str]) -> None:
    import shutil
    import subprocess

    bash = shutil.which("bash")
    if bash is None:
        pytest.skip("bash ausente")
    script = PROJECT_ROOT / "dev_env" / "build" / f"build_{backend}_debian.sh"
    result = subprocess.run(
        [bash, str(script), *args], capture_output=True, text=True, timeout=30, check=False
    )
    assert result.returncode == 2, result.stderr
    assert "debian_amd64 ou debian_arm64" in result.stderr


def test_nuitka_debian_clears_previous_dist_once_before_building() -> None:
    """BL-10: o Nuitka grava direto no destino; o .dist anterior sai uma vez, antes do build."""
    remove_dist = 'rm -rf -- "${GUI_DIST}" "${CLI_DIST}"'
    lines = [
        line.strip()
        for line in (PROJECT_ROOT / "dev_env" / "build" / "build_nuitka_debian.sh")
        .read_text(encoding="utf-8")
        .splitlines()
    ]
    first_build = lines.index('LAST_STEP="nuitka_gui"')
    removals = [i for i, line in enumerate(lines) if line == remove_dist]
    assert len(removals) == 1
    assert removals[0] < first_build
    assert not any(line.startswith("cp -a ") for line in lines)


def test_nuitka_windows_includes_docs_and_build_info() -> None:
    nuitka_script = (PROJECT_ROOT / "dev_env" / "build" / "build_nuitka_clean.bat").read_text(
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


def test_pyinstaller_windows_pins_x64_python_for_every_stage() -> None:
    script = (PROJECT_ROOT / "dev_env" / "build" / "build_pyinstaller.bat").read_text(
        encoding="utf-8"
    )

    assert 'set "UV_PYTHON=cpython-3.13-windows-x86_64-none"' in script
    commands = [line.strip() for line in script.splitlines() if line.strip().startswith("uv run ")]
    assert commands
    assert all(
        'uv run --frozen --python "%UV_PYTHON%" ' in command for command in commands
    )


def test_pyinstaller_windows_arm64_build_script_isolated_from_x64() -> None:
    script = (
        PROJECT_ROOT / "dev_env" / "build" / "build_pyinstaller_windows_arm64.bat"
    ).read_text(encoding="utf-8")

    assert "windows_arm64" in script
    assert "--platform windows_arm64 --clean" in script
    assert "--platform windows_arm64 --apps cli gui" in script
    assert "cpython-3.13-windows-x86_64-none" not in script
    assert 'set "UV_PROJECT_ENVIRONMENT=.venv-win-arm64"' in script
    assert 'set "UV_PYTHON=%SSA_WINDOWS_ARM64_PYTHON%"' in script
    assert 'set "UV_MANAGED_PYTHON=false"' in script
    assert script.index("sysconfig.get_platform() == 'win-arm64'") < script.index(
        "--platform windows_arm64 --clean"
    )
    commands = [line.strip() for line in script.splitlines() if line.strip().startswith("uv run ")]
    assert all("--no-sync" in command for command in commands)


def test_pyinstaller_windows_embeds_only_explicit_runtime_database() -> None:
    script = (PROJECT_ROOT / "dev_env" / "build" / "build_pyinstaller.bat").read_text(
        encoding="utf-8"
    )

    assert "--with-runtime-db" in script
    assert '--runtime-db "%REPO_ROOT%\\data\\ssas.db"' in script
    assert "copy_data_to_builds.py" not in script
    assert "--allow-local-data" not in script


def test_nuitka_windows_cleanup_and_canonical_dist_names() -> None:
    script = (PROJECT_ROOT / "dev_env" / "build" / "build_nuitka_clean.bat").read_text(
        encoding="utf-8"
    )
    post_build_block = section_between(
        script,
        'if "%WITH_LOCAL_DATA%"=="1" (',
        "echo Build Nuitka concluido com sucesso.",
    )

    assert "gui_entry.dist" in script
    assert "cli_entry.dist" in script
    assert "gui_entry.build" in script
    assert "cli_entry.build" in script
    assert "ren " in script
    assert (
        'if not exist "%REPO_ROOT%\\builds\\nuitka\\windows_amd64\\gui_entry.dist" '
        'if exist "%REPO_ROOT%\\builds\\nuitka\\windows_amd64\\SSA_GUI_v%APP_VERSION%_windows_amd64.dist"'
        in script
    )
    assert (
        'if not exist "%REPO_ROOT%\\builds\\nuitka\\windows_amd64\\cli_entry.dist" '
        'if exist "%REPO_ROOT%\\builds\\nuitka\\windows_amd64\\SSA_CLI_v%APP_VERSION%_windows_amd64.dist"'
        in script
    )
    assert 'rmdir /s /q "%REPO_ROOT%\\builds\\nuitka\\windows_amd64\\gui_entry.dist"' not in post_build_block
    assert 'rmdir /s /q "%REPO_ROOT%\\builds\\nuitka\\windows_amd64\\cli_entry.dist"' not in post_build_block
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

    for script in (cli_cmd, gui_cmd):
        assert "C:\\Users\\menon" not in script
        assert 'for %%I in ("%~dp0..") do set "ROOT=%%~fI"' in script

    assert '"%PYEXE%" main.py %*' in cli_cmd
    assert "--gui" not in cli_cmd
    assert '"%PYEXE%" main.py --gui %*' in gui_cmd
    # CD-18: launchers .bat do PyInstaller apontavam para um .exe que nenhum build gera.
    for legacy in ("launcher_ssa_consulta_rapida_cli.bat", "launcher_ssa_consulta_rapida_gui.bat"):
        assert not (PROJECT_ROOT / "launchers" / legacy).exists()
