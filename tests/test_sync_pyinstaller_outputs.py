from __future__ import annotations

import importlib.util
import os
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
    changed_target = target_dir / "changed.txt"
    changed_target.write_text("old", encoding="utf-8")
    source_mtime_ns = changed_source.stat().st_mtime_ns
    os.utime(
        changed_target,
        ns=(source_mtime_ns - 1_000_000_000, source_mtime_ns - 1_000_000_000),
    )

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


def test_sync_platform_preserves_file_symlink_target(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[1]
    module = _load_module(
        "sync_pyinstaller_outputs_file_symlink",
        root / "scripts" / "sync_pyinstaller_outputs.py",
    )
    source_dir = tmp_path / "launchers" / "dist" / "windows_amd64"
    target_dir = tmp_path / "builds" / "pyinstaller" / "windows_amd64"
    source_dir.mkdir(parents=True)
    (source_dir / "real.txt").write_text("linked content", encoding="utf-8")
    source_link = source_dir / "linked.txt"
    try:
        source_link.symlink_to("real.txt")
    except OSError as exc:
        pytest.skip(f"symlink unavailable: {exc}")

    assert module._sync_platform(tmp_path, "windows_amd64", verbose=False) is True

    target_link = target_dir / "linked.txt"
    assert target_link.is_symlink()
    assert target_link.readlink() == Path("real.txt")
    assert target_link.read_text(encoding="utf-8") == "linked content"


def test_sync_platform_removes_file_symlink_outside_repo_root(
    tmp_path: Path, tmp_path_factory: pytest.TempPathFactory
) -> None:
    root = Path(__file__).resolve().parents[1]
    module = _load_module(
        "sync_pyinstaller_outputs_file_symlink_outside",
        root / "scripts" / "sync_pyinstaller_outputs.py",
    )
    source_dir = tmp_path / "launchers" / "dist" / "windows_amd64"
    target_dir = tmp_path / "builds" / "pyinstaller" / "windows_amd64"
    external_dir = tmp_path_factory.mktemp("external-pyinstaller-file-link")
    external_file = external_dir / "outside.txt"
    source_dir.mkdir(parents=True)
    target_dir.mkdir(parents=True)
    external_file.write_text("do not link", encoding="utf-8")
    source_link = source_dir / "linked.txt"
    target_link = target_dir / "linked.txt"
    try:
        source_link.symlink_to(external_file)
        target_link.symlink_to(external_file)
    except OSError as exc:
        pytest.skip(f"symlink unavailable: {exc}")

    assert module._sync_platform(tmp_path, "windows_amd64", verbose=False) is True

    assert not target_link.exists()
    assert not target_link.is_symlink()


def test_sync_platform_skips_directory_symlink_outside_repo_root(
    tmp_path: Path, tmp_path_factory: pytest.TempPathFactory
) -> None:
    root = Path(__file__).resolve().parents[1]
    module = _load_module(
        "sync_pyinstaller_outputs_external_symlink",
        root / "scripts" / "sync_pyinstaller_outputs.py",
    )
    source_dir = tmp_path / "launchers" / "dist" / "windows_amd64"
    target_dir = tmp_path / "builds" / "pyinstaller" / "windows_amd64"
    external_dir = tmp_path_factory.mktemp("external-pyinstaller-link")
    source_dir.mkdir(parents=True)
    (external_dir / "outside.txt").write_text("do not copy", encoding="utf-8")

    symlink_path = source_dir / "linked_dir"
    try:
        symlink_path.symlink_to(external_dir, target_is_directory=True)
    except OSError as exc:
        pytest.skip(f"symlink unavailable: {exc}")

    assert module._sync_platform(tmp_path, "windows_amd64", verbose=False) is True

    assert not (target_dir / "linked_dir" / "outside.txt").exists()


def test_sync_platform_removes_stale_broken_target_symlink(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[1]
    module = _load_module(
        "sync_pyinstaller_outputs_broken_target",
        root / "scripts" / "sync_pyinstaller_outputs.py",
    )
    source_dir = tmp_path / "launchers" / "dist" / "windows_amd64"
    target_dir = tmp_path / "builds" / "pyinstaller" / "windows_amd64"
    source_dir.mkdir(parents=True)
    target_dir.mkdir(parents=True)
    broken_link = target_dir / "stale_link"
    try:
        broken_link.symlink_to(tmp_path / "missing")
    except OSError as exc:
        pytest.skip(f"symlink unavailable: {exc}")

    assert module._sync_platform(tmp_path, "windows_amd64", verbose=False) is True

    assert not broken_link.is_symlink()
    assert not broken_link.exists()


def test_sync_platform_reports_stale_removal_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = Path(__file__).resolve().parents[1]
    module = _load_module(
        "sync_pyinstaller_outputs_remove_failure",
        root / "scripts" / "sync_pyinstaller_outputs.py",
    )
    source_dir = tmp_path / "launchers" / "dist" / "windows_amd64"
    target_dir = tmp_path / "builds" / "pyinstaller" / "windows_amd64"
    source_dir.mkdir(parents=True)
    target_dir.mkdir(parents=True)
    stale_file = target_dir / "stale.txt"
    stale_file.write_text("stale", encoding="utf-8")

    def fail_remove(path: Path) -> None:
        if path == stale_file:
            raise PermissionError("locked")
        path.unlink()

    monkeypatch.setattr(module, "_remove_path", fail_remove)

    with pytest.raises(RuntimeError, match="Falha ao remover artefato obsoleto"):
        module._sync_platform(tmp_path, "windows_amd64", verbose=False)


def test_sync_platform_replaces_target_directory_with_source_file(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[1]
    module = _load_module(
        "sync_pyinstaller_outputs_type_mismatch",
        root / "scripts" / "sync_pyinstaller_outputs.py",
    )
    source_dir = tmp_path / "launchers" / "dist" / "windows_amd64"
    target_dir = tmp_path / "builds" / "pyinstaller" / "windows_amd64"
    source_dir.mkdir(parents=True)
    target_dir.mkdir(parents=True)
    (source_dir / "artifact").write_text("file", encoding="utf-8")
    target_artifact = target_dir / "artifact"
    target_artifact.mkdir()
    (target_artifact / "old.txt").write_text("old", encoding="utf-8")

    assert module._sync_platform(tmp_path, "windows_amd64", verbose=False) is True

    assert target_artifact.is_file()
    assert target_artifact.read_text(encoding="utf-8") == "file"
