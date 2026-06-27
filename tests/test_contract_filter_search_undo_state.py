"""Contract tests for filter undo snapshot side effects."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import patch

import pandas as pd

from gui.ssa.filter_search_undo_controller import safe_store_last_filter_state


def test_safe_store_last_filter_state_marks_cache_context_dirty():
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
    with patch(
        "gui.ssa.filter_search_undo_controller.store_last_filter_state",
        lambda *_args, **_kwargs: None,
    ):
        safe_store_last_filter_state(window, reason="contract-test")
    assert window._filter_cache_context_dirty is True
