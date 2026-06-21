from __future__ import annotations

import importlib.util
import shutil
from pathlib import Path

import pytest


def _load_module(module_name: str, path: Path):
    spec = importlib.util.spec_from_file_location(module_name, path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_sync_platform_updates_incrementally_and_removes_stale(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = Path(__file__).resolve().parents[1]
    module = _load_module(
        "sync_pyinstaller_outputs", root / "scripts" / "sync_pyinstaller_outputs.py"
    )
    source_dir = tmp_path / "launchers" / "dist" / "windows_amd64"
    target_dir = tmp_path / "builds" / "pyinstaller" / "windows_amd64"
    source_dir.mkdir(parents=True)
    target_dir.mkdir(parents=True)

    unchanged_source = source_dir / "unchanged.txt"
    unchanged_source.write_text("same", encoding="utf-8")
    shutil.copy2(unchanged_source, target_dir / "unchanged.txt")

    changed_source = source_dir / "changed.txt"
    changed_source.write_text("new", encoding="utf-8")
    (target_dir / "changed.txt").write_text("old", encoding="utf-8")

    new_source = source_dir / "nested" / "new.txt"
    new_source.parent.mkdir()
    new_source.write_text("fresh", encoding="utf-8")

    (target_dir / "stale.txt").write_text("stale", encoding="utf-8")
    stale_dir = target_dir / "stale_dir"
    stale_dir.mkdir()
    (stale_dir / "old.txt").write_text("old", encoding="utf-8")

    original_copy2 = module.shutil.copy2
    copied: list[Path] = []

    def fake_copy2(src, dst):
        source_path = Path(src)
        copied.append(source_path.relative_to(source_dir))
        return original_copy2(src, dst)

    monkeypatch.setattr(module.shutil, "copy2", fake_copy2)

    assert module._sync_platform(tmp_path, "windows_amd64", verbose=False) is True

    assert set(copied) == {Path("changed.txt"), Path("nested/new.txt")}
    assert (target_dir / "unchanged.txt").read_text(encoding="utf-8") == "same"
    assert (target_dir / "changed.txt").read_text(encoding="utf-8") == "new"
    assert (target_dir / "nested" / "new.txt").read_text(encoding="utf-8") == "fresh"
    assert not (target_dir / "stale.txt").exists()
    assert not stale_dir.exists()


def test_sync_platform_missing_source_preserves_existing_target(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[1]
    module = _load_module(
        "sync_pyinstaller_outputs_missing",
        root / "scripts" / "sync_pyinstaller_outputs.py",
    )
    target_file = (
        tmp_path / "builds" / "pyinstaller" / "windows_amd64" / "existing.txt"
    )
    target_file.parent.mkdir(parents=True)
    target_file.write_text("keep", encoding="utf-8")

    assert module._sync_platform(tmp_path, "windows_amd64", verbose=False) is False

    assert target_file.read_text(encoding="utf-8") == "keep"


def test_sync_platform_copies_symlinked_directory_contents(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[1]
    module = _load_module(
        "sync_pyinstaller_outputs_symlink",
        root / "scripts" / "sync_pyinstaller_outputs.py",
    )
    source_dir = tmp_path / "launchers" / "dist" / "windows_amd64"
    target_dir = tmp_path / "builds" / "pyinstaller" / "windows_amd64"
    linked_real_dir = tmp_path / "linked_real"
    source_dir.mkdir(parents=True)
    linked_real_dir.mkdir()
    (linked_real_dir / "inside.txt").write_text("linked content", encoding="utf-8")

    symlink_path = source_dir / "linked_dir"
    try:
        symlink_path.symlink_to(linked_real_dir, target_is_directory=True)
    except OSError as exc:
        pytest.skip(f"symlink unavailable: {exc}")

    assert module._sync_platform(tmp_path, "windows_amd64", verbose=False) is True

    copied_file = target_dir / "linked_dir" / "inside.txt"
    assert copied_file.read_text(encoding="utf-8") == "linked content"
    assert copied_file.is_file()
