# gui/ssa/gui_theme.py
# Relation: used by gui/gui_ssa.py (SSAMainWindow facade).
# Relation: depends on gui/helpers/theme_helpers.py and utils/themes.py.
# Relation: does not touch data loading or filters.

from __future__ import annotations

import os
import sys

from core.config_manager import atomic_write_json_file
from gui.gui_config import get_gui_main_preferences_path
from utils.robust_logging import get_robust_logger
from utils.themes import get_palette, get_theme_roles, normalize_theme

logger = get_robust_logger().get_logger(__name__, "gui")


def _set_stylesheet_if_changed(widget, stylesheet: str) -> None:
    current = str(widget.styleSheet() or "")
    if current != stylesheet:
        widget.setStyleSheet(stylesheet)


def get_theme_catalog():
    light_themes = [
        ("Classico", "classico"),
        ("Mint Light", "mint-light"),
        ("Paper", "paper"),
        ("Solarized Light", "solarized-light"),
        ("Windows 7", "windows7"),
    ]
    dark_themes = [
        ("Catppuccin (Mocha)", "catppuccin"),
        ("Dark", "dark"),
        ("Dracula", "dracula"),
        ("Grayscale", "grayscale"),
        ("Gruvbox", "gruvbox"),
        ("Nord", "nord"),
        ("Solarized Dark", "solarized-dark"),
        ("Tokyo Night", "tokyo-night"),
    ]
    return light_themes, dark_themes


def get_theme_keys():
    light_themes, dark_themes = get_theme_catalog()
    return {key for _, key in light_themes + dark_themes}


def resolve_startup_theme(gui_settings: dict) -> str:
    theme_default = gui_settings.get("theme_default")
    last_theme = gui_settings.get("theme")
    theme_keys = get_theme_keys()
    for candidate in (theme_default, last_theme, "gruvbox"):
        if isinstance(candidate, str) and candidate.strip():
            normalized = normalize_theme(candidate)
            if normalized in theme_keys:
                return normalized
    return "gruvbox"


def persist_gui_preferences(
    gui_prefs: dict, project_root: str, *, retries: int = 1
) -> bool:
    _ = project_root
    attempts = max(0, int(retries or 0)) + 1
    for attempt in range(attempts):
        try:
            atomic_write_json_file(
                get_gui_main_preferences_path(),
                gui_prefs,
                indent=2,
                ensure_ascii=False,
            )
            return True
        except Exception as exc:
            logger.warning(
                "Falha ao persistir preferencias GUI (tentativa %s/%s): %s",
                attempt + 1,
                attempts,
                exc,
            )
    return False


