from __future__ import annotations

import types
import errno as errno_mod

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

    try:
        manager._save_settings()
        raised = False
    except RuntimeError as exc:
        raised = True
        assert "lock indisponivel" in str(exc)

    assert raised
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


def test_lock_file_retries_and_succeeds_for_busy_fcntl(tmp_path, monkeypatch):
    manager = CLIEnhancementManager()
    manager.settings_file = str(tmp_path / "cli_enhancements.json")

    calls = {"count": 0}

    def _fake_flock(_fd, _flags):
        calls["count"] += 1
        if calls["count"] < 3:
            raise OSError(errno_mod.EAGAIN, "busy")

    fake_fcntl = types.SimpleNamespace(LOCK_EX=1, LOCK_NB=2, flock=_fake_flock)
    monkeypatch.setattr(cli_mgr_mod, "fcntl", fake_fcntl)
    monkeypatch.setattr(cli_mgr_mod, "msvcrt", None)
    monkeypatch.setattr(cli_mgr_mod.time, "sleep", lambda _s: None)

    class DummyFile:
        def fileno(self):
            return 1

    manager._lock_file_if_possible(DummyFile())
    assert calls["count"] == 3


def test_lock_file_fails_after_retry_exhaustion_for_busy_fcntl(tmp_path, monkeypatch):
    manager = CLIEnhancementManager()
    manager.settings_file = str(tmp_path / "cli_enhancements.json")

    calls = {"count": 0}

    def _always_busy(_fd, _flags):
        calls["count"] += 1
        raise OSError(errno_mod.EAGAIN, "busy")

    fake_fcntl = types.SimpleNamespace(LOCK_EX=1, LOCK_NB=2, flock=_always_busy)
    monkeypatch.setattr(cli_mgr_mod, "fcntl", fake_fcntl)
    monkeypatch.setattr(cli_mgr_mod, "msvcrt", None)
    monkeypatch.setattr(cli_mgr_mod.time, "sleep", lambda _s: None)

    class DummyFile:
        def fileno(self):
            return 1

    try:
        manager._lock_file_if_possible(DummyFile())
        raised = False
    except RuntimeError as exc:
        raised = True
        assert "apos retries" in str(exc)

    assert raised
    assert calls["count"] == cli_mgr_mod.LOCK_RETRY_ATTEMPTS


def test_lock_file_retries_and_succeeds_for_busy_msvcrt(tmp_path, monkeypatch):
    manager = CLIEnhancementManager()
    manager.settings_file = str(tmp_path / "cli_enhancements.json")

    call_count = {"value": 0}
    lock_lens: list[int] = []

    def _locking(_fd, _mode, _len):
        call_count["value"] += 1
        lock_lens.append(_len)
        if call_count["value"] < 3:
            raise OSError(errno_mod.EACCES, "busy")

    fake_msvcrt = types.SimpleNamespace(LK_NBLCK=7, locking=_locking)
    monkeypatch.setattr(cli_mgr_mod, "fcntl", None)
    monkeypatch.setattr(cli_mgr_mod, "msvcrt", fake_msvcrt)
    monkeypatch.setattr(cli_mgr_mod.time, "sleep", lambda _s: None)

    class DummyFile:
        def fileno(self):
            return 1

        def tell(self):
            return 0

    manager._lock_file_if_possible(DummyFile())
    assert call_count["value"] == 3
    assert lock_lens == [1, 1, 1]


def test_lock_file_fails_fast_for_non_lock_msvcrt_error(tmp_path, monkeypatch):
    manager = CLIEnhancementManager()
    manager.settings_file = str(tmp_path / "cli_enhancements.json")

    def _locking(_fd, _mode, _len):
        raise OSError(errno_mod.EBADF, "bad fd")

    fake_msvcrt = types.SimpleNamespace(LK_NBLCK=7, locking=_locking)
    monkeypatch.setattr(cli_mgr_mod, "fcntl", None)
    monkeypatch.setattr(cli_mgr_mod, "msvcrt", fake_msvcrt)
    monkeypatch.setattr(cli_mgr_mod.time, "sleep", lambda _s: None)

    class DummyFile:
        def fileno(self):
            return 1

        def tell(self):
            return 0

    try:
        manager._lock_file_if_possible(DummyFile())
        raised = False
    except RuntimeError as exc:
        raised = True
        assert "Falha critica" in str(exc)

    assert raised
