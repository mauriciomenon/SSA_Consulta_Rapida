#!/usr/bin/env python3
"""
Run pytest streaming output to terminal while writing to a log file, with external timeout.

Usage:
  python scripts/run_pytest_stream_and_log_v2.py --test tests/test_terminal_integration.py --timeout 10

This shows output live (for interactive debugging) and also saves it to
`local_ai_private/pytest_terminal_integration_stream.log`.
"""

import argparse
import json
import os
import queue
import signal
import subprocess
import sys
import time
import shutil
import threading
from datetime import datetime, timezone

# Ensure scripts directory is importable for helper modules
_SCRIPT_DIR = os.path.dirname(__file__)
if _SCRIPT_DIR not in sys.path:
    sys.path.insert(0, _SCRIPT_DIR)
try:
    import pwsh_discovery
except Exception:
    pwsh_discovery = None


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
    parser.add_argument("--dry-run", action="store_true", help="don't execute pytest; only print what would run")
    parser.add_argument("--list-candidates", action="store_true", help="print discovered pwsh/powershell candidates and exit")
    parser.add_argument("--verbose", action="store_true", help="print discovered pwsh/powershell candidates before running")
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

    header = (
        f"=== pytest streaming run at {datetime.now(timezone.utc).isoformat()} ===\n"
        f"Command: {' '.join(cmd)}\nTimeout: {args.timeout}s\n\n"
    )

    start = time.time()
    # Dry-run: print header and command, write header to log, but do not execute
    if getattr(args, "dry_run", False):
        logdir = os.path.join(os.getcwd(), "local_ai_private")
        logpath = args.log or os.path.join(logdir, "pytest_terminal_integration_stream.log")
        ensure_log_path(logpath)
        with open(logpath, "w", encoding="utf-8", errors="replace") as f:
            f.write(header)
            f.write("=== DRY RUN: streaming wrapper did not execute pytest ===\n")
            f.flush()
        print(header)
        print("DRY RUN: streaming wrapper would have started pytest. Log written to:", logpath)
        return 0

    if getattr(args, "list_candidates", False):
        try:
            c = pwsh_discovery.find_pwsh_candidates(os.getcwd())
            for p in c:
                print(p)
        except Exception as exc:
            print(f"pwsh_discovery not available or failed: {exc}")
        return 0

    # If verbose, print discovered candidates before proceeding
    if getattr(args, "verbose", False):
        try:
            c = pwsh_discovery.find_pwsh_candidates(os.getcwd())
            print("Detected pwsh/powershell candidates:")
            for p in c:
                print(" -", p)
        except Exception as exc:
            print(f"pwsh_discovery not available or failed to list candidates: {exc}")

    # Start process in a new process group on Unix so we can kill the group; on Windows we'll use taskkill
    if os.name == 'nt':
        p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    else:
        p = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            start_new_session=True,
        )

    line_queue: "queue.Queue[str | None]" = queue.Queue(maxsize=4096)

    def _safe_queue_put(value: str | None) -> None:
        while True:
            try:
                line_queue.put(value, timeout=0.1)
                return
            except queue.Full:
                # Apply bounded backpressure and avoid unbounded memory use.
                if p.poll() is not None:
                    try:
                        line_queue.get_nowait()
                    except queue.Empty:
                        pass
                    try:
                        line_queue.put_nowait(value)
                    except queue.Full:
                        pass
                    return

    def _reader_worker() -> None:
        try:
            if p.stdout is None:
                return
            while True:
                try:
                    raw_line = p.stdout.readline()
                except BaseException as exc:
                    _safe_queue_put(f"[WARN] reader thread error: {exc}\n")
                    break
                if raw_line == "":
                    break
                _safe_queue_put(raw_line)
        finally:
            _safe_queue_put(None)

    reader_thread = threading.Thread(target=_reader_worker, daemon=True)
    reader_thread.start()

    with open(logpath, "w", encoding="utf-8", errors="replace") as f:
        f.write(header)
        f.flush()

        try:
            reader_done = False
            while True:
                # Timeout must be enforced independently from child stdout flow.
                if time.time() - start > args.timeout:
                    # Attempt graceful shutdown of process tree
                    try:
                        if os.name == 'nt':
                            if kill_tree_default:
                                # Use taskkill to kill process tree on Windows
                                res = subprocess.run(
                                    ["taskkill", "/PID", str(p.pid), "/T", "/F"],
                                    stdout=subprocess.DEVNULL,
                                    stderr=subprocess.DEVNULL,
                                )
                                if res.returncode != 0:
                                    # fallback to PowerShell Stop-Process
                                    pwsh = None
                                    if pwsh_discovery:
                                        pwsh = pwsh_discovery.pick_pwsh(os.getcwd())
                                    if not pwsh:
                                        pwsh = shutil.which("pwsh") or shutil.which("powershell")
                                    if pwsh:
                                        try:
                                            subprocess.run(
                                                [
                                                    pwsh,
                                                    "-NoProfile",
                                                    "-NonInteractive",
                                                    "-Command",
                                                    f"Stop-Process -Id {p.pid} -Force -ErrorAction SilentlyContinue",
                                                ],
                                                stdout=subprocess.DEVNULL,
                                                stderr=subprocess.DEVNULL,
                                            )
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

                    try:
                        p.wait(timeout=5)
                    except Exception:
                        try:
                            if os.name == "nt":
                                p.kill()
                            else:
                                try:
                                    os.killpg(os.getpgid(p.pid), signal.SIGKILL)
                                except Exception:
                                    p.kill()
                        except Exception:
                            pass
                        try:
                            p.wait(timeout=5)
                        except Exception:
                            pass

                    msg = f"\n=== TIMEOUT: pytest exceeded {args.timeout}s and was terminated ===\n"
                    print(msg)
                    f.write(msg)
                    f.flush()

                    if fallback_to_tee:
                        logpath_ps = logpath.replace("/", "\\")
                        print(
                            "Fallback: to stream+log use (PowerShell):\n"
                            f'python -m pytest "{args.test}" 2>&1 | Tee-Object -FilePath '
                            f'"{logpath_ps}"'
                        )

                    reader_thread.join(timeout=1.0)
                    return 124

                try:
                    queued_line = line_queue.get(timeout=0.2)
                except queue.Empty:
                    queued_line = ""

                if queued_line is None:
                    reader_done = True
                elif queued_line:
                    print(queued_line, end="")
                    f.write(queued_line)
                    f.flush()

                if reader_done and p.poll() is not None and line_queue.empty():
                    break

            ret = p.wait()
            footer = f"\n=== Process exited with code {ret} ===\n"
            f.write(footer)
            print(footer)
            reader_thread.join(timeout=1.0)
            return ret

        except BaseException:
            try:
                if os.name == "nt":
                    res = subprocess.run(
                        ["taskkill", "/PID", str(p.pid), "/T", "/F"],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                    )
                    if res.returncode != 0:
                        p.kill()
                else:
                    try:
                        os.killpg(os.getpgid(p.pid), signal.SIGKILL)
                    except Exception:
                        p.kill()
            except Exception:
                pass
            try:
                p.wait(timeout=5)
            except Exception:
                pass
            try:
                reader_thread.join(timeout=1.0)
            except Exception:
                pass
            raise


if __name__ == "__main__":
    sys.exit(main())
