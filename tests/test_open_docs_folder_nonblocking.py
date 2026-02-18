import pytest
from typing import Any, cast


def test_open_docs_folder_uses_qdesktopservices_when_available(monkeypatch, tmp_path):
    # Import inside the test so skip logic can inspect QT availability.
    from gui import gui_ssa

    if not getattr(gui_ssa, "QT_AVAILABLE", False):
        pytest.skip("Qt not available in this test environment")

    docs_dir = tmp_path / "docs_entrada"
    docs_dir.mkdir()

    monkeypatch.setattr(gui_ssa, "project_root", str(tmp_path))

    class DummyQDesktopServices:
        called = []

        @staticmethod
        def openUrl(url):
            DummyQDesktopServices.called.append(url)
            return True

    monkeypatch.setattr(gui_ssa, "QDesktopServices", DummyQDesktopServices)
    DummyQDesktopServices.called.clear()
    monkeypatch.setattr(gui_ssa.subprocess, "run", lambda *a, **k: pytest.fail("subprocess.run called"))
    monkeypatch.setattr(gui_ssa.subprocess, "Popen", lambda *a, **k: pytest.fail("subprocess.Popen called"))
    monkeypatch.setattr(gui_ssa.QMessageBox, "warning", lambda *a, **k: pytest.fail("QMessageBox.warning called"))

    gui_ssa.SSAMainWindow.open_docs_folder(cast(Any, object()))

    assert DummyQDesktopServices.called, "Expected QDesktopServices.openUrl to be used"


def test_open_docs_folder_missing_skips_modal_under_pytest(monkeypatch, tmp_path):
    from gui import gui_ssa

    if not getattr(gui_ssa, "QT_AVAILABLE", False):
        pytest.skip("Qt not available in this test environment")

    # Ensure the guard condition is active even if pytest env var is not set for some runner.
    monkeypatch.setenv("PYTEST_CURRENT_TEST", "1")

    monkeypatch.setattr(gui_ssa, "project_root", str(tmp_path))
    monkeypatch.setattr(gui_ssa.QMessageBox, "warning", lambda *a, **k: pytest.fail("QMessageBox.warning called"))

    gui_ssa.SSAMainWindow.open_docs_folder(cast(Any, object()))
