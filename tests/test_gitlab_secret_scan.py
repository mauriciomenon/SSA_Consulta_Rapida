from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import textwrap
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
ZERO_SHA = "0" * 40
BOOTSTRAP_SHA = "cd0b092e5acdf15b85d3c816ad04dbc1b3c4e3c8"
pytestmark = pytest.mark.skipif(
    os.name == "nt" or shutil.which("gitleaks") is None,
    reason="Teste exige shell POSIX e gitleaks real",
)


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=repo, check=True, capture_output=True, text=True,
    ).stdout.strip()


def _init_repo(repo: Path) -> str:
    repo.mkdir()
    _git(repo, "init")
    _git(repo, "config", "user.name", "Mauricio Menon")
    _git(repo, "config", "user.email", "mauriciomenon@users.noreply.github.com")
    _git(repo, "config", "commit.gpgsign", "false")
    _git(repo, "config", "core.hooksPath", "/dev/null")
    shutil.copy2(ROOT / ".gitleaks.toml", repo / ".gitleaks.toml")
    _git(repo, "add", ".")
    _git(repo, "commit", "-m", "Base sintetica")
    return _git(repo, "rev-parse", "HEAD")


def _synthetic_secret() -> str:
    return "gh" + "p_" + hashlib.sha256(b"fixture gitlab historico").hexdigest()[:36]


def _add_and_remove_secret(repo: Path) -> str:
    candidate = repo / "credencial_teste.txt"
    candidate.write_text(_synthetic_secret(), encoding="utf-8")
    signal = subprocess.run(
        ["gitleaks", "dir", ".", "--redact", "--no-banner"], cwd=repo,
        capture_output=True, text=True, check=False,
    )
    assert signal.returncode == 1, "Fixture deve ser detectada pelo scanner real"
    assert _synthetic_secret() not in signal.stdout + signal.stderr
    _git(repo, "add", ".")
    _git(repo, "commit", "-m", "Adiciona fixture sintetica")
    candidate.unlink()
    _git(repo, "add", "-u")
    _git(repo, "commit", "-m", "Remove fixture sintetica")
    return _git(repo, "rev-parse", "HEAD")


def _run_job(
    repo: Path, *, bootstrap_sha: str | None = None, **overrides: str
) -> tuple[subprocess.CompletedProcess[str], str]:
    config = (ROOT / ".gitlab-ci.yml").read_text(encoding="utf-8")
    job = config.split("\nsecret-scan:\n", 1)[1]
    commands = job.split("  script:\n", 1)[1]
    if commands.startswith("    - |\n"):
        script = textwrap.dedent(commands.split("    - |\n", 1)[1])
    else:
        script = "\n".join(line.removeprefix("    - ") for line in commands.splitlines())
    assert f'BOOTSTRAP_SHA="{BOOTSTRAP_SHA}"' in script
    bootstrap = bootstrap_sha or _git(repo, "rev-list", "--max-parents=0", "HEAD").splitlines()[0]
    script = script.replace(BOOTSTRAP_SHA, bootstrap)
    trace = repo.parent / "git.trace"
    env = os.environ.copy()
    env.update(
        CI_PIPELINE_SOURCE="push", CI_COMMIT_BEFORE_SHA=ZERO_SHA,
        CI_COMMIT_SHA=_git(repo, "rev-parse", "HEAD"),
        CI_MERGE_REQUEST_DIFF_BASE_SHA="", CI_MERGE_REQUEST_SOURCE_BRANCH_SHA="",
        GIT_TRACE=str(trace),
    )
    env.update(overrides)
    result = subprocess.run(
        ["sh", "-c", script], cwd=repo, env=env, capture_output=True,
        text=True, check=False,
    )
    assert _synthetic_secret() not in result.stdout + result.stderr
    return result, trace.read_text(encoding="utf-8") if trace.exists() else ""


