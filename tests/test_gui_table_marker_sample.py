"""Regression tests: render marker must distinguish equal-sized pages.

Covers the 2026-09 bug where a swallowed TypeError in
_build_render_marker_sample (fillna("") on nullable numeric columns) produced
an empty marker sample. The empty marker collapsed both the formatted-page
cache key and the render signature, so applying a filter that kept the page at
50 rows reused the stale formatted page and the table never changed.
"""

import os
import sys
from collections import OrderedDict
from threading import Event
from unittest.mock import patch

import pandas as pd
import pytest

pytest.importorskip("PyQt6", reason="PyQt6 dependency unavailable in test environment")

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from PyQt6.QtCore import QEvent  # noqa: E402
from PyQt6.QtWidgets import QApplication  # noqa: E402

from core import search_filter  # noqa: E402
from gui.cache.filter_cache import FilterCache  # noqa: E402
from gui.workers.filter_worker import FilterWorker  # noqa: E402
from gui import gui_ssa  # noqa: E402
from gui.gui_ssa import SSAMainWindow  # noqa: E402
from gui.mixins import filter_gui_ssa_mixin as filter_mixin  # noqa: E402
from gui.ssa import gui_table  # noqa: E402


@pytest.fixture(autouse=True)
def isolated_filter_caches(monkeypatch):
    monkeypatch.setattr(search_filter, "_NORMALIZED_SEARCH_CACHE", OrderedDict())
    monkeypatch.setattr(search_filter, "_NORMALIZED_SEARCH_CACHE_GENERATION", 0)
    monkeypatch.setattr(FilterWorker, "_cache", FilterCache(max_size=50))


def _nullable_frame(rows: int, executors: list[str]) -> pd.DataFrame:
    """Frame mimicking production dtypes (numpy_nullable backend).

    The single NA sits near the end but inside the first 50 rows so it is
    present in BOTH the mixed page and the filtered 50-row page - this is
    what made both pages produce an EMPTY marker on the old code.
    """
    na_position = max(0, min(rows - 6, 44))
    week_values: list[int | None] = [202628] * rows
    week_values[na_position] = None
    return pd.DataFrame(
        {
            "numero_ssa": [202600000 + i for i in range(rows)],
            "situacao": ["APV"] * rows,
            "derivada_de": [""] * rows,
            "localizacao_codigo": [f"L{i}" for i in range(rows)],
            "descricao_localizacao": ["Desc"] * rows,
            "equipamento": ["EQ"] * rows,
            "semana_cadastro": pd.array([202627] * rows, dtype="Int64"),
            "semana_programada": pd.array(week_values, dtype="Int64"),
            "data_cadastro": ["2026-07-01"] * rows,
            "descricao_ssa": [f"Texto {i}" for i in range(rows)],
            "setor_executor": executors,
            "setor_emissor": ["AAA"] * rows,
            "descricao_execucao": [f"Exec {i}" for i in range(rows)],
            "solicitante": [f"User{i}" for i in range(rows)],
        }
    )


def _table_column_index(window, header_fragment: str) -> int:
    table = window.table_widget
    for index in range(table.columnCount()):
        item = table.horizontalHeaderItem(index)
        if item is not None and header_fragment in item.text():
            return index
    raise AssertionError(f"column with header '{header_fragment}' not found")


