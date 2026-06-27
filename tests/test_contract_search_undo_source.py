"""Contract tests for general search source selection (undo/refinement path)."""

from __future__ import annotations

from types import SimpleNamespace

from gui.helpers.formatting_helpers import normalize_chunk_for_parse
from gui.ssa.filter_search_undo_controller import select_general_filter_source_candidate
from tests._helpers.contract_data_builders import build_base_filter_df


def _make_window(**overrides):
    complete = build_base_filter_df()
    last = complete.iloc[[0, 1]].copy()
    base = {
        "df_completo": complete,
        "_df_last_search_filtered": last,
        "_active_column_filters": {},
        "_advanced_filters_active": False,
        "_exclude_ste_sca": False,
        "_active_filter_search_display": "alpha",
        "filter_thread": None,
        "_normalize_chunk_for_parse": normalize_chunk_for_parse,
    }
    base.update(overrides)
    return SimpleNamespace(**base)


def test_select_source_does_not_reuse_last_search_when_exclude_ste_active():
    window = _make_window(_exclude_ste_sca=True)
    source = select_general_filter_source_candidate(window, "alpha beta")
    assert source is window.df_completo
    assert len(source) == len(window.df_completo)


def test_select_source_does_not_reuse_last_search_when_column_filter_active():
    window = _make_window(_active_column_filters={"situacao": "APV"})
    source = select_general_filter_source_candidate(window, "alpha beta")
    assert source is window.df_completo


def test_select_source_reuses_last_search_on_conservative_term_refinement():
    window = _make_window(_active_filter_search_display="alpha")
    source = select_general_filter_source_candidate(window, "alpha beta")
    assert source is window._df_last_search_filtered
    assert len(source) == 2
