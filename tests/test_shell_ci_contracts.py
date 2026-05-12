from __future__ import annotations

import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _test_env(**overrides: str) -> dict[str, str]:
    env = os.environ.copy()
    env.update(overrides)
    return env


def _read_repo_text(*parts: str) -> str:
    return (PROJECT_ROOT.joinpath(*parts)).read_text(encoding="utf-8")


def _load_opencode_review_module():
    script_path = PROJECT_ROOT / "scripts" / "ci" / "opencode_pr_review.py"
    spec = importlib.util.spec_from_file_location("opencode_pr_review_test", script_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


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


def test_ci_quality_gates_does_not_expand_arg_string_unquoted() -> None:
    script = _read_repo_text("scripts", "ci_quality_gates.sh")

    assert "run_quality_gates.py $GATES_ARGS" not in script
    assert "read -r -a GATES_ARGS_ARRAY" in script
    assert '"${GATES_ARGS_ARRAY[@]}"' in script


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
    assert 'bash scripts/security/scan_secrets.sh pr-diff "$BASE_SHA"' in workflow
    assert 'git fetch origin "$BASE_REF" --depth=1' not in workflow
    assert 'git fetch origin "$BASE_REF" || true' not in workflow
    assert 'git diff --unified=0 "origin/${BASE_REF}...HEAD"' not in workflow


def test_dev_bootstrap_requires_hash_for_remote_pyenv_install() -> None:
    script = _read_repo_text("dev_env", "bootstrap.ps1")

    assert "[string]$PyenvInstallerSha256" in script
    assert "Instalacao remota do pyenv-win exige -PyenvInstallerSha256" in script
    assert "Get-FileHash -Algorithm SHA256" in script
    assert "Unblock-File -LiteralPath $installerPath" in script
    assert "[Net.SecurityProtocolType]::Tls12" in script
    assert "Invoke-Expression" not in script


def test_secret_scan_workspace_and_pr_diff_are_blocking_on_main_and_dev() -> None:
    workflow = _read_repo_text(".github", "workflows", "secret_scan.yml")

    assert "branches: [main, dev]" in workflow
    assert "continue-on-error: true" not in workflow
    assert "bash scripts/security/scan_secrets.sh workspace" in workflow
    assert "bash scripts/security/scan_secrets.sh history" in workflow


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


def test_opencode_secret_jobs_use_environment_without_oidc() -> None:
    workflow = _read_repo_text(".github", "workflows", "opencode.yml")
    local_action = _read_repo_text(".github", "actions", "opencode-github", "action.yml")

    assert "push:" not in workflow
    assert "pull_request:" in workflow
    assert "opencode-pr-review:" in workflow
    assert "github.event.pull_request.head.repo.fork == false" in workflow
    assert "opencode-push-review:" not in workflow
    assert workflow.count("environment: SECRETS") == 4
    assert "noop:" in workflow
    assert 'echo "No opencode command in comment; skipping."' in workflow
    assert "Run automatic PR review" in workflow
    assert "Run automatic push review" not in workflow
    assert "Review this pull request for concrete bugs" in workflow
    assert "Review the pushed commit range for concrete bugs" not in workflow
    assert workflow.count("uses: ./.github/actions/configure-qwen-opencode") == 2
    assert workflow.count("uses: ./.github/actions/opencode-github") == 4
    assert workflow.count("qwen-cloud-coding-plan") == 2
    assert workflow.count("github.event.issue.pull_request") == 3
    assert "anomalyco/opencode/github@" not in workflow
    assert 'default: "true"' in local_action
    assert "GITHUB_TOKEN: ${{ github.token }}" in local_action
    assert "opencode github run" not in local_action
    assert "python scripts/ci/opencode_pr_review.py" in local_action
    assert "GH_TOKEN: ${{ github.token }}" in local_action
    assert "actions/cache@0057852bfaa89a56745cba8c7296529d2fc39830" in local_action
    assert "actions/cache@v4" not in local_action
    assert "opencode-ai@${{ inputs.opencode_version }}" in local_action
    assert "curl -fsSL https://opencode.ai/install | bash" not in local_action
    assert "releases/latest" not in local_action
    assert "id-token: write" not in workflow
    qwen_action = _read_repo_text(".github", "actions", "configure-qwen-opencode", "action.yml")
    assert "umask 077" in qwen_action
    assert 'chmod 600 "${HOME}/.config/opencode/opencode.json"' in qwen_action


def test_opencode_review_script_extracts_pr_number() -> None:
    module = _load_opencode_review_module()

    assert module.extract_pr_number({"pull_request": {"number": 58}}) == 58
    assert module.extract_pr_number({"issue": {"number": 59, "pull_request": {"url": "x"}}}) == 59
    with pytest.raises(ValueError, match="pull request"):
        module.extract_pr_number({"issue": {"number": 60}})


def test_opencode_review_script_requires_clear_environment(monkeypatch) -> None:
    module = _load_opencode_review_module()

    monkeypatch.delenv("MODEL", raising=False)

    with pytest.raises(RuntimeError, match="MODEL"):
        module.required_env("MODEL")


def test_opencode_review_script_does_not_print_failed_command_output(tmp_path: Path, capsys) -> None:
    module = _load_opencode_review_module()
    output_path = tmp_path / "captured.txt"

    with pytest.raises(subprocess.CalledProcessError):
        module.run_checked(
            [
                sys.executable,
                "-c",
                "import sys; print('SECRET_STDOUT'); print('SECRET_STDERR', file=sys.stderr); sys.exit(3)",
            ],
            stdout_path=output_path,
        )

    captured = capsys.readouterr()
    assert "SECRET_STDOUT" not in captured.out
    assert "SECRET_STDERR" not in captured.out
    assert "SECRET_STDERR" not in captured.err
    assert "stdout captured in:" in captured.out
    assert "SECRET_STDOUT" in output_path.read_text(encoding="utf-8")


def test_opencode_review_script_truncates_large_diff(tmp_path: Path) -> None:
    module = _load_opencode_review_module()
    diff_path = tmp_path / "large.diff"
    diff_path.write_bytes(b"a" * 120)

    text, truncated = module.truncate_diff(diff_path, limit=80)
    assert truncated is True
    data = diff_path.read_bytes()
    assert data == b"a" * 120
    assert len(text.encode("utf-8")) <= 80
    assert "[diff truncated at 80 bytes]" in text

    utf8_path = tmp_path / "utf8.diff"
    utf8_path.write_text("linha\n" + ("\u00e1" * 100), encoding="utf-8")
    text, truncated = module.truncate_diff(utf8_path, limit=80)
    assert truncated is True
    assert "\ufffd" not in text
    assert "[diff truncated at 80 bytes]" in text

    source_path = tmp_path / "source.diff"
    review_path = tmp_path / "review.diff"
    source_path.write_bytes(b"b" * 120)
    _, truncated = module.truncate_diff(source_path, output_path=review_path, limit=80)
    assert truncated is True
    assert source_path.read_bytes() == b"b" * 120
    assert b"[diff truncated at 80 bytes]" in review_path.read_bytes()


def test_opencode_review_script_adds_lfs_note() -> None:
    module = _load_opencode_review_module()

    prompt = module.build_prompt("base", "version https://git-lfs.github.com/spec/v1")

    assert "manual review" in prompt


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
