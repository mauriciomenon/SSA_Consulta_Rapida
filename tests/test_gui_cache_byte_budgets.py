"""Cache budgets measure full retained payloads and release invalid generations."""

from collections import OrderedDict

import pandas as pd
import pytest

from core import search_filter
from core.cache_manager import CacheManager
from gui.cache.filter_cache import FilterCache
from gui.simple_width_manager import SimpleCacheManager
from gui.ssa import gui_filters_advanced_state, gui_filters_responsavel_refresh, table_sorting
from gui.ssa import gui_filters_advanced_refresh
from gui.ssa.column_filter_engine import _trim_cache_dict
from gui.ssa.column_filter_engine import ColumnFilterCaches, _trim_date_caches
from gui.workers.filter_worker import FilterWorker


def test_normalized_cache_counts_long_values_after_sample_prefix():
    series = pd.Series(["x"] * 1024 + ["z" * 10000] * 20)
    actual_bytes = int(series.memory_usage(index=True, deep=True))
    assert search_filter._estimate_normalized_cache_bytes({"text": series}) == actual_bytes


def test_normalized_cache_does_not_retain_build_completed_after_clear(monkeypatch):
    frame = pd.DataFrame({"descricao_ssa": ["text"]})
    frame.attrs[search_filter.FILTER_SOURCE_TOKEN_ATTR] = "generation-test"
    frame.attrs[search_filter.FILTER_SOURCE_REVISION_ATTR] = 1
    original_builder = search_filter._build_normalized_columns

    def clear_while_building(*args):
        result = original_builder(*args)
        FilterWorker.clear_shared_cache()
        return result

    monkeypatch.setattr(search_filter, "_build_normalized_columns", clear_while_building)
    result = search_filter._build_normalized_column_cache(frame, ["descricao_ssa"])
    assert result["descricao_ssa"].tolist() == ["text"]
    assert not search_filter._NORMALIZED_SEARCH_CACHE


def test_filter_cache_measures_deep_bytes_exactly():
    frame = pd.DataFrame({"text": ["a"] * 64 + ["b" * 1000] * 100})
    assert FilterCache()._estimate_result_bytes(frame) == int(frame.memory_usage(deep=True).sum())


def test_formatted_cache_rejects_oversized_frame_before_copy(monkeypatch):
    manager = CacheManager()
    manager.max_dataframe_bytes = 100
    frame = pd.DataFrame({"text": ["x" * 1000]})

    def forbidden_copy(*args, **kwargs):
        raise AssertionError("oversized frame must not be copied")

    monkeypatch.setattr(frame, "copy", forbidden_copy)
    manager.cache_formatted_df("large", frame)
    assert manager.get_cached_formatted_df("large") is None


def test_formatted_cache_evicts_to_aggregate_budget():
    manager = CacheManager()
    frame = pd.DataFrame({"text": ["x" * 1000]})
    frame_bytes = int(frame.memory_usage(deep=True).sum())
    manager.max_dataframe_bytes = frame_bytes + 1
    manager.cache_formatted_df("first", frame)
    manager.cache_formatted_df("second", frame)
    assert manager.get_cached_formatted_df("first") is None
    pd.testing.assert_frame_equal(manager.get_cached_formatted_df("second"), frame)


def test_active_gui_formatted_cache_obeys_byte_limit():
    manager = SimpleCacheManager()
    manager.max_formatted_bytes = 100
    manager.cache_formatted_df("large", pd.DataFrame({"text": ["x" * 1000]}))
    assert manager.get_cached_formatted_df("large") is None


def test_named_cache_rejects_oversized_value_without_evicting_existing():
    manager = SimpleCacheManager()
    manager.max_named_bytes = 1024
    manager.cache_value("small", "kept", "value")
    manager.cache_value("large", "rejected", pd.Series(["x" * 2000]))
    assert manager.get_cached_value("small", "kept") == "value"
    assert manager.get_cached_value("large", "rejected") is None


