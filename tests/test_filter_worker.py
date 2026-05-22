"""Regressões para cache/fingerprint do FilterWorker."""

import os
import sys
from unittest.mock import patch

import pandas as pd
import pytest

pytest.importorskip(
    "PyQt6", reason="Dependência PyQt6 indisponível no ambiente de teste"
)
from PyQt6.QtWidgets import QApplication

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from gui.cache.filter_cache import FilterCache  # noqa: E402
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

    def test_build_df_hash_changes_when_only_middle_rows_change(self):
        base_rows = [{"texto": f"valor_{idx}", "situacao": "APV"} for idx in range(80)]
        df1 = pd.DataFrame(base_rows)
        df2 = df1.copy()
        df2.loc[35, "texto"] = "valor_meio_alterado"

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
        worker_second.filter_finished.connect(
            lambda df: results_second.append(df.copy())
        )
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

    def test_run_uses_injected_cache_instance(self):
        df = pd.DataFrame({"texto": ["alfa", "beta"]})
        injected_cache = FilterCache(max_size=1)
        worker = FilterWorker(df, [["alfa"]], cache=injected_cache)
        emitted = []

        worker.filter_finished.connect(lambda frame: emitted.append(frame))
        worker.run()

        assert len(emitted) == 1
        assert injected_cache.get_stats()["size"] == 1

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

        with patch(
            "gui.workers.filter_worker.filter_dataframe", side_effect=_fake_filter
        ):
            worker.run()

        assert calls["count"] == 1
        assert emitted == []
        assert errors == []

    def test_run_single_chunk_skips_concat_path(self):
        df = pd.DataFrame({"texto": ["alfa", "beta", "gama"]})
        worker = FilterWorker(df, [["alfa"]])
        emitted = []
        errors = []
        filtered_frame = df.iloc[:1].copy()

        worker.filter_finished.connect(lambda frame: emitted.append(frame))
        worker.error_occurred.connect(errors.append)

        with patch(
            "gui.workers.filter_worker.filter_dataframe",
            return_value=filtered_frame,
        ) as filter_mock:
            with patch("gui.workers.filter_worker.pd.concat") as concat_mock:
                worker.run()

        assert errors == []
        assert len(emitted) == 1
        assert emitted[0] is not filtered_frame
        assert emitted[0]["texto"].tolist() == ["alfa"]
        assert filter_mock.call_count == 1
        concat_mock.assert_not_called()

    def test_run_empty_chunk_reuses_full_dataframe_reference(self):
        df = pd.DataFrame({"texto": ["alfa", "beta", "gama"]})
        worker = FilterWorker(df, [[]])
        emitted = []
        errors = []

        worker.filter_finished.connect(lambda frame: emitted.append(frame))
        worker.error_occurred.connect(errors.append)

        worker.run()

        assert errors == []
        assert len(emitted) == 1
        assert emitted[0] is not df
        assert emitted[0]["texto"].tolist() == df["texto"].tolist()

    def test_run_duplicate_chunks_filter_once_per_unique_chunk(self):
        df = pd.DataFrame({"texto": ["alfa", "beta", "gama"]})
        worker = FilterWorker(df, [["alfa"], ["alfa"], ["beta"]])
        emitted = []
        errors = []
        calls = []

        worker.filter_finished.connect(lambda frame: emitted.append(frame))
        worker.error_occurred.connect(errors.append)

        def _fake_filter(_dataframe, parsed, **_kwargs):
            calls.append(tuple(token.get("value") for token in parsed))
            row_indexes = []
            values = {str(token.get("value")) for token in parsed}
            if "alfa" in values:
                row_indexes.append(0)
            if "beta" in values:
                row_indexes.append(1)
            return df.iloc[row_indexes].copy()

        with patch(
            "gui.workers.filter_worker.filter_dataframe",
            side_effect=_fake_filter,
        ):
            worker.run()

        assert errors == []
        assert len(emitted) == 1
        assert calls == [("alfa", "beta")]
        assert emitted[0]["texto"].tolist() == ["alfa", "beta"]

    def test_run_multi_chunk_deduplicates_overlaps_by_original_index(self):
        df = pd.DataFrame({"texto": ["alfa", "beta", "gama"]})
        worker = FilterWorker(df, [["chunk-a"], ["chunk-b"]])
        emitted = []
        errors = []

        worker.filter_finished.connect(lambda frame: emitted.append(frame))
        worker.error_occurred.connect(errors.append)

        def _fake_filter(_dataframe, parsed, **_kwargs):
            values = tuple(token.get("value") for token in parsed)
            if values == ("chunk-a", "chunk-b"):
                return df.copy()
            return df.iloc[0:0].copy()

        with patch(
            "gui.workers.filter_worker.filter_dataframe",
            side_effect=_fake_filter,
        ):
            worker.run()

        assert errors == []
        assert len(emitted) == 1
        assert emitted[0]["texto"].tolist() == ["alfa", "beta", "gama"]
        assert emitted[0].index.tolist() == [0, 1, 2]

    def test_run_multi_chunk_keeps_equal_rows_with_distinct_indexes(self):
        df = pd.DataFrame({"texto": ["igual", "igual", "fim"]})
        worker = FilterWorker(df, [["chunk-a"], ["chunk-b"]])
        emitted = []
        errors = []

        worker.filter_finished.connect(lambda frame: emitted.append(frame))
        worker.error_occurred.connect(errors.append)

        def _fake_filter(_dataframe, parsed, **_kwargs):
            values = tuple(token.get("value") for token in parsed)
            if values == ("chunk-a", "chunk-b"):
                return df.iloc[[0, 1]].copy()
            return df.iloc[0:0].copy()

        with patch(
            "gui.workers.filter_worker.filter_dataframe",
            side_effect=_fake_filter,
        ):
            worker.run()

        assert errors == []
        assert len(emitted) == 1
        assert emitted[0]["texto"].tolist() == ["igual", "igual"]

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

    def test_cache_context_changes_cache_key(self):
        df = pd.DataFrame({"texto": ["alfa", "beta"]})
        errors = []
        calls = {"count": 0}

        def _fake_filter(dataframe, _parsed):
            calls["count"] += 1
            if calls["count"] == 1:
                return dataframe[dataframe["texto"] == "alfa"].copy()
            return dataframe[dataframe["texto"] == "beta"].copy()

        with patch(
            "gui.workers.filter_worker.filter_dataframe", side_effect=_fake_filter
        ):
            first = []
            worker_first = FilterWorker(df, [["x"]], cache_context='{"adv":"A"}')
            worker_first.filter_finished.connect(
                lambda frame: first.append(frame.copy())
            )
            worker_first.error_occurred.connect(errors.append)
            worker_first.run()

            second = []
            worker_second = FilterWorker(df, [["x"]], cache_context='{"adv":"B"}')
            worker_second.filter_finished.connect(
                lambda frame: second.append(frame.copy())
            )
            worker_second.error_occurred.connect(errors.append)
            worker_second.run()

        assert errors == []
        assert calls["count"] == 2
        assert first[0]["texto"].tolist() == ["alfa"]
        assert second[0]["texto"].tolist() == ["beta"]

    def test_cache_context_changes_cache_key_for_real_filter_state_payload(self):
        df = pd.DataFrame({"texto": ["alfa", "beta"]})
        errors = []
        calls = {"count": 0}

        def _fake_filter(dataframe, _parsed):
            calls["count"] += 1
            if calls["count"] == 1:
                return dataframe[dataframe["texto"] == "alfa"].copy()
            return dataframe[dataframe["texto"] == "beta"].copy()

        context_with_column_filter = (
            '{"active_column_filters":{"setor_executor":"MEL4"},'
            '"advanced_filters":{},"advanced_filters_active":false,"exclude_ste_sca":false}'
        )
        context_with_exclude = (
            '{"active_column_filters":{},"advanced_filters":{},'
            '"advanced_filters_active":false,"exclude_ste_sca":true}'
        )

        with patch(
            "gui.workers.filter_worker.filter_dataframe", side_effect=_fake_filter
        ):
            first = []
            worker_first = FilterWorker(
                df,
                [["x"]],
                cache_context=context_with_column_filter,
            )
            worker_first.filter_finished.connect(
                lambda frame: first.append(frame.copy())
            )
            worker_first.error_occurred.connect(errors.append)
            worker_first.run()

            second = []
            worker_second = FilterWorker(
                df,
                [["x"]],
                cache_context=context_with_exclude,
            )
            worker_second.filter_finished.connect(
                lambda frame: second.append(frame.copy())
            )
            worker_second.error_occurred.connect(errors.append)
            worker_second.run()

        assert errors == []
        assert calls["count"] == 2
        assert first[0]["texto"].tolist() == ["alfa"]
        assert second[0]["texto"].tolist() == ["beta"]
