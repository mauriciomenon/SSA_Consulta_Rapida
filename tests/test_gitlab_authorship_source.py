from __future__ import annotations

import os
import shutil
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
pytestmark = pytest.mark.skipif(sys.platform == "win32", reason="Etapa CI usa shell POSIX")


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=repo, check=True, capture_output=True, text=True
    ).stdout.strip()


def _gitlab_authorship_script() -> str:
    workflow = (PROJECT_ROOT / ".gitlab-ci.yml").read_text(encoding="utf-8")
    job = workflow.split("autoria-git:\n", 1)[1].split("\nquality-gates:", 1)[0]
    return textwrap.dedent(job.split("script:\n    - |\n", 1)[1])


def test_gitlab_merge_request_uses_validator_from_base(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "--quiet")
    _git(repo, "config", "user.name", "Mauricio Menon")
    _git(repo, "config", "user.email", "mauriciomenon@users.noreply.github.com")
    _git(repo, "config", "commit.gpgsign", "false")
    _git(repo, "config", "core.hooksPath", os.devnull)
    validator = repo / "scripts" / "validate_git_authorship.py"
    validator.parent.mkdir()
    shutil.copy2(PROJECT_ROOT / "scripts" / "validate_git_authorship.py", validator)
    _git(repo, "add", ".")
    _git(repo, "commit", "--quiet", "-m", "Base confiavel")
    base = _git(repo, "rev-parse", "HEAD")

    validator.write_text('print("VALIDADOR_DO_MR_EXECUTADO")\n', encoding="utf-8")
    _git(repo, "add", ".")
    _git(
        repo,
        "-c", "user.name=Intruso",
        "-c", "user.email=intruso@example.invalid",
        "commit", "--quiet", "-m", "Alteracao nao autorizada",
    )
    head = _git(repo, "rev-parse", "HEAD")
    env = os.environ | {
        "CI_PIPELINE_SOURCE": "merge_request_event",
        "CI_MERGE_REQUEST_DIFF_BASE_SHA": base,
        "CI_MERGE_REQUEST_SOURCE_BRANCH_SHA": head,
        "CI_COMMIT_SHA": head,
    }

    result = subprocess.run(
        ["sh", "-c", _gitlab_authorship_script()],
        cwd=repo,
        env=env,
        capture_output=True,
        text=True,
        check=False,
        timeout=15,
    )

    assert result.returncode == 1, result.stdout + result.stderr
    assert "identidade nao autorizada" in result.stderr
    assert "VALIDADOR_DO_MR_EXECUTADO" not in result.stdout