def show_theme_selection_dialog(window, *, gui_prefs: dict, project_root: str) -> None:
    from PyQt6.QtWidgets import (
        QCheckBox,
        QComboBox,
        QDialog,
        QDialogButtonBox,
        QLabel,
        QVBoxLayout,
    )

    light_themes, dark_themes = get_theme_catalog()
    gui_settings = gui_prefs.get("gui_settings", {})
    theme_default = gui_settings.get("theme_default")
    current_theme = normalize_theme(
        getattr(window, "_current_theme", "") or theme_default or "gruvbox"
    )
    is_default_theme = normalize_theme(theme_default or "") == current_theme

    dialog = QDialog(window)
    dialog.setWindowTitle("Selecionar Tema")
    dialog.setModal(True)

    layout = QVBoxLayout(dialog)
    info_label = QLabel("Escolha um tema para a interface.")
    layout.addWidget(info_label)

    theme_combo = QComboBox(dialog)
    selected_index = 0
    idx = 0
    for label, key in sorted(light_themes, key=lambda item: item[0].lower()):
        theme_combo.addItem(f"Light - {label}", key)
        if normalize_theme(key) == current_theme:
            selected_index = idx
        idx += 1
    for label, key in sorted(dark_themes, key=lambda item: item[0].lower()):
        theme_combo.addItem(f"Dark - {label}", key)
        if normalize_theme(key) == current_theme:
            selected_index = idx
        idx += 1
    theme_combo.setCurrentIndex(selected_index)
    layout.addWidget(theme_combo)

    default_checkbox = QCheckBox("Usar tema selecionado como padrao", dialog)
    default_checkbox.setChecked(is_default_theme)
    layout.addWidget(default_checkbox)

    buttons = QDialogButtonBox(
        QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel,
        parent=dialog,
    )
    buttons.accepted.connect(dialog.accept)
    buttons.rejected.connect(dialog.reject)
    layout.addWidget(buttons)

    if dialog.exec() != QDialog.DialogCode.Accepted:
        return

    selected_theme_key = normalize_theme(str(theme_combo.currentData() or "gruvbox"))
    try:
        window.apply_theme(selected_theme_key)
    except Exception as exc:
        logger.warning(
            "Falha ao aplicar tema selecionado '%s': %s", selected_theme_key, exc
        )
        return

    gui_settings = gui_prefs.setdefault("gui_settings", {})
    default_changed = False
    if default_checkbox.isChecked():
        default_changed = normalize_theme(
            str(gui_settings.get("theme_default") or "")
        ) != selected_theme_key
        if default_changed:
            gui_settings["theme_default"] = selected_theme_key
    if default_changed:
        persist_gui_preferences(gui_prefs, project_root)


def _apply_global_palette(window, normalized: str, same_theme: bool):
    from gui.helpers import build_global_widget_qss

    if same_theme:
        return window.palette()
    try:
        from PyQt6.QtWidgets import QApplication, QStyleFactory

        app_instance = QApplication.instance()
        app = app_instance if isinstance(app_instance, QApplication) else None
        pal = get_palette(normalized)
        try:
            if app is not None:
                styles = QStyleFactory.keys()
                if styles and "Fusion" in styles:
                    app.setStyle("Fusion")
        except Exception as exc:
            logger.debug("Falha ao forcar estilo Fusion na aplicacao: %s", exc)
        if app is not None:
            app.setPalette(pal)
            try:
                cached_theme_name = str(
                    getattr(window, "_last_global_theme_name", "") or ""
                )
                cached_qss = getattr(window, "_last_global_theme_qss", None)
                if (
                    cached_theme_name != normalized
                    or not isinstance(cached_qss, str)
                    or not cached_qss
                ):
                    block = build_global_widget_qss(pal)
                    current_app_qss = str(app.styleSheet() or "")
                    if current_app_qss != block:
                        app.setStyleSheet(block)
                    window._last_global_theme_qss = block
                window._last_global_theme_name = normalized
            except Exception as exc:
                logger.debug("Falha ao aplicar QSS global do tema: %s", exc)
        window.setPalette(pal)
        return pal
    except Exception as exc:  # noqa: BLE001
        logger.debug(
            "Falha ao aplicar paleta global do tema '%s'; seguindo fallback local: %s",
            normalized,
            exc,
        )
        pal = get_palette(normalized)
        window.setPalette(pal)
        return pal


def _apply_central_widget_theme(window, normalized: str, pal) -> None:
    from gui.helpers import build_central_widget_qss

    try:
        central = window.centralWidget()
        if central is not None:
            existing = central.styleSheet() or ""
            start = existing.find("/* SSA_MAIN_BG_START */")
            if start != -1:
                end = existing.find("/* SSA_MAIN_BG_END */", start)
                if end != -1:
                    end += len("/* SSA_MAIN_BG_END */")
                    existing = (existing[:start] + existing[end:]).rstrip()
                else:
                    existing = existing[:start].rstrip()
            normalized_name = normalize_theme(normalized)
            if normalized_name in {
                "grayscale",
                "gruvbox",
                "dark",
                "dracula",
                "solarized-dark",
                "tokyo-night",
                "catppuccin",
                "nord",
            }:
                bg = pal.window().color().name()
                block = build_central_widget_qss(bg)
                new_css = existing
                if new_css:
                    if not new_css.endswith("\n"):
                        new_css += "\n"
                    new_css += block
                else:
                    new_css = block
                if central.styleSheet() != new_css:
                    central.setStyleSheet(new_css)
            else:
                if central.styleSheet() != existing:
                    central.setStyleSheet(existing)
    except Exception as exc:
        logger.warning("Falha ao aplicar tema no central widget: %s", exc)


