from __future__ import annotations

import shutil
import subprocess
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


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
    ]
    for script in scripts:
        result = subprocess.run(
            [bash, "-n", script],
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


def test_ci_quality_gates_does_not_expand_arg_string_unquoted() -> None:
    script = _read_repo_text("scripts", "ci_quality_gates.sh")

    assert "run_quality_gates.py $GATES_ARGS" not in script
    assert "read -r -a GATES_ARGS_ARRAY" in script
    assert '"${GATES_ARGS_ARRAY[@]}"' in script


def test_minimal_ci_runs_for_any_workflow_change() -> None:
    workflow = _read_repo_text(".github", "workflows", "minimal-ci.yml")

    assert workflow.count('".github/workflows/*.yml"') == 2
    assert '".github/workflows/minimal-ci.yml"' not in workflow


def test_secret_scan_uses_quoted_env_for_pr_base_ref() -> None:
    workflow = _read_repo_text(".github", "workflows", "secret_scan.yml")

    assert "git fetch origin ${{ github.base_ref }}" not in workflow
    assert "origin/${{ github.base_ref }}" not in workflow
    assert "BASE_REF: ${{ github.base_ref }}" in workflow
    assert 'git fetch origin "$BASE_REF"' in workflow
    assert 'git fetch origin "$BASE_REF" --depth=1' not in workflow
    assert 'git fetch origin "$BASE_REF" || true' not in workflow
    assert 'git diff --unified=0 "origin/${BASE_REF}...HEAD"' in workflow


def test_secret_scan_is_blocking_on_main_and_dev() -> None:
    workflow = _read_repo_text(".github", "workflows", "secret_scan.yml")

    assert "branches: [ main, dev ]" in workflow
    assert "continue-on-error: true" not in workflow
    assert "echo '[ERROR] Sensitive patterns found'" in workflow
    assert "echo '[ERROR] Possible secret in diff'" in workflow


def test_opencode_secret_jobs_use_environment_without_oidc() -> None:
    workflow = _read_repo_text(".github", "workflows", "opencode.yml")

    assert workflow.count("environment: SECRETS") == 3
    assert "id-token: write" not in workflow


def test_codeql_precheck_runs_advanced_when_default_setup_is_unverified() -> None:
    workflow = _read_repo_text(".github", "workflows", "codeql.yml")

    assert 'RUN_ADVANCED="true"' in workflow
    assert 'REASON="advanced_allowed_default_setup_unverified"' in workflow
    assert "Could not verify CodeQL default setup state: HTTP ${HTTP_CODE}; running advanced scan." in workflow
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
