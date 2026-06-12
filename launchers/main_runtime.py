from __future__ import annotations

import builtins
import json
import os
import shutil
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path
from types import ModuleType
from typing import Any, cast


APP_RUNTIME_NAME = "SSA_Consulta_Rapida"
_original_import = builtins.__import__
_pandas_patch_installed = False
_runtime_environment_initialized = False
_runtime_root = ""


def patch_pyoxidizer_pandas() -> None:
    """Patch pandas delvewheel imports when running under PyOxidizer."""
    global _pandas_patch_installed
    if _pandas_patch_installed or not getattr(sys, "oxidized", False):
        return

    def _patched_import(
        name: str,
        globals: Mapping[str, object] | None = None,
        locals: Mapping[str, object] | None = None,
        fromlist: Sequence[str] | None = (),
        level: int = 0,
    ) -> ModuleType:
        module = _original_import(name, globals, locals, fromlist, level)
        module_name = getattr(module, "__name__", name)
        if module_name == "pandas" or str(module_name).startswith("pandas."):
            if not hasattr(module, "__file__") or module.__file__ is None:
                module.__file__ = os.path.join(
                    os.path.dirname(sys.executable),
                    f"{name.replace('.', os.sep)}.py",
                )
        return module

    builtins.__import__ = cast(Any, _patched_import)
    _pandas_patch_installed = True


def _get_project_root() -> str:
    """Return trusted code/bundle root for source and frozen builds."""
    if getattr(sys, "oxidized", False):
        return os.path.dirname(sys.executable)
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return os.path.abspath(os.fspath(getattr(sys, "_MEIPASS")))
    if "__compiled__" in globals():
        return os.path.dirname(sys.executable)
    try:
        if __file__ is not None:
            return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        return os.getcwd()
    except (NameError, TypeError):
        return os.getcwd()


def _resolve_runtime_home() -> Path:
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


def _runtime_seed_marker_value(src_dir: Path) -> str:
    source_stat = src_dir.stat()
    return f"{src_dir.resolve()}\n{source_stat.st_mtime_ns}\n{source_stat.st_size}"


def _runtime_seed_marker_matches(marker_path: Path, marker_value: str) -> bool:
    try:
        return marker_path.read_text(encoding="utf-8") == marker_value
    except FileNotFoundError:
        return False


def _target_has_top_level_entries(source_dir: Path, target_dir: Path) -> bool:
    for source in source_dir.iterdir():
        if not (target_dir / source.name).exists():
            return False
    return True


def _seed_manifest_path(target_dir: Path, folder_name: str) -> Path:
    return target_dir / f".ssa_seed_manifest_{folder_name}.json"


def _file_fingerprint(path: Path) -> str:
    stat_result = path.stat()
    return f"{stat_result.st_mtime_ns}:{stat_result.st_size}"


def _load_seed_manifest(manifest_path: Path) -> dict[str, str]:
    try:
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return {}
    if not isinstance(data, dict):
        return {}
    return {str(key): str(value) for key, value in data.items()}


def _write_seed_manifest(manifest_path: Path, manifest: dict[str, str]) -> None:
    manifest_path.write_text(
        json.dumps(manifest, sort_keys=True, indent=2), encoding="utf-8"
    )


def _copy_seed_file(
    source: Path,
    target: Path,
    relative_name: str,
    folder_name: str,
    previous_manifest: dict[str, str],
    next_manifest: dict[str, str],
    force_existing_without_manifest: bool,
) -> None:
    source_fingerprint = _file_fingerprint(source)
    if target.exists():
        if target.is_dir():
            raise RuntimeError(
                f"Conflito no runtime {folder_name}: {target} deveria ser arquivo"
            )
        previous_fingerprint = previous_manifest.get(relative_name)
        target_fingerprint = _file_fingerprint(target)
        should_replace = (
            force_existing_without_manifest
            or (
                previous_fingerprint is not None
                and target_fingerprint == previous_fingerprint
            )
        )
        if should_replace:
            shutil.copy2(source, target)
    else:
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
    next_manifest[relative_name] = source_fingerprint


def _copy_seed_tree(
    source_dir: Path,
    target_dir: Path,
    folder_name: str,
    previous_manifest: dict[str, str],
    force_existing_without_manifest: bool,
) -> dict[str, str]:
    next_manifest: dict[str, str] = {}
    for source in source_dir.rglob("*"):
        relative = source.relative_to(source_dir)
        target = target_dir / relative
        relative_name = relative.as_posix()
        if source.is_dir():
            if target.exists() and not target.is_dir():
                raise RuntimeError(
                    f"Conflito no runtime {folder_name}: {target} deveria ser diretorio"
                )
            target.mkdir(parents=True, exist_ok=True)
        elif source.is_file():
            _copy_seed_file(
                source,
                target,
                relative_name,
                folder_name,
                previous_manifest,
                next_manifest,
                force_existing_without_manifest,
            )
    return next_manifest


