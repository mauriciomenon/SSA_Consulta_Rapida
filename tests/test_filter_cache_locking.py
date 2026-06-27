from typing import Any, cast

import pandas as pd

from gui.cache.filter_cache import FilterCache


class _SpyLock:
    def __init__(self) -> None:
        self.enter_count = 0
        self.exit_count = 0

    def __enter__(self):
        self.enter_count += 1
        return self

    def __exit__(self, exc_type, exc, _tb):
        self.exit_count += 1
        return False


def test_filter_cache_uses_lock_for_all_mutations_and_reads():
    spy = _SpyLock()
    cache = FilterCache(max_size=2, lock=spy)

    df = pd.DataFrame({"a": [1, 2]})

    assert spy.enter_count == 0
    before_put = spy.enter_count
    cache.put("df1", [["x"]], "contains", df)
    assert spy.enter_count == before_put + 1
    assert spy.enter_count == spy.exit_count

    before_get = spy.enter_count
    hit = cache.get("df1", [["x"]], "contains")
    assert isinstance(hit, pd.DataFrame)
    assert spy.enter_count == before_get + 1
    assert spy.enter_count == spy.exit_count

    before_stats = spy.enter_count
    stats = cache.get_stats()
    assert stats["hits"] >= 1
    assert spy.enter_count == before_stats + 1

    before_clear = spy.enter_count
    cache.clear()
    assert spy.enter_count == before_clear + 1
    assert spy.enter_count == spy.exit_count


def test_filter_cache_put_ignores_non_dataframe_result():
    cache = FilterCache(max_size=2)

    cache.put("df1", [["x"]], "contains", cast(Any, None))

    stats = cache.get_stats()
    assert stats["size"] == 0
    assert stats["skipped_large_entries"] == 0
    assert cache.get("df1", [["x"]], "contains") is None


def test_filter_cache_skips_large_entries_when_limit_is_set(monkeypatch):
    monkeypatch.setenv("SSA_CACHE_MAX_MB", "0.0001")
    cache = FilterCache(max_size=2)
    large_df = pd.DataFrame({"descricao_ssa": ["x" * 4096, "y" * 4096]})

    cache.put("df_large", [["x"]], "contains", large_df)

    stats = cache.get_stats()
    assert stats["size"] == 0
    assert stats["skipped_large_entries"] == 1
    assert stats["max_entry_mb"] is not None


def test_filter_cache_keeps_small_entries_when_limit_allows(monkeypatch):
    monkeypatch.setenv("SSA_CACHE_MAX_MB", "64")
    cache = FilterCache(max_size=2)
    small_df = pd.DataFrame({"a": [1, 2]})

    cache.put("df_small", [["x"]], "contains", small_df)
    cached = cache.get("df_small", [["x"]], "contains")

    stats = cache.get_stats()
    assert cached is not None
    assert stats["skipped_large_entries"] == 0
    assert stats["hits"] >= 1


def test_filter_cache_uses_default_limit_for_invalid_env(monkeypatch):
    monkeypatch.setenv("SSA_CACHE_MAX_MB", "invalid")
    cache = FilterCache(max_size=2)

    stats = cache.get_stats()

    assert stats["max_entry_mb"] == 64.0


def test_filter_cache_skips_entries_with_unknown_size(monkeypatch):
    cache = FilterCache(max_size=2)
    monkeypatch.setattr(cache, "_estimate_result_bytes", lambda _result: None)

    cache.put("df_unknown", [["x"]], "contains", pd.DataFrame({"a": [1]}))

    stats = cache.get_stats()
    assert stats["size"] == 0
    assert stats["skipped_large_entries"] == 1


def test_filter_cache_shallow_copies_keep_cache_values_isolated():
    cache = FilterCache(max_size=2)
    source_df = pd.DataFrame({"a": [1, 2], "b": ["x", "y"]})

    cache.put("df_small", [["x"]], "contains", source_df)
    source_df.loc[0, "a"] = 999
    source_df.loc[0, "b"] = "changed"

    cached_first = cache.get("df_small", [["x"]], "contains")

    assert cached_first is not None
    assert cached_first["a"].tolist() == [1, 2]
    assert cached_first["b"].tolist() == ["x", "y"]

    cached_first.loc[1, "a"] = 777
    cached_second = cache.get("df_small", [["x"]], "contains")

    assert cached_second is not None
    assert cached_second["a"].tolist() == [1, 2]
    assert cached_second["b"].tolist() == ["x", "y"]
