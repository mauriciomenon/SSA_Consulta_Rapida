from __future__ import annotations

import importlib.util
from pathlib import Path


def _load_module(module_name: str, path: Path):
    spec = importlib.util.spec_from_file_location(module_name, path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_resolve_target_build_dirs_pyoxidizer_prefers_legacy_root_when_present(
    tmp_path: Path,
) -> None:
    root = Path(__file__).resolve().parents[1]
    module = _load_module(
        "copy_data_to_builds", root / "scripts" / "copy_data_to_builds.py"
    )
    legacy_dir = tmp_path / "builds" / "pyoxidizer"
    legacy_dir.mkdir(parents=True)

    resolved = module.resolve_target_build_dirs(tmp_path, "pyoxidizer")

    assert resolved == [legacy_dir]


def test_resolve_target_build_dirs_pyoxidizer_uses_platform_fallbacks_without_root(
    tmp_path: Path,
) -> None:
    root = Path(__file__).resolve().parents[1]
    module = _load_module(
        "copy_data_to_builds", root / "scripts" / "copy_data_to_builds.py"
    )

    resolved = module.resolve_target_build_dirs(tmp_path, "pyoxidizer")

    expected = [tmp_path / rel for rel in module.PYOXIDIZER_PLATFORM_DIRS]
    assert resolved == expected
    assert tmp_path / "builds" / "pyoxidizer" not in resolved
