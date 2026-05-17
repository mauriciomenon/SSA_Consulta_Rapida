"""Column filter panel construction for the SSA GUI."""

from __future__ import annotations

from collections import OrderedDict
from contextlib import contextmanager
from typing import Any

from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMenu,
    QPushButton,
    QSizePolicy,
    QWidget,
)

from gui.gui_config import COMPATIBILITY_NULL_UI_COLUMNS
from utils.robust_logging import get_robust_logger

logger = get_robust_logger().get_logger(__name__, "gui")


@contextmanager
def _blocked_widget_signals(widget: Any, *, log_context: str):
    previous_state = False
    try:
        previous_state = bool(widget.blockSignals(True))
    except RuntimeError as exc:
        logger.debug("Widget destruido ao bloquear sinais em %s: %s", log_context, exc)
        yield
        return
    try:
        yield
    finally:
        try:
            widget.blockSignals(previous_state)
        except Exception as exc:
            logger.debug("Falha ao reativar sinais em %s: %s", log_context, exc)


def build_column_filters_panel(window) -> None:
    target_layout = _resolve_column_filters_layout(window)
    if target_layout is None:
        return

    row_pool = getattr(window, "_column_filter_row_pool", None)
    if not isinstance(row_pool, dict):
        row_pool = {}
        window._column_filter_row_pool = row_pool
    pending_focused_text = window._capture_focused_column_filter_text()
    _clear_column_filters_layout(target_layout)
    window._column_filter_inputs = {}
    window._column_filter_labels = {}
    if not hasattr(window, "_hidden_column_filter_lines"):
        window._hidden_column_filter_lines = set()

    if not window._active_column_filters:
        window._active_column_filters = OrderedDict(
            (col, "") for col in window._column_filter_default_columns()
        )

    min_label_column_width = _column_filter_min_label_width(window)
    for col, term in window._active_column_filters.items():
        if (
            hasattr(window, "_hidden_column_filter_lines")
            and col in window._hidden_column_filter_lines
        ):
            continue
        display_term = pending_focused_text.get(col, term)
        target_layout.addWidget(
            _build_column_filter_row_widget(window, col, display_term, min_label_column_width)
        )

    window._update_col_filter_indicator()
    _restore_pending_column_filter_focus(window)
    window._refresh_column_filter_widgets()
    _ensure_column_filters_footer(window, target_layout)
    target_layout.addStretch()
    _sync_bottom_panel_heights(window)


def open_add_column_filter_menu(window) -> None:
    menu = QMenu(window if isinstance(window, QWidget) else None)
    columns = []
    candidates = []
    canonical_provider = getattr(window, "_get_canonical_available_columns", None)
    if callable(canonical_provider):
        try:
            candidates.extend(canonical_provider())
        except Exception as exc:
            logger.debug(
                "Falha ao obter lista canonica de colunas para menu de filtros: %s",
                exc,
            )
    candidates.extend((window._active_column_filters or {}).keys())

    seen = set()
    try:
        window._last_unmapped_alias_columns = window._find_unmapped_alias_columns(
            candidates
        )
    except Exception as exc:
        logger.debug("Falha ao mapear colunas sem alias: %s", exc)
        window._last_unmapped_alias_columns = []
    legacy_invalid_columns = {
        "Número da SSA",
        "Numero da SSA",
        "No SSA",
        "Data Cadastro",
    }
    valid_cols = []
    for col in candidates:
        if not isinstance(col, str) or not col or col == "#" or col in seen:
            continue
        if col in COMPATIBILITY_NULL_UI_COLUMNS:
            continue
        if col in legacy_invalid_columns:
            continue
        display = window._resolve_column_display_name(col)
        if str(display).strip() == "No SSA" and col != "numero_ssa":
            continue
        seen.add(col)
        valid_cols.append(col)

    pinned = []
    pinned_seen = set()
    for col in getattr(window, "_current_display_columns", []) or []:
        if col in valid_cols and col not in pinned_seen:
            pinned.append(col)
            pinned_seen.add(col)
    for col in window._active_column_filters.keys():
        if col in valid_cols and col not in pinned_seen:
            pinned.append(col)
            pinned_seen.add(col)
    remaining = [c for c in valid_cols if c not in pinned_seen]
    remaining.sort(key=lambda c: window._expand_column_alias_for_filter(c).casefold())
    ordered_cols = pinned + remaining

    label_counts = {}
    for col in ordered_cols:
        display = window._expand_column_alias_for_filter(col)
        key = str(display).strip().casefold()
        label_counts[key] = label_counts.get(key, 0) + 1
    for col in ordered_cols:
        display = window._expand_column_alias_for_filter(col)
        display_text = str(display)
        if label_counts.get(display_text.strip().casefold(), 0) > 1:
            display_text = f"{display_text} [{col}]"
        action = menu.addAction(display_text)
        if action is None:
            continue
        action.setCheckable(True)
        action.setChecked(col in window._active_column_filters)
        action.setData(col)
        columns.append(action)
    if not columns:
        menu.deleteLater()
        return
    button = window.add_column_filter_btn
    chosen = menu.exec(button.mapToGlobal(button.rect().bottomLeft()))
    if chosen is None:
        return
    col_name = chosen.data()
    if not col_name:
        return
    if col_name in window._active_column_filters:
        window._deactivate_column_filter(col_name)
    else:
        window._activate_column_filter(col_name)


