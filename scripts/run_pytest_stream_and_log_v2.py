#!/usr/bin/env python3
"""
Run pytest streaming output to terminal while writing to a log file.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from typing import Any

from pytest_stream_common import ensure_log_path, get_stream_logger
from pytest_stream_common import resolve_safe_logpath as _resolve_safe_logpath
from pytest_stream_common import resolve_safe_test_target as _resolve_safe_test_target
from pytest_stream_common import run_streaming_pytest

# Ensure scripts directory is importable for helper modules
_SCRIPT_DIR = os.path.dirname(__file__)
if _SCRIPT_DIR not in sys.path:
    sys.path.insert(0, _SCRIPT_DIR)
try:
    import pwsh_discovery as _pwsh_discovery

    pwsh_discovery: Any | None = _pwsh_discovery
except Exception:
    pwsh_discovery = None

logger = get_stream_logger(__name__)


def _pick_pwsh() -> str | None:
    if pwsh_discovery is None:
        return None
    try:
        return pwsh_discovery.pick_pwsh(os.getcwd())
    except Exception:
        return None


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
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="do not execute pytest; only print what would run",
    )
    parser.add_argument(
        "--list-candidates",
        action="store_true",
        help="print discovered pwsh/powershell candidates and exit",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="print discovered pwsh/powershell candidates before running",
    )
    args = parser.parse_args()

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
    try:
        test_target = _resolve_safe_test_target(args.test, os.getcwd())
    except ValueError as exc:
        logger.error("invalid pytest target: %s", exc)
        return 2
    ensure_log_path(logpath)

    cmd = [sys.executable, "-m", "pytest", test_target]
    header = (
        f"=== pytest streaming run at {datetime.now(timezone.utc).isoformat()} ===\n"
        f"Command: {' '.join(cmd)}\nTimeout: {args.timeout}s\n\n"
    )

    if args.dry_run:
        with open(logpath, "w", encoding="utf-8", errors="replace") as f:
            f.write(header)
            f.write("=== DRY RUN: streaming wrapper did not execute pytest ===\n")
            f.flush()
        print(header)
        print(
            "DRY RUN: streaming wrapper would have started pytest. Log written to:",
            logpath,
        )
        return 0

    if args.list_candidates:
        try:
            if pwsh_discovery is None:
                raise RuntimeError("pwsh_discovery module unavailable")
            for candidate in pwsh_discovery.find_pwsh_candidates(os.getcwd()):
                print(candidate)
        except Exception as exc:
            print(f"pwsh_discovery not available or failed: {exc}")
        return 0

    if args.verbose:
        try:
            if pwsh_discovery is None:
                raise RuntimeError("pwsh_discovery module unavailable")
            print("Detected pwsh/powershell candidates:")
            for candidate in pwsh_discovery.find_pwsh_candidates(os.getcwd()):
                print(" -", candidate)
        except Exception as exc:
            print(f"pwsh_discovery not available or failed to list candidates: {exc}")

    return run_streaming_pytest(
        cmd=cmd,
        timeout_s=args.timeout,
        logpath=logpath,
        fallback_to_tee=fallback_to_tee,
        test_arg=test_target,
        kill_process_tree=kill_process_tree,
        pwsh_picker=_pick_pwsh,
    )


if __name__ == "__main__":
    sys.exit(main())
