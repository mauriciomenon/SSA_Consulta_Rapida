from __future__ import annotations

import codecs
import json
import os
# This CI helper uses argv lists with shell=False.
import subprocess  # nosec B404
from pathlib import Path
from typing import Any

DIFF_LIMIT_BYTES = 200_000
GH_COMMAND_TIMEOUT = 120
OPENCODE_BASE_ENV_NAMES = (
    "CI",
    "HOME",
    "LANG",
    "LC_ALL",
    "PATH",
    "RUNNER_TEMP",
    "SHELL",
    "TEMP",
    "TERM",
    "TMP",
    "TMPDIR",
    "USER",
    "XDG_CACHE_HOME",
    "XDG_CONFIG_HOME",
    "XDG_DATA_HOME",
)
DEFAULT_PROMPT = (
    "Review this pull request for concrete bugs, security risks, CI/CD regressions, "
    "path/quoting problems, and release/build reproducibility issues. Comment only "
    "on actionable findings. If there are no actionable findings, say that explicitly. "
    "Do not make code changes."
)
LFS_POINTER_MARKER = "git-lfs.github.com/spec"


def extract_pr_number(event: dict[str, Any]) -> int:
    if "pull_request" in event:
        return int(event["pull_request"]["number"])
    issue = event.get("issue")
    if isinstance(issue, dict) and issue.get("pull_request") and issue.get("number") is not None:
        return int(issue["number"])
    raise ValueError("opencode review requires a pull request event or PR comment")


def truncate_diff(path: Path, output_path: Path | None = None, limit: int = DIFF_LIMIT_BYTES) -> tuple[str, bool]:
    if limit <= 0:
        raise ValueError("limit must be positive")
    notice = f"\n\n[diff truncated at {limit} bytes]\n"
    notice_size = len(notice.encode("utf-8"))
    payload_limit = max(1, limit - notice_size)
    if path.stat().st_size <= limit:
        text = path.read_text(encoding="utf-8", errors="replace")
        if output_path is not None:
            output_path.write_text(text, encoding="utf-8", newline="\n")
        return text, False
    with path.open("rb") as source:
        data = source.read(payload_limit)
    decoder = codecs.getincrementaldecoder("utf-8")(errors="replace")
    text = decoder.decode(data, final=False)
    newline = text.rfind("\n")
    if newline > 0:
        text = text[:newline]
    text = text + notice
    if output_path is not None:
        output_path.write_text(text, encoding="utf-8", newline="\n")
    return text, True


def run_checked(
    command: list[str],
    *,
    stdout_path: Path | None = None,
    timeout: int | None = None,
    env: dict[str, str] | None = None,
) -> None:
    if stdout_path is None:
        # command is an argv list; shell is never enabled.
        subprocess.run(  # nosec B603
            command,
            check=True,
            text=True,
            timeout=timeout,
            env=env,
        )
        return
    stdout_path.parent.mkdir(parents=True, exist_ok=True)
    with stdout_path.open("w", encoding="utf-8", newline="\n") as output_file:
        # command is an argv list; shell is never enabled.
        result = subprocess.run(  # nosec B603
            command,
            check=False,
            text=True,
            stdout=output_file,
            stderr=subprocess.PIPE,
            timeout=timeout,
            env=env,
        )
    if result.returncode != 0:
        print(f"Command failed with exit code {result.returncode}: {command[0]}")
        print(f"stdout captured in: {stdout_path}")
        raise subprocess.CalledProcessError(
            result.returncode,
            command,
            stderr=result.stderr,
        )


def build_prompt(base_prompt: str, diff_text: str) -> str:
    if LFS_POINTER_MARKER not in diff_text:
        return base_prompt
    return (
        base_prompt
        + "\n\nThe diff contains Git LFS pointer content. Call out that affected "
        "LFS-backed files need manual review because pointer text is not the real file content."
    )


def require_cli_option_value(name: str, value: str) -> str:
    text = str(value or "").strip()
    if not text:
        raise RuntimeError(f"{name} must not be empty")
    if text.startswith("-") or any(char.isspace() for char in text):
        raise RuntimeError(f"{name} contains an unsafe CLI option value")
    return text


def require_prompt_argument(prompt: str) -> str:
    text = str(prompt or "")
    if not text.strip():
        raise RuntimeError("PROMPT must not be empty")
    if text.lstrip().startswith("-") or "\x00" in text:
        raise RuntimeError("PROMPT contains an unsafe CLI argument")
    return text


def github_cli_env() -> dict[str, str]:
    token = os.environ.get("REVIEW_GITHUB_TOKEN") or os.environ.get("GITHUB_TOKEN")
    env = os.environ.copy()
    if token:
        env["GITHUB_TOKEN"] = token
        env["GH_TOKEN"] = token
    return env


