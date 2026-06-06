"""Multiselect menu construction for advanced filters."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from gui.qt_stubs import (
    QApplication,
    QCheckBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSignalBlocker,
    QScrollArea,
    QSizePolicy,
    Qt,
    QWidget,
    QWidgetAction,
    sip,
)
from utils.robust_logging import get_robust_logger

logger = get_robust_logger().get_logger(__name__, "gui")

SIMPLE_POPUP_TEXT_CLAMP = True
SIMPLE_POPUP_LABEL_MAX_PX = 300
SIMPLE_POPUP_RIGHT_GUTTER_PX = 10
SIMPLE_POPUP_SCROLLBAR_GUARD_PX = 18
HIGH_CARDINALITY_MENU_LIMIT = 160

@dataclass(frozen=True)
class MultiselectMenuModel:
    filter_name: str
    has_exclude_column: bool
    popup_width: int
    include_col_min: int
    exclude_col_min: int
    values: list[Any]
    total_values: int
    selected_norm: set[str]
    exclude_norm: set[str]
    label_display_by_key: dict[str, str]


@dataclass(frozen=True)
class MultiselectThemeTokens:
    popup_bg: str
    popup_text: str
    popup_border: str
    checked_bg: str
    checkbox_bg: str
    checkbox_border: str


def _get_widget_screen_geometry(widget):
    candidate_widgets = []
    if widget is not None:
        candidate_widgets.append(widget)
        try:
            window = widget.window()
        except Exception:
            window = None
        if window is not None and window is not widget:
            candidate_widgets.append(window)
    for candidate in candidate_widgets:
        try:
            handle = candidate.windowHandle()
            if handle is not None:
                screen = handle.screen()
                if screen is not None:
                    return screen.availableGeometry()
        except Exception as exc:
            logger.debug("Failed to get screen geometry from window handle: %s", exc)
        try:
            screen_at = getattr(QApplication, "screenAt", None)
            if callable(screen_at):
                screen = screen_at(candidate.mapToGlobal(candidate.rect().center()))
                if screen is not None:
                    return screen.availableGeometry()
        except Exception as exc:
            logger.debug("Failed to get screen geometry from widget center: %s", exc)
    try:
        screen = QApplication.primaryScreen()
        if screen is not None:
            return screen.availableGeometry()
    except Exception as exc:
        logger.debug("Failed to get primary screen geometry: %s", exc)
    return None

def _is_not_deleted(widget) -> bool:
    if widget is None:
        return False
    if sip is None:
        return True
    try:
        return not sip.isdeleted(widget)
    except RuntimeError:
        return False
    except TypeError:
        return True

def _build_multiselect_summary_candidates(
    selected_values,
    excluded_values,
    placeholder: str,
    total: int | None = None,
) -> list[str]:
    selected = [str(v) for v in (selected_values or []) if str(v).strip()]
    excluded = [str(v) for v in (excluded_values or []) if str(v).strip()]
    include_text = ", ".join(selected) if selected else ""
    exclude_text = ", ".join(excluded) if excluded else ""
    if total == 0 and not selected and not excluded:
        return ["Sem dados"]
    if not selected and not excluded:
        return [placeholder]
    if total is not None and len(selected) == total and not excluded:
        return ["Todos", f"Incluir: {include_text}"]
    if selected and excluded:
        return [
            f"Incluir: {include_text} | Diferente: {exclude_text}",
            f"{len(selected)} incluir, {len(excluded)} diferente",
            f"Incluir: {include_text}",
            f"Diferente: {exclude_text}",
        ]
    if selected:
        return [
            f"Incluir: {include_text}",
            "1 incluir" if len(selected) == 1 else f"{len(selected)} incluir",
        ]
    return [
        f"Diferente: {exclude_text}",
        "1 diferente" if len(excluded) == 1 else f"{len(excluded)} diferente",
    ]

def _attach_multiselect_menu(self, button, menu):
    if button is None or menu is None:
        return

    def _show_menu():
        if not _is_not_deleted(button) or not _is_not_deleted(menu):
            return
        try:
            self._run_menu_pre_show_hook(button)
        except Exception as exc:
            logger.debug("Falha no pre-show do menu multiselect: %s", exc)
        try:
            rect = button.rect()
            pos = button.mapToGlobal(rect.bottomLeft())
            try:
                menu_size = menu.sizeHint()
                screen = _get_widget_screen_geometry(button)
                if screen is not None:
                    if menu_size and pos.y() + menu_size.height() > screen.bottom():
                        pos = button.mapToGlobal(rect.topLeft())
                        pos.setY(pos.y() - menu_size.height())
                    if menu_size and pos.x() + menu_size.width() > screen.right():
                        pos.setX(
                            max(screen.left(), screen.right() - menu_size.width() - 4)
                        )
                    if pos.x() < screen.left():
                        pos.setX(screen.left() + 2)
                    if pos.y() < screen.top():
                        pos.setY(screen.top() + 2)
            except Exception as exc:
                logger.debug(
                    "Falha ao ajustar posicao do menu multiselect na tela: %s", exc
                )
            menu.exec(pos)
            return
        except Exception as exc:
            logger.warning("Falha ao abrir menu multiselect: %s", exc)

    try:
        button.clicked.connect(_show_menu)
    except Exception as exc:
        logger.warning("Falha ao conectar abertura de menu multiselect: %s", exc)

def _update_multiselect_button(
    self, button, checks, placeholder: str = "Selecionar", exclude_checks=None
):
    if not _is_not_deleted(button):
        return
    selected = _checked_values_from_checkboxes(checks)
    excluded = _checked_values_from_checkboxes(exclude_checks)
    total = len(checks or [])
    if total == 0 and not selected and not excluded:
        try:
            button.setText("Sem dados")
            button.setEnabled(False)
            button.setToolTip("Nenhum dado disponivel")
        except Exception as exc:
            logger.debug("Falha ao atualizar botao multiselect sem dados: %s", exc)
        return
    candidates = _build_multiselect_summary_candidates(
        selected,
        excluded,
        placeholder,
        total=total,
    )
    text = _fit_button_text(button, candidates, candidates[-1])
    try:
        button.setText(text)
        button.setEnabled(True)
        if selected or excluded:
            button.setToolTip(
                "Incluir: "
                + ", ".join(selected)
                + ("\nDiferente: " + ", ".join(excluded) if excluded else "")
            )
        else:
            button.setToolTip(placeholder if total > 0 else "Nenhum dado disponivel")
    except Exception as exc:
        logger.debug("Falha ao atualizar resumo/tooltip do botao multiselect: %s", exc)

def _fit_button_text(button, candidates, fallback: str) -> str:
    try:
        if not _is_not_deleted(button):
            return str(fallback)
        fm = button.fontMetrics()
        width = _safe_widget_width(button)
        available = max(24, width - 10)
        for text in candidates:
            if text and fm.horizontalAdvance(text) <= available:
                return text
        primary = next((str(item) for item in candidates if item), str(fallback))
        if fm.horizontalAdvance(primary) <= available:
            return primary
        elided = fm.elidedText(primary, Qt.TextElideMode.ElideRight, available)
        return elided or str(fallback)
    except Exception as exc:
        logger.debug("Falha ao ajustar texto de botao ao espaco disponivel: %s", exc)
        return str(fallback)

def _safe_widget_width(widget) -> int:
    if widget is None or not _is_not_deleted(widget):
        return 0
    try:
        width_fn = getattr(widget, "width", None)
        if callable(width_fn):
            value = int(width_fn() or 0)
            if value > 0:
                return value
    except Exception as exc:
        logger.debug("Falha ao medir largura atual de widget: %s", exc)
    try:
        size_hint_fn = getattr(widget, "sizeHint", None)
        if callable(size_hint_fn):
            hint = size_hint_fn()
            if hint is not None:
                value = int(hint.width() or 0)
                if value > 0:
                    return value
    except Exception as exc:
        logger.debug("Falha ao medir sizeHint de widget: %s", exc)
    try:
        minimum_width_fn = getattr(widget, "minimumWidth", None)
        if callable(minimum_width_fn):
            return max(0, int(minimum_width_fn() or 0))
    except Exception as exc:
        logger.debug("Falha ao medir largura minima de widget: %s", exc)
    return 0

def _palette_color_name(widget, palette_attr: str) -> str:
    if widget is None or not _is_not_deleted(widget):
        return ""
    try:
        palette = widget.palette()
        color_group = getattr(palette, palette_attr, None)
        if callable(color_group):
            color = color_group().color()
            name = color.name()
            if isinstance(name, str):
                value = name.strip()
                if value:
                    return value
    except Exception:
        return ""
    return ""

def _resolve_popup_theme_tokens(
    self, button, menu
) -> MultiselectThemeTokens:
    roles = getattr(self, "_current_theme_roles", None)
    if not isinstance(roles, dict):
        roles = {}
    popup_bg = (
        roles.get("popup_bg")
        or roles.get("panel_bg")
        or _palette_color_name(menu, "window")
        or _palette_color_name(button, "window")
    )
    popup_text = (
        roles.get("popup_text")
        or roles.get("panel_text")
        or roles.get("label_color")
        or _palette_color_name(menu, "windowText")
        or _palette_color_name(button, "windowText")
    )
    popup_border = (
        roles.get("popup_border")
        or roles.get("panel_border")
        or _palette_color_name(menu, "mid")
        or _palette_color_name(button, "mid")
    )
    checked_bg = (
        roles.get("checkbox_checked_bg")
        or roles.get("accent")
        or _palette_color_name(menu, "highlight")
    )
    checkbox_bg = roles.get("checkbox_bg") or popup_bg
    checkbox_border = roles.get("checkbox_border") or popup_border

    if not popup_bg:
        popup_bg = "palette(window)"
    if not popup_text:
        popup_text = "palette(window-text)"
    if not popup_border:
        popup_border = "palette(mid)"
    if not checked_bg:
        checked_bg = popup_border
    if not checkbox_bg:
        checkbox_bg = popup_bg
    if not checkbox_border:
        checkbox_border = popup_border
    return MultiselectThemeTokens(
        popup_bg=popup_bg,
        popup_text=popup_text,
        popup_border=popup_border,
        checked_bg=checked_bg,
        checkbox_bg=checkbox_bg,
        checkbox_border=checkbox_border,
    )

def _detect_filter_name_from_button(button) -> str:
    try:
        prop_value = button.property("filter_name") if button is not None else None
        if isinstance(prop_value, str):
            filter_name = prop_value.strip()
            if filter_name:
                return filter_name
    except Exception as exc:
        logger.debug("Falha ao ler propriedade filter_name do botao: %s", exc)
    return ""

def _multiselect_value_key_label(value) -> tuple[str, str]:
    if isinstance(value, (list, tuple)):
        key = value[0] if len(value) > 0 else ""
        label = value[1] if len(value) > 1 else key
    else:
        key = value
        label = value
    return str(key), str(label)

def _collect_limited_multiselect_values(
    values,
    selected_values_raw,
    exclude_values_raw,
) -> tuple[list[Any], int]:
    selected_norm = {str(v).casefold() for v in (selected_values_raw or ())}
    exclude_norm = {str(v).casefold() for v in (exclude_values_raw or ())}
    selected_keys = selected_norm | exclude_norm
    selected_display_by_key = {
        str(value).casefold(): value
        for value in tuple(selected_values_raw or ()) + tuple(exclude_values_raw or ())
    }
    selected_values = []
    found_selected_keys: set[str] = set()
    remaining = []
    total_values = 0
    for raw_value in values or ():
        key_text, label_text = _multiselect_value_key_label(raw_value)
        if not label_text or not label_text.strip():
            continue
        total_values += 1
        key = key_text.casefold()
        if key in selected_keys:
            selected_values.append(raw_value)
            found_selected_keys.add(key)
            continue
        if len(remaining) < HIGH_CARDINALITY_MENU_LIMIT:
            remaining.append(raw_value)
    for key in sorted(selected_keys - found_selected_keys):
        selected_values.append(selected_display_by_key.get(key, key))
    if total_values <= HIGH_CARDINALITY_MENU_LIMIT:
        return selected_values + remaining, total_values
    limit = max(0, HIGH_CARDINALITY_MENU_LIMIT - len(selected_values))
    return selected_values + remaining[:limit], total_values


def _compute_multiselect_popup_metrics(
    button,
    displayed_values,
    total_values: int,
    filter_name: str,
    has_exclude_column: bool,
):
    try:
        fm = button.fontMetrics() if button is not None else None
    except Exception:
        fm = None
    try:
        max_label_chars = max(
            len(_multiselect_value_key_label(value)[1]) for value in displayed_values
        )
        avg_char_px = 8
        if fm is not None:
            avg_char_px = max(7, min(10, fm.horizontalAdvance("MMMMmmmm") // 8))
        max_label_px = max_label_chars * avg_char_px
    except Exception:
        max_label_px = 64
    # Simple clamp for very long names in responsavel menus.
    # Easy rollback: set SIMPLE_POPUP_TEXT_CLAMP = False.
    if SIMPLE_POPUP_TEXT_CLAMP:
        max_label_px = min(max_label_px, SIMPLE_POPUP_LABEL_MAX_PX)
    content_width = max_label_px + (112 if has_exclude_column else 80)
    if filter_name:
        try:
            header_width = (
                fm.horizontalAdvance(filter_name)
                if fm is not None
                else (len(filter_name) * 8)
            )
        except Exception:
            header_width = len(filter_name) * 8
        header_extra = 144 if has_exclude_column else 34
        content_width = max(content_width, header_width + header_extra)
    include_col_min = 54
    exclude_col_min = 54
    if has_exclude_column and fm is not None:
        include_col_min = max(include_col_min, fm.horizontalAdvance("Incluir") + 12)
        exclude_col_min = max(exclude_col_min, fm.horizontalAdvance("Excluir") + 12)
        exclude_col_min += SIMPLE_POPUP_RIGHT_GUTTER_PX
        content_width = max(
            content_width,
            max_label_px + include_col_min + exclude_col_min + 48,
        )
        # Keep a small guard for vertical scrollbar in large lists.
        # Easy rollback: set SIMPLE_POPUP_SCROLLBAR_GUARD_PX = 0.
        if total_values > 9:
            content_width += SIMPLE_POPUP_SCROLLBAR_GUARD_PX
    popup_max_width = 680
    try:
        screen_geometry = _get_widget_screen_geometry(button)
        if screen_geometry is not None:
            screen_w = int(screen_geometry.width())
            if screen_w > 0:
                popup_max_width = max(420, min(960, int(screen_w * 0.72)))
    except Exception:
        popup_max_width = 680
    popup_width = max(220, min(popup_max_width, content_width))
    return popup_width, include_col_min, exclude_col_min

def _build_multiselect_menu_model(
    button,
    values,
    selected_set,
    exclude_selected_set,
    font_source=None,
) -> MultiselectMenuModel:
    selected_norm = {str(v).casefold() for v in (selected_set or [])}
    exclude_norm = {str(v).casefold() for v in (exclude_selected_set or [])}
    filter_name = _detect_filter_name_from_button(button)
    has_exclude_column = exclude_selected_set is not None
    limited_values, total_values = _collect_limited_multiselect_values(
        values,
        selected_set,
        exclude_selected_set,
    )
    popup_width, include_col_min, exclude_col_min = _compute_multiselect_popup_metrics(
        button,
        limited_values,
        total_values,
        filter_name,
        has_exclude_column,
    )
    label_display_by_key = _build_multiselect_label_display_map(
        font_source or button,
        limited_values,
    )
    return MultiselectMenuModel(
        filter_name=filter_name,
        has_exclude_column=has_exclude_column,
        popup_width=popup_width,
        include_col_min=include_col_min,
        exclude_col_min=exclude_col_min,
        values=limited_values,
        total_values=total_values,
        selected_norm=selected_norm,
        exclude_norm=exclude_norm,
        label_display_by_key=label_display_by_key,
    )

def _build_multiselect_label_display_map(button, values) -> dict[str, str]:
    if not SIMPLE_POPUP_TEXT_CLAMP:
        return {}
    try:
        fm_label = button.fontMetrics() if button is not None else None
        if fm_label is None:
            return {}
        return {
            key: fm_label.elidedText(
                label,
                Qt.TextElideMode.ElideRight,
                SIMPLE_POPUP_LABEL_MAX_PX,
            )
            for key, label in (_multiselect_value_key_label(value) for value in values)
        }
    except Exception:
        return {}

def _configure_multiselect_grid(
    grid,
    has_exclude_column: bool,
    include_col_min: int,
    exclude_col_min: int,
) -> None:
    grid.setContentsMargins(6, 4, 14 + SIMPLE_POPUP_RIGHT_GUTTER_PX, 4)
    grid.setHorizontalSpacing(6)
    grid.setVerticalSpacing(4)
    try:
        grid.setAlignment(Qt.AlignmentFlag.AlignTop)
    except Exception as exc:
        logger.debug("Falha ao alinhar grid do menu multiselect no topo: %s", exc)
    if has_exclude_column:
        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 0)
        grid.setColumnStretch(2, 0)
        grid.setColumnMinimumWidth(1, include_col_min)
        grid.setColumnMinimumWidth(2, exclude_col_min)
    else:
        grid.setColumnStretch(0, 1)

def _append_multiselect_header(
    grid,
    row_idx: int,
    *,
    filter_name: str,
    has_exclude_column: bool,
    include_col_min: int = 0,
    exclude_col_min: int = 0,
    popup_text: str,
) -> int:
    if not filter_name:
        return row_idx
    label_filter = QLabel(filter_name)
    try:
        label_filter.setStyleSheet("font-weight: bold; font-size: 11px;")
    except Exception as exc:
        logger.debug("Failed to style multiselect menu header label: %s", exc)
    grid.addWidget(label_filter, row_idx, 0)

    if has_exclude_column:
        label_inc = QLabel("Incluir")
        label_exc = QLabel("Excluir")
        try:
            label_style_inc = (
                "font-size: 10px;"
                f" color: {popup_text};"
                " padding: 1px 0px;"
            )
            label_style_exc = (
                "font-size: 10px;"
                f" color: {popup_text};"
                " padding: 1px 0px;"
            )
            label_inc.setStyleSheet(label_style_inc)
            label_exc.setStyleSheet(label_style_exc)
            label_inc.setAlignment(Qt.AlignmentFlag.AlignHCenter)
            label_exc.setAlignment(Qt.AlignmentFlag.AlignHCenter)
            if include_col_min > 0:
                label_inc.setMinimumWidth(include_col_min)
            if exclude_col_min > 0:
                label_exc.setMinimumWidth(exclude_col_min)
        except Exception as exc:
            logger.debug(
                "Falha ao estilizar header include/exclude do menu multiselect: %s",
                exc,
            )
        grid.addWidget(label_inc, row_idx, 1, alignment=Qt.AlignmentFlag.AlignHCenter)
        grid.addWidget(label_exc, row_idx, 2, alignment=Qt.AlignmentFlag.AlignHCenter)
    return row_idx + 1

def _append_multiselect_limit_notice(
    grid,
    row_idx: int,
    *,
    displayed_count: int,
    total_values: int,
    has_exclude_column: bool,
    popup_text: str,
) -> int:
    if total_values <= displayed_count:
        return row_idx
    limited_label = QLabel(
        f"Mostrando {displayed_count} de {total_values}. Refine o filtro."
    )
    try:
        limited_label.setStyleSheet(f"font-size: 10px; color: {popup_text};")
        limited_label.setToolTip(
            "A lista completa tem muitos itens; valores ja selecionados foram preservados."
        )
    except Exception as exc:
        logger.debug("Falha ao estilizar aviso de lista limitada: %s", exc)
    col_span = 3 if has_exclude_column else 1
    grid.addWidget(limited_label, row_idx, 0, 1, col_span)
    row_idx += 1

    header_sep = QFrame()
    header_sep.setFrameShape(QFrame.Shape.HLine)
    header_sep.setFrameShadow(QFrame.Shadow.Sunken)
    grid.addWidget(header_sep, row_idx, 0, 1, col_span)
    return row_idx + 1


def _build_multiselect_header_widget(
    model: MultiselectMenuModel,
    tokens: MultiselectThemeTokens,
) -> QWidget | None:
    if not model.filter_name:
        return None
    header = QWidget()
    layout = QGridLayout(header)
    layout.setContentsMargins(8, 4, 8, 2)
    layout.setHorizontalSpacing(6)
    layout.setVerticalSpacing(2)
    _configure_multiselect_grid(
        layout,
        has_exclude_column=model.has_exclude_column,
        include_col_min=model.include_col_min,
        exclude_col_min=model.exclude_col_min,
    )
    _append_multiselect_header(
        layout,
        0,
        filter_name=model.filter_name,
        has_exclude_column=model.has_exclude_column,
        include_col_min=model.include_col_min,
        exclude_col_min=model.exclude_col_min,
        popup_text=tokens.popup_text,
    )
    try:
        header.setStyleSheet(
            "QWidget {"
            f" background: {tokens.popup_bg};"
            f" color: {tokens.popup_text};"
            "}"
            "QLabel {"
            " font-size: 11px;"
            f" color: {tokens.popup_text};"
            "}"
        )
    except Exception as exc:
        logger.debug("Falha ao estilizar header fixo do menu multiselect: %s", exc)
    return header


def _build_multiselect_checkbox_styles(
    *,
    checkbox_bg: str,
    checkbox_border: str,
    checked_bg: str,
) -> tuple[str, str]:
    checkbox_style = (
        "QCheckBox::indicator {"
        " width:14px; height:14px;"
        f" border:1px solid {checkbox_border};"
        f" background:{checkbox_bg};"
        "}"
        "QCheckBox::indicator:checked {"
        f" border:1px solid {checked_bg};"
        f" background:{checked_bg};"
        "}"
        "QCheckBox::indicator:checked:hover {"
        f" background:{checked_bg};"
        "}"
        "QCheckBox::indicator:disabled {"
        f" border:1px solid {checkbox_border};"
        f" background:{checkbox_bg};"
        "}"
    )
    return checkbox_style, checkbox_style

def _add_multiselect_item_row(
    self,
    *,
    grid,
    row_idx: int,
    button,
    model: MultiselectMenuModel,
    value,
    popup_text: str,
    cb_style_include: str,
    cb_style_exclude: str,
    apply_checkbox_styles: bool,
    exclude_enabled: bool,
    on_toggle,
    on_exclude_toggle,
) -> tuple[int, QCheckBox, QCheckBox | None]:
    cb_value, label_text = _multiselect_value_key_label(value)
    label_text_display = model.label_display_by_key.get(cb_value, label_text)
    label = QLabel(label_text_display)
    try:
        label.setWordWrap(False)
        label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        label.setStyleSheet(f"font-size: 11px; color: {popup_text};")
        if label_text_display != label_text:
            label.setToolTip(label_text)
    except Exception as exc:
        logger.debug("Falha ao estilizar label do item no menu multiselect: %s", exc)
    include_cb = QCheckBox()
    exclude_cb = QCheckBox() if exclude_enabled else None
    cb_key = str(cb_value).casefold()
    _configure_multiselect_item_checkbox(
        include_cb,
        value=cb_value,
        checked=cb_key in model.selected_norm,
        style=cb_style_include if apply_checkbox_styles else "",
    )
    if exclude_cb is not None:
        _configure_multiselect_item_checkbox(
            exclude_cb,
            value=cb_value,
            checked=cb_key in model.exclude_norm,
            style=cb_style_exclude if apply_checkbox_styles else "",
        )
    grid.addWidget(label, row_idx, 0)
    grid.addWidget(include_cb, row_idx, 1, alignment=Qt.AlignmentFlag.AlignHCenter)
    if exclude_cb is not None:
        grid.addWidget(exclude_cb, row_idx, 2, alignment=Qt.AlignmentFlag.AlignHCenter)
        _connect_multiselect_exclusion_pair(
            self,
            include_cb,
            exclude_cb,
            on_toggle=on_toggle,
            on_exclude_toggle=on_exclude_toggle,
        )
    elif on_toggle is not None:
        _connect_checkbox_callback(include_cb, on_toggle, "on_toggle")
    return row_idx + 1, include_cb, exclude_cb

def _configure_multiselect_item_checkbox(
    checkbox,
    *,
    value,
    checked: bool,
    style: str,
) -> None:
    try:
        checkbox.setProperty("value", str(value))
        checkbox.setProperty("value_norm", str(value).casefold())
        if style:
            checkbox.setStyleSheet(style)
        checkbox.setChecked(bool(checked))
    except Exception as exc:
        logger.debug("Falha ao configurar checkbox do menu multiselect: %s", exc)

def _connect_checkbox_callback(checkbox, callback, label: str) -> None:
    if callback is None:
        return
    try:
        checkbox.toggled.connect(callback)
    except Exception as exc:
        logger.warning("Falha ao conectar callback %s do menu multiselect: %s", label, exc)

def _connect_multiselect_exclusion_pair(
    self,
    include_cb,
    exclude_cb,
    *,
    on_toggle,
    on_exclude_toggle,
) -> None:
    def _toggle_include(checked, other=exclude_cb):
        if getattr(self, "_multiselect_batch_updating", False):
            return
        if not checked or not _is_not_deleted(other):
            return
        try:
            if not other.isChecked():
                return
            with QSignalBlocker(other):
                other.setChecked(False)
        except Exception as exc:
            logger.debug("Falha ao limpar exclusao oposta no multiselect: %s", exc)

    def _toggle_exclude(checked, other=include_cb):
        if getattr(self, "_multiselect_batch_updating", False):
            return
        if not checked or not _is_not_deleted(other):
            return
        try:
            if not other.isChecked():
                return
            with QSignalBlocker(other):
                other.setChecked(False)
        except Exception as exc:
            logger.debug("Falha ao limpar inclusao oposta no multiselect: %s", exc)

    try:
        include_cb.toggled.connect(_toggle_include)
        exclude_cb.toggled.connect(_toggle_exclude)
    except Exception as exc:
        logger.warning(
            "Falha ao conectar mutual exclusion include/exclude no menu multiselect: %s",
            exc,
        )
    _connect_checkbox_callback(include_cb, on_toggle, "on_toggle")
    _connect_checkbox_callback(exclude_cb, on_exclude_toggle, "on_exclude_toggle")

def _notify_multiselect_batch_change(
    self,
    button,
    checks,
    exclude_checks,
    on_toggle,
    on_exclude_toggle,
    *,
    include_changed: bool,
    exclude_changed: bool,
) -> None:
    try:
        _update_multiselect_button(self, button, checks, exclude_checks=exclude_checks)
    except Exception as exc:
        logger.debug(
            "Falha ao atualizar resumo de botao apos lote no menu multiselect: %s", exc
        )
    if include_changed and callable(on_toggle):
        on_toggle()
    if exclude_changed and callable(on_exclude_toggle):
        on_exclude_toggle()

def _make_multiselect_batch_button(
    label: str,
    *,
    checkbox_bg: str,
    checkbox_border: str,
    checked_bg: str,
):
    button = QPushButton()
    try:
        button.setText("")
        button.setAccessibleName(label)
        button.setToolTip(label)
        button.setFixedSize(14, 14)
        button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        button.setStyleSheet(
            "QPushButton {"
            " min-width:14px; max-width:14px; min-height:14px; max-height:14px;"
            f" border:1px solid {checkbox_border}; background:{checkbox_bg};"
            " border-radius:2px; padding:0px;"
            "}"
            "QPushButton:pressed {"
            f" border:1px solid {checked_bg}; background:{checked_bg};"
            "}"
        )
    except Exception as exc:
        logger.debug("Falha ao configurar botao batch do multiselect: %s", exc)
    return button

def _apply_multiselect_batch_state(
    self,
    *,
    button,
    checks,
    exclude_checks,
    target_checks,
    opposite_checks,
    target_state: bool,
    include_callback,
    exclude_callback,
    include_changed: bool,
    exclude_changed: bool,
) -> None:
    self._multiselect_batch_updating = True
    try:
        if target_state:
            for cb in opposite_checks or ():
                if not _is_not_deleted(cb):
                    continue
                with QSignalBlocker(cb):
                    cb.setChecked(False)
        for cb in target_checks or ():
            if not _is_not_deleted(cb):
                continue
            with QSignalBlocker(cb):
                cb.setChecked(target_state)
    finally:
        self._multiselect_batch_updating = False
    _notify_multiselect_batch_change(
        self,
        button,
        checks,
        exclude_checks,
        include_callback,
        exclude_callback,
        include_changed=include_changed,
        exclude_changed=exclude_changed,
    )


def _append_multiselect_batch_controls(
    self,
    *,
    grid,
    row_idx,
    checks,
    exclude_checks,
    checkbox_bg: str,
    checkbox_border: str,
    checked_bg: str,
    popup_text: str,
    on_toggle,
    on_exclude_toggle,
    button,
):
    separator = QFrame()
    separator.setFrameShape(QFrame.Shape.HLine)
    separator.setFrameShadow(QFrame.Shadow.Sunken)
    grid.addWidget(separator, row_idx, 0, 1, 3)
    row_idx += 1

    batch_mark_include = _make_multiselect_batch_button(
        "Selecionar tudo para incluir",
        checkbox_bg=checkbox_bg,
        checkbox_border=checkbox_border,
        checked_bg=checked_bg,
    )
    batch_clear_include = _make_multiselect_batch_button(
        "Limpar tudo para incluir",
        checkbox_bg=checkbox_bg,
        checkbox_border=checkbox_border,
        checked_bg=checked_bg,
    )
    batch_mark_exclude = _make_multiselect_batch_button(
        "Selecionar tudo para excluir",
        checkbox_bg=checkbox_bg,
        checkbox_border=checkbox_border,
        checked_bg=checked_bg,
    )
    batch_clear_exclude = _make_multiselect_batch_button(
        "Limpar tudo para excluir",
        checkbox_bg=checkbox_bg,
        checkbox_border=checkbox_border,
        checked_bg=checked_bg,
    )

    label_mark = QLabel("Selecionar tudo")
    label_clear = QLabel("Limpar tudo")
    try:
        label_mark.setStyleSheet(f"font-size: 11px; color: {popup_text};")
        label_clear.setStyleSheet(f"font-size: 11px; color: {popup_text};")
    except Exception as exc:
        logger.debug(
            "Falha ao estilizar labels de marcacao em lote no menu multiselect: %s", exc
        )

    grid.addWidget(label_mark, row_idx, 0)
    grid.addWidget(
        batch_mark_include, row_idx, 1, alignment=Qt.AlignmentFlag.AlignHCenter
    )
    grid.addWidget(
        batch_mark_exclude, row_idx, 2, alignment=Qt.AlignmentFlag.AlignHCenter
    )
    row_idx += 1

    grid.addWidget(label_clear, row_idx, 0)
    grid.addWidget(
        batch_clear_include, row_idx, 1, alignment=Qt.AlignmentFlag.AlignHCenter
    )
    grid.addWidget(
        batch_clear_exclude, row_idx, 2, alignment=Qt.AlignmentFlag.AlignHCenter
    )
    row_idx += 1

    def _batch_set_include(
        target_state: bool,
        include_callback=on_toggle,
        exclude_callback=on_exclude_toggle,
    ):
        _apply_multiselect_batch_state(
            self,
            button=button,
            checks=checks,
            exclude_checks=exclude_checks,
            target_checks=checks,
            opposite_checks=exclude_checks,
            target_state=target_state,
            include_callback=include_callback,
            exclude_callback=exclude_callback,
            include_changed=True,
            exclude_changed=False,
        )

    def _batch_set_exclude(
        target_state: bool,
        include_callback=on_toggle,
        exclude_callback=on_exclude_toggle,
    ):
        _apply_multiselect_batch_state(
            self,
            button=button,
            checks=checks,
            exclude_checks=exclude_checks,
            target_checks=exclude_checks,
            opposite_checks=checks,
            target_state=target_state,
            include_callback=include_callback,
            exclude_callback=exclude_callback,
            include_changed=False,
            exclude_changed=True,
        )

    try:
        batch_mark_include.clicked.connect(lambda: _batch_set_include(True))
        batch_clear_include.clicked.connect(lambda: _batch_set_include(False))
        batch_mark_exclude.clicked.connect(lambda: _batch_set_exclude(True))
        batch_clear_exclude.clicked.connect(lambda: _batch_set_exclude(False))
    except Exception as exc:
        logger.debug(
            "Falha ao conectar acoes de marcacao em lote no menu multiselect: %s", exc
        )
    return row_idx

def _make_multiselect_scroll(
    *,
    container,
    model: MultiselectMenuModel,
    popup_bg: str,
    popup_text: str,
    popup_border: str,
    checked_bg: str,
    menu,
):
    scroll = QScrollArea()
    scroll.setWidget(container)
    scroll.setWidgetResizable(True)
    scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
    scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
    try:
        scroll.setAlignment(Qt.AlignmentFlag.AlignTop)
    except Exception as exc:
        logger.debug("Falha ao alinhar scroll do menu multiselect no topo: %s", exc)
    try:
        container.setStyleSheet(
            "QWidget {"
            f" background: {popup_bg};"
            f" color: {popup_text};"
            "}"
            "QLabel {"
            " font-size: 11px;"
            f" color: {popup_text};"
            "}"
        )
        scroll.setStyleSheet(
            "QScrollArea {"
            f" border: 1px solid {popup_border};"
            f" background: {popup_bg};"
            "}"
        )
        menu.setStyleSheet(
            "QMenu {"
            f" background: {popup_bg};"
            f" color: {popup_text};"
            f" border: 1px solid {popup_border};"
            "}"
            "QPushButton {"
            f" color: {popup_text};"
            f" background: {popup_bg};"
            f" border: 1px solid {popup_border};"
            " border-radius: 4px;"
            " padding: 2px 8px;"
            "}"
            "QPushButton:hover {"
            f" border: 1px solid {checked_bg};"
            "}"
        )
    except Exception as exc:
        logger.debug(
            "Falha ao aplicar estilo visual do scroll/menu multiselect: %s", exc
        )
    try:
        base_rows = len(model.values)
        if model.total_values > len(model.values):
            base_rows += 1
        if model.has_exclude_column:
            base_rows += 3
        visible_rows = max(1, min(8, base_rows))
        target_height = 8 + (visible_rows * 22)
        scroll.setFixedHeight(max(54, min(196, target_height)))
    except Exception as exc:
        logger.debug(
            "Falha ao ajustar altura dinamica do scroll no menu multiselect: %s", exc
        )
    return scroll

def _append_multiselect_scroll_action(menu, scroll) -> None:
    scroll_act = QWidgetAction(menu)
    scroll_act.setDefaultWidget(scroll)
    try:
        menu.addAction(scroll_act)
    except Exception as exc:
        logger.debug("Falha ao adicionar scroll action no menu multiselect: %s", exc)


def _append_multiselect_header_action(menu, header_widget) -> None:
    if header_widget is None:
        return
    try:
        header_widget.ensurePolished()
        header_height = max(1, int(header_widget.sizeHint().height() or 0))
        header_widget.setMinimumHeight(header_height)
        header_widget.setMaximumHeight(header_height)
        header_widget.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
        )
    except Exception as exc:
        logger.debug("Falha ao fixar altura do header do menu multiselect: %s", exc)
    header_act = QWidgetAction(menu)
    header_act.setDefaultWidget(header_widget)
    try:
        menu.addAction(header_act)
    except Exception as exc:
        logger.debug("Falha ao adicionar header fixo do menu multiselect: %s", exc)


def _append_multiselect_footer(menu, *, show_footer) -> None:
    if show_footer is None:
        return
    close_btn = QPushButton("Fechar")
    close_btn.setFixedWidth(88)
    close_btn.setToolTip("Fechar menu")
    try:
        close_btn.clicked.connect(menu.close)
    except Exception as exc:
        logger.debug("Falha ao conectar botao Fechar no menu multiselect: %s", exc)
    ok_row = QWidget()
    ok_layout = QHBoxLayout(ok_row)
    ok_layout.setContentsMargins(8, 4, 8, 6)
    ok_layout.setSpacing(6)
    ok_layout.addStretch()
    ok_layout.addWidget(close_btn)
    ok_layout.addStretch()
    ok_act = QWidgetAction(menu)
    ok_act.setDefaultWidget(ok_row)
    try:
        menu.addAction(ok_act)
    except Exception as exc:
        logger.debug("Falha ao adicionar rodape de acoes no menu multiselect: %s", exc)

def _try_reuse_multiselect_menu_cache(self, *, menu, button, signature):
    cached = getattr(menu, "_ssa_multiselect_cache", None)
    if not isinstance(cached, dict) or cached.get("signature") != signature:
        return None
    cached_checks = list(cached.get("checks") or [])
    cached_exclude_checks = list(cached.get("exclude_checks") or [])
    if not all(_is_not_deleted(check) for check in cached_checks):
        return None
    if not all(_is_not_deleted(check) for check in cached_exclude_checks):
        return None
    self._update_multiselect_button(
        button,
        cached_checks,
        exclude_checks=cached_exclude_checks,
    )
    return cached_checks, cached_exclude_checks

def _prepare_multiselect_menu(menu, model: MultiselectMenuModel) -> None:
    try:
        menu.clear()
    except Exception as exc:
        logger.debug("Falha ao limpar menu multiselect antes de reconstruir: %s", exc)
    try:
        menu.setMinimumWidth(model.popup_width)
        menu.setMaximumWidth(model.popup_width)
    except Exception as exc:
        logger.debug("Falha ao ajustar largura do menu multiselect: %s", exc)

def _build_multiselect_grid(model: MultiselectMenuModel):
    container = QWidget()
    grid = QGridLayout(container)
    _configure_multiselect_grid(
        grid,
        model.has_exclude_column,
        model.include_col_min,
        model.exclude_col_min,
    )
    return container, grid

def _configure_multiselect_checkbox_style(
    *,
    container,
    checkbox_bg: str,
    checkbox_border: str,
    checked_bg: str,
    value_count: int,
) -> tuple[str, str, bool]:
    apply_checkbox_styles = value_count <= HIGH_CARDINALITY_MENU_LIMIT
    try:
        cb_style_include, cb_style_exclude = _build_multiselect_checkbox_styles(
            checkbox_bg=checkbox_bg,
            checkbox_border=checkbox_border,
            checked_bg=checked_bg,
        )
    except Exception as exc:
        logger.debug("Falha ao gerar estilo de checkbox do menu multiselect: %s", exc)
        return "", "", apply_checkbox_styles
    if apply_checkbox_styles and cb_style_include:
        try:
            container.setStyleSheet(cb_style_include)
            apply_checkbox_styles = False
        except Exception as exc:
            logger.debug(
                "Falha ao aplicar estilo de checkbox no container multiselect: %s", exc
            )
    return cb_style_include, cb_style_exclude, apply_checkbox_styles

def _populate_multiselect_items(
    self,
    *,
    grid,
    row_idx: int,
    button,
    model: MultiselectMenuModel,
    popup_text: str,
    cb_style_include: str,
    cb_style_exclude: str,
    apply_checkbox_styles: bool,
    exclude_enabled: bool,
    on_toggle,
    on_exclude_toggle,
) -> tuple[int, list[QCheckBox], list[QCheckBox]]:
    checks: list[QCheckBox] = []
    exclude_checks: list[QCheckBox] = []
    for val in model.values:
        row_idx, include_cb, exclude_cb = _add_multiselect_item_row(
            self,
            grid=grid,
            row_idx=row_idx,
            button=button,
            model=model,
            value=val,
            popup_text=popup_text,
            cb_style_include=cb_style_include,
            cb_style_exclude=cb_style_exclude,
            apply_checkbox_styles=apply_checkbox_styles,
            exclude_enabled=exclude_enabled,
            on_toggle=on_toggle,
            on_exclude_toggle=on_exclude_toggle,
        )
        checks.append(include_cb)
        if exclude_cb is not None:
            exclude_checks.append(exclude_cb)
    return row_idx, checks, exclude_checks


def _multiselect_input_signature(
    owner,
    values,
    selected_set,
    exclude_selected_set,
    show_footer,
):
    try:
        value_count = len(values)
    except Exception:
        value_count = 0
    return (
        str(getattr(owner, "_current_theme", "") or ""),
        value_count,
        tuple(str(v) for v in (values or ())),
        frozenset(str(v).casefold() for v in (selected_set or ())),
        frozenset(str(v).casefold() for v in (exclude_selected_set or ())),
        bool(show_footer),
    )


class MultiselectMenuBuilder:
    def __init__(
        self,
        owner,
        button,
        menu,
        values,
        selected_set,
        *,
        on_toggle=None,
        show_footer=None,
        exclude_selected_set=None,
        on_exclude_toggle=None,
    ):
        self.owner = owner
        self.button = button
        self.menu = menu
        self.values = values
        self.selected_set = selected_set
        self.on_toggle = on_toggle
        self.show_footer = show_footer
        self.exclude_selected_set = exclude_selected_set
        self.on_exclude_toggle = on_exclude_toggle
        self.signature = _multiselect_input_signature(
            owner,
            values,
            selected_set,
            exclude_selected_set,
            show_footer,
        )

    def build(self):
        cached_result = _try_reuse_multiselect_menu_cache(
            self.owner,
            menu=self.menu,
            button=self.button,
            signature=self.signature,
        )
        if cached_result is not None:
            return cached_result
        model = _build_multiselect_menu_model(
            self.button,
            self.values,
            self.selected_set,
            self.exclude_selected_set,
            font_source=self.menu,
        )
        _prepare_multiselect_menu(self.menu, model)
        tokens = _resolve_popup_theme_tokens(self.owner, self.button, self.menu)
        header_widget = _build_multiselect_header_widget(model, tokens)
        container, grid = _build_multiselect_grid(model)
        row_idx, checks, exclude_checks = self._populate_grid(
            grid,
            container,
            model,
            tokens,
        )
        self._append_batch_controls(grid, row_idx, checks, exclude_checks, tokens)
        self._append_scroll_and_footer(header_widget, container, model, tokens)
        return self._store_result(checks, exclude_checks)

    def _populate_grid(
        self,
        grid,
        container,
        model: MultiselectMenuModel,
        tokens: MultiselectThemeTokens,
    ):
        row_idx = 0
        row_idx = _append_multiselect_limit_notice(
            grid,
            row_idx,
            displayed_count=len(model.values),
            total_values=model.total_values,
            has_exclude_column=model.has_exclude_column,
            popup_text=tokens.popup_text,
        )
        cb_style_include, cb_style_exclude, apply_checkbox_styles = (
            _configure_multiselect_checkbox_style(
                container=container,
                checkbox_bg=tokens.checkbox_bg,
                checkbox_border=tokens.checkbox_border,
                checked_bg=tokens.checked_bg,
                value_count=len(model.values),
            )
        )
        return _populate_multiselect_items(
            self.owner,
            grid=grid,
            row_idx=row_idx,
            button=self.button,
            model=model,
            popup_text=tokens.popup_text,
            cb_style_include=cb_style_include,
            cb_style_exclude=cb_style_exclude,
            apply_checkbox_styles=apply_checkbox_styles,
            exclude_enabled=self.exclude_selected_set is not None,
            on_toggle=self.on_toggle,
            on_exclude_toggle=self.on_exclude_toggle,
        )

    def _append_batch_controls(self, grid, row_idx, checks, exclude_checks, tokens):
        if self.exclude_selected_set is None:
            return
        _append_multiselect_batch_controls(
            self.owner,
            grid=grid,
            row_idx=row_idx,
            checks=checks,
            exclude_checks=exclude_checks,
            checkbox_bg=tokens.checkbox_bg,
            checkbox_border=tokens.checkbox_border,
            checked_bg=tokens.checked_bg,
            popup_text=tokens.popup_text,
            on_toggle=self.on_toggle,
            on_exclude_toggle=self.on_exclude_toggle,
            button=self.button,
        )

    def _append_scroll_and_footer(
        self,
        header_widget,
        container,
        model: MultiselectMenuModel,
        tokens: MultiselectThemeTokens,
    ) -> None:
        scroll = _make_multiselect_scroll(
            container=container,
            model=model,
            popup_bg=tokens.popup_bg,
            popup_text=tokens.popup_text,
            popup_border=tokens.popup_border,
            checked_bg=tokens.checked_bg,
            menu=self.menu,
        )
        _append_multiselect_header_action(self.menu, header_widget)
        _append_multiselect_scroll_action(self.menu, scroll)
        _append_multiselect_footer(self.menu, show_footer=self.show_footer)

    def _store_result(self, checks, exclude_checks):
        self.menu._ssa_multiselect_cache = {
            "signature": self.signature,
            "checks": checks,
            "exclude_checks": exclude_checks,
        }
        _update_multiselect_button(
            self.owner,
            self.button,
            checks,
            exclude_checks=exclude_checks,
        )
        if self.exclude_selected_set is not None:
            return checks, exclude_checks
        return checks, []


def _rebuild_multiselect_menu(
    self,
    button,
    menu,
    values,
    selected_set,
    on_toggle=None,
    show_footer=None,
    exclude_selected_set=None,
    on_exclude_toggle=None,
):
    return MultiselectMenuBuilder(
        self,
        button,
        menu,
        values,
        selected_set,
        on_toggle=on_toggle,
        show_footer=show_footer,
        exclude_selected_set=exclude_selected_set,
        on_exclude_toggle=on_exclude_toggle,
    ).build()

def _checkbox_value(*args) -> str:
    checkbox = args[-1] if args else None
    if checkbox is None:
        return ""
    try:
        value = checkbox.property("value")
        if value is not None:
            return str(value)
    except Exception as exc:
        logger.debug(
            "Falha ao obter propriedade 'value' do checkbox em _checkbox_value: %s", exc
        )
    try:
        text = checkbox.text()
        if text:
            return text
    except Exception as exc:
        logger.debug("Falha ao obter texto do checkbox em _checkbox_value: %s", exc)
    return ""


def _checked_values_from_checkboxes(checks) -> list[str]:
    values: list[str] = []
    for checkbox in checks or []:
        try:
            if not _is_not_deleted(checkbox):
                continue
            is_checked = getattr(checkbox, "isChecked", None)
            if not callable(is_checked) or not is_checked():
                continue
            value = _checkbox_value(checkbox)
            if value:
                values.append(value)
        except Exception as exc:
            logger.debug("Failed to read multiselect checkbox value: %s", exc)
    return values


def _sync_multiselect_checks(
    self, button, checks, selected, exclude_checks=None, exclude_selected=None
):
    selected_set = {str(v).casefold() for v in (selected or [])}
    for cb in checks or []:
        try:
            value_norm = cb.property("value_norm") or _checkbox_value(cb).casefold()
            cb.setChecked(str(value_norm) in selected_set)
        except Exception as exc:
            logger.debug(
                "Falha ao sincronizar checkbox include em multiselect: %s", exc
            )
    exclude_set = {str(v).casefold() for v in (exclude_selected or [])}
    for cb in exclude_checks or []:
        try:
            value_norm = cb.property("value_norm") or _checkbox_value(cb).casefold()
            cb.setChecked(str(value_norm) in exclude_set)
        except Exception as exc:
            logger.debug(
                "Falha ao sincronizar checkbox exclude em multiselect: %s", exc
            )
    _update_multiselect_button(self, button, checks, exclude_checks=exclude_checks)


def _sync_include_exclude_multiselect_checks(
    self,
    *,
    button,
    include_checks,
    include_values,
    exclude_checks,
    exclude_values,
) -> None:
    _sync_multiselect_checks(
        self,
        button,
        include_checks,
        include_values,
        exclude_checks,
        exclude_values,
    )
