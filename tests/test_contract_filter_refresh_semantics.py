"""Contract tests for filter refresh semantics and has_post_search_filters.

Pipeline-level contracts; GUI wiring for the same gates lives in
test_scenario_filter_refresh_mixin_qt.py.
"""

from __future__ import annotations

from collections import OrderedDict
from unittest.mock import MagicMock

import pandas as pd

from gui.ssa.filter_refresh_pipeline import apply_filter_refresh_pipeline
from tests._helpers.contract_data_builders import (
    BASE_SEARCH_SORTED_SSAS_DESC,
    BASE_SEARCH_SUBSET_ILOC,
    build_base_filter_df,
    make_numero_ssa_sort_counter,
    pipeline_measure_timing,
)


def test_terminal_only_skips_post_search_callbacks():
    """Terminal-only refresh excludes STE/SCA without post-search callbacks."""
    df = build_base_filter_df()

    def _unexpected(_frame):
        raise AssertionError("post-search filters must not run for terminal-only")

    filtered, cache_update = apply_filter_refresh_pipeline(
        df,
        has_post_search_filters=False,
        has_excluded_terminal_status=True,
        cache_key=("revision", "terminal-only"),
        cached=None,
        apply_advanced_filters=_unexpected,
        apply_column_filters=_unexpected,
        measure_timing=pipeline_measure_timing,
    )

    assert "STE" not in filtered["situacao"].tolist()
    assert "SCA" not in filtered["situacao"].tolist()
    assert cache_update is not None


def test_refresh_path_excludes_terminal_from_has_post_search_filters():
    """Refresh path treats terminal exclusion separately from post-search filters."""
    df = build_base_filter_df()
    post_search_calls = {"count": 0}

    def _track_post_search(_frame):
        post_search_calls["count"] += 1
        return _frame

    refresh_has_post_search = False
    refresh_has_terminal = True

    filtered, _ = apply_filter_refresh_pipeline(
        df,
        has_post_search_filters=refresh_has_post_search,
        has_excluded_terminal_status=refresh_has_terminal,
        cache_key=("revision", "refresh-semantics"),
        cached=None,
        apply_advanced_filters=_track_post_search,
        apply_column_filters=_track_post_search,
        measure_timing=pipeline_measure_timing,
    )

    assert post_search_calls["count"] == 0
    assert "STE" not in filtered["situacao"].tolist()


def test_on_filter_finished_includes_terminal_in_has_post_search_filters():
    """on_filter_finished gate differs from refresh path for terminal exclusion."""
    from gui.mixins.filter_gui_ssa_mixin import FilterGUISSAMixin

    class _Window(FilterGUISSAMixin):
        pass

    window = _Window()
    window._active_column_filters = OrderedDict()
    window._advanced_filters_active = False
    window._exclude_ste_sca = True

    (
        has_column_filters,
        has_advanced_filters,
        has_excluded_terminal_status,
    ) = window._filter_refresh_flags()

    refresh_has_post_search = window._compute_has_post_search_filters(
        has_column_filters=has_column_filters,
        has_advanced_filters=has_advanced_filters,
        has_excluded_terminal_status=has_excluded_terminal_status,
        for_sort_defer=False,
    )
    on_finished_has_post_search = window._compute_has_post_search_filters(
        has_column_filters=has_column_filters,
        has_advanced_filters=has_advanced_filters,
        has_excluded_terminal_status=has_excluded_terminal_status,
        for_sort_defer=True,
    )

    assert refresh_has_post_search is False
    assert on_finished_has_post_search is True
    assert has_excluded_terminal_status is True