def test_named_cache_budget_covers_all_namespaces():
    manager = SimpleCacheManager()
    value = pd.Series(["x" * 1000])
    manager.max_named_bytes = CacheManager._estimate_cache_items_memory([("entry", (value, 0))]) + 1
    manager.cache_value("first", "entry", value)
    manager.cache_value("second", "entry", value.copy())
    assert manager.get_cached_value("first", "entry") is None
    pd.testing.assert_series_equal(manager.get_cached_value("second", "entry"), value)


def test_named_cache_measures_only_incoming_snapshot(monkeypatch):
    manager = SimpleCacheManager()
    original_estimator = CacheManager._estimate_cache_items_memory
    measured = []

    def record_estimate(items):
        measured.append(items)
        return original_estimator(items)

    monkeypatch.setattr(CacheManager, "_estimate_cache_items_memory", record_estimate)
    manager.cache_value("first", "one", {"value": "one"})
    manager.cache_value("second", "two", pd.Series(["two"]))
    assert len(measured) == 2
    for named_cache in manager._named_caches.values():
        for entry in named_cache.values():
            assert entry[1] >= original_estimator([("entry", entry)])


def test_named_cache_metadata_is_not_deduplicated_with_payload():
    manager = SimpleCacheManager()
    manager.cache_value("integer", "limit", manager.max_named_bytes)
    entry = manager._named_caches["integer"]["limit"]
    assert entry[1] >= CacheManager._estimate_cache_items_memory([("entry", entry)])


def test_named_cache_replacement_count_limit_and_clear_keep_accounting_consistent():
    manager = SimpleCacheManager()
    manager.cache_value("values", "one", "old", max_entries=2)
    manager.cache_value("values", "one", "updated", max_entries=2)
    manager.cache_value("values", "two", "second", max_entries=2)
    assert manager.get_cached_value("values", "one") == "updated"
    manager.cache_value("values", "three", "third", max_entries=2)
    assert manager.get_cached_value("values", "one") is None
    assert set(manager._named_caches["values"]) == {"two", "three"}
    manager._named_caches.clear()
    manager.cache_value("values", "one", "fresh", max_entries=2)
    assert list(manager._named_caches["values"]) == ["one"]
    assert manager.get_cached_value("values", "one") == "fresh"


def test_named_cache_oversized_replacement_does_not_leave_stale_value():
    manager = SimpleCacheManager()
    manager.max_named_bytes = 1024
    manager.cache_value("values", "updated", "old")
    manager.cache_value("values", "kept", "other")
    manager.cache_value("values", "updated", "x" * 2000)
    assert manager.get_cached_value("values", "updated") is None
    assert manager.get_cached_value("values", "kept") == "other"


def test_named_cache_evicts_old_other_namespace_before_incoming_snapshot():
    manager = SimpleCacheManager()
    manager.max_named_bytes = 1000
    manager.cache_value("first", "initial", "old", max_entries=1)
    manager.cache_value("second", "older", "x" * 600)
    manager.cache_value("first", "fresh", "y" * 600, max_entries=1)
    assert manager.get_cached_value("first", "fresh") == "y" * 600
    assert manager.get_cached_value("second", "older") is None
    assert sum(entry[1] for cache in manager._named_caches.values()
               for entry in cache.values()) <= manager.max_named_bytes


def test_named_cache_measures_lazy_index_retained_frame():
    from gui.ssa.details_series_index import DetailsSeriesIndex

    manager = SimpleCacheManager()
    manager.max_named_bytes = 1024
    frame = pd.DataFrame({"numero_ssa": ["1"], "description": ["x" * 2000]})
    index = DetailsSeriesIndex(frame, {"1": 0})
    measured = CacheManager._estimate_cache_items_memory([("index", index)])
    assert measured >= int(frame.memory_usage(deep=True).sum())
    manager.cache_value("details", "index", index)
    assert manager.get_cached_value("details", "index") is None


def test_named_cache_does_not_retain_mutable_lazy_mapping():
    from gui.ssa.details_series_index import DetailsSeriesIndex

    manager = SimpleCacheManager()
    frame = pd.DataFrame({"numero_ssa": ["1"]})
    index = DetailsSeriesIndex(frame, {"1": 0})
    manager.cache_value("details", "index", index)
    assert manager.get_cached_value("details", "index") is None
    assert index["1"]["numero_ssa"] == "1"
    manager.cache_value("dictionary", "entry", OrderedDict(number="1"))
    assert manager.get_cached_value("dictionary", "entry") == {"number": "1"}


