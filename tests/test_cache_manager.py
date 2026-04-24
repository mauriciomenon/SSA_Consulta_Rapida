from __future__ import annotations

from datetime import datetime, timedelta

import pandas as pd

from core.cache_manager import CacheManager


def test_width_cache_keeps_zero_width_distinct_from_unspecified_width() -> None:
    cache = CacheManager()

    cache.cache_widths("frame", {"a": 10})
    cache.cache_widths("frame", {"a": 0}, table_width=0)

    assert cache.get_cached_widths("frame") == {"a": 10}
    assert cache.get_cached_widths("frame", table_width=0) == {"a": 0}


def test_dataframe_hash_detects_middle_row_changes() -> None:
    cache = CacheManager()
    left = pd.DataFrame({"a": [1, 2, 3, 4, 5]})
    right = pd.DataFrame({"a": [1, 2, 99, 4, 5]})

    assert cache.get_dataframe_hash(left) != cache.get_dataframe_hash(right)


def test_cleanup_old_entries_uses_timedelta_arithmetic() -> None:
    cache = CacheManager()
    cache.cache_config("old", {"value": 1})
    cache._access_times["configurations"]["old"] = datetime.now() - timedelta(hours=2)

    removed = cache.cleanup_old_entries(max_age_minutes=60)

    assert removed == 1
    assert cache.get_cached_config("old") is None


def test_cache_stats_does_not_stringify_cached_dataframes(monkeypatch) -> None:
    cache = CacheManager()
    frame = pd.DataFrame({"a": [1, 2, 3]})
    cache.cache_formatted_df("frame", frame)

    def fail_to_string(*_args, **_kwargs):
        raise AssertionError("DataFrame string formatting should not be used")

    monkeypatch.setattr(pd.DataFrame, "to_string", fail_to_string)

    stats = cache.get_cache_stats()

    assert stats["cache_details"]["dataframes"]["entries"] == 1
    assert stats["cache_details"]["dataframes"]["memory_estimate"] > 0
