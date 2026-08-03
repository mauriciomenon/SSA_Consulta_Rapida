from __future__ import annotations

import os
import shutil
import sys
import tempfile
from pathlib import Path
from types import ModuleType


APP_RUNTIME_NAME = "SSA_Consulta_Rapida"
RUNTIME_HOME_ARG = "--runtime-home"
SMOKE_TEST_ENV = "SSA_SMOKE_TEST"
CLI_SMOKE_OK_MARKER = "SMOKE_CLI_OK"
GUI_SMOKE_OK_MARKER = "SMOKE_GUI_OK"


def resolve_runtime_home() -> Path:
    """Return a writable runtime directory for frozen apps."""
    home_dir = Path.home()
    if sys.platform == "darwin":
        base_dir = home_dir / "Library" / "Application Support"
    elif sys.platform.startswith("win"):
        appdata = os.environ.get("APPDATA")
        if appdata:
            base_dir = Path(appdata)
        else:
            base_dir = home_dir / "AppData" / "Roaming"
    else:
        base_dir = Path(os.environ.get("XDG_DATA_HOME", home_dir / ".local" / "share"))

    runtime_dir = base_dir / APP_RUNTIME_NAME
    runtime_dir.mkdir(parents=True, exist_ok=True)
    return runtime_dir


def resolve_executable_path() -> Path:
    executable = str(getattr(sys, "executable", "") or "").strip()
    if executable:
        return Path(executable).resolve()
    return Path(__file__).resolve()


def resolve_bundle_root() -> Path:
    meipass = str(getattr(sys, "_MEIPASS", "") or "").strip()
    if meipass:
        return Path(meipass).resolve()
    return resolve_executable_path().parent


def is_frozen_entry(
    exe_path: Path,
    *,
    executable_prefixes: tuple[str, ...],
    global_vars: dict[str, object],
) -> bool:
    return bool(
        getattr(sys, "frozen", False)
        or getattr(sys, "oxidized", False)
        or "__compiled__" in global_vars
        or exe_path.parent.name.endswith(".dist")
        or exe_path.name.startswith(executable_prefixes)
    )


def resolve_entry_runtime(
    entry_file: str,
    *,
    executable_prefixes: tuple[str, ...],
    global_vars: dict[str, object],
) -> tuple[Path, bool, str]:
    exe_path = resolve_executable_path()
    is_frozen_runtime = is_frozen_entry(
        exe_path,
        executable_prefixes=executable_prefixes,
        global_vars=global_vars,
    )
    if is_frozen_runtime:
        app_dir = str(resolve_bundle_root())
    else:
        app_dir = os.path.dirname(os.path.dirname(os.path.abspath(entry_file)))
    return exe_path, is_frozen_runtime, app_dir


def bootstrap_entry_import_path(
    global_vars: dict[str, object],
    entry_file: str,
    *,
    executable_prefixes: tuple[str, ...],
    sys_module: ModuleType = sys,
) -> tuple[Path, bool, str]:
    exe_path, is_frozen_runtime, app_dir = resolve_entry_runtime(
        entry_file,
        executable_prefixes=executable_prefixes,
        global_vars=global_vars,
    )
    global_vars["exe_path"] = exe_path
    global_vars["is_frozen_runtime"] = is_frozen_runtime
    global_vars["app_dir"] = app_dir
    if app_dir not in sys_module.path:
        sys_module.path.insert(0, app_dir)
    return exe_path, is_frozen_runtime, app_dir


def bootstrap_entry_runtime(
    global_vars: dict[str, object],
    entry_file: str,
    *,
    executable_prefixes: tuple[str, ...],
    logger_name: str,
    include_resources: bool,
    copy_all_data: bool,
    create_common_dirs: bool,
    sys_module: ModuleType = sys,
) -> str:
    _, is_frozen_runtime, app_dir = bootstrap_entry_import_path(
        global_vars,
        entry_file,
        executable_prefixes=executable_prefixes,
        sys_module=sys_module,
    )
    if is_frozen_runtime and not bool(global_vars.get("_runtime_prepared", False)):
        prepare_frozen_runtime(
            app_dir,
            logger_name=logger_name,
            include_resources=include_resources,
            copy_all_data=copy_all_data,
            create_common_dirs=create_common_dirs,
            sys_module=sys_module,
        )
    global_vars["_runtime_prepared"] = True
    return app_dir


def find_bundled_dir(app_dir: str, folder_name: str) -> Path | None:
    """Find bundled folders in common packaging layouts."""
    exe_path = resolve_executable_path()
    app_path = Path(app_dir)
    if folder_name == "data":
        external_data = exe_path.parent / folder_name
        return external_data if external_data.is_dir() else None
    candidates = [
        app_path / folder_name,
        app_path / "_internal" / folder_name,
        exe_path.parent.parent / "Resources" / folder_name,
    ]
    candidates.append(exe_path.parent.parent / folder_name)
    for candidate in candidates:
        if candidate.is_dir():
            return candidate
    return None


