"""CF-06: o runtime empacotado avisa quando descarta SSA_* definida pelo usuario."""

from __future__ import annotations

import logging
from pathlib import Path

import pytest

import utils.robust_logging as robust_logging
from launchers import main_runtime, runtime_entry_helpers


class _FakeRobustLogger:
    def __init__(self, sink: list[str]) -> None:
        self._sink = sink

    def get_logger(self, name: str, component: str | None = None) -> logging.Logger:
        sink = self._sink

        class _Capture(logging.Handler):
            def emit(self, record: logging.LogRecord) -> None:
                sink.append(record.getMessage())

        logger = logging.getLogger(f"test.cf06.{name}.{component}")
        logger.handlers = [_Capture()]
        logger.propagate = False
        logger.setLevel(logging.WARNING)  # BL-43: nao herdar o nivel do logger raiz
        return logger


@pytest.fixture()
def warnings_sink(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    sink: list[str] = []
    monkeypatch.setattr(
        robust_logging, "get_robust_logger", lambda *_a, **_k: _FakeRobustLogger(sink)
    )
    for name in ("SSA_DB_PATH", "SSA_CONFIG_DIR", "SSA_RUNTIME_ROOT", "SSA_BUNDLED_ROOT"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.delenv("SSA_EXTRA_ALLOWED_PATHS", raising=False)
    return sink


def _runtime(tmp_path: Path) -> tuple[Path, Path, Path]:
    runtime_dir = tmp_path / "rt"
    config = runtime_dir / "config"
    data = runtime_dir / "data"
    for folder in (config, data):
        folder.mkdir(parents=True)
    return runtime_dir, config, data


def test_entry_helpers_warn_discarded_db_path(tmp_path, monkeypatch, warnings_sink):
    runtime_dir, config, data = _runtime(tmp_path)
    user_db = tmp_path / "meu.db"
    monkeypatch.setenv("SSA_DB_PATH", str(user_db))

    runtime_entry_helpers._apply_runtime_environment(str(tmp_path), runtime_dir, config, data)

    assert len(warnings_sink) == 1
    assert "SSA_DB_PATH" in warnings_sink[0] and str(user_db) in warnings_sink[0]
    assert str(data / "ssas.db") in warnings_sink[0]


def test_main_runtime_warns_discarded_runtime_root(tmp_path, monkeypatch, warnings_sink):
    runtime_dir, config, data = _runtime(tmp_path)
    user_root = tmp_path / "minha_raiz"
    monkeypatch.setenv("SSA_RUNTIME_ROOT", str(user_root))
    dirs = {key: runtime_dir / key for key in (
        "docs_in", "docs_out", "reports", "exportacao", "logs"
    )}

    main_runtime._apply_runtime_environment(runtime_dir, config, data, dirs, str(tmp_path))

    assert len(warnings_sink) == 1
    assert "SSA_RUNTIME_ROOT" in warnings_sink[0] and str(user_root) in warnings_sink[0]


def test_no_warning_when_preset_matches(tmp_path, monkeypatch, warnings_sink):
    runtime_dir, config, data = _runtime(tmp_path)
    monkeypatch.setenv("SSA_DB_PATH", str(data / "ssas.db"))
    monkeypatch.setenv("SSA_RUNTIME_ROOT", str(runtime_dir))

    runtime_entry_helpers._apply_runtime_environment(str(tmp_path), runtime_dir, config, data)

    assert warnings_sink == []


def test_no_warning_when_preset_is_symlink_to_same_path(tmp_path, monkeypatch, warnings_sink):
    """BL-28: /var x /private/var (symlink) e o mesmo caminho; nao avisa."""
    runtime_dir, config, data = _runtime(tmp_path)
    link = tmp_path / "link_rt"
    link.symlink_to(runtime_dir, target_is_directory=True)
    monkeypatch.setenv("SSA_RUNTIME_ROOT", str(link))
    monkeypatch.setenv("SSA_DB_PATH", str(link / "data" / "ssas.db"))

    runtime_entry_helpers._apply_runtime_environment(str(tmp_path), runtime_dir, config, data)

    assert warnings_sink == []
