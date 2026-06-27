"""Contract tests for stale data load guards."""

from __future__ import annotations

from contextlib import ExitStack
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pandas as pd

from gui.ssa.gui_workers import _is_stale_data_load_result, on_data_loaded


def test_is_stale_data_load_result_true_when_request_superseded():
    window = SimpleNamespace(_active_data_load_request_id=3)
    assert _is_stale_data_load_result(window, 2) is True
    assert _is_stale_data_load_result(window, 4) is True
    assert _is_stale_data_load_result(window, 3) is False


def test_on_data_loaded_ignores_stale_payload_without_mutating_frames():
    old_df = pd.DataFrame({"numero_ssa": [1, 2]})
    stale_payload = pd.DataFrame({"numero_ssa": [99]})
    window = SimpleNamespace(
        _active_data_load_request_id=5,
        df_completo=old_df,
        df_exibido=old_df.copy(),
        _df_last_search_filtered=old_df.copy(),
        _data_revision=1,
        _data_revision_request_id=None,
        _data_uuid="uuid-old",
    )

    on_data_loaded(window, stale_payload, request_id=4)

    assert window.df_completo is old_df
    assert window.df_exibido["numero_ssa"].tolist() == [1, 2]
    assert window._data_revision == 1
    assert window._data_uuid == "uuid-old"


def test_on_data_loaded_stale_skips_prepare_and_post_load_hooks():
    old_df = pd.DataFrame({"numero_ssa": [1, 2]})
    stale_payload = pd.DataFrame({"numero_ssa": [99]})
    window = SimpleNamespace(
        _active_data_load_request_id=5,
        df_completo=old_df,
        df_exibido=old_df.copy(),
        _df_last_search_filtered=old_df.copy(),
        _data_revision=1,
        _data_revision_request_id=None,
        _data_uuid="uuid-old",
    )
    post_load_paths = (
        "gui.ssa.gui_workers.prepare_loaded_dataframes",
        "gui.ssa.gui_workers._reset_post_load_filter_state",
        "gui.ssa.gui_workers._reset_post_load_sort_and_width_state",
        "gui.ssa.gui_workers._sync_non_null_column_cache_after_load",
        "gui.ssa.gui_workers._sync_column_selector_after_load",
        "gui.ssa.gui_workers._sync_filter_controls_after_load",
        "gui.ssa.gui_workers._update_loaded_data_status",
        "gui.ssa.gui_workers._sync_data_revision_after_load",
    )
    with ExitStack() as stack:
        spies = {
            path: stack.enter_context(patch(path, MagicMock()))
            for path in post_load_paths
        }
        on_data_loaded(window, stale_payload, request_id=4)

    for spy in spies.values():
        assert spy.call_count == 0
        spy.assert_not_called()


def test_on_data_loaded_applies_fresh_payload_when_request_matches():
    old_df = pd.DataFrame({"numero_ssa": [1, 2]})
    fresh_payload = pd.DataFrame({"numero_ssa": [10, 20, 30]})
    window = SimpleNamespace(
        _active_data_load_request_id=5,
        df_completo=old_df,
        df_exibido=old_df.copy(),
        _df_last_search_filtered=old_df.copy(),
        _data_revision=1,
        _data_revision_request_id=None,
        _data_uuid="uuid-old",
    )
    post_load_patches = (
        "gui.ssa.gui_workers._reset_post_load_filter_state",
        "gui.ssa.gui_workers._reset_post_load_sort_and_width_state",
        "gui.ssa.gui_workers._sync_non_null_column_cache_after_load",
        "gui.ssa.gui_workers._sync_column_selector_after_load",
        "gui.ssa.gui_workers._sync_filter_controls_after_load",
        "gui.ssa.gui_workers._update_loaded_data_status",
    )
    from gui.ssa.gui_loaded_dataframes import prepare_loaded_dataframes

    with ExitStack() as stack:
        prepare_spy = stack.enter_context(
            patch(
                "gui.ssa.gui_workers.prepare_loaded_dataframes",
                wraps=prepare_loaded_dataframes,
            )
        )
        spies = {
            path: stack.enter_context(patch(path, MagicMock()))
            for path in post_load_patches
        }
        on_data_loaded(window, fresh_payload, request_id=5)

    assert prepare_spy.call_count == 1
    assert prepare_spy.call_args[0][0] is fresh_payload
    assert window.df_completo is not old_df
    assert window.df_completo["numero_ssa"].astype(int).tolist() == [10, 20, 30]
    assert set(window.df_exibido["numero_ssa"].astype(int).tolist()) == {10, 20, 30}
    assert len(window.df_exibido) == 3
    assert window._data_revision == 2
    assert window._data_uuid != "uuid-old"
    for spy in spies.values():
        assert spy.call_count == 1


def test_on_data_loaded_sequential_stale_then_fresh_keeps_latest():
    """Supersession: stale payload ignored, matching request_id wins display."""
    baseline = pd.DataFrame({"numero_ssa": [1, 2]})
    stale_payload = pd.DataFrame({"numero_ssa": [99]})
    fresh_payload = pd.DataFrame({"numero_ssa": [10, 20, 30]})
    window = SimpleNamespace(
        _active_data_load_request_id=5,
        df_completo=baseline,
        df_exibido=baseline.copy(),
        _df_last_search_filtered=baseline.copy(),
        _data_revision=1,
        _data_revision_request_id=None,
        _data_uuid="uuid-old",
    )
    post_load_patches = (
        "gui.ssa.gui_workers._reset_post_load_filter_state",
        "gui.ssa.gui_workers._reset_post_load_sort_and_width_state",
        "gui.ssa.gui_workers._sync_non_null_column_cache_after_load",
        "gui.ssa.gui_workers._sync_column_selector_after_load",
        "gui.ssa.gui_workers._sync_filter_controls_after_load",
        "gui.ssa.gui_workers._update_loaded_data_status",
    )
    with ExitStack() as stack:
        spies = {
            path: stack.enter_context(patch(path, MagicMock()))
            for path in post_load_patches
        }
        on_data_loaded(window, stale_payload, request_id=4)
        on_data_loaded(window, fresh_payload, request_id=5)

    assert window.df_completo["numero_ssa"].astype(int).tolist() == [10, 20, 30]
    assert set(window.df_exibido["numero_ssa"].astype(int).tolist()) == {10, 20, 30}
    assert len(window.df_exibido) == 3
    assert window._data_revision == 2
    assert window._data_uuid != "uuid-old"
    for spy in spies.values():
        assert spy.call_count == 1
