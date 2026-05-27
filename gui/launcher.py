from __future__ import annotations

import logging
import os
import sys
import threading


class GuiOperationalError(RuntimeError):
    """Raised when GUI creation fails after dependencies were imported."""


_TSM_STDERR_LINE = (
    "TSMSendMessageToUIServer: CFMessagePortSendRequest FAILED(-1) "
    "to send to port com.apple.tsm.uiserver"
)


def _should_filter_macos_stderr_line(line: str) -> bool:
    return _TSM_STDERR_LINE in str(line or "")


class _MacOSStderrFilter:
    def __init__(self, logger: logging.Logger) -> None:
        self._logger = logger
        self._pipe_read_fd: int | None = None
        self._pipe_write_fd: int | None = None
        self._stderr_dup_fd: int | None = None
        self._thread: threading.Thread | None = None

    def install(self) -> bool:
        try:
            self._stderr_dup_fd = os.dup(2)
            read_fd, write_fd = os.pipe()
            self._pipe_read_fd = read_fd
            self._pipe_write_fd = write_fd
            os.dup2(write_fd, 2)
            self._thread = threading.Thread(
                target=self._pump_lines,
                name="ssa-macos-stderr-filter",
                daemon=True,
            )
            self._thread.start()
            return True
        except OSError as exc:
            self.close()
            self._logger.debug("Falha ao instalar filtro stderr do macOS: %s", exc)
            return False

    def close(self) -> None:
        stderr_dup_fd = self._stderr_dup_fd
        pipe_write_fd = self._pipe_write_fd
        if stderr_dup_fd is not None:
            try:
                os.dup2(stderr_dup_fd, 2)
            except OSError:
                pass
        if pipe_write_fd is not None:
            try:
                os.close(pipe_write_fd)
            except OSError:
                pass
        if self._thread is not None:
            self._thread.join(timeout=0.5)
        if self._pipe_read_fd is not None:
            try:
                os.close(self._pipe_read_fd)
            except OSError:
                pass
        if stderr_dup_fd is not None:
            try:
                os.close(stderr_dup_fd)
            except OSError:
                pass
        self._pipe_read_fd = None
        self._pipe_write_fd = None
        self._stderr_dup_fd = None
        self._thread = None

    def _pump_lines(self) -> None:
        read_fd = self._pipe_read_fd
        stderr_dup_fd = self._stderr_dup_fd
        if read_fd is None or stderr_dup_fd is None:
            return
        try:
            with os.fdopen(read_fd, "r", encoding="utf-8", errors="replace") as reader:
                for line in reader:
                    if _should_filter_macos_stderr_line(line):
                        continue
                    os.write(stderr_dup_fd, line.encode("utf-8", "replace"))
        except OSError:
            return


def _install_macos_stderr_filter(
    logger: logging.Logger,
) -> _MacOSStderrFilter | None:
    if sys.platform != "darwin":
        return None
    if str(os.environ.get("SSA_TSM_DEBUG", "")).strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }:
        return None
    stderr_filter = _MacOSStderrFilter(logger)
    if stderr_filter.install():
        return stderr_filter
    return None


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

    stderr_filter = _install_macos_stderr_filter(logger)
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
    finally:
        if stderr_filter is not None:
            stderr_filter.close()