class TestRenderMarkerSample:
    def test_digest_includes_categorical_dtype_metadata(self):
        frame = pd.DataFrame({"value": pd.Categorical(["a"], categories=["a", "b"])})
        changed = pd.DataFrame({"value": pd.Categorical(["a"], categories=["a", "c"])})
        assert gui_table._build_page_content_digest(frame) != gui_table._build_page_content_digest(changed)

    @pytest.mark.parametrize("change", ["index", "dtype", "columns", "order", "cell"])
    def test_digest_covers_full_frame_contract(self, change):
        frame = pd.DataFrame({"left": range(500), "right": range(500)})
        changed = frame.copy()
        if change == "index":
            changed.index = range(1, 501)
        elif change == "dtype":
            changed = changed.astype("Int64")
        elif change == "columns":
            changed.columns = ["left|right", ""]
        elif change == "order":
            changed = changed.iloc[::-1]
        else:
            changed.iloc[321, 1] = 987654
        assert gui_table._build_page_content_digest(frame) != gui_table._build_page_content_digest(changed)

    def test_responsavel_fingerprint_failure_never_reuses_shape(self, monkeypatch):
        from gui.ssa.filter_domain_rules import generate_responsavel_sector_filter_cache_signature

        def fail_hash(*args, **kwargs):
            raise TypeError("unsupported value")

        monkeypatch.setattr(pd.util, "hash_pandas_object", fail_hash)
        frame = pd.DataFrame({"solicitante": ["A"]})
        first = generate_responsavel_sector_filter_cache_signature(frame, data_load_token=None)
        frame.loc[0, "solicitante"] = "B"
        second = generate_responsavel_sector_filter_cache_signature(frame, data_load_token=None)
        assert first != second

    def test_marker_non_empty_and_content_sensitive_with_nullable_numbers(self):
        frame = _nullable_frame(3, ["IEE3", "MEL4", "XYZ"])
        marker = gui_table._build_render_marker_sample(frame)
        assert marker, "marker sample must not be empty for nullable numeric frames"

        changed = frame.copy()
        changed.loc[0, "descricao_ssa"] = "Outro texto"
        assert gui_table._build_render_marker_sample(changed) != marker

    def test_marker_covers_all_rows_for_large_frames(self):
        frame = _nullable_frame(120, ["IEE3"] * 120)
        marker = gui_table._build_render_marker_sample(frame)
        assert len(marker) == 120, "S8: marker covers ALL rows, not a sample"


