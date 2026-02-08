"""Guards to prevent generated artifacts from entering release branches."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest


def _require_git() -> None:
    if shutil.which("git") is None:
        pytest.skip("git nao encontrado no ambiente")


def test_gitignore_blocks_sonar_directory():
    gitignore = Path(".gitignore")
    assert gitignore.exists(), ".gitignore deve existir"
    content = gitignore.read_text(encoding="utf-8")
    assert ".sonar/" in content or "\n.sonar\n" in content, (
        ".gitignore deve bloquear artefatos .sonar/"
    )


def test_sonar_directory_is_not_tracked():
    _require_git()
    result = subprocess.run(
        ["git", "ls-files", ".sonar"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, f"git ls-files falhou: {result.stderr}"
    tracked = [line for line in result.stdout.splitlines() if line.strip()]
    assert tracked == [], f".sonar nao deve ter arquivos versionados: {tracked[:5]}"


def test_backup_artifacts_are_not_tracked():
    _require_git()
    tracked_result = subprocess.run(
        ["git", "ls-files"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert tracked_result.returncode == 0, f"git ls-files falhou: {tracked_result.stderr}"

    deleted_result = subprocess.run(
        ["git", "ls-files", "--deleted"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert (
        deleted_result.returncode == 0
    ), f"git ls-files --deleted falhou: {deleted_result.stderr}"

    tracked_files = {
        line.strip() for line in tracked_result.stdout.splitlines() if line.strip()
    }
    deleted_files = {
        line.strip() for line in deleted_result.stdout.splitlines() if line.strip()
    }
    effective_tracked = sorted(tracked_files - deleted_files)
    forbidden_tokens = [".backup_", ".py.bak_", ".py.planv", "_bkp_"]
    offenders = [
        path for path in effective_tracked if any(token in path for token in forbidden_tokens)
    ]
    assert offenders == [], f"Arquivos de backup nao devem ser versionados: {offenders[:10]}"
