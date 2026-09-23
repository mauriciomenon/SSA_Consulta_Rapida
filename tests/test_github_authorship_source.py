from __future__ import annotations

import os
from pathlib import Path
import shutil
import subprocess
import sys
import textwrap

import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
BOOTSTRAP_SHA = "cd0b092e5acdf15b85d3c816ad04dbc1b3c4e3c8"
VALIDATOR_PATH = "scripts/validate_git_authorship.py"
pytestmark = pytest.mark.skipif(sys.platform == "win32", reason="Etapa CI executa Bash POSIX")


def _git(repo: Path, *arguments: str) -> str:
    return subprocess.run(
        ["git", *arguments], cwd=repo, capture_output=True, text=True,
        check=True, timeout=15,
    ).stdout.strip()


def _workflow_script() -> str:
    workflow = (PROJECT_ROOT / ".github/workflows/minimal-ci.yml").read_text(encoding="utf-8")
    job = workflow.split("- name: Validar autoria Git", 1)[1]
    return textwrap.dedent(job.split("run: |\n", 1)[1].split("\n      - name:", 1)[0])


@pytest.fixture
def ci_repositories(tmp_path: Path) -> tuple[Path, Path]:
    repo = tmp_path / "repo"
    remote = tmp_path / "remote"
    for target in (repo, remote):
        target.mkdir()
        _git(target, "init", "--quiet")
        _git(target, "config", "user.name", "Mauricio Menon")
        _git(target, "config", "user.email", "mauriciomenon@users.noreply.github.com")
        _git(target, "config", "commit.gpgsign", "false")
        _git(target, "config", "core.hooksPath", os.devnull)
    _git(repo, "remote", "add", "origin", str(remote))
    return repo, remote


def _commit(repo: Path, message: str, *, authorized: bool = True) -> str:
    _git(repo, "add", ".")
    identity = [] if authorized else [
        "-c", "user.name=Identidade recusada", "-c", "user.email=recusado@example.invalid",
    ]
    _git(repo, *identity, "commit", "--quiet", "-m", message)
    return _git(repo, "rev-parse", "HEAD")


def _prepare_pr(
    repo: Path, remote: Path, *, base_has_validator: bool, authorized: bool = True,
) -> tuple[str, str, str]:
    for target in (repo, remote):
        (target / "base.txt").write_text(target.name, encoding="utf-8")
        if target == remote or base_has_validator:
            validator = target / VALIDATOR_PATH
            validator.parent.mkdir()
            shutil.copy2(PROJECT_ROOT / VALIDATOR_PATH, validator)
    base = _commit(repo, "Base do evento")
    bootstrap = _commit(remote, "Fonte confiavel do bootstrap")
    validator = repo / VALIDATOR_PATH
    validator.parent.mkdir(exist_ok=True)
    validator.write_text('print("VALIDADOR_DO_PR_EXECUTADO")\n', encoding="utf-8")
    head = _commit(repo, "Mudanca de PR", authorized=authorized)
    return base, head, bootstrap


