# gui/ssa/gui_theme.py
# Relation: used by gui/gui_ssa.py (SSAMainWindow facade).
# Relation: depends on gui/helpers/theme_helpers.py and utils/themes.py.
# Relation: does not touch data loading or filters.

from __future__ import annotations

import sys
from utils.robust_logging import get_robust_logger
from utils.themes import get_palette, get_theme_roles, normalize_theme
from .gui_filters_advanced_panel_state import advanced_panel_state
from .gui_preferences_persistence import persist_gui_preferences_async
from .gui_theme_dialog import show_theme_selection_dialog as _show_theme_dialog
from .gui_theme_styles import (
    LIGHT_THEME_KEYS,
    build_theme_widget_style_bundle,
    get_details_text_theme_font,
)

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


def get_theme_dialog_items() -> list[tuple[str, str]]:
    light_themes, dark_themes = get_theme_catalog()
    items: list[tuple[str, str]] = []
    for label, key in sorted(light_themes, key=lambda item: item[0].lower()):
        items.append((f"Light - {label}", key))
    for label, key in sorted(dark_themes, key=lambda item: item[0].lower()):
        items.append((f"Dark - {label}", key))
    return items


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


def show_theme_selection_dialog(window, *, gui_prefs: dict, project_root: str) -> None:
    _ = project_root
    return _show_theme_dialog(
        window,
        gui_prefs=gui_prefs,
        theme_items=get_theme_dialog_items(),
        persist_preferences_async=persist_gui_preferences_async,
    )


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
    from gui.helpers import build_central_widget_qss, replace_tagged_qss_block

    try:
        central = window.centralWidget()
        if central is not None:
            existing = central.styleSheet() or ""
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
                new_css = replace_tagged_qss_block(
                    existing,
                    start_marker="/* SSA_MAIN_BG_START */",
                    end_marker="/* SSA_MAIN_BG_END */",
                    block=block,
                )
                if central.styleSheet() != new_css:
                    central.setStyleSheet(new_css)
            else:
                existing = replace_tagged_qss_block(
                    existing,
                    start_marker="/* SSA_MAIN_BG_START */",
                    end_marker="/* SSA_MAIN_BG_END */",
                    block="",
                )
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
        setter = getattr(window, "set_theme_name_for_filter_context", None)
        if callable(setter):
            setter(normalized)
    except Exception as exc:
        logger.debug("Falha ao registrar tema atual no contexto de filtros: %s", exc)


def _apply_style_to_window_widgets(window, names: tuple[str, ...], css: str) -> None:
    for name in names:
        widget = getattr(window, name, None)
        if widget is not None:
            _set_stylesheet_if_changed(widget, css)


