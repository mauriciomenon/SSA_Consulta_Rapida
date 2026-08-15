from __future__ import annotations

import time

from utils.robust_logging import get_robust_logger


_LOGGER = get_robust_logger().get_logger("launchers", "maintenance")


def log_launcher_status(
    message: str,
    level: str = "INFO",
    *,
    timestamp: bool = False,
) -> None:
    text = f"[{time.strftime('%H:%M:%S')}] {message}" if timestamp else message
    level_norm = str(level or "INFO").upper()
    if level_norm in {"ERR", "ERROR"}:
        _LOGGER.error(text)
    elif level_norm in {"WARN", "WARNING"}:
        _LOGGER.warning(text)
    elif level_norm == "DEBUG":
        _LOGGER.debug(text)
    else:
        _LOGGER.info(text)
