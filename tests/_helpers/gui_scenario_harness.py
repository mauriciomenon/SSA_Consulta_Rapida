"""Headless Qt harness for filter GUI scenario tests."""

from __future__ import annotations

import copy
import os
import sys
import tempfile
import time
from typing import Any, Literal, TypedDict, cast
from unittest.mock import patch

import pandas as pd
import pytest

pytest.importorskip(
    "PyQt6", reason="Dependencia PyQt6 indisponivel no ambiente de teste"
)

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from PyQt6.QtCore import QTimer  # noqa: E402
from PyQt6.QtTest import QTest  # noqa: E402
from PyQt6.QtWidgets import QApplication  # noqa: E402

from gui import gui_ssa  # noqa: E402
from gui.gui_ssa import SSAMainWindow  # noqa: E402
from gui.mixins import filter_gui_ssa_mixin as filter_mixin  # noqa: E402
from tests._helpers.contract_data_builders import (  # noqa: E402
    build_advanced_filter_contract_df,
    build_base_filter_df,
)


class _RetiredWorkerGlobalsSnapshot(TypedDict):
    data_loader_workers: list[Any]
    data_loader_meta: dict[Any, Any]
    rescan_workers: list[Any]
    rescan_meta: dict[Any, Any]
    filter_workers: list[Any]
    max_data_loader_workers: Literal[64]
    max_rescan_workers: Literal[8]
    max_filter_workers: Literal[64]


