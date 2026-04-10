from __future__ import annotations

import os
import queue
import shutil
import signal
import subprocess
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from utils.robust_logging import get_robust_logger

DEFAULT_LOG_FILENAME = "pytest_terminal_integration_stream.log"


def get_stream_logger(name: str):
    return get_robust_logger().get_logger(name, "cli")


def ensure_log_path(logpath: str) -> None:
    d = os.path.dirname(logpath)
    if d and not os.path.exists(d):
        os.makedirs(d, exist_ok=True)


def queue_maxsize() -> int:
    raw = os.environ.get("PYTEST_STREAM_QUEUE_MAX")
    if not raw:
        return 4096
    try:
        value = int(raw)
    except ValueError:
        return 4096
    if value < 256:
        return 256
    if value > 65536:
        return 65536
    return value


def flush_every_lines() -> int:
    raw = os.environ.get("PYTEST_STREAM_FLUSH_EVERY")
    if not raw:
        return 64
    try:
        value = int(raw)
    except ValueError:
        return 64
    if value < 1:
        return 1
    if value > 4096:
        return 4096
    return value


def dropped_warn_every_lines() -> int:
    raw = os.environ.get("PYTEST_STREAM_DROPPED_WARN_EVERY")
    if not raw:
        return 200
    try:
        value = int(raw)
    except ValueError:
        return 200
    if value < 10:
        return 10
    if value > 10000:
        return 10000
    return value


def queue_poll_timeout_seconds() -> float:
    raw = os.environ.get("PYTEST_STREAM_QUEUE_POLL_TIMEOUT_MS")
    if not raw:
        return 0.2
    try:
        value_ms = int(raw)
    except ValueError:
        return 0.2
    if value_ms < 20:
        value_ms = 20
    if value_ms > 2000:
        value_ms = 2000
    return float(value_ms) / 1000.0


def reader_join_timeout_seconds() -> float:
    raw = os.environ.get("PYTEST_STREAM_READER_JOIN_TIMEOUT_MS")
    if not raw:
        return 1.0
    try:
        value_ms = int(raw)
    except ValueError:
        return 1.0
    if value_ms < 100:
        value_ms = 100
    if value_ms > 5000:
        value_ms = 5000
    return float(value_ms) / 1000.0


def resolve_safe_logpath(logdir: str, user_log: str | None) -> str:
    from utils.path_safety import PathSafetyError, ensure_path_is_allowed

    base_dir = os.path.abspath(logdir)
    if not user_log:
        return os.path.join(base_dir, DEFAULT_LOG_FILENAME)
    try:
        resolved_path = ensure_path_is_allowed(
            user_log,
            purpose="stream_log_path",
            base=Path(base_dir),
            expect_directory=False,
        )
    except PathSafetyError as exc:
        raise ValueError(str(exc)) from exc
    resolved = str(resolved_path)
    common = os.path.commonpath([base_dir, resolved])
    if common != base_dir:
        raise ValueError(f"--log must stay under {base_dir}")
    return resolved


def resolve_safe_test_target(raw_test: str, cwd: str | None = None) -> str:
    from utils.path_safety import PathSafetyError, ensure_path_is_allowed

    if not raw_test or not raw_test.strip():
        raise ValueError("--test must not be empty")
    if raw_test.startswith("-"):
        raise ValueError("--test must be a pytest path or nodeid, not a flag")

    base_dir = Path(cwd or os.getcwd()).resolve()
    path_part, separator, node_part = raw_test.partition("::")
    try:
        resolved_path = ensure_path_is_allowed(
            path_part,
            purpose="pytest_test_target",
            base=base_dir,
            expect_directory=None,
            extra_allowed_roots=[base_dir],
        )
    except PathSafetyError as exc:
        raise ValueError(str(exc)) from exc

    resolved = os.fspath(resolved_path)
    if separator:
        return f"{resolved}{separator}{node_part}"
    return resolved


