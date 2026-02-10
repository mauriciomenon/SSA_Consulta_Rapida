#!/usr/bin/env python3
"""
Run pytest streaming output to terminal while writing to a log file, with external timeout.

Usage:
  python scripts/run_pytest_stream_and_log.py --test tests/test_terminal_integration.py --timeout 10

This shows output live (for interactive debugging) and also saves it to
`local_ai_private/pytest_terminal_integration_stream.log`.
"""

import argparse
import json
import os
import signal
import shutil
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
    parser.add_argument("--timeout", type=int, default=None)
    parser.add_argument("--log", default=None)
    parser.add_argument("--fallback-tee", action="store_true", help="If streaming fails, print instruction for tee fallback")
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
        args.timeout = int(ws_settings.get("pytestWrapper", {}).get("timeout", 10))

    fallback_to_tee = bool(ws_settings.get("pytestWrapper", {}).get("fallbackToTee", False) or args.fallback_tee)
    kill_tree_default = bool(ws_settings.get("pytestWrapper", {}).get("killProcessTree", True))

    logdir = os.path.join(os.getcwd(), "local_ai_private")
    logpath = args.log or os.path.join(logdir, "pytest_terminal_integration_stream.log")
    ensure_log_path(logpath)

    cmd = [sys.executable, "-m", "pytest", args.test]

    header = f"=== pytest streaming run at {datetime.utcnow().isoformat()}Z ===\nCommand: {' '.join(cmd)}\nTimeout: {args.timeout}s\n\n"

    start = time.time()
    # Start process in a new process group on Unix so we can kill the group; on Windows we'll use taskkill
    if os.name == 'nt':
        p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    else:
        p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, preexec_fn=os.setsid)

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
                    # Attempt graceful shutdown of process tree
                    try:
                        if os.name == 'nt' and kill_tree_default:
                            # Use taskkill to kill process tree on Windows
                            res = subprocess.run(["taskkill", "/PID", str(p.pid), "/T", "/F"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                            if res.returncode != 0:
                                # fallback to PowerShell Stop-Process
                                pwsh = shutil.which("pwsh") or shutil.which("powershell")
                                if pwsh:
                                    try:
                                        subprocess.run([pwsh, "-NoProfile", "-NonInteractive", "-Command", f"Stop-Process -Id {p.pid} -Force -ErrorAction SilentlyContinue"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                                    except Exception:
                                        try:
                                            p.kill()
                                        except Exception:
                                            pass
                                else:
                                    try:
                                        p.kill()
                                    except Exception:
                                        pass
                        else:
                            # Unix: kill process group
                            try:
                                os.killpg(os.getpgid(p.pid), signal.SIGTERM)
                            except Exception:
                                p.kill()
                    except Exception:
                        try:
                            p.kill()
                        except Exception:
                            pass

                    msg = f"\n=== TIMEOUT: pytest exceeded {args.timeout}s and was terminated ===\n"
                    print(msg)
                    f.write(msg)
                    f.flush()

                    if fallback_to_tee:
                        print("Fallback: to stream+log use (PowerShell):\npython -m pytest tests/test_terminal_integration.py 2>&1 | Tee-Object -FilePath local_ai_private\pytest_terminal_integration.log")

                    return 124

            ret = p.wait()
            footer = f"\n=== Process exited with code {ret} ===\n"
            f.write(footer)
            print(footer)
            return ret

        except Exception:
            try:
                p.kill()
            except Exception:
                pass
            raise


if __name__ == "__main__":
    sys.exit(main())
