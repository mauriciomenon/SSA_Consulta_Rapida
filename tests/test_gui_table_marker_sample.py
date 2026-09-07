"""Regression tests: render marker must distinguish equal-sized pages.

Covers the 2026-09 bug where a swallowed TypeError in
_build_render_marker_sample (fillna("") on nullable numeric columns) produced
an empty marker sample. The empty marker collapsed both the formatted-page
cache key and the render signature, so applying a filter that kept the page at
50 rows reused the stale formatted page and the table never changed.
"""

import os
import sys
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

from gui import gui_ssa  # noqa: E402
from gui.gui_ssa import SSAMainWindow  # noqa: E402
from gui.mixins import filter_gui_ssa_mixin as filter_mixin  # noqa: E402
from gui.ssa import gui_table  # noqa: E402


def _nullable_frame(rows: int, executors: list[str]) -> pd.DataFrame:
    """Frame mimicking production dtypes (numpy_nullable backend).

    The single NA sits near the end but inside the first 50 rows so it is
    present in BOTH the mixed page and the filtered 50-row page - this is
    what made both pages produce an EMPTY marker on the old code.
    """
    na_position = max(0, min(rows - 6, 44))
    week_values = [202628] * rows
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
        self._load_patch.stop()
        filter_worker_registry = self.window._filter_worker_registry
        filter_worker_registry.clear()
        self.window.close()
        self.window.deleteLater()
        QApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
        QApplication.processEvents()
        try:
            gui_ssa.GLOBAL_RETIRED_DATA_LOADER_WORKERS.clear()
        except Exception:
            gui_ssa.GLOBAL_RETIRED_DATA_LOADER_WORKERS[:] = []

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
