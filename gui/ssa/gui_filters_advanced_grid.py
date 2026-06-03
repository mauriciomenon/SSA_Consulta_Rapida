from __future__ import annotations

from typing import Any

from utils.robust_logging import get_robust_logger

from .gui_filters_advanced_layout import (
    LAYOUT_ADV_CONTROL_HEIGHT,
    LAYOUT_ADV_FIELD_BOX_MAX_HEIGHT,
    LAYOUT_ADV_FIELD_BOX_MIN_HEIGHT,
    LAYOUT_ADV_PANEL_MAX_HEIGHT,
    LAYOUT_GRID_MAX_COLS,
    LAYOUT_GRID_MIN_COLS,
    LAYOUT_GRID_PREF_COLS,
    LAYOUT_MIN_VALID_WIDTH,
    AdvancedGridLayoutConstraints,
    AdvancedGridLayoutMetrics,
    build_advanced_grid_layout_plan,
)
from .gui_filters_advanced_panel_state import advanced_panel_state
from .gui_filters_multiselect_menu import _is_not_deleted

logger = get_robust_logger().get_logger(__name__, "gui")


def resolve_adv_layout_baseline(window: Any) -> tuple[int, int, int]:
    _ = window
    return 212, 88, 134


def apply_advanced_filters_font_policy(window: Any, width: int) -> None:
    state = advanced_panel_state(window)
    group = state.group if state is not None else None
    if group is None:
        return
    base_pt = 10
    try:
        ref_button = getattr(window, "search_button", None)
        ref_font = ref_button.font() if ref_button is not None else group.font()
        current = int(ref_font.pointSize())
        if current > 0:
            base_pt = current
    except Exception as exc:
        logger.debug("Falha ao ler fonte base do grupo de filtros avancados: %s", exc)
    if width < 760:
        target_pt = 10
    elif width < 980:
        target_pt = 11
    else:
        target_pt = 12
    control_pt = max(10, min(target_pt, base_pt if base_pt > 0 else target_pt))
    title_pt = max(control_pt, min(12, control_pt + 1))
    try:
        boxes = (
            state.grid_widgets.values()
            if state is not None
            else ()
        )
    except Exception:
        boxes = []
    for box in boxes:
        if box is None:
            continue
        try:
            box_font = box.font()
            box_font.setPointSize(title_pt)
            box.setFont(box_font)
        except Exception as exc:
            logger.debug("Falha ao ajustar fonte do box de filtro avancado: %s", exc)
    controls = (
        state.metric_controls if state is not None else ()
    )
    for control in controls:
        if control is None:
            continue
        try:
            control_font = control.font()
            control_font.setPointSize(control_pt)
            control.setFont(control_font)
        except Exception as exc:
            logger.debug(
                "Falha ao ajustar fonte de controle no painel avancado: %s", exc
            )


