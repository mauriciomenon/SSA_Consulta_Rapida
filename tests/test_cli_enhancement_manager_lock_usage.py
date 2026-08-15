from __future__ import annotations

import errno as errno_mod
import os
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


def test_save_settings_does_not_remove_preexisting_lock_file_on_lock_failure(
    tmp_path, monkeypatch
):
    manager = CLIEnhancementManager()
    manager.settings_file = str(tmp_path / "cli_enhancements.json")
    manager.settings = {"enhanced_table_printer": True}

    real_os_open = os.open
    lock_path = f"{manager.settings_file}.lock"
    lock_attempts = {"count": 0}
    remove_calls: list[str] = []

    def _fake_open(path, flags, mode=0o777):  # noqa: ANN001,ANN002,ANN003
        if path == lock_path:
            lock_attempts["count"] += 1
            if lock_attempts["count"] == 1 and (flags & os.O_EXCL):
                raise FileExistsError()
        return real_os_open(path, flags, mode)

    def _spy_remove(path):  # noqa: ANN001
        remove_calls.append(path)
        return os.unlink(path)

    monkeypatch.setattr(cli_mgr_mod.os, "open", _fake_open)
    monkeypatch.setattr(cli_mgr_mod.os, "remove", _spy_remove)
    monkeypatch.setattr(
        manager,
        "_lock_file_if_possible",
        lambda _f: (_ for _ in ()).throw(RuntimeError("lock busy")),
    )

    lock_fd = os.open(lock_path, os.O_RDWR | os.O_CREAT, 0o600)
    os.close(lock_fd)

    try:
        manager._save_settings()
        raised = False
    except RuntimeError as exc:
        raised = True
        assert "lock indisponivel" in str(exc)

    assert raised
    assert lock_attempts["count"] >= 2
    assert remove_calls == []
    assert os.path.exists(lock_path)


def test_save_settings_removes_new_lock_file_on_lock_failure(tmp_path, monkeypatch):
    manager = CLIEnhancementManager()
    manager.settings_file = str(tmp_path / "cli_enhancements.json")
    manager.settings = {"enhanced_table_printer": True}

    lock_path = f"{manager.settings_file}.lock"
    remove_calls: list[str] = []

    def _spy_remove(path):  # noqa: ANN001
        remove_calls.append(path)
        return os.unlink(path)

    monkeypatch.setattr(cli_mgr_mod.os, "remove", _spy_remove)
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
    assert lock_path in remove_calls
    assert not os.path.exists(lock_path)