def _resolve_column_filters_layout(window):
    if hasattr(window, "col_filters_list_layout"):
        return window.col_filters_list_layout
    if hasattr(window, "col_filters_layout"):
        return window.col_filters_layout
    return None


def _clear_column_filters_layout(target_layout) -> None:
    while target_layout.count():
        item = target_layout.takeAt(0)
        widget = item.widget()
        if widget:
            widget.setVisible(False)
            widget.setParent(None)


def _column_filter_min_label_width(window) -> int:
    font_obj = _window_info_font(window)
    font_key = None
    if font_obj is not None:
        try:
            font_key = (
                str(font_obj.family()),
                int(font_obj.pointSize()),
                int(font_obj.pixelSize()),
                bool(font_obj.bold()),
            )
        except Exception:
            font_key = None
    cached_label_width = getattr(window, "_column_filter_label_width", None)
    cached_label_width_key = getattr(window, "_column_filter_label_width_key", None)
    min_label_column_width = cached_label_width
    if isinstance(min_label_column_width, int) and cached_label_width_key == font_key:
        return min_label_column_width
    min_label_column_width = 100
    try:
        ref_name = _expand_column_alias_for_filter(window, "descricao_execucao")
        ref_probe = QLabel(ref_name)
        if font_obj is not None:
            ref_probe.setFont(font_obj)
        ref_metrics = ref_probe.fontMetrics()
        ref_width = int(ref_metrics.horizontalAdvance(ref_name) + 16)
        min_label_column_width = max(100, min(260, ref_width))
        window._column_filter_label_width = min_label_column_width
        window._column_filter_label_width_key = font_key
    except Exception as exc:
        logger.debug(
            "Falha ao calcular largura minima de labels de filtro: %s",
            exc,
        )
    return min_label_column_width


def _build_column_filter_row_widget(
    window,
    col: str,
    term: Any,
    min_label_column_width: int,
) -> QWidget:
    row_pool = getattr(window, "_column_filter_row_pool", None)
    if not isinstance(row_pool, dict):
        row_pool = {}
        window._column_filter_row_pool = row_pool
    full_name = _expand_column_alias_for_filter(window, col)
    try:
        formatter = getattr(window, "_format_column_filter_display_value", None)
        if callable(formatter):
            display_text = formatter(str(term), column=col)
        else:
            display_text = str(term)
    except Exception:
        display_text = str(term)
    pooled = row_pool.get(col)
    if isinstance(pooled, dict):
        row_w = pooled.get("row_widget")
        name_lbl = pooled.get("label")
        term_box = pooled.get("input")
        if (
            isinstance(row_w, QWidget)
            and isinstance(name_lbl, QLabel)
            and isinstance(term_box, QLineEdit)
        ):
            name_lbl.setText(full_name)
            _configure_column_filter_label(
                window, name_lbl, col, full_name, min_label_column_width
            )
            with _blocked_widget_signals(term_box, log_context=f"reuse_column_filter_{col}"):
                term_box.setText(display_text)
            window._column_filter_labels[col] = name_lbl
            window._column_filter_inputs[col] = term_box
            row_w.setVisible(True)
            return row_w
    return _create_column_filter_row_widget(
        window, col, full_name, display_text, min_label_column_width, row_pool
    )


