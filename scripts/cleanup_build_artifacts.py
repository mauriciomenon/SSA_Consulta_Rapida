"""
Cleanup helper for build artifacts.

Default scope is safe (`temp`): remove only transient/staging dirs.
Use `--scope full` to also remove generated build outputs.
"""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Cleanup de artefatos de build.")
    parser.add_argument(
        "--scope",
        choices=("temp", "full"),
        default="temp",
        help="Escopo da limpeza: temp (seguro) ou full (inclui outputs finais).",
    )
    parser.add_argument(
        "--repo-root",
        default=str(Path(__file__).resolve().parents[1]),
        help="Raiz do repositorio.",
    )
    parser.add_argument(
        "--yes",
        action="store_true",
        help="Nao pedir confirmacao em modo full.",
    )
    return parser.parse_args()


def _remove_path(path: Path) -> bool:
    if not path.exists():
        return False
    if path.is_dir():
        shutil.rmtree(path, ignore_errors=True)
    else:
        path.unlink(missing_ok=True)
    return True


def _collect_paths(repo_root: Path, scope: str) -> list[Path]:
    temp_paths = [
        repo_root / "build" / "pyoxidizer_stage_windows_amd64",
        repo_root / "build" / "x86_64-pc-windows-msvc",
        repo_root / "build" / "x86_64-unknown-linux-gnu",
        repo_root / "launchers" / "platforms" / "windows_amd64" / "temp",
        repo_root / "launchers" / "platforms" / "debian_amd64" / "temp",
        repo_root / "launchers" / "platforms" / "macos_arm64" / "temp",
    ]
    if scope == "temp":
        return temp_paths
    return temp_paths + [
        repo_root / "builds" / "pyinstaller",
        repo_root / "builds" / "nuitka",
        repo_root / "builds" / "pyoxidizer",
        repo_root / "launchers" / "dist",
        repo_root / "dist_packages",
    ]


def main() -> int:
    args = parse_args()
    repo_root = Path(args.repo_root).resolve()
    if not repo_root.exists():
        print(f"[erro] repo-root invalido: {repo_root}")
        return 1

    if args.scope == "full" and not args.yes:
        answer = (
            input("Confirmar cleanup FULL (remove builds/dist/dist_packages)? [s/N]: ")
            .strip()
            .lower()
        )
        if answer not in {"s", "sim", "y", "yes"}:
            print("[info] cleanup cancelado")
            return 0

    paths = _collect_paths(repo_root, args.scope)
    removed = 0
    for path in paths:
        if _remove_path(path):
            removed += 1
            print(f"[ok] removido: {path}")
        else:
            print(f"[skip] inexistente: {path}")

    print(f"[ok] cleanup concluido (scope={args.scope}, removidos={removed})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
