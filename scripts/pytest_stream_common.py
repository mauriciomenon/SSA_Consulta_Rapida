from __future__ import annotations

import os
import queue
import re
import shlex
import signal
import subprocess
import sys
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from scripts.pwsh_discovery import pick_pwsh
from utils.robust_logging import get_robust_logger

DEFAULT_LOG_FILENAME = "pytest_terminal_integration_stream.log"
SAFE_PYTEST_NODEID_RE = re.compile(r"^[A-Za-z0-9_:\.\-\[\]/]+$")
DEFAULT_TIMEOUT_WRAPPER_LOG_FILENAME = "pytest_terminal_integration.log"


def get_stream_logger(name: str):
    return get_robust_logger().get_logger(name, "cli")


def ensure_local_ai_dir(cwd: str | None = None) -> str:
    base_dir = cwd or os.getcwd()
    log_dir = os.path.join(base_dir, "local_ai_private")
    os.makedirs(log_dir, exist_ok=True)
    return log_dir


def ensure_log_path(logpath: str) -> None:
    if not os.path.basename(logpath):
        raise ValueError("log path must include a file name")
    d = os.path.dirname(logpath)
    if d and not os.path.exists(d):
        os.makedirs(d, exist_ok=True)


def add_timeout_wrapper_common_args(parser) -> None:
    parser.add_argument(
        "--test",
        required=True,
        help="pytest path or args (e.g. tests/test_terminal_integration.py)",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=60,
        help="timeout in seconds for the pytest run",
    )
    parser.add_argument("--log", default=None, help="optional log path")


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
        return 0.5
    try:
        value_ms = int(raw)
    except ValueError:
        return 0.5
    if value_ms < 100:
        value_ms = 100
    if value_ms > 5000:
        value_ms = 5000
    return float(value_ms) / 1000.0


def resolve_safe_logpath(logdir: str, user_log: str | None) -> str:
    from utils.path_safety import PathSafetyError, ensure_path_is_allowed

    base_dir = Path(logdir).resolve()
    if not user_log:
        return os.fspath(base_dir / DEFAULT_LOG_FILENAME)
    try:
        resolved_path = ensure_path_is_allowed(
            user_log,
            purpose="stream_log_path",
            base=base_dir,
            expect_directory=False,
        )
    except PathSafetyError as exc:
        raise ValueError(str(exc)) from exc
    try:
        resolved_path.resolve().relative_to(base_dir)
    except ValueError:
        raise ValueError(f"--log must stay under {base_dir}")
    return os.fspath(resolved_path)


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
        if not node_part or not SAFE_PYTEST_NODEID_RE.fullmatch(node_part):
            raise ValueError("--test nodeid contains unsupported characters")
        return f"{resolved}{separator}{node_part}"
    return resolved


def validate_safe_pytest_extra_args(extra_args: list[str]) -> list[str]:
    allowed_exact = {
        "-q",
        "-qq",
        "-v",
        "-vv",
        "-vvv",
        "-s",
        "-x",
        "--lf",
        "--ff",
        "--disable-warnings",
    }
    allowed_with_value = {"-k", "-m", "--maxfail", "--tb", "--capture"}
    allowed_prefixes = ("--maxfail=", "--tb=", "--capture=")

    validated: list[str] = []
    index = 0
    while index < len(extra_args):
        arg = extra_args[index]
        if arg in allowed_exact:
            validated.append(arg)
            index += 1
            continue
        if arg.startswith(allowed_prefixes):
            validated.append(arg)
            index += 1
            continue
        if arg in allowed_with_value:
            next_index = index + 1
            if next_index >= len(extra_args):
                raise ValueError(f"pytest extra arg {arg!r} requires a value")
            value = extra_args[next_index]
            if not value or value.startswith("-"):
                raise ValueError(f"pytest extra arg {arg!r} requires a value")
            validated.extend([arg, value])
            index += 2
            continue
        raise ValueError(f"unsupported pytest extra arg: {arg!r}")
    return validated


def build_timeout_wrapper_cmd(
    *,
    raw_test: str,
    extra_args: list[str],
    cwd: str | None = None,
) -> list[str]:
    test_target = resolve_safe_test_target(raw_test, cwd)
    cmd = [sys.executable, "-m", "pytest", test_target]
    if extra_args:
        cmd.extend(validate_safe_pytest_extra_args(extra_args))
    return cmd


