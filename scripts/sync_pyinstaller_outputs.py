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


def _sync_platform(repo_root: Path, platform: str, verbose: bool) -> bool:
    source_dir = repo_root / "launchers" / "dist" / platform
    target_dir = repo_root / "builds" / "pyinstaller" / platform

    if not source_dir.exists():
        if verbose:
            print(f"SKIP source ausente: {source_dir}")
        return False

    target_dir.parent.mkdir(parents=True, exist_ok=True)
    if target_dir.exists():
        shutil.rmtree(target_dir)
    shutil.copytree(source_dir, target_dir)

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
