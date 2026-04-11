#!/usr/bin/env python3
"""
Run pytest streaming output to terminal while writing to a log file, with external timeout.

Usage:
  python scripts/run_pytest_stream_and_log.py --test tests/test_terminal_integration.py --timeout 60

This shows output live (for interactive debugging) and also saves it to
`local_ai_private/pytest_terminal_integration_stream.log`.

Exit codes:
  0: pytest finished successfully
  >0: pytest failure or runner error
  124: timeout reached and process was terminated
"""

import argparse
import json
import os
import sys

from pytest_stream_common import ensure_log_path, get_stream_logger
from pytest_stream_common import resolve_safe_logpath as _resolve_safe_logpath
from pytest_stream_common import resolve_safe_test_target as _resolve_safe_test_target
from pytest_stream_common import run_streaming_pytest

logger = get_stream_logger(__name__)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--test", required=True)
    parser.add_argument("--timeout", type=int, default=None)
    parser.add_argument("--log", default=None)
    parser.add_argument(
        "--fallback-tee",
        action="store_true",
        help="If streaming fails, print instruction for tee fallback",
    )
    args = parser.parse_args()

    # Try to read workspace settings for defaults
    ws_settings = {}
    try:
        ws_path = os.path.join(os.getcwd(), ".vscode", "settings.json")
        if os.path.exists(ws_path):
            with open(ws_path, "r", encoding="utf-8") as wf:
                ws_settings = json.load(wf)
    except Exception:
        ws_settings = {}

    if args.timeout is None:
        args.timeout = int(ws_settings.get("pytestWrapper", {}).get("timeout", 60))

    fallback_to_tee = bool(
        ws_settings.get("pytestWrapper", {}).get("fallbackToTee", False)
        or args.fallback_tee
    )
    kill_process_tree = bool(
        ws_settings.get("pytestWrapper", {}).get("killProcessTree", True)
    )

    logdir = os.path.join(os.getcwd(), "local_ai_private")
    try:
        logpath = _resolve_safe_logpath(logdir, args.log)
    except ValueError as exc:
        logger.error("invalid stream log path: %s", exc)
        return 2
    ensure_log_path(logpath)
    try:
        test_target = _resolve_safe_test_target(args.test, os.getcwd())
    except ValueError as exc:
        logger.error("invalid --test target: %s", exc)
        return 2

    cmd = [sys.executable, "-m", "pytest", test_target]
    return run_streaming_pytest(
        cmd=cmd,
        timeout_s=args.timeout,
        logpath=logpath,
        fallback_to_tee=fallback_to_tee,
        test_arg=test_target,
        kill_process_tree=kill_process_tree,
    )


if __name__ == "__main__":
    sys.exit(main())