def _apply_tabs_theme(window, pal, roles: dict) -> None:
    try:
        if hasattr(window, "main_tabs") and window.main_tabs is not None:
            from PyQt6.QtGui import QPalette as _QPal

            tab_bg = pal.color(_QPal.ColorRole.Window).name()
            tab_text = pal.color(_QPal.ColorRole.WindowText).name()
            tab_mid = pal.color(_QPal.ColorRole.Mid).name()
            accent = roles.get("accent", tab_text)
            support_color = roles.get("support_text_color", tab_text)
            tab_css = (
                "QTabWidget::pane {"
                f" border:1px solid {tab_mid};"
                f" background:{tab_bg};"
                " margin:0; padding:0;"
                " }"
                "QTabBar::tab {"
                f" color:{support_color}; background:{tab_bg};"
                " padding:4px 10px; font-weight:500; border:1px solid transparent;"
                " }"
                "QTabBar::tab:selected {"
                f" color:{tab_text}; font-weight:600; background:{tab_bg};"
                f" border:1px solid {accent}; border-bottom:2px solid {accent};"
                " margin-bottom:-1px; margin-top:1px;"
                " }"
                "QTabBar::tab:!selected {"
                f" color:{support_color};"
                " }"
            )
            window.main_tabs.setStyleSheet(tab_css)
    except Exception as exc:
        logger.warning("Falha ao aplicar estilo de tabs no tema atual: %s", exc)


def _apply_table_header_theme(window) -> None:
    try:
        header = window.table_widget.horizontalHeader()
        header.setStyleSheet("QHeaderView::section{font-weight: normal;}")
    except Exception as exc:
        logger.debug(
            "Falha ao aplicar estilo no header da tabela durante apply_theme: %s", exc
        )


def _update_filter_panel_context(window, normalized: str) -> None:
    try:
        context = getattr(window, "_filter_panel_context", None)
        if isinstance(context, dict):
            context["_theme_name"] = normalized
    except Exception as exc:
        logger.debug("Falha ao registrar tema atual no contexto de filtros: %s", exc)


def _apply_style_to_window_widgets(window, names: tuple[str, ...], css: str) -> None:
    for name in names:
        widget = getattr(window, name, None)
        if widget is not None:
            _set_stylesheet_if_changed(widget, css)


def _apply_style_to_context_widgets(
    context: dict, names: tuple[str, ...], css: str
) -> None:
    for name in names:
        widget = context.get(name)
        if widget is not None:
            _set_stylesheet_if_changed(widget, css)


def _apply_group_style(
    window, name: str, normalized: str, light_themes: set[str], css: str
) -> None:
    widget = getattr(window, name, None)
    if widget is None:
        return
    _set_stylesheet_if_changed(widget, "" if normalized in light_themes else css)


