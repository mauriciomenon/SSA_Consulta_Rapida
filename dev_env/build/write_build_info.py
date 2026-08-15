from __future__ import annotations

import argparse
import datetime
import json
import os
import pathlib
import subprocess
import sys


def _run_output(args: list[str], cwd: pathlib.Path, *, require_success: bool) -> str:
    try:
        result = subprocess.run(
            args,
            cwd=str(cwd),
            text=True,
            capture_output=True,
            check=False,
            timeout=20,
        )
    except OSError as exc:
        if require_success:
            print(f"Metadata command failed ({' '.join(args)}): {exc}", file=sys.stderr)
        return ""
    except subprocess.TimeoutExpired as exc:
        if require_success:
            print(f"Metadata command timed out ({' '.join(args)}): {exc}", file=sys.stderr)
        return ""
    if result.returncode != 0:
        if require_success:
            print(
                "Metadata command failed "
                f"({' '.join(args)}): exit {result.returncode}; "
                f"stdout={result.stdout.strip()!r}; stderr={result.stderr.strip()!r}",
                file=sys.stderr,
            )
            return ""
        return result.stdout.strip()
    return "\n".join(
        part.strip() for part in (result.stdout, result.stderr) if part and part.strip()
    ).strip()


def _first_line(text: str) -> str:
    for line in text.splitlines():
        line = line.strip()
        if line:
            return line
    return ""


def _first_tool_version(commands: tuple[list[str], ...], cwd: pathlib.Path) -> str:
    for command in commands:
        output = _run_output(command, cwd, require_success=False)
        if output:
            return _first_line(output)
    return ""


def _c_compiler_version(cwd: pathlib.Path) -> str:
    cc_env = os.environ.get("CC", "").strip()
    commands: list[list[str]] = []
    if cc_env:
        commands.append([cc_env, "--version"])
    commands.extend(
        (
            ["cc", "--version"],
            ["gcc", "--version"],
            ["clang", "--version"],
            ["cl"],
        )
    )
    version = _first_tool_version(tuple(commands), cwd)
    if version:
        return version
    msvc_version = os.environ.get("VCToolsVersion", "").strip()
    if msvc_version:
        return f"MSVC {msvc_version}"
    return ""


def build_payload(
    repo_root: pathlib.Path,
    build_system: str,
    platform_name: str,
    app_version: str,
) -> dict[str, str]:
    commit = _run_output(["git", "rev-parse", "HEAD"], repo_root, require_success=True)
    return {
        "app_version": app_version,
        "build_datetime": datetime.datetime.now()
        .astimezone()
        .isoformat(timespec="seconds"),
        "build_system": build_system,
        "c_compiler_version": _c_compiler_version(repo_root),
        "git_commit": commit,
        "git_commit_datetime": _run_output(
            ["git", "log", "-1", "--format=%cI"],
            repo_root,
            require_success=True,
        ),
        "git_commit_short": commit[:7] if commit else "",
        "git_commit_title": _run_output(
            ["git", "log", "-1", "--format=%s"],
            repo_root,
            require_success=True,
        ),
        "platform": platform_name,
        "rustc_version": _first_tool_version((["rustc", "--version"],), repo_root),
        "uv_version": _run_output(["uv", "--version"], repo_root, require_success=True),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=pathlib.Path, required=True)
    parser.add_argument("--output", type=pathlib.Path, required=True)
    parser.add_argument("--build-system", required=True)
    parser.add_argument("--platform", required=True)
    parser.add_argument("--app-version", required=True)
    args = parser.parse_args()

    payload = build_payload(
        args.repo_root,
        args.build_system,
        args.platform,
        args.app_version,
    )
    try:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        serialized = json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True)
        json.loads(serialized)
        args.output.write_text(serialized + "\n", encoding="utf-8")
    except OSError as exc:
        print(f"Failed to write build info: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