def _seed_runtime_folder(
    runtime_dir: Path, src_dir: Path | None, folder_name: str
) -> Path:
    target_dir = runtime_dir / folder_name
    target_dir.mkdir(parents=True, exist_ok=True)
    if src_dir is None or not src_dir.is_dir():
        return target_dir
    marker_path = target_dir / f".ssa_seed_{folder_name}"
    marker_value = _runtime_seed_marker_value(src_dir)
    if _runtime_seed_marker_matches(
        marker_path, marker_value
    ) and _target_has_top_level_entries(src_dir, target_dir):
        return target_dir
    try:
        manifest_path = _seed_manifest_path(target_dir, folder_name)
        previous_manifest = _load_seed_manifest(manifest_path)
        force_existing = marker_path.exists() and not previous_manifest
        next_manifest = _copy_seed_tree(
            src_dir,
            target_dir,
            folder_name,
            previous_manifest,
            force_existing,
        )
        _write_seed_manifest(manifest_path, next_manifest)
        marker_path.write_text(marker_value, encoding="utf-8")
    except (OSError, shutil.Error, RuntimeError) as exc:
        message = f"Falha ao preparar runtime {folder_name}: {exc}"
        sys.stderr.write(f"ERRO: {message}\n")
        raise RuntimeError(message) from exc
    return target_dir


def _asset_candidates(source_root: Path, exe_root: Path, folder_name: str) -> tuple[Path, ...]:
    return (
        source_root / folder_name,
        exe_root / folder_name,
        exe_root / "_internal" / folder_name,
        exe_root.parent / "Resources" / folder_name,
    )


def _first_existing_dir(candidates: tuple[Path, ...]) -> Path | None:
    return next((path for path in candidates if path.is_dir()), None)


def _ensure_runtime_directories(runtime_dir: Path) -> dict[str, Path]:
    folders = {
        "docs_in": runtime_dir / "docs_entrada",
        "docs_out": runtime_dir / "docs_saida",
        "reports": runtime_dir / "reports",
        "exportacao": runtime_dir / "exportacao",
        "logs": runtime_dir / "logs",
        "data_backups": runtime_dir / "data" / "historico_backups",
    }
    for folder in folders.values():
        folder.mkdir(parents=True, exist_ok=True)
    return folders


def _dedupe_paths(paths: list[str]) -> list[str]:
    deduped: list[str] = []
    for path in paths:
        if path not in deduped:
            deduped.append(path)
    return deduped


def _apply_runtime_environment(
    runtime_dir: Path,
    runtime_config: Path,
    runtime_data: Path,
    runtime_dirs: dict[str, Path],
    bundled_root: str,
) -> None:
    os.environ["SSA_BUNDLED_ROOT"] = bundled_root
    os.environ["SSA_RUNTIME_ROOT"] = str(runtime_dir)
    os.environ["SSA_CONFIG_DIR"] = str(runtime_config)
    os.environ["SSA_DB_PATH"] = str(runtime_data / "ssas.db")
    allowed_roots = [
        str(runtime_dir),
        str(runtime_config),
        str(runtime_data),
        str(runtime_dirs["docs_in"]),
        str(runtime_dirs["docs_out"]),
        str(runtime_dirs["reports"]),
        str(runtime_dirs["exportacao"]),
        str(runtime_dirs["logs"]),
    ]
    existing_extra = os.environ.get("SSA_EXTRA_ALLOWED_PATHS", "")
    for candidate in existing_extra.split(os.pathsep):
        candidate = candidate.strip()
        if candidate:
            allowed_roots.append(candidate)
    os.environ["SSA_EXTRA_ALLOWED_PATHS"] = os.pathsep.join(
        _dedupe_paths(allowed_roots)
    )


def _enter_runtime_dir(runtime_dir: Path) -> None:
    try:
        os.chdir(runtime_dir)
    except OSError as exc:
        message = f"Falha ao entrar no runtime frozen {runtime_dir}: {exc}"
        sys.stderr.write(f"ERRO: {message}\n")
        raise RuntimeError(message) from exc


def _prepare_frozen_runtime(project_root_path: str) -> str:
    is_frozen_mode = bool(
        getattr(sys, "frozen", False)
        or getattr(sys, "oxidized", False)
        or "__compiled__" in globals()
    )
    if not is_frozen_mode:
        return project_root_path

    runtime_dir = _resolve_runtime_home()
    source_root = Path(project_root_path)
    exe_root = Path(sys.executable).resolve().parent

    bundled_config = _first_existing_dir(_asset_candidates(source_root, exe_root, "config"))
    bundled_data = _first_existing_dir(_asset_candidates(source_root, exe_root, "data"))
    bundled_resources = _first_existing_dir(
        _asset_candidates(source_root, exe_root, "resources")
    )
    runtime_config = _seed_runtime_folder(runtime_dir, bundled_config, "config")
    runtime_data = _seed_runtime_folder(runtime_dir, bundled_data, "data")
    _seed_runtime_folder(runtime_dir, bundled_resources, "resources")
    runtime_dirs = _ensure_runtime_directories(runtime_dir)

    bundled_root = next(
        (
            str(p.parent)
            for p in (bundled_resources, bundled_config, bundled_data)
            if p is not None
        ),
        str(exe_root),
    )
    _apply_runtime_environment(
        runtime_dir, runtime_config, runtime_data, runtime_dirs, bundled_root
    )
    _enter_runtime_dir(runtime_dir)
    return str(runtime_dir)


def ensure_runtime_environment(project_root_path: str) -> str:
    """Prepare writable runtime once while keeping project_root trusted."""
    global _runtime_environment_initialized, _runtime_root
    if not _runtime_environment_initialized:
        _runtime_root = _prepare_frozen_runtime(project_root_path)
        _runtime_environment_initialized = True
    return _runtime_root
