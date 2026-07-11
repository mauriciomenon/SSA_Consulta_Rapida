"""Worker thread for computing advanced filter option values off the GUI thread.

The computation in collect_advanced_filter_option_values / get_cached_advanced_filter_option_values
runs 6+ pd.unique / pd.to_datetime / pd.to_numeric over the full DataFrame and
blocks the GUI event loop on large datasets. This worker offloads that work.
"""

from __future__ import annotations

import logging
from typing import Any, Callable

import pandas as pd

try:
    from PyQt6.QtCore import QThread, pyqtSignal
except Exception:  # pragma: no cover - headless fallback
    from gui.workers.qt_thread_shim import QThread, pyqtSignal

from gui.ssa.gui_filters_advanced_refresh import (
    AdvancedFilterUIState,
)

logger = logging.getLogger(__name__)


class AdvancedOptionsWorker(QThread):
    """Computes AdvancedFilterUIState off the GUI thread.

    Emits ui_state_ready(AdvancedFilterUIState) when done, or error_occurred(str).
    The signal should be connected with QueuedConnection so the slot runs on
    the GUI thread.

    The get_cached_fn parameter is injected so tests that patch
    gui.ssa.gui_filters_advanced_ui.get_cached_advanced_filter_option_values
    continue to work.
    """

    ui_state_ready = pyqtSignal(object)
    error_occurred = pyqtSignal(str)

    def __init__(
        self,
        df: pd.DataFrame,
        filters: dict[str, Any],
        cache: dict[str, Any],
        data_load_token: Any,
        sort_sectors: Callable[[list[str]], list[str]],
        get_cached_fn: Callable[..., Any],
        force_refresh: bool = False,
    ):
        super().__init__()
        self._df_snapshot = df
        self._filters = dict(filters)
        self._cache_snapshot = cache
        self._data_load_token = data_load_token
        self._sort_sectors = sort_sectors
        self._get_cached_fn = get_cached_fn
        self._force_refresh = force_refresh

    def run(self) -> None:
        try:
            values = self._get_cached_fn(
                self._cache_snapshot,
                self._df_snapshot,
                data_load_token=self._data_load_token,
                sort_sectors=self._sort_sectors,
                force_refresh=self._force_refresh,
            )
            ui_state = AdvancedFilterUIState(filters=self._filters, values=values)
            self.ui_state_ready.emit(ui_state)
        except Exception as exc:
            logger.debug("AdvancedOptionsWorker falhou: %s", exc)
            self.error_occurred.emit(str(exc))
