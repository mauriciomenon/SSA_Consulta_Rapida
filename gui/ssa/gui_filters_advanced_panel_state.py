from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class AdvancedFilterPanelParts:
    group: Any
    fields: dict
    controls: dict
    main_grid: Any
    action_box: Any | None
    apply_btn: Any | None
    clear_btn: Any | None
    controls_scroll: Any


@dataclass
class AdvancedFilterPanelState:
    group: Any
    main_grid: Any
    grid_widgets: dict[str, Any]
    grid_order: tuple[str, ...]
    apply_btn: Any | None
    clear_btn: Any | None
    metric_controls: tuple[Any, ...]
    action_widget: Any | None
    controls_scroll: Any
    action_btn_dims: tuple[int, int] | None = None
    grid_cols: int | None = None
    last_widget_count: int | None = None
    layout_mode: str | None = None
    last_effective_width: int | None = None
    last_max_scroll_h: int | None = None
    cell_min_width: int | None = None
    cell_min_width_widget_key: tuple[int, ...] | None = None
    sector_handler_running: bool = False
    sector_syncing: bool = False


def advanced_panel_state(window: Any) -> AdvancedFilterPanelState | None:
    state = getattr(window, "_advanced_filter_panel_state", None)
    if isinstance(state, AdvancedFilterPanelState):
        return state
    return None
