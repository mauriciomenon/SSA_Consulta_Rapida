from __future__ import annotations

import sys
from pathlib import Path

import pytest

from launchers import main_runtime


def test_seed_runtime_folder_reports_copy_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source_dir = tmp_path / "bundle" / "config"
    source_dir.mkdir(parents=True)
    (source_dir / "settings.json").write_text("{}", encoding="utf-8")
    runtime_dir = tmp_path / "runtime"

    def fail_copy2(*_args: object, **_kwargs: object) -> None:
        raise OSError("copy denied")

    monkeypatch.setattr(main_runtime.shutil, "copy2", fail_copy2)

    with pytest.raises(RuntimeError, match="Falha ao preparar runtime config"):
        main_runtime._seed_runtime_folder(runtime_dir, source_dir, "config")


def test_seed_runtime_folder_preserves_nested_user_file(tmp_path: Path) -> None:
    source_dir = tmp_path / "bundle" / "config"
    nested_source = source_dir / "profiles"
    nested_source.mkdir(parents=True)
    (nested_source / "settings.json").write_text("bundle", encoding="utf-8")

    runtime_dir = tmp_path / "runtime"
    nested_target = runtime_dir / "config" / "profiles"
    nested_target.mkdir(parents=True)
    target_file = nested_target / "settings.json"
    target_file.write_text("user", encoding="utf-8")

    main_runtime._seed_runtime_folder(runtime_dir, source_dir, "config")

    assert target_file.read_text(encoding="utf-8") == "user"


def test_seed_runtime_folder_updates_previous_bundle_file(tmp_path: Path) -> None:
    source_dir = tmp_path / "bundle" / "config"
    source_dir.mkdir(parents=True)
    source_file = source_dir / "settings.json"
    source_file.write_text("bundle-v1", encoding="utf-8")
    runtime_dir = tmp_path / "runtime"

    main_runtime._seed_runtime_folder(runtime_dir, source_dir, "config")
    source_file.write_text("bundle-v2", encoding="utf-8")
    main_runtime.os.utime(source_dir, None)
    main_runtime._seed_runtime_folder(runtime_dir, source_dir, "config")

    target_file = runtime_dir / "config" / "settings.json"
    assert target_file.read_text(encoding="utf-8") == "bundle-v2"


def test_seed_runtime_folder_preserves_user_modified_seeded_file(
    tmp_path: Path,
) -> None:
    source_dir = tmp_path / "bundle" / "config"
    source_dir.mkdir(parents=True)
    source_file = source_dir / "settings.json"
    source_file.write_text("bundle-v1", encoding="utf-8")
    runtime_dir = tmp_path / "runtime"

    main_runtime._seed_runtime_folder(runtime_dir, source_dir, "config")
    target_file = runtime_dir / "config" / "settings.json"
    target_file.write_text("user-change", encoding="utf-8")
    source_file.write_text("bundle-v2", encoding="utf-8")
    main_runtime.os.utime(source_dir, None)
    main_runtime._seed_runtime_folder(runtime_dir, source_dir, "config")

    assert target_file.read_text(encoding="utf-8") == "user-change"


def test_seed_runtime_folder_reports_file_directory_conflict(tmp_path: Path) -> None:
    source_dir = tmp_path / "bundle" / "config"
    (source_dir / "profiles").mkdir(parents=True)

    runtime_dir = tmp_path / "runtime"
    target_file = runtime_dir / "config" / "profiles"
    target_file.parent.mkdir(parents=True)
    target_file.write_text("user file", encoding="utf-8")

    with pytest.raises(RuntimeError, match="Conflito no runtime config"):
        main_runtime._seed_runtime_folder(runtime_dir, source_dir, "config")


def test_seed_runtime_folder_reports_directory_file_conflict(tmp_path: Path) -> None:
    source_dir = tmp_path / "bundle" / "config"
    source_dir.mkdir(parents=True)
    (source_dir / "settings.json").write_text("bundle", encoding="utf-8")

    runtime_dir = tmp_path / "runtime"
    target_dir = runtime_dir / "config" / "settings.json"
    target_dir.mkdir(parents=True)

    with pytest.raises(RuntimeError, match="Conflito no runtime config"):
        main_runtime._seed_runtime_folder(runtime_dir, source_dir, "config")


