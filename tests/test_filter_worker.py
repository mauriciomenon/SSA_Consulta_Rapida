"""Regressões para cache/fingerprint do FilterWorker."""

import os
import sys
from unittest.mock import patch

import pandas as pd
import pytest

pytest.importorskip("PyQt6", reason="Dependência PyQt6 indisponível no ambiente de teste")
from PyQt6.QtWidgets import QApplication

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from gui.workers.filter_worker import FilterWorker  # noqa: E402


@pytest.fixture(scope="module", autouse=True)
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


class TestFilterWorker:
    def setup_method(self):
        cache = getattr(FilterWorker, "_cache", None)
        if hasattr(cache, "clear"):
            cache.clear()

    def test_build_df_hash_is_stable_for_same_content(self):
        df = pd.DataFrame({"texto": ["alfa", "beta"], "situacao": ["APV", "STE"]})

        hash1 = FilterWorker._build_df_hash(df)
        hash2 = FilterWorker._build_df_hash(df.copy())

        assert hash1 == hash2

    def test_build_df_hash_changes_for_same_shape_different_content(self):
        df1 = pd.DataFrame({"texto": ["alfa", "omega"]})
        df2 = pd.DataFrame({"texto": ["beta", "gamma"]})

        hash1 = FilterWorker._build_df_hash(df1)
        hash2 = FilterWorker._build_df_hash(df2)

        assert hash1 != hash2

    def test_cache_does_not_reuse_result_for_different_df_same_shape(self):
        df1 = pd.DataFrame({"texto": ["alfa", "omega"]})
        df2 = pd.DataFrame({"texto": ["beta", "gamma"]})
        chunks = [["alfa"]]
        errors = []

        results_first = []
        worker_first = FilterWorker(df1, chunks)
        worker_first.filter_finished.connect(lambda df: results_first.append(df.copy()))
        worker_first.error_occurred.connect(errors.append)
        worker_first.run()

        results_second = []
        worker_second = FilterWorker(df2, chunks)
        worker_second.filter_finished.connect(lambda df: results_second.append(df.copy()))
        worker_second.error_occurred.connect(errors.append)
        worker_second.run()

        assert errors == []
        assert len(results_first) == 1
        assert len(results_second) == 1
        assert results_first[0]["texto"].tolist() == ["alfa"]
        assert results_second[0].empty is True

    def test_run_honors_interruption_before_processing(self):
        df = pd.DataFrame({"texto": ["alfa", "beta"]})
        worker = FilterWorker(df, [["alfa"]])
        emitted = []
        errors = []
        worker.filter_finished.connect(lambda frame: emitted.append(frame))
        worker.error_occurred.connect(errors.append)

        worker.cancel()
        with patch("gui.workers.filter_worker.filter_dataframe") as filter_mock:
            worker.run()

        assert emitted == []
        assert errors == []
        filter_mock.assert_not_called()

    def test_run_stops_between_chunks_when_interrupted(self):
        df = pd.DataFrame({"texto": ["alfa", "beta", "gama"]})
        worker = FilterWorker(df, [["alfa"], ["beta"]])
        emitted = []
        errors = []
        calls = {"count": 0}

        def _fake_filter(dataframe, _parsed):
            calls["count"] += 1
            if calls["count"] == 1:
                worker.cancel()
            return dataframe.iloc[:1].copy()

        worker.filter_finished.connect(lambda frame: emitted.append(frame))
        worker.error_occurred.connect(errors.append)

        with patch("gui.workers.filter_worker.filter_dataframe", side_effect=_fake_filter):
            worker.run()

        assert calls["count"] == 1
        assert emitted == []
        assert errors == []

    def test_run_emits_empty_result_when_df_is_none(self):
        worker = FilterWorker(None, [["alfa"]])
        emitted = []
        errors = []
        worker.filter_finished.connect(lambda frame: emitted.append(frame))
        worker.error_occurred.connect(errors.append)

        worker.run()

        assert len(emitted) == 1
        assert emitted[0].empty
        assert errors == []