def _apply_search_widget_styles(window, context: dict | None, style: dict) -> None:
    if hasattr(window, "search_label"):
        _set_stylesheet_if_changed(
            window.search_label,
            f"color: {style['label_color']}; font-weight: 600;",
        )

    search_input_style = style.get("line_edit_css", "")
    if isinstance(context, dict) and context.get("quick_search_box") is not None:
        quick_box = context.get("quick_search_box")
        _set_stylesheet_if_changed(quick_box, style.get("quick_search_box_css", ""))
        search_input_style = style.get("quick_search_input_css", search_input_style)
        for button_name in ("clear_filter_button", "search_button"):
            button = context.get(button_name)
            if button is not None:
                _set_stylesheet_if_changed(
                    button, style.get("quick_search_button_css", "")
                )

    seen_search_inputs = set()
    for search_widget in (getattr(window, "search_input", None),):
        if search_widget is None or id(search_widget) in seen_search_inputs:
            continue
        seen_search_inputs.add(id(search_widget))
        _set_stylesheet_if_changed(search_widget, search_input_style)
    if isinstance(context, dict):
        search_widget = context.get("search_input")
        if search_widget is None or id(search_widget) in seen_search_inputs:
            search_widget = None
        if search_widget is not None:
            _set_stylesheet_if_changed(search_widget, search_input_style)


def _apply_advanced_filter_control_styles(window, style: dict) -> None:
    adv_buttons = (
        "adv_executor_button",
        "adv_emissor_button",
        "adv_divisao_button",
        "adv_status_button",
        "adv_year_emissao_button",
        "adv_year_execucao_button",
        "adv_prioridade_emissao_button",
        "adv_prioridade_planejamento_button",
        "adv_reprog_button",
        "adv_derivada_button",
        "adv_responsavel_solicitante_button",
        "adv_responsavel_programacao_button",
        "adv_responsavel_execucao_button",
        "adv_responsavel_emissor_button",
    )
    try:
        _apply_style_to_window_widgets(window, adv_buttons, style["tool_btn_css"])
        _apply_style_to_window_widgets(
            window,
            ("_adv_filters_apply_btn", "_adv_filters_clear_btn"),
            style["action_btn_css"],
        )
        _apply_style_to_window_widgets(
            window, ("adv_macro_combo", "adv_reprog_mode"), style["combo_css"]
        )
        _apply_style_to_window_widgets(
            window,
            (
                "adv_week_emissao_start",
                "adv_week_emissao_end",
                "adv_week_execucao_start",
                "adv_week_execucao_end",
            ),
            style["line_edit_css"],
        )
    except Exception as exc:
        logger.debug("Falha ao aplicar estilos dos controles avancados: %s", exc)


def _apply_details_and_group_styles(
    window,
    *,
    normalized: str,
    light_themes: set[str],
    group_css: str,
    panel_text: str,
    panel_bg: str,
) -> None:
    if hasattr(window, "details_text"):
        if hasattr(window, "details_group"):
            try:
                from PyQt6.QtGui import QFont

                base_font = window.details_group.font()
                size = base_font.pointSizeF()
                if size <= 0:
                    size = float(base_font.pointSize())
                if size > 0:
                    cached_font = getattr(window, "_details_text_small_font_cached", None)
                    cached_size = getattr(
                        window, "_details_text_small_font_base_size", None
                    )
                    cached_family = getattr(
                        window, "_details_text_small_font_base_family", None
                    )
                    cached_weight = getattr(
                        window, "_details_text_small_font_base_weight", None
                    )
                    should_rebuild = (
                        not isinstance(cached_font, QFont)
                        or not isinstance(cached_size, (int, float))
                        or abs(float(cached_size) - float(size)) > 0.01
                        or cached_family != base_font.family()
                        or cached_weight != int(base_font.weight())
                    )
                    if should_rebuild:
                        small_font = QFont(base_font)
                        small_font.setPointSizeF(max(size - 1.5, 1.0))
                        window._details_text_small_font_cached = small_font
                        window._details_text_small_font_base_size = float(size)
                        window._details_text_small_font_base_family = base_font.family()
                        window._details_text_small_font_base_weight = int(
                            base_font.weight()
                        )
                    active_small_font = getattr(
                        window, "_details_text_small_font_cached", None
                    )
                    if isinstance(active_small_font, QFont):
                        window.details_text.setFont(active_small_font)
            except Exception as exc:
                logger.debug(
                    "Falha ao ajustar fonte reduzida no painel de detalhes: %s", exc
                )
        if normalized in light_themes:
            _set_stylesheet_if_changed(window.details_text, "")
        else:
            _set_stylesheet_if_changed(
                window.details_text,
                "QTextEdit {"
                f" color: {panel_text}; background: {panel_bg}; border: none; padding:4px;"
                " }",
            )

    for group_name in ("details_group", "col_filters_group", "adv_filters_group"):
        _apply_group_style(window, group_name, normalized, light_themes, group_css)
    action_widget = getattr(window, "_adv_filters_action_widget", None)
    if action_widget is not None:
        _set_stylesheet_if_changed(
            action_widget, "" if normalized in light_themes else group_css
        )


