from __future__ import annotations

import os
import runpy
import sys
from pathlib import Path
from typing import cast


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
    home_dir = tmp_path / "home"
    xdg_data_home = tmp_path / "xdg_data"
    appdata.mkdir()
    home_dir.mkdir()
    xdg_data_home.mkdir()

    monkeypatch.setattr(sys, "executable", str(executable))
    monkeypatch.setenv("APPDATA", str(appdata))
    monkeypatch.setenv("LOCALAPPDATA", str(appdata))
    monkeypatch.setenv("HOME", str(home_dir))
    monkeypatch.setenv("XDG_DATA_HOME", str(xdg_data_home))
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
    ssa_keys = (
        "SSA_BUNDLED_ROOT",
        "SSA_CONFIG_DIR",
        "SSA_DB_PATH",
        "SSA_EXTRA_ALLOWED_PATHS",
        "SSA_RUNTIME_ROOT",
    )
    original_env = {key: os.environ.get(key) for key in ssa_keys}
    try:
        init_globals = {"__compiled__": True} if compiled_global else None
        namespace = runpy.run_path(
            str(REPO_ROOT / "launchers" / entry_name),
            init_globals=init_globals,
            run_name=f"test_{entry_name}",
        )
        namespace["_runtime_env"] = {
            key: os.environ[key]
            for key in (
                "SSA_BUNDLED_ROOT",
                "SSA_CONFIG_DIR",
                "SSA_DB_PATH",
                "SSA_EXTRA_ALLOWED_PATHS",
                "SSA_RUNTIME_ROOT",
            )
            if key in os.environ
        }
        return namespace
    finally:
        os.chdir(original_cwd)
        sys.path[:] = original_sys_path
        for key, value in original_env.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


def _write_parent_data_db(tmp_path: Path) -> Path:
    parent_data = tmp_path / "data"
    parent_data.mkdir()
    parent_db = parent_data / "ssas.db"
    parent_db.write_text("local-db-must-not-be-seeded", encoding="utf-8")
    return parent_db


def test_cli_entry_nuitka_runtime_does_not_use_build_repo_db(
    monkeypatch, tmp_path: Path
) -> None:
    parent_db = _write_parent_data_db(tmp_path)

    namespace = _run_entry_as_nuitka(
        monkeypatch, tmp_path, "cli_entry.py", "SSA_CLI_v4.37_windows_amd64.exe"
    )

    runtime_env = cast(dict[str, str], namespace["_runtime_env"])
    db_path = Path(runtime_env["SSA_DB_PATH"])
    runtime_root = Path(runtime_env["SSA_RUNTIME_ROOT"])

    assert namespace["app_dir"] == str(tmp_path / "entry.dist")
    assert db_path == runtime_root / "data" / "ssas.db"
    assert REPO_ROOT not in db_path.parents
    assert parent_db.exists()
    assert not db_path.exists()


def test_cli_entry_nuitka_runtime_uses_executable_layout_without_compiled_global(
    monkeypatch, tmp_path: Path
) -> None:
    parent_db = _write_parent_data_db(tmp_path)

    namespace = _run_entry_as_nuitka(
        monkeypatch,
        tmp_path,
        "cli_entry.py",
        "SSA_CLI_v4.37_windows_amd64.exe",
        compiled_global=False,
    )

    runtime_env = cast(dict[str, str], namespace["_runtime_env"])
    db_path = Path(runtime_env["SSA_DB_PATH"])
    runtime_root = Path(runtime_env["SSA_RUNTIME_ROOT"])

    assert namespace["app_dir"] == str(tmp_path / "entry.dist")
    assert db_path == runtime_root / "data" / "ssas.db"
    assert REPO_ROOT not in db_path.parents
    assert parent_db.exists()
    assert not db_path.exists()


def test_gui_entry_nuitka_runtime_does_not_use_build_repo_db(
    monkeypatch, tmp_path: Path
) -> None:
    parent_db = _write_parent_data_db(tmp_path)

    namespace = _run_entry_as_nuitka(
        monkeypatch, tmp_path, "gui_entry.py", "SSA_GUI_v4.37_windows_amd64.exe"
    )

    runtime_env = cast(dict[str, str], namespace["_runtime_env"])
    db_path = Path(runtime_env["SSA_DB_PATH"])
    runtime_root = Path(runtime_env["SSA_RUNTIME_ROOT"])

    assert namespace["app_dir"] == str(tmp_path / "entry.dist")
    assert db_path == runtime_root / "data" / "ssas.db"
    assert REPO_ROOT not in db_path.parents
    assert parent_db.exists()
    assert not db_path.exists()


def test_launcher_runtime_helper_does_not_leak_ssa_environment(
    monkeypatch,
    tmp_path: Path,
) -> None:
    namespace = _run_entry_as_nuitka(
        monkeypatch,
        tmp_path,
        "cli_entry.py",
        "SSA_CLI_v4.37_windows_amd64.exe",
    )
    runtime_env = cast(dict[str, str], namespace["_runtime_env"])

    assert "SSA_RUNTIME_ROOT" in runtime_env
    for key in (
        "SSA_BUNDLED_ROOT",
        "SSA_CONFIG_DIR",
        "SSA_DB_PATH",
        "SSA_EXTRA_ALLOWED_PATHS",
        "SSA_RUNTIME_ROOT",
    ):
        assert key not in os.environ


