from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
NATIVE_POSIX_ONLY = pytest.mark.skipif(
    sys.platform.startswith("win"),
    reason="POSIX harness intentionally blocks Windows filesystems; use PowerShell",
)


def _test_env(**overrides: str) -> dict[str, str]:
    env = os.environ.copy()
    env.update(overrides)
    return env


def _read_repo_text(*parts: str) -> str:
    return (PROJECT_ROOT.joinpath(*parts)).read_text(encoding="utf-8")


def test_key_shell_scripts_parse_with_available_bash() -> None:
    bash = shutil.which("bash")
    assert bash is not None, "bash must be available for shell contract tests"

    scripts = [
        "scripts/env/direnv_common.sh",
        "scripts/shell_doctor.sh",
        "scripts/ci_quality_gates.sh",
        "scripts/run_tests.sh",
        "scripts/git_hooks/pre-commit.secret-scan.sh",
        "scripts/security/scan_secrets.sh",
        "dev_env/build/release_debian_arm64.sh",
        "dev_env/build/release_debian_arm64_backend.sh",
        "dev_env/build/package_debian_arm64_tar.sh",
    ]
    for script in scripts:
        script_path = PROJECT_ROOT / script
        assert script_path.exists(), f"Script not found: {script_path}"
        result = subprocess.run(
            [bash, "-n", str(script_path)],
            cwd=PROJECT_ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        assert result.returncode == 0, (
            f"{script} failed bash -n with {bash}\n"
            f"stdout={result.stdout}\nstderr={result.stderr}"
        )


def test_bash_regex_guards_are_windows_git_bash_compatible() -> None:
    direnv_common = _read_repo_text("scripts", "env", "direnv_common.sh")
    direnv_common_ps1 = _read_repo_text("scripts", "env", "direnv_common.ps1")
    shell_doctor = _read_repo_text("scripts", "shell_doctor.sh")

    assert '[[ "${SSA_ENV__FILE_VERSION}" =~ ^[0-9]+\\.[0-9]+(\\.[0-9]+)?$ ]]' not in direnv_common
    assert "[[ $name =~ (KEY|TOKEN|SECRET|API) ]]" not in shell_doctor
    assert "[[ $name =~ $SENSITIVE_ENV_NAME_RE ]]" not in shell_doctor

    assert "SSA_ENV__PYTHON_VERSION_RE=" in direnv_common
    assert "$pythonVersionPattern = '^\\d+\\.\\d+(\\.\\d+)?$'" in direnv_common_ps1
    assert 'case "$name" in' in shell_doctor


def test_direnv_common_shell_and_powershell_share_stable_version() -> None:
    direnv_common = _read_repo_text("scripts", "env", "direnv_common.sh")
    direnv_common_ps1 = _read_repo_text("scripts", "env", "direnv_common.ps1")

    assert 'SSA_PYTHON_STABLE_VERSION="${SSA_PYTHON_STABLE_VERSION:-3.13.12}"' in direnv_common
    assert 'else { "3.13.12" }' in direnv_common_ps1



ENVIRONMENT_SCRIPTS = (
    "scripts/env/direnv_common.sh",
    "scripts/env/direnv_common.ps1",
    "dev_env/activate_repo.ps1",
    "dev_env/bootstrap.sh",
    "dev_env/bootstrap.ps1",
    "scripts/env/setup_env.sh",
    "scripts/env/setup_env.ps1",
    "dev_env/activate_env.bat",
    "dev_env/setup_pyox_venv.bat",
)


@pytest.mark.parametrize("relative_path", ENVIRONMENT_SCRIPTS)
def test_environment_scripts_do_not_seed_or_invoke_pip(relative_path: str) -> None:
    script = _read_repo_text(*relative_path.split("/"))
    assert "ensurepip" not in script
    assert "--seed" not in script
    assert "ensure_venv_pip" not in script
    assert re.search(r"(?<!uv )\bpip install\b|\b-m pip\b", script) is None
    for line in script.splitlines():
        if "-m venv " in line or "'venv'," in line:
            assert "--without-pip" in line


@pytest.mark.parametrize("extension", ["sh", "ps1"])
def test_environment_installers_sync_selected_environment(extension: str) -> None:
    bootstrap = _read_repo_text("dev_env", f"bootstrap.{extension}")
    setup = _read_repo_text("scripts", "env", f"setup_env.{extension}")
    for script in (bootstrap, setup):
        assert "uv sync --project" in script
        assert "--python" in script
        assert "--frozen" in script
        assert "--inexact" in script
        assert "UV_PROJECT_ENVIRONMENT" in script
        assert "VIRTUAL_ENV" in script
    assert "--no-dev" in bootstrap
    assert "--no-dev" not in setup


@pytest.fixture
def isolated_env_repo(tmp_path: Path) -> tuple[Path, dict[str, str]]:
    uv = shutil.which("uv")
    if uv is None:
        pytest.skip("uv necessario para validar ambiente sem pip")
    repo = tmp_path / "repo"
    env_scripts = repo / "scripts" / "env"
    env_scripts.mkdir(parents=True)
    for name in ("direnv_common.sh", "native_host_guard.sh", "setup_env.sh"):
        shutil.copy2(PROJECT_ROOT / "scripts" / "env" / name, env_scripts / name)
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    fake_uv = fake_bin / "uv"
    fake_uv.write_text(
        "#!/usr/bin/env bash\n"
        'printf "%s\\n" "$*" >> "$SSA_TEST_UV_LOG"\n'
        'if [[ "$1 $2" == "python install" ]]; then exit 1; fi\n'
        'if [[ "$1" == "venv" && "${SSA_TEST_FAIL_UV:-0}" == 1 ]]; then exit 42; fi\n'
        'if [[ "$1" == sync && -n "${SSA_TEST_SYNC_RESULT:-}" ]]; then\n'
        '  printf "%s\\n" "$UV_PROJECT_ENVIRONMENT" >> "$SSA_TEST_UV_LOG"\n'
        '  exit "$SSA_TEST_SYNC_RESULT"\n'
        'fi\n'
        'exec "$SSA_TEST_UV" "$@"\n',
        encoding="utf-8",
    )
    fake_uv.chmod(0o755)
    env = _test_env(
        PATH=f"{fake_bin}{os.pathsep}{os.environ['PATH']}",
        SSA_TEST_UV=uv,
        SSA_TEST_UV_LOG=str(tmp_path / "uv.log"),
        SSA_SKIP_PYENV="1",
        SSA_PYTHON_STABLE_VERSION=f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
        UV_OFFLINE="1",
        UV_PYTHON_DOWNLOADS="never",
    )
    for name in (
        "SSA_ENV_COMMON_SOURCED", "SSA_ENV_PYENV_INITIALIZED", "SSA_PYTHON_VARIANT",
        "SSA_USE_FREE_THREADED", "SSA_SKIP_UV", "SSA_VENV_DIR_OVERRIDE",
        "UV_PROJECT_ENVIRONMENT", "UV_PYTHON", "VIRTUAL_ENV",
    ):
        env.pop(name, None)
    return repo, env


@NATIVE_POSIX_ONLY
@pytest.mark.parametrize("existing", [False, True])
@pytest.mark.parametrize("fallback", [False, True])
def test_environment_activation_keeps_pip_absent(
    isolated_env_repo: tuple[Path, dict[str, str]], existing: bool, fallback: bool
) -> None:
    repo, env = isolated_env_repo
    if existing:
        subprocess.run(
            [env["SSA_TEST_UV"], "venv", "--python", sys.executable, str(repo / ".venv")],
            check=True, capture_output=True, text=True, env=env,
        )
        (repo / ".venv" / "preserved.txt").write_text("preservado", encoding="utf-8")
    if fallback:
        env["SSA_SKIP_UV"] = "1"
        env["SSA_ENV_FALLBACK_PYTHON"] = sys.executable
    result = subprocess.run(
        ["bash", "-c", ('source scripts/env/direnv_common.sh && ssa_env::apply manual && '
         'python -c "import importlib.util; assert importlib.util.find_spec(\\\"pip\\\") is None"')],
        cwd=repo, env=env, capture_output=True, text=True, check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert (repo / ".venv" / "bin" / "python").exists()
    if existing:
        assert (repo / ".venv" / "preserved.txt").read_text(encoding="utf-8") == "preservado"
    log = Path(env["SSA_TEST_UV_LOG"])
    calls = log.read_text(encoding="utf-8") if log.exists() else ""
    assert "--seed" not in calls
    if existing:
        assert "venv --python" not in calls


@NATIVE_POSIX_ONLY
@pytest.mark.parametrize("failure", ["incomplete", "version", "uv", "fallback_version"])
def test_environment_activation_rejects_invalid_state(
    isolated_env_repo: tuple[Path, dict[str, str]], failure: str
) -> None:
    repo, env = isolated_env_repo
    if failure == "incomplete":
        (repo / ".venv").mkdir()
    elif failure == "version":
        subprocess.run(
            [env["SSA_TEST_UV"], "venv", "--python", sys.executable, str(repo / ".venv")],
            check=True, capture_output=True, text=True, env=env,
        )
        env["SSA_PYTHON_STABLE_VERSION"] = "0.0.0"
    elif failure == "fallback_version":
        env.update(SSA_PYTHON_STABLE_VERSION="0.0.0", SSA_SKIP_UV="1", SSA_ENV_FALLBACK_PYTHON=sys.executable)
    else:
        env["SSA_TEST_FAIL_UV"] = "1"
    result = subprocess.run(
        ["bash", "-c", "source scripts/env/direnv_common.sh && ssa_env::apply manual"],
        cwd=repo, env=env, capture_output=True, text=True, check=False,
    )
    assert result.returncode != 0
    assert "pip missing" not in result.stdout
    if failure == "uv":
        assert "uv failed to provision" in result.stdout
    elif failure == "version":
        assert "wanted 0.0.0" in result.stdout
    elif failure == "fallback_version":
        assert "esperado 0.0.0" in result.stdout
    else:
        assert "venv incompleta" in result.stderr



@NATIVE_POSIX_ONLY
@pytest.mark.parametrize("sync_result", [0, 42])
def test_environment_setup_syncs_selected_venv_and_propagates_failure(
    isolated_env_repo: tuple[Path, dict[str, str]], sync_result: int
) -> None:
    repo, env = isolated_env_repo
    env["SSA_TEST_SYNC_RESULT"] = str(sync_result)
    (repo / ".python-version").write_text(env["SSA_PYTHON_STABLE_VERSION"] + "\n", encoding="utf-8")
    result = subprocess.run(
        ["bash", "scripts/env/setup_env.sh"],
        cwd=repo, env=env, input="y", capture_output=True, text=True, check=False,
    )
    assert (result.returncode == 0) == (sync_result == 0), result.stdout + result.stderr
    calls = Path(env["SSA_TEST_UV_LOG"]).read_text(encoding="utf-8")
    assert f"sync --project {repo} --python {repo}/.venv/bin/python --frozen --inexact" in calls
    assert calls.endswith(f"{repo}/.venv\n")
    if sync_result:
        assert "Erro ao instalar dependencias com uv." in result.stdout
        assert "Setup conclu" not in result.stdout


@NATIVE_POSIX_ONLY
def test_environment_setup_keeps_stable_version_when_selecting_free_threaded(
    isolated_env_repo: tuple[Path, dict[str, str]],
) -> None:
    repo, env = isolated_env_repo
    env.update(
        SSA_PYTHON_VARIANT="free-threaded",
        SSA_PYTHON_FT_VERSION=env["SSA_PYTHON_STABLE_VERSION"],
        SSA_PYTHON_STABLE_VERSION="3.12.0",
        SSA_TEST_SYNC_RESULT="0",
    )
    (repo / ".python-version").write_text("3.12.0\n", encoding="utf-8")
    result = subprocess.run(
        ["bash", "-c", (
            "source scripts/env/setup_env.sh && "
            "SSA_PYTHON_VARIANT=stable && ssa_env__determine_variant && "
            'printf "STABLE=%s\\n" "$SSA_ENV_PY_VERSION"'
        )],
        cwd=repo, env=env, input="y", capture_output=True, text=True, check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "STABLE=3.12.0" in result.stdout
    assert (repo / ".venv_ft" / "bin" / "python").exists()


def _run_powershell_activation_probe(
    repo: Path, env: dict[str, str], target: str, variant: str = "stable",
) -> subprocess.CompletedProcess[str]:
    pwsh = shutil.which("pwsh")
    if pwsh is None:
        pytest.skip("pwsh necessario para validar provisionamento PowerShell")
    env = env | {
        "SSA_TEST_REPO": str(repo),
        "SSA_TEST_SCRIPT": str(PROJECT_ROOT / "dev_env" / "activate_repo.ps1"),
        "SSA_TEST_TARGET": target,
        "SSA_TEST_VARIANT": variant,
    }
    # Executa os blocos reais de provisionamento sem o guard exclusivo do Windows.
    command = r"""
$ErrorActionPreference = 'Stop'
$repoRoot = $env:SSA_TEST_REPO
$targetVersion = $env:SSA_TEST_TARGET
$variant = $env:SSA_TEST_VARIANT
$venvDir = if ($variant -eq 'free-threaded') { '.venv_ft' } else { '.venv' }
$envSource = $null
$ast = [Management.Automation.Language.Parser]::ParseFile($env:SSA_TEST_SCRIPT, [ref]$null, [ref]$null)
foreach ($statement in $ast.EndBlock.Statements) {
    if (($statement -is [Management.Automation.Language.FunctionDefinitionAst] -and $statement.Name -eq 'Write-EnvLog') -or
        ($statement -is [Management.Automation.Language.IfStatementAst] -and
            $statement.Clauses[0].Item1.Extent.Text -in @(
                '-not $envSource', '$variant -eq ''free-threaded''', '$envSource -like ''venv:*'''))) {
        . ([scriptblock]::Create($statement.Extent.Text))
    }
}
Write-Output "SOURCE=$envSource"
"""
    return subprocess.run(
        [pwsh, "-NoProfile", "-Command", command],
        cwd=repo, env=env, capture_output=True, text=True, check=False,
    )


@NATIVE_POSIX_ONLY
@pytest.mark.parametrize("target,variant,requested", [
    ("3.13.12", "stable", "3.13.12"),
    ("3.14-dev", "free-threaded", "3.14+freethreaded"),
    ("3.14.2t", "free-threaded", "3.14.2+freethreaded"),
])
def test_powershell_activation_requests_target_and_propagates_uv_failure(
    isolated_env_repo: tuple[Path, dict[str, str]], target: str, variant: str, requested: str,
) -> None:
    repo, env = isolated_env_repo
    env["SSA_TEST_FAIL_UV"] = "1"
    result = _run_powershell_activation_probe(repo, env, target, variant)
    assert result.returncode != 0
    assert "Falha ao criar" in result.stderr
    calls = Path(env["SSA_TEST_UV_LOG"]).read_text(encoding="utf-8").splitlines()
    venv_dir = ".venv_ft" if variant == "free-threaded" else ".venv"
    assert calls == [f"venv --python {requested} {repo / venv_dir}"]
    assert not (repo / venv_dir).exists()


@NATIVE_POSIX_ONLY
@pytest.mark.parametrize("failure", [None, "version", "ft_version", "free-threaded"])
def test_powershell_activation_validates_existing_interpreter_without_recreating(
    isolated_env_repo: tuple[Path, dict[str, str]], failure: str | None,
) -> None:
    repo, env = isolated_env_repo
    variant = "free-threaded" if failure in ("ft_version", "free-threaded") else "stable"
    venv_dir = ".venv_ft" if variant == "free-threaded" else ".venv"
    scripts = repo / venv_dir / "Scripts"
    scripts.mkdir(parents=True)
    (scripts / "python.exe").symlink_to(sys.executable)
    (scripts / "Activate.ps1").write_text(
        "Set-Content -LiteralPath (Join-Path $env:SSA_TEST_REPO 'activated.txt') -Value '1'\n",
        encoding="utf-8",
    )
    target = "0.0.0" if failure == "version" else env["SSA_PYTHON_STABLE_VERSION"]
    if failure == "ft_version":
        target = "0.0.0t"
    result = _run_powershell_activation_probe(repo, env, target, variant)
    assert (result.returncode == 0) == (failure is None), result.stdout + result.stderr
    if failure in ("version", "ft_version"):
        assert "Versao Python invalida" in result.stderr
    elif failure == "free-threaded":
        assert "nao e uma build free-threaded" in result.stderr
    else:
        assert "SOURCE=venv:.venv" in result.stdout
    assert (repo / "activated.txt").exists() == (failure is None)
    assert not Path(env["SSA_TEST_UV_LOG"]).exists()


def test_powershell_setup_keeps_stable_version_when_selecting_free_threaded() -> None:
    pwsh = shutil.which("pwsh")
    if pwsh is None:
        pytest.skip("pwsh necessario para validar selecao PowerShell")
    env = _test_env(SSA_TEST_SETUP=str(PROJECT_ROOT / "scripts" / "env" / "setup_env.ps1"))
    command = r"""
$ErrorActionPreference = 'Stop'
$Variant = 'free-threaded'
$pythonVersion = '3.14-dev'
$env:SSA_PYTHON_STABLE_VERSION = '3.13.12'
$ast = [Management.Automation.Language.Parser]::ParseFile($env:SSA_TEST_SETUP, [ref]$null, [ref]$null)
$installBlock = $ast.EndBlock.Statements | Where-Object {
    $_ -is [Management.Automation.Language.IfStatementAst] -and $_.Clauses[0].Item1.Extent.Text.StartsWith('$install -eq')
}
foreach ($statement in $installBlock.Clauses[0].Item2.Statements) {
    if ($statement -is [Management.Automation.Language.PipelineAst] -and
        $statement.PipelineElements[0].InvocationOperator -eq [Management.Automation.Language.TokenKind]::Dot) { break }
    . ([scriptblock]::Create($statement.Extent.Text))
}
@($env:SSA_PYTHON_STABLE_VERSION, $env:SSA_PYTHON_FT_VERSION) | ConvertTo-Json -Compress
"""
    result = subprocess.run(
        [pwsh, "-NoProfile", "-Command", command],
        env=env, capture_output=True, text=True, check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert json.loads(result.stdout) == ["3.13.12", "3.14-dev"]


@NATIVE_POSIX_ONLY
def test_environment_setup_rejects_missing_uv(isolated_env_repo: tuple[Path, dict[str, str]]) -> None:
    repo, env = isolated_env_repo
    bin_dir = Path(env["PATH"].split(os.pathsep)[0])
    (bin_dir / "uv").unlink()
    for command in ("bash", "dirname", "tr"):
        executable = shutil.which(command)
        assert executable is not None
        (bin_dir / command).symlink_to(executable)
    env["PATH"] = str(bin_dir)
    result = subprocess.run(
        ["bash", "scripts/env/setup_env.sh"],
        cwd=repo, env=env, input="y", capture_output=True, text=True, check=False,
    )
    assert result.returncode != 0
    assert "ferramenta ausente ou nao executavel: uv" in result.stderr
    assert not (repo / ".venv").exists()

@NATIVE_POSIX_ONLY
@pytest.mark.parametrize("backend,option", [("python -m venv", "--without-pip"), ("virtualenv 20.0", "--no-pip")])
def test_pyenv_creation_disables_pip_for_selected_backend(
    isolated_env_repo: tuple[Path, dict[str, str]], backend: str, option: str
) -> None:
    repo, env = isolated_env_repo
    fake_pyenv = Path(env["PATH"].split(os.pathsep)[0]) / "pyenv"
    fake_pyenv.write_text(
        "#!/usr/bin/env bash\n"
        'printf "%s\\n" "$*" >> "$SSA_TEST_PYENV_LOG"\n'
        'case "$1 $2" in\n'
        '  "versions --bare") printf "%s\\n" "$SSA_PYTHON_STABLE_VERSION" ;;\n'
        '  "virtualenv --version") printf "pyenv-virtualenv 1.2.4 (%s)\\n" "$SSA_TEST_BACKEND" ;;\n'
        'esac\n',
        encoding="utf-8",
    )
    fake_pyenv.chmod(0o755)
    env.update(SSA_TEST_PYENV_LOG=str(repo / "pyenv.log"), SSA_TEST_BACKEND=backend)
    result = subprocess.run(
        ["bash", "-c", ("source scripts/env/direnv_common.sh && ssa_env__determine_variant && "
         "SSA_ENV_PYENV_AVAILABLE=1 && SSA_ENV_PYENV_HAS_VIRTUALENV=1 && ssa_env__ensure_pyenv_env")],
        cwd=repo, env=env, capture_output=True, text=True, check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert f"virtualenv {option} " in (repo / "pyenv.log").read_text(encoding="utf-8")

def test_windows_activation_avoids_dynamic_eval_and_silent_catches() -> None:
    activate_repo = _read_repo_text("dev_env", "activate_repo.ps1")
    direnv_common = _read_repo_text("scripts", "env", "direnv_common.ps1")

    assert "Invoke-Expression" not in activate_repo
    assert "pyenv init -" not in activate_repo
    assert "pyenv virtualenv-init -" not in activate_repo
    silent_catch = re.compile(r"catch\s*\{\s*(?:#[^\r\n]*\s*)?\}", re.MULTILINE)
    assert silent_catch.search(activate_repo) is None
    assert silent_catch.search(direnv_common) is None


def test_ci_quality_gates_does_not_expand_arg_string_unquoted() -> None:
    script = _read_repo_text("scripts", "ci_quality_gates.sh")

    assert "run_quality_gates.py $GATES_ARGS" not in script
    assert "read -r -a GATES_ARGS_ARRAY" not in script
    assert "shlex.split" in script
    assert "eval" not in script
    assert '"${GATES_ARGS_ARRAY[@]}"' in script


@NATIVE_POSIX_ONLY
def test_ci_quality_gates_parses_gate_args_with_quotes(tmp_path: Path) -> None:
    bash = shutil.which("bash")
    assert bash is not None, "bash must be available for shell contract tests"

    capture = tmp_path / "argv.txt"
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    fake_python = fake_bin / "python"
    fake_python.write_text(
        "#!/usr/bin/env bash\n"
        "set -euo pipefail\n"
        "if [[ \"${1:-}\" == \"-c\" ]]; then\n"
        "  exec \"$REAL_PYTHON\" \"$@\"\n"
        "fi\n"
        "if [[ \"${1:-}\" == \"scripts/run_quality_gates.py\" ]]; then\n"
        "  printf '%s\\n' \"${@:2}\" > \"$QUALITY_GATES_CAPTURE\"\n"
        "  printf '{\"overall_status\":\"ok\"}\\n'\n"
        "  exit 0\n"
        "fi\n"
        "if [[ \"${1:-}\" == \"-m\" && \"${2:-}\" == \"pytest\" ]]; then\n"
        "  exit 0\n"
        "fi\n"
        "printf 'unexpected python invocation: %s\\n' \"$*\" >&2\n"
        "exit 99\n",
        encoding="utf-8",
    )
    fake_python.chmod(0o755)

    result = subprocess.run(
        [bash, str(PROJECT_ROOT / "scripts" / "ci_quality_gates.sh")],
        cwd=PROJECT_ROOT,
        text=True,
        capture_output=True,
        check=False,
        env=_test_env(
            PATH=f"{fake_bin}{os.pathsep}{os.environ['PATH']}",
            GATES_ARGS='--skip "check docs" --label "cache manager"',
            REAL_PYTHON=sys.executable,
            QUALITY_GATES_CAPTURE=str(capture),
            QUALITY_GATES_JSONL=str(tmp_path / "quality_gates_output.jsonl"),
        ),
    )

    assert result.returncode == 0, result.stderr
    assert capture.read_text(encoding="utf-8").splitlines() == [
        "--skip",
        "check docs",
        "--label",
        "cache manager",
    ]


@NATIVE_POSIX_ONLY
def test_run_tests_parses_pytest_addopts_with_quotes(tmp_path: Path) -> None:
    bash = shutil.which("bash")
    assert bash is not None, "bash must be available for shell contract tests"

    capture = tmp_path / "argv.txt"
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    fake_python = fake_bin / "python"
    fake_python.write_text(
        "#!/usr/bin/env bash\n"
        "set -euo pipefail\n"
        "if [[ \"${1:-}\" == \"-\" ]]; then\n"
        "  exec \"$REAL_PYTHON\" \"$@\"\n"
        "fi\n"
        "printf '%s\\n' \"$@\" > \"$RUN_TESTS_CAPTURE\"\n",
        encoding="utf-8",
    )
    fake_python.chmod(0o755)

    result = subprocess.run(
        [bash, str(PROJECT_ROOT / "scripts" / "run_tests.sh"), "quiet"],
        cwd=PROJECT_ROOT,
        text=True,
        capture_output=True,
        check=False,
        env=_test_env(
            PATH=f"{fake_bin}{os.pathsep}{os.environ['PATH']}",
            PYTEST_ADDOPTS='--collect-only -k "cache manager"',
            REAL_PYTHON=sys.executable,
            RUN_TESTS_CAPTURE=str(capture),
        ),
    )

    assert result.returncode == 0, result.stderr
    assert capture.read_text(encoding="utf-8").splitlines() == [
        "-m",
        "pytest",
        "--cache-clear",
        "-q",
        "--collect-only",
        "-k",
        "cache manager",
    ]


def test_run_tests_does_not_expand_pytest_addopts_unquoted() -> None:
    script = _read_repo_text("scripts", "run_tests.sh")

    assert '"${base_cmd[@]}" ${PYTEST_ADDOPTS:-}' not in script
    assert "shlex.split" in script
    assert '"${base_cmd[@]}" "${pytest_extra_opts[@]}"' in script


def test_secret_scan_hook_loop_safety_and_log_hygiene() -> None:
    script = _read_repo_text("scripts", "git_hooks", "pre-commit.secret-scan.sh")

    assert "echo \"$ADDED\" | sed" not in script
    assert "echo \"$ADDED_STRIPPED\" | grep" not in script
    assert "printf '%s\\n' \"$ADDED_STRIPPED\" | grep" in script
    assert "cut -c2-" in script
    assert "API_KEY_LINES=" in script
    assert "done <<< \"$API_KEY_LINES\"" in script
    assert ": $line" not in script
    assert "Valor potencial de API_KEY (redacted)" in script


def test_minimal_ci_runs_for_any_workflow_change() -> None:
    workflow = _read_repo_text(".github", "workflows", "minimal-ci.yml")

    assert "paths:" not in workflow
    assert "Detect quality gate scope" in workflow
    assert "run_python=false" in workflow
    assert "required status will pass without expensive gates" in workflow
    assert "|^scripts/|^dev_env/build/" in workflow


def test_minimal_ci_isolates_gui_other_pytest_files() -> None:
    workflow = _read_repo_text(".github", "workflows", "minimal-ci.yml")

    assert 'if [ "${PYTEST_GROUP}" = "gui-other" ]; then' in workflow
    assert 'for target in "${targets[@]}"; do' in workflow
    assert (
        'pytest -q --timeout=45 --timeout-method=thread '
        '--durations=20 --durations-min=1 "${target}"'
    ) in workflow
    assert (
        'uv run --python 3.13 pytest -q --timeout=45 --timeout-method=thread '
        '--durations=20 --durations-min=1 "${target}"'
    ) in workflow
    assert (
        'pytest -q --timeout=45 --timeout-method=thread '
        '--durations=20 --durations-min=1 "${targets[@]}"'
    ) in workflow
    assert (
        'uv run --python 3.13 pytest -q --timeout=45 --timeout-method=thread '
        '--durations=20 --durations-min=1 "${targets[@]}"'
    ) in workflow


def test_dependabot_ignores_platform_requirement_snapshots() -> None:
    config = _read_repo_text(".github", "dependabot.yml")
    template = _read_repo_text(".github", "dependabot-template.yml")

    assert config == template
    pip_blocks = re.findall(
        r"(?ms)^\s*-\s*package-ecosystem:\s*['\"]?pip['\"]?\s*$"
        r".*?(?=^\s*-\s*package-ecosystem:|\Z)",
        config,
    )
    root_pip_blocks = [
        block
        for block in pip_blocks
        if re.search(r"(?m)^\s*directory:\s*['\"]?/['\"]?\s*$", block)
    ]
    assert root_pip_blocks, "No root pip Dependabot update found"
    for block in root_pip_blocks:
        assert re.search(
            r"(?ms)^\s*exclude-paths:\s*$"
            r"(?:(?!^\s*[A-Za-z0-9_-]+:).)*"
            r"^\s*-\s*['\"]?launchers/platforms/\*\*['\"]?\s*$",
            block,
        ), (
            "Missing launchers/platforms/** in root pip Dependabot exclude-paths"
        )


def test_secret_scan_uses_quoted_env_for_pr_base_ref() -> None:
    workflow = _read_repo_text(".github", "workflows", "secret_scan.yml")

    assert "git fetch origin ${{ github.base_ref }}" not in workflow
    assert "origin/${{ github.base_ref }}" not in workflow
    assert "BASE_REF: ${{ github.base_ref }}" not in workflow
    assert "BASE_SHA: ${{ github.event.pull_request.base.sha }}" in workflow
    assert 'bash "${{ steps.secret_scanner.outputs.script }}" pr-diff "$BASE_SHA"' in workflow
    assert 'git archive "$BASE_SHA" scripts/security/scan_secrets.sh' in workflow
    assert 'git fetch origin "$BASE_REF" --depth=1' not in workflow
    assert 'git fetch origin "$BASE_REF" || true' not in workflow
    assert 'git diff --unified=0 "origin/${BASE_REF}...HEAD"' not in workflow


def test_dev_bootstrap_requires_hash_for_remote_pyenv_install() -> None:
    script = _read_repo_text("dev_env", "bootstrap.ps1")

    assert "[string]$PyenvInstallerSha256" in script
    assert "[string]::IsNullOrWhiteSpace($InstallerSha256)" in script
    assert "Instalacao remota do pyenv-win exige -PyenvInstallerSha256" in script
    assert "Get-FileHash -Algorithm SHA256" in script
    assert "Unblock-File -LiteralPath $installerPath" in script
    assert "[Net.SecurityProtocolType]::Tls12" in script
    assert "Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser" not in script
    assert "-ExecutionPolicy Bypass -File $installerPath" in script
    assert "Invoke-Expression" not in script


def test_setup_env_scripts_require_explicit_verified_remote_pyenv_install() -> None:
    shell_script = _read_repo_text("scripts", "env", "setup_env.sh")
    powershell_script = _read_repo_text("scripts", "env", "setup_env.ps1")

    assert "curl https://pyenv.run | bash" not in shell_script
    assert "wget -O- https://pyenv.run | bash" not in shell_script
    assert "SSA_ALLOW_REMOTE_PYENV_INSTALL" in shell_script
    assert "SSA_PYENV_INSTALLER_SHA256" in shell_script
    assert "SSA_CONFIRM_REMOVE_PYENV" in shell_script
    assert "sha256sum" in shell_script
    assert "shasum -a 256" in shell_script
    assert "IFS= read -r python_version" in shell_script
    assert "SSA_PYTHON_STABLE_VERSION" in shell_script

    assert "[switch]$AllowRemotePyenvInstall" in powershell_script
    assert "[string]$PyenvInstallerSha256" in powershell_script
    assert "SSA_ALLOW_REMOTE_PYENV_INSTALL" in powershell_script
    assert "SSA_CONFIRM_REMOVE_PYENV" in powershell_script
    assert "Get-FileHash -Algorithm SHA256" in powershell_script
    assert "SSA_PYTHON_STABLE_VERSION" in powershell_script
    assert "& \"$env:TEMP\\install-pyenv-win.ps1\"" not in powershell_script


def test_secret_scan_workspace_and_pr_diff_are_blocking_on_main_and_dev() -> None:
    workflow = _read_repo_text(".github", "workflows", "secret_scan.yml")

    assert "branches: [main, dev]" in workflow
    assert "timeout-minutes: 30" in workflow
    assert workflow.count("continue-on-error: true") == 1
    assert 'bash "${{ steps.secret_scanner.outputs.script }}" workspace' in workflow
    assert 'bash "${{ steps.secret_scanner.outputs.script }}" history' in workflow


@NATIVE_POSIX_ONLY
def test_secret_scan_script_blocks_workspace_matches(tmp_path: Path) -> None:
    bash = shutil.which("bash")
    assert bash is not None, "bash must be available for shell contract tests"

    script = PROJECT_ROOT / "scripts" / "security" / "scan_secrets.sh"
    clean_dir = tmp_path / "clean"
    clean_dir.mkdir()
    (clean_dir / "app.txt").write_text("no sensitive value here\n", encoding="utf-8")

    clean_result = subprocess.run(
        [bash, str(script), "workspace"],
        cwd=clean_dir,
        text=True,
        capture_output=True,
        check=False,
        env=_test_env(SENSITIVE_PATTERN="TEST_SECRET_[0-9][0-9][0-9][0-9]"),
    )
    assert clean_result.returncode == 0, clean_result.stderr

    dirty_dir = tmp_path / "dirty"
    dirty_dir.mkdir()
    (dirty_dir / "app.txt").write_text("token=TEST_SECRET_1234\n", encoding="utf-8")

    dirty_result = subprocess.run(
        [bash, str(script), "workspace"],
        cwd=dirty_dir,
        text=True,
        capture_output=True,
        check=False,
        env=_test_env(SENSITIVE_PATTERN="TEST_SECRET_[0-9][0-9][0-9][0-9]"),
    )
    assert dirty_result.returncode == 1
    assert "TEST_SECRET_1234" not in dirty_result.stdout
    assert "TEST_SECRET_1234" not in dirty_result.stderr


@NATIVE_POSIX_ONLY
def test_secret_scan_script_blocks_untracked_git_workspace_matches(tmp_path: Path) -> None:
    bash = shutil.which("bash")
    git = shutil.which("git")
    assert bash is not None, "bash must be available for shell contract tests"
    assert git is not None, "git must be available for shell contract tests"

    script = PROJECT_ROOT / "scripts" / "security" / "scan_secrets.sh"
    subprocess.run([git, "init"], cwd=tmp_path, check=True, capture_output=True, text=True)
    (tmp_path / "tracked.txt").write_text("clean tracked file\n", encoding="utf-8")
    subprocess.run([git, "add", "tracked.txt"], cwd=tmp_path, check=True, capture_output=True, text=True)
    (tmp_path / "untracked.txt").write_text("token=TEST_SECRET_9999\n", encoding="utf-8")

    result = subprocess.run(
        [bash, str(script), "workspace"],
        cwd=tmp_path,
        text=True,
        capture_output=True,
        check=False,
        env=_test_env(SENSITIVE_PATTERN="TEST_SECRET_[0-9][0-9][0-9][0-9]"),
    )

    assert result.returncode == 1
    assert "TEST_SECRET_9999" not in result.stdout
    assert "TEST_SECRET_9999" not in result.stderr


def test_secret_scan_script_uses_fetch_head_pr_diff_and_configurable_history() -> None:
    script = _read_repo_text("scripts", "security", "scan_secrets.sh")

    assert "require_commands" in script
    assert "for command in git grep awk mktemp sed" in script
    assert "grep -R" not in script
    assert "grep -r" in script
    assert 'git cat-file -e "${diff_base}^{commit}"' in script
    assert 'git fetch --no-tags --depth=1 origin "$base_ref"' in script
    assert 'diff_base="FETCH_HEAD"' in script
    assert 'git diff --unified=0 "${diff_base}...HEAD"' in script
    assert 'git grep --untracked -I -E -l -e "$SENSITIVE_PATTERN"' in script
    assert '>"$added_lines"' in script
    assert 'if ! added_lines="$(mktemp)"; then' in script
    assert 'if ! git diff --unified=0 "${diff_base}...HEAD"' in script
    assert 'grep -E -q -- "$SENSITIVE_PATTERN" "$added_lines"' in script
    assert "PR diff scan failed" in script
    assert "trap - RETURN" not in script
    assert 'git diff --unified=0 "origin/${base_ref}...HEAD"' not in script
    assert 'SECRET_SCAN_HISTORY_MAX_COUNT:-200' in script


@NATIVE_POSIX_ONLY
def test_secret_scan_script_treats_dash_prefixed_pattern_as_data(tmp_path: Path) -> None:
    bash = shutil.which("bash")
    assert bash is not None, "bash must be available for shell contract tests"

    script = PROJECT_ROOT / "scripts" / "security" / "scan_secrets.sh"
    (tmp_path / "clean.txt").write_text("plain text\n", encoding="utf-8")

    result = subprocess.run(
        [bash, str(script), "workspace"],
        cwd=tmp_path,
        text=True,
        capture_output=True,
        check=False,
        env=_test_env(SENSITIVE_PATTERN="-not-a-real-secret"),
    )

    assert result.returncode == 0, result.stderr


@NATIVE_POSIX_ONLY
def test_secret_scan_script_valid_pattern_without_match_succeeds(tmp_path: Path) -> None:
    bash = shutil.which("bash")
    assert bash is not None, "bash must be available for shell contract tests"

    script = PROJECT_ROOT / "scripts" / "security" / "scan_secrets.sh"
    (tmp_path / "clean.txt").write_text("nothing to report\n", encoding="utf-8")

    result = subprocess.run(
        [bash, str(script), "workspace"],
        cwd=tmp_path,
        text=True,
        capture_output=True,
        check=False,
        env=_test_env(SENSITIVE_PATTERN="TEST_SECRET_[0-9][0-9][0-9][0-9]"),
    )

    assert result.returncode == 0, result.stderr
    assert "[OK] No sensitive patterns detected" in result.stdout


def test_github_actions_do_not_install_python_or_npm_packages_dynamically() -> None:
    checked_paths = [
        ".github/workflows/codeql.yml",
        ".github/workflows/dependency-review.yml",
        ".github/workflows/minimal-ci.yml",
        ".github/workflows/release-windows.yml",
        ".github/workflows/secret_scan.yml",
    ]
    forbidden_patterns = [
        r"\bpip\s+install\b",
        r"\bpython\s+-m\s+pip\b",
        r"\buv\s+pip\b",
        r"\bpipx\b",
        r"\bnpm\s+install\b",
        r"\bpnpm\s+install\b",
        r"\byarn\s+install\b",
        r"\bbun\s+install\b",
    ]

    findings: list[str] = []
    for relative_path in checked_paths:
        text = _read_repo_text(*relative_path.split("/"))
        for pattern in forbidden_patterns:
            if re.search(pattern, text):
                findings.append(f"{relative_path}: {pattern}")

    assert findings == []


def test_github_workflow_external_actions_are_pinned_by_sha() -> None:
    checked_paths = [
        ".github/workflows/codeql.yml",
        ".github/workflows/dependency-review.yml",
        ".github/workflows/minimal-ci.yml",
        ".github/workflows/release-windows.yml",
        ".github/workflows/secret_scan.yml",
    ]
    uses_reference = re.compile(r"^\s*uses:\s+([^#\s]+)")

    findings: list[str] = []
    for relative_path in checked_paths:
        for line_number, line in enumerate(
            _read_repo_text(*relative_path.split("/")).splitlines(),
            start=1,
        ):
            match = uses_reference.search(line)
            if match is None:
                continue
            reference = match.group(1)
            if reference.startswith("./"):
                continue
            if not re.search(r"@[0-9a-f]{40}$", reference):
                findings.append(f"{relative_path}:{line_number}: {line.strip()}")

    assert findings == []


def test_code_quality_documents_dynamic_dependency_submission_status() -> None:
    docs = _read_repo_text(".github", "CODE_QUALITY.md")

    assert "Automatic Dependency Submission is a dynamic GitHub-managed workflow" in docs
    assert "GH_DEPENDENCY_SUBMISSION_SKIP_CACHE=true" in docs
    assert "HTTP 422" in docs


def test_release_windows_workflow_uses_env_for_dispatch_inputs() -> None:
    workflow = _read_repo_text(".github", "workflows", "release-windows.yml")

    assert '$backend = "${{ inputs.backend }}"' not in workflow
    assert 'if ("${{ inputs.skip_installer }}" -eq "true")' not in workflow
    assert 'if ("${{ inputs.skip_installer }}" -ne "true")' not in workflow
    assert "RELEASE_BACKEND: ${{ inputs.backend || 'nuitka' }}" in workflow
    assert "RELEASE_INSTALLER_REQUIRED: ${{ !inputs.skip_installer }}" in workflow
    assert "RELEASE_SKIP_INSTALLER: ${{ inputs.skip_installer }}" not in workflow
    assert "$backend = $env:RELEASE_BACKEND" in workflow
    assert 'if ($env:RELEASE_INSTALLER_REQUIRED -ne "true")' in workflow
    assert 'if ($env:RELEASE_INSTALLER_REQUIRED -eq "true")' in workflow
    assert "if: ${{ env.RELEASE_INSTALLER_REQUIRED == 'true' }}" in workflow
    assert "windows-release-${{ env.RELEASE_BACKEND }}" in workflow


def test_codeql_precheck_runs_advanced_when_default_setup_is_unverified() -> None:
    workflow = _read_repo_text(".github", "workflows", "codeql.yml")

    assert 'RUN_ADVANCED="true"' in workflow
    assert 'REASON="advanced_allowed_default_setup_unverified"' in workflow
    assert 'if STATE="$(jq -r' in workflow
    assert 'STATE="unknown"' in workflow
    assert "Could not verify CodeQL default setup state: HTTP ${HTTP_CODE}; running advanced scan." in workflow
    assert 'HTTP_CODE="000"' in workflow
    assert 'Unsupported CodeQL default setup state: ${STATE}; running advanced scan.' in workflow
    assert 'REASON="advanced_allowed_default_setup_unverified_http_${HTTP_CODE}"' in workflow
    assert 'echo "Could not verify CodeQL default setup state: HTTP ${HTTP_CODE}" >&2\n            exit 1' not in workflow
    assert "default-setup-skip-note:" in workflow
    assert "verification could not be completed" not in workflow


def test_shell_doctor_does_not_print_sensitive_value_prefixes() -> None:
    script = _read_repo_text("scripts", "shell_doctor.sh")

    assert "${value:0:6}" not in script
    assert 'echo "$matches"' not in script
    assert "grep -REl" in script
    assert "suspect+=(\"${name}\")" in script


def test_secret_baseline_paths_are_posix_style() -> None:
    payload = json.loads(_read_repo_text(".secrets.baseline"))

    for path in payload["results"]:
        assert "\\" not in path


def test_gitleaks_baseline_hash_allowlist_is_line_anchored() -> None:
    config = _read_repo_text(".gitleaks.toml")

    assert 'regexTarget = "line"' in config
    assert '^\\s*"hashed_secret": "[a-f0-9]{40}",?\\s*$' in config
    assert '"hashed_secret": "[a-f0-9]{40}"\'\'\']' not in config


def test_shell_doctor_help_describes_all_history_as_git_history() -> None:
    script = _read_repo_text("scripts", "shell_doctor.sh")

    assert "~/.zsh_history" not in script
    assert "historico Git" in script


def test_shell_doctor_history_scan_uses_single_git_history_search() -> None:
    script = _read_repo_text("scripts", "shell_doctor.sh")

    assert "git rev-list --all | while read" not in script
    assert "git log --all --format='%H' -E -G" in script


def test_shell_doctor_validates_zcompdump_stat_before_age_math() -> None:
    script = _read_repo_text("scripts", "shell_doctor.sh")

    assert "stat_mtime=" in script
    assert "case \"$stat_mtime\" in" in script
    assert "date +%s) - $(stat" not in script
