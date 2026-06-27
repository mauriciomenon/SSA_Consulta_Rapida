"""Qt smoke budget tests for GUI filter refresh path.

Performance-marked tests (RSS/timing budgets) run only with ``-m performance``.
TestScenarioGUIFilterSmokeFunctional covers row-count smoke without perf markers.
"""

from __future__ import annotations

import os
import resource

import pytest
from PyQt6.QtWidgets import QApplication

from tests._helpers.contract_data_builders import (
    BASE_APV_COUNT,
    BASE_APV_SSAS,
    build_large_filter_df,
)
from tests._helpers.gui_scenario_harness import GUIFilterScenarioHarness


class TestScenarioGUIFilterSmokeFunctional(GUIFilterScenarioHarness):
    def test_filter_situacao_apv_row_count(self):
        self.window._active_column_filters["situacao"] = "APV"
        self.window._refresh_after_filter_change()
        QApplication.processEvents()

        assert len(self.window.df_exibido) == BASE_APV_COUNT
        assert set(self.window.df_exibido["numero_ssa"].tolist()) == BASE_APV_SSAS


def _rss_mb() -> float:
    usage = resource.getrusage(resource.RUSAGE_SELF)
    # macOS reports bytes; Linux reports kilobytes.
    if os.uname().sysname == "Darwin":
        return usage.ru_maxrss / (1024 * 1024)
    return usage.ru_maxrss / 1024


@pytest.mark.performance
class TestScenarioGUIFilterSmokeBudget(GUIFilterScenarioHarness):
    def test_filter_refresh_smoke_stays_within_rss_budget(self):
        rss_before = _rss_mb()
        cycles = int(os.environ.get("SSA_GUI_SMOKE_CYCLES", "8"))

        for idx in range(cycles):
            self.window._active_column_filters["situacao"] = "APV" if idx % 2 == 0 else ""
            self.window._exclude_ste_sca = idx % 3 == 0
            self.window._refresh_after_filter_change()
            QApplication.processEvents()

        rss_after = _rss_mb()
        delta = rss_after - rss_before
        limit_mb = float(os.environ.get("SSA_GUI_SMOKE_RSS_LIMIT_MB", "256"))

        assert delta < limit_mb, (
            f"RSS delta {delta:.1f}MB exceeded budget {limit_mb:.1f}MB "
            f"(before={rss_before:.1f} after={rss_after:.1f})"
        )

    def test_filter_refresh_smoke_records_ms_per_stage(self, monkeypatch):
        captured: dict = {}
        original_log = self.window._log_filter_refresh_timings

        def _capture_log(**kwargs):
            captured.update(kwargs)
            return original_log(**kwargs)

        monkeypatch.setattr(self.window, "_log_filter_refresh_timings", _capture_log)
        self.window._active_column_filters["situacao"] = "APV"
        self.window._refresh_after_filter_change()
        QApplication.processEvents()

        timings = captured.get("timings", {})
        assert timings
        expected_stages = (
            "advanced",
            "column",
            "exclude",
            "sort",
            "paginate",
            "render",
            "status",
        )
        for stage in expected_stages:
            assert stage in timings
            assert isinstance(timings[stage], float)
            assert timings[stage] >= 0.0

    def test_filter_refresh_smoke_large_df_rss_ceiling(self, monkeypatch):
        large_df = build_large_filter_df(rows=50_000)
        self.window.df_completo = large_df.copy()
        self.window.df_exibido = large_df.copy()
        self.window._df_last_search_filtered = large_df.copy()
        self.window.paginator.set_dataframe(large_df.copy())

        rss_before = _rss_mb()
        cycles = int(os.environ.get("SSA_GUI_SMOKE_LARGE_CYCLES", "3"))
        captured_timings: list[dict] = []
        original_log = self.window._log_filter_refresh_timings

        def _capture_log(**kwargs):
            timings = kwargs.get("timings")
            if isinstance(timings, dict):
                captured_timings.append(dict(timings))
            return original_log(**kwargs)

        monkeypatch.setattr(self.window, "_log_filter_refresh_timings", _capture_log)

        for idx in range(cycles):
            self.window._active_column_filters["situacao"] = "APV" if idx % 2 == 0 else ""
            self.window._exclude_ste_sca = idx % 2 == 1
            self.window._refresh_after_filter_change()
            QApplication.processEvents()

        rss_after = _rss_mb()
        delta = rss_after - rss_before
        limit_mb = float(os.environ.get("SSA_GUI_SMOKE_LARGE_RSS_LIMIT_MB", "512"))

        assert delta < limit_mb, (
            f"Large-df RSS delta {delta:.1f}MB exceeded budget {limit_mb:.1f}MB "
            f"(before={rss_before:.1f} after={rss_after:.1f})"
        )
        assert captured_timings
        last_timings = captured_timings[-1]
        for stage in ("advanced", "column", "exclude", "sort", "paginate", "render"):
            assert stage in last_timings
            assert last_timings[stage] >= 0.0

    def test_filter_refresh_smoke_large_df_stage_ms_within_budget(self, monkeypatch):
        large_df = build_large_filter_df(rows=50_000)
        self.window.df_completo = large_df.copy()
        self.window.df_exibido = large_df.copy()
        self.window._df_last_search_filtered = large_df.copy()
        self.window.paginator.set_dataframe(large_df.copy())

        captured_timings: list[dict] = []
        original_log = self.window._log_filter_refresh_timings

        def _capture_log(**kwargs):
            timings = kwargs.get("timings")
            if isinstance(timings, dict):
                captured_timings.append(dict(timings))
            return original_log(**kwargs)

        monkeypatch.setattr(self.window, "_log_filter_refresh_timings", _capture_log)

        self.window._active_column_filters["situacao"] = "APV"
        self.window._refresh_after_filter_change()
        QApplication.processEvents()

        stage_limit_ms = float(
            os.environ.get("SSA_GUI_SMOKE_LARGE_STAGE_MS_LIMIT", "60000")
        )
        total_limit_ms = float(
            os.environ.get("SSA_GUI_SMOKE_LARGE_TOTAL_MS_LIMIT", "120000")
        )

        assert captured_timings
        last_timings = captured_timings[-1]
        monitored_stages = (
            "advanced",
            "column",
            "exclude",
            "sort",
            "paginate",
            "render",
            "status",
        )
        for stage in monitored_stages:
            assert stage in last_timings
            assert last_timings[stage] < stage_limit_ms, (
                f"Stage {stage} took {last_timings[stage]:.1f}ms "
                f"(limit {stage_limit_ms:.1f}ms)"
            )

        total_ms = sum(last_timings[stage] for stage in monitored_stages)
        assert total_ms < total_limit_ms, (
            f"Total refresh ms {total_ms:.1f} exceeded budget {total_limit_ms:.1f}"
        )