def _window_info_font(window):
    font_obj = getattr(window, "_info_font", None)
    if font_obj is not None:
        return font_obj
    font_method = getattr(window, "font", None)
    if callable(font_method):
        try:
            return font_method()
        except Exception as exc:
            logger.debug("Falha ao obter fonte da janela de filtros por coluna: %s", exc)
    return None


def _expand_column_alias_for_filter(window, column_name: str) -> str:
    expander = getattr(window, "_expand_column_alias_for_filter", None)
    if callable(expander):
        try:
            return str(expander(column_name))
        except Exception as exc:
            logger.debug(
                "Falha ao expandir nome do filtro de coluna %s: %s",
                column_name,
                exc,
            )
    return str(column_name)


def _create_column_filter_row_widget(
    window,
    col: str,
    full_name: str,
    display_text: str,
    min_label_column_width: int,
    row_pool: dict,
) -> QWidget:
    row = QHBoxLayout()
    row.setContentsMargins(0, 0, 0, 0)
    row.setSpacing(4)
    name_lbl = QLabel(full_name)
    window._column_filter_labels[col] = name_lbl
    _configure_column_filter_label(window, name_lbl, col, full_name, min_label_column_width)
    term_box = QLineEdit(display_text)
    window._column_filter_inputs[col] = term_box
    _configure_column_filter_input(term_box, col)
    window._apply_filter_widget_theme(name_lbl, term_box)
    apply_btn = _build_column_filter_button("↵", col, tooltip="Aplicar filtro desta coluna.")
    clear_btn = _build_column_filter_button(
        "⌫",
        col,
        tooltip="Limpa o valor desta coluna e reaplica os filtros.",
    )
    hide_btn = _build_column_filter_button(
        "Ocultar",
        col,
        tooltip="Oculta a linha somente quando o filtro da coluna estiver vazio.",
    )
    _connect_column_filter_row_actions(window, col, term_box, apply_btn, clear_btn, hide_btn)
    row.addWidget(name_lbl)
    row.addWidget(term_box, 1)
    row.addWidget(apply_btn)
    row.addWidget(clear_btn)
    row.addWidget(hide_btn)
    row_w = QWidget()
    row_w.setLayout(row)
    row_pool[col] = {
        "row_widget": row_w,
        "label": name_lbl,
        "input": term_box,
        "apply": apply_btn,
        "clear": clear_btn,
        "hide": hide_btn,
    }
    return row_w


def _configure_column_filter_label(
    window,
    label: QLabel,
    col: str,
    full_name: str,
    min_label_column_width: int,
) -> None:
    try:
        width_cache = getattr(window, "_column_filter_label_width_cache", None)
        if not isinstance(width_cache, dict):
            width_cache = {}
            window._column_filter_label_width_cache = width_cache
        label_font = label.font()
        cache_key = (
            str(full_name),
            int(min_label_column_width),
            label_font.family(),
            int(label_font.pointSize()),
            int(label_font.weight()),
        )
        dynamic_width = width_cache.get(cache_key)
        if not isinstance(dynamic_width, int):
            label_metrics = label.fontMetrics()
            desired_width = int(label_metrics.horizontalAdvance(full_name) + 16)
            dynamic_width = max(78, min(150, desired_width))
            width_cache[cache_key] = dynamic_width
        label.setMinimumWidth(max(min_label_column_width, dynamic_width))
    except Exception as exc:
        logger.debug(
            "Falha ao ajustar largura do label do filtro de coluna %s: %s",
            col,
            exc,
        )
        label.setMinimumWidth(min_label_column_width)
    try:
        label.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
    except Exception as exc:
        logger.debug(
            "Falha ao aplicar size policy no label do filtro de coluna %s: %s",
            col,
            exc,
        )


