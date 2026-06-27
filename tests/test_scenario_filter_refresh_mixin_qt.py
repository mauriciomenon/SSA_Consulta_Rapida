"""Qt scenario tests for filter refresh mixin behavior."""

from __future__ import annotations

import logging
from unittest.mock import MagicMock

import pandas as pd
from PyQt6.QtWidgets import QApplication

from gui.ssa import gui_filters_advanced_logic as adv_logic
from tests._helpers.gui_scenario_harness import GUIFilterScenarioHarness


class TestScenarioFilterRefreshMixin(GUIFilterScenarioHarness):
    def test_terminal_only_refresh_skips_post_search_callbacks(self, monkeypatch):
        advanced_calls = {"count": 0}
        column_calls = {"count": 0}

        def _fail_advanced(_df):
            advanced_calls["count"] += 1
            raise AssertionError("advanced filters should be skipped")

        def _fail_column(_df):
            column_calls["count"] += 1
            raise AssertionError("column filters should be skipped")

        self.window._exclude_ste_sca = True
        self.window._advanced_filters_active = False
        self.window._active_column_filters = {
            key: "" for key in self.window._active_column_filters
        }
        monkeypatch.setattr(self.window, "_apply_advanced_filters", _fail_advanced)
        monkeypatch.setattr(self.window, "_apply_column_filters", _fail_column)

        self.window._refresh_after_filter_change()

        assert advanced_calls["count"] == 0
        assert column_calls["count"] == 0
        assert "STE" not in self.window.df_exibido["situacao"].tolist()

    def test_on_filter_finished_defers_double_sort_with_post_filters(
        self, monkeypatch
    ):
        self.window._active_filter_request_id = 51
        self.window._active_filter_search_request_id = 51
        self.window._active_filter_search_display = "Teste"
        self.window.search_input.setText("Teste")
        self.window._active_column_filters["situacao"] = "APV"
        filtered_search = self.base_df.iloc[[0, 4, 3]].copy()
        sort_calls = {"numero_ssa": 0}
        original_sort_values = pd.DataFrame.sort_values

        def _count_numero_sort(frame, by=None, *args, **kwargs):
            if by == "numero_ssa":
                sort_calls["numero_ssa"] += 1
            return original_sort_values(frame, by=by, *args, **kwargs)

        monkeypatch.setattr(pd.DataFrame, "sort_values", _count_numero_sort)

        self.window.on_filter_finished(filtered_search, request_id=51)
        QApplication.processEvents()

        assert sort_calls["numero_ssa"] == 1
        assert self.window._df_last_search_filtered["numero_ssa"].tolist() == [1, 5, 4]
        assert self.window.df_exibido["numero_ssa"].tolist() == [5, 1]

    def test_exclude_terminal_blocks_preprocessed_sort_reuse(self):
        preprocessed = self.base_df.copy()
        preprocessed.attrs["ssa_preprocessed_for_gui"] = True
        self.window.df_completo = preprocessed
        self.window._df_last_search_filtered = preprocessed
        self.window._exclude_ste_sca = True

        self.window._refresh_after_filter_change()

        assert "STE" not in self.window.df_exibido["situacao"].tolist()
        assert "SCA" not in self.window.df_exibido["situacao"].tolist()

    def test_filter_refresh_flags_failure_allows_search_sort(self, monkeypatch):
        self.window._active_filter_request_id = 9
        self.window._active_filter_search_request_id = 9
        self.window._active_filter_search_display = "Teste"
        self.window.search_input.setText("Teste")
        unsorted = self.base_df.iloc[[0, 4, 3]].copy()
        sort_calls = {"numero_ssa": 0}
        original_sort_values = pd.DataFrame.sort_values

        def _count_numero_sort(frame, by=None, *args, **kwargs):
            if by == "numero_ssa":
                sort_calls["numero_ssa"] += 1
            return original_sort_values(frame, by=by, *args, **kwargs)

        monkeypatch.setattr(pd.DataFrame, "sort_values", _count_numero_sort)
        monkeypatch.setattr(
            self.window,
            "_filter_refresh_flags",
            MagicMock(side_effect=RuntimeError("flags failure")),
        )
        monkeypatch.setattr(
            self.window, "_refresh_after_filter_change", lambda **_kwargs: None
        )

        self.window.on_filter_finished(unsorted, request_id=9)
        QApplication.processEvents()

        assert sort_calls["numero_ssa"] == 1
        assert self.window._df_last_search_filtered["numero_ssa"].tolist() == [5, 4, 1]

    def test_mask_any_failure_surfaces_adv_notice_not_silent_empty(
        self, monkeypatch, caplog
    ):
        self.load_advanced_contract_df()
        rows_before = len(self.window.df_exibido)

        def _broken_mask_any(_mask, _context):
            raise RuntimeError(
                "Failed to evaluate advanced filter mask.any() after reprogramacoes"
            )

        monkeypatch.setattr(adv_logic, "_mask_any", _broken_mask_any)
        monkeypatch.setattr(
            "gui.ssa.gui_filters_advanced_ui._read_advanced_filters_from_ui",
            lambda _self, _previous: {"derivada_all_ste": True},
        )

        with caplog.at_level(logging.WARNING):
            self.window._apply_advanced_filters_from_ui(store_only=False)
        QApplication.processEvents()

        assert any(
            "Falha ao atualizar resultado apos aplicar filtros avancados" in record.message
            for record in caplog.records
        )
        assert len(self.window.df_exibido) == rows_before
        assert self.window.filtered_status_label.text()

    def test_filter_refresh_flags_failure_updates_status_label(self, monkeypatch):
        self.window._active_filter_request_id = 9
        self.window._active_filter_search_request_id = 9
        self.window._active_filter_search_display = "Teste"
        self.window.search_input.setText("Teste")
        unsorted = self.base_df.iloc[[0, 4, 3]].copy()

        monkeypatch.setattr(
            self.window,
            "_filter_refresh_flags",
            MagicMock(side_effect=RuntimeError("flags failure")),
        )
        monkeypatch.setattr(
            self.window, "_refresh_after_filter_change", lambda **_kwargs: None
        )

        self.window.on_filter_finished(unsorted, request_id=9)
        QApplication.processEvents()

        status_text = self.window.filtered_status_label.text()
        assert status_text
        assert "de" in status_text
        assert "SSA" in status_text
