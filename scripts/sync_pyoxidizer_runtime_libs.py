"""
Sync native ".libs" runtime folders for PyOxidizer outputs.

This script must run in an environment where numpy/pandas are installed.
Example:
  uv run --python 3.10 --with numpy --with pandas python scripts/sync_pyoxidizer_runtime_libs.py --target C:\\repo\\builds\\pyoxidizer\\windows_amd64\\lib
"""

from __future__ import annotations

import argparse
import shutil
import sys
import sysconfig
from pathlib import Path

DEFAULT_LIB_DIRS = ("numpy.libs", "pandas.libs")


def _resolve_site_packages() -> Path:
    paths = sysconfig.get_paths()
    candidates = []
    for key in ("platlib", "purelib"):
        value = paths.get(key)
        if value:
            candidates.append(Path(value))

    seen = set()
    ordered = []
    for candidate in candidates:
        key = str(candidate.resolve()) if candidate.exists() else str(candidate)
        if key in seen:
            continue
        seen.add(key)
        ordered.append(candidate)

    for candidate in ordered:
        if candidate.exists():
            return candidate

    raise FileNotFoundError("site-packages nao encontrado para o interpreter atual")


def _copy_lib_dir(site_packages: Path, lib_dir_name: str, target_lib_dir: Path) -> bool:
    source = site_packages / lib_dir_name
    if not source.exists():
        print(f"[skip] {lib_dir_name} nao encontrado em {site_packages}")
        return False

    destination = target_lib_dir / lib_dir_name
    shutil.copytree(source, destination, dirs_exist_ok=True)
    print(f"[ok] copiado {lib_dir_name} -> {destination}")
    return True


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Sincroniza pastas .libs para runtime PyOxidizer."
    )
    parser.add_argument(
        "--target",
        required=True,
        help="Diretorio lib do artefato PyOxidizer (ex.: builds/pyoxidizer/windows_amd64/lib)",
    )
    parser.add_argument(
        "--lib-dir",
        action="append",
        default=[],
        help="Nome da pasta .libs para copiar (repetivel). Padrao: numpy.libs, pandas.libs",
    )
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    target_lib_dir = Path(args.target).resolve()
    if not target_lib_dir.exists():
        print(f"[erro] target nao existe: {target_lib_dir}")
        return 1

    site_packages = _resolve_site_packages()
    print(f"[info] site-packages: {site_packages}")
    print(f"[info] target lib: {target_lib_dir}")

    lib_dirs = tuple(args.lib_dir) if args.lib_dir else DEFAULT_LIB_DIRS
    copied_any = False
    for lib_dir_name in lib_dirs:
        copied_any = (
            _copy_lib_dir(site_packages, lib_dir_name, target_lib_dir) or copied_any
        )

    if not copied_any:
        print("[erro] nenhuma pasta .libs foi copiada")
        return 1

    print("[ok] sync de runtime libs concluido")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
