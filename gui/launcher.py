from __future__ import annotations

import logging
import os
import sys


class GuiOperationalError(RuntimeError):
    """Raised when GUI creation fails after dependencies were imported."""


def _get_icon_candidates(active_runtime_root: str) -> list[str]:
    if sys.platform == "darwin":
        extensions = ("icns", "png", "ico", "svg")
    elif sys.platform.startswith("win"):
        extensions = ("ico", "png", "svg", "icns")
    else:
        extensions = ("png", "svg", "ico", "icns")
    resources_dir = os.path.join(active_runtime_root, "resources")
    return [os.path.join(resources_dir, f"app_icon.{ext}") for ext in extensions]


def launch_gui(
    active_runtime_root: str,
    argv: list[str],
    logger: logging.Logger,
) -> None:
    from PyQt6.QtGui import QIcon
    from PyQt6.QtWidgets import QApplication

    from gui.gui_ssa import SSAMainWindow

    try:
        app = QApplication(argv)
        try:
            if sys.platform == "darwin":
                app.setApplicationName("Consulta Rapida de SSAs")
                app.setApplicationDisplayName("Consulta Rapida de SSAs")
        except (AttributeError, OSError, RuntimeError) as exc:
            logger.debug("Falha ao configurar nome da aplicacao: %s", exc)
        try:
            for icon_path in _get_icon_candidates(active_runtime_root):
                if not os.path.exists(icon_path):
                    continue
                app_icon = QIcon(icon_path)
                if app_icon.isNull():
                    continue
                app.setWindowIcon(app_icon)
                QApplication.setWindowIcon(app_icon)
                logger.debug("Icone da aplicacao carregado: %s", icon_path)
                break
        except (OSError, RuntimeError) as exc:
            logger.debug("Falha ao configurar icone da aplicacao: %s", exc)
        window = SSAMainWindow()
        if not bool(getattr(window, "_startup_show_pending", False)):
            window.show()
        app.exec()
    except (OSError, RuntimeError) as exc:
        raise GuiOperationalError(str(exc)) from exc
