from __future__ import annotations

import sys
import logging

import pytest


def test_main_no_automatic_legacy_retry_when_optimized_runtime_fails_on_force_rescan(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import armazenamento.database_optimized as db_opt
    import core.app_logic as app_logic
    import main

    calls = {"importer": 0, "disable": 0}

    def fake_enable() -> None:
        return None

    def fake_disable() -> None:
        calls["disable"] += 1

    def fake_run_importer_logic(*, force_import: bool = False):  # noqa: ARG001
        calls["importer"] += 1
        raise RuntimeError("optimized runtime failure")

    monkeypatch.setattr(db_opt, "enable_optimized_import", fake_enable)
    monkeypatch.setattr(db_opt, "disable_optimized_import", fake_disable)
    monkeypatch.setattr(app_logic, "run_importer_logic", fake_run_importer_logic)

    with pytest.raises(SystemExit) as excinfo:
        main.main(cli_args=["--force-rescan", "--log-level", "CRITICAL"])
    assert excinfo.value.code == 1

    assert calls["importer"] == 1
    assert calls["disable"] == 1


def test_main_force_rescan_does_not_fallback_when_optimized_import_is_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import core.app_logic as app_logic
    import main

    calls = {"importer": 0}
    original_import_module = main.importlib.import_module

    def fake_import_module(name: str):
        if name == "armazenamento.database_optimized":
            raise ImportError("optimized module missing")
        return original_import_module(name)

    def fake_run_importer_logic(*, force_import: bool = False):  # noqa: ARG001
        calls["importer"] += 1
        return True

    monkeypatch.setattr(main.importlib, "import_module", fake_import_module)
    monkeypatch.setattr(app_logic, "run_importer_logic", fake_run_importer_logic)

    with pytest.raises(SystemExit) as excinfo:
        main.main(cli_args=["--force-rescan", "--log-level", "CRITICAL"])

    assert excinfo.value.code == 1
    assert calls["importer"] == 0


def test_main_version_handles_missing_sys_argv(monkeypatch: pytest.MonkeyPatch) -> None:
    import main

    monkeypatch.delattr(sys, "argv", raising=False)

    main.main(cli_args=["--version"])


def test_main_log_level_updates_root_handlers(monkeypatch: pytest.MonkeyPatch) -> None:
    import main

    root_logger = logging.getLogger()
    original_root_level = root_logger.level
    original_handler_levels = [handler.level for handler in root_logger.handlers]
    monkeypatch.setattr(main, "_logging_configured", False)

    try:
        main.main(cli_args=["--version", "--log-level", "DEBUG"])

        assert root_logger.level == logging.DEBUG
        assert root_logger.handlers
        file_handlers = [
            handler
            for handler in root_logger.handlers
            if isinstance(handler, logging.FileHandler)
        ]
        stream_handlers = [
            handler
            for handler in root_logger.handlers
            if isinstance(handler, logging.StreamHandler)
            and not isinstance(handler, logging.FileHandler)
        ]
        assert file_handlers
        assert stream_handlers
        assert all(handler.level == logging.DEBUG for handler in file_handlers)
        assert all(handler.level == logging.DEBUG for handler in stream_handlers)
    finally:
        root_logger.setLevel(original_root_level)
        for handler, level in zip(root_logger.handlers, original_handler_levels):
            handler.setLevel(level)


def test_main_dependency_failure_exits_nonzero(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import main

    monkeypatch.setattr(main, "_load_runtime_dependencies", lambda: None)

    with pytest.raises(SystemExit) as excinfo:
        main.main(cli_args=["--log-level", "CRITICAL"])

    assert excinfo.value.code == 1
