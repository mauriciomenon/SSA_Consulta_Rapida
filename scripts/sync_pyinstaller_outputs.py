#!/usr/bin/env python3
"""
Sync canonical PyInstaller outputs to equivalent structured build folders.

Canonical source:
    launchers/dist/<platform>/

Equivalent structured target:
    builds/pyinstaller/<platform>/

Usage:
    uv run --python 3.13 scripts/sync_pyinstaller_outputs.py
    uv run --python 3.13 scripts/sync_pyinstaller_outputs.py --platform windows_amd64
"""

from __future__ import annotations

import argparse
import importlib
import shutil
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

MultiPlatformBuilder = importlib.import_module(
    "launchers.build_multiplatform"
).MultiPlatformBuilder
PLATFORMS = tuple(sorted(MultiPlatformBuilder.PLATFORMS))


def _remove_path(path: Path) -> None:
    if path.is_dir() and not path.is_symlink():
        shutil.rmtree(path)
        return
    path.unlink()


def _exists_or_symlink(path: Path) -> bool:
    return path.exists() or path.is_symlink()


def _file_is_current(source_path: Path, target_path: Path) -> bool:
    if source_path.is_symlink() or target_path.is_symlink():
        if not (source_path.is_symlink() and target_path.is_symlink()):
            return False
        try:
            return source_path.readlink() == target_path.readlink()
        except OSError:
            return False

    if not target_path.is_file():
        return False

    try:
        source_stat = source_path.stat()
        target_stat = target_path.stat()
    except OSError:
        return False
    return (
        source_stat.st_size == target_stat.st_size
        and source_stat.st_mtime_ns == target_stat.st_mtime_ns
    )


def _sync_directory_symlink(source_path: Path, target_path: Path, allowed_root: Path) -> None:
    resolved_source = source_path.resolve(strict=True)
    try:
        resolved_source.relative_to(allowed_root)
    except ValueError:
        return
    if _exists_or_symlink(target_path) and not target_path.is_dir():
        _remove_path(target_path)
    _sync_tree_incremental(resolved_source, target_path, allowed_root=allowed_root)


def _sync_directory(source_path: Path, target_path: Path) -> None:
    if _exists_or_symlink(target_path) and not target_path.is_dir():
        _remove_path(target_path)
    target_path.mkdir(parents=True, exist_ok=True)


def _sync_symlink(source_path: Path, target_path: Path) -> None:
    if not source_path.exists():
        return
    target_path.parent.mkdir(parents=True, exist_ok=True)
    if not _file_is_current(source_path, target_path):
        if _exists_or_symlink(target_path):
            _remove_path(target_path)
        target_path.symlink_to(source_path.readlink())


def _sync_regular_file(source_path: Path, target_path: Path) -> None:
    target_path.parent.mkdir(parents=True, exist_ok=True)
    if _exists_or_symlink(target_path) and not target_path.is_file():
        _remove_path(target_path)
    if not _file_is_current(source_path, target_path):
        shutil.copy2(source_path, target_path)


def _remove_stale_entries(source_dir: Path, target_dir: Path) -> None:
    for target_path in sorted(
        target_dir.rglob("*"),
        key=lambda path: len(path.parts),
        reverse=True,
    ):
        if not _exists_or_symlink(target_path):
            continue
        source_path = source_dir / target_path.relative_to(target_dir)
        if _exists_or_symlink(source_path):
            continue
        try:
            _remove_path(target_path)
        except OSError as exc:
            raise RuntimeError(
                f"Falha ao remover artefato obsoleto: {target_path}"
            ) from exc


def _sync_tree_incremental(
    source_dir: Path, target_dir: Path, *, allowed_root: Path
) -> None:
    target_dir.mkdir(parents=True, exist_ok=True)

    for source_path in source_dir.rglob("*"):
        target_path = target_dir / source_path.relative_to(source_dir)
        if source_path.is_symlink() and source_path.is_dir():
            _sync_directory_symlink(source_path, target_path, allowed_root)
            continue

        if source_path.is_dir():
            _sync_directory(source_path, target_path)
            continue

        if source_path.is_symlink():
            _sync_symlink(source_path, target_path)
            continue

        _sync_regular_file(source_path, target_path)

    _remove_stale_entries(source_dir, target_dir)


def _sync_platform(repo_root: Path, platform: str, verbose: bool) -> bool:
    source_dir = repo_root / "launchers" / "dist" / platform
    target_dir = repo_root / "builds" / "pyinstaller" / platform

    if not source_dir.exists():
        if verbose:
            print(f"SKIP source ausente: {source_dir}")
        return False

    target_dir.parent.mkdir(parents=True, exist_ok=True)
    _sync_tree_incremental(source_dir, target_dir, allowed_root=repo_root.resolve())

    if verbose:
        print(f"OK synced: {source_dir} -> {target_dir}")
    return True


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Sync launchers/dist/<platform> to builds/pyinstaller/<platform>"
    )
    parser.add_argument(
        "--platform",
        choices=PLATFORMS,
        help="Sync only one platform",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Reduce output",
    )
    args = parser.parse_args()

    verbose = not args.quiet
    repo_root = PROJECT_ROOT
    platforms = [args.platform] if args.platform else list(PLATFORMS)
    any_synced = False
    for platform in platforms:
        any_synced = _sync_platform(repo_root, platform, verbose) or any_synced

    if not any_synced and verbose:
        print("WARN nenhuma plataforma sincronizada")

    return 0 if any_synced else 1


if __name__ == "__main__":
    raise SystemExit(main())
