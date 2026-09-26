"""Contract tests for stale data load guards."""

from __future__ import annotations

from contextlib import ExitStack
from functools import partial
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from gui.ssa import gui_workers
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


@pytest.mark.parametrize(
    "failure_stage", ["duplicate_column", "post_load_hook", "active_refresh", "fallback_refresh"]
)
def test_on_data_loaded_recovers_after_delivery_failure(failure_stage):
    old_df = pd.DataFrame({"numero_ssa": [10001, 10002]})
    old_display = old_df.copy()
    fresh_payload = pd.DataFrame({"numero_ssa": [20001, 20002]})
    if failure_stage == "duplicate_column":
        payload = pd.DataFrame([[20001, 20002]], columns=["numero_ssa", "numero_ssa"])
    else:
        payload = fresh_payload
    status_label = MagicMock()
    status_label.text.return_value = "Status: Carregando dados..."
    status_label.setText.side_effect = lambda text: setattr(status_label.text, "return_value", text)
    refresh = MagicMock(return_value=failure_stage not in {"active_refresh", "fallback_refresh"})
    window = SimpleNamespace(
        _active_data_load_request_id=5,
        _data_load_busy=True,
        df_completo=old_df,
        df_exibido=old_display,
        _df_last_search_filtered=old_display,
        _data_revision=1,
        _data_revision_request_id=None,
        _data_uuid="uuid-old",
        status_label=status_label,
        load_button=MagicMock(),
        search_button=MagicMock(),
        progress_bar=MagicMock(),
        clear_filter_button=MagicMock(),
        _has_any_active_filters=lambda: failure_stage != "fallback_refresh",
        _refresh_after_filter_change=refresh,
    )
    finish_load = partial(
        gui_workers.on_load_finished,
        window,
        global_workers=[],
        global_meta={},
        max_global_workers=8,
        retired_ttl_sec=30.0,
        retired_force_wait_ms=10,
        sip_module=None,
    )
    hook_error = RuntimeError("Falha sintetica no pos-load") if failure_stage == "post_load_hook" else None
    with patch("gui.ssa.gui_workers._reset_post_load_filter_state", side_effect=hook_error) as hook:
        assert on_data_loaded(window, payload, request_id=5) is False
        assert window._data_load_busy is False
        window.load_button.setEnabled.assert_called_with(True)
        window.search_button.setEnabled.assert_called_with(True)
        window.progress_bar.setVisible.assert_called_with(False)
        error_status = status_label.text()
        assert error_status.startswith("Status: Erro ao carregar dados.")
        if failure_stage == "duplicate_column":
            assert window.df_completo is old_df
            assert window.df_exibido is old_display
            assert "tabela anterior foi mantida" in error_status
            assert window._data_revision == 1
        else:
            assert window.df_completo["numero_ssa"].astype(int).tolist() == [20001, 20002]
            assert "exibicao pode estar incompleta" in error_status
            assert "tabela anterior foi mantida" not in error_status
        if failure_stage in {"active_refresh", "fallback_refresh"}:
            refresh.assert_called_once()

        finish_load(request_id=5)
        assert status_label.text() == error_status

        hook.side_effect = None
        refresh.return_value = True
        window._active_data_load_request_id = 6
        window._data_load_busy = True
        status_label.setText("Status: Carregando dados...")
        assert on_data_loaded(window, fresh_payload, request_id=6) is True
        finish_load(request_id=6)

    assert window._data_load_busy is False
    assert window.df_completo["numero_ssa"].astype(int).tolist() == [20001, 20002]
    assert window._data_revision_request_id == 6
    assert "Pronto para filtrar" in status_label.text()
    assert "Erro" not in status_label.text()
    window.load_button.setEnabled.assert_called_with(True)
