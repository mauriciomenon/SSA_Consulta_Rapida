"""Qt scenario tests for filter worker cache synchronization.

GUI wiring for worker cancel/race contracts in
test_contract_filter_worker_cancel_race.py.
"""

from __future__ import annotations

from threading import Event

import pandas as pd
from PyQt6.QtWidgets import QApplication

from gui.workers.filter_worker import FilterWorker
from tests._helpers.contract_data_builders import BASE_APV_SSAS
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

    def test_sync_search_then_inplace_edit_returns_fresh_rows(self):
        FilterWorker.clear_shared_cache()
        self.window._sync_filtering = False

        self.window.search_input.setText("Teste A")
        self.window.initiate_filtering()
        self.wait_until_filter_idle()

        first_count = len(self.window.df_exibido)
        assert first_count == 1
        assert self.window.df_exibido.iloc[0]["descricao_ssa"] == "Teste A"

        self.window.df_completo.loc[4, "descricao_ssa"] = "Teste A secundario"
        self.window.initiate_filtering()
        self.wait_until_filter_idle()

        descriptions = self.window.df_exibido["descricao_ssa"].astype(str).tolist()
        assert set(descriptions) == {"Teste A", "Teste A secundario"}
        assert len(descriptions) == 2
        assert set(self.window.df_exibido["numero_ssa"].tolist()) == BASE_APV_SSAS

    def test_async_inplace_mutation_superseded_by_fresh_token(self, monkeypatch):
        """H3: in-flight worker with stale token must not win over fresh search."""
        FilterWorker.clear_shared_cache()
        self.enable_async_filtering()

        release_slow = Event()
        slow_started = Event()
        original_run = FilterWorker.run
        worker_run_count = {"count": 0}

        def gated_run(worker_self):
            worker_run_count["count"] += 1
            if worker_run_count["count"] == 1:
                slow_started.set()
                release_slow.wait(timeout=5)
            return original_run(worker_self)

        monkeypatch.setattr(FilterWorker, "run", gated_run)

        self.window.search_input.setText("Teste A")
        self.window.initiate_filtering()
        QApplication.processEvents()
        first_request = self.window._active_filter_request_id
        self.wait_until_event(slow_started)

        self.window.df_completo.loc[4, "descricao_ssa"] = "Teste A secundario"
        self.window.search_input.setText("Teste A")
        self.window.initiate_filtering()
        QApplication.processEvents()
        second_request = self.window._active_filter_request_id
        assert second_request > first_request

        self.wait_until_filter_idle()
        descriptions = set(self.extract_visible_descriptions())
        assert descriptions == {"Teste A", "Teste A secundario"}

        release_slow.set()
        self.wait_until_filter_idle()

        assert self.window._active_filter_request_id == second_request
        assert set(self.extract_visible_descriptions()) == {
            "Teste A",
            "Teste A secundario",
        }
