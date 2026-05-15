# gui/ssa/gui_filters_advanced_layout.py
# Relation: calculates advanced-filter grid placement without touching Qt widgets.

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class AdvancedGridLayoutPlan:
    cols: int
    rows: int
    scroll_height: int
    layout_mode: str


@dataclass(frozen=True, slots=True)
class AdvancedGridLayoutConstraints:
    min_cols: int
    max_cols: int
    preferred_cols: int
    field_box_min_height: int
    field_box_max_height: int
    max_scroll_height: int


@dataclass(frozen=True, slots=True)
class AdvancedGridLayoutMetrics:
    effective_width: int
    cell_min_width: int
    spacing: int
    horizontal_padding: int
    vertical_spacing: int
    vertical_padding: int


def build_advanced_grid_layout_plan(
    *,
    visible_count: int,
    metrics: AdvancedGridLayoutMetrics,
    constraints: AdvancedGridLayoutConstraints,
) -> AdvancedGridLayoutPlan | None:
    if visible_count <= 0 or metrics.effective_width <= 0:
        return None
    available_for_cells = max(
        0,
        int(metrics.effective_width) - int(metrics.horizontal_padding),
    )
    max_try_cols = max(1, min(int(constraints.max_cols), int(visible_count)))
    preferred_cols = max(1, min(int(constraints.preferred_cols), max_try_cols))
    candidate_order = list(range(preferred_cols, 0, -1))
    if max_try_cols > preferred_cols:
        candidate_order = (
            list(range(max_try_cols, preferred_cols - 1, -1)) + candidate_order
        )
    cols = 1
    for candidate_cols in candidate_order:
        required_width = (candidate_cols * metrics.cell_min_width) + max(
            0, candidate_cols - 1
        ) * metrics.spacing
        if required_width <= available_for_cells:
            cols = candidate_cols
            break
    cols = max(int(constraints.min_cols), cols)
    cols = max(1, min(cols, int(visible_count)))
    rows = max(1, (int(visible_count) + cols - 1) // cols)
    content_h = (
        rows * int(constraints.field_box_max_height)
        + max(0, rows - 1) * max(0, int(metrics.vertical_spacing))
        + int(metrics.vertical_padding)
        + 2
    )
    min_content_h = (
        int(metrics.vertical_padding) + int(constraints.field_box_min_height) + 2
    )
    content_h = max(content_h, min_content_h)
    scroll_height = max(60, min(int(constraints.max_scroll_height), content_h))
    return AdvancedGridLayoutPlan(
        cols=cols,
        rows=rows,
        scroll_height=scroll_height,
        layout_mode=f"cols_{cols}",
    )
