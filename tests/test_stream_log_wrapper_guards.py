from __future__ import annotations

import importlib.util
from pathlib import Path
import sys

import pytest


def _load_module(module_name: str, path: Path):
    script_dir = str(path.parent)
    if script_dir not in sys.path:
        sys.path.insert(0, script_dir)
    spec = importlib.util.spec_from_file_location(module_name, path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def modules():
    root = Path(__file__).resolve().parents[1]
    v1 = _load_module("stream_wrap_v1", root / "scripts" / "run_pytest_stream_and_log.py")
    v2 = _load_module("stream_wrap_v2", root / "scripts" / "run_pytest_stream_and_log_v2.py")
    common = _load_module("stream_wrap_common", root / "scripts" / "pytest_stream_common.py")
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


def test_flush_every_lines_clamp_and_default(monkeypatch: pytest.MonkeyPatch, modules) -> None:
    _, _, common = modules
    monkeypatch.delenv("PYTEST_STREAM_FLUSH_EVERY", raising=False)
    assert common.flush_every_lines() == 64
    monkeypatch.setenv("PYTEST_STREAM_FLUSH_EVERY", "0")
    assert common.flush_every_lines() == 1
    monkeypatch.setenv("PYTEST_STREAM_FLUSH_EVERY", "10000")
    assert common.flush_every_lines() == 4096
    monkeypatch.setenv("PYTEST_STREAM_FLUSH_EVERY", "bad")
    assert common.flush_every_lines() == 64


def test_dropped_warn_every_lines_clamp_and_default(monkeypatch: pytest.MonkeyPatch, modules) -> None:
    _, _, common = modules
    monkeypatch.delenv("PYTEST_STREAM_DROPPED_WARN_EVERY", raising=False)
    assert common.dropped_warn_every_lines() == 200
    monkeypatch.setenv("PYTEST_STREAM_DROPPED_WARN_EVERY", "1")
    assert common.dropped_warn_every_lines() == 10
    monkeypatch.setenv("PYTEST_STREAM_DROPPED_WARN_EVERY", "50000")
    assert common.dropped_warn_every_lines() == 10000
    monkeypatch.setenv("PYTEST_STREAM_DROPPED_WARN_EVERY", "bad")
    assert common.dropped_warn_every_lines() == 200


def test_queue_poll_timeout_seconds_clamp_and_default(monkeypatch: pytest.MonkeyPatch, modules) -> None:
    _, _, common = modules
    monkeypatch.delenv("PYTEST_STREAM_QUEUE_POLL_TIMEOUT_MS", raising=False)
    assert common.queue_poll_timeout_seconds() == 0.2
    monkeypatch.setenv("PYTEST_STREAM_QUEUE_POLL_TIMEOUT_MS", "1")
    assert common.queue_poll_timeout_seconds() == 0.02
    monkeypatch.setenv("PYTEST_STREAM_QUEUE_POLL_TIMEOUT_MS", "5000")
    assert common.queue_poll_timeout_seconds() == 2.0
    monkeypatch.setenv("PYTEST_STREAM_QUEUE_POLL_TIMEOUT_MS", "bad")
    assert common.queue_poll_timeout_seconds() == 0.2


def test_reader_join_timeout_seconds_clamp_and_default(monkeypatch: pytest.MonkeyPatch, modules) -> None:
    _, _, common = modules
    monkeypatch.delenv("PYTEST_STREAM_READER_JOIN_TIMEOUT_MS", raising=False)
    assert common.reader_join_timeout_seconds() == 1.0
    monkeypatch.setenv("PYTEST_STREAM_READER_JOIN_TIMEOUT_MS", "1")
    assert common.reader_join_timeout_seconds() == 0.1
    monkeypatch.setenv("PYTEST_STREAM_READER_JOIN_TIMEOUT_MS", "50000")
    assert common.reader_join_timeout_seconds() == 5.0
    monkeypatch.setenv("PYTEST_STREAM_READER_JOIN_TIMEOUT_MS", "bad")
    assert common.reader_join_timeout_seconds() == 1.0
