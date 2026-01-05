#!/usr/bin/env python3
"""
Run pytest streaming output to terminal while writing to a log file, with external timeout.

Usage:
  python scripts/run_pytest_stream_and_log.py --test tests/test_terminal_integration.py --timeout 10

This shows output live (for interactive debugging) and also saves it to
`local_ai_private/pytest_terminal_integration_stream.log`.
"""

import argparse
import os
import subprocess
import sys
import time
from datetime import datetime


def ensure_log_path(logpath: str):
    d = os.path.dirname(logpath)
    if d and not os.path.exists(d):
        os.makedirs(d, exist_ok=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--test", required=True)
    parser.add_argument("--timeout", type=int, default=10)
    parser.add_argument("--log", default=None)
    args = parser.parse_args()

    logdir = os.path.join(os.getcwd(), "local_ai_private")
    logpath = args.log or os.path.join(logdir, "pytest_terminal_integration_stream.log")
    ensure_log_path(logpath)

    cmd = [sys.executable, "-m", "pytest", args.test]

    header = f"=== pytest streaming run at {datetime.utcnow().isoformat()}Z ===\nCommand: {' '.join(cmd)}\nTimeout: {args.timeout}s\n\n"

    start = time.time()
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)

    with open(logpath, "w", encoding="utf-8", errors="replace") as f:
        f.write(header)
        f.flush()

        try:
            while True:
                # Read line by line to stream output
                line = p.stdout.readline()
                if line:
                    print(line, end='')
                    f.write(line)
                    f.flush()
                else:
                    # No data available
                    if p.poll() is not None:
                        break

                # Timeout check
                if time.time() - start > args.timeout:
                    p.kill()
                    msg = f"\n=== TIMEOUT: pytest exceeded {args.timeout}s and was killed ===\n"
                    print(msg)
                    f.write(msg)
                    f.flush()
                    return 124

            ret = p.wait()
            footer = f"\n=== Process exited with code {ret} ===\n"
            f.write(footer)
            print(footer)
            return ret

        except Exception as e:
            try:
                p.kill()
            except Exception:
                pass
            raise


if __name__ == "__main__":
    sys.exit(main())
