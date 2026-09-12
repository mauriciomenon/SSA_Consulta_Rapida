"""Regressao: log_dir relativo ancora no SSA_RUNTIME_ROOT (modo empacotado)."""

from __future__ import annotations

import logging
from pathlib import Path

import pytest

from utils.robust_logging import RobustLogger


def _release_root_handlers() -> None:
    root_logger = logging.getLogger()
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
        try:
            handler.close()
        except Exception:  # noqa: BLE001 - cleanup best-effort
            pass


def test_relative_log_dir_anchors_at_ssa_runtime_root(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    runtime_root = tmp_path / "runtime_root"
    runtime_root.mkdir()
    monkeypatch.setenv("SSA_RUNTIME_ROOT", str(runtime_root))

    robust_logger = RobustLogger(config_path=str(tmp_path / "missing.json"))
    try:
        expected_dir = runtime_root / "logs"
        assert expected_dir.is_dir()

        handler_filenames = [
            Path(getattr(handler, "baseFilename", "")).resolve()
            for handler in logging.getLogger().handlers
        ]
        assert any(
            expected_dir.resolve() in filename.parents or filename.parent == expected_dir.resolve()
            for filename in handler_filenames
        ), handler_filenames
    finally:
        _release_root_handlers()
        robust_logger.loggers.clear()


def test_relative_log_dir_falls_back_to_package_root(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.delenv("SSA_RUNTIME_ROOT", raising=False)

    robust_logger = RobustLogger(config_path=str(tmp_path / "missing.json"))
    try:
        package_root = Path(__file__).resolve().parents[1]
        handler_filenames = [
            Path(getattr(handler, "baseFilename", ""))
            for handler in logging.getLogger().handlers
        ]
        assert any(
            str(filename).startswith(str(package_root / "logs"))
            for filename in handler_filenames
        ), handler_filenames
    finally:
        _release_root_handlers()
        robust_logger.loggers.clear()