def _terminate_process(
    process: subprocess.Popen[str],
    *,
    kill_tree_default: bool,
    pwsh_picker: Callable[[], str | None] | None,
    logger,
) -> None:
    try:
        if os.name == "nt":
            if kill_tree_default:
                res = subprocess.run(
                    ["taskkill", "/PID", str(process.pid), "/T", "/F"],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                if res.returncode != 0:
                    pwsh = pwsh_picker() if pwsh_picker else None
                    if not pwsh:
                        pwsh = shutil.which("pwsh") or shutil.which("powershell")
                    if pwsh:
                        subprocess.run(
                            [
                                pwsh,
                                "-NoProfile",
                                "-NonInteractive",
                                "-Command",
                                f"Stop-Process -Id {process.pid} -Force -ErrorAction SilentlyContinue",
                            ],
                            stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL,
                        )
                    else:
                        process.kill()
            else:
                process.kill()
        else:
            try:
                os.killpg(os.getpgid(process.pid), signal.SIGTERM)
            except (ProcessLookupError, PermissionError, OSError) as exc:
                logger.warning("SIGTERM process group failed: %s", exc)
                process.kill()
    except (
        ProcessLookupError,
        PermissionError,
        OSError,
        subprocess.SubprocessError,
    ) as exc:
        logger.warning("terminate process failed: %s", exc)
        try:
            process.kill()
        except (ProcessLookupError, PermissionError, OSError) as kill_exc:
            logger.warning("final process kill failed: %s", kill_exc)


def _wait_for_termination(process: subprocess.Popen[str], *, logger) -> None:
    try:
        process.wait(timeout=5)
    except (subprocess.TimeoutExpired, subprocess.SubprocessError, OSError) as exc:
        logger.warning("wait for process termination timed out or failed: %s", exc)
        try:
            if os.name == "nt":
                process.kill()
            else:
                try:
                    os.killpg(os.getpgid(process.pid), signal.SIGKILL)
                except (ProcessLookupError, PermissionError, OSError) as killpg_exc:
                    logger.warning("SIGKILL process group failed: %s", killpg_exc)
                    process.kill()
        except (ProcessLookupError, PermissionError, OSError) as kill_exc:
            logger.warning("forced process kill failed: %s", kill_exc)
        try:
            process.wait(timeout=5)
        except (
            subprocess.TimeoutExpired,
            subprocess.SubprocessError,
            OSError,
        ) as wait_exc:
            logger.warning("second wait for process termination failed: %s", wait_exc)


def run_streaming_pytest(
    *,
    cmd: list[str],
    timeout_s: int,
    logpath: str,
    fallback_to_tee: bool,
    test_arg: str,
    kill_tree_default: bool,
    pwsh_picker: Callable[[], str | None] | None = None,
) -> int:
    robust_logger = get_robust_logger().get_logger(__name__, "cli")
    header = (
        f"=== pytest streaming run at {datetime.now(timezone.utc).isoformat()} ===\n"
        f"Command: {' '.join(cmd)}\nTimeout: {timeout_s}s\n\n"
    )

    start = time.time()
    if os.name == "nt":
        process = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True
        )
    else:
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            start_new_session=True,
        )

    line_queue: "queue.Queue[str | None]" = queue.Queue(maxsize=queue_maxsize())
    dropped_lines = 0
    dropped_lock = threading.Lock()
    last_warned = 0
    reader_done = threading.Event()
    dropped_warn_every = dropped_warn_every_lines()
    queue_poll_timeout = queue_poll_timeout_seconds()
    reader_join_timeout = reader_join_timeout_seconds()

    def _best_effort_queue_put(value: str | None) -> None:
        nonlocal dropped_lines, last_warned
        try:
            line_queue.put_nowait(value)
            return
        except queue.Full:
            pass
        evicted = False
        try:
            line_queue.get_nowait()
            evicted = True
        except queue.Empty:
            pass
        if evicted:
            with dropped_lock:
                if value is not None:
                    dropped_lines += 1
        try:
            line_queue.put_nowait(value)
            return
        except queue.Full:
            with dropped_lock:
                if value is None:
                    return
                dropped_lines += 1
                warn_count = dropped_lines
                should_warn = warn_count == 1 or (
                    warn_count % dropped_warn_every == 0 and warn_count != last_warned
                )
                if should_warn:
                    last_warned = warn_count
            if should_warn:
                robust_logger.warning(
                    "output queue full; dropped %s line(s)", warn_count
                )

    def _reader_worker() -> None:
        try:
            if process.stdout is None:
                return
            while True:
                try:
                    raw_line = process.stdout.readline()
                except BaseException as exc:
                    _best_effort_queue_put(f"[WARN] reader thread error: {exc}\n")
                    break
                if raw_line == "":
                    break
                _best_effort_queue_put(raw_line)
        finally:
            reader_done.set()
            _best_effort_queue_put(None)

    reader_thread = threading.Thread(target=_reader_worker, daemon=True)
    reader_thread.start()

    with open(logpath, "w", encoding="utf-8", errors="replace") as logf:
        flush_every = flush_every_lines()
        pending_flush_lines = 0
        last_flush = time.monotonic()

        def _flush_if_needed(force: bool = False) -> None:
            nonlocal pending_flush_lines, last_flush
            now = time.monotonic()
            if (
                force
                or pending_flush_lines >= flush_every
                or (pending_flush_lines > 0 and (now - last_flush) >= 1.0)
            ):
                logf.flush()
                pending_flush_lines = 0
                last_flush = now

        logf.write(header)
        pending_flush_lines += 1
        _flush_if_needed(force=True)

        try:
            sentinel_seen = False
            while True:
                if time.time() - start > timeout_s:
                    _terminate_process(
                        process,
                        kill_tree_default=kill_tree_default,
                        pwsh_picker=pwsh_picker,
                        logger=robust_logger,
                    )
                    _wait_for_termination(process, logger=robust_logger)
                    msg = f"\n=== TIMEOUT: pytest exceeded {timeout_s}s and was terminated ===\n"
                    print(msg)
                    logf.write(msg)
                    pending_flush_lines += 1
                    _flush_if_needed(force=True)
                    if fallback_to_tee:
                        logpath_ps = logpath.replace("/", "\\")
                        print(
                            "Fallback: to stream+log use (PowerShell):\n"
                            f'python -m pytest "{test_arg}" 2>&1 | Tee-Object -FilePath '
                            f'"{logpath_ps}"'
                        )
                    reader_thread.join(timeout=reader_join_timeout)
                    return 124

                try:
                    queued_line = line_queue.get(timeout=queue_poll_timeout)
                except queue.Empty:
                    queued_line = ""

                if queued_line is None:
                    sentinel_seen = True
                elif queued_line:
                    print(queued_line, end="")
                    logf.write(queued_line)
                    pending_flush_lines += 1
                    _flush_if_needed()

                process_done = process.poll() is not None
                if process_done and sentinel_seen:
                    break
                if process_done and reader_done.is_set() and line_queue.empty():
                    break

            ret = process.wait()
            footer = f"\n=== Process exited with code {ret} ===\n"
            logf.write(footer)
            pending_flush_lines += 1
            _flush_if_needed(force=True)
            print(footer)
            reader_thread.join(timeout=reader_join_timeout)
            return ret

        except BaseException as exc:
            robust_logger.exception(
                "unexpected failure while streaming pytest output: %s", exc
            )
            logf.write(
                f"[ERR] unexpected failure while streaming pytest output: {exc}\n"
            )
            pending_flush_lines += 1
            _flush_if_needed(force=True)
            _terminate_process(
                process,
                kill_tree_default=kill_tree_default,
                pwsh_picker=pwsh_picker,
                logger=robust_logger,
            )
            _wait_for_termination(process, logger=robust_logger)
            try:
                reader_thread.join(timeout=reader_join_timeout)
            except Exception:
                pass
            raise
