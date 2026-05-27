from __future__ import annotations

import builtins
import os
import subprocess
import sys
from types import SimpleNamespace
from typing import Any

import pytest


def test_gui_ssa_window_instantiates_when_pyqt_is_available() -> None:
    from gui.gui_ssa import QT_AVAILABLE, SSAMainWindow

    if not QT_AVAILABLE:
        pytest.skip("PyQt6 indisponivel neste ambiente")

    from PyQt6.QtWidgets import QApplication

    app = QApplication.instance() or QApplication([])
    window = SSAMainWindow()
    try:
        assert isinstance(window, SSAMainWindow)
    finally:
        window.close()
        app.processEvents()


def _patch_gui_import_failure(
    monkeypatch: pytest.MonkeyPatch,
    exc_to_raise: Exception,
) -> None:
    real_import = builtins.__import__
    monkeypatch.delitem(sys.modules, "gui.gui_ssa", raising=False)
    monkeypatch.delitem(sys.modules, "gui.launcher", raising=False)

    def fake_import(name, globals=None, locals=None, fromlist=(), level=0):  # noqa: ANN001
        if name == "gui.gui_ssa":
            raise exc_to_raise
        return real_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", fake_import)


def _launcher_test_deps(show_calls: dict[str, int], exec_calls: dict[str, int]) -> tuple[type[Any], type[Any], type[Any]]:
    class FakeWindow:
        _startup_show_pending = False

        def __init__(self) -> None:
            self._startup_show_pending = bool(type(self)._startup_show_pending)

        def show(self) -> None:
            show_calls["count"] += 1

    class FakeQApplication:
        @staticmethod
        def setWindowIcon(_icon) -> None:  # noqa: ANN001
            return None

        def __init__(self, _argv) -> None:  # noqa: ANN001
            return None

        def setApplicationName(self, _value: str) -> None:
            return None

        def setApplicationDisplayName(self, _value: str) -> None:
            return None

        def exec(self) -> int:
            exec_calls["count"] += 1
            return 0

    class FakeIcon:
        def __init__(self, _path: str) -> None:
            return None

        def isNull(self) -> bool:
            return True

    return FakeWindow, FakeQApplication, FakeIcon


def test_main_gui_importerror_falls_back_to_cli(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import interface.cli as cli
    import main

    calls = {"cli": 0}

    def fake_start_cli_loop(db_path: str, table_name: str) -> None:  # noqa: ARG001
        calls["cli"] += 1

    monkeypatch.setattr(cli, "start_cli_loop", fake_start_cli_loop)
    _patch_gui_import_failure(monkeypatch, ImportError("simulated missing gui module"))

    main.main(cli_args=["--skip-import", "--gui", "--log-level", "CRITICAL"])

    assert calls["cli"] == 1


def test_main_gui_unexpected_import_error_exits_with_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import interface.cli as cli
    import main

    calls = {"cli": 0}

    def fake_start_cli_loop(db_path: str, table_name: str) -> None:  # noqa: ARG001
        calls["cli"] += 1

    monkeypatch.setattr(cli, "start_cli_loop", fake_start_cli_loop)
    _patch_gui_import_failure(
        monkeypatch, RuntimeError("simulated runtime import failure")
    )

    with pytest.raises(SystemExit) as excinfo:
        main.main(cli_args=["--skip-import", "--gui", "--log-level", "CRITICAL"])

    assert excinfo.value.code == 1
    assert calls["cli"] == 0


def test_gui_ssa_import_disables_window_when_pyqt_is_unavailable() -> None:
    code = """
import builtins
import importlib
import pytest

real_import = builtins.__import__

def fake_import(name, globals=None, locals=None, fromlist=(), level=0):
    if name == "PyQt6" or name.startswith("PyQt6."):
        raise ImportError("blocked PyQt6")
    return real_import(name, globals, locals, fromlist, level)

builtins.__import__ = fake_import
module = importlib.import_module("gui.gui_ssa")
assert module.QT_AVAILABLE is False
assert module.PYQT_VERSION_STR == "indisponivel"
with pytest.raises(RuntimeError, match="GUI unavailable"):
    module.SSAMainWindow()
"""
    env = dict(os.environ)
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    env["PYTHONPATH"] = repo_root

    result = subprocess.run(
        [sys.executable, "-c", code],
        check=False,
        capture_output=True,
        env=env,
        text=True,
    )

    assert result.returncode == 0, result.stderr


def test_launch_gui_skips_show_when_startup_load_is_pending(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from gui.gui_ssa import QT_AVAILABLE

    if not QT_AVAILABLE:
        pytest.skip("PyQt6 indisponivel neste ambiente")

    show_calls = {"count": 0}
    exec_calls = {"count": 0}
    FakeWindow, FakeQApplication, FakeIcon = _launcher_test_deps(
        show_calls, exec_calls
    )
    FakeWindow._startup_show_pending = True  # type: ignore[attr-defined]

    monkeypatch.delitem(sys.modules, "gui.launcher", raising=False)
    from PyQt6 import QtGui, QtWidgets
    monkeypatch.setattr(QtWidgets, "QApplication", FakeQApplication)
    monkeypatch.setattr(QtGui, "QIcon", FakeIcon)
    monkeypatch.setitem(sys.modules, "gui.gui_ssa", SimpleNamespace(SSAMainWindow=FakeWindow))
    from gui import launcher

    launcher.launch_gui(os.getcwd(), ["app"], launcher.logging.getLogger("test"))

    assert show_calls["count"] == 0
    assert exec_calls["count"] == 1


def test_launch_gui_shows_window_when_startup_load_is_not_pending(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from gui.gui_ssa import QT_AVAILABLE

    if not QT_AVAILABLE:
        pytest.skip("PyQt6 indisponivel neste ambiente")

    show_calls = {"count": 0}
    exec_calls = {"count": 0}
    FakeWindow, FakeQApplication, FakeIcon = _launcher_test_deps(
        show_calls, exec_calls
    )

    monkeypatch.delitem(sys.modules, "gui.launcher", raising=False)
    from PyQt6 import QtGui, QtWidgets
    monkeypatch.setattr(QtWidgets, "QApplication", FakeQApplication)
    monkeypatch.setattr(QtGui, "QIcon", FakeIcon)
    monkeypatch.setitem(sys.modules, "gui.gui_ssa", SimpleNamespace(SSAMainWindow=FakeWindow))
    from gui import launcher

    launcher.launch_gui(os.getcwd(), ["app"], launcher.logging.getLogger("test"))

    assert show_calls["count"] == 1
    assert exec_calls["count"] == 1


def test_should_filter_macos_stderr_line_matches_known_noise() -> None:
    from gui import launcher

    assert launcher._should_filter_macos_stderr_line(
        "TSMSendMessageToUIServer: CFMessagePortSendRequest FAILED(-1) "
        "to send to port com.apple.tsm.uiserver\n"
    )
    assert launcher._should_filter_macos_stderr_line(
        "This plugin does not support propagateSizeHints()\n"
    )
    assert not launcher._should_filter_macos_stderr_line("RuntimeError: boom\n")


def test_install_macos_stderr_filter_skips_when_tsm_debug_is_enabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from gui import launcher

    monkeypatch.setattr(launcher.sys, "platform", "darwin")
    monkeypatch.setenv("SSA_TSM_DEBUG", "1")

    assert launcher._install_macos_stderr_filter(
        launcher.logging.getLogger("test")
    ) is None
