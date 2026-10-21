"""Qt scenario tests for filter race conditions and superseded requests.

GUI wiring for worker cancel/race contracts in
test_contract_filter_worker_cancel_race.py.
"""

from __future__ import annotations

from threading import Event
from unittest.mock import MagicMock

from PyQt6.QtWidgets import QApplication

from gui.workers.filter_worker import FilterWorker
from tests._helpers.gui_scenario_harness import GUIFilterScenarioHarness


class TestScenarioFilterRaceConditions(GUIFilterScenarioHarness):
    _SEARCH_RACE_DESCRIPTIONS = (
        "Alpha item",
        "Beta item",
        "Gamma item",
        "Delta item",
        "Epsilon item",
    )

    def _install_search_race_df(self):
        df = self.base_df.copy()
        df["descricao_ssa"] = list(self._SEARCH_RACE_DESCRIPTIONS)
        return self.bind_window_dataframes(df)

    def test_second_sync_search_supersedes_first_result(self):
        df = self._install_search_race_df()

        self.window.search_input.setText("Alpha")
        self.window.initiate_filtering()
        QApplication.processEvents()
        first_request = self.window._active_filter_request_id

        self.window.search_input.setText("Beta")
        self.window.initiate_filtering()
        QApplication.processEvents()
        second_request = self.window._active_filter_request_id
        assert second_request != first_request
        assert second_request > first_request
        beta_rows = list(self.window.df_exibido["descricao_ssa"])
        beta_snapshot = self.snapshot_display_state()

        stale_single = df.iloc[[4]].copy()
        self.window.on_filter_finished(stale_single, request_id=first_request)
        QApplication.processEvents()

        assert self.window._active_filter_request_id == second_request
        self.assert_display_matches(beta_snapshot)
        assert all("Beta" in row for row in beta_rows)
        assert not any("Alpha" in row for row in beta_rows)

    def test_filter_error_restores_label_of_displayed_result(self):
        self._install_search_race_df()
        self.window.search_input.setText("Alpha")
        self.window.initiate_filtering()
        QApplication.processEvents()
        alpha_rows = list(self.window.df_exibido["descricao_ssa"])

        # Busca "Beta" comeca (rotulo otimista) e falha antes de produzir dados.
        self.window._active_filter_search_display = "Beta"
        self.window.on_filter_error(
            "falha simulada", request_id=self.window._active_filter_request_id
        )
        QApplication.processEvents()

        assert list(self.window.df_exibido["descricao_ssa"]) == alpha_rows
        assert self.window._active_filter_search_display == "Alpha"

    def test_toggle_exclude_ste_during_search_reruns_pending_search(self, monkeypatch):
        self._install_search_race_df()
        self.enable_async_filtering()
        entered = Event()
        release = Event()
        import gui.workers.filter_worker as filter_worker_module

        original_apply = filter_worker_module.apply_general_search_terms
        calls: list[int] = []

        def blocked_search(_df, _chunks, *args, should_cancel=None, **kwargs):
            calls.append(1)
            if len(calls) == 1:
                entered.set()
                release.wait(timeout=5)
            return original_apply(
                _df, _chunks, *args, should_cancel=should_cancel, **kwargs
            )

        monkeypatch.setattr(
            filter_worker_module, "apply_general_search_terms", blocked_search
        )

        self.window.search_input.setText("Beta")
        self.window.initiate_filtering()
        self.wait_until_event(entered)
        self.window._on_exclude_ste_sca_toggled(False)
        release.set()
        self.wait_until_filter_idle()

        rows = list(self.window.df_exibido["descricao_ssa"])
        assert rows and all("Beta" in row for row in rows)

    def test_finished_search_sync_keeps_debounce_of_text_being_typed(self, monkeypatch):
        self._install_search_race_df()
        self.window.search_input.setText("Beta")  # usuario digitando: debounce armado
        self.window._debounce_timer.start()
        monkeypatch.setattr(self.window.search_input, "hasFocus", lambda: True)

        # Busca anterior ("Alpha") termina e sincroniza os campos.
        self.window._sync_search_inputs(
            "Alpha", skip_if_any_focused=True, log_context="teste_g02"
        )

        assert self.window._debounce_timer.isActive()
        assert self.window.search_input.text() == "Beta"

    def test_stale_filter_finished_skips_refresh_pipeline(self, monkeypatch):
        self.window._active_filter_request_id = 10
        refresh_spy = MagicMock()
        monkeypatch.setattr(
            self.window, "_refresh_after_filter_change", refresh_spy
        )
        stale_df = self.base_df.iloc[[0]].copy()
        self.window.on_filter_finished(stale_df, request_id=9)
        QApplication.processEvents()
        assert refresh_spy.call_count == 0
        refresh_spy.assert_not_called()

    def test_stale_filter_error_does_not_mark_ui_error(self, monkeypatch):
        self.window._active_filter_request_id = 20
        ui_state = self.window._filter_ui_state()
        ui_state.set_idle()
        set_error = MagicMock()
        monkeypatch.setattr(ui_state, "set_error", set_error)
        self.window.on_filter_error("stale worker failure", request_id=19)
        QApplication.processEvents()
        assert set_error.call_count == 0
        set_error.assert_not_called()

    def test_abort_active_filtering_increments_request_and_clears_worker_ref(self):
        self.window.filter_thread = MagicMock()
        before = self.window._active_filter_request_id or 0
        new_id = self.window._abort_active_filtering("race-test")
        QApplication.processEvents()
        assert new_id > before
        assert self.window._active_filter_request_id == new_id
        assert self.window.filter_thread is None

    def test_rapid_sync_searches_finish_on_latest_request(self):
        df = self.base_df.copy()
        df["descricao_ssa"] = [f"Term{i}" for i in range(len(df))]
        self.bind_window_dataframes(df)

        request_ids: list[int] = []
        for term in ("Term0", "Term1", "Term2", "Term3", "Term4"):
            self.window.search_input.setText(term)
            self.window.initiate_filtering()
            QApplication.processEvents()
            request_ids.append(self.window._active_filter_request_id)

        assert request_ids == sorted(request_ids)
        assert len(set(request_ids)) == len(request_ids)
        final_request = request_ids[-1]
        assert self.window._active_filter_request_id == final_request
        assert self.window._active_filter_search_display == "Term4"
        assert len(self.window.df_exibido) == 1
        assert self.window.df_exibido.iloc[0]["descricao_ssa"] == "Term4"
        assert all(
            "Term4" in str(description)
            for description in self.extract_visible_descriptions()
        )
        assert "Term0" not in self.extract_visible_descriptions()

        stale_df = df.iloc[[0]].copy()
        self.window.on_filter_finished(stale_df, request_id=request_ids[0])
        QApplication.processEvents()
        assert self.window._active_filter_request_id == final_request
        assert self.window._active_filter_search_display == "Term4"

    def test_async_slow_first_worker_superseded_by_second(self, monkeypatch):
        """H3: blocked first worker must not overwrite second worker display."""
        FilterWorker.clear_shared_cache()
        self.enable_async_filtering()

        df = self._install_search_race_df()

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

        self.window.search_input.setText("Alpha")
        self.window.initiate_filtering()
        QApplication.processEvents()
        first_request = self.window._active_filter_request_id
        self.wait_until_event(slow_started)

        self.window.search_input.setText("Beta")
        self.window.initiate_filtering()
        QApplication.processEvents()
        second_request = self.window._active_filter_request_id
        assert second_request > first_request

        self.wait_until_filter_idle()
        beta_descriptions = self.extract_visible_descriptions()
        beta_snapshot = self.snapshot_display_state()
        assert beta_descriptions == beta_snapshot["descriptions"]
        assert all("Beta" in row for row in beta_descriptions)
        assert not any("Alpha" in row for row in beta_descriptions)

        release_slow.set()
        self.wait_until_filter_idle()

        assert self.window._active_filter_request_id == second_request
        assert self.window._active_filter_search_display == "Beta"
        self.assert_display_matches(beta_snapshot)

        stale_single = df.iloc[[0]].copy()
        self.window.on_filter_finished(stale_single, request_id=first_request)
        QApplication.processEvents()
        self.assert_display_matches(beta_snapshot)