def build_timeout_wrapper_header(cmd: list[str], timeout_s: int) -> str:
    return (
        f"=== pytest wrapper run at {datetime.now(timezone.utc).isoformat()} ===\n"
        f"Command: {shlex.join(cmd)}\nTimeout: {timeout_s}s\n\n"
    )


def _terminate_process(
    process: subprocess.Popen[str],
    *,
    kill_process_tree: bool,
    pwsh_picker: Callable[[], str | None] | None,
    logger,
) -> None:
    try:
        if os.name == "nt":
            if kill_process_tree:
                res = subprocess.run(
                    ["taskkill", "/PID", str(process.pid), "/T", "/F"],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    timeout=2,
                )
                if res.returncode != 0:
                    pwsh = pwsh_picker() if pwsh_picker else None
                    if not pwsh:
                        pwsh = pick_pwsh()
                    if pwsh:
                        subprocess.run(
                            [
                                pwsh,
                                "-NoProfile",
                                "-NonInteractive",
                                "-Command",
                                "Stop-Process",
                                "-Id",
                                str(process.pid),
                                "-Force",
                                "-ErrorAction",
                                "SilentlyContinue",
                            ],
                            stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL,
                            timeout=2,
                        )
                    else:
                        process.kill()
            else:
                process.kill()
        else:
            try:
                if kill_process_tree:
                    process_group_id = os.getpgid(process.pid)
                    os.killpg(process_group_id, signal.SIGTERM)
                else:
                    os.kill(process.pid, signal.SIGTERM)
            except (ProcessLookupError, PermissionError, OSError) as exc:
                logger.warning("SIGTERM process termination failed: %s", exc)
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


def _wait_for_termination(
    process: subprocess.Popen[str],
    *,
    kill_process_tree: bool,
    logger,
) -> None:
    try:
        process.wait(timeout=5)
    except (subprocess.TimeoutExpired, subprocess.SubprocessError, OSError) as exc:
        logger.warning("wait for process termination timed out or failed: %s", exc)
        try:
            if os.name == "nt":
                process.kill()
            else:
                try:
                    if kill_process_tree:
                        os.killpg(os.getpgid(process.pid), signal.SIGKILL)
                    else:
                        os.kill(process.pid, signal.SIGKILL)
                except (ProcessLookupError, PermissionError, OSError) as killpg_exc:
                    logger.warning("SIGKILL process termination failed: %s", killpg_exc)
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


def _terminate_and_wait(
    process: subprocess.Popen[str],
    *,
    kill_process_tree: bool,
    pwsh_picker: Callable[[], str | None] | None = None,
    logger,
) -> None:
    _terminate_process(
        process,
        kill_process_tree=kill_process_tree,
        pwsh_picker=pwsh_picker,
        logger=logger,
    )
    _wait_for_termination(
        process,
        kill_process_tree=kill_process_tree,
        logger=logger,
    )


def _process_exit_footer(exit_code: int) -> str:
    return f"\n=== Process exited with code {exit_code} ===\n"


def run_logged_pytest(
    *,
    cmd: list[str],
    timeout_s: int,
    logpath: str,
    header: str,
    kill_process_tree: bool,
    pwsh_picker: Callable[[], str | None] | None = None,
) -> int:
    logger = get_robust_logger().get_logger(__name__, "cli")
    resolved_pwsh_picker = pwsh_picker or pick_pwsh
    process = None
    with open(logpath, "w", encoding="utf-8", errors="replace") as logf:
        logf.write(header)
        logf.flush()
        try:
            popen_kwargs = {}
            if os.name != "nt":
                popen_kwargs["start_new_session"] = True
            process = subprocess.Popen(
                cmd,
                stdout=logf,
                stderr=subprocess.STDOUT,
                **popen_kwargs,
            )
            try:
                process.wait(timeout=timeout_s)
            except subprocess.TimeoutExpired:
                _terminate_and_wait(
                    process,
                    kill_process_tree=kill_process_tree,
                    pwsh_picker=resolved_pwsh_picker,
                    logger=logger,
                )
                timeout_footer = f"\n=== TIMEOUT: pytest exceeded {timeout_s}s and was terminated ===\n"
                logf.write(timeout_footer)
                logf.flush()
                print(f"TIMEOUT: pytest exceeded {timeout_s}s; log: {logpath}")
                return 124

            exit_code = process.returncode
            footer = _process_exit_footer(exit_code)
            logf.write(footer)
            logf.flush()
            print(f"pytest finished with exit code {exit_code}; log: {logpath}")
            return exit_code
        except BaseException as exc:
            try:
                logf.write(f"\n=== ERROR: {exc} ===\n")
                logf.flush()
            except Exception:
                logger.exception("failed to write wrapper error to log")
            if process is not None and process.poll() is None:
                _terminate_and_wait(
                    process,
                    kill_process_tree=kill_process_tree,
                    pwsh_picker=resolved_pwsh_picker,
                    logger=logger,
                )
            raise


