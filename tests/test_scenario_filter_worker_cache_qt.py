"""Qt scenario tests for filter worker cache synchronization."""

from __future__ import annotations

import pandas as pd

from gui.workers.filter_worker import FilterWorker
from tests._helpers.gui_scenario_harness import GUIFilterScenarioHarness


class TestScenarioFilterWorkerCache(GUIFilterScenarioHarness):
    def setup_method(self):
        super().setup_method()
        cache = getattr(FilterWorker, "_cache", None)
        if hasattr(cache, "clear"):
            cache.clear()

    def test_filter_worker_token_tracks_inplace_mutation(self):
        df = self.base_df.copy()
        first = self.window._build_filter_worker_df_token(df)
        df.loc[0, "descricao_ssa"] = "Mutated"
        second = self.window._build_filter_worker_df_token(df)
        assert second != first

    def test_filter_worker_cache_miss_after_inplace_mutation(self):
        df1 = pd.DataFrame({"texto": ["alfa", "omega"]})
        df2 = pd.DataFrame({"texto": ["beta", "gamma"]})
        chunks = [["alfa"]]
        errors: list[str] = []

        worker_first = FilterWorker(df1, chunks)
        results_first: list[pd.DataFrame] = []
        worker_first.filter_finished.connect(lambda frame: results_first.append(frame.copy()))
        worker_first.error_occurred.connect(errors.append)
        worker_first.run()

        worker_second = FilterWorker(df2, chunks)
        results_second: list[pd.DataFrame] = []
        worker_second.filter_finished.connect(
            lambda frame: results_second.append(frame.copy())
        )
        worker_second.error_occurred.connect(errors.append)
        worker_second.run()

        assert errors == []
        assert len(results_first) == 1
        assert len(results_second) == 1
        assert results_first[0]["texto"].tolist() == ["alfa"]
        assert results_second[0].empty

    def test_window_token_sync_after_df_completo_replace(self):
        replacement = self.base_df.copy()
        replacement.loc[0, "descricao_ssa"] = "Replacement row"
        self.window.df_completo = replacement
        token = self.window._build_filter_worker_df_token(replacement)
        assert token == self.window._build_filter_worker_df_token(self.window.df_completo)
