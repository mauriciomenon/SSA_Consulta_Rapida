import json
from concurrent.futures import ThreadPoolExecutor

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


def test_save_cache_concurrent_writes_remain_valid_json(tmp_path):
    cache_file = tmp_path / "file_cache.json"
    payloads = [
        {"a.xlsx": "hash_a"},
        {"b.xlsx": "hash_b"},
        {"c.xlsx": "hash_c"},
        {"d.xlsx": "hash_d"},
    ]

    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = [executor.submit(caching.save_cache, payload, str(cache_file)) for payload in payloads]
        for future in futures:
            future.result()

    loaded = json.loads(cache_file.read_text(encoding="utf-8"))
    assert loaded in payloads