def _apply_status_summary_styles(window, selector, context: dict | None, style: dict) -> None:
    highlight_style = style["highlight_style"]
    window._week_label_style = highlight_style
    if hasattr(window, "week_label"):
        _set_stylesheet_if_changed(window.week_label, highlight_style)

    if hasattr(window, "status_label"):
        _set_stylesheet_if_changed(window.status_label, style["status_label_css"])

    if hasattr(window, "search_help"):
        if hasattr(window, "status_label"):
            try:
                window.search_help.setFont(window.status_label.font())
            except Exception as exc:
                logger.debug(
                    "Falha ao sincronizar fonte de search_help com status_label: %s",
                    exc,
                )
        _set_stylesheet_if_changed(window.search_help, style["search_help_css"])

    if hasattr(window, "col_filter_indicator"):
        _set_stylesheet_if_changed(
            window.col_filter_indicator, style["indicator_css"]
        )
    if hasattr(window, "filters_summary_label"):
        _set_stylesheet_if_changed(
            window.filters_summary_label, style["filters_summary_label_css"]
        )
    if hasattr(window, "filters_summary_frame"):
        _set_stylesheet_if_changed(
            window.filters_summary_frame, style["filters_summary_frame_css"]
        )
    if hasattr(window, "filters_summary_scroll"):
        _set_stylesheet_if_changed(
            window.filters_summary_scroll, style["filters_summary_scroll_css"]
        )

    highlight_button_names = (
        "clear_all_filters_btn",
        "export_list_btn",
        "undo_filter_btn",
        "save_filter_button",
    )
    _apply_style_to_window_widgets(window, highlight_button_names, highlight_style)
    if isinstance(context, dict):
        _apply_style_to_context_widgets(context, highlight_button_names, highlight_style)
        filter_tab_bar = context.get("filter_panel_tab_bar")
        if filter_tab_bar is not None:
            _set_stylesheet_if_changed(filter_tab_bar, style["tab_bar_css"])

    update_summary = getattr(window, "_update_filters_summary", None)
    if callable(update_summary):
        update_summary()

    if hasattr(window, "add_column_filter_btn") and hasattr(window, "clear_all_btn"):
        _set_stylesheet_if_changed(window.add_column_filter_btn, style["footer_btn_css"])
        _set_stylesheet_if_changed(window.clear_all_btn, style["footer_btn_css"])

    if selector is not None and hasattr(selector, "summary_label"):
        _set_stylesheet_if_changed(selector.summary_label, style["indicator_css"])

    if hasattr(window, "col_filters_hint"):
        _set_stylesheet_if_changed(window.col_filters_hint, style["hint_css"])


