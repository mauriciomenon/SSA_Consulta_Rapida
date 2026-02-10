#!/usr/bin/env python3
"""
Wrapper to run pytest with an external timeout and write stdout/stderr to a log file.

Usage:
  python scripts/run_pytest_with_timeout.py --test tests/test_terminal_integration.py --timeout 10

This script writes a combined stdout/stderr log to `local_ai_private/pytest_terminal_integration.log`.
"""

import argparse
import os
import shutil
import signal
import subprocess
import sys
from datetime import datetime, timezone


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

    header = (
        f"=== pytest wrapper run at {datetime.now(timezone.utc).isoformat()} ===\n"
        f"Command: {' '.join(cmd)}\nTimeout: {args.timeout}s\n\n"
    )

    with open(logpath, "w", encoding="utf-8", errors="replace") as logf:
        logf.write(header)
        logf.flush()
        try:
            popen_kwargs = {}
            if os.name != 'nt':
                # Isolate child process group so killpg does not target this wrapper process.
                popen_kwargs["start_new_session"] = True
            proc = subprocess.Popen(
                cmd,
                stdout=logf,
                stderr=subprocess.STDOUT,
                **popen_kwargs,
            )
            try:
                proc.wait(timeout=args.timeout)
                logf.write(f"\n=== Process exited with code {proc.returncode} ===\n")
                print(f"pytest finished with exit code {proc.returncode}; log: {logpath}")
                return proc.returncode
            except subprocess.TimeoutExpired:
                # Timeout: attempt to kill process tree
                try:
                    if os.name == 'nt':
                        res = subprocess.run(["taskkill", "/PID", str(proc.pid), "/T", "/F"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                        if res.returncode != 0:
                            # fallback to PowerShell Stop-Process if taskkill is not available/succeeds
                            pwsh = shutil.which("pwsh") or shutil.which("powershell")
                            if pwsh:
                                try:
                                    subprocess.run([pwsh, "-NoProfile", "-NonInteractive", "-Command", f"Stop-Process -Id {proc.pid} -Force -ErrorAction SilentlyContinue"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                                except Exception:
                                    try:
                                        proc.kill()
                                    except Exception:
                                        pass
                            else:
                                try:
                                    proc.kill()
                                except Exception:
                                    pass
                    else:
                        try:
                            os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
                        except Exception:
                            proc.kill()
                except Exception:
                    try:
                        proc.kill()
                    except Exception:
                        pass

                try:
                    proc.wait(timeout=5)
                except Exception:
                    pass

                logf.write(f"\n=== TIMEOUT: pytest exceeded {args.timeout}s and was terminated ===\n")
                print(f"TIMEOUT: pytest exceeded {args.timeout}s; log: {logpath}")
                return 124
        except BaseException as e:
            logf.write(f"\n=== ERROR: {e} ===\n")
            raise


if __name__ == "__main__":
    sys.exit(main())
