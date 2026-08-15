import json
import os
import time
from concurrent.futures import ThreadPoolExecutor

import pytest

import utils.caching as caching


def test_save_cache_is_atomic_and_does_not_corrupt_existing_file(tmp_path, monkeypatch):
    cache_file = tmp_path / "file_cache.json"

    # Seed with a known-good cache file.
    initial = {"a.xlsx": "hash_a"}
    cache_file.write_text(json.dumps(initial, indent=4), encoding="utf-8")
    original_text = cache_file.read_text(encoding="utf-8")

    tmp_prefix = f".{cache_file.name}.tmp."

    def bad_dump(obj, fh, indent=4):  # noqa: ARG001
        # Simulate a crash mid-write.
        fh.write("{")
        fh.flush()
        raise RuntimeError("boom")

    monkeypatch.setattr(caching.json, "dump", bad_dump)

    # save_cache should not raise; it should keep the original file intact.
    caching.save_cache({"b.xlsx": "hash_b"}, str(cache_file))

    assert cache_file.read_text(encoding="utf-8") == original_text
    leftovers = [p for p in tmp_path.iterdir() if p.name.startswith(tmp_prefix)]
    assert leftovers == []


def test_save_cache_writes_valid_json(tmp_path):
    cache_file = tmp_path / "file_cache.json"
    data = {"a.xlsx": "hash_a", "b.xlsx": "hash_b"}
    caching.save_cache(data, str(cache_file))

    loaded = json.loads(cache_file.read_text(encoding="utf-8"))
    assert loaded == data


def test_save_cache_concurrent_writes_last_writer_wins_with_valid_json(tmp_path):
    cache_file = tmp_path / "file_cache.json"
    payloads = [
        {"a.xlsx": "hash_a"},
        {"b.xlsx": "hash_b"},
        {"c.xlsx": "hash_c"},
        {"d.xlsx": "hash_d"},
    ]

    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = [
            executor.submit(caching.save_cache, payload, str(cache_file))
            for payload in payloads
        ]
        for future in futures:
            future.result()

    loaded = json.loads(cache_file.read_text(encoding="utf-8"))
    # save_cache is blind overwrite with atomic replace. Contract: valid JSON,
    # no file corruption. Last writer wins is expected behavior.
    assert loaded in payloads
    assert len(loaded) == 1


def test_save_cache_uses_lock_file_and_releases_it(tmp_path, monkeypatch):
    cache_file = tmp_path / "file_cache.json"
    lock_seen = {"present_during_write": False}
    original_atomic_write = caching._atomic_write_json

    def wrapped_atomic_write(cache, cache_path):
        lock_seen["present_during_write"] = os.path.exists(f"{cache_path}.lock")
        return original_atomic_write(cache, cache_path)

    monkeypatch.setattr(caching, "_atomic_write_json", wrapped_atomic_write)

    caching.save_cache({"a.xlsx": "hash_a"}, str(cache_file))

    assert lock_seen["present_during_write"] is True
    assert (tmp_path / "file_cache.json.lock").exists() is False


def test_update_cache_for_files_concurrent_merges_keep_all_entries(tmp_path):
    docs_dir = tmp_path / "docs_entrada"
    docs_dir.mkdir()
    file_a = docs_dir / "a.xlsx"
    file_b = docs_dir / "b.xlsx"
    file_a.write_text("a", encoding="utf-8")
    file_b.write_text("b", encoding="utf-8")
    cache_file = tmp_path / "file_cache.json"

    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [
            executor.submit(
                caching.update_cache_for_files,
                [str(file_a)],
                str(cache_file),
                str(docs_dir),
            ),
            executor.submit(
                caching.update_cache_for_files,
                [str(file_b)],
                str(cache_file),
                str(docs_dir),
            ),
        ]
        for future in futures:
            future.result()

    # update_cache_for_files merges updates under file lock, so concurrent writes
    # should preserve entries from both workers.
    loaded = json.loads(cache_file.read_text(encoding="utf-8"))
    assert "a.xlsx" in loaded
    assert "b.xlsx" in loaded


def test_acquire_cache_lock_removes_stale_dead_pid_lock(tmp_path, monkeypatch):
    cache_file = tmp_path / "file_cache.json"
    lock_path = str(cache_file) + ".lock"
    with open(lock_path, "w", encoding="ascii") as f:
        f.write("999999\n")

    stale_time = time.time() - 60.0
    os.utime(lock_path, (stale_time, stale_time))

    monkeypatch.setattr(caching, "_CACHE_STALE_MIN_AGE_SEC", 0.0)
    monkeypatch.setattr(caching, "_is_process_alive", lambda pid: False)

    lock_fd = caching._acquire_cache_lock(lock_path)
    try:
        assert os.path.exists(lock_path)
    finally:
        caching._release_cache_lock(lock_fd, lock_path)

    assert not os.path.exists(lock_path)


def test_acquire_cache_lock_preserves_active_lock_and_times_out(tmp_path, monkeypatch):
    cache_file = tmp_path / "file_cache.json"
    lock_path = str(cache_file) + ".lock"
    with open(lock_path, "w", encoding="ascii") as f:
        f.write(f"{os.getpid()}\n")

    monkeypatch.setattr(caching, "_CACHE_STALE_MIN_AGE_SEC", 0.0)
    monkeypatch.setattr(caching, "_CACHE_LOCK_TIMEOUT_SEC", 0.01)
    monkeypatch.setattr(caching, "_CACHE_LOCK_RETRY_SEC", 0.001)
    monkeypatch.setattr(caching, "_is_process_alive", lambda pid: True)

    with pytest.raises(TimeoutError):
        caching._acquire_cache_lock(lock_path)

    assert os.path.exists(lock_path)


def test_acquire_cache_lock_removes_partial_lock_when_pid_write_fails(
    tmp_path, monkeypatch
):
    cache_file = tmp_path / "file_cache.json"
    lock_path = str(cache_file) + ".lock"

    def fail_write(fd, data):  # noqa: ARG001
        raise OSError("write failed")

    monkeypatch.setattr(caching.os, "write", fail_write)

    with pytest.raises(RuntimeError, match="Failed to write cache lock metadata"):
        caching._acquire_cache_lock(lock_path)

    assert not os.path.exists(lock_path)
