from __future__ import annotations

import io
import logging

import main


def test_set_logging_level_preserves_console_and_file_levels(tmp_path) -> None:
    root_logger = logging.getLogger()
    original_handlers = list(root_logger.handlers)
    original_level = root_logger.level
    original_console_level = main._console_logging_level
    original_file_level = main._file_logging_level
    original_logger = getattr(main, "logger", None)

    console_buffer = io.StringIO()
    console_handler = logging.StreamHandler(console_buffer)
    file_handler = logging.FileHandler(tmp_path / "ssa.log", encoding="utf-8")

    try:
        root_logger.handlers.clear()
        root_logger.addHandler(console_handler)
        root_logger.addHandler(file_handler)
        main.logger = logging.getLogger("ssa.test.logging")

        main._set_logging_level(
            logging.INFO,
            level_console=logging.WARNING,
            level_file=logging.INFO,
        )

        assert root_logger.level == logging.INFO
        assert console_handler.level == logging.WARNING
        assert file_handler.level == logging.INFO
        assert main._console_logging_level == logging.WARNING
        assert main._file_logging_level == logging.INFO
    finally:
        console_handler.close()
        file_handler.close()
        root_logger.handlers.clear()
        for handler in original_handlers:
            root_logger.addHandler(handler)
        root_logger.setLevel(original_level)
        main._console_logging_level = original_console_level
        main._file_logging_level = original_file_level
        if original_logger is not None:
            main.logger = original_logger