def _apply_theme_widget_styles(
    window,
    normalized: str,
    pal,
    roles: dict,
    *,
    highlight_bg_default: str,
    highlight_weight_default: str,
) -> None:
    from gui.helpers import build_group_box_qss, build_line_edit_qss

    try:
        light_themes = {
            "windows7",
            "classico",
            "solarized-light",
            "mint-light",
            "paper",
        }
        selector = getattr(window, "column_selector", None)
        pal_active = window.palette()
        from PyQt6.QtGui import QPalette as _QPal

        txt = pal_active.color(_QPal.ColorRole.WindowText).name()
        base = pal_active.color(_QPal.ColorRole.Base).name()
        mid = pal_active.color(_QPal.ColorRole.Mid).name()
        high = pal_active.color(_QPal.ColorRole.Highlight).name()
        label_color = roles.get("label_color", txt)
        support_color = roles.get("support_text_color", label_color)
        indicator_color = roles.get("indicator_text_color", support_color)
        summary_color = roles.get("summary_text_color", label_color)
        summary_bg = roles.get("summary_frame_bg", roles.get("panel_bg", base))
        summary_border = roles.get(
            "summary_frame_border", roles.get("panel_border", mid)
        )
        accent = roles.get("accent", high)
        accent_soft = roles.get("accent_soft", support_color)
        input_bg = roles.get("input_bg", base)
        input_text = roles.get("input_text", txt)
        input_border = roles.get("input_border", mid)
        input_focus = roles.get("input_border_focus", accent)
        input_placeholder = roles.get("input_placeholder", support_color)
        panel_bg = roles.get(
            "panel_bg", pal_active.color(_QPal.ColorRole.Window).name()
        )
        panel_text = roles.get("panel_text", txt)
        panel_border = roles.get("panel_border", input_border)
        window._current_theme_roles = dict(roles)
        try:
            highlight_fg = pal_active.color(_QPal.ColorRole.HighlightedText).name()
        except Exception as exc:
            logger.debug("Falha ao obter cor de texto destacado da paleta: %s", exc)
            highlight_fg = None
        window._highlight_bg_color = high or highlight_bg_default
        window._highlight_text_color = highlight_fg or None
        window._highlight_font_weight = highlight_weight_default

        line_edit_css = build_line_edit_qss(
            input_text, input_bg, input_border, input_focus, input_placeholder
        )
        context = getattr(window, "_filter_panel_context", None)
        style = {
            "label_color": label_color,
            "line_edit_css": line_edit_css,
            "quick_search_box_css": (
                "QFrame#quickSearchBox {"
                f" color:{input_text}; background:{input_bg};"
                f" border:1px solid {input_border}; border-radius:4px;"
                "}"
                "QFrame#quickSearchBox:hover {"
                f" border:1px solid {input_focus};"
                "}"
            ),
            "quick_search_input_css": (
                "QLineEdit {"
                f" color:{input_text}; background:transparent; border:0;"
                f" selection-background-color:{accent_soft};"
                f" selection-color:{input_text};"
                " padding:2px 4px;"
                "}"
                "QLineEdit:focus { border:0; }"
                "QLineEdit:disabled {"
                f" color:{support_color}; background:transparent;"
                "}"
            ),
            "quick_search_button_css": (
                "QPushButton {"
                f" color:{input_text}; background:transparent; border:0;"
                " border-radius:3px; padding:0;"
                " font-weight:700;"
                "}"
                "QPushButton:hover {"
                f" background:{accent_soft};"
                "}"
                "QPushButton:disabled {"
                f" color:{support_color}; background:transparent;"
                "}"
            ),
            "tool_btn_css": (
            "QToolButton {"
            f" color: {input_text}; background: {input_bg}; border:1px solid {input_border};"
            " border-radius:4px; padding:2px 6px; }"
            "QToolButton:hover {"
            f" border:1px solid {input_focus};"
            "}"
            "QToolButton:pressed {"
            f" background: {accent_soft}; "
            "}"
            "QToolButton:checked {"
            f" border:1px solid {accent}; background: {accent_soft};"
            "}"
            ),
            "action_btn_css": (
            "QPushButton {"
            f" color: {panel_text}; background: {panel_bg}; border:1px solid {panel_border};"
            " border-radius:4px; padding:2px 8px; }"
            "QPushButton:hover {"
            f" border:1px solid {accent};"
            "}"
            "QPushButton:pressed {"
            f" background: {accent_soft};"
            "}"
            ),
            "combo_css": (
            "QComboBox {"
            f" color: {input_text}; background: {input_bg}; border:1px solid {input_border};"
            " border-radius:4px; padding:2px 6px; }"
            "QComboBox:hover {"
            f" border:1px solid {input_focus};"
            "}"
            "QComboBox::drop-down { border:0px; }"
            "QComboBox QAbstractItemView {"
            f" color: {panel_text}; background: {panel_bg};"
            f" selection-background-color: {accent_soft}; selection-color: {panel_text};"
            f" border:1px solid {panel_border};"
            "}"
            ),
        }
        style["highlight_style"] = (
            f"font-weight:600; color:{accent}; background:{panel_bg}; "
            f"border:1px solid {panel_border}; border-radius:4px; padding:2px 6px;"
        )
        style["status_label_css"] = (
            f"color:{accent}; background:{panel_bg}; border:1px solid {panel_border}; "
            "border-radius:4px; padding:2px 6px;"
        )
        style["search_help_css"] = (
            f"font-size:10px; color:{support_color}; margin:0; padding:0;"
        )
        style["indicator_css"] = f"color:{indicator_color};"
        style["filters_summary_label_css"] = (
            f"color:{summary_color}; background:transparent; padding:0 2px;"
        )
        style["filters_summary_frame_css"] = (
            "QFrame#filtersSummaryFrame {"
            f" background:{summary_bg}; border:1px solid {summary_border}; border-radius:4px;"
            " }"
        )
        style["filters_summary_scroll_css"] = (
            "QScrollArea { border:0; background:transparent; }"
            "QScrollArea > QWidget > QWidget { background:transparent; }"
        )
        style["tab_bar_css"] = (
            "QTabBar::tab {"
            f"font-weight:600; color:{panel_text}; background:{panel_bg}; "
            f"border:1px solid {panel_border}; border-bottom:0; "
            "min-width:96px; padding:1px 10px; margin-right:1px;"
            "}"
            "QTabBar::tab:selected {"
            f"background:{accent}; color:{panel_bg}; border:1px solid {accent};"
            "border-bottom:0;"
            "}"
        )
        style["footer_btn_css"] = (
            f"QPushButton {{ color:{panel_text}; background:{panel_bg}; "
            f"border:1px solid {panel_border}; border-radius:4px; padding:4px 10px; }}\n"
            f"QPushButton:hover {{ border:1px solid {accent}; }}\n"
        )
        style["hint_css"] = f"color:{support_color}; font-size: 11px;"

        _apply_search_widget_styles(window, context, style)
        _apply_advanced_filter_control_styles(window, style)

        group_css = build_group_box_qss(panel_text, panel_border, panel_bg)
        _apply_details_and_group_styles(
            window,
            normalized=normalized,
            light_themes=light_themes,
            group_css=group_css,
            panel_text=panel_text,
            panel_bg=panel_bg,
        )
        _apply_status_summary_styles(window, selector, context, style)
    except Exception as exc:
        logger.warning("Falha no bloco principal de estilizacao do tema: %s", exc)