class _StreamLogWriter:
    def __init__(self, logf, *, flush_every: int, stdout=None) -> None:
        self._logf = logf
        self._stdout = stdout or sys.stdout
        self._flush_every = flush_every
        self._pending_flush_lines = 0
        self._last_flush = time.monotonic()

    def flush_if_needed(self, force: bool = False) -> None:
        now = time.monotonic()
        if (
            force
            or self._pending_flush_lines >= self._flush_every
            or (self._pending_flush_lines > 0 and (now - self._last_flush) >= 1.0)
        ):
            self._stdout.flush()
            self._logf.flush()
            self._pending_flush_lines = 0
            self._last_flush = now

    def write_line(self, line: str) -> None:
        self._stdout.write(line)
        self._logf.write(line)
        self._pending_flush_lines += 1
        self.flush_if_needed()

    def write_block(self, text: str, *, force_flush: bool = False) -> None:
        self._logf.write(text)
        newline_count = text.count("\n")
        self._pending_flush_lines += newline_count
        self.flush_if_needed(force=force_flush)

    def drain_queue(self, line_queue: "queue.Queue[str]") -> None:
        while True:
            try:
                queued_line = line_queue.get_nowait()
            except queue.Empty:
                return
            self.write_line(queued_line)


class _StreamingQueuePump:
    def __init__(
        self,
        process: subprocess.Popen[str],
        *,
        robust_logger,
        queue_poll_timeout: float,
        reader_join_timeout: float,
        dropped_warn_every: int,
    ) -> None:
        self._process = process
        self._logger = robust_logger
        self._queue_poll_timeout = queue_poll_timeout
        self._reader_join_timeout = reader_join_timeout
        self._line_queue: "queue.Queue[str]" = queue.Queue(maxsize=queue_maxsize())
        self._reader_done = threading.Event()
        self._dropped_lines = 0
        self._last_warned = 0
        self._dropped_warn_every = dropped_warn_every
        self._reader_thread = threading.Thread(target=self._reader_worker, daemon=True)

    @property
    def line_queue(self) -> "queue.Queue[str]":
        return self._line_queue

    @property
    def reader_done(self) -> threading.Event:
        return self._reader_done

    @property
    def queue_poll_timeout(self) -> float:
        return self._queue_poll_timeout

    def start(self) -> None:
        self._reader_thread.start()

    def join_and_drain(self, writer: _StreamLogWriter) -> None:
        deadline = time.monotonic() + self._reader_join_timeout
        while self._reader_thread.is_alive():
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                break
            self._reader_thread.join(timeout=min(self._queue_poll_timeout, remaining))
            writer.drain_queue(self._line_queue)
        writer.drain_queue(self._line_queue)

    def record_dropped_line(self) -> None:
        self._dropped_lines += 1
        warn_count = self._dropped_lines
        should_warn = warn_count == 1 or (
            warn_count % self._dropped_warn_every == 0
            and warn_count != self._last_warned
        )
        if should_warn:
            self._last_warned = warn_count
            self._logger.warning("output queue full; dropped %s line(s)", warn_count)

    def best_effort_queue_put(self, value: str) -> None:
        try:
            self._line_queue.put_nowait(value)
            return
        except queue.Full:
            pass
        dropped_recorded = False
        try:
            self._line_queue.get_nowait()
        except queue.Empty:
            pass
        else:
            self.record_dropped_line()
            dropped_recorded = True
        try:
            self._line_queue.put_nowait(value)
        except queue.Full:
            if not dropped_recorded:
                self.record_dropped_line()

    def _reader_worker(self) -> None:
        try:
            stdout = self._process.stdout
            if stdout is not None:
                while True:
                    try:
                        raw_line = stdout.readline()
                    except BaseException as exc:
                        self.best_effort_queue_put(
                            f"[ERR] reader thread error: {exc}\n"
                        )
                        break
                    if raw_line == "":
                        break
                    self.best_effort_queue_put(raw_line)
        finally:
            self._reader_done.set()