def update_advanced_filters_action_buttons(window: Any, width: int) -> None:
    state = advanced_panel_state(window)
    if state is None:
        return
    apply_btn = state.apply_btn
    clear_btn = state.clear_btn
    if apply_btn is None or clear_btn is None:
        return
    if not _is_not_deleted(apply_btn) or not _is_not_deleted(clear_btn):
        return
    _ = width
    _, min_width, max_width = resolve_adv_layout_baseline(window)
    min_width = max(56, min(72, min_width))
    max_width = max(min_width + 6, min(84, max_width))
    grid_cols = _current_grid_cols(window, state)
    if width > 0:
        cell_width = max(112, int(width // grid_cols))
        pair_budget = max(96, cell_width - 10)
        per_button_budget = max(48, int((pair_budget - 6) // 2))
        min_width = max(48, min(min_width, per_button_budget))
        max_width = max(min_width, min(max_width, per_button_budget))
    new_dims = (min_width, max_width)
    current_dims = state.action_btn_dims
    if current_dims == new_dims:
        return
    state.action_btn_dims = new_dims
    for button in (apply_btn, clear_btn):
        _apply_advanced_action_button_size(window, button, min_width, max_width)


def enforce_advanced_filters_compact_metrics(window: Any) -> None:
    state = advanced_panel_state(window)
    if state is None or state.group is None:
        return
    grid_widgets = state.grid_widgets
    for field_box in grid_widgets.values():
        _set_fixed_height(
            field_box,
            LAYOUT_ADV_FIELD_BOX_MIN_HEIGHT,
            LAYOUT_ADV_FIELD_BOX_MAX_HEIGHT,
            "box de filtro avancado",
        )
    controls = (
        state.metric_controls
    )
    for control in controls:
        _set_fixed_height(
            control,
            LAYOUT_ADV_CONTROL_HEIGHT,
            LAYOUT_ADV_CONTROL_HEIGHT,
            "controle de filtro avancado",
        )


def reorganize_advanced_filters_grid(window: Any, width: int) -> None:
    effective_width, max_scroll_h, controls_scroll = _resolve_grid_viewport_metrics(
        window, width
    )
    grid, visible = _visible_grid_widgets(window)
    if not visible:
        return
    if grid is not None:
        _apply_responsive_grid_spacing(grid, effective_width)
    update_advanced_filters_action_buttons(window, effective_width)
    if effective_width < LAYOUT_MIN_VALID_WIDTH:
        return
    if _advanced_grid_recently_applied(window, effective_width, max_scroll_h):
        return
    enforce_advanced_filters_compact_metrics(window)
    apply_advanced_filters_font_policy(window, effective_width)
    _store_advanced_grid_viewport_metrics(window, effective_width, max_scroll_h)
    try:
        plan = _build_grid_plan(
            window,
            grid=grid,
            visible=visible,
            effective_width=effective_width,
            max_scroll_h=max_scroll_h,
        )
    except Exception as exc:
        logger.debug("Falha ao calcular layout dos filtros avancados: %s", exc)
        return
    if plan is None:
        return
    if controls_scroll is not None:
        controls_scroll.setMinimumHeight(plan.scroll_height)
        controls_scroll.setMaximumHeight(plan.scroll_height)
    if not _grid_relayout_needed(window, plan, len(visible)):
        return
    _apply_grid_plan(
        window,
        grid=grid,
        visible=visible,
        plan=plan,
        effective_width=effective_width,
    )


def _current_grid_cols(window: Any, state: Any) -> int:
    if state is None:
        return LAYOUT_GRID_PREF_COLS
    try:
        value = int(
            state.grid_cols or LAYOUT_GRID_PREF_COLS
        )
    except Exception:
        value = LAYOUT_GRID_PREF_COLS
    return max(1, min(LAYOUT_GRID_MAX_COLS, value))


def _apply_advanced_action_button_size(
    window: Any, button: Any, min_width: int, max_width: int
) -> None:
    if not _is_not_deleted(button):
        return
    try:
        ref_btn = getattr(window, "search_button", None)
        if ref_btn is not None and _is_not_deleted(ref_btn):
            ref_font = ref_btn.font()
            ref_font.setBold(False)
            button.setFont(ref_font)
            ref_h = int(
                ref_btn.height() or ref_btn.sizeHint().height() or LAYOUT_ADV_CONTROL_HEIGHT
            )
            ref_h = max(20, min(24, ref_h))
            button.setMinimumHeight(ref_h)
            button.setMaximumHeight(ref_h)
        button.setMinimumWidth(min_width)
        button.setMaximumWidth(max_width)
    except Exception as exc:
        logger.debug("Falha ao ajustar largura minima de botao de acao: %s", exc)


def _set_fixed_height(widget: Any, min_height: int, max_height: int, label: str) -> None:
    if widget is None:
        return
    try:
        widget.setMinimumHeight(min_height)
        widget.setMaximumHeight(max_height)
    except Exception as exc:
        logger.debug("Falha ao aplicar metrica compacta em %s: %s", label, exc)


def _resolve_grid_viewport_metrics(window: Any, width: int):
    effective_width = width
    state = advanced_panel_state(window)
    controls_scroll = state.controls_scroll if state is not None else None
    max_scroll_h = LAYOUT_ADV_PANEL_MAX_HEIGHT
    try:
        if controls_scroll is not None and hasattr(controls_scroll, "viewport"):
            viewport_w = int(controls_scroll.viewport().width())
            if viewport_w > 0:
                effective_width = min(effective_width, viewport_w)
        group = getattr(window, "adv_filters_group", None)
        if controls_scroll is not None and group is not None:
            group_h = int(group.height())
            if group_h > 0:
                max_scroll_h = max(
                    80,
                    min(
                        LAYOUT_ADV_PANEL_MAX_HEIGHT,
                        group_h - 4,
                    ),
                )
    except Exception as exc:
        logger.debug(
            "Falha ao obter largura efetiva do viewport dos filtros avancados: %s", exc
        )
    return effective_width, max_scroll_h, controls_scroll


def _visible_grid_widgets(window: Any):
    state = advanced_panel_state(window)
    if state is None:
        return None, []
    widgets = state.grid_widgets
    grid = state.main_grid
    if not widgets or grid is None:
        return None, []
    order = state.grid_order
    visible = [
        (name, widget)
        for name in order
        if (widget := widgets.get(name)) is not None
    ]
    return grid, visible


def _apply_responsive_grid_spacing(grid: Any, effective_width: int) -> None:
    if grid is None:
        return
    if effective_width >= 900:
        horizontal_spacing = 12
        vertical_spacing = 6
    elif effective_width >= 700:
        horizontal_spacing = 8
        vertical_spacing = 5
    elif effective_width >= 560:
        horizontal_spacing = 8
        vertical_spacing = 4
    else:
        horizontal_spacing = 4
        vertical_spacing = 3
    try:
        grid.setHorizontalSpacing(horizontal_spacing)
        grid.setVerticalSpacing(vertical_spacing)
    except Exception as exc:
        logger.debug("Falha ao aplicar espacamento responsivo do grid avancado: %s", exc)


def _advanced_grid_spacing_metrics(grid: Any):
    try:
        spacing = int(grid.horizontalSpacing())
    except Exception:
        spacing = 0
    try:
        margins = grid.contentsMargins()
        horizontal_padding = int(margins.left() + margins.right())
        vertical_padding = int(margins.top() + margins.bottom())
    except Exception:
        horizontal_padding = 0
        vertical_padding = 0
    try:
        vertical_spacing = int(grid.verticalSpacing())
    except Exception:
        vertical_spacing = 0
    return spacing, horizontal_padding, vertical_spacing, vertical_padding


def _build_grid_plan(
    window: Any,
    *,
    grid: Any,
    visible: list[tuple[str, Any]],
    effective_width: int,
    max_scroll_h: int,
):
    cell_min_width = _compute_grid_cell_min_width(window, visible)
    spacing, horizontal_padding, vertical_spacing, vertical_padding = (
        _advanced_grid_spacing_metrics(grid)
    )
    return build_advanced_grid_layout_plan(
        visible_count=len(visible),
        metrics=AdvancedGridLayoutMetrics(
            effective_width=effective_width,
            cell_min_width=cell_min_width,
            spacing=spacing,
            horizontal_padding=horizontal_padding,
            vertical_spacing=vertical_spacing,
            vertical_padding=vertical_padding,
        ),
        constraints=AdvancedGridLayoutConstraints(
            min_cols=LAYOUT_GRID_MIN_COLS,
            max_cols=LAYOUT_GRID_MAX_COLS,
            preferred_cols=LAYOUT_GRID_PREF_COLS,
            field_box_min_height=LAYOUT_ADV_FIELD_BOX_MIN_HEIGHT,
            field_box_max_height=LAYOUT_ADV_FIELD_BOX_MAX_HEIGHT,
            max_scroll_height=max_scroll_h,
        ),
    )


def _compute_grid_cell_min_width(
    window: Any, visible_widgets: list[tuple[str, Any]]
) -> int:
    state = advanced_panel_state(window)
    widget_key = tuple(id(widget) for _, widget in visible_widgets if widget is not None)
    if (
        state is not None
        and state.cell_min_width is not None
        and state.cell_min_width_widget_key == widget_key
    ):
        return state.cell_min_width
    base_cell_min, _, _ = resolve_adv_layout_baseline(window)
    widths = []
    for _, widget in visible_widgets:
        if widget is None:
            continue
        try:
            widths.append(int(widget.minimumSizeHint().width()))
        except Exception as exc:
            logger.debug("Falha ao medir largura minima de filtro avancado: %s", exc)
            continue
    if not widths:
        return base_cell_min
    widths.sort()
    p75_idx = max(0, min(len(widths) - 1, int((len(widths) - 1) * 0.75)))
    p75 = widths[p75_idx]
    avg = sum(widths) // len(widths)
    dynamic_baseline = max(p75, avg) + 22
    result = max(150, min(280, max(min(base_cell_min, 188), dynamic_baseline)))
    if state is not None:
        state.cell_min_width = result
        state.cell_min_width_widget_key = widget_key
    return result


def _advanced_grid_recently_applied(
    window: Any, effective_width: int, max_scroll_h: int
) -> bool:
    state = advanced_panel_state(window)
    if state is None:
        return False
    previous_effective_width = state.last_effective_width
    previous_max_scroll_h = state.last_max_scroll_h
    current_cols = state.grid_cols
    return (
        previous_effective_width is not None
        and abs(int(effective_width) - int(previous_effective_width)) < 8
        and previous_max_scroll_h is not None
        and abs(int(max_scroll_h) - int(previous_max_scroll_h)) < 8
        and current_cols is not None
    )


def _store_advanced_grid_viewport_metrics(
    window: Any, effective_width: int, max_scroll_h: int
) -> None:
    state = advanced_panel_state(window)
    if state is None:
        return
    state.last_effective_width = int(effective_width)
    state.last_max_scroll_h = int(max_scroll_h)


def _grid_relayout_needed(window: Any, plan: Any, visible_count: int) -> bool:
    state = advanced_panel_state(window)
    if state is None:
        return False
    return not (
        state.grid_cols == plan.cols and state.last_widget_count == visible_count
    )


def _resolve_grid_cell_width_budget(grid: Any, effective_width: int, cols: int) -> int:
    spacing, horizontal_padding, _vertical_spacing, _vertical_padding = (
        _advanced_grid_spacing_metrics(grid)
    )
    usable_width = max(0, int(effective_width) - int(horizontal_padding))
    total_spacing = max(0, cols - 1) * max(0, int(spacing))
    return max(0, (usable_width - total_spacing) // max(1, cols))


def _apply_widget_width_cap(widget: Any, width_budget: int, cols: int) -> None:
    if widget is None:
        return
    if cols <= 1:
        max_width = min(max(280, width_budget), 460)
    elif cols == 2:
        max_width = min(max(232, width_budget), 340)
    else:
        max_width = min(max(200, width_budget), 300)
    try:
        widget.setMaximumWidth(max_width)
    except Exception as exc:
        logger.debug("Falha ao limitar largura de box no grid avancado: %s", exc)


def _apply_grid_plan(
    window: Any,
    *,
    grid: Any,
    visible: list[tuple[str, Any]],
    plan,
    effective_width: int,
):
    state = advanced_panel_state(window)
    if state is None:
        return
    previous_cols = state.grid_cols
    state.grid_cols = plan.cols
    state.last_widget_count = len(visible)
    state.layout_mode = plan.layout_mode
    width_budget = _resolve_grid_cell_width_budget(grid, effective_width, plan.cols)
    for idx, (_, widget) in enumerate(visible):
        row = idx // plan.cols
        col = idx % plan.cols
        grid.addWidget(widget, row, col)
        _apply_widget_width_cap(widget, width_budget, plan.cols)
        if not widget.isVisible():
            widget.show()
    _apply_grid_stretch(grid, previous_cols, plan.cols)


def _apply_grid_stretch(grid: Any, previous_cols: Any, next_cols: int) -> None:
    if previous_cols == next_cols:
        return
    reset_until = max(LAYOUT_GRID_MAX_COLS, int(previous_cols or 0), int(next_cols or 0))
    for col in range(0, reset_until + 1):
        try:
            grid.setColumnStretch(col, 0)
        except Exception as exc:
            logger.debug("Falha ao resetar stretch de coluna no grid avancado: %s", exc)
    for col in range(0, max(1, int(next_cols))):
        try:
            grid.setColumnStretch(col, 1)
        except Exception as exc:
            logger.debug("Falha ao aplicar stretch de coluna no grid avancado: %s", exc)
