from __future__ import annotations

from interface.cli_enhancement_manager import CLIEnhancementManager


def test_save_settings_applies_single_lock_on_lockfile(tmp_path, monkeypatch):
    manager = CLIEnhancementManager()
    manager.settings_file = str(tmp_path / "cli_enhancements.json")
    manager.settings = {"enhanced_table_printer": True}

    calls = {"count": 0}

    def _spy_lock(_f):
        calls["count"] += 1

    monkeypatch.setattr(manager, "_lock_file_if_possible", _spy_lock)
    manager._save_settings()

    assert calls["count"] == 1


def test_save_settings_aborts_when_lock_acquisition_fails(tmp_path, monkeypatch):
    manager = CLIEnhancementManager()
    manager.settings_file = str(tmp_path / "cli_enhancements.json")
    manager.settings = {"enhanced_table_printer": True}

    monkeypatch.setattr(
        manager,
        "_lock_file_if_possible",
        lambda _f: (_ for _ in ()).throw(RuntimeError("lock busy")),
    )

    manager._save_settings()

    assert not (tmp_path / "cli_enhancements.json").exists()
