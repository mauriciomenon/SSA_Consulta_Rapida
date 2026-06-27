"""Contract tests for FilterWorker cancel/race edges."""

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
    worker.filter_finished.connect(emit_spy)

    with patch.object(worker, "_is_cancelled", side_effect=[False, True]):
        with patch(
            "gui.workers.filter_worker.apply_general_search_terms"
        ) as heavy_search:
            worker.run()

    assert emit_spy.call_count == 0
    heavy_search.assert_not_called()


def test_worker_cancel_after_cache_hit_does_not_emit_error():
    df = pd.DataFrame({"texto": ["alfa", "beta"], "situacao": ["APV", "STE"]})
    cache = FilterCache(max_size=4)
    cache.put("hash-a", [["alfa"]], "contains", df.iloc[[0]].copy(), cache_context="")

    worker = FilterWorker(
        df,
        [["alfa"]],
        df_hash="hash-a",
        cache=cache,
    )
    error_spy = MagicMock()
    worker.error_occurred.connect(error_spy)

    with patch.object(worker, "_is_cancelled", side_effect=[False, True]):
        worker.run()

    assert error_spy.call_count == 0


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