@pytest.mark.parametrize("event", ["push", "merge_request_event"])
def test_gitlab_scanner_detects_secret_removed_within_event(
    tmp_path: Path, event: str
) -> None:
    repo = tmp_path / "repo"
    base = _init_repo(repo)
    head = _add_and_remove_secret(repo)
    inputs = {"CI_PIPELINE_SOURCE": event, "CI_COMMIT_BEFORE_SHA": base}
    if event == "merge_request_event":
        inputs.update(
            CI_MERGE_REQUEST_DIFF_BASE_SHA=base,
            CI_MERGE_REQUEST_SOURCE_BRANCH_SHA=head,
            CI_COMMIT_SHA="f" * 40, CI_COMMIT_BEFORE_SHA=ZERO_SHA,
        )

    result, trace = _run_job(repo, **inputs)

    assert result.returncode == 1, result.stdout + result.stderr
    assert f"{base}..{head}" in trace
    assert "leaks found" in result.stderr


def test_gitlab_scanner_keeps_workspace_and_history_checks(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    base = _init_repo(repo)
    _add_and_remove_secret(repo)
    (repo / "arquivo_local.txt").write_text(_synthetic_secret(), encoding="utf-8")

    result, trace = _run_job(repo, CI_COMMIT_BEFORE_SHA=base)

    assert result.returncode == 1, result.stdout + result.stderr
    assert "git log" in trace
    assert result.stderr.count("leaks found:") == 2


@pytest.mark.parametrize("scope", ["range", "zero", "manual"])
def test_gitlab_scanner_does_not_expand_scope_to_older_history(
    tmp_path: Path, scope: str
) -> None:
    repo = tmp_path / "repo"
    _init_repo(repo)
    base = _add_and_remove_secret(repo)
    _git(repo, "commit", "--allow-empty", "-m", "Commit atual limpo")
    head = _git(repo, "rev-parse", "HEAD")
    inputs = {"CI_COMMIT_BEFORE_SHA": base if scope == "range" else ZERO_SHA}
    if scope == "manual":
        inputs.update(CI_PIPELINE_SOURCE="web", CI_COMMIT_BEFORE_SHA="f" * 40)

    result, trace = _run_job(repo, **inputs)

    assert result.returncode == 0, result.stdout + result.stderr
    expected = f"{base}..{head}" if scope == "range" else f"-1 {head}"
    assert expected in trace


@pytest.mark.parametrize("available", [False, True])
def test_gitlab_scanner_fetches_only_missing_event_base(
    tmp_path: Path, available: bool
) -> None:
    repo = tmp_path / "repo"
    remote = tmp_path / "remote"
    _init_repo(repo)
    _init_repo(remote)
    _git(remote, "commit", "--allow-empty", "-m", "Base apenas no remoto")
    base = _git(remote, "rev-parse", "HEAD") if available else "f" * 40
    _git(repo, "remote", "add", "origin", str(remote))

    result, trace = _run_job(repo, CI_COMMIT_BEFORE_SHA=base)

    assert f"git fetch --no-tags origin {base}" in trace
    if available:
        assert result.returncode == 0, result.stdout + result.stderr
        assert _git(repo, "rev-parse", "FETCH_HEAD") == base
    else:
        assert result.returncode != 0
        assert "git log" not in trace


@pytest.mark.parametrize(
    "invalid_input",
    [{"CI_COMMIT_BEFORE_SHA": "--all"}, {"CI_COMMIT_SHA": "abc"},
     {"CI_COMMIT_SHA": "0" * 40 + "\n--all"},
     {"CI_PIPELINE_SOURCE": "merge_request_event", "CI_MERGE_REQUEST_DIFF_BASE_SHA": ""}],
)
def test_gitlab_scanner_rejects_invalid_event_shas(
    tmp_path: Path, invalid_input: dict[str, str]
) -> None:
    repo = tmp_path / "repo"
    _init_repo(repo)

    result, trace = _run_job(repo, **invalid_input)

    assert result.returncode != 0
    assert "git cat-file" not in trace
    assert "git fetch" not in trace
    assert "git log" not in trace


@pytest.mark.parametrize("policy", ["config", "ignore"])
@pytest.mark.parametrize("event", ["push", "merge_request_event", "zero", "manual"])
def test_gitlab_scanner_rejects_policy_changes_that_hide_secret(
    tmp_path: Path, policy: str, event: str
) -> None:
    repo = tmp_path / "repo"
    base = _init_repo(repo)
    (repo / "credencial_teste.txt").write_text(_synthetic_secret(), encoding="utf-8")
    _git(repo, "add", ".")
    _git(repo, "commit", "-m", "Adiciona fixture sintetica")
    fingerprints = set()
    for scan in ("dir", "git"):
        report = tmp_path / f"{scan}.json"
        args = ["gitleaks", scan, ".", "--redact", "--no-banner", "--report-format", "json", "--report-path", str(report)]
        if scan == "git":
            args.append(f"--log-opts={base}..HEAD")
        result = subprocess.run(args, cwd=repo, capture_output=True, text=True, check=False)
        assert result.returncode == 1
        fingerprints.update(item["Fingerprint"] for item in json.loads(report.read_text()))
    if policy == "config":
        (repo / ".gitleaks.toml").write_text(
            "[extend]\nuseDefault = true\n[allowlist]\nregexes = ['.*']\n",
            encoding="utf-8",
        )
    else:
        (repo / ".gitleaksignore").write_text("\n".join(sorted(fingerprints)) + "\n", encoding="utf-8")
    _git(repo, "add", ".")
    _git(repo, "commit", "-m", "Tenta ocultar fixture na politica local")
    for scan in ("dir", "git"):
        args = ["gitleaks", scan, ".", "--redact", "--no-banner"]
        if scan == "git":
            args.append(f"--log-opts={base}..HEAD")
        bypass = subprocess.run(args, cwd=repo, capture_output=True, text=True, check=False)
        assert bypass.returncode == 0, "Fixture deve demonstrar bypass pela politica local"
    inputs = {"CI_COMMIT_BEFORE_SHA": base}
    if event == "merge_request_event":
        inputs.update(CI_PIPELINE_SOURCE=event, CI_MERGE_REQUEST_DIFF_BASE_SHA=base)
    elif event == "zero":
        inputs["CI_COMMIT_BEFORE_SHA"] = ZERO_SHA
    elif event == "manual":
        inputs["CI_PIPELINE_SOURCE"] = "web"
    ignore = repo / ".gitleaksignore"
    original_ignore = ignore.read_bytes() if ignore.exists() else None

    result, _trace = _run_job(repo, **inputs)

    assert result.returncode == 1, result.stdout + result.stderr
    expected_failures = 2 if event in {"push", "merge_request_event"} else 1
    assert result.stderr.count("leaks found:") == expected_failures
    assert (ignore.read_bytes() if ignore.exists() else None) == original_ignore
    assert not list(repo.glob("gitleaks-checkout-ignore.*"))


def test_gitlab_scanner_missing_base_config_uses_bootstrap(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    bootstrap = _init_repo(repo)
    _git(repo, "rm", ".gitleaks.toml")
    _git(repo, "commit", "-m", "Base sem configuracao")
    base = _git(repo, "rev-parse", "HEAD")
    (repo / ".gitleaks.toml").write_text(
        "[extend]\nuseDefault = true\n[allowlist]\nregexes = ['.*']\n",
        encoding="utf-8",
    )
    (repo / "credencial_teste.txt").write_text(_synthetic_secret(), encoding="utf-8")
    _git(repo, "add", ".")
    _git(repo, "commit", "-m", "Tenta introduzir politica permissiva")

    result, trace = _run_job(repo, CI_COMMIT_BEFORE_SHA=base)

    assert result.returncode == 1, result.stdout + result.stderr
    assert f"Base sem .gitleaks.toml; bootstrap fixo: {bootstrap}" in result.stdout
    assert f"git show {bootstrap}:.gitleaks.toml" in trace
    assert result.stderr.count("leaks found:") == 2


@pytest.mark.parametrize("damaged_object", ["tree", ".gitleaks.toml", ".gitleaksignore"])
def test_gitlab_scanner_git_read_failure_never_becomes_empty_policy(
    tmp_path: Path, damaged_object: str
) -> None:
    repo = tmp_path / "repo"
    _init_repo(repo)
    (repo / ".gitleaksignore").write_text("sem-correspondencia\n", encoding="utf-8")
    _git(repo, "add", ".")
    _git(repo, "commit", "-m", "Base com arquivo de exclusoes")
    base = _git(repo, "rev-parse", "HEAD")
    object_ref = f"{base}^{{tree}}" if damaged_object == "tree" else f"{base}:{damaged_object}"
    object_sha = _git(repo, "rev-parse", object_ref)
    (repo / ".git" / "objects" / object_sha[:2] / object_sha[2:]).unlink()
    temporary_root = tmp_path / "temporarios"
    temporary_root.mkdir()

    result, trace = _run_job(repo, CI_COMMIT_BEFORE_SHA=base, TMPDIR=str(temporary_root))

    assert result.returncode != 0
    assert "git log" not in trace
    assert "Base sem .gitleaks.toml" not in result.stdout
    assert "no leaks found" not in result.stderr
    assert not list(temporary_root.iterdir())


@pytest.mark.parametrize("available", [False, True])
def test_gitlab_scanner_fetches_exact_missing_bootstrap(
    tmp_path: Path, available: bool
) -> None:
    repo = tmp_path / "repo"
    remote = tmp_path / "remote"
    _init_repo(repo)
    _init_repo(remote)
    _git(remote, "commit", "--allow-empty", "-m", "Bootstrap apenas no remoto")
    bootstrap = _git(remote, "rev-parse", "HEAD") if available else "f" * 40
    _git(repo, "remote", "add", "origin", str(remote))

    result, trace = _run_job(repo, bootstrap_sha=bootstrap)

    assert f"git fetch --no-tags origin {bootstrap}" in trace
    if available:
        assert result.returncode == 0, result.stdout + result.stderr
        assert _git(repo, "rev-parse", "FETCH_HEAD") == bootstrap
    else:
        assert result.returncode != 0
        assert "git log" not in trace


def test_gitlab_scanner_restores_trusted_ignore_after_success(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    _init_repo(repo)
    (repo / "credencial_teste.txt").write_text(_synthetic_secret(), encoding="utf-8")
    report = tmp_path / "findings.json"
    signal = subprocess.run(
        ["gitleaks", "dir", ".", "--redact", "--no-banner", "--report-format", "json", "--report-path", str(report)],
        cwd=repo, capture_output=True, text=True, check=False,
    )
    assert signal.returncode == 1
    ignore = repo / ".gitleaksignore"
    ignore.write_text("\n".join(item["Fingerprint"] for item in json.loads(report.read_text())) + "\n", encoding="utf-8")
    _git(repo, "add", ".")
    _git(repo, "commit", "-m", "Base com exclusao aprovada da fixture")
    base = _git(repo, "rev-parse", "HEAD")
    _git(repo, "commit", "--allow-empty", "-m", "Alteracao limpa")
    original = ignore.read_bytes()

    result, _trace = _run_job(repo, CI_COMMIT_BEFORE_SHA=base)

    assert result.returncode == 0, result.stdout + result.stderr
    assert ignore.read_bytes() == original
    assert not list(repo.glob("gitleaks-checkout-ignore.*"))


def test_gitlab_scanner_still_scans_renamed_ignore_contents(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    base = _init_repo(repo)
    ignore = repo / ".gitleaksignore"
    original = _synthetic_secret().encode()
    ignore.write_bytes(original)
    _git(repo, "commit", "--allow-empty", "-m", "Alteracao limpa")

    result, _trace = _run_job(repo, CI_COMMIT_BEFORE_SHA=base)

    assert result.returncode == 1, result.stdout + result.stderr
    assert "leaks found:" in result.stderr
    assert ignore.read_bytes() == original
    assert not list(repo.glob("gitleaks-checkout-ignore.*"))