def test_details_positions_cache_reuses_index_and_preserves_first_duplicate(monkeypatch):
    from types import SimpleNamespace
    from gui.ssa import gui_details

    window = SimpleNamespace(_data_uuid="position-test", _data_revision=1,
                             cache_manager=SimpleCacheManager())
    frame = pd.DataFrame({"numero_ssa": ["123", "123", "456"],
                          "description": ["first", "duplicate", "other"]})
    first = gui_details._get_df_ssa_series_index(window, frame)

    def fail_rebuild(*args):
        raise AssertionError("cached positions must avoid index reconstruction")

    monkeypatch.setattr(gui_details, "_get_cached_normalized_series", fail_rebuild)
    second = gui_details._get_df_ssa_series_index(window, frame)
    assert second is not first
    assert second["123"]["description"] == "first"
    assert second["456"]["description"] == "other"
    assert second.get("missing") is None
    assert next(iter(window.cache_manager._named_caches["details_df_ssa_index"].values()))[0].to_dict() == {
        "123": 0, "456": 2,
    }


def test_details_positions_cache_does_not_retain_source_dataframe():
    import gc
    import weakref
    from types import SimpleNamespace
    from gui.ssa import gui_details

    window = SimpleNamespace(_data_uuid="position-owner", _data_revision=1,
                             cache_manager=SimpleCacheManager())
    frame = pd.DataFrame({"numero_ssa": ["123"], "description": ["text"]})
    source_ref = weakref.ref(frame)
    lookup = gui_details._get_df_ssa_series_index(window, frame)
    assert lookup["123"]["description"] == "text"
    del lookup, frame
    gc.collect()
    assert source_ref() is None
    assert window.cache_manager._named_caches["details_df_ssa_index"]


def test_details_positions_over_budget_still_returns_correct_lookup():
    from types import SimpleNamespace
    from gui.ssa import gui_details

    manager = SimpleCacheManager()
    manager.max_named_bytes = 128
    window = SimpleNamespace(_data_uuid="position-limit", _data_revision=1,
                             cache_manager=manager)
    frame = pd.DataFrame({"numero_ssa": ["123", "456"]})
    lookup = gui_details._get_df_ssa_series_index(window, frame)
    assert lookup["456"]["numero_ssa"] == "456"
    assert not manager._named_caches.get("details_df_ssa_index")


def test_details_positions_index_engine_is_counted_before_admission():
    from types import SimpleNamespace
    from gui.ssa import gui_details

    manager = SimpleCacheManager()
    window = SimpleNamespace(_data_uuid="position-engine", _data_revision=1,
                             cache_manager=manager)
    numbers = [str(202600000 + i) for i in range(10000)]
    frame = pd.DataFrame({"numero_ssa": numbers})
    gui_details._get_df_ssa_series_index(window, frame)
    entry = next(iter(manager._named_caches["details_df_ssa_index"].values()))
    before = CacheManager._estimate_cache_items_memory([("entry", entry)])
    lookup = gui_details._get_df_ssa_series_index(window, frame)
    for number in (numbers[0], numbers[3456], numbers[-1]):
        assert lookup[number]["numero_ssa"] == number
    assert lookup.get("missing") is None
    with pytest.raises(KeyError):
        lookup["another-missing"]
    after = CacheManager._estimate_cache_items_memory([("entry", entry)])
    assert before == after
    assert entry[1] >= after


def test_details_positions_series_preserves_mapping_and_input_isolation():
    from gui.ssa.details_series_index import DetailsSeriesIndex

    frame = pd.DataFrame({"numero_ssa": ["first", "second"]})
    positions = pd.Series([0, 1], index=["first", "second"], dtype="int64")
    lookup = DetailsSeriesIndex(frame, positions)
    positions.iloc[0] = 1
    assert list(lookup) == ["first", "second"]
    assert len(lookup) == 2
    assert lookup["first"]["numero_ssa"] == "first"
    assert lookup.get_position("first") == 0
    assert isinstance(lookup.get_position("first"), int)
    assert lookup.get_position("missing") is None
    fallback = object()
    assert lookup.get("missing", fallback) is fallback
    with pytest.raises(KeyError):
        lookup["missing"]