def _seed_marker_value(source_dir: Path) -> str:
    parts = [str(source_dir.resolve()), str(source_dir.stat().st_mtime_ns)]
    for child in sorted(source_dir.iterdir(), key=lambda path: path.name):
        child_stat = child.stat()
        parts.append(
            f"{child.name}:{int(child.is_dir())}:"
            f"{child_stat.st_mtime_ns}:{child_stat.st_size}"
        )
    return "\n".join(parts)


def _seed_marker_matches(marker_path: Path, marker_value: str) -> bool:
    try:
        return marker_path.read_text(encoding="utf-8") == marker_value
    except FileNotFoundError:
        return False


def _target_has_top_level_entries(source_dir: Path, target_dir: Path) -> bool:
    for source in source_dir.iterdir():
        target = target_dir / source.name
        if not target.exists():
            return False
    return True


def copy_missing_tree(
    source_dir: Path,
    target_dir: Path,
    *,
    marker_name: str | None = None,
) -> None:
    marker_path = target_dir / marker_name if marker_name else None
    marker_value = _seed_marker_value(source_dir) if marker_path is not None else ""
    if (
        marker_path is not None
        and _seed_marker_matches(marker_path, marker_value)
        and _target_has_top_level_entries(source_dir, target_dir)
    ):
        return

    for source in source_dir.rglob("*"):
        relative = source.relative_to(source_dir)
        target = target_dir / relative
        if source.is_dir():
            target.mkdir(parents=True, exist_ok=True)
        elif source.is_file() and not target.exists():
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
    if marker_path is not None:
        marker_path.write_text(marker_value, encoding="utf-8")


def warn_runtime_seed_failure(logger_name: str, message: str, exc: Exception) -> None:
    try:
        from utils.robust_logging import get_robust_logger

        logger = get_robust_logger().get_logger("ssa.launcher", logger_name)
        logger.warning("%s: %s", message, exc)
    except Exception:
        sys.stderr.write(f"AVISO: {message}: {exc}\n")


def log_launcher_failure(
    logger_name: str,
    message: str,
    exc: Exception,
    *,
    include_trace: bool = False,
) -> None:
    try:
        from utils.robust_logging import get_robust_logger

        logger = get_robust_logger().get_logger("ssa.launcher", logger_name)
        logger.error("%s: %s", message, exc, exc_info=include_trace)
    except Exception as log_exc:
        sys.stderr.write(f"AVISO: Falha ao registrar erro no logger: {log_exc}\n")


def seed_runtime_config(
    runtime_dir: Path,
    bundled_config: Path | None,
    *,
    logger_name: str,
) -> Path:
    """Seed runtime config with bundled defaults without overwriting user files."""
    return _seed_runtime_tree_folder(
        runtime_dir,
        bundled_config,
        folder_name="config",
        logger_name=logger_name,
        failure_message="Falha ao preparar config de runtime",
    )


def seed_runtime_data(
    runtime_dir: Path,
    bundled_data: Path | None,
    *,
    logger_name: str,
    copy_all: bool,
) -> Path:
    """Seed runtime data from the bundle without overwriting user files."""
    runtime_data = runtime_dir / "data"
    runtime_data.mkdir(parents=True, exist_ok=True)
    if bundled_data is None:
        return runtime_data
    if bundled_data.resolve() == runtime_data.resolve():
        return runtime_data

    try:
        if copy_all:
            copy_missing_tree(
                bundled_data,
                runtime_data,
                marker_name=".ssa_seed_data",
            )
        else:
            source_db = bundled_data / "ssas.db"
            target_db = runtime_data / "ssas.db"
            if source_db.is_file() and not target_db.exists():
                shutil.copy2(source_db, target_db)
    except Exception as exc:
        warn_runtime_seed_failure(
            logger_name,
            "Falha ao preparar data de runtime",
            exc,
        )
    return runtime_data


def seed_runtime_resources(
    runtime_dir: Path,
    bundled_resources: Path | None,
    *,
    logger_name: str,
) -> Path:
    """Seed runtime resources without overwriting user files."""
    return _seed_runtime_tree_folder(
        runtime_dir,
        bundled_resources,
        folder_name="resources",
        logger_name=logger_name,
        failure_message="Falha ao preparar resources de runtime",
    )


def _seed_runtime_tree_folder(
    runtime_dir: Path,
    bundled_dir: Path | None,
    *,
    logger_name: str,
    folder_name: str,
    failure_message: str,
) -> Path:
    runtime_target = runtime_dir / folder_name
    runtime_target.mkdir(parents=True, exist_ok=True)
    if bundled_dir is None:
        return runtime_target

    try:
        for source in bundled_dir.iterdir():
            target = runtime_target / source.name
            if source.is_dir():
                target.mkdir(parents=True, exist_ok=True)
                copy_missing_tree(
                    source,
                    target,
                    marker_name=f".ssa_seed_{source.name}",
                )
            elif source.is_file() and not target.exists():
                shutil.copy2(source, target)
    except Exception as exc:
        warn_runtime_seed_failure(logger_name, failure_message, exc)
    return runtime_target


