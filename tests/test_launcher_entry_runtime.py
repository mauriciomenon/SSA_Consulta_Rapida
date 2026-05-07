from __future__ import annotations

import os
import runpy
import shutil
import sys
from pathlib import Path
from types import ModuleType
from typing import Callable, cast

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]
SSA_ENV_KEYS = (
    "SSA_BUNDLED_ROOT",
    "SSA_CONFIG_DIR",
    "SSA_DB_PATH",
    "SSA_EXTRA_ALLOWED_PATHS",
    "SSA_RUNTIME_ROOT",
)


def _prepare_isolated_runtime_env(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("APPDATA", str(tmp_path / "appdata"))
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "appdata"))
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "xdg_data"))
    for key in SSA_ENV_KEYS:
        monkeypatch.delenv(key, raising=False)


def _bootstrap_entry_namespace(namespace: dict[str, object]) -> None:
    bootstrap_runtime = namespace.get("_bootstrap_runtime")
    if callable(bootstrap_runtime):
        app_dir = cast(Callable[[], object], bootstrap_runtime)()
        if isinstance(app_dir, str):
            namespace["app_dir"] = app_dir


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
    monkeypatch.setattr(sys, "executable", str(executable))
    _prepare_isolated_runtime_env(monkeypatch, tmp_path)

    original_cwd = Path.cwd()
    original_sys_path = list(sys.path)
    original_env = {key: os.environ.get(key) for key in SSA_ENV_KEYS}
    try:
        init_globals = {"__compiled__": True} if compiled_global else None
        namespace = runpy.run_path(
            str(REPO_ROOT / "launchers" / entry_name),
            init_globals=init_globals,
            run_name=f"test_{entry_name}",
        )
        _bootstrap_entry_namespace(namespace)
        namespace["_runtime_env"] = {
            key: os.environ[key]
            for key in SSA_ENV_KEYS
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


def test_cli_entry_loads_local_helpers_without_launchers_package(
    monkeypatch, tmp_path: Path
) -> None:
    entry_path = tmp_path / "cli_entry.py"
    helper_path = tmp_path / "runtime_entry_helpers.py"
    entry_path.write_text((REPO_ROOT / "launchers" / "cli_entry.py").read_text(encoding="utf-8"), encoding="utf-8")
    helper_path.write_text(
        "CLI_SMOKE_OK_MARKER = 'ok'\n"
        "SMOKE_TEST_ENV = 'SSA_SMOKE_TEST'\n"
        "def bootstrap_entry_runtime(*args, **kwargs): return 'runtime'\n"
        "def log_launcher_failure(*args, **kwargs): return None\n"
        "def resolve_runtime_home(*args, **kwargs): return None\n"
        "def seed_runtime_config(*args, **kwargs): return None\n"
        "def seed_runtime_data(*args, **kwargs): return None\n",
        encoding="utf-8",
    )
    monkeypatch.syspath_prepend(str(tmp_path))
    monkeypatch.setitem(sys.modules, "launchers", None)
    monkeypatch.delitem(sys.modules, "runtime_entry_helpers", raising=False)

    namespace = runpy.run_path(str(entry_path), run_name="frozen_cli_entry_test")

    assert callable(namespace["_bootstrap_runtime"])


def test_gui_entry_loads_local_helpers_without_launchers_package(
    monkeypatch, tmp_path: Path
) -> None:
    entry_path = tmp_path / "gui_entry.py"
    helper_path = tmp_path / "runtime_entry_helpers.py"
    entry_path.write_text(
        (REPO_ROOT / "launchers" / "gui_entry.py").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    helper_path.write_text(
        "GUI_SMOKE_OK_MARKER = 'ok'\n"
        "SMOKE_TEST_ENV = 'SSA_SMOKE_TEST'\n"
        "def bootstrap_entry_runtime(*args, **kwargs): return 'runtime'\n"
        "def log_launcher_failure(*args, **kwargs): return None\n"
        "def seed_runtime_config(*args, **kwargs): return None\n"
        "def seed_runtime_data(*args, **kwargs): return None\n"
        "def seed_runtime_resources(*args, **kwargs): return None\n",
        encoding="utf-8",
    )
    monkeypatch.syspath_prepend(str(tmp_path))
    monkeypatch.setitem(sys.modules, "launchers", None)
    monkeypatch.delitem(sys.modules, "runtime_entry_helpers", raising=False)

    namespace = runpy.run_path(str(entry_path), run_name="frozen_gui_entry_test")

    assert callable(namespace["_bootstrap_runtime"])


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


def test_cli_entry_nuitka_runtime_overwrites_stale_ssa_environment(
    monkeypatch,
    tmp_path: Path,
) -> None:
    exe_dir = tmp_path / "entry.dist"
    exe_dir.mkdir()
    executable = exe_dir / "SSA_CLI_v4.37_windows_amd64.exe"
    executable.write_text("", encoding="utf-8")
    stale_root = tmp_path / "stale"
    stale_root.mkdir()

    monkeypatch.setattr(sys, "executable", str(executable))
    _prepare_isolated_runtime_env(monkeypatch, tmp_path)
    monkeypatch.setenv("SSA_BUNDLED_ROOT", str(stale_root))
    monkeypatch.setenv("SSA_RUNTIME_ROOT", str(tmp_path / "runtime"))
    monkeypatch.setenv("SSA_CONFIG_DIR", str(stale_root / "config"))
    monkeypatch.setenv("SSA_DB_PATH", str(stale_root / "data" / "ssas.db"))

    original_cwd = Path.cwd()
    original_sys_path = list(sys.path)
    try:
        namespace = runpy.run_path(
            str(REPO_ROOT / "launchers" / "cli_entry.py"),
            init_globals={"__compiled__": True},
            run_name="test_cli_entry_stale_env",
        )
        _bootstrap_entry_namespace(namespace)
        runtime_root = Path(os.environ["SSA_RUNTIME_ROOT"])
        assert os.environ["SSA_BUNDLED_ROOT"] == str(exe_dir)
        assert Path(os.environ["SSA_CONFIG_DIR"]) == runtime_root / "config"
        assert Path(os.environ["SSA_DB_PATH"]) == runtime_root / "data" / "ssas.db"
        assert stale_root not in Path(os.environ["SSA_DB_PATH"]).parents
    finally:
        os.chdir(original_cwd)
        sys.path[:] = original_sys_path


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
    for key in SSA_ENV_KEYS:
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
    _prepare_isolated_runtime_env(monkeypatch, tmp_path)

    original_cwd = Path.cwd()
    original_sys_path = list(sys.path)
    try:
        namespace = runpy.run_path(
            str(REPO_ROOT / "launchers" / "cli_entry.py"),
            run_name="test_cli_entry_pyinstaller",
        )
        _bootstrap_entry_namespace(namespace)
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
    _prepare_isolated_runtime_env(monkeypatch, tmp_path)

    original_cwd = Path.cwd()
    original_sys_path = list(sys.path)
    try:
        namespace = runpy.run_path(
            str(REPO_ROOT / "launchers" / "gui_entry.py"),
            run_name="test_gui_entry_pyinstaller",
        )
        _bootstrap_entry_namespace(namespace)
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
    _prepare_isolated_runtime_env(monkeypatch, tmp_path)

    original_cwd = Path.cwd()
    original_sys_path = list(sys.path)
    try:
        namespace = runpy.run_path(
            str(REPO_ROOT / "launchers" / "cli_entry.py"),
            run_name="test_cli_entry_pyoxidizer",
        )
        _bootstrap_entry_namespace(namespace)
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


def test_cli_seed_runtime_config_does_not_overwrite_user_files(tmp_path: Path) -> None:
    namespace = runpy.run_path(
        str(REPO_ROOT / "launchers" / "cli_entry.py"),
        run_name="test_cli_seed_config",
    )
    seed_config = namespace["_seed_runtime_config"]
    runtime_dir = tmp_path / "runtime"
    bundled_config = tmp_path / "bundle" / "config"
    bundled_config_nested = bundled_config / "nested"
    user_config_nested = runtime_dir / "config" / "nested"
    bundled_config_nested.mkdir(parents=True)
    user_config_nested.mkdir(parents=True)
    (bundled_config_nested / "settings.json").write_text("bundle", encoding="utf-8")
    (bundled_config_nested / "new.json").write_text("new", encoding="utf-8")
    (user_config_nested / "settings.json").write_text("user", encoding="utf-8")

    seed_config(runtime_dir, bundled_config)

    assert (user_config_nested / "settings.json").read_text(encoding="utf-8") == "user"
    assert (user_config_nested / "new.json").read_text(encoding="utf-8") == "new"


def test_gui_seed_runtime_resources_does_not_overwrite_user_files(
    tmp_path: Path,
) -> None:
    namespace = runpy.run_path(
        str(REPO_ROOT / "launchers" / "gui_entry.py"),
        run_name="test_gui_seed_resources",
    )
    seed_resources = namespace["_seed_runtime_resources"]
    runtime_dir = tmp_path / "runtime"
    bundled_resources = tmp_path / "bundle" / "resources"
    bundled_resources_nested = bundled_resources / "icons"
    user_resources_nested = runtime_dir / "resources" / "icons"
    bundled_resources_nested.mkdir(parents=True)
    user_resources_nested.mkdir(parents=True)
    (bundled_resources_nested / "theme.txt").write_text("bundle", encoding="utf-8")
    (bundled_resources_nested / "new.txt").write_text("new", encoding="utf-8")
    (user_resources_nested / "theme.txt").write_text("user", encoding="utf-8")

    seed_resources(runtime_dir, bundled_resources)

    assert (user_resources_nested / "theme.txt").read_text(encoding="utf-8") == "user"
    assert (user_resources_nested / "new.txt").read_text(encoding="utf-8") == "new"


def test_gui_seed_runtime_resources_reports_copy_failure(
    monkeypatch,
    tmp_path: Path,
    capsys,
) -> None:
    from launchers.runtime_entry_helpers import seed_runtime_resources

    runtime_dir = tmp_path / "runtime"
    bundled_resources = tmp_path / "bundle" / "resources"
    bundled_resources.mkdir(parents=True)
    (bundled_resources / "icon.txt").write_text("icon", encoding="utf-8")

    robust_logging = ModuleType("utils.robust_logging")

    def fail_get_logger():
        raise RuntimeError("logger unavailable")

    setattr(robust_logging, "get_robust_logger", fail_get_logger)
    monkeypatch.setitem(sys.modules, "utils.robust_logging", robust_logging)

    def fail_copy2(*_args: object, **_kwargs: object) -> None:
        raise PermissionError("read only target")

    monkeypatch.setattr(shutil, "copy2", fail_copy2)

    result = seed_runtime_resources(
        runtime_dir,
        bundled_resources,
        logger_name="gui_entry",
    )

    captured = capsys.readouterr()
    assert result == runtime_dir / "resources"
    assert "Falha ao preparar resources de runtime: read only target" in captured.err


def test_runtime_copy_missing_tree_uses_marker_to_skip_repeated_scan(
    monkeypatch,
    tmp_path: Path,
) -> None:
    from launchers import runtime_entry_helpers

    source_dir = tmp_path / "bundle" / "config"
    target_dir = tmp_path / "runtime" / "config"
    nested = source_dir / "nested"
    nested.mkdir(parents=True)
    target_dir.mkdir(parents=True)
    (nested / "settings.json").write_text("bundle", encoding="utf-8")

    runtime_entry_helpers.copy_missing_tree(
        source_dir,
        target_dir,
        marker_name=".ssa_seed_config",
    )
    assert (target_dir / "nested" / "settings.json").is_file()

    def fail_rglob(_pattern: str):
        raise AssertionError("rglob nao deve rodar quando marcador esta valido")

    monkeypatch.setattr(Path, "rglob", fail_rglob)

    runtime_entry_helpers.copy_missing_tree(
        source_dir,
        target_dir,
        marker_name=".ssa_seed_config",
    )


def test_runtime_copy_missing_tree_restores_missing_top_level_entry(
    tmp_path: Path,
) -> None:
    from launchers import runtime_entry_helpers

    source_dir = tmp_path / "bundle" / "config"
    target_dir = tmp_path / "runtime" / "config"
    source_dir.mkdir(parents=True)
    target_dir.mkdir(parents=True)
    (source_dir / "root.txt").write_text("bundle", encoding="utf-8")

    runtime_entry_helpers.copy_missing_tree(
        source_dir,
        target_dir,
        marker_name=".ssa_seed_config",
    )
    (target_dir / "root.txt").unlink()

    runtime_entry_helpers.copy_missing_tree(
        source_dir,
        target_dir,
        marker_name=".ssa_seed_config",
    )

    assert (target_dir / "root.txt").read_text(encoding="utf-8") == "bundle"


def test_cli_entry_force_rescan_runs_importer_without_interactive_cli(
    monkeypatch,
) -> None:
    calls: list[tuple[str, object]] = []

    config_manager = ModuleType("core.config_manager")
    setattr(
        config_manager,
        "ensure_default_settings",
        lambda fail_fast: calls.append(("ensure", fail_fast)),
    )
    app_logic = ModuleType("core.app_logic")

    def fake_run_importer_logic(**kwargs: object) -> dict[str, str]:
        calls.append(("import", kwargs))
        return {"status": "success"}

    setattr(app_logic, "run_importer_logic", fake_run_importer_logic)
    cli_module = ModuleType("interface.cli")

    def fail_start_cli_loop(*_args: object) -> None:
        raise AssertionError("start_cli_loop nao deve rodar em --force-rescan")

    setattr(cli_module, "start_cli_loop", fail_start_cli_loop)
    setup_project_structure = ModuleType("utils.setup_project_structure")
    setattr(
        setup_project_structure,
        "setup_dirs",
        lambda base_path=None: calls.append(("setup", base_path)),
    )
    import utils

    monkeypatch.setitem(sys.modules, "core.config_manager", config_manager)
    monkeypatch.setitem(sys.modules, "core.app_logic", app_logic)
    monkeypatch.setitem(sys.modules, "interface.cli", cli_module)
    monkeypatch.setitem(
        sys.modules,
        "utils.setup_project_structure",
        setup_project_structure,
    )
    monkeypatch.setattr(
        utils,
        "setup_project_structure",
        setup_project_structure,
        raising=False,
    )
    monkeypatch.setattr(sys, "argv", ["SSA_CLI", "--force-rescan"])
    for key in SSA_ENV_KEYS:
        monkeypatch.delenv(key, raising=False)

    namespace = runpy.run_path(
        str(REPO_ROOT / "launchers" / "cli_entry.py"),
        run_name="test_cli_force_rescan",
    )

    with pytest.raises(SystemExit) as exc_info:
        namespace["main"]()

    assert exc_info.value.code == 0
    assert calls[0:2] == [("setup", str(REPO_ROOT)), ("ensure", False)]
    assert calls[2][0] == "import"
    import_kwargs = cast(dict[str, object], calls[2][1])
    assert import_kwargs["force_import"] is True
    assert import_kwargs["docs_dir"] == os.path.join(str(REPO_ROOT), "docs_entrada")
    assert import_kwargs["data_dir"] == os.path.join(str(REPO_ROOT), "data")
    assert import_kwargs["extra_allowed_roots"] == [str(REPO_ROOT)]
    assert os.environ["SSA_DB_PATH"].endswith(os.path.join("data", "ssas.db"))


def test_cli_entry_force_rescan_returns_error_when_import_reports_candidate_failure(
    monkeypatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    calls: list[tuple[str, object]] = []

    config_manager = ModuleType("core.config_manager")
    setattr(
        config_manager,
        "ensure_default_settings",
        lambda fail_fast: calls.append(("ensure", fail_fast)),
    )
    app_logic = ModuleType("core.app_logic")

    def fake_run_importer_logic(**kwargs: object) -> bool:
        calls.append(("import", kwargs))
        callback = cast(Callable[[str, dict[str, object]], None], kwargs["progress_callback"])
        callback("start", {"total": 1})
        callback("file_error", {"filename": "bad.xlsx", "error": "bad cols"})
        callback(
            "finish",
            {
                "total": 1,
                "processed": 0,
                "errors": [("extraction", "bad.xlsx", "bad cols")],
            },
        )
        return False

    setattr(app_logic, "run_importer_logic", fake_run_importer_logic)
    cli_module = ModuleType("interface.cli")

    def fail_start_cli_loop(*_args: object) -> None:
        raise AssertionError("start_cli_loop nao deve rodar em --force-rescan")

    setattr(cli_module, "start_cli_loop", fail_start_cli_loop)
    setup_project_structure = ModuleType("utils.setup_project_structure")
    setattr(
        setup_project_structure,
        "setup_dirs",
        lambda base_path=None: calls.append(("setup", base_path)),
    )
    import utils

    monkeypatch.setitem(sys.modules, "core.config_manager", config_manager)
    monkeypatch.setitem(sys.modules, "core.app_logic", app_logic)
    monkeypatch.setitem(sys.modules, "interface.cli", cli_module)
    monkeypatch.setitem(
        sys.modules,
        "utils.setup_project_structure",
        setup_project_structure,
    )
    monkeypatch.setattr(
        utils,
        "setup_project_structure",
        setup_project_structure,
        raising=False,
    )
    monkeypatch.setattr(sys, "argv", ["SSA_CLI", "--force-rescan"])
    for key in SSA_ENV_KEYS:
        monkeypatch.delenv(key, raising=False)

    namespace = runpy.run_path(
        str(REPO_ROOT / "launchers" / "cli_entry.py"),
        run_name="test_cli_force_rescan_false",
    )

    with pytest.raises(SystemExit) as exc_info:
        namespace["main"]()

    captured = capsys.readouterr()
    assert exc_info.value.code == 1
    assert calls[0:2] == [("setup", str(REPO_ROOT)), ("ensure", False)]
    assert calls[2][0] == "import"
    assert "Importacao nao gravou atualizacoes" in captured.err
    assert "Importacao concluida" not in captured.out


def test_cli_entry_force_rescan_no_work_keeps_success_exit(
    monkeypatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    calls: list[tuple[str, object]] = []

    config_manager = ModuleType("core.config_manager")
    setattr(
        config_manager,
        "ensure_default_settings",
        lambda fail_fast: calls.append(("ensure", fail_fast)),
    )
    app_logic = ModuleType("core.app_logic")

    def fake_run_importer_logic(**kwargs: object) -> bool:
        calls.append(("import", kwargs))
        callback = cast(Callable[[str, dict[str, object]], None], kwargs["progress_callback"])
        callback("start", {"total": 0})
        callback("finish", {"total": 0, "processed": 0, "errors": []})
        return False

    setattr(app_logic, "run_importer_logic", fake_run_importer_logic)
    cli_module = ModuleType("interface.cli")

    def fail_start_cli_loop(*_args: object) -> None:
        raise AssertionError("start_cli_loop nao deve rodar em --force-rescan")

    setattr(cli_module, "start_cli_loop", fail_start_cli_loop)
    setup_project_structure = ModuleType("utils.setup_project_structure")
    setattr(
        setup_project_structure,
        "setup_dirs",
        lambda base_path=None: calls.append(("setup", base_path)),
    )
    import utils

    monkeypatch.setitem(sys.modules, "core.config_manager", config_manager)
    monkeypatch.setitem(sys.modules, "core.app_logic", app_logic)
    monkeypatch.setitem(sys.modules, "interface.cli", cli_module)
    monkeypatch.setitem(
        sys.modules,
        "utils.setup_project_structure",
        setup_project_structure,
    )
    monkeypatch.setattr(
        utils,
        "setup_project_structure",
        setup_project_structure,
        raising=False,
    )
    monkeypatch.setattr(sys, "argv", ["SSA_CLI", "--force-rescan"])
    for key in SSA_ENV_KEYS:
        monkeypatch.delenv(key, raising=False)

    namespace = runpy.run_path(
        str(REPO_ROOT / "launchers" / "cli_entry.py"),
        run_name="test_cli_force_rescan_no_work",
    )

    with pytest.raises(SystemExit) as exc_info:
        namespace["main"]()

    captured = capsys.readouterr()
    assert exc_info.value.code == 0
    assert calls[0:2] == [("setup", str(REPO_ROOT)), ("ensure", False)]
    assert calls[2][0] == "import"
    assert "Importacao concluida sem atualizacoes" in captured.out
    assert "ERRO:" not in captured.err


def test_cli_entry_force_rescan_candidate_without_update_is_failure(
    monkeypatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    calls: list[tuple[str, object]] = []

    config_manager = ModuleType("core.config_manager")
    setattr(
        config_manager,
        "ensure_default_settings",
        lambda fail_fast: calls.append(("ensure", fail_fast)),
    )
    app_logic = ModuleType("core.app_logic")

    def fake_run_importer_logic(**kwargs: object) -> bool:
        calls.append(("import", kwargs))
        callback = cast(Callable[[str, dict[str, object]], None], kwargs["progress_callback"])
        callback("start", {"total": 2})
        callback("finish", {"total": 2, "processed": 2, "errors": []})
        return False

    setattr(app_logic, "run_importer_logic", fake_run_importer_logic)
    cli_module = ModuleType("interface.cli")
    setattr(
        cli_module,
        "start_cli_loop",
        lambda *_args: (_ for _ in ()).throw(
            AssertionError("start_cli_loop nao deve rodar em --force-rescan")
        ),
    )
    setup_project_structure = ModuleType("utils.setup_project_structure")
    setattr(
        setup_project_structure,
        "setup_dirs",
        lambda base_path=None: calls.append(("setup", base_path)),
    )
    import utils

    monkeypatch.setitem(sys.modules, "core.config_manager", config_manager)
    monkeypatch.setitem(sys.modules, "core.app_logic", app_logic)
    monkeypatch.setitem(sys.modules, "interface.cli", cli_module)
    monkeypatch.setitem(
        sys.modules,
        "utils.setup_project_structure",
        setup_project_structure,
    )
    monkeypatch.setattr(
        utils,
        "setup_project_structure",
        setup_project_structure,
        raising=False,
    )
    monkeypatch.setattr(sys, "argv", ["SSA_CLI", "--force-rescan"])
    for key in SSA_ENV_KEYS:
        monkeypatch.delenv(key, raising=False)

    namespace = runpy.run_path(
        str(REPO_ROOT / "launchers" / "cli_entry.py"),
        run_name="test_cli_force_rescan_no_update",
    )

    with pytest.raises(SystemExit) as exc_info:
        namespace["main"]()

    captured = capsys.readouterr()
    assert exc_info.value.code == 1
    assert "Importacao nao gravou atualizacoes" in captured.err
    assert "Importacao concluida" not in captured.out


def test_cli_entry_force_rescan_partial_errors_fail_exit(
    monkeypatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    calls: list[tuple[str, object]] = []

    config_manager = ModuleType("core.config_manager")
    setattr(
        config_manager,
        "ensure_default_settings",
        lambda fail_fast: calls.append(("ensure", fail_fast)),
    )
    app_logic = ModuleType("core.app_logic")

    def fake_run_importer_logic(**kwargs: object) -> bool:
        calls.append(("import", kwargs))
        callback = cast(Callable[[str, dict[str, object]], None], kwargs["progress_callback"])
        callback("start", {"total": 2})
        callback("file_error", {"filename": "bad.xlsx", "error": "bad cols"})
        callback("finish", {"total": 2, "processed": 1, "errors": ["bad.xlsx"]})
        return True

    setattr(app_logic, "run_importer_logic", fake_run_importer_logic)
    cli_module = ModuleType("interface.cli")
    setattr(
        cli_module,
        "start_cli_loop",
        lambda *_args: (_ for _ in ()).throw(
            AssertionError("start_cli_loop nao deve rodar em --force-rescan")
        ),
    )
    setup_project_structure = ModuleType("utils.setup_project_structure")
    setattr(
        setup_project_structure,
        "setup_dirs",
        lambda base_path=None: calls.append(("setup", base_path)),
    )
    import utils

    monkeypatch.setitem(sys.modules, "core.config_manager", config_manager)
    monkeypatch.setitem(sys.modules, "core.app_logic", app_logic)
    monkeypatch.setitem(sys.modules, "interface.cli", cli_module)
    monkeypatch.setitem(
        sys.modules,
        "utils.setup_project_structure",
        setup_project_structure,
    )
    monkeypatch.setattr(
        utils,
        "setup_project_structure",
        setup_project_structure,
        raising=False,
    )
    monkeypatch.setattr(sys, "argv", ["SSA_CLI", "--force-rescan"])
    for key in SSA_ENV_KEYS:
        monkeypatch.delenv(key, raising=False)

    namespace = runpy.run_path(
        str(REPO_ROOT / "launchers" / "cli_entry.py"),
        run_name="test_cli_force_rescan_partial",
    )

    with pytest.raises(SystemExit) as exc_info:
        namespace["main"]()

    captured = capsys.readouterr()
    assert exc_info.value.code == 1
    assert "Importacao parcial encontrou falhas" in captured.err
    assert "Importacao concluida" not in captured.out


def test_gui_ssa_keeps_project_root_out_of_import_path_contract() -> None:
    source = (REPO_ROOT / "gui" / "gui_ssa.py").read_text(encoding="utf-8")

    assert "code_root = os.path.abspath" in source
    assert "sys.path.insert(0, code_root)" in source
    assert "sys.path.insert(0, project_root)" not in source
