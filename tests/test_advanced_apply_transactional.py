"""Advanced filter apply must restore filter state when refresh fails.

Regression for the 2026-09-03 S2 contract: `_apply_advanced_filters_from_ui`
used to publish new UI/filter state BEFORE the refresh; when the refresh
failed (AdvancedFilterMaskError handled with preserved dataframe), the
checkboxes/chips/summary showed the NEW filter while the table kept the OLD
result. The contract now restores the previous filter state atomically.
"""

import os
import sys
from unittest.mock import patch

import pytest

pytest.importorskip("PyQt6", reason="PyQt6 dependency unavailable in test environment")

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from PyQt6.QtCore import QEvent  # noqa: E402
from PyQt6.QtWidgets import QApplication  # noqa: E402

from gui import gui_ssa  # noqa: E402
from gui.gui_ssa import SSAMainWindow  # noqa: E402
from gui.mixins import filter_gui_ssa_mixin as filter_mixin  # noqa: E402
from gui.ssa import gui_filters_advanced_ui as adv_ui  # noqa: E402


class TestAdvancedApplyTransactional:
    @classmethod
    def setup_class(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setup_method(self):
        self._load_patch = patch.object(SSAMainWindow, "load_data", lambda self: None)
        self._load_patch.start()
        self.window = SSAMainWindow()
        self.window._filter_worker_registry = filter_mixin.DeferredFilterWorkerRegistry()
        self.window.show()
        self.window._advanced_filters = {"setor_executor": ["IEE3"]}
        self.window._advanced_filters_active = True
        self.window._active_column_filters["setor_executor"] = "IEE3"

    def teardown_method(self):
        self._load_patch.stop()
        worker_registry = self.window._filter_worker_registry
        worker_registry.clear()
        self.window.close()
        self.window.deleteLater()
        QApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
        QApplication.processEvents()
        try:
            gui_ssa.GLOBAL_RETIRED_DATA_LOADER_WORKERS.clear()
        except Exception:
            gui_ssa.GLOBAL_RETIRED_DATA_LOADER_WORKERS[:] = []

    def test_apply_restores_state_when_refresh_fails(self, monkeypatch):
        window = self.window
        monkeypatch.setattr(
            adv_ui,
            "_read_advanced_filters_from_ui",
            lambda self, previous: {"setor_executor": ["MEL4"]},
        )
        monkeypatch.setattr(
            window,
            "_refresh_after_filter_change",
            lambda *args, **kwargs: False,
        )

        window._apply_advanced_filters_from_ui()

        assert window._advanced_filters == {"setor_executor": ["IEE3"]}
        assert window._advanced_filters_active is True
        assert window._active_column_filters.get("setor_executor") == "IEE3"
        assert window._filter_cache_context_dirty is True

    def test_apply_keeps_new_state_when_refresh_succeeds(self, monkeypatch):
        window = self.window
        monkeypatch.setattr(
            adv_ui,
            "_read_advanced_filters_from_ui",
            lambda self, previous: {"setor_executor": ["MEL4"]},
        )
        monkeypatch.setattr(
            window,
            "_refresh_after_filter_change",
            lambda *args, **kwargs: True,
        )

        window._apply_advanced_filters_from_ui()

        assert window._advanced_filters == {"setor_executor": ["MEL4"]}
        assert window._active_column_filters.get("setor_executor") == "MEL4"
