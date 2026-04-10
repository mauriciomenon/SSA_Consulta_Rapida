#!/usr/bin/env python3
"""
Wrapper to run pytest with an external timeout and write stdout/stderr to a log file.

Usage:
  python scripts/run_pytest_with_timeout.py --test tests/test_terminal_integration.py --timeout 60

This script writes a combined stdout/stderr log to `local_ai_private/pytest_terminal_integration.log`.
"""

import argparse
import os
import sys
from datetime import datetime, timezone

from pytest_stream_common import ensure_local_ai_dir
from pytest_stream_common import resolve_safe_test_target
from pytest_stream_common import run_logged_pytest


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--test",
        required=True,
        help="pytest path or args (e.g. tests/test_terminal_integration.py)",
    )
    parser.add_argument(
        "--timeout", type=int, default=60, help="timeout in seconds for the pytest run"
    )
    parser.add_argument("--log", default=None, help="optional log path")
    args, extra = parser.parse_known_args()

    logdir = ensure_local_ai_dir()
    logpath = args.log or os.path.join(logdir, "pytest_terminal_integration.log")
    try:
        test_target = resolve_safe_test_target(args.test, os.getcwd())
    except ValueError as exc:
        print(f"[ERR] invalid --test target: {exc}", file=sys.stderr)
        return 2

    cmd = [sys.executable, "-m", "pytest", test_target]
    if extra:
        cmd.extend(extra)

    header = (
        f"=== pytest wrapper run at {datetime.now(timezone.utc).isoformat()} ===\n"
        f"Command: {' '.join(cmd)}\nTimeout: {args.timeout}s\n\n"
    )
    return run_logged_pytest(
        cmd=cmd,
        timeout_s=args.timeout,
        logpath=logpath,
        header=header,
        kill_tree_default=True,
    )


if __name__ == "__main__":
    sys.exit(main())