class GUIFilterScenarioHarness:
    """Minimal SSAMainWindow setup copied from TestGUIFilterLogic."""

    @classmethod
    def setup_class(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setup_method(self):
        self._ssa_sync_filter_was_set = "SSA_SYNC_FILTER" in os.environ
        self._ssa_sync_filter_snapshot = os.environ.get("SSA_SYNC_FILTER")
        os.environ["SSA_SYNC_FILTER"] = "1"
        self._gui_main_preferences_snapshot = copy.deepcopy(
            gui_ssa.GUI_MAIN_PREFERENCES
        )
        self._retired_worker_globals_snapshot: _RetiredWorkerGlobalsSnapshot = {
            "data_loader_workers": list(gui_ssa.GLOBAL_RETIRED_DATA_LOADER_WORKERS),
            "data_loader_meta": dict(gui_ssa.GLOBAL_RETIRED_DATA_LOADER_META),
            "rescan_workers": list(gui_ssa.GLOBAL_RETIRED_RESCAN_WORKERS),
            "rescan_meta": dict(gui_ssa.GLOBAL_RETIRED_RESCAN_META),
            "filter_workers": [],
            "max_data_loader_workers": gui_ssa.MAX_GLOBAL_RETIRED_DATA_LOADER_WORKERS,
            "max_rescan_workers": gui_ssa.MAX_GLOBAL_RETIRED_RESCAN_WORKERS,
            "max_filter_workers": filter_mixin.MAX_GLOBAL_RETIRED_FILTER_WORKERS,
        }
        gui_ssa.GLOBAL_RETIRED_DATA_LOADER_WORKERS.clear()
        gui_ssa.GLOBAL_RETIRED_DATA_LOADER_META.clear()
        gui_ssa.GLOBAL_RETIRED_RESCAN_WORKERS.clear()
        gui_ssa.GLOBAL_RETIRED_RESCAN_META.clear()
        self._saved_filters_tmpdir = tempfile.TemporaryDirectory()
        self._saved_filters_path = os.path.join(
            self._saved_filters_tmpdir.name, "gui_saved_filters.json"
        )
        self._saved_filters_path_patch = patch.object(
            filter_mixin,
            "get_gui_saved_filters_path",
            lambda: self._saved_filters_path,
        )
        self._saved_filters_path_patch.start()
        self._load_patch = patch.object(SSAMainWindow, "load_data", lambda self: None)
        self._load_patch.start()
        self.window = SSAMainWindow()
        self.window._filter_worker_registry = filter_mixin.DeferredFilterWorkerRegistry()
        self.window.show()

        self.base_df = build_base_filter_df()
        self.window.df_completo = self.base_df.copy()
        self.window.df_exibido = self.base_df.copy()
        self.window._df_last_search_filtered = self.base_df.copy()
        self.window.paginator.set_dataframe(self.base_df.copy())

    def teardown_method(self):
        try:
            self._load_patch.stop()
            self._saved_filters_path_patch.stop()
            for dialog in list(getattr(self.window, "_open_details_dialogs", [])):
                dialog.close()
            self.window.close()
        finally:
            self._saved_filters_tmpdir.cleanup()
            gui_ssa.GUI_MAIN_PREFERENCES.clear()
            gui_ssa.GUI_MAIN_PREFERENCES.update(self._gui_main_preferences_snapshot)
            gui_ssa.GLOBAL_RETIRED_DATA_LOADER_WORKERS[:] = (
                self._retired_worker_globals_snapshot["data_loader_workers"]
            )
            gui_ssa.GLOBAL_RETIRED_DATA_LOADER_META.clear()
            gui_ssa.GLOBAL_RETIRED_DATA_LOADER_META.update(
                self._retired_worker_globals_snapshot["data_loader_meta"]
            )
            gui_ssa.GLOBAL_RETIRED_RESCAN_WORKERS[:] = (
                self._retired_worker_globals_snapshot["rescan_workers"]
            )
            gui_ssa.GLOBAL_RETIRED_RESCAN_META.clear()
            gui_ssa.GLOBAL_RETIRED_RESCAN_META.update(
                self._retired_worker_globals_snapshot["rescan_meta"]
            )
            gui_ssa.MAX_GLOBAL_RETIRED_DATA_LOADER_WORKERS = (
                self._retired_worker_globals_snapshot["max_data_loader_workers"]
            )
            gui_ssa.MAX_GLOBAL_RETIRED_RESCAN_WORKERS = (
                self._retired_worker_globals_snapshot["max_rescan_workers"]
            )
            if self._ssa_sync_filter_was_set:
                os.environ["SSA_SYNC_FILTER"] = str(self._ssa_sync_filter_snapshot)
            else:
                os.environ.pop("SSA_SYNC_FILTER", None)

    def load_advanced_contract_df(self) -> pd.DataFrame:
        df = build_advanced_filter_contract_df()
        self.window.df_completo = df.copy()
        self.window.df_exibido = df.copy()
        self.window._df_last_search_filtered = df.copy()
        self.window.paginator.set_dataframe(df.copy())
        self.window._refresh_advanced_filter_options()
        QApplication.processEvents()
        return df

    def wait_until_timer_inactive(self, timer: QTimer, timeout_ms: int = 1000) -> None:
        deadline = time.monotonic() + (timeout_ms / 1000)
        while timer.isActive() and time.monotonic() < deadline:
            QApplication.processEvents()
            cast(Any, QTest).qWait(10)
        QApplication.processEvents()

    def wait_until_filter_idle(self, timeout_ms: int = 5000) -> None:
        deadline = time.monotonic() + (timeout_ms / 1000)
        while time.monotonic() < deadline:
            QApplication.processEvents()
            if getattr(self.window, "filter_thread", None) is None:
                return
            cast(Any, QTest).qWait(10)
        QApplication.processEvents()

    def extract_visible_ssa(self) -> list:
        return list(self.window.df_exibido["numero_ssa"])

    def extract_visible_descriptions(self) -> list[str]:
        return [
            str(value)
            for value in self.window.df_exibido["descricao_ssa"].astype(str).tolist()
        ]

    def snapshot_display_state(self) -> dict[str, object]:
        return {
            "count": len(self.window.df_exibido),
            "ssa": self.extract_visible_ssa(),
            "descriptions": self.extract_visible_descriptions(),
            "search_display": str(
                getattr(self.window, "_active_filter_search_display", "") or ""
            ),
        }

    def assert_display_matches(self, expected: dict[str, object]) -> None:
        assert len(self.window.df_exibido) == expected["count"]
        assert self.extract_visible_ssa() == expected["ssa"]
        assert self.extract_visible_descriptions() == expected["descriptions"]
        assert (
            str(getattr(self.window, "_active_filter_search_display", "") or "")
            == expected["search_display"]
        )

    def get_adv_exec_vals(self) -> list[str]:
        return list(self.window._adv_values_cache.get("exec_vals") or [])

    def set_filter_panel_tab(self, panel: str) -> dict[str, Any]:
        target_index = 1 if panel in {"filters", "advanced"} else 0
        ctx = self.window._filter_panel_context
        tab_bar = ctx["filter_panel_tab_bar"]
        tab_bar.setCurrentIndex(target_index)
        QApplication.processEvents()
        return ctx

    def toggle_advanced_multiselect_value(
        self,
        *,
        prefix: str,
        value: str,
        exclude: bool = False,
    ):
        checks_attr = f"{prefix}_exclude_checks" if exclude else f"{prefix}_checks"
        checks = getattr(self.window, checks_attr, []) or []
        target = next(
            check for check in checks if str(check.property("value") or "") == value
        )
        target.setChecked(True)
        QApplication.processEvents()
        self.wait_until_timer_inactive(self.window._advanced_apply_timer)
        return target
