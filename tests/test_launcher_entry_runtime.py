from __future__ import annotations

import os
import runpy
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def _run_entry_as_nuitka(
    monkeypatch,
    tmp_path: Path,
    entry_name: str,
    executable_name: str,
    *,
    compiled_global: bool = True,
) -> dict[str, object]:
    exe_dir = tmp_path / "entry.dist"
    exe_dir.mkdir()
    executable = exe_dir / executable_name
    executable.write_text("", encoding="utf-8")
    appdata = tmp_path / "appdata"
    appdata.mkdir()

    monkeypatch.setattr(sys, "executable", str(executable))
    monkeypatch.setenv("APPDATA", str(appdata))
    monkeypatch.setenv("LOCALAPPDATA", str(appdata))
    for key in (
        "SSA_BUNDLED_ROOT",
        "SSA_CONFIG_DIR",
        "SSA_DB_PATH",
        "SSA_EXTRA_ALLOWED_PATHS",
        "SSA_RUNTIME_ROOT",
    ):
        monkeypatch.delenv(key, raising=False)

    original_cwd = Path.cwd()
    original_sys_path = list(sys.path)
    try:
        init_globals = {"__compiled__": True} if compiled_global else None
        return runpy.run_path(
            str(REPO_ROOT / "launchers" / entry_name),
            init_globals=init_globals,
            run_name=f"test_{entry_name}",
        )
    finally:
        os.chdir(original_cwd)
        sys.path[:] = original_sys_path


def test_cli_entry_nuitka_runtime_does_not_use_build_repo_db(
    monkeypatch, tmp_path: Path
) -> None:
    namespace = _run_entry_as_nuitka(
        monkeypatch, tmp_path, "cli_entry.py", "SSA_CLI_v4.37_windows_amd64.exe"
    )

    db_path = Path(os.environ["SSA_DB_PATH"])
    runtime_root = Path(os.environ["SSA_RUNTIME_ROOT"])

    assert namespace["app_dir"] == str(tmp_path / "entry.dist")
    assert db_path == runtime_root / "data" / "ssas.db"
    assert REPO_ROOT not in db_path.parents


def test_cli_entry_nuitka_runtime_uses_executable_layout_without_compiled_global(
    monkeypatch, tmp_path: Path
) -> None:
    namespace = _run_entry_as_nuitka(
        monkeypatch,
        tmp_path,
        "cli_entry.py",
        "SSA_CLI_v4.37_windows_amd64.exe",
        compiled_global=False,
    )

    db_path = Path(os.environ["SSA_DB_PATH"])
    runtime_root = Path(os.environ["SSA_RUNTIME_ROOT"])

    assert namespace["app_dir"] == str(tmp_path / "entry.dist")
    assert db_path == runtime_root / "data" / "ssas.db"
    assert REPO_ROOT not in db_path.parents


def test_gui_entry_nuitka_runtime_does_not_use_build_repo_db(
    monkeypatch, tmp_path: Path
) -> None:
    namespace = _run_entry_as_nuitka(
        monkeypatch, tmp_path, "gui_entry.py", "SSA_GUI_v4.37_windows_amd64.exe"
    )

    db_path = Path(os.environ["SSA_DB_PATH"])
    runtime_root = Path(os.environ["SSA_RUNTIME_ROOT"])

    assert namespace["app_dir"] == str(tmp_path / "entry.dist")
    assert db_path == runtime_root / "data" / "ssas.db"
    assert REPO_ROOT not in db_path.parents