def _trusted_runtime_roots() -> list[Path]:
    roots = [
        Path.home(),
        Path(tempfile.gettempdir()),
        resolve_executable_path().parent,
    ]
    for env_key in ("APPDATA", "LOCALAPPDATA", "XDG_DATA_HOME"):
        raw_root = os.environ.get(env_key)
        if raw_root:
            roots.append(Path(raw_root).expanduser())
    return roots


def _resolve_writable_runtime_dir() -> Path:
    from utils.path_safety import ensure_path_is_allowed

    explicit_root = os.environ.get("SSA_RUNTIME_ROOT")
    if explicit_root:
        runtime_dir = Path(explicit_root).expanduser()
    elif RUNTIME_HOME_ARG in sys.argv:
        runtime_dir = resolve_runtime_home()
    else:
        runtime_dir = resolve_executable_path().parent
    safe_runtime_dir = ensure_path_is_allowed(
        runtime_dir,
        purpose="runtime root",
        expect_directory=True,
        extra_allowed_roots=_trusted_runtime_roots(),
    )
    safe_runtime_dir.mkdir(parents=True, exist_ok=True)
    return safe_runtime_dir


def _runtime_common_paths(runtime_dir: Path) -> dict[str, Path]:
    return {
        "logs": runtime_dir / "logs",
        "docs_in": runtime_dir / "docs_entrada",
        "docs_out": runtime_dir / "docs_saida",
        "reports": runtime_dir / "reports",
        "exportacao": runtime_dir / "exportacao",
    }


def _create_common_runtime_dirs(runtime_dir: Path) -> None:
    paths = _runtime_common_paths(runtime_dir)
    runtime_data_backups = runtime_dir / "data" / "historico_backups"
    for folder in (
        paths["logs"],
        paths["docs_in"],
        paths["docs_out"],
        paths["reports"],
        paths["exportacao"],
        runtime_data_backups,
    ):
        folder.mkdir(parents=True, exist_ok=True)


def _runtime_allowed_roots(
    runtime_dir: Path,
    runtime_config: Path,
    runtime_data: Path,
) -> list[str]:
    paths = _runtime_common_paths(runtime_dir)
    allowed_roots = [
        str(runtime_dir),
        str(runtime_config),
        str(runtime_data),
        str(paths["docs_in"]),
        str(paths["docs_out"]),
        str(paths["reports"]),
        str(paths["exportacao"]),
        str(paths["logs"]),
    ]
    existing_extra = os.environ.get("SSA_EXTRA_ALLOWED_PATHS", "")
    for candidate in existing_extra.split(os.pathsep):
        candidate = candidate.strip()
        if candidate:
            allowed_roots.append(candidate)
    return allowed_roots


def _dedup_paths(paths: list[str]) -> list[str]:
    dedup_allowed: list[str] = []
    for candidate in paths:
        if candidate not in dedup_allowed:
            dedup_allowed.append(candidate)
    return dedup_allowed


def _apply_runtime_environment(
    app_dir: str,
    runtime_dir: Path,
    runtime_config: Path,
    runtime_data: Path,
) -> None:
    os.environ["SSA_BUNDLED_ROOT"] = app_dir
    os.environ["SSA_RUNTIME_ROOT"] = str(runtime_dir)
    os.environ["SSA_CONFIG_DIR"] = str(runtime_config)
    os.environ["SSA_DB_PATH"] = str(runtime_data / "ssas.db")
    allowed_roots = _runtime_allowed_roots(runtime_dir, runtime_config, runtime_data)
    os.environ["SSA_EXTRA_ALLOWED_PATHS"] = os.pathsep.join(_dedup_paths(allowed_roots))


def prepare_frozen_runtime(
    app_dir: str,
    *,
    logger_name: str,
    include_resources: bool,
    copy_all_data: bool,
    create_common_dirs: bool,
    sys_module: ModuleType = sys,
) -> Path:
    """Prepare writable runtime directories and environment for frozen apps."""
    if app_dir not in sys_module.path:
        sys_module.path.insert(0, app_dir)
    runtime_dir = _resolve_writable_runtime_dir()
    if create_common_dirs:
        _create_common_runtime_dirs(runtime_dir)

    bundled_config = find_bundled_dir(app_dir, "config")
    bundled_data = find_bundled_dir(app_dir, "data")
    runtime_config = seed_runtime_config(
        runtime_dir,
        bundled_config,
        logger_name=logger_name,
    )
    runtime_data = seed_runtime_data(
        runtime_dir,
        bundled_data,
        logger_name=logger_name,
        copy_all=copy_all_data,
    )
    if include_resources:
        bundled_resources = find_bundled_dir(app_dir, "resources")
        seed_runtime_resources(
            runtime_dir,
            bundled_resources,
            logger_name=logger_name,
        )

    _apply_runtime_environment(app_dir, runtime_dir, runtime_config, runtime_data)
    return runtime_dir
