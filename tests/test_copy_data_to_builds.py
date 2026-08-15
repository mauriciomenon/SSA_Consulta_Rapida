from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest


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


def test_resolve_target_build_dirs_pyoxidizer_prefers_specific_targets_over_legacy_root(
    tmp_path: Path,
) -> None:
    root = Path(__file__).resolve().parents[1]
    module = _load_module(
        "copy_data_to_builds_pyoxidizer_specifics",
        root / "scripts" / "copy_data_to_builds.py",
    )
    legacy_dir = tmp_path / "builds" / "pyoxidizer"
    legacy_dir.mkdir(parents=True)
    specific_dir = tmp_path / module.PYOXIDIZER_PLATFORM_DIRS[0]
    specific_dir.mkdir(parents=True)

    resolved = module.resolve_target_build_dirs(tmp_path, "pyoxidizer")

    assert resolved == [specific_dir]


def test_copy_data_to_build_reuses_staged_config_for_multiple_runtime_dirs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = Path(__file__).resolve().parents[1]
    module = _load_module(
        "copy_data_to_builds", root / "scripts" / "copy_data_to_builds.py"
    )
    build_dir = tmp_path / "build"
    runtime_dir_one = build_dir / "SSA_Runtime_A.dist"
    runtime_dir_two = build_dir / "SSA_Runtime_B.dist"
    runtime_dir_one.mkdir(parents=True)
    runtime_dir_two.mkdir(parents=True)

    copytree_calls: list[tuple[Path, Path, bool]] = []

    def fake_copytree(src, dst, dirs_exist_ok=False):
        src_path = Path(src)
        dst_path = Path(dst)
        copytree_calls.append((src_path, dst_path, dirs_exist_ok))
        dst_path.mkdir(parents=True, exist_ok=True)
        return str(dst_path)

    monkeypatch.setattr(module.shutil, "copytree", fake_copytree)

    success = module.copy_data_to_build(
        build_dir,
        verbose=False,
        db_path=tmp_path / "missing.db",
        docs_dir=tmp_path / "missing_docs",
    )

    assert success is True
    assert len(copytree_calls) == 3
    assert sum(1 for src, _, _ in copytree_calls if src == root / "config") == 1
    assert copytree_calls[1][0] == copytree_calls[0][1]
    assert copytree_calls[2][0] == copytree_calls[0][1]
    assert {copytree_calls[1][1], copytree_calls[2][1]} == {
        runtime_dir_one / "config",
        runtime_dir_two / "config",
    }


def test_copy_data_to_build_reports_cached_excel_size_after_target_removal(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    root = Path(__file__).resolve().parents[1]
    module = _load_module(
        "copy_data_to_builds_sizes", root / "scripts" / "copy_data_to_builds.py"
    )
    build_dir = tmp_path / "build"
    build_dir.mkdir(parents=True)
    docs_dir = tmp_path / "docs_entrada"
    docs_dir.mkdir()
    excel_path = docs_dir / "sample.xlsx"
    excel_path.write_bytes(b"1234567890")

    original_copy2 = module.shutil.copy2

    def fake_copy2(src, dst):
        result = original_copy2(src, dst)
        Path(dst).unlink()
        return result

    monkeypatch.setattr(module.shutil, "copy2", fake_copy2)

    success = module.copy_data_to_build(
        build_dir,
        verbose=True,
        db_path=tmp_path / "missing.db",
        docs_dir=docs_dir,
        max_excel_files=1,
    )

    captured = capsys.readouterr()
    assert success is True
    assert (
        "WARN  Revise se DB e planilhas contem dados sensiveis antes de distribuir o build"
        in captured.out
    )
    assert "sample.xlsx (0 KB)" in captured.out


def test_resolve_runtime_dirs_prefers_specific_runtime_dirs(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[1]
    module = _load_module(
        "copy_data_to_builds_runtime_dirs", root / "scripts" / "copy_data_to_builds.py"
    )
    build_dir = tmp_path / "build"
    build_dir.mkdir()
    runtime_dir = build_dir / "SSA_Runtime.dist"
    runtime_dir.mkdir()

    resolved = module._resolve_runtime_dirs(build_dir)

    assert resolved == [runtime_dir]


def test_resolve_runtime_dirs_returns_empty_on_scan_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = Path(__file__).resolve().parents[1]
    module = _load_module(
        "copy_data_to_builds_runtime_dirs_error",
        root / "scripts" / "copy_data_to_builds.py",
    )
    build_dir = tmp_path / "build"
    build_dir.mkdir()
    original_iterdir = module.Path.iterdir

    def fake_iterdir(path_obj):
        if path_obj == build_dir:
            raise OSError("scan failed")
        return original_iterdir(path_obj)

    monkeypatch.setattr(module.Path, "iterdir", fake_iterdir)

    resolved = module._resolve_runtime_dirs(build_dir)

    assert resolved == []