def _apply_style_to_widgets(widgets, css: str) -> None:
    for widget in widgets:
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
        state = advanced_panel_state(window)
        if state is not None:
            field_box_css = (
                style["advanced_field_box_windows_css"]
                if sys.platform.startswith("win")
                else style["advanced_field_box_css"]
            )
            _apply_style_to_widgets(
                state.grid_widgets.values(),
                field_box_css,
            )
            _apply_style_to_widgets(
                (state.apply_btn, state.clear_btn),
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
                small_font = get_details_text_theme_font(window)
                if small_font is not None:
                    window.details_text.setFont(small_font)
            except Exception as exc:
                logger.debug(
                    "Falha ao ajustar fonte reduzida no painel de detalhes: %s", exc
                )
        _set_stylesheet_if_changed(
            window.details_text,
            "QTextEdit {"
            f" color: {panel_text}; background: {panel_bg}; border: none; padding:2px;"
            " }",
        )

    for group_name in ("details_group", "col_filters_group", "adv_filters_group"):
        _apply_group_style(window, group_name, normalized, light_themes, group_css)
    state = advanced_panel_state(window)
    action_widget = state.action_widget if state is not None else None
    if action_widget is not None:
        _set_stylesheet_if_changed(
            action_widget, "" if normalized in light_themes else group_css
        )


def _apply_status_label_styles(window, style: dict) -> None:
    highlight_style = style["highlight_style"]
    window._week_label_style = highlight_style
    if hasattr(window, "week_label"):
        _set_stylesheet_if_changed(window.week_label, highlight_style)

    if hasattr(window, "status_label"):
        _set_stylesheet_if_changed(window.status_label, style["status_label_css"])

    if hasattr(window, "search_help"):
        status_label = getattr(window, "status_label", None)
        if status_label is not None:
            try:
                status_font = status_label.font()
                font_info = status_label.fontInfo()
                status_font.setFamily(font_info.family())
                if font_info.pointSizeF() > 0:
                    status_font.setPointSizeF(font_info.pointSizeF())
                elif font_info.pixelSize() > 0:
                    status_font.setPixelSize(font_info.pixelSize())
                status_font.setWeight(font_info.weight())
                window.search_help.setFont(status_font)
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


def _apply_filter_summary_styles(window, style: dict) -> None:
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


def _apply_filter_action_button_styles(
    window, context: dict | None, style: dict
) -> None:
    highlight_style = style["highlight_style"]
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


def _apply_column_filter_footer_styles(window, style: dict) -> None:
    if hasattr(window, "add_column_filter_btn") and hasattr(window, "clear_all_btn"):
        _set_stylesheet_if_changed(window.add_column_filter_btn, style["footer_btn_css"])
        _set_stylesheet_if_changed(window.clear_all_btn, style["footer_btn_css"])


def _apply_selector_hint_styles(window, selector, style: dict) -> None:
    if selector is not None and hasattr(selector, "summary_label"):
        _set_stylesheet_if_changed(selector.summary_label, style["indicator_css"])

    if hasattr(window, "col_filters_hint"):
        _set_stylesheet_if_changed(window.col_filters_hint, style["hint_css"])


def _refresh_filters_summary_after_theme(window) -> None:
    update_summary = getattr(window, "_update_filters_summary", None)
    if callable(update_summary):
        update_summary()
        return
    if getattr(window, "filters_summary_frame", None) is not None:
        logger.debug("Resumo de filtros sem callback durante aplicacao de tema.")


def _apply_status_summary_styles(
    window, selector, context: dict | None, style: dict
) -> None:
    _apply_status_label_styles(window, style)
    _apply_filter_summary_styles(window, style)
    _apply_filter_action_button_styles(window, context, style)
    _refresh_filters_summary_after_theme(window)
    _apply_column_filter_footer_styles(window, style)
    _apply_selector_hint_styles(window, selector, style)


def _apply_theme_widget_styles(
    window,
    normalized: str,
    pal,
    roles: dict,
    *,
    highlight_bg_default: str,
    highlight_weight_default: str,
) -> None:
    try:
        selector = getattr(window, "column_selector", None)
        pal_active = window.palette()
        style_bundle = build_theme_widget_style_bundle(
            pal_active,
            roles,
            highlight_bg_default=highlight_bg_default,
            highlight_weight_default=highlight_weight_default,
        )
        window._current_theme_roles = dict(roles)
        window._highlight_bg_color = style_bundle.highlight_bg
        window._highlight_text_color = style_bundle.highlight_text
        window._highlight_font_weight = style_bundle.highlight_font_weight
        context_getter = getattr(window, "theme_filter_context", None)
        context = context_getter() if callable(context_getter) else None
        style = style_bundle.styles

        _apply_search_widget_styles(window, context, style)
        _apply_advanced_filter_control_styles(window, style)

        _apply_details_and_group_styles(
            window,
            normalized=normalized,
            light_themes=LIGHT_THEME_KEYS,
            group_css=style_bundle.group_css,
            panel_text=style_bundle.panel_text,
            panel_bg=style_bundle.panel_bg,
        )
        _apply_status_summary_styles(window, selector, context, style)
    except Exception as exc:
        logger.warning("Falha no bloco principal de estilizacao do tema: %s", exc)


def _refresh_filter_widgets_for_theme(window, normalized: str) -> None:
    try:
        refresher = getattr(window, "refresh_filter_widgets_after_theme", None)
        if callable(refresher):
            refresher(normalized)
    except Exception as exc:
        logger.debug(
            "Falha ao atualizar widgets dinamicos de filtro por coluna no tema: %s", exc
        )


def _persist_theme_preferences(
    window, gui_prefs: dict
) -> None:
    try:
        _ = window
        persist_gui_preferences_async(gui_prefs)
    except Exception as exc:
        logger.warning("Falha ao persistir tema em gui_main_preferences.json: %s", exc)


def _run_scheduled_theme_persistence(window) -> None:
    gui_prefs = getattr(window, "_theme_persist_gui_prefs", None)
    if isinstance(gui_prefs, dict):
        _persist_theme_preferences(window, gui_prefs)


def _schedule_theme_persistence(
    window, normalized: str, gui_prefs: dict, project_root: str
) -> None:
    _ = project_root
    gui_settings = gui_prefs.setdefault("gui_settings", {})
    if gui_settings.get("theme") == normalized:
        return
    gui_settings["theme"] = normalized
    try:
        from PyQt6.QtCore import QTimer

        timer = getattr(window, "_theme_persist_timer", None)
        if timer is None:
            timer = QTimer(window)
            timer.setSingleShot(True)
            window._theme_persist_timer = timer
        if not getattr(window, "_theme_persist_timer_connected", False):
            timer.timeout.connect(lambda: _run_scheduled_theme_persistence(window))
            window._theme_persist_timer_connected = True
        window._theme_persist_gui_prefs = gui_prefs
        timer.start(0)
    except Exception as exc:
        logger.debug(
            "Falha ao agendar persistencia de tema; persistindo agora: %s", exc
        )
        _persist_theme_preferences(window, gui_prefs)


def _apply_theme_foundation(window, normalized: str, same_theme: bool, roles: dict):
    pal = _apply_global_palette(window, normalized, same_theme)
    _apply_central_widget_theme(window, normalized, pal)
    _apply_tabs_theme(window, pal, roles)
    _apply_table_header_theme(window)
    window._current_theme = normalized
    _update_filter_panel_context(window, normalized)
    return pal


def _apply_theme_window_styles(
    window,
    normalized: str,
    pal,
    roles: dict,
    *,
    highlight_bg_default: str,
    highlight_weight_default: str,
) -> None:
    _apply_theme_widget_styles(
        window,
        normalized,
        pal,
        roles,
        highlight_bg_default=highlight_bg_default,
        highlight_weight_default=highlight_weight_default,
    )


def _finish_theme_application(
    window, normalized: str, gui_prefs: dict, project_root: str, *, same_theme: bool
) -> None:
    if not same_theme:
        _refresh_filter_widgets_for_theme(window, normalized)
    _schedule_theme_persistence(window, normalized, gui_prefs, project_root)
    apply_macos_contrast(window, normalized)
    previous_derivadas_series = getattr(
        window, "_details_current_series_for_derivadas", None
    )
    previous_derivadas_font_family = getattr(
        window, "_details_current_derivadas_font_family", None
    )
    try:
        window.update_details_from_selection()
    except Exception as exc:
        logger.debug("Falha ao atualizar painel de detalhes apos apply_theme: %s", exc)
    if previous_derivadas_series is not None:
        if getattr(window, "_details_current_series_for_derivadas", None) is None:
            window._details_current_series_for_derivadas = previous_derivadas_series
            window._details_current_derivadas_font_family = previous_derivadas_font_family
        if getattr(window, "_pending_details_series", None) is None:
            window._pending_details_series = previous_derivadas_series
    try:
        from gui.ssa import gui_details

        gui_details.refresh_derivadas_views_after_theme(window)
    except Exception as exc:
        logger.debug("Falha ao atualizar grafos de derivadas apos apply_theme: %s", exc)
    try:
        update_filter_tags = getattr(window, "update_filter_tags", None)
        if callable(update_filter_tags):
            update_filter_tags()
    except Exception as exc:
        logger.debug("Falha ao atualizar filtros salvos apos apply_theme: %s", exc)


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
    pal = _apply_theme_foundation(window, normalized, same_theme, roles)
    _apply_theme_window_styles(
        window,
        normalized,
        pal,
        roles,
        highlight_bg_default=highlight_bg_default,
        highlight_weight_default=highlight_weight_default,
    )
    _finish_theme_application(
        window, normalized, gui_prefs, project_root, same_theme=same_theme
    )


def apply_macos_contrast(window, theme_name: str) -> None:
    from gui.helpers import build_line_edit_qss, replace_tagged_qss_block

    if sys.platform != "darwin":
        return
    normalized = normalize_theme(theme_name)
    roles = get_theme_roles(normalized)
    text_color = str(roles.get("panel_text") or "#000000")
    bg_color = str(roles.get("panel_bg") or "#ffffff")
    border_color = str(roles.get("panel_border") or "#808080")
    label_color = str(roles.get("label_color") or text_color)
    block = (
        "/* SSA_MAC_QSS_START */\n"
        + build_line_edit_qss(
            text_color, bg_color, border_color, border_color, label_color
        )
        + "\n"
        "QTextEdit, QTextBrowser {"
        f" color:{text_color}; background-color:{bg_color}; border:1px solid {border_color}; }}\n"
        "QGroupBox, QLabel {"
        f" color:{label_color}; }}\n"
        "/* SSA_MAC_QSS_END */"
    )
    try:
        central = window.centralWidget()
        if central is not None:
            existing = central.styleSheet() or ""
            new_qss = replace_tagged_qss_block(
                existing,
                start_marker="/* SSA_MAC_QSS_START */",
                end_marker="/* SSA_MAC_QSS_END */",
                block=block,
            )
            central.setStyleSheet(new_qss)
    except Exception as exc:
        logger.debug(
            "Falha ao aplicar ajustes de contraste macOS no tema %s: %s",
            normalized,
            exc,
        )
