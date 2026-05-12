from __future__ import annotations

from pathlib import Path

from launchers.main_runtime import _get_project_root


PROJECT_ROOT = Path(_get_project_root())


def resolve_project_path(relative_path: str) -> Path:
    return PROJECT_ROOT / relative_path


def require_project_path(relative_path: str) -> Path:
    path = resolve_project_path(relative_path)
    if not path.exists():
        raise FileNotFoundError(f"Required project path not found: {relative_path}")
    return path