def run_streaming_pytest(
    *,
    cmd: list[str],
    timeout_s: int,
    logpath: str,
    fallback_to_tee: bool,
    test_arg: str,
    kill_process_tree: bool | None = None,
    kill_tree_default: bool | None = None,
    pwsh_picker: Callable[[], str | None] | None = None,
    cwd: str | None = None,
    env: dict[str, str] | None = None,
) -> int:
    if kill_process_tree is None:
        kill_process_tree = bool(kill_tree_default)

    robust_logger = get_robust_logger().get_logger(__name__, "cli")
    header = (
        f"=== pytest streaming run at {datetime.now(timezone.utc).isoformat()} ===\n"
        f"Command: {shlex.join(cmd)}\nTimeout: {timeout_s}s\n\n"
    )

    start = time.monotonic()
    if os.name == "nt":
        process = subprocess.Popen(
            cmd,
            cwd=cwd,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            errors="replace",
        )
    else:
        process = subprocess.Popen(
            cmd,
            cwd=cwd,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            errors="replace",
            start_new_session=True,
        )

    dropped_warn_every = dropped_warn_every_lines()
    queue_poll_timeout = queue_poll_timeout_seconds()
    reader_join_timeout = reader_join_timeout_seconds()
    pump = _StreamingQueuePump(
        process,
        robust_logger=robust_logger,
        queue_poll_timeout=queue_poll_timeout,
        reader_join_timeout=reader_join_timeout,
        dropped_warn_every=dropped_warn_every,
    )
    pump.start()

    with open(logpath, "w", encoding="utf-8", errors="replace") as logf:
        writer = _StreamLogWriter(logf, flush_every=flush_every_lines())

        def _join_reader_and_drain() -> None:
            pump.join_and_drain(writer)

        def _handle_timeout() -> int:
            _terminate_and_wait(
                process,
                kill_process_tree=kill_process_tree,
                pwsh_picker=pwsh_picker,
                logger=robust_logger,
            )
            _join_reader_and_drain()
            msg = (
                f"\n=== TIMEOUT: pytest exceeded {timeout_s}s and was terminated ===\n"
            )
            print(msg)
            writer.write_block(msg, force_flush=True)
            if fallback_to_tee:
                logpath_ps = logpath.replace("/", "\\")
                print(
                    "Fallback: to stream+log use (PowerShell):\n"
                    f'python -m pytest "{test_arg}" 2>&1 | Tee-Object -FilePath '
                    f'"{logpath_ps}"'
                )
            return 124

        def _next_queue_timeout() -> float:
            remaining = timeout_s - (time.monotonic() - start)
            if remaining <= 0:
                return 0.0
            return max(0.0, min(pump.queue_poll_timeout, remaining))

        def _stream_until_exit() -> None:
            while True:
                if time.monotonic() - start > timeout_s:
                    raise TimeoutError

                try:
                    queued_line = pump.line_queue.get(timeout=_next_queue_timeout())
                except queue.Empty:
                    queued_line = ""

                if queued_line:
                    writer.write_line(queued_line)

                process_done = process.poll() is not None
                if (
                    process_done
                    and pump.reader_done.is_set()
                    and pump.line_queue.empty()
                ):
                    return

        writer.write_block(header, force_flush=True)

        try:
            try:
                _stream_until_exit()
            except TimeoutError:
                return _handle_timeout()

            ret = process.wait()
            footer = _process_exit_footer(ret)
            writer.write_block(footer, force_flush=True)
            print(footer)
            _join_reader_and_drain()
            return ret

        except BaseException as exc:
            robust_logger.exception(
                "unexpected failure while streaming pytest output: %s", exc
            )
            writer.write_block(
                f"[ERR] unexpected failure while streaming pytest output: {exc}\n",
                force_flush=True,
            )
            _terminate_and_wait(
                process,
                kill_process_tree=kill_process_tree,
                pwsh_picker=pwsh_picker,
                logger=robust_logger,
            )
            try:
                _join_reader_and_drain()
            except Exception as join_exc:
                robust_logger.warning(
                    "failed to drain pytest reader after stream failure: %s",
                    join_exc,
                )
            raise
