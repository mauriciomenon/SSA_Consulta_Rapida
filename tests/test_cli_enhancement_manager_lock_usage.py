from __future__ import annotations

import types

import interface.cli_enhancement_manager as cli_mgr_mod
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


def test_lock_file_fails_fast_when_fcntl_has_no_lock_nb(tmp_path, monkeypatch):
    manager = CLIEnhancementManager()
    manager.settings_file = str(tmp_path / "cli_enhancements.json")

    fake_fcntl = types.SimpleNamespace(LOCK_EX=1, flock=lambda _fd, _flags: None)
    monkeypatch.setattr(cli_mgr_mod, "fcntl", fake_fcntl)
    monkeypatch.setattr(cli_mgr_mod, "msvcrt", None)

    class DummyFile:
        def fileno(self):
            return 1

    try:
        manager._lock_file_if_possible(DummyFile())
        raised = False
    except RuntimeError as exc:
        raised = True
        assert "LOCK_NB" in str(exc)

    assert raised
