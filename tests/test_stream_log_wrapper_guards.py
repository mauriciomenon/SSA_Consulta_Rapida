from __future__ import annotations

import contextlib
import importlib.util
import io
import sys
from pathlib import Path
from typing import Any

import pytest


def _load_module(module_name: str, path: Path):
    spec = importlib.util.spec_from_file_location(module_name, path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def modules(monkeypatch: pytest.MonkeyPatch):
    root = Path(__file__).resolve().parents[1]
    monkeypatch.syspath_prepend(str(root / "scripts"))
    v1 = _load_module(
        "stream_wrap_v1", root / "scripts" / "run_pytest_stream_and_log.py"
    )
    v2 = _load_module(
        "stream_wrap_v2", root / "scripts" / "run_pytest_stream_and_log_v2.py"
    )
    common = _load_module(
        "stream_wrap_common", root / "scripts" / "pytest_stream_common.py"
    )
    return v1, v2, common


def test_resolve_safe_logpath_default_inside_logdir(tmp_path: Path, modules) -> None:
    v1, v2, _ = modules
    for mod in (v1, v2):
        resolved = Path(mod._resolve_safe_logpath(str(tmp_path), None))
        assert resolved == tmp_path / "pytest_terminal_integration_stream.log"


def test_resolve_safe_logpath_rejects_traversal(tmp_path: Path, modules) -> None:
    v1, v2, _ = modules
    for mod in (v1, v2):
        with pytest.raises(ValueError):
            mod._resolve_safe_logpath(str(tmp_path), "../escape.log")


def test_resolve_safe_logpath_rejects_absolute_outside(tmp_path: Path, modules) -> None:
    v1, v2, _ = modules
    outside = tmp_path.parent / "outside.log"
    for mod in (v1, v2):
        with pytest.raises(ValueError):
            mod._resolve_safe_logpath(str(tmp_path), str(outside))


def test_resolve_safe_test_target_accepts_pytest_nodeid(modules) -> None:
    _, _, common = modules
    root = Path(__file__).resolve().parents[1]

    resolved = common.resolve_safe_test_target(
        "tests/test_stream_log_wrapper_guards.py::test_resolve_safe_logpath_default_inside_logdir",
        str(root),
    )

    assert resolved.startswith(
        str(root / "tests" / "test_stream_log_wrapper_guards.py")
    )
    assert "::test_resolve_safe_logpath_default_inside_logdir" in resolved


def test_resolve_safe_test_target_rejects_flag_input(modules) -> None:
    _, _, common = modules

    with pytest.raises(ValueError, match="not a flag"):
        common.resolve_safe_test_target("-k smoke")


def test_resolve_safe_test_target_rejects_traversal(modules) -> None:
    _, _, common = modules
    root = Path(__file__).resolve().parents[1]

    with pytest.raises(ValueError):
        common.resolve_safe_test_target("../outside.py", str(root))


def test_resolve_safe_test_target_rejects_unsafe_nodeid(modules) -> None:
    _, _, common = modules
    root = Path(__file__).resolve().parents[1]

    with pytest.raises(ValueError, match="unsupported characters"):
        common.resolve_safe_test_target(
            "tests/test_stream_log_wrapper_guards.py::test_name;rm",
            str(root),
        )


def test_build_timeout_wrapper_cmd_accepts_safe_extra_args(modules) -> None:
    _, _, common = modules
    root = Path(__file__).resolve().parents[1]

    cmd = common.build_timeout_wrapper_cmd(
        raw_test="tests/test_stream_log_wrapper_guards.py",
        extra_args=["-q", "--maxfail=1", "-k", "queue"],
        cwd=str(root),
    )

    assert cmd[:3] == [sys.executable, "-m", "pytest"]
    assert str(root / "tests" / "test_stream_log_wrapper_guards.py") in cmd
    assert "-q" in cmd
    assert "--maxfail=1" in cmd
    assert "-k" in cmd
    assert "queue" in cmd


def test_build_timeout_wrapper_cmd_rejects_unsupported_extra_arg(modules) -> None:
    _, _, common = modules
    root = Path(__file__).resolve().parents[1]

    with pytest.raises(ValueError, match="unsupported pytest extra arg"):
        common.build_timeout_wrapper_cmd(
            raw_test="tests/test_stream_log_wrapper_guards.py",
            extra_args=["--rootdir=tmp"],
            cwd=str(root),
        )


def test_build_timeout_wrapper_cmd_rejects_missing_extra_arg_value(modules) -> None:
    _, _, common = modules
    root = Path(__file__).resolve().parents[1]

    with pytest.raises(ValueError, match="requires a value"):
        common.build_timeout_wrapper_cmd(
            raw_test="tests/test_stream_log_wrapper_guards.py",
            extra_args=["-k"],
            cwd=str(root),
        )


def test_flush_every_lines_clamp_and_default(
    monkeypatch: pytest.MonkeyPatch, modules
) -> None:
    _, _, common = modules
    monkeypatch.delenv("PYTEST_STREAM_FLUSH_EVERY", raising=False)
    assert common.flush_every_lines() == 64
    monkeypatch.setenv("PYTEST_STREAM_FLUSH_EVERY", "0")
    assert common.flush_every_lines() == 1
    monkeypatch.setenv("PYTEST_STREAM_FLUSH_EVERY", "10000")
    assert common.flush_every_lines() == 4096
    monkeypatch.setenv("PYTEST_STREAM_FLUSH_EVERY", "bad")
    assert common.flush_every_lines() == 64


def test_dropped_warn_every_lines_clamp_and_default(
    monkeypatch: pytest.MonkeyPatch, modules
) -> None:
    _, _, common = modules
    monkeypatch.delenv("PYTEST_STREAM_DROPPED_WARN_EVERY", raising=False)
    assert common.dropped_warn_every_lines() == 200
    monkeypatch.setenv("PYTEST_STREAM_DROPPED_WARN_EVERY", "1")
    assert common.dropped_warn_every_lines() == 10
    monkeypatch.setenv("PYTEST_STREAM_DROPPED_WARN_EVERY", "50000")
    assert common.dropped_warn_every_lines() == 10000
    monkeypatch.setenv("PYTEST_STREAM_DROPPED_WARN_EVERY", "bad")
    assert common.dropped_warn_every_lines() == 200


def test_queue_poll_timeout_seconds_clamp_and_default(
    monkeypatch: pytest.MonkeyPatch, modules
) -> None:
    _, _, common = modules
    monkeypatch.delenv("PYTEST_STREAM_QUEUE_POLL_TIMEOUT_MS", raising=False)
    assert common.queue_poll_timeout_seconds() == 0.2
    monkeypatch.setenv("PYTEST_STREAM_QUEUE_POLL_TIMEOUT_MS", "1")
    assert common.queue_poll_timeout_seconds() == 0.02
    monkeypatch.setenv("PYTEST_STREAM_QUEUE_POLL_TIMEOUT_MS", "5000")
    assert common.queue_poll_timeout_seconds() == 2.0
    monkeypatch.setenv("PYTEST_STREAM_QUEUE_POLL_TIMEOUT_MS", "bad")
    assert common.queue_poll_timeout_seconds() == 0.2


def test_reader_join_timeout_seconds_clamp_and_default(
    monkeypatch: pytest.MonkeyPatch, modules
) -> None:
    _, _, common = modules
    monkeypatch.delenv("PYTEST_STREAM_READER_JOIN_TIMEOUT_MS", raising=False)
    assert common.reader_join_timeout_seconds() == 0.5
    monkeypatch.setenv("PYTEST_STREAM_READER_JOIN_TIMEOUT_MS", "1")
    assert common.reader_join_timeout_seconds() == 0.1
    monkeypatch.setenv("PYTEST_STREAM_READER_JOIN_TIMEOUT_MS", "50000")
    assert common.reader_join_timeout_seconds() == 5.0
    monkeypatch.setenv("PYTEST_STREAM_READER_JOIN_TIMEOUT_MS", "bad")
    assert common.reader_join_timeout_seconds() == 0.5


def test_process_exit_footer_uses_shared_format(modules) -> None:
    _, _, common = modules
    assert common._process_exit_footer(7) == "\n=== Process exited with code 7 ===\n"


def test_run_streaming_pytest_marks_reader_failure_as_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, modules
) -> None:
    _, _, common = modules
    logpath = tmp_path / "stream_reader_error.log"

    class _BrokenStdout:
        def readline(self) -> str:
            raise RuntimeError("boom")

    class _FakeProcess:
        def __init__(self) -> None:
            self.stdout = _BrokenStdout()
            self.pid = 321
            self.returncode = 0

        def poll(self) -> int:
            return 0

        def wait(self, timeout: float | None = None) -> int:
            return 0

    def _fake_popen(*args: Any, **kwargs: Any) -> _FakeProcess:
        return _FakeProcess()

    monkeypatch.setattr(common.subprocess, "Popen", _fake_popen)
    monkeypatch.setattr(common, "queue_poll_timeout_seconds", lambda: 0.02)
    monkeypatch.setattr(common, "reader_join_timeout_seconds", lambda: 0.1)

    with contextlib.redirect_stdout(io.StringIO()):
        ret = common.run_streaming_pytest(
            cmd=[sys.executable, "-c", "print('unused')"],
            timeout_s=1,
            logpath=str(logpath),
            fallback_to_tee=False,
            test_arg="reader-error",
            kill_tree_default=True,
        )

    assert ret == 0
    text = logpath.read_text(encoding="utf-8", errors="replace")
    assert "[ERR] reader thread error: boom" in text


def test_run_streaming_pytest_finishes_under_queue_pressure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, modules
) -> None:
    _, _, common = modules
    logpath = tmp_path / "stream_pressure.log"

    monkeypatch.setattr(common, "queue_maxsize", lambda: 1)
    monkeypatch.setattr(common, "flush_every_lines", lambda: 1)
    monkeypatch.setattr(common, "queue_poll_timeout_seconds", lambda: 0.02)
    monkeypatch.setattr(common, "reader_join_timeout_seconds", lambda: 0.5)

    cmd = [
        sys.executable,
        "-c",
        "for i in range(20000): print('line-%d' % i)",
    ]

    with contextlib.redirect_stdout(io.StringIO()):
        ret = common.run_streaming_pytest(
            cmd=cmd,
            timeout_s=10,
            logpath=str(logpath),
            fallback_to_tee=False,
            test_arg="pressure",
            kill_tree_default=True,
        )

    assert ret == 0
    text = logpath.read_text(encoding="utf-8", errors="replace")
    assert "pytest streaming run" in text
    assert "Process exited with code 0" in text