def test_on_filter_finished_skips_sort_when_filter_refresh_flags_fail(monkeypatch):
    """Flags failure fail-closes sort defer and skips pre-search numero_ssa sort."""
    from gui.mixins.filter_gui_ssa_mixin import FilterGUISSAMixin

    class _Window(FilterGUISSAMixin):
        pass

    window = _Window()
    setattr(window, "_active_filter_request_id", 7)
    setattr(window, "_active_filter_search_request_id", 7)
    setattr(window, "_active_filter_search_display", "Teste")
    setattr(window, "table_widget", MagicMock())
    setattr(window, "df_completo", build_base_filter_df())
    setattr(window, "df_exibido", window.df_completo.copy())
    setattr(window, "paginator", MagicMock())
    search_input = MagicMock()
    search_input.text.return_value = "Teste"
    setattr(window, "search_input", search_input)
    status_label = MagicMock()
    status_label.text.return_value = ""
    setattr(window, "filtered_status_label", status_label)
    setattr(window, "clear_filter_button", MagicMock())

    unsorted = window.df_completo.iloc[list(BASE_SEARCH_SUBSET_ILOC)].copy()
    sort_calls, count_numero_sort = make_numero_ssa_sort_counter()

    monkeypatch.setattr(
        "gui.mixins.filter_gui_ssa_mixin._is_search_widget_valid",
        lambda _widget: True,
    )
    monkeypatch.setattr(pd.DataFrame, "sort_values", count_numero_sort)
    monkeypatch.setattr(
        window,
        "_filter_refresh_flags",
        MagicMock(side_effect=RuntimeError("flags failure")),
    )
    monkeypatch.setattr(window, "_refresh_after_filter_change", lambda **_kwargs: None)
    monkeypatch.setattr(window, "_update_filter_status_display", lambda **_kwargs: None)
    monkeypatch.setattr(window, "_sync_clear_filter_button_state", lambda: None)
    monkeypatch.setattr(window, "_apply_search_display", lambda: None)
    monkeypatch.setattr(
        window, "_apply_filter_result_width_safety", lambda *_args, **_kwargs: None
    )
    monkeypatch.setattr(window, "_consume_pending_jump_to_ssa", lambda *_args: None)

    window.on_filter_finished(unsorted, request_id=7)

    assert sort_calls["numero_ssa"] == 0
    assert window._df_last_search_filtered["numero_ssa"].tolist() == unsorted["numero_ssa"].tolist()


def test_refresh_path_applies_post_search_when_column_filter_active():
    """Active column filters run advanced and column stages in refresh path."""
    df = build_base_filter_df()
    advanced_calls = {"count": 0}
    column_calls = {"count": 0}

    def _track_advanced(frame):
        advanced_calls["count"] += 1
        return frame

    def _track_column(frame):
        column_calls["count"] += 1
        return frame[frame["situacao"].eq("APV")]

    filtered, _ = apply_filter_refresh_pipeline(
        df,
        has_post_search_filters=True,
        has_excluded_terminal_status=False,
        cache_key=("revision", "column-active"),
        cached=None,
        apply_advanced_filters=_track_advanced,
        apply_column_filters=_track_column,
        measure_timing=pipeline_measure_timing,
    )

    assert advanced_calls["count"] == 1
    assert column_calls["count"] == 1
    assert filtered["situacao"].tolist() == ["APV", "APV"]


def test_sort_filter_refresh_result_skips_when_sorted_attr_set(monkeypatch):
    """J1: reuse search-sorted frame when ssa_sorted_for_display is set."""
    from gui.mixins.filter_gui_ssa_mixin import FilterGUISSAMixin

    class _Window(FilterGUISSAMixin):
        pass

    window = _Window()
    sorted_df = build_base_filter_df().iloc[list(BASE_SEARCH_SUBSET_ILOC)].copy()
    sorted_df.attrs["ssa_sorted_for_display"] = True
    window._df_last_search_filtered = sorted_df

    sort_calls, count_numero_sort = make_numero_ssa_sort_counter()
    monkeypatch.setattr(pd.DataFrame, "sort_values", count_numero_sort)

    result = window._sort_filter_refresh_result(
        sorted_df,
        has_general_search=True,
        has_column_filters=False,
        has_advanced_filters=False,
        has_excluded_terminal_status=False,
        measure_timing=lambda _name, callback: callback(),
    )

    assert sort_calls["numero_ssa"] == 0
    assert result is sorted_df


def test_sort_filter_refresh_result_sorts_when_sorted_attr_missing(monkeypatch):
    """J1: without ssa_sorted_for_display, refresh path sorts by numero_ssa."""
    from gui.mixins.filter_gui_ssa_mixin import FilterGUISSAMixin

    class _Window(FilterGUISSAMixin):
        pass

    window = _Window()
    unsorted = build_base_filter_df().iloc[list(BASE_SEARCH_SUBSET_ILOC)].copy()
    window._df_last_search_filtered = unsorted.copy()

    sort_calls, count_numero_sort = make_numero_ssa_sort_counter()
    monkeypatch.setattr(pd.DataFrame, "sort_values", count_numero_sort)

    result = window._sort_filter_refresh_result(
        unsorted,
        has_general_search=True,
        has_column_filters=False,
        has_advanced_filters=False,
        has_excluded_terminal_status=False,
        measure_timing=lambda _name, callback: callback(),
    )

    assert sort_calls["numero_ssa"] == 1
    assert result["numero_ssa"].tolist() == BASE_SEARCH_SORTED_SSAS_DESC
