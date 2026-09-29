from __future__ import annotations

from types import SimpleNamespace

from gui.ssa.gui_filters_advanced_grid import _advanced_grid_recently_applied
from gui.ssa.gui_filters_advanced_panel_state import AdvancedFilterPanelState


def test_advanced_grid_recently_applied_requires_same_visible_widget_count():
    state = AdvancedFilterPanelState(
        group=None,
        main_grid=None,
        grid_widgets={},
        grid_order=(),
        apply_btn=None,
        clear_btn=None,
        metric_controls=(),
        action_widget=None,
        controls_scroll=None,
        grid_cols=3,
        last_widget_count=5,
        last_effective_width=1200,
        last_max_scroll_h=320,
    )
    window = SimpleNamespace(_advanced_filter_panel_state=state)

    assert _advanced_grid_recently_applied(window, 1202, 321, 5) is True
    assert _advanced_grid_recently_applied(window, 1202, 321, 6) is False
