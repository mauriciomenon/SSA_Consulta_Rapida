from __future__ import annotations

import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import pandas as pd
import pytest

from core.cache_manager import CacheManager

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_formatted_cache_measures_each_frame_once_when_evicting(monkeypatch) -> None:
    cache = CacheManager()
    small = pd.DataFrame({"text": ["x" * 1000]})
    cache.max_dataframe_bytes = 3 * int(small.memory_usage(deep=True).sum()) + 1
    for key in ("first", "second", "third"):
        cache.cache_formatted_df(key, small)
    retained_ids = {id(frame) for frame in cache._caches["dataframes"].values()}
    incoming = pd.DataFrame({"text": ["y" * 1900]})
    original_measure = pd.DataFrame.memory_usage
    calls = {}

    def measure(frame, *args, **kwargs):
        calls[id(frame)] = calls.get(id(frame), 0) + 1
        return original_measure(frame, *args, **kwargs)

    monkeypatch.setattr(pd.DataFrame, "memory_usage", measure)
    cache.cache_formatted_df("incoming", incoming)

    assert calls == dict.fromkeys(retained_ids | {id(incoming)}, 1)
    assert cache.get_cached_formatted_df("first") is None
    assert cache.get_cached_formatted_df("second") is None
    assert cache.get_cached_formatted_df("third") is not None
    pd.testing.assert_frame_equal(cache.get_cached_formatted_df("incoming"), incoming)


def test_formatted_cache_does_not_hide_copy_failure(monkeypatch) -> None:
    cache = CacheManager()
    frame = pd.DataFrame({"text": ["value"]})

    def fail_copy(*args, **kwargs):
        raise ValueError("copy failed")

    monkeypatch.setattr(frame, "copy", fail_copy)
    with pytest.raises(ValueError, match="copy failed"):
        cache.cache_formatted_df("frame", frame)
    assert cache.get_cached_formatted_df("frame") is None


def test_formatted_cache_reports_inconsistent_eviction_state() -> None:
    cache = CacheManager()
    frame = pd.DataFrame({"text": ["x" * 1000]})
    cache.max_dataframe_bytes = int(frame.memory_usage(deep=True).sum()) + 1
    cache.cache_formatted_df("first", frame)
    cache._access_times["dataframes"].clear()

    with pytest.raises(RuntimeError, match="eviction did not remove an entry"):
        cache.cache_formatted_df("second", frame)
    assert cache.get_cached_formatted_df("second") is None


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


def test_dataframe_hash_handles_unhashable_object_cells() -> None:
    cache = CacheManager()
    left = pd.DataFrame(
        {"a": [[1, 2], {"nested": ["x"]}, {3, 4}], "b": ["same", "same", "same"]}
    )
    right = pd.DataFrame(
        {"a": [[1, 2], {"nested": ["y"]}, {3, 4}], "b": ["same", "same", "same"]}
    )

    assert cache.get_dataframe_hash(left) != cache.get_dataframe_hash(right)


def test_dataframe_hash_handles_mixed_dict_keys() -> None:
    cache = CacheManager()
    left = pd.DataFrame({"a": [{1: "a", "1": "b"}]})
    right = pd.DataFrame({"a": [{1: "a", "1": "changed"}]})

    assert cache.get_dataframe_hash(left) != cache.get_dataframe_hash(right)


def test_dataframe_hash_handles_cyclic_object_cells() -> None:
    cache = CacheManager()
    cyclic: list[Any] = []
    cyclic.append(cyclic)
    different: list[Any] = ["changed"]
    different.append(different)
    frame = pd.DataFrame({"a": [cyclic]})
    other_frame = pd.DataFrame({"a": [different]})

    first = cache.get_dataframe_hash(frame)
    second = cache.get_dataframe_hash(frame)

    assert first == second
    assert first != cache.get_dataframe_hash(other_frame)


def test_dataframe_hash_handles_bad_repr_object_cells_without_pickle() -> None:
    class BadObject:
        def __getstate__(self):
            raise TypeError("no pickle")

        def __repr__(self):
            raise RuntimeError("no repr")

    cache = CacheManager()
    frame = pd.DataFrame({"a": [[BadObject()]]})

    result = cache.get_dataframe_hash(frame)

    assert isinstance(result, str)
    assert len(result) == 32


def test_dataframe_hash_fallback_does_not_use_pickle() -> None:
    source = (PROJECT_ROOT / "core" / "cache_manager.py").read_text(encoding="utf-8")

    assert "import pickle" not in source
    assert "pickle.dumps" not in source


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


def test_cache_stats_counts_container_entries() -> None:
    cache = CacheManager()
    widths = {"numero_ssa": 120, "descricao_ssa": 320}
    cache.cache_widths("frame", widths)

    stats = cache.get_cache_stats()

    assert stats["cache_details"]["widths"]["entries"] == 1
    assert stats["cache_details"]["widths"]["memory_estimate"] > sys.getsizeof(widths)


def test_cache_stats_estimates_memory_outside_lock(monkeypatch) -> None:
    cache = CacheManager()
    cache.cache_widths("frame", {"numero_ssa": 120})
    original_getsizeof = sys.getsizeof

    class TrackingLock:
        owned = False

        def __enter__(self):
            self.owned = True
            return self

        def __exit__(self, _exc_type, _exc, _traceback):
            self.owned = False
            return False

    tracking_lock = TrackingLock()
    setattr(cache, "_lock", tracking_lock)

    def guarded_getsizeof(value):
        assert not tracking_lock.owned
        return original_getsizeof(value)

    monkeypatch.setattr("core.cache_manager.sys.getsizeof", guarded_getsizeof)

    stats = cache.get_cache_stats()

    assert stats["cache_details"]["widths"]["entries"] == 1


def test_cache_stats_reuses_memory_estimate_until_cache_changes(monkeypatch) -> None:
    cache = CacheManager()
    cache.cache_widths("frame", {"numero_ssa": 120})
    original_getsizeof = sys.getsizeof
    calls = 0

    def counting_getsizeof(value):
        nonlocal calls
        calls += 1
        return original_getsizeof(value)

    monkeypatch.setattr("core.cache_manager.sys.getsizeof", counting_getsizeof)

    first = cache.get_cache_stats()
    calls_after_first = calls
    second = cache.get_cache_stats()

    assert first["cache_details"] == second["cache_details"]
    assert calls == calls_after_first

    cache.cache_widths("other", {"descricao_ssa": 320})
    cache.get_cache_stats()

    assert calls > calls_after_first


def test_cache_manager_named_cache_honors_independent_limit() -> None:
    cache = CacheManager()

    cache.cache_value("details", ("k", 0), 0, max_entries=2)
    cache.cache_value("details", ("k", 1), 1, max_entries=2)
    cache.cache_value("details", ("k", 2), 2, max_entries=2)

    assert cache.get_cached_value("details", ("k", 0)) is None
    assert cache.get_cached_value("details", ("k", 1)) == 1
    assert cache.get_cached_value("details", ("k", 2)) == 2


def test_cache_manager_invalidate_cache_clears_named_cache() -> None:
    cache = CacheManager()
    cache.cache_value("details", "row", {"value": 1}, max_entries=2)

    cache.invalidate_cache("details")

    assert cache.get_cached_value("details", "row") is None
