"""Qt scenario tests for cooperative cancel during async general search.

Uses GUIFilterScenarioHarness.wait_until_event (no time.sleep).
Cross-ref: test_contract_filter_worker_cancel_race.py for worker-level cancel contract.
"""

from __future__ import annotations

from threading import Event

from gui.workers.filter_worker import FilterWorker
from tests._helpers.gui_scenario_harness import GUIFilterScenarioHarness


class TestScenarioFilterCancelMidSearch(GUIFilterScenarioHarness):
    def test_gui_initiated_search_cancel_mid_apply_keeps_display(self, monkeypatch):
        FilterWorker.clear_shared_cache()
        self.enable_async_filtering()

        before = self.snapshot_display_state()
        entered = Event()
        release = Event()
        emitted: list = []
        cancel_observed: list[bool] = []

        import gui.workers.filter_worker as filter_worker_module

        original_apply = filter_worker_module.apply_general_search_terms

        def blocked_search(_df, _chunks, *_, should_cancel=None, **_kwargs):
            entered.set()
            release.wait(timeout=5)
            cancelled = callable(should_cancel) and should_cancel()
            cancel_observed.append(cancelled)
            if cancelled:
                return _df.iloc[[0]].copy()
            return original_apply(
                _df, _chunks, *_, should_cancel=should_cancel, **_kwargs
            )

        monkeypatch.setattr(
            filter_worker_module, "apply_general_search_terms", blocked_search
        )

        self.window.search_input.setText("Teste A")
        self.window.initiate_filtering()
        self.wait_until_event(entered)

        worker = getattr(self.window, "filter_thread", None)
        assert worker is not None
        worker.filter_finished.connect(lambda frame: emitted.append(frame.copy()))
        worker.cancel()
        release.set()
        self.wait_until_filter_idle()

        assert cancel_observed == [True]
        assert emitted == []
        assert len(self.window.df_exibido) == before["count"]
        assert self.extract_visible_ssa() == before["ssa"]
        assert self.extract_visible_descriptions() == before["descriptions"]
