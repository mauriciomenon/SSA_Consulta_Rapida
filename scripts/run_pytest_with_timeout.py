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

from pytest_stream_common import (
    DEFAULT_TIMEOUT_WRAPPER_LOG_FILENAME,
    add_timeout_wrapper_common_args,
    build_timeout_wrapper_cmd,
    build_timeout_wrapper_header,
    ensure_local_ai_dir,
    run_logged_pytest,
)


def main():
    parser = argparse.ArgumentParser()
    add_timeout_wrapper_common_args(parser)
    args, extra = parser.parse_known_args()

    logdir = ensure_local_ai_dir()
    logpath = args.log or os.path.join(logdir, DEFAULT_TIMEOUT_WRAPPER_LOG_FILENAME)
    try:
        cmd = build_timeout_wrapper_cmd(
            raw_test=args.test,
            extra_args=extra,
            cwd=os.getcwd(),
        )
    except ValueError as exc:
        print(f"[ERR] invalid --test target: {exc}", file=sys.stderr)
        return 2

    header = build_timeout_wrapper_header(cmd, args.timeout)
    return run_logged_pytest(
        cmd=cmd,
        timeout_s=args.timeout,
        logpath=logpath,
        header=header,
        kill_process_tree=True,
    )


if __name__ == "__main__":
    sys.exit(main())
