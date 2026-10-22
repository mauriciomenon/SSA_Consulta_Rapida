"""pre-push: branch novo nao revalida historico ja publicado (refs remotas)."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

VALIDATOR = Path(__file__).resolve().parents[1] / "scripts" / "validate_git_authorship.py"
IDENTITY = {
    "GIT_AUTHOR_NAME": "Mauricio Menon",
    "GIT_AUTHOR_EMAIL": "mauriciomenon@users.noreply.github.com",
    "GIT_COMMITTER_NAME": "Mauricio Menon",
    "GIT_COMMITTER_EMAIL": "mauriciomenon@users.noreply.github.com",
}
ZERO = "0" * 40


def _git(repo: Path, *args: str) -> str:
    env = {**os.environ, **IDENTITY}
    result = subprocess.run(
        ["git", "-c", "core.hooksPath=/dev/null", "-c", "commit.gpgsign=false", *args],
        cwd=repo,
        env=env,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def _repo_with_published_credit(tmp_path: Path, *, publish: bool) -> tuple[Path, str]:
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-q", "-b", "main")
    _git(repo, "commit", "-q", "--allow-empty", "-m", "ci: antigo", "-m",
         "Co-authored-by: Codex <noreply@openai.com>")
    if publish:
        _git(repo, "update-ref", "refs/remotes/origin/main", "HEAD")
    _git(repo, "checkout", "-q", "-b", "rev")
    _git(repo, "commit", "-q", "--allow-empty", "-m", "fix: novo e limpo")
    return repo, _git(repo, "rev-parse", "HEAD")


def _pre_push(repo: Path, head: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(VALIDATOR), "pre-push"],
        cwd=repo,
        input=f"refs/heads/rev {head} refs/heads/rev {ZERO}\n",
        capture_output=True,
        text=True,
        timeout=60,
    )


def test_new_branch_skips_history_already_on_remote(tmp_path: Path) -> None:
    repo, head = _repo_with_published_credit(tmp_path, publish=True)

    result = _pre_push(repo, head)

    assert result.returncode == 0, result.stderr
    assert "1 commits" in result.stderr


def test_new_branch_without_remote_refs_validates_full_history(tmp_path: Path) -> None:
    repo, head = _repo_with_published_credit(tmp_path, publish=False)

    result = _pre_push(repo, head)

    assert result.returncode == 1
    assert "BLOQUEADO" in result.stderr


def test_new_unpublished_commit_with_credit_is_still_blocked(tmp_path: Path) -> None:
    repo, _ = _repo_with_published_credit(tmp_path, publish=True)
    _git(repo, "commit", "-q", "--allow-empty", "-m", "feat: x", "-m",
         "Co-authored-by: Codex <noreply@openai.com>")
    head = _git(repo, "rev-parse", "HEAD")

    result = _pre_push(repo, head)

    assert result.returncode == 1
    assert "BLOQUEADO" in result.stderr