def opencode_provider_secret_names(model: str) -> tuple[str, ...]:
    model_text = str(model or "").lower()
    if "qwen" in model_text:
        return ("QWEN_API_KEY",)
    if "glm" in model_text or "zai-" in model_text or "zhipu" in model_text:
        return ("ZAI_API_KEY", "ZHIPU_API_KEY")
    return ("OPENCODE_API_KEY",)


def opencode_env(model: str) -> dict[str, str]:
    env = {
        name: value
        for name in OPENCODE_BASE_ENV_NAMES
        if (value := os.environ.get(name)) is not None
    }
    for name in opencode_provider_secret_names(model):
        value = os.environ.get(name)
        if value:
            env[name] = value
    return env


def run_capture(
    command: list[str],
    *,
    timeout: int | None = None,
    env: dict[str, str] | None = None,
) -> str:
    result = subprocess.run(  # nosec B603
        command,
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=timeout,
        env=env,
    )
    return result.stdout


def ensure_trusted_pr_source(pr_number: int, repository: str) -> None:
    if not repository:
        raise RuntimeError("GITHUB_REPOSITORY is required for PR trust checks")
    output = run_capture(
        [
            "gh",
            "pr",
            "view",
            str(pr_number),
            "--json",
            "headRepository",
        ],
        env=github_cli_env(),
        timeout=GH_COMMAND_TIMEOUT,
    )
    data = json.loads(output)
    head_repository = data.get("headRepository")
    if not isinstance(head_repository, dict):
        raise RuntimeError("Could not determine PR head repository")
    name_with_owner = str(head_repository.get("nameWithOwner") or "")
    if name_with_owner != repository:
        raise RuntimeError(
            "Refusing to process untrusted PR diff with opencode secrets in scope"
        )


def fetch_pr_diff(pr_number: int, diff_file: Path) -> None:
    run_checked(
        ["gh", "pr", "diff", str(pr_number), "--patch"],
        stdout_path=diff_file,
        env=github_cli_env(),
        timeout=GH_COMMAND_TIMEOUT,
    )


def run_opencode_review(model: str, agent: str, review_diff_file: Path, prompt: str, review_file: Path) -> None:
    safe_model = require_cli_option_value("MODEL", model)
    safe_agent = require_cli_option_value("AGENT", agent)
    safe_prompt = require_prompt_argument(prompt)
    run_checked(
        [
            "opencode",
            "run",
            "--model",
            safe_model,
            "--agent",
            safe_agent,
            "--file",
            str(review_diff_file),
            "--format",
            "default",
            safe_prompt,
        ],
        stdout_path=review_file,
        timeout=1200,
        env=opencode_env(safe_model),
    )


def write_comment_body(body_file: Path, *, model: str, workflow: str, job: str, review_text: str) -> None:
    body_file.write_text(
        "\n".join(
            [
                "### opencode review",
                "",
                f"- model: `{model}`",
                "- mode: review-only",
                f"- source: `{workflow}` / `{job}`",
                "",
                review_text,
            ]
        ),
        encoding="utf-8",
        newline="\n",
    )


def post_pr_comment(pr_number: int, body_file: Path) -> None:
    run_checked(
        ["gh", "pr", "comment", str(pr_number), "--body-file", str(body_file)],
        env=github_cli_env(),
        timeout=GH_COMMAND_TIMEOUT,
    )


def required_env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(f"Required environment variable is missing: {name}")
    return value


def main() -> int:
    event_path = Path(required_env("GITHUB_EVENT_PATH"))
    runner_temp = Path(required_env("RUNNER_TEMP"))
    model = require_cli_option_value("MODEL", required_env("MODEL"))
    agent = require_cli_option_value("AGENT", os.environ.get("AGENT") or "plan")
    workflow = os.environ.get("GITHUB_WORKFLOW", "opencode")
    job = os.environ.get("GITHUB_JOB", "opencode")
    prompt = require_prompt_argument(os.environ.get("PROMPT") or DEFAULT_PROMPT)

    event = json.loads(event_path.read_text(encoding="utf-8"))
    pr_number = extract_pr_number(event)
    ensure_trusted_pr_source(pr_number, os.environ.get("GITHUB_REPOSITORY", ""))

    diff_file = runner_temp / f"opencode-pr-{pr_number}.diff"
    review_diff_file = runner_temp / f"opencode-pr-{pr_number}-review.diff"
    review_file = runner_temp / f"opencode-review-{pr_number}.md"
    body_file = runner_temp / f"opencode-comment-{pr_number}.md"

    fetch_pr_diff(pr_number, diff_file)
    diff_text, _ = truncate_diff(diff_file, output_path=review_diff_file)
    prompt = build_prompt(prompt, diff_text)

    run_opencode_review(model, agent, review_diff_file, prompt, review_file)
    review_text = review_file.read_text(encoding="utf-8", errors="replace")
    write_comment_body(body_file, model=model, workflow=workflow, job=job, review_text=review_text)
    post_pr_comment(pr_number, body_file)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
