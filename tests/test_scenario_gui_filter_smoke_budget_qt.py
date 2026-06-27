"""Qt smoke budget test for GUI filter refresh path."""

from __future__ import annotations

import os
import resource

import pytest
from PyQt6.QtWidgets import QApplication

from tests._helpers.gui_scenario_harness import GUIFilterScenarioHarness


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