def _run_pr(
    tmp_path: Path, repo: Path, base: str, head: str, bootstrap: str,
    *, extra_env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    trusted_tmp = tmp_path / "trusted-tmp"
    trusted_tmp.mkdir()
    env = os.environ | {
        "EVENT_NAME": "pull_request", "PR_BASE_SHA": base, "PR_HEAD_SHA": head,
        "BEFORE_SHA": "e" * 40, "HEAD_SHA": "e" * 40,
        "GIT_TRACE": str(tmp_path / "git.trace"), "TMPDIR": str(trusted_tmp),
    } | (extra_env or {})
    # Substitui somente o pin pelo commit da fixture; o SHA publicado e conferido abaixo.
    script = _workflow_script().replace(BOOTSTRAP_SHA, bootstrap)
    return subprocess.run(
        ["bash", "-c", script], cwd=repo, env=env,
        capture_output=True, text=True, check=False, timeout=15,
    )


def test_github_authorship_bootstrap_pins_reviewed_commit() -> None:
    assert f'BOOTSTRAP_SHA="{BOOTSTRAP_SHA}"' in _workflow_script()


@pytest.mark.parametrize("source", ["base", "bootstrap-local", "bootstrap-fetch"])
@pytest.mark.parametrize("authorized", [False, True])
def test_github_pr_uses_trusted_validator_and_exact_range(
    tmp_path: Path, ci_repositories: tuple[Path, Path], source: str, authorized: bool,
) -> None:
    repo, remote = ci_repositories
    base, head, bootstrap = _prepare_pr(
        repo, remote, base_has_validator=source == "base", authorized=authorized,
    )
    if source == "bootstrap-local":
        _git(repo, "fetch", "--no-tags", "origin", bootstrap)
    result = _run_pr(tmp_path, repo, base, head, bootstrap)
    assert "VALIDADOR_DO_PR_EXECUTADO" not in result.stdout
    assert result.returncode == (0 if authorized else 1), result.stdout + result.stderr
    if authorized:
        assert "[autoria-git] OK: 1 commits" in result.stderr
    else:
        assert "identidade nao autorizada" in result.stderr
    assert ("Bootstrap explicito" in result.stdout) is (source != "base")
    assert list((tmp_path / "trusted-tmp").iterdir()) == []
    trace = (tmp_path / "git.trace").read_text(encoding="utf-8")
    assert f"git rev-list {head} --not '{base}^{{commit}}'" in trace
    assert (f"git fetch --no-tags origin {bootstrap}" in trace) is (source == "bootstrap-fetch")


def test_github_pr_missing_base_fetch_failure_does_not_bootstrap(
    tmp_path: Path, ci_repositories: tuple[Path, Path],
) -> None:
    repo, remote = ci_repositories
    _, head, bootstrap = _prepare_pr(repo, remote, base_has_validator=False)
    unknown = "f" * 40
    result = _run_pr(tmp_path, repo, unknown, head, bootstrap)
    assert result.returncode != 0
    assert "Bootstrap explicito" not in result.stdout
    assert "VALIDADOR_DO_PR_EXECUTADO" not in result.stdout
    trace = (tmp_path / "git.trace").read_text(encoding="utf-8")
    assert f"git fetch --no-tags origin {unknown}" in trace
    assert f"git fetch --no-tags origin {bootstrap}" not in trace
    assert "git rev-list" not in trace


@pytest.mark.parametrize("failed_command", ["ls-tree", "show"])
def test_github_pr_source_read_failure_does_not_bootstrap(
    tmp_path: Path, ci_repositories: tuple[Path, Path], failed_command: str,
) -> None:
    repo, remote = ci_repositories
    base, head, bootstrap = _prepare_pr(repo, remote, base_has_validator=True)
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    git = bin_dir / "git"
    git.write_text(
        '#!/bin/sh\nif [ "$1" = "$SSA_FAIL_GIT_COMMAND" ]; then\n'
        '  echo "falha de leitura injetada" >&2\n  exit 71\nfi\n'
        'exec "$SSA_REAL_GIT" "$@"\n', encoding="utf-8",
    )
    git.chmod(0o755)
    real_git = shutil.which("git")
    assert real_git is not None
    result = _run_pr(tmp_path, repo, base, head, bootstrap, extra_env={
        "PATH": f"{bin_dir}{os.pathsep}{os.environ['PATH']}",
        "SSA_REAL_GIT": real_git, "SSA_FAIL_GIT_COMMAND": failed_command,
    })
    assert result.returncode == 71
    assert "falha de leitura injetada" in result.stderr
    assert "Bootstrap explicito" not in result.stdout
    assert "VALIDADOR_DO_PR_EXECUTADO" not in result.stdout
    assert list((tmp_path / "trusted-tmp").iterdir()) == []


@pytest.mark.parametrize("field", ["base", "head"])
@pytest.mark.parametrize("invalid_sha", ["--opcao-invalida", "1234"])
def test_github_pr_validates_sha_before_git_commands(
    tmp_path: Path, ci_repositories: tuple[Path, Path], field: str, invalid_sha: str,
) -> None:
    repo, remote = ci_repositories
    base, head, bootstrap = _prepare_pr(repo, remote, base_has_validator=True)
    if field == "base":
        base = invalid_sha
    else:
        head = invalid_sha
    result = _run_pr(tmp_path, repo, base, head, bootstrap)
    assert result.returncode != 0
    assert "SHA invalido" in result.stderr
    assert not (tmp_path / "git.trace").exists()