def _refresh_filter_widgets_for_theme(window, normalized: str) -> None:
    try:
        try:
            # Force a full advanced-menu rebuild under the active theme.
            setattr(window, "_adv_options_dirty", True)
        except Exception as exc:
            logger.debug(
                "Falha ao marcar opcoes avancadas como dirty apos troca de tema: %s",
                exc,
            )
        if getattr(window, "_active_filter_panel_kind", None) == "advanced":
            window._pending_theme_refresh_column_filters = normalized
            try:
                if hasattr(window, "_schedule_adv_options_refresh"):
                    window._schedule_adv_options_refresh()
                elif hasattr(window, "_refresh_advanced_filter_options"):
                    window._refresh_advanced_filter_options()
            except Exception as exc:
                logger.debug(
                    "Falha ao atualizar menus avancados apos troca de tema: %s", exc
                )
        else:
            window._refresh_column_filter_widgets()
            window._pending_theme_refresh_column_filters = None
    except Exception as exc:
        logger.debug(
            "Falha ao atualizar widgets dinamicos de filtro por coluna no tema: %s", exc
        )


def _persist_theme_selection(
    window, normalized: str, gui_prefs: dict, project_root: str
) -> None:
    try:
        gui_settings = gui_prefs.setdefault("gui_settings", {})
        if gui_settings.get("theme") != normalized:
            gui_settings["theme"] = normalized
            ok = persist_gui_preferences(gui_prefs, project_root, retries=1)
            if not ok:
                if not os.environ.get("PYTEST_CURRENT_TEST"):
                    try:
                        window.status_label.setText(
                            "Status: Tema aplicado; falha ao salvar preferencia."
                        )
                    except Exception as exc:
                        logger.debug(
                            "Falha ao atualizar status_label apos persistencia de tema: %s",
                            exc,
                        )
    except Exception as exc:
        logger.warning("Falha ao persistir tema em gui_main_preferences.json: %s", exc)


