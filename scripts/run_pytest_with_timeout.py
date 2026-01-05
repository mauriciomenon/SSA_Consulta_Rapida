#!/usr/bin/env python3
"""
Wrapper to run pytest with an external timeout and write stdout/stderr to a log file.

Usage:
  python scripts/run_pytest_with_timeout.py --test tests/test_terminal_integration.py --timeout 10

This script writes a combined stdout/stderr log to `local_ai_private/pytest_terminal_integration.log`.
"""

import argparse
import os
import subprocess
import sys
from datetime import datetime


def ensure_local_ai_dir():
    d = os.path.join(os.getcwd(), "local_ai_private")
    os.makedirs(d, exist_ok=True)
    return d


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--test", required=True, help="pytest path or args (e.g. tests/test_terminal_integration.py)")
    parser.add_argument("--timeout", type=int, default=10, help="timeout in seconds for the pytest run")
    parser.add_argument("--log", default=None, help="optional log path")
    args, extra = parser.parse_known_args()

    logdir = ensure_local_ai_dir()
    logpath = args.log or os.path.join(logdir, "pytest_terminal_integration.log")

    cmd = [sys.executable, "-m", "pytest", args.test]
    if extra:
        cmd.extend(extra)

    header = f"=== pytest wrapper run at {datetime.utcnow().isoformat()}Z ===\nCommand: {' '.join(cmd)}\nTimeout: {args.timeout}s\n\n"

    with open(logpath, "w", encoding="utf-8", errors="replace") as logf:
        logf.write(header)
        logf.flush()
        try:
            proc = subprocess.run(cmd, stdout=logf, stderr=subprocess.STDOUT, timeout=args.timeout)
            logf.write(f"\n=== Process exited with code {proc.returncode} ===\n")
            print(f"pytest finished with exit code {proc.returncode}; log: {logpath}")
            return proc.returncode
        except subprocess.TimeoutExpired as e:
            logf.write(f"\n=== TIMEOUT: pytest exceeded {args.timeout}s and was terminated ===\n")
            logf.write("Partial output (if any):\n")
            if e.output:
                try:
                    logf.write(e.output.decode('utf-8', errors='replace'))
                except Exception:
                    logf.write(str(e.output))
            logf.write("\n=== End of partial output ===\n")
            print(f"TIMEOUT: pytest exceeded {args.timeout}s; log: {logpath}")
            return 124


if __name__ == "__main__":
    sys.exit(main())
