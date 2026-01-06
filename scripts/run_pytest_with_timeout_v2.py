#!/usr/bin/env python3
"""
Wrapper to run pytest with an external timeout and write stdout/stderr to a log file.

Usage:
  python scripts/run_pytest_with_timeout_v2.py --test tests/test_terminal_integration.py --timeout 10

This script writes a combined stdout/stderr log to `local_ai_private/pytest_terminal_integration.log`.
"""

import argparse
import os
import subprocess
import sys
import signal
import shutil
from datetime import datetime

# Ensure scripts directory is importable for helper modules
_SCRIPT_DIR = os.path.dirname(__file__)
if _SCRIPT_DIR not in sys.path:
    sys.path.insert(0, _SCRIPT_DIR)
try:
    import pwsh_discovery
except Exception:
    pwsh_discovery = None


def ensure_local_ai_dir():
    d = os.path.join(os.getcwd(), "local_ai_private")
    os.makedirs(d, exist_ok=True)
    return d


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--test", required=True, help="pytest path or args (e.g. tests/test_terminal_integration.py)")
    parser.add_argument("--timeout", type=int, default=10, help="timeout in seconds for the pytest run")
    parser.add_argument("--log", default=None, help="optional log path")
    parser.add_argument("--dry-run", action="store_true", help="don't execute pytest; only print what would run")
    parser.add_argument("--list-candidates", action="store_true", dest="list_candidates", help="print discovered pwsh/powershell candidates and exit")
    parser.add_argument("--verbose", action="store_true", help="print discovered pwsh/powershell candidates before running")
    args, extra = parser.parse_known_args()

    logdir = ensure_local_ai_dir()
    logpath = args.log or os.path.join(logdir, "pytest_terminal_integration.log")

    cmd = [sys.executable, "-m", "pytest", args.test]
    if extra:
        cmd.extend(extra)

    header = f"=== pytest wrapper run at {datetime.utcnow().isoformat()}Z ===\nCommand: {' '.join(cmd)}\nTimeout: {args.timeout}s\n\n"
    # If requested, list discovered pwsh candidates and exit
    if getattr(args, "list_candidates", False):
        try:
            import pwsh_discovery
            c = pwsh_discovery.find_pwsh_candidates(os.getcwd())
            for p in c:
                print(p)
        except Exception:
            print("pwsh_discovery not available or failed")
        return 0

    # If verbose, print discovered candidates before proceeding
    if getattr(args, "verbose", False):
        try:
            import pwsh_discovery
            c = pwsh_discovery.find_pwsh_candidates(os.getcwd())
            print("Detected pwsh/powershell candidates:")
            for p in c:
                print(" -", p)
        except Exception:
            print("pwsh_discovery not available or failed to list candidates")

    # Dry-run: print header and command, write header to log, but do not execute
    if getattr(args, "dry_run", False):
        with open(logpath, "w", encoding="utf-8", errors="replace") as logf:
            logf.write(header)
            logf.write("=== DRY RUN: pytest not executed ===\n")
            logf.flush()
        print(header)
        print("DRY RUN: pytest would be executed but was not run. Log written to:", logpath)
        return 0

    with open(logpath, "w", encoding="utf-8", errors="replace") as logf:
        logf.write(header)
        logf.flush()
        try:
            proc = subprocess.Popen(cmd, stdout=logf, stderr=subprocess.STDOUT)
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
                            # fallback to PowerShell Stop-Process if taskkill did not succeed
                            pwsh = None
                            if pwsh_discovery:
                                pwsh = pwsh_discovery.pick_pwsh(os.getcwd())
                            if not pwsh:
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

                logf.write(f"\n=== TIMEOUT: pytest exceeded {args.timeout}s and was terminated ===\n")
                print(f"TIMEOUT: pytest exceeded {args.timeout}s; log: {logpath}")
                return 124
        except Exception as e:
            logf.write(f"\n=== ERROR: {e} ===\n")
            raise


if __name__ == "__main__":
    sys.exit(main())
