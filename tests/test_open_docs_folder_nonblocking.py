from typing import Any, cast

import pytest


def test_open_docs_folder_uses_qdesktopservices_when_available(monkeypatch, tmp_path):
    # Import inside the test so skip logic can inspect QT availability.
    from gui import gui_ssa

    if not getattr(gui_ssa, "QT_AVAILABLE", False):
        pytest.skip("Qt not available in this test environment")

    docs_dir = tmp_path / "docs_entrada"
    docs_dir.mkdir()

    monkeypatch.setattr(gui_ssa, "project_root", str(tmp_path))
    opened_urls = []

    class DummyQDesktopServices:
        @staticmethod
        def openUrl(url):
            opened_urls.append(url)
            return True

    monkeypatch.setattr(gui_ssa, "QDesktopServices", DummyQDesktopServices)
    monkeypatch.setattr(
        gui_ssa.subprocess, "run", lambda *a, **k: pytest.fail("subprocess.run called")
    )
    monkeypatch.setattr(
        gui_ssa.subprocess,
        "Popen",
        lambda *a, **k: pytest.fail("subprocess.Popen called"),
    )
    monkeypatch.setattr(
        gui_ssa.QMessageBox,
        "warning",
        lambda *a, **k: pytest.fail("QMessageBox.warning called"),
    )

    gui_ssa.SSAMainWindow.open_docs_folder(cast(Any, object()))

    assert opened_urls, "Expected QDesktopServices.openUrl to be used"


def test_resolve_platform_open_command_prefers_absolute_windows_launcher(monkeypatch):
    from gui import gui_ssa
    from gui.ssa import system_integration

    monkeypatch.setattr(system_integration.sys, "platform", "win32")
    monkeypatch.setenv("WINDIR", r"C:\\Windows")
    monkeypatch.setattr(
        system_integration.ntpath,
        "isfile",
        lambda path: path == r"C:\Windows\explorer.exe",
    )
    monkeypatch.setattr(
        system_integration.shutil,
        "which",
        lambda _name: pytest.fail("shutil.which should not be needed"),
    )

    resolved = gui_ssa.SSAMainWindow._resolve_platform_open_command()

    assert resolved == r"C:\Windows\explorer.exe"


def test_resolve_platform_open_command_prefers_absolute_linux_launcher(monkeypatch):
    from gui import gui_ssa
    from gui.ssa import system_integration

    monkeypatch.setattr(system_integration.sys, "platform", "linux")
    monkeypatch.setattr(
        system_integration.posixpath,
        "isfile",
        lambda path: path == "/usr/bin/xdg-open",
    )
    monkeypatch.setattr(
        system_integration.shutil,
        "which",
        lambda _name: pytest.fail("shutil.which should not be needed"),
    )

    resolved = gui_ssa.SSAMainWindow._resolve_platform_open_command()

    assert resolved == "/usr/bin/xdg-open"


def test_open_docs_folder_missing_skips_modal_under_pytest(monkeypatch, tmp_path):
    from gui import gui_ssa

    if not getattr(gui_ssa, "QT_AVAILABLE", False):
        pytest.skip("Qt not available in this test environment")

    # Ensure the guard condition is active even if pytest env var is not set for some runner.
    monkeypatch.setenv("PYTEST_CURRENT_TEST", "1")

    monkeypatch.setattr(gui_ssa, "project_root", str(tmp_path))
    monkeypatch.setattr(
        gui_ssa.QMessageBox,
        "warning",
        lambda *a, **k: pytest.fail("QMessageBox.warning called"),
    )

    gui_ssa.SSAMainWindow.open_docs_folder(cast(Any, object()))


def test_open_docs_folder_missing_prompts_and_creates_folder(monkeypatch, tmp_path):
    from gui import gui_ssa

    if not getattr(gui_ssa, "QT_AVAILABLE", False):
        pytest.skip("Qt not available in this test environment")

    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
    monkeypatch.setattr(gui_ssa, "project_root", str(tmp_path))

    class _StdButtons:
        Yes = 1
        No = 2

    asks = {"count": 0}

    def _question(*_args, **_kwargs):
        asks["count"] += 1
        return _StdButtons.Yes

    class DummyQDesktopServices:
        @staticmethod
        def openUrl(_url):
            return True

    monkeypatch.setattr(gui_ssa, "QDesktopServices", DummyQDesktopServices)
    monkeypatch.setattr(
        gui_ssa.QMessageBox, "StandardButton", _StdButtons, raising=False
    )
    monkeypatch.setattr(gui_ssa.QMessageBox, "question", _question, raising=False)
    monkeypatch.setattr(
        gui_ssa.QMessageBox,
        "warning",
        lambda *a, **k: pytest.fail("QMessageBox.warning called"),
    )

    target_folder = tmp_path / "docs_entrada"
    assert not target_folder.exists()
    gui_ssa.SSAMainWindow.open_docs_folder(cast(Any, object()))

    assert asks["count"] == 1
    assert target_folder.exists()