def apply_theme(
    window,
    name: str,
    *,
    gui_prefs: dict,
    project_root: str,
    highlight_defaults: tuple[str, str] | None = None,
) -> None:
    highlight_defaults = highlight_defaults or ("yellow", "bold")
    highlight_bg_default, highlight_weight_default = highlight_defaults

    normalized = normalize_theme(name)
    current_theme = normalize_theme(getattr(window, "_current_theme", "") or "")
    same_theme = bool(current_theme and normalized == current_theme)
    roles = get_theme_roles(normalized)
    pal = _apply_global_palette(window, normalized, same_theme)
    _apply_central_widget_theme(window, normalized, pal)
    _apply_tabs_theme(window, pal, roles)
    _apply_table_header_theme(window)

    window._current_theme = normalized
    _update_filter_panel_context(window, normalized)
    _apply_theme_widget_styles(
        window,
        normalized,
        pal,
        roles,
        highlight_bg_default=highlight_bg_default,
        highlight_weight_default=highlight_weight_default,
    )
    _refresh_filter_widgets_for_theme(window, normalized)
    _persist_theme_selection(window, normalized, gui_prefs, project_root)
    apply_macos_contrast(window, normalized)
    try:
        window.update_details_from_selection()
    except Exception as exc:
        logger.debug("Falha ao atualizar painel de detalhes apos apply_theme: %s", exc)


def apply_macos_contrast(window, theme_name: str) -> None:
    if sys.platform != "darwin":
        return
    normalized = normalize_theme(theme_name)
    roles = get_theme_roles(normalized)
    text_color = roles.get("panel_text")
    bg_color = roles.get("panel_bg")
    border_color = roles.get("panel_border")
    label_color = roles.get("label_color")
    block = (
        "/* SSA_MAC_QSS_START */\n"
        "QLineEdit, QTextEdit, QTextBrowser {"
        f" color:{text_color}; background-color:{bg_color}; border:1px solid {border_color}; }}\n"
        "QGroupBox, QLabel {"
        f" color:{label_color}; }}\n"
        "/* SSA_MAC_QSS_END */"
    )
    try:
        central = window.centralWidget()
        if central is not None:
            existing = central.styleSheet() or ""
            start = existing.find("/* SSA_MAC_QSS_START */")
            end = existing.find("/* SSA_MAC_QSS_END */", start)
            if start != -1 and end != -1 and end > start:
                end += len("/* SSA_MAC_QSS_END */")
                existing = existing[:start] + existing[end:]
            new_qss = (
                existing
                + ("\n" if existing and not existing.endswith("\n") else "")
                + block
            ).strip()
            central.setStyleSheet(new_qss)
    except Exception as exc:
        logger.debug(
            "Falha ao aplicar ajustes de contraste macOS no tema %s: %s",
            normalized,
            exc,
        )