class TestEqualSizedPageRender:
    @classmethod
    def setup_class(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setup_method(self):
        self._retired_workers_patch = patch.object(
            gui_ssa, "GLOBAL_RETIRED_DATA_LOADER_WORKERS", []
        )
        self._retired_workers_patch.start()
        self._load_patch = patch.object(SSAMainWindow, "load_data", lambda self: None)
        self._load_patch.start()
        self.window = SSAMainWindow()
        self.window._data_uuid = "marker-regression-test"
        self.window._filter_worker_registry = filter_mixin.DeferredFilterWorkerRegistry()
        self.window.show()
        executors = ["IEE3"] * 50 + ["MEL4"] * 5 + ["MMU2"] * 5
        self.mixed_df = (
            _nullable_frame(60, executors)
            .sort_values("numero_ssa", ascending=False)
            .reset_index(drop=True)
        )

    def teardown_method(self):
        try:
            filter_worker_registry = self.window._filter_worker_registry
            filter_worker_registry.clear()
            self.window.close()
            self.window.deleteLater()
            QApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
            QApplication.processEvents()
        finally:
            self._load_patch.stop()
            self._retired_workers_patch.stop()

    def test_blank_search_rejects_previous_callback_and_restores_undo(self):
        self._set_search_baseline()
        window = self.window
        window._sync_filtering = True
        target = str(self.mixed_df.iloc[0]["numero_ssa"])
        window.search_input.setText(f"={target}")
        window.initiate_filtering()
        previous_request = window._active_filter_request_id
        previous_result = window._df_last_search_filtered.copy()
        assert len(previous_result) == 1

        window.search_input.clear()
        window._debounce_timer.start(10000)
        window.initiate_filtering()
        assert not window._debounce_timer.isActive()
        assert window._active_filter_request_id != previous_request
        assert window._df_last_search_filtered is window.df_completo
        window.on_filter_finished(previous_result, request_id=previous_request)
        assert window._df_last_search_filtered is window.df_completo

        window._restore_last_filter_state()
        assert window.search_input.text() == f"={target}"
        assert len(window.df_exibido) == 1

    def test_data_revision_releases_all_retained_filter_owners(self):
        self._set_search_baseline()
        window = self.window
        retained = self.mixed_df.copy()
        window._filter_refresh_result_cache = retained
        window._column_filter_series_cache = {"old": retained["descricao_ssa"]}
        window._adv_str_cache = {"old": retained["descricao_ssa"]}
        window.cache_manager.cache_formatted_df("old", retained)
        search_filter._NORMALIZED_SEARCH_CACHE[("old",)] = {"columns": retained}

        window._bump_data_revision("release_owner_regression")

        assert window._filter_refresh_result_cache is None
        assert not window._column_filter_series_cache
        assert not window._adv_str_cache
        assert window.cache_manager.get_cached_formatted_df("old") is None
        assert not search_filter._NORMALIZED_SEARCH_CACHE

    def test_blank_search_cancels_running_worker_before_late_result(self, monkeypatch):
        from gui.workers import filter_worker

        self._set_search_baseline()
        window = self.window
        entered, release = Event(), Event()
        filter_worker.FilterWorker.clear_shared_cache()

        def delayed_search(frame, *args, **kwargs):
            entered.set()
            assert release.wait(3), "test did not release blocked worker"
            return frame.iloc[:1]

        monkeypatch.setattr(filter_worker, "apply_general_search_terms", delayed_search)
        window._sync_filtering = False
        window.search_input.setText("Texto")
        window.initiate_filtering()
        worker = window.filter_thread
        try:
            assert entered.wait(3), "worker did not enter search"
            window.search_input.clear()
            window.initiate_filtering()
            assert worker.isInterruptionRequested()
        finally:
            release.set()
            assert worker.wait(3000), "worker did not stop"
        QApplication.processEvents()
        assert window._df_last_search_filtered is window.df_completo
        assert len(window.df_exibido) == len(self.mixed_df)

    def test_refresh_without_cache_candidate_drops_previous_result(self):
        self._set_search_baseline()
        window = self.window
        window._filter_refresh_result_cache = self.mixed_df.copy()
        result = window._apply_filter_refresh_filters_and_update_cache(
            window.df_completo,
            has_post_search_filters=False,
            has_excluded_terminal_status=False,
            measure_timing=lambda name, operation: operation(),
        )
        assert result is window.df_completo
        assert window._filter_refresh_result_cache is None

    def _set_search_baseline(self) -> None:
        self.window.df_completo = self.mixed_df.copy()
        self.window.df_exibido = self.mixed_df.copy()
        self.window._df_last_search_filtered = self.mixed_df.copy()
        self.window.paginator.page_size = 50
        self.window.paginator.set_dataframe(self.mixed_df.copy())

    def _render_initial_page(self) -> str:
        gui_table.display_current_page(self.window, 1)
        item = self.window.table_widget.item(0, 1)
        assert item is not None
        return item.text()

    def _executor_values_on_table(self) -> set[str]:
        col = _table_column_index(self.window, "Set. Exec")
        table = self.window.table_widget
        return {
            table.item(row, col).text() for row in range(table.rowCount())
        }

    def test_display_rebuilds_equal_sized_page_with_stable_revision(self):
        self._set_search_baseline()
        first_before = self._render_initial_page()

        filtered = (
            self.mixed_df[self.mixed_df["setor_executor"] == "IEE3"]
            .reset_index(drop=True)
        )
        assert len(filtered) == 50
        self.window.df_exibido = filtered
        self.window._df_last_search_filtered = filtered
        self.window.paginator.set_dataframe(filtered)

        gui_table.display_current_page(self.window, 1)

        assert self.window.table_widget.rowCount() == 50
        first_after = self.window.table_widget.item(0, 1).text()
        assert first_after != first_before, "table kept stale first row"
        assert self._executor_values_on_table() == {"IEE3"}

    def test_executor_filter_refresh_rebuilds_table_through_pipeline(self):
        self._set_search_baseline()
        self._render_initial_page()

        self.window._advanced_filters = {"setor_executor": ["IEE3"]}
        self.window._advanced_filters_active = True
        self.window._refresh_after_filter_change()

        assert len(self.window.df_exibido) == 50
        assert self.window.table_widget.rowCount() == 50
        assert self._executor_values_on_table() == {"IEE3"}
