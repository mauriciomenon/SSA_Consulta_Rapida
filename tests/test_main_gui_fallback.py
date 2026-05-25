from __future__ import annotations

import builtins
import os
import subprocess
import sys

import pytest


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
