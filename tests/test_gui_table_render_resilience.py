"""Regression tests for gui table render resilience."""

import logging
import os
import sys
from unittest.mock import patch

import pandas as pd
import pytest

pytest.importorskip("PyQt6", reason="PyQt6 dependency unavailable in test environment")

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from PyQt6.QtWidgets import QApplication  # noqa: E402

from gui import gui_ssa  # noqa: E402
from gui.gui_ssa import SSAMainWindow  # noqa: E402
from gui.mixins import filter_gui_ssa_mixin as filter_mixin  # noqa: E402
from gui.ssa import gui_details as ssa_gui_details  # noqa: E402
from gui.ssa import gui_table  # noqa: E402
from utils.formatting import format_dataframe_for_display  # noqa: E402


def _expected_visible_columns(window, dataframe: pd.DataFrame) -> list[str]:
    return [column for column in window.visible_columns if column in dataframe.columns]


class TestGUITableRenderResilience:
    @classmethod
    def setup_class(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setup_method(self):
        self._load_patch = patch.object(SSAMainWindow, "load_data", lambda self: None)
        self._load_patch.start()
        self.window = SSAMainWindow()
        self.window._filter_worker_registry = filter_mixin.DeferredFilterWorkerRegistry()
        self.window.show()

        self.base_df = pd.DataFrame(
            {
                "numero_ssa": [1, 2, 3],
                "situacao": ["APV", "STE", "AMP"],
                "derivada_de": ["", "", ""],
                "localizacao_codigo": ["LOC1", "LOC2", "LOC3"],
                "descricao_localizacao": ["Desc"] * 3,
                "equipamento": ["EQ1"] * 3,
                "semana_cadastro": [202501, 202501, 202501],
                "semana_programada": [202503, 202503, 202503],
                "data_cadastro": ["2025-01-01", "2025-01-01", "2025-01-01"],
                "descricao_ssa": ["Teste A", "Teste B", "Teste C"],
                "setor_executor": ["IEE3", "MEL4", "XYZ"],
                "setor_emissor": ["ABC", "MEL4", "XYZ"],
                "descricao_execucao": ["Exec A", "Exec B", "Exec C"],
                "solicitante": ["User1", "User2", "User3"],
            }
        )

        self._set_window_dataframe(self.base_df.copy(), page_size=10)

    def _set_window_dataframe(self, dataframe: pd.DataFrame, *, page_size: int) -> None:
        self.window.df_completo = dataframe.copy()
        self.window.df_exibido = dataframe.copy()
        self.window._df_last_search_filtered = dataframe.copy()
        self.window.paginator.page_size = page_size
        self.window.paginator.set_dataframe(dataframe.copy())

    def _build_preserve_details_df(self) -> pd.DataFrame:
        extra_rows = self.base_df.iloc[:2].copy().reset_index(drop=True)
        preserve_df = pd.concat([self.base_df.copy(), extra_rows], ignore_index=True)
        preserve_df.loc[:, "numero_ssa"] = [
            202500001,
            202500002,
            202500003,
            202500004,
            202500005,
        ]
        preserve_df.loc[:, "situacao"] = ["APV", "STE", "AMP", "APV", "APV"]
        preserve_df.loc[:, "descricao_ssa"] = [
            "Teste A",
            "Teste B",
            "Teste C",
            "Teste D",
            "Teste E",
        ]
        preserve_df.loc[:, "localizacao_codigo"] = ["L1", "L2", "L3", "L4", "L5"]
        preserve_df.loc[:, "descricao_localizacao"] = ["D1", "D2", "D3", "D4", "D5"]
        preserve_df.loc[:, "equipamento"] = ["E1", "E2", "E3", "E4", "E5"]
        preserve_df.loc[:, "setor_executor"] = ["IEE3", "MEL4", "XYZ", "ABC", "DEF"]
        preserve_df.loc[:, "setor_emissor"] = ["AAA", "BBB", "CCC", "DDD", "EEE"]
        preserve_df.loc[:, "descricao_execucao"] = [
            "Exec A",
            "Exec B",
            "Exec C",
            "Exec D",
            "Exec E",
        ]
        preserve_df.loc[:, "solicitante"] = [
            "User1",
            "User2",
            "User3",
            "User4",
            "User5",
        ]
        return preserve_df

    def teardown_method(self):
        self._load_patch.stop()
        self.window.close()
        try:
            gui_ssa.GLOBAL_RETIRED_DATA_LOADER_WORKERS.clear()
        except Exception:
            gui_ssa.GLOBAL_RETIRED_DATA_LOADER_WORKERS[:] = []
        try:
            self.window._filter_worker_registry.clear()
        except Exception:
            self.window._filter_worker_registry = filter_mixin.DeferredFilterWorkerRegistry()

    def test_display_current_page_continues_when_first_cell_item_creation_fails(self):
        from gui.ssa import gui_table

        original_qtable_item = gui_table.QTableWidgetItem
        calls = {"count": 0}

        def flaky_qtable_item(text):
            calls["count"] += 1
            if calls["count"] == 1:
                raise RuntimeError("forced cell construction failure")
            return original_qtable_item(text)

        with patch("gui.ssa.gui_table.QTableWidgetItem", side_effect=flaky_qtable_item):
            with patch(
                "gui.ssa.gui_table._render_signature_and_reuse",
                return_value=(object(), False),
            ):
                self.window.table_widget.setRowCount(0)
                self.window.display_current_page(1)
                QApplication.processEvents()

        assert calls["count"] > 1
        assert self.window.table_widget.rowCount() == len(self.base_df)
        assert self.window.table_widget.item(0, 0) is not None
        assert self.window.table_widget.item(0, 0).text() == ""

    def test_display_current_page_skips_redundant_detail_refresh_for_same_signature(
        self,
    ):
        with patch.object(
            ssa_gui_details,
            "_update_details_from_series",
            wraps=ssa_gui_details._update_details_from_series,
        ) as update_details:
            self.window.display_current_page(1)
            QApplication.processEvents()
            first_call_count = update_details.call_count
            initial_ssa = self.window._details_current_ssa
            self.window.display_current_page(1)
            QApplication.processEvents()

        assert update_details.call_count == first_call_count
        assert self.window._details_current_ssa == initial_ssa

    def test_display_current_page_refreshes_details_when_search_terms_change(self):
        with patch.object(
            ssa_gui_details,
            "_update_details_from_series",
            wraps=ssa_gui_details._update_details_from_series,
        ) as update_details:
            self.window.display_current_page(1)
            QApplication.processEvents()
            first_call_count = update_details.call_count
            self.window.search_input.setText("Teste A")
            self.window.display_current_page(1)
            QApplication.processEvents()

        assert update_details.call_count > first_call_count
        assert self.window._details_current_ssa == 1
        assert "Teste A" in str(self.window.details_text.toHtml() or "")

    def test_display_current_page_rebuilds_when_page_changes(self):
        extra_rows = self.base_df.iloc[:2].copy()
        extra_rows.loc[:, "numero_ssa"] = [4, 5]
        extra_rows.loc[:, "situacao"] = ["NOV", "NOV"]
        extra_rows.loc[:, "localizacao_codigo"] = ["LOC4", "LOC5"]
        extra_rows.loc[:, "descricao_ssa"] = ["Teste D", "Teste E"]
        extra_rows.loc[:, "setor_executor"] = ["MEL4", "MEL4"]
        extra_rows.loc[:, "descricao_execucao"] = ["Exec D", "Exec E"]
        extra_rows.loc[:, "solicitante"] = ["User4", "User5"]
        paged_df = pd.concat([self.base_df, extra_rows], ignore_index=True)
        self._set_window_dataframe(paged_df, page_size=2)

        with patch.object(
            ssa_gui_details,
            "_update_details_from_series",
            wraps=ssa_gui_details._update_details_from_series,
        ) as update_details:
            self.window.display_current_page(1)
            QApplication.processEvents()
            first_call_count = update_details.call_count
            self.window.display_current_page(2)
            QApplication.processEvents()

        expected_page = format_dataframe_for_display(
            paged_df.iloc[2:4][_expected_visible_columns(self.window, paged_df)].copy()
        )
        assert update_details.call_count > first_call_count
        assert self.window._details_current_ssa == 3
        assert self.window.table_widget.rowCount() == 2
        numero_ssa_col = self.window._current_display_columns.index("numero_ssa")
        assert (
            self.window.table_widget.item(0, numero_ssa_col).text()
            == expected_page.iloc[0]["numero_ssa"]
        )

    def test_display_current_page_restores_widget_batch_state_after_render(self):
        header = self.window.table_widget.horizontalHeader()
        self.window.table_widget.setSortingEnabled(True)
        self.window.table_widget.blockSignals(False)
        header.blockSignals(False)

        self.window.display_current_page(1)
        QApplication.processEvents()

        assert self.window.table_widget.isSortingEnabled() is True
        assert self.window.table_widget.signalsBlocked() is False
        assert header.signalsBlocked() is False
        assert self.window.table_widget.updatesEnabled() is True
        assert header.updatesEnabled() is True

    def test_display_current_page_updates_details_without_forcing_selection(self):
        self.window.display_current_page(1)
        QApplication.processEvents()

        assert self.window.table_widget.selectionModel().selectedRows() == []
        assert self.window._details_current_ssa == 1
        details_html = str(self.window.details_text.toHtml() or "")
        assert "Teste A" in details_html

    def test_manual_row_selection_updates_details_to_selected_row(self):
        self.window.display_current_page(1)
        QApplication.processEvents()

        self.window.table_widget.selectRow(1)
        QApplication.processEvents()

        assert [
            idx.row()
            for idx in self.window.table_widget.selectionModel().selectedRows()
        ] == [1]
        assert self.window._details_current_ssa == 2
        assert "Teste B" in str(self.window.details_text.toHtml() or "")

    def test_manual_selection_clear_clears_details(self):
        self.window.display_current_page(1)
        QApplication.processEvents()
        self.window.table_widget.selectRow(1)
        QApplication.processEvents()

        self.window.table_widget.clearSelection()
        QApplication.processEvents()

        assert self.window.table_widget.selectionModel().selectedRows() == []
        assert self.window._details_current_ssa is None
        assert self.window.details_text.toPlainText().strip() == ""

    def test_display_current_page_can_skip_initial_details_update(self):
        self.window._details_current_ssa = None
        self.window.details_text.clear()

        with patch.object(
            ssa_gui_details,
            "_update_details_from_series",
            wraps=ssa_gui_details._update_details_from_series,
        ) as update_details:
            self.window.display_current_page(1, update_details=False)
            QApplication.processEvents()

        assert update_details.call_count == 0
        assert self.window.table_widget.rowCount() == len(self.base_df)
        assert self.window._details_current_ssa is None

    def test_display_current_page_update_details_false_preserves_existing_details(self):
        self.window.display_current_page(1)
        QApplication.processEvents()
        initial_html = str(self.window.details_text.toHtml() or "")
        initial_ssa = self.window._details_current_ssa

        paged_df = pd.concat(
            [self.base_df, self.base_df.iloc[:2].copy()], ignore_index=True
        )
        paged_df.loc[3:, "numero_ssa"] = [44, 55]
        paged_df.loc[3:, "descricao_ssa"] = ["Outro D", "Outro E"]
        self._set_window_dataframe(paged_df, page_size=2)

        self.window.display_current_page(2, update_details=False)
        QApplication.processEvents()

        expected_page = format_dataframe_for_display(
            paged_df.iloc[2:4][_expected_visible_columns(self.window, paged_df)].copy()
        )
        numero_ssa_col = self.window._current_display_columns.index("numero_ssa")
        assert (
            self.window.table_widget.item(0, numero_ssa_col).text()
            == expected_page.iloc[0]["numero_ssa"]
        )
        assert self.window._details_current_ssa == initial_ssa
        assert str(self.window.details_text.toHtml() or "") == initial_html

    def test_page_change_with_existing_selection_keeps_new_page_details(self):
        paged_df = self._build_preserve_details_df()
        self._set_window_dataframe(paged_df, page_size=2)

        self.window.display_current_page(1)
        QApplication.processEvents()
        self.window.table_widget.selectRow(1)
        QApplication.processEvents()

        assert self.window._details_current_ssa == 202500002
        assert "Teste B" in str(self.window.details_text.toHtml() or "")

        self.window.display_current_page(2)
        QApplication.processEvents()
        QApplication.processEvents()

        assert self.window.table_widget.selectionModel().selectedRows() == []
        assert self.window._details_current_ssa == 202500003
        details_html = str(self.window.details_text.toHtml() or "")
        assert "Teste C" in details_html
        assert "Teste B" not in details_html

    def test_on_columns_changed_preserves_existing_details(self):
        self.window.display_current_page(1)
        QApplication.processEvents()
        initial_html = str(self.window.details_text.toHtml() or "")
        initial_ssa = self.window._details_current_ssa

        reordered_columns = ["situacao"] + [
            col for col in self.window.visible_columns if col != "situacao"
        ]

        with patch.object(
            ssa_gui_details,
            "_update_details_from_series",
            wraps=ssa_gui_details._update_details_from_series,
        ) as update_details:
            self.window.on_columns_changed(reordered_columns)
            QApplication.processEvents()

        assert self.window.visible_columns[0] == "situacao"
        assert update_details.call_count == 0
        assert self.window._details_current_ssa == initial_ssa
        assert str(self.window.details_text.toHtml() or "") == initial_html

    def test_header_reorder_preserves_existing_details(self):
        self.window.display_current_page(1)
        QApplication.processEvents()
        initial_html = str(self.window.details_text.toHtml() or "")
        initial_ssa = self.window._details_current_ssa

        if "solicitante" not in self.window.visible_columns:
            self.window.visible_columns.append("solicitante")
        self.window.display_current_page(1)
        QApplication.processEvents()

        header = self.window.table_widget.horizontalHeader()
        situacao_logical_index = self.window._current_display_columns.index("situacao")

        with patch.object(
            ssa_gui_details,
            "_update_details_from_series",
            wraps=ssa_gui_details._update_details_from_series,
        ) as update_details:
            header.moveSection(header.visualIndex(situacao_logical_index), 1)
            QApplication.processEvents()

        assert self.window.visible_columns[0] == "situacao"
        assert update_details.call_count == 0
        assert self.window._details_current_ssa == initial_ssa
        assert str(self.window.details_text.toHtml() or "") == initial_html

    def test_sort_preserves_existing_details(self):
        sortable_df = self.base_df.copy()
        sortable_df.loc[:, "numero_ssa"] = [3, 1, 2]
        sortable_df.loc[:, "descricao_ssa"] = ["Teste C", "Teste A", "Teste B"]
        self._set_window_dataframe(sortable_df, page_size=10)

        self.window.display_current_page(1)
        QApplication.processEvents()
        initial_html = str(self.window.details_text.toHtml() or "")
        initial_ssa = self.window._details_current_ssa
        logical_index = self.window._current_display_columns.index("numero_ssa")

        with patch.object(
            ssa_gui_details,
            "_update_details_from_series",
            wraps=ssa_gui_details._update_details_from_series,
        ) as update_details:
            self.window.on_header_clicked(logical_index)
            QApplication.processEvents()

        assert self.window.df_exibido["numero_ssa"].tolist() == [1, 2, 3]
        assert update_details.call_count == 0
        assert self.window._details_current_ssa == initial_ssa
        assert str(self.window.details_text.toHtml() or "") == initial_html

    def test_filter_refresh_preserves_current_details_when_ssa_remains_visible(self):
        preserve_df = self._build_preserve_details_df()
        self._set_window_dataframe(preserve_df, page_size=10)

        self.window.display_current_page(1)
        QApplication.processEvents()
        self.window._jump_to_ssa("202500004")
        QApplication.processEvents()
        QApplication.processEvents()
        initial_ssa = self.window._details_current_ssa

        self.window._active_column_filters = {"situacao": "APV"}
        self.window._refresh_after_filter_change()
        QApplication.processEvents()

        assert self.window.df_exibido["numero_ssa"].tolist() == [
            202500005,
            202500004,
            202500001,
        ]
        assert self.window._details_current_ssa == initial_ssa
        assert "Teste D" in str(self.window.details_text.toHtml() or "")

    def test_filter_refresh_updates_details_when_current_ssa_leaves_result(self):
        preserve_df = self._build_preserve_details_df()
        self._set_window_dataframe(preserve_df, page_size=10)

        self.window.display_current_page(1)
        QApplication.processEvents()
        self.window._jump_to_ssa("202500004")
        QApplication.processEvents()
        QApplication.processEvents()

        self.window._active_column_filters = {"descricao_ssa": "Teste C"}
        self.window._refresh_after_filter_change()
        QApplication.processEvents()

        assert self.window.df_exibido["numero_ssa"].tolist() == [202500003]
        assert self.window._details_current_ssa == 202500003
        assert "Teste C" in str(self.window.details_text.toHtml() or "")

    def test_table_cell_alignment_change_preserves_existing_details(self):
        preserve_df = self._build_preserve_details_df()
        self._set_window_dataframe(preserve_df, page_size=10)

        self.window.display_current_page(1)
        QApplication.processEvents()
        self.window._jump_to_ssa("202500004")
        QApplication.processEvents()
        QApplication.processEvents()
        initial_ssa = self.window._details_current_ssa
        initial_html = str(self.window.details_text.toHtml() or "")
        gui_settings = gui_ssa.GUI_MAIN_PREFERENCES.setdefault("gui_settings", {})
        previous_alignment = gui_settings.get("table_cell_alignment")

        try:
            with patch.object(
                ssa_gui_details,
                "_update_details_from_series",
                wraps=ssa_gui_details._update_details_from_series,
            ) as update_details:
                ok = self.window._apply_table_cell_alignment_preference("left")
                QApplication.processEvents()

            assert ok is True
            assert update_details.call_count == 0
            assert self.window._details_current_ssa == initial_ssa
            assert str(self.window.details_text.toHtml() or "") == initial_html
        finally:
            gui_settings["table_cell_alignment"] = previous_alignment or "right"

    def test_tab_switch_preserves_existing_details(self):
        preserve_df = self._build_preserve_details_df()
        self._set_window_dataframe(preserve_df, page_size=10)

        self.window.display_current_page(1)
        QApplication.processEvents()
        self.window._jump_to_ssa("202500004")
        QApplication.processEvents()
        QApplication.processEvents()
        initial_ssa = self.window._details_current_ssa

        self.window._filter_panel_context["filter_panel_tab_bar"].setCurrentIndex(1)
        QApplication.processEvents()
        QApplication.processEvents()
        assert self.window._details_current_ssa == initial_ssa
        assert "Teste D" in str(self.window.details_text.toHtml() or "")

    def test_jump_to_ssa_overrides_previous_selection_without_intermediate_reset(
        self, monkeypatch
    ):
        rows = 220
        jump_df = pd.DataFrame(
            {
                "numero_ssa": list(range(202500001, 202500001 + rows)),
                "situacao": ["APV"] * rows,
                "derivada_de": [""] * rows,
                "localizacao_codigo": [f"L{i}" for i in range(rows)],
                "descricao_localizacao": [f"DL{i}" for i in range(rows)],
                "equipamento": [f"E{i}" for i in range(rows)],
                "semana_cadastro": [202501] * rows,
                "semana_programada": [202503] * rows,
                "data_cadastro": ["2025-01-01"] * rows,
                "descricao_ssa": [f"Teste {i}" for i in range(rows)],
                "setor_executor": ["IEE3"] * rows,
                "setor_emissor": ["ABC"] * rows,
                "descricao_execucao": [f"Exec {i}" for i in range(rows)],
                "solicitante": [f"User{i}" for i in range(rows)],
            }
        )
        target_pos = 157
        target_ssa = str(jump_df.iloc[target_pos]["numero_ssa"])
        target_desc = str(jump_df.iloc[target_pos]["descricao_ssa"])
        page_first_desc = str(jump_df.iloc[100]["descricao_ssa"])

        self.window.df_completo = jump_df.copy()
        self.window.df_exibido = jump_df.copy()
        self.window._df_last_search_filtered = jump_df.copy()
        self.window.paginator.page_size = 100
        self.window.paginator.set_dataframe(jump_df.copy())

        self.window.display_current_page(1)
        QApplication.processEvents()
        self.window.table_widget.selectRow(0)
        QApplication.processEvents()

        scheduled = {}

        def fake_single_shot(delay, callback):
            scheduled["delay"] = delay
            scheduled["callback"] = callback

        monkeypatch.setattr(ssa_gui_details.QTimer, "singleShot", fake_single_shot)

        self.window._jump_to_ssa(target_ssa)

        details_html = str(self.window.details_text.toHtml() or "")
        assert str(self.window._details_current_ssa) == target_ssa
        assert target_desc in details_html
        assert page_first_desc not in details_html
        assert self.window.table_widget.selectionModel().selectedRows() == []
        assert scheduled["delay"] == 0

        scheduled["callback"]()
        QApplication.processEvents()

        selected_rows = self.window.table_widget.selectionModel().selectedRows()
        assert [idx.row() for idx in selected_rows] == [57]
        assert str(self.window._details_current_ssa) == target_ssa
        assert target_desc in str(self.window.details_text.toHtml() or "")

    def test_display_current_page_dataset_swap_updates_visible_table_and_details(self):
        self.window.display_current_page(1)
        QApplication.processEvents()

        replacement_df = self.base_df.copy()
        replacement_df.loc[:, "numero_ssa"] = [101, 102, 103]
        replacement_df.loc[:, "descricao_ssa"] = ["Novo A", "Novo B", "Novo C"]
        replacement_df.loc[:, "descricao_execucao"] = [
            "Exec Novo A",
            "Exec Novo B",
            "Exec Novo C",
        ]
        self._set_window_dataframe(replacement_df, page_size=10)

        self.window.display_current_page(1)
        QApplication.processEvents()

        expected_page = format_dataframe_for_display(
            replacement_df[
                _expected_visible_columns(self.window, replacement_df)
            ].copy()
        )
        numero_ssa_col = self.window._current_display_columns.index("numero_ssa")
        assert (
            self.window.table_widget.item(0, numero_ssa_col).text()
            == expected_page.iloc[0]["numero_ssa"]
        )
        assert self.window._details_current_ssa == 101
        details_html = str(self.window.details_text.toHtml() or "")
        assert "Novo A" in details_html
        assert "Teste A" not in details_html

    def test_display_current_page_happy_path_emits_no_warnings(self, caplog):
        caplog.set_level(logging.WARNING)

        self.window.display_current_page(1)
        QApplication.processEvents()
        self.window.display_current_page(1)
        QApplication.processEvents()
        self.window.search_input.setText("Teste A")
        self.window.display_current_page(1)
        QApplication.processEvents()

        gui_warnings = [
            record
            for record in caplog.records
            if record.levelno >= logging.WARNING and str(record.name).startswith("gui")
        ]
        assert gui_warnings == []

    def test_display_current_page_reuses_formatted_cache_for_equivalent_dataframe_copy(
        self,
    ):
        self.window._data_uuid = "stable-data"
        self.window.__dict__["_ensure_data_revision"] = lambda: None

        with patch.object(
            gui_table,
            "format_dataframe_for_display",
            wraps=gui_table.format_dataframe_for_display,
        ) as formatter:
            self.window.display_current_page(1)
            QApplication.processEvents()
            assert formatter.call_count == 1

            self._set_window_dataframe(self.base_df.copy(), page_size=10)
            self.window._data_uuid = "stable-data"
            self.window.__dict__["_ensure_data_revision"] = lambda: None
            self.window.display_current_page(1)
            QApplication.processEvents()

        assert formatter.call_count == 1

    def test_display_current_page_rebuilds_when_mid_row_changes_with_stable_revision(
        self,
    ):
        self.window._data_uuid = "stable-data"
        self.window.__dict__["_ensure_data_revision"] = lambda: None
        self.window.display_current_page(1)
        QApplication.processEvents()

        mutated_df = self.base_df.copy()
        mutated_df.loc[1, "descricao_ssa"] = "Teste B alterado"
        self._set_window_dataframe(mutated_df, page_size=10)
        self.window._data_uuid = "stable-data"
        self.window.__dict__["_ensure_data_revision"] = lambda: None
        self.window.display_current_page(1)
        QApplication.processEvents()

        descricao_idx = self.window._current_display_columns.index("descricao_ssa")
        assert (
            self.window.table_widget.item(1, descricao_idx).text() == "Teste B alterado"
        )

    def test_display_current_page_rebuilds_when_data_revision_changes_with_stable_markers(
        self,
    ):
        reorder_df = self._build_preserve_details_df().copy().reset_index(drop=True)
        reorder_df.loc[:, "numero_ssa"] = [1, 4, 3, 2, 5]
        reorder_df.loc[:, "descricao_ssa"] = [
            "Teste A",
            "Teste D",
            "Teste C",
            "Teste B",
            "Teste E",
        ]
        self._set_window_dataframe(reorder_df, page_size=10)
        self.window._data_uuid = "stable-data"

        self.window.display_current_page(1)
        QApplication.processEvents()

        descricao_idx = self.window._current_display_columns.index("descricao_ssa")
        initial_revision = int(getattr(self.window, "_data_revision", 0) or 0)
        initial_descriptions = [
            self.window.table_widget.item(row_idx, descricao_idx).text()
            for row_idx in range(len(reorder_df))
        ]
        assert initial_descriptions == [
            "Teste A",
            "Teste D",
            "Teste C",
            "Teste B",
            "Teste E",
        ]

        sorted_df = reorder_df.sort_values("numero_ssa").reset_index(drop=True)
        self._set_window_dataframe(sorted_df, page_size=10)
        self.window._data_uuid = "stable-data"

        self.window.display_current_page(1)
        QApplication.processEvents()

        assert int(getattr(self.window, "_data_revision", 0) or 0) > initial_revision
        sorted_descriptions = [
            self.window.table_widget.item(row_idx, descricao_idx).text()
            for row_idx in range(len(sorted_df))
        ]
        assert sorted_descriptions == [
            "Teste A",
            "Teste B",
            "Teste C",
            "Teste D",
            "Teste E",
        ]

    def test_display_current_page_keeps_hash_column_when_tooltip_fails(self):
        from gui.ssa import gui_table

        class _TooltipFailItem(gui_table.QTableWidgetItem):
            def setToolTip(self, *_args, **_kwargs):  # type: ignore[override]
                raise RuntimeError("tooltip failure")

        with patch("gui.ssa.gui_table.QTableWidgetItem", _TooltipFailItem):
            self.window.display_current_page(1)
            QApplication.processEvents()

        first_item = self.window.table_widget.item(0, 0)
        assert first_item is not None
        assert first_item.text() == "1"

    def test_display_current_page_empty_table_clears_stale_details(self):
        self.window.display_current_page(1)
        QApplication.processEvents()
        assert self.window._details_current_ssa == 1
        assert "Teste A" in str(self.window.details_text.toHtml() or "")

        empty_df = self.base_df.iloc[0:0].copy()
        self._set_window_dataframe(empty_df, page_size=10)

        self.window.display_current_page(1)
        QApplication.processEvents()

        assert self.window.table_widget.rowCount() == 0
        assert self.window._details_current_ssa is None
        assert self.window.details_text.toPlainText().strip() == ""

    def test_display_current_page_reuses_render_without_width_recompute(
        self, monkeypatch
    ):
        self.window.display_current_page(1, update_details=False)
        QApplication.processEvents()

        calls = {"rebuild": 0, "widths": 0}
        original_rebuild = gui_table._rebuild_table_widget
        original_widths = gui_table._apply_rendered_table_widths

        def counted_rebuild(*args, **kwargs):
            calls["rebuild"] += 1
            return original_rebuild(*args, **kwargs)

        def counted_widths(*args, **kwargs):
            calls["widths"] += 1
            return original_widths(*args, **kwargs)

        monkeypatch.setattr(gui_table, "_rebuild_table_widget", counted_rebuild)
        monkeypatch.setattr(gui_table, "_apply_rendered_table_widths", counted_widths)

        self.window.display_current_page(1, update_details=False)
        QApplication.processEvents()

        assert calls == {"rebuild": 0, "widths": 0}