def test_seed_runtime_folder_skips_recursive_scan_when_marker_matches(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source_dir = tmp_path / "bundle" / "config"
    nested_source = source_dir / "profiles"
    nested_source.mkdir(parents=True)
    (nested_source / "settings.json").write_text("bundle", encoding="utf-8")
    runtime_dir = tmp_path / "runtime"

    main_runtime._seed_runtime_folder(runtime_dir, source_dir, "config")

    def fail_copy2(*_args: object, **_kwargs: object) -> None:
        raise OSError("unexpected copy")

    monkeypatch.setattr(main_runtime.shutil, "copy2", fail_copy2)
    main_runtime._seed_runtime_folder(runtime_dir, source_dir, "config")

    assert (
        runtime_dir / "config" / "profiles" / "settings.json"
    ).read_text(encoding="utf-8") == "bundle"


def test_ensure_runtime_environment_keeps_project_root_trusted(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    bundle_root = tmp_path / "bundle"
    runtime_dir = tmp_path / "runtime"
    (bundle_root / "config").mkdir(parents=True)
    (bundle_root / "config" / "version.json").write_text("{}", encoding="utf-8")

    monkeypatch.setattr(main_runtime, "_runtime_root", "")
    monkeypatch.setattr(main_runtime, "_runtime_environment_initialized", False)
    monkeypatch.setattr(main_runtime, "_resolve_runtime_home", lambda: runtime_dir)
    monkeypatch.setattr(sys, "frozen", True, raising=False)

    original_cwd = Path.cwd()
    try:
        resolved_runtime = main_runtime.ensure_runtime_environment(str(bundle_root))
    finally:
        main_runtime.os.chdir(original_cwd)
        for key in (
            "SSA_BUNDLED_ROOT",
            "SSA_RUNTIME_ROOT",
            "SSA_CONFIG_DIR",
            "SSA_DB_PATH",
            "SSA_EXTRA_ALLOWED_PATHS",
        ):
            main_runtime.os.environ.pop(key, None)

    assert resolved_runtime == str(runtime_dir)
    assert str(runtime_dir) not in sys.path


def test_prepare_frozen_runtime_overwrites_stale_runtime_env(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    bundle_root = tmp_path / "bundle"
    runtime_dir = tmp_path / "runtime"
    bundle_root.mkdir()
    stale_root = tmp_path / "stale"
    stale_root.mkdir()

    monkeypatch.setenv("SSA_BUNDLED_ROOT", str(stale_root))
    monkeypatch.setenv("SSA_RUNTIME_ROOT", str(stale_root))
    monkeypatch.setenv("SSA_CONFIG_DIR", str(stale_root / "config"))
    monkeypatch.setenv("SSA_DB_PATH", str(stale_root / "data" / "ssas.db"))
    monkeypatch.setattr(main_runtime, "_resolve_runtime_home", lambda: runtime_dir)
    monkeypatch.setattr(sys, "frozen", True, raising=False)

    original_cwd = Path.cwd()
    try:
        resolved_runtime = main_runtime._prepare_frozen_runtime(str(bundle_root))
        env_snapshot = {
            "SSA_BUNDLED_ROOT": main_runtime.os.environ["SSA_BUNDLED_ROOT"],
            "SSA_RUNTIME_ROOT": main_runtime.os.environ["SSA_RUNTIME_ROOT"],
            "SSA_CONFIG_DIR": main_runtime.os.environ["SSA_CONFIG_DIR"],
            "SSA_DB_PATH": main_runtime.os.environ["SSA_DB_PATH"],
        }
    finally:
        main_runtime.os.chdir(original_cwd)

    assert resolved_runtime == str(runtime_dir)
    assert env_snapshot == {
        "SSA_BUNDLED_ROOT": str(Path(sys.executable).resolve().parent),
        "SSA_RUNTIME_ROOT": str(runtime_dir),
        "SSA_CONFIG_DIR": str(runtime_dir / "config"),
        "SSA_DB_PATH": str(runtime_dir / "data" / "ssas.db"),
    }


def test_prepare_frozen_runtime_reports_chdir_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runtime_dir = tmp_path / "runtime"
    bundle_root = tmp_path / "bundle"
    bundle_root.mkdir()

    monkeypatch.setattr(main_runtime, "_resolve_runtime_home", lambda: runtime_dir)
    monkeypatch.setattr(sys, "frozen", True, raising=False)

    def fail_chdir(*_args: object, **_kwargs: object) -> None:
        raise OSError("chdir denied")

    monkeypatch.setattr(main_runtime.os, "chdir", fail_chdir)

    with pytest.raises(RuntimeError, match="Falha ao entrar no runtime frozen"):
        main_runtime._prepare_frozen_runtime(str(bundle_root))