def test_cache_estimator_counts_shared_object_once_and_handles_cycles():
    from types import SimpleNamespace

    frame = pd.DataFrame({"text": ["x" * 2000]})
    owner = SimpleNamespace(frame=frame)
    owner.cycle = owner
    single = CacheManager._estimate_cache_items_memory([("owner", owner)])
    shared = CacheManager._estimate_cache_items_memory([("owner", owner), ("same", owner)])
    assert single == shared
    assert single >= int(frame.memory_usage(deep=True).sum())


def test_column_cache_evicts_by_deep_bytes():
    series = pd.Series(["x" * 1000])
    cache = OrderedDict(first=series.copy(), second=series.copy())
    _trim_cache_dict(cache, 96, max_bytes=int(series.memory_usage(deep=True)) + 1)
    assert list(cache) == ["second"]


@pytest.mark.parametrize("oversized_owner", ["display", "parsed"])
def test_date_cache_byte_eviction_keeps_display_and_parsed_keys_paired(oversized_owner):
    small_display = pd.Series(["01/01/2026"])
    small_parsed = pd.Series(pd.to_datetime(["2026-01-01"]))
    caches = ColumnFilterCaches(
        revision=1, series={}, casefold={}, mask={}, date_scope=None,
        date={"evicted": pd.Series(["x" * 2000]) if oversized_owner == "display" else small_display,
              "kept": small_display},
        date_parsed={"evicted": pd.Series(pd.to_datetime(["2026-01-01"] * 200))
                     if oversized_owner == "parsed" else small_parsed,
                     "kept": small_parsed},
        max_bytes=6000,
    )
    _trim_date_caches(caches)
    assert set(caches.date) == set(caches.date_parsed) == {"kept"}


def test_advanced_cache_subcota_limits_full_owner(monkeypatch):
    monkeypatch.setattr(gui_filters_advanced_state, "ADV_FILTER_CACHE_MAX_BYTES", 400)
    for _ in gui_filters_advanced_state.ADV_FILTER_CACHE_ATTRS:
        cache = {"series": pd.Series(["x" * 1000])}
        gui_filters_advanced_state.prune_adv_cache(cache, 96)
        assert not cache


def test_advanced_options_budget_discards_whole_payload(monkeypatch):
    monkeypatch.setattr(gui_filters_advanced_refresh, "ADV_FILTER_CACHE_MAX_BYTES", 100)
    frame = pd.DataFrame({"setor_executor": ["IEE3"], "situacao": ["APV"]})
    cache = {}
    result = gui_filters_advanced_refresh.get_cached_advanced_filter_option_values(
        cache, frame, data_load_token="options-budget", sort_sectors=sorted,
    )
    assert result.exec_vals == ["IEE3"]
    assert result.status_vals == ["APV"]
    assert cache == {}


def test_responsavel_cache_counts_nested_strings(monkeypatch):
    monkeypatch.setattr(gui_filters_responsavel_refresh, "RESPONSAVEL_CACHE_MAX_BYTES", 300)
    cache = OrderedDict(rank={"person": {"sector": "x" * 1000}})
    gui_filters_responsavel_refresh._trim_ordered_cache(cache)
    assert not cache


def test_sort_cache_skips_oversized_keys(monkeypatch):
    monkeypatch.setattr(table_sorting, "MAX_SORT_CACHE_BYTES", 200)
    keys = pd.DataFrame({"text": ["x" * 1000]})
    result = table_sorting._build_sort_cache((1,), 1, keys)
    assert result["keys_df"] is None


def test_unknown_column_cache_size_discards_entry(monkeypatch):
    def fail_size(*args):
        raise ValueError("size unavailable")

    monkeypatch.setattr(CacheManager, "_estimate_cache_items_memory", fail_size)
    cache = {"entry": pd.Series(["text"])}
    _trim_cache_dict(cache, 96, max_bytes=1000)
    assert not cache