def test_cli_entry_pyinstaller_runtime_uses_meipass_bundle_root(
    monkeypatch,
    tmp_path: Path,
) -> None:
    exe_dir = tmp_path / "dist"
    bundle_root = tmp_path / "_MEIPASS"
    bundled_config = bundle_root / "config"
    bundled_data = bundle_root / "data"
    bundled_config.mkdir(parents=True)
    bundled_data.mkdir()
    (bundled_config / "build_info.json").write_text("{}", encoding="utf-8")
    (bundled_data / "ssas.db").write_text("bundle-db", encoding="utf-8")
    executable = exe_dir / "SSA_CLI_v4.37_windows_amd64.exe"
    exe_dir.mkdir()
    executable.write_text("", encoding="utf-8")

    monkeypatch.setattr(sys, "executable", str(executable))
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "_MEIPASS", str(bundle_root), raising=False)
    monkeypatch.setenv("APPDATA", str(tmp_path / "appdata"))
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
        namespace = runpy.run_path(
            str(REPO_ROOT / "launchers" / "cli_entry.py"),
            run_name="test_cli_entry_pyinstaller",
        )
        runtime_root = Path(os.environ["SSA_RUNTIME_ROOT"])
        assert namespace["app_dir"] == str(bundle_root)
        assert Path(os.environ["SSA_CONFIG_DIR"]) == runtime_root / "config"
        assert (runtime_root / "config" / "build_info.json").is_file()
        assert (runtime_root / "data" / "ssas.db").read_text(encoding="utf-8") == "bundle-db"
    finally:
        os.chdir(original_cwd)
        sys.path[:] = original_sys_path


def test_gui_entry_pyinstaller_runtime_uses_meipass_bundle_root(
    monkeypatch,
    tmp_path: Path,
) -> None:
    exe_dir = tmp_path / "dist"
    bundle_root = tmp_path / "_MEIPASS"
    bundled_config = bundle_root / "config"
    bundled_data = bundle_root / "data"
    bundled_resources = bundle_root / "resources"
    bundled_config.mkdir(parents=True)
    bundled_data.mkdir()
    bundled_resources.mkdir()
    (bundled_config / "build_info.json").write_text("{}", encoding="utf-8")
    (bundled_data / "ssas.db").write_text("bundle-db", encoding="utf-8")
    (bundled_resources / "icon.txt").write_text("icon", encoding="utf-8")
    executable = exe_dir / "SSA_GUI_v4.37_windows_amd64.exe"
    exe_dir.mkdir()
    executable.write_text("", encoding="utf-8")

    monkeypatch.setattr(sys, "executable", str(executable))
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "_MEIPASS", str(bundle_root), raising=False)
    monkeypatch.setenv("APPDATA", str(tmp_path / "appdata"))
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
        namespace = runpy.run_path(
            str(REPO_ROOT / "launchers" / "gui_entry.py"),
            run_name="test_gui_entry_pyinstaller",
        )
        runtime_root = Path(os.environ["SSA_RUNTIME_ROOT"])
        assert namespace["app_dir"] == str(bundle_root)
        assert Path(os.environ["SSA_CONFIG_DIR"]) == runtime_root / "config"
        assert (runtime_root / "config" / "build_info.json").is_file()
        assert (runtime_root / "data" / "ssas.db").read_text(encoding="utf-8") == (
            "bundle-db"
        )
        assert (runtime_root / "resources" / "icon.txt").read_text(encoding="utf-8") == (
            "icon"
        )
    finally:
        os.chdir(original_cwd)
        sys.path[:] = original_sys_path


def test_cli_entry_pyoxidizer_runtime_uses_executable_dir_as_bundle_root(
    monkeypatch,
    tmp_path: Path,
) -> None:
    bundle_root = tmp_path / "pyoxidizer"
    bundled_config = bundle_root / "config"
    bundled_data = bundle_root / "data"
    bundled_config.mkdir(parents=True)
    bundled_data.mkdir()
    (bundled_config / "build_info.json").write_text("{}", encoding="utf-8")
    (bundled_data / "ssas.db").write_text("bundle-db", encoding="utf-8")
    executable = bundle_root / "SSA_Consulta_Rapida.exe"
    executable.write_text("", encoding="utf-8")

    monkeypatch.setattr(sys, "executable", str(executable))
    monkeypatch.setattr(sys, "oxidized", True, raising=False)
    monkeypatch.delattr(sys, "_MEIPASS", raising=False)
    monkeypatch.setenv("APPDATA", str(tmp_path / "appdata"))
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
        namespace = runpy.run_path(
            str(REPO_ROOT / "launchers" / "cli_entry.py"),
            run_name="test_cli_entry_pyoxidizer",
        )
        runtime_root = Path(os.environ["SSA_RUNTIME_ROOT"])
        assert namespace["app_dir"] == str(bundle_root)
        assert Path(os.environ["SSA_CONFIG_DIR"]) == runtime_root / "config"
        assert (runtime_root / "config" / "build_info.json").is_file()
        assert (runtime_root / "data" / "ssas.db").read_text(encoding="utf-8") == (
            "bundle-db"
        )
    finally:
        os.chdir(original_cwd)
        sys.path[:] = original_sys_path
