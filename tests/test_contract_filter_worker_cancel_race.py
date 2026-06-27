"""Contract tests for FilterWorker cancel/race edges.

Pipeline contracts; GUI race scenarios in test_scenario_filter_race_conditions_qt.py
and worker cache sync in test_scenario_filter_worker_cache_qt.py.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

pytest.importorskip(
    "PyQt6", reason="Dependencia PyQt6 indisponivel no ambiente de teste"
)
from PyQt6.QtWidgets import QApplication

from gui.cache.filter_cache import FilterCache
from gui.workers.filter_worker import FilterWorker


@pytest.fixture(scope="module", autouse=True)
def _qapp():
    app = QApplication.instance() or QApplication([])
    yield app


def test_worker_cancel_after_cache_hit_does_not_emit():
    df = pd.DataFrame({"texto": ["alfa", "beta"], "situacao": ["APV", "STE"]})
    cache = FilterCache(max_size=4)
    cache.put("hash-a", [["alfa"]], "contains", df.iloc[[0]].copy(), cache_context="")

    worker = FilterWorker(
        df,
        [["alfa"]],
        df_hash="hash-a",
        cache=cache,
    )
    emit_spy = MagicMock()
    error_spy = MagicMock()
    worker.filter_finished.connect(emit_spy)
    worker.error_occurred.connect(error_spy)

    with patch.object(worker, "_is_cancelled", side_effect=[False, True]):
        with patch(
            "gui.workers.filter_worker.apply_general_search_terms"
        ) as heavy_search:
            worker.run()

    assert emit_spy.call_count == 0
    assert error_spy.call_count == 0
    heavy_search.assert_not_called()


def test_worker_cancel_after_cache_miss_discards_before_emit():
    df = pd.DataFrame({"texto": ["alfa"], "situacao": ["APV"]})
    cache = FilterCache(max_size=4)
    worker = FilterWorker(
        df,
        [],
        df_hash=FilterWorker._build_df_hash(df),
        cache=cache,
    )
    emit_spy = MagicMock()
    worker.filter_finished.connect(emit_spy)

    with patch.object(worker, "_is_cancelled", side_effect=[False, True]):
        worker.run()

    assert emit_spy.call_count == 0
    assert cache.get(
        worker.df_hash,
        [],
        worker.default_mode,
        cache_context=worker.cache_context,
    ) is None


def test_worker_empty_search_performs_deep_copy_on_miss():
    df = pd.DataFrame({"texto": ["alfa"], "situacao": ["APV"]})
    cache = FilterCache(max_size=4)
    worker = FilterWorker(df, [], df_hash=FilterWorker._build_df_hash(df), cache=cache)
    copy_calls = {"count": 0}
    original_copy = pd.DataFrame.copy

    def _spy_copy(self, *args, **kwargs):
        copy_calls["count"] += 1
        return original_copy(self, *args, **kwargs)

    emitted: list[pd.DataFrame] = []
    worker.filter_finished.connect(lambda frame: emitted.append(frame))

    with patch.object(pd.DataFrame, "copy", _spy_copy):
        worker.run()

    assert len(emitted) == 1
    assert copy_calls["count"] >= 1
    assert emitted[0]["texto"].tolist() == ["alfa"]
    assert emitted[0] is not df
    emitted[0].loc[emitted[0].index[0], "texto"] = "mutated"
    assert df["texto"].tolist() == ["alfa"]


def test_sequential_workers_isolate_cache_by_df_token():
    """H3: second worker with mutated token must not reuse first worker cache entry."""
    df_a = pd.DataFrame({"texto": ["alfa", "omega"]})
    df_b = pd.DataFrame({"texto": ["beta", "gamma"]})
    hash_a = FilterWorker._build_df_hash(df_a)
    hash_b = FilterWorker._build_df_hash(df_b)
    assert hash_a != hash_b

    shared_cache = FilterCache(max_size=8)
    chunks = [["alfa"]]
    worker_a = FilterWorker(df_a, chunks, df_hash=hash_a, cache=shared_cache)
    emitted_a: list[pd.DataFrame] = []
    worker_a.filter_finished.connect(lambda frame: emitted_a.append(frame.copy()))
    worker_a.run()

    worker_b = FilterWorker(df_b, chunks, df_hash=hash_b, cache=shared_cache)
    emitted_b: list[pd.DataFrame] = []
    worker_b.filter_finished.connect(lambda frame: emitted_b.append(frame.copy()))
    worker_b.run()

    assert len(emitted_a) == 1
    assert len(emitted_b) == 1
    assert emitted_a[0]["texto"].tolist() == ["alfa"]
    assert emitted_b[0].empty
    cached_b = shared_cache.get(
        hash_b, chunks, worker_b.default_mode, cache_context=""
    )
    assert cached_b is not None
    assert cached_b.empty
    cached_a = shared_cache.get(
        hash_a, chunks, worker_a.default_mode, cache_context=""
    )
    assert cached_a is not None
    assert cached_a["texto"].tolist() == ["alfa"]


def test_sequential_workers_second_cancel_discards_first_emit():
    """H3: cancelled first worker must not emit even if second worker already ran."""
    df = pd.DataFrame({"texto": ["alfa", "omega"]})
    chunks = [["alfa"]]
    cache = FilterCache(max_size=4)

    worker_first = FilterWorker(
        df,
        chunks,
        df_hash=FilterWorker._build_df_hash(df),
        cache=cache,
    )
    worker_second = FilterWorker(
        df,
        [["omega"]],
        df_hash=FilterWorker._build_df_hash(df),
        cache=cache,
    )
    first_emit = MagicMock()
    second_emit = MagicMock()
    worker_first.filter_finished.connect(first_emit)
    worker_second.filter_finished.connect(second_emit)

    worker_first.cancel()
    worker_first.run()
    worker_second.run()

    assert first_emit.call_count == 0
    first_emit.assert_not_called()
    assert second_emit.call_count == 1
    assert second_emit.call_args[0][0]["texto"].tolist() == ["omega"]
