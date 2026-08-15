#!/usr/bin/env python3
"""
Wrapper to run pytest with an external timeout and write stdout/stderr to a log file.

Usage:
  python scripts/run_pytest_with_timeout_v2.py --test tests/test_terminal_integration.py --timeout 60

This script writes a combined stdout/stderr log to `local_ai_private/pytest_terminal_integration.log`.
"""

import argparse
import os
import sys
from typing import Any

from pytest_stream_common import (
    DEFAULT_TIMEOUT_WRAPPER_LOG_FILENAME,
    add_timeout_wrapper_common_args,
    build_timeout_wrapper_cmd,
    build_timeout_wrapper_header,
    ensure_local_ai_dir,
    resolve_safe_logpath,
    run_logged_pytest,
)

# Ensure scripts directory is importable for helper modules
_SCRIPT_DIR = os.path.dirname(__file__)
if _SCRIPT_DIR not in sys.path:
    sys.path.insert(0, _SCRIPT_DIR)
try:
    import pwsh_discovery as _pwsh_discovery

    pwsh_discovery: Any | None = _pwsh_discovery
except Exception:
    pwsh_discovery = None


def pick_discovered_pwsh() -> str | None:
    if pwsh_discovery is None:
        return None
    pick_pwsh = getattr(pwsh_discovery, "pick_pwsh", None)
    if pick_pwsh is None:
        return None
    return pick_pwsh(os.getcwd())


def main():
    parser = argparse.ArgumentParser()
    add_timeout_wrapper_common_args(parser)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="don't execute pytest; only print what would run",
    )
    parser.add_argument(
        "--list-candidates",
        action="store_true",
        dest="list_candidates",
        help="print discovered pwsh/powershell candidates and exit",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="print discovered pwsh/powershell candidates before running",
    )
    args, extra = parser.parse_known_args()

    logdir = ensure_local_ai_dir()
    try:
        logpath = resolve_safe_logpath(logdir, args.log)
    except ValueError as exc:
        print(f"invalid log path: {exc}", file=sys.stderr)
        return 2
    try:
        cmd = build_timeout_wrapper_cmd(
            raw_test=args.test,
            extra_args=extra,
            cwd=os.getcwd(),
        )
    except ValueError as exc:
        print(f"invalid pytest target: {exc}", file=sys.stderr)
        return 2

    if not args.log:
        logpath = resolve_safe_logpath(
            logdir,
            os.path.join(logdir, DEFAULT_TIMEOUT_WRAPPER_LOG_FILENAME),
        )

    header = build_timeout_wrapper_header(cmd, args.timeout)
    # If requested, list discovered pwsh candidates and exit
    if getattr(args, "list_candidates", False):
        try:
            if pwsh_discovery is None:
                raise RuntimeError("pwsh_discovery module unavailable")
            c = pwsh_discovery.find_pwsh_candidates(os.getcwd())
            for p in c:
                print(p)
        except Exception as exc:
            print(f"pwsh_discovery not available or failed: {exc}")
        return 0

    # If verbose, print discovered candidates before proceeding
    if getattr(args, "verbose", False):
        try:
            if pwsh_discovery is None:
                raise RuntimeError("pwsh_discovery module unavailable")
            c = pwsh_discovery.find_pwsh_candidates(os.getcwd())
            print("Detected pwsh/powershell candidates:")
            for p in c:
                print(" -", p)
        except Exception as exc:
            print(f"pwsh_discovery not available or failed to list candidates: {exc}")

    # Dry-run: print header and command, write header to log, but do not execute
    if getattr(args, "dry_run", False):
        with open(logpath, "w", encoding="utf-8", errors="replace") as logf:
            logf.write(header)
            logf.write("=== DRY RUN: pytest not executed ===\n")
            logf.flush()
        print(header)
        print(
            "DRY RUN: pytest would be executed but was not run. Log written to:",
            logpath,
        )
        return 0

    return run_logged_pytest(
        cmd=cmd,
        timeout_s=args.timeout,
        logpath=logpath,
        header=header,
        kill_process_tree=True,
        pwsh_picker=pick_discovered_pwsh if pwsh_discovery is not None else None,
    )


if __name__ == "__main__":
    sys.exit(main())
