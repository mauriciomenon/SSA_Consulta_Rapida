"""Qt scenario tests for filter refresh mixin behavior.

GUI wiring complements pipeline contracts in test_contract_filter_refresh_semantics.py.
"""

from __future__ import annotations

import logging
from unittest.mock import MagicMock

import pandas as pd
from PyQt6.QtWidgets import QApplication

from gui.ssa import gui_filters_advanced_logic as adv_logic
from tests._helpers.contract_data_builders import (
    BASE_SEARCH_APV_SSAS_DESC,
    BASE_SEARCH_SORTED_SSAS_DESC,
    BASE_SEARCH_SUBSET_ILOC,
    make_numero_ssa_sort_counter,
)
from tests._helpers.gui_scenario_harness import GUIFilterScenarioHarness


class TestScenarioFilterRefreshMixin(GUIFilterScenarioHarness):
    def test_terminal_only_refresh_skips_post_search_callbacks(self, monkeypatch):
        """Terminal-only _refresh_after_filter_change skips advanced/column stages."""
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
        filtered_search = self.base_df.iloc[list(BASE_SEARCH_SUBSET_ILOC)].copy()
        sort_calls, count_numero_sort = make_numero_ssa_sort_counter()
        monkeypatch.setattr(pd.DataFrame, "sort_values", count_numero_sort)

        self.window.on_filter_finished(filtered_search, request_id=51)
        QApplication.processEvents()

        assert sort_calls["numero_ssa"] == 1
        assert self.window._df_last_search_filtered["numero_ssa"].tolist() == [1, 5, 4]
        assert self.window.df_exibido["numero_ssa"].tolist() == BASE_SEARCH_APV_SSAS_DESC

    def test_gui_search_only_sorts_display_descending(self):
        """H5/J1: search-only path sorts df_exibido by numero_ssa desc via on_filter_finished."""
        self.window._active_filter_request_id = 60
        self.window._active_filter_search_request_id = 60
        self.window._active_filter_search_display = "Teste"
        self.window.search_input.setText("Teste")
        self.window._active_column_filters = {
            key: "" for key in self.window._active_column_filters
        }
        self.window._advanced_filters_active = False
        self.window._exclude_ste_sca = False

        unsorted = self.base_df.iloc[list(BASE_SEARCH_SUBSET_ILOC)].copy()
        self.window.on_filter_finished(unsorted, request_id=60)
        QApplication.processEvents()

        assert self.window.df_exibido["numero_ssa"].tolist() == BASE_SEARCH_SORTED_SSAS_DESC
        assert bool(
            getattr(self.window._df_last_search_filtered, "attrs", {}).get(
                "ssa_sorted_for_display"
            )
        )

    def test_gui_post_filter_column_keeps_refresh_sort_order(self, monkeypatch):
        """H5/J1: post-search column filter applies APV subset in refresh sort order."""
        self.window._active_filter_request_id = 61
        self.window._active_filter_search_request_id = 61
        self.window._active_filter_search_display = "Teste"
        self.window.search_input.setText("Teste")
        self.window._active_column_filters["situacao"] = "APV"
        self.window._advanced_filters_active = False
        self.window._exclude_ste_sca = False

        filtered_search = self.base_df.iloc[list(BASE_SEARCH_SUBSET_ILOC)].copy()
        sort_calls, count_numero_sort = make_numero_ssa_sort_counter()
        monkeypatch.setattr(pd.DataFrame, "sort_values", count_numero_sort)

        self.window.on_filter_finished(filtered_search, request_id=61)
        QApplication.processEvents()

        assert sort_calls["numero_ssa"] == 1
        assert self.window.df_exibido["numero_ssa"].tolist() == BASE_SEARCH_APV_SSAS_DESC
        assert self.window.df_exibido["situacao"].tolist() == ["APV", "APV"]

    def test_exclude_terminal_blocks_preprocessed_sort_reuse(self):
        preprocessed = self.base_df.copy()
        preprocessed.attrs["ssa_preprocessed_for_gui"] = True
        self.window.df_completo = preprocessed
        self.window._df_last_search_filtered = preprocessed
        self.window._exclude_ste_sca = True

        self.window._refresh_after_filter_change()

        assert "STE" not in self.window.df_exibido["situacao"].tolist()
        assert "SCA" not in self.window.df_exibido["situacao"].tolist()

    def test_filter_refresh_flags_failure_skips_pre_search_sort(self, monkeypatch):
        """Flags failure fail-closes sort defer and skips pre-search numero_ssa sort."""
        self.window._active_filter_request_id = 9
        self.window._active_filter_search_request_id = 9
        self.window._active_filter_search_display = "Teste"
        self.window.search_input.setText("Teste")
        unsorted = self.base_df.iloc[list(BASE_SEARCH_SUBSET_ILOC)].copy()
        sort_calls, count_numero_sort = make_numero_ssa_sort_counter()
        monkeypatch.setattr(pd.DataFrame, "sort_values", count_numero_sort)
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

        assert sort_calls["numero_ssa"] == 0
        assert (
            self.window._df_last_search_filtered["numero_ssa"].tolist()
            == unsorted["numero_ssa"].tolist()
        )

    def test_mask_any_failure_surfaces_adv_notice_not_silent_empty(
        self, monkeypatch, caplog
    ):
        """H6: mask.any() failure keeps df_exibido rows and count label in sync.

        When advanced filter mask.any() raises, df_exibido retains the pre-failure
        rows and filtered_status_label must keep reporting the displayed count.
        status_label must stay non-empty and must not host the derivada aviso text.
        """
        self.load_advanced_contract_df()
        rows_before = len(self.window.df_exibido)
        complete_rows = len(self.window.df_completo)

        def _broken_mask_any(_mask, _context):
            raise adv_logic.AdvancedFilterMaskError(
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
            or "Falha ao aplicar filtros avancados no refresh pos-busca" in record.message
            for record in caplog.records
        )
        assert len(self.window.df_exibido) == rows_before
        count_text = str(self.window.filtered_status_label.text() or "")
        notice_text = str(self.window.status_label.text() or "")
        assert count_text == f"{rows_before} de {complete_rows} SSAs"
        assert notice_text.strip() != ""
        assert "Aviso" not in notice_text
        assert "Falha ao aplicar filtro avancado" in notice_text

    def test_mask_any_failure_via_refresh_after_filter_change_keeps_status(
        self, monkeypatch
    ):
        """H6: mixin refresh path must resync count and surface failure notice."""
        self.load_advanced_contract_df()
        rows_before = len(self.window.df_exibido)
        complete_rows = len(self.window.df_completo)
        self.window._advanced_filters = {"derivada_all_ste": True}
        self.window._advanced_filters_active = True

        def _broken_mask_any(_mask, _context):
            raise adv_logic.AdvancedFilterMaskError(
                "Failed to evaluate advanced filter mask.any() after reprogramacoes"
            )

        monkeypatch.setattr(adv_logic, "_mask_any", _broken_mask_any)
        self.window._refresh_after_filter_change()
        QApplication.processEvents()

        assert len(self.window.df_exibido) == rows_before
        count_text = str(self.window.filtered_status_label.text() or "")
        notice_text = str(self.window.status_label.text() or "")
        assert count_text == f"{rows_before} de {complete_rows} SSAs"
        assert "Falha ao aplicar filtro avancado" in notice_text

    def test_stale_filter_request_ignored_without_mutating_display(self):
        """Stale on_filter_finished payload must not change the visible dataframe."""
        self.window._active_filter_request_id = 10
        before_len = len(self.window.df_exibido)
        before_first = self.window.df_exibido.iloc[0]["numero_ssa"]
        stale_result = self.base_df.iloc[[4]].copy()
        self.window.on_filter_finished(stale_result, request_id=9)
        QApplication.processEvents()
        assert len(self.window.df_exibido) == before_len
        assert self.window.df_exibido.iloc[0]["numero_ssa"] == before_first
