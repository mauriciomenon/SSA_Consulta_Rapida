"""Contract tests for filter undo snapshot side effects."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import patch

import pandas as pd

from gui.ssa.filter_search_undo_controller import safe_store_last_filter_state


def test_safe_store_last_filter_state_marks_cache_context_dirty():
    """Undo snapshot invokes store and marks _filter_cache_context_dirty."""
    window = SimpleNamespace(
        df_completo=pd.DataFrame({"numero_ssa": [1]}),
        _filter_cache_context_dirty=False,
        _active_column_filters={},
        _column_or_groups=[],
        _pending_search_display=None,
        _exclude_ste_sca=False,
        _advanced_filters={},
        _advanced_filters_active=False,
        current_filter_profile=None,
        _profile_base_filters={},
        _hidden_column_filter_lines=set(),
        _dedicated_or_text="",
        _active_filter_search_display="",
    )
    store_calls: list[object] = []

    def _capture_store(captured_window, **_kwargs):
        store_calls.append(captured_window)

    with patch(
        "gui.ssa.filter_search_undo_controller.store_last_filter_state",
        _capture_store,
    ):
        safe_store_last_filter_state(window, reason="contract-test")
    assert len(store_calls) == 1
    assert store_calls[0] is window
    assert window._filter_cache_context_dirty is True


def test_safe_store_last_filter_state_forwards_search_text_override():
    """Dirty flag is set before store; this test covers override forwarding only."""
    window = SimpleNamespace(
        df_completo=pd.DataFrame({"numero_ssa": [1]}),
        _filter_cache_context_dirty=False,
        _active_column_filters={},
        _column_or_groups=[],
        _pending_search_display=None,
        _exclude_ste_sca=False,
        _advanced_filters={},
        _advanced_filters_active=False,
        current_filter_profile=None,
        _profile_base_filters={},
        _hidden_column_filter_lines=set(),
        _dedicated_or_text="",
        _active_filter_search_display="",
    )
    store_calls: list[tuple[object, dict[str, object]]] = []

    def _capture_store(
        captured_window,
        *,
        search_text_override=None,
        pending_search_display_override=None,
    ):
        store_calls.append(
            (
                captured_window,
                {
                    "search_text_override": search_text_override,
                    "pending_search_display_override": pending_search_display_override,
                },
            )
        )

    with patch(
        "gui.ssa.filter_search_undo_controller.store_last_filter_state",
        _capture_store,
    ):
        safe_store_last_filter_state(
            window,
            reason="undo-before-change",
            search_text_override="alpha",
        )

    assert len(store_calls) == 1
    assert store_calls[0][0] is window
    assert store_calls[0][1]["search_text_override"] == "alpha"
    assert window._filter_cache_context_dirty is True


def test_safe_store_last_filter_state_keeps_dirty_when_store_raises():
    window = SimpleNamespace(
        df_completo=pd.DataFrame({"numero_ssa": [1]}),
        _filter_cache_context_dirty=False,
        _active_column_filters={},
        _column_or_groups=[],
        _pending_search_display=None,
        _exclude_ste_sca=False,
        _advanced_filters={},
        _advanced_filters_active=False,
        current_filter_profile=None,
        _profile_base_filters={},
        _hidden_column_filter_lines=set(),
        _dedicated_or_text="",
        _active_filter_search_display="",
    )

    def _fail_store(*_args, **_kwargs):
        raise RuntimeError("store failed")

    with patch(
        "gui.ssa.filter_search_undo_controller.store_last_filter_state",
        _fail_store,
    ):
        safe_store_last_filter_state(window, reason="store-failure")

    assert window._filter_cache_context_dirty is True
