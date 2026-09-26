from __future__ import annotations

import os
from pathlib import Path
import shutil
import subprocess
import sys

import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
pytestmark = pytest.mark.skipif(sys.platform == "win32", reason="Scripts exigem host POSIX nativo")


@pytest.fixture
def shell_workspace(tmp_path: Path) -> tuple[Path, dict[str, str], str]:
    repo = tmp_path / "repo"
    (repo / "scripts" / "env").mkdir(parents=True)
    for script in ("shell_doctor.sh", "install_hooks.sh", "env/native_host_guard.sh"):
        shutil.copy2(PROJECT_ROOT / "scripts" / script, repo / "scripts" / script)
    source_hooks = repo / "scripts" / "git_hooks"
    source_hooks.mkdir()
    for name in ("pre-commit", "commit-msg", "pre-push"):
        shutil.copy2(PROJECT_ROOT / "scripts" / "git_hooks" / name, source_hooks / name)
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    for tool in ("git", "dirname", "tr", "cat", "mkdir", "chmod", "cmp", "grep", "realpath"):
        executable = shutil.which(tool)
        if executable is not None:
            (bin_dir / tool).symlink_to(executable)
    bash = shutil.which("bash")
    git = shutil.which("git")
    assert bash is not None and git is not None
    home = tmp_path / "home"
    home.mkdir()
    env = os.environ | {
        "PATH": str(bin_dir), "HOME": str(home), "ZDOTDIR": str(home),
        "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_SYSTEM": os.devnull,
    }
    for key in ("BASH_ENV", "ENV", "GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE"):
        env.pop(key, None)
    subprocess.run([git, "init", "--quiet", str(repo)], env=env, check=True, timeout=10)
    return repo, env, bash


@pytest.mark.parametrize(
    "argument,expected_exit,output",
    [("--help", 0, "Uso:"), ("-h", 0, "Uso:"),
     ("--self-test", 1, "ISSUE_TEST"), ("--quick", 1, "Repo root:")],
)
def test_shell_doctor_modes_without_git(
    shell_workspace: tuple[Path, dict[str, str], str],
    argument: str, expected_exit: int, output: str,
) -> None:
    repo, env, bash = shell_workspace
    (Path(env["PATH"]) / "git").unlink()
    result = subprocess.run(
        [bash, str(repo / "scripts" / "shell_doctor.sh"), argument],
        cwd=repo, env=env, capture_output=True, text=True, check=False, timeout=10,
    )
    assert result.returncode == expected_exit, result.stdout + result.stderr
    assert output in result.stdout
    assert "BLOCKED" not in result.stderr


@pytest.mark.parametrize("argument", ["--all-history", "--full"])
def test_shell_doctor_history_requires_git(
    shell_workspace: tuple[Path, dict[str, str], str], argument: str,
) -> None:
    repo, env, bash = shell_workspace
    (Path(env["PATH"]) / "git").unlink()
    result = subprocess.run(
        [bash, str(repo / "scripts" / "shell_doctor.sh"), argument],
        cwd=repo, env=env, capture_output=True, text=True, check=False, timeout=10,
    )
    assert result.returncode == 2
    assert "ferramenta ausente ou nao executavel: git" in result.stderr
    assert "Repo root:" not in result.stdout


def test_shell_doctor_operation_keeps_native_repo_guard(
    shell_workspace: tuple[Path, dict[str, str], str],
) -> None:
    repo, env, bash = shell_workspace
    blocked_repo = Path(env["HOME"]) / "gitlab"
    shutil.copytree(repo, blocked_repo)
    result = subprocess.run(
        [bash, str(blocked_repo / "scripts" / "shell_doctor.sh"), "--quick"],
        cwd=blocked_repo, env=env, capture_output=True, text=True, check=False, timeout=10,
    )
    assert result.returncode == 2
    assert "filesystem Windows proibido" in result.stderr


@pytest.mark.parametrize("arguments", [[], ["--authorship-only"]])
@pytest.mark.parametrize("existing_hooks", [False, True])
def test_install_hooks_without_uv_preserves_destinations(
    shell_workspace: tuple[Path, dict[str, str], str],
    arguments: list[str], existing_hooks: bool,
) -> None:
    repo, env, bash = shell_workspace
    destination = repo / ".git" / "hooks"
    shutil.rmtree(destination)
    original = b"#!/bin/sh\necho hook existente\n"
    external = repo / "custom-hook"
    if existing_hooks:
        destination.mkdir()
        (destination / "commit-msg").write_bytes(original)
        (destination / "commit-msg").chmod(0o640)
        external.write_bytes(original)
        (destination / "pre-push").symlink_to(external)
    result = subprocess.run(
        [bash, str(repo / "scripts" / "install_hooks.sh"), *arguments],
        cwd=repo, env=env, capture_output=True, text=True, check=False, timeout=10,
    )
    assert result.returncode == 1
    assert "ferramenta ausente ou nao executavel: uv" in result.stderr
    assert "Concluido" not in result.stdout
    if existing_hooks:
        assert {path.name for path in destination.iterdir()} == {"commit-msg", "pre-push"}
        assert (destination / "commit-msg").read_bytes() == original
        assert (destination / "commit-msg").stat().st_mode & 0o777 == 0o640
        assert (destination / "pre-push").is_symlink()
        assert (destination / "pre-push").resolve() == external
        assert external.read_bytes() == original
    else:
        assert not destination.exists()


@pytest.mark.parametrize("authorship_only", [False, True])
def test_install_hooks_available_uv_preserves_installation_modes(
    shell_workspace: tuple[Path, dict[str, str], str], authorship_only: bool,
) -> None:
    repo, env, bash = shell_workspace
    bin_dir = Path(env["PATH"])
    for tool in ("uv", "pre-commit"):
        executable = bin_dir / tool
        executable.write_text('#!/bin/sh\necho chamada indevida >&2\nexit 99\n', encoding="utf-8")
        executable.chmod(0o755)
    arguments = []
    expected = {"pre-commit", "commit-msg", "pre-push"}
    if authorship_only:
        arguments = ["--authorship-only"]
        expected.remove("pre-commit")
        (repo / ".pre-commit-config.yaml").write_text("repos: []\n", encoding="utf-8")
    result = subprocess.run(
        [bash, str(repo / "scripts" / "install_hooks.sh"), *arguments],
        cwd=repo, env=env, capture_output=True, text=True, check=False, timeout=10,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "Concluido" in result.stdout
    destination = repo / ".git" / "hooks"
    assert {path.name for path in destination.iterdir() if not path.name.endswith(".sample")} == expected
    for name in expected:
        assert (destination / name).read_bytes() == (repo / "scripts" / "git_hooks" / name).read_bytes()
        assert os.access(destination / name, os.X_OK)