def _configure_column_filter_input(term_box: QLineEdit, col: str) -> None:
    term_box.setPlaceholderText(
        "Termos separados por virgula sao alternativas. Modos: foo, ^pre, suf$, =exato, ~^regex, !neg"
    )
    term_box.setMinimumWidth(220)
    try:
        term_box.setMinimumHeight(26)
    except Exception as exc:
        logger.debug(
            "Falha ao aplicar altura minima no input do filtro de coluna %s: %s",
            col,
            exc,
        )
    try:
        term_box.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
    except Exception as exc:
        logger.debug(
            "Falha ao aplicar size policy no input do filtro de coluna %s: %s",
            col,
            exc,
        )


def _build_column_filter_button(
    text: str,
    col: str,
    *,
    tooltip: str | None = None,
) -> QPushButton:
    button = QPushButton(text)
    try:
        button.setMinimumHeight(26)
        button.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        button.setFixedWidth(42 if len(text) <= 2 else 70)
        if tooltip:
            button.setToolTip(tooltip)
    except Exception as exc:
        logger.debug(
            "Falha ao configurar botao %s do filtro de coluna %s: %s",
            text,
            col,
            exc,
        )
    return button


def _connect_column_filter_row_actions(
    window,
    col: str,
    term_box: QLineEdit,
    apply_btn: QPushButton,
    clear_btn: QPushButton,
    hide_btn: QPushButton,
) -> None:
    def apply_current_text() -> None:
        new_text = str(term_box.text()).strip()
        current_text = str(window._active_column_filters.get(col, "")).strip()
        if new_text == current_text:
            window._sync_or_group_values(col, new_text)
            build_column_filters_panel(window)
            window._refresh_after_filter_change()
            window._sync_clear_filter_button_state()
            return
        window._safe_store_last_filter_state("apply_column_filter")
        window._active_column_filters[col] = new_text
        window._sync_or_group_values(col, new_text)
        window._mark_profile_as_custom()
        build_column_filters_panel(window)
        window._refresh_after_filter_change()
        window._sync_clear_filter_button_state()

    def clear_current_text() -> None:
        current_text = str(window._active_column_filters.get(col, "")).strip()
        typed_raw = str(term_box.text())
        if not current_text and not typed_raw:
            return
        window._safe_store_last_filter_state("clear_column_filter_value")
        window._active_column_filters[col] = ""
        window._sync_or_group_values(col, "")
        with _blocked_widget_signals(term_box, log_context=f"clear_column_filter_{col}"):
            term_box.setText("")
        window._mark_profile_as_custom()
        build_column_filters_panel(window)
        window._refresh_after_filter_change()
        window._sync_clear_filter_button_state()

    try:
        term_box.returnPressed.connect(apply_current_text)
        apply_btn.clicked.connect(apply_current_text)
        clear_btn.clicked.connect(clear_current_text)
        hide_btn.clicked.connect(
            lambda _checked=False, column=col: window._try_hide_column_filter_line(column)
        )
    except Exception as exc:
        logger.debug("Falha ao conectar controles do filtro de coluna %s: %s", col, exc)


def _restore_pending_column_filter_focus(window) -> None:
    focus_col = window._pending_filter_focus
    if focus_col and focus_col in window._column_filter_inputs:
        try:
            widget = window._column_filter_inputs[focus_col]
            widget.setFocus()
            widget.selectAll()
        except Exception as exc:
            logger.debug(
                "Falha ao focar campo do filtro de coluna %s: %s",
                focus_col,
                exc,
            )
    window._pending_filter_focus = None


def _ensure_column_filters_footer(window, target_layout) -> None:
    if hasattr(window, "clear_all_btn"):
        return
    clear_all = QPushButton("Limpar todos filtros de colunas")
    clear_all.setMaximumWidth(260)
    clear_all.clicked.connect(window._clear_all_column_filters)
    footer = QHBoxLayout()
    footer.addStretch()
    footer.addWidget(clear_all)
    footer.addStretch()
    row_w = QWidget()
    row_w.setLayout(footer)
    target_layout.addWidget(row_w)


def _sync_bottom_panel_heights(window) -> None:
    try:
        sync_heights = getattr(window, "_sync_bottom_panel_heights", None)
        if callable(sync_heights):
            sync_heights()
    except Exception as exc:
        logger.debug(
            "Falha ao sincronizar altura dos paineis inferiores apos rebuild de filtros por coluna: %s",
            exc,
        )
