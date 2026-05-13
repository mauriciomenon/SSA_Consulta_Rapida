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
    elif "theme_default" in gui_settings:
        gui_settings.pop("theme_default", None)
        default_changed = True
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


def _update_tab_contexts(window, normalized: str) -> None:
    try:
        tab_contexts = getattr(window, "_tab_contexts", None)
        if isinstance(tab_contexts, list):
            active_kind = getattr(window, "_current_tab_kind", None)
            active_search = getattr(window, "search_input", None)
            for ctx in tab_contexts:
                if not isinstance(ctx, dict):
                    continue
                if active_kind and ctx.get("tab_kind") == active_kind:
                    ctx["_theme_name"] = normalized
                    break
                if (
                    active_search is not None
                    and ctx.get("search_input") is active_search
                ):
                    ctx["_theme_name"] = normalized
                    break
    except Exception as exc:
        logger.debug("Falha ao registrar tema atual nos contextos de aba: %s", exc)


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

        if hasattr(window, "search_label"):
            _set_stylesheet_if_changed(
                window.search_label, f"color: {label_color}; font-weight: 600;"
            )

        if hasattr(window, "search_input") and window.search_input is not None:
            _set_stylesheet_if_changed(
                window.search_input,
                build_line_edit_qss(
                    input_text, input_bg, input_border, input_focus, input_placeholder
                ),
            )

        tool_btn_css = (
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
        )
        adv_buttons = [
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
        ]
        for name in adv_buttons:
            btn = getattr(window, name, None)
            if btn is not None:
                try:
                    _set_stylesheet_if_changed(btn, tool_btn_css)
                except Exception as exc:
                    logger.debug(
                        "Falha ao aplicar estilo no botao avancado %s: %s", name, exc
                    )
        action_btn_css = (
            "QPushButton {"
            f" color: {panel_text}; background: {panel_bg}; border:1px solid {panel_border};"
            " border-radius:4px; padding:2px 8px; }"
            "QPushButton:hover {"
            f" border:1px solid {accent};"
            "}"
            "QPushButton:pressed {"
            f" background: {accent_soft};"
            "}"
        )
        for name in ("_adv_filters_apply_btn", "_adv_filters_clear_btn"):
            btn = getattr(window, name, None)
            if btn is not None:
                try:
                    _set_stylesheet_if_changed(btn, action_btn_css)
                except Exception as exc:
                    logger.debug(
                        "Falha ao aplicar estilo no botao de acao %s: %s", name, exc
                    )
        combo_css = (
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
        )
        for name in ("adv_macro_combo", "adv_reprog_mode"):
            combo = getattr(window, name, None)
            if combo is not None:
                try:
                    _set_stylesheet_if_changed(combo, combo_css)
                except Exception as exc:
                    logger.debug(
                        "Falha ao aplicar estilo no combo avancado %s: %s", name, exc
                    )
        adv_line_edits = [
            "adv_week_emissao_start",
            "adv_week_emissao_end",
            "adv_week_execucao_start",
            "adv_week_execucao_end",
        ]
        for name in adv_line_edits:
            widget = getattr(window, name, None)
            if widget is not None:
                try:
                    _set_stylesheet_if_changed(
                        widget,
                        build_line_edit_qss(
                            input_text,
                            input_bg,
                            input_border,
                            input_focus,
                            input_placeholder,
                        ),
                    )
                except Exception as exc:
                    logger.debug(
                        "Falha ao aplicar estilo no campo avancado %s: %s", name, exc
                    )

        if hasattr(window, "details_text"):
            if hasattr(window, "details_group"):
                try:
                    from PyQt6.QtGui import QFont

                    base_font = window.details_group.font()
                    size = base_font.pointSizeF()
                    if size <= 0:
                        size = float(base_font.pointSize())
                    if size > 0:
                        cached_font = getattr(
                            window, "_details_text_small_font_cached", None
                        )
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
                            window._details_text_small_font_base_family = (
                                base_font.family()
                            )
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

        group_css = build_group_box_qss(panel_text, panel_border, panel_bg)

        if hasattr(window, "details_group"):
            if normalized in light_themes:
                _set_stylesheet_if_changed(window.details_group, "")
            else:
                _set_stylesheet_if_changed(window.details_group, group_css)

        if hasattr(window, "col_filters_group"):
            if normalized in light_themes:
                _set_stylesheet_if_changed(window.col_filters_group, "")
            else:
                _set_stylesheet_if_changed(window.col_filters_group, group_css)
        if hasattr(window, "adv_filters_group"):
            if normalized in light_themes:
                _set_stylesheet_if_changed(window.adv_filters_group, "")
            else:
                _set_stylesheet_if_changed(window.adv_filters_group, group_css)
        action_widget = getattr(window, "_adv_filters_action_widget", None)
        if action_widget is not None:
            try:
                if normalized in light_themes:
                    _set_stylesheet_if_changed(action_widget, "")
                else:
                    _set_stylesheet_if_changed(action_widget, group_css)
            except Exception as exc:
                logger.debug(
                    "Falha ao aplicar estilo no action box dos filtros avancados: %s",
                    exc,
                )

        highlight_style = (
            f"font-weight:600; color:{accent}; background:{panel_bg}; "
            f"border:1px solid {panel_border}; border-radius:4px; padding:2px 6px;"
        )
        window._week_label_style = highlight_style
        if hasattr(window, "week_label"):
            _set_stylesheet_if_changed(window.week_label, highlight_style)

        if hasattr(window, "status_label"):
            _set_stylesheet_if_changed(
                window.status_label,
                f"color:{accent}; background:{panel_bg}; border:1px solid {panel_border}; border-radius:4px; padding:2px 6px;",
            )

        if hasattr(window, "search_help"):
            css = f"font-size:10px; color:{support_color}; margin:0; padding:0;"
            if hasattr(window, "status_label"):
                try:
                    window.search_help.setFont(window.status_label.font())
                except Exception as exc:
                    logger.debug(
                        "Falha ao sincronizar fonte de search_help com status_label: %s",
                        exc,
                    )
            _set_stylesheet_if_changed(window.search_help, css)

        if hasattr(window, "col_filter_indicator"):
            _set_stylesheet_if_changed(
                window.col_filter_indicator, f"color:{indicator_color};"
            )

        if hasattr(window, "filters_summary_label"):
            _set_stylesheet_if_changed(
                window.filters_summary_label, f"color:{summary_color};"
            )

        if hasattr(window, "filters_summary_frame"):
            _set_stylesheet_if_changed(
                window.filters_summary_frame,
                "QFrame#filtersSummaryFrame {"
                f" background:{summary_bg}; border:1px solid {summary_border}; border-radius:4px;"
                " }",
            )
        if hasattr(window, "filters_summary_scroll"):
            try:
                _set_stylesheet_if_changed(
                    window.filters_summary_scroll,
                    "QScrollArea { border:0; background:transparent; }"
                    "QScrollArea > QWidget > QWidget { background:transparent; }",
                )
            except Exception as exc:
                logger.debug(
                    "Falha ao aplicar estilo no scroll de filtros ativos: %s", exc
                )
        highlight_button_names = (
            "clear_all_filters_btn",
            "export_list_btn",
            "undo_filter_btn",
            "save_filter_button",
            "search_button",
            "clear_filter_button",
        )
        for name in highlight_button_names:
            button = getattr(window, name, None)
            if button is not None:
                try:
                    _set_stylesheet_if_changed(button, highlight_style)
                except Exception as exc:
                    logger.debug("Falha ao aplicar estilo no botao %s: %s", name, exc)
        for ctx in getattr(window, "_tab_contexts", []) or []:
            if not isinstance(ctx, dict):
                continue
            for name in highlight_button_names:
                button = ctx.get(name)
                if button is not None:
                    try:
                        _set_stylesheet_if_changed(button, highlight_style)
                    except Exception as exc:
                        logger.debug(
                            "Falha ao aplicar estilo no botao %s do contexto: %s",
                            name,
                            exc,
                        )
            tab_selector_style = (
                "QPushButton {"
                f"font-weight:600; color:{accent}; background:{panel_bg}; "
                f"border:1px solid {panel_border}; border-radius:4px; padding:2px 12px;"
                "}"
                "QPushButton:checked {"
                f"background:{accent}; color:{panel_bg}; border:1px solid {accent};"
                "}"
            )
            for name in ("tab_selector_ssas_btn", "tab_selector_filters_btn"):
                button = ctx.get(name)
                if button is not None:
                    try:
                        _set_stylesheet_if_changed(button, tab_selector_style)
                    except Exception as exc:
                        logger.debug(
                            "Falha ao aplicar estilo no seletor de aba %s: %s",
                            name,
                            exc,
                        )
        try:
            update_summary = getattr(window, "_update_filters_summary", None)
            if callable(update_summary):
                update_summary()
        except Exception as exc:
            logger.debug("Falha ao atualizar resumo de filtros apos tema: %s", exc)
        if hasattr(window, "add_column_filter_btn") and hasattr(
            window, "clear_all_btn"
        ):
            footer_btn_style = (
                f"QPushButton {{ color:{panel_text}; background:{panel_bg}; border:1px solid {panel_border}; border-radius:4px; padding:4px 10px; }}\n"
                f"QPushButton:hover {{ border:1px solid {accent}; }}\n"
            )
            try:
                _set_stylesheet_if_changed(
                    window.add_column_filter_btn, footer_btn_style
                )
                _set_stylesheet_if_changed(window.clear_all_btn, footer_btn_style)
            except Exception as exc:
                logger.debug(
                    "Falha ao aplicar estilo consistente para botoes de filtros por coluna: %s",
                    exc,
                )

        if selector is not None and hasattr(selector, "summary_label"):
            _set_stylesheet_if_changed(
                selector.summary_label, f"color:{indicator_color};"
            )

        if hasattr(window, "col_filters_hint"):
            _set_stylesheet_if_changed(
                window.col_filters_hint, f"color:{support_color}; font-size: 11px;"
            )
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
        if getattr(window, "_current_tab_kind", None) == "filters":
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
    _update_tab_contexts(window, normalized)
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


def reapply_current_theme_widget_styles(
    window,
    *,
    highlight_defaults: tuple[str, str] | None = None,
) -> None:
    """Reaplica estilos de widgets do tema atual sem persistir configuracao."""
    highlight_defaults = highlight_defaults or ("yellow", "bold")
    highlight_bg_default, highlight_weight_default = highlight_defaults
    normalized = normalize_theme(getattr(window, "_current_theme", "") or "")
    roles = get_theme_roles(normalized)
    pal = window.palette()
    _apply_theme_widget_styles(
        window,
        normalized,
        pal,
        roles,
        highlight_bg_default=highlight_bg_default,
        highlight_weight_default=highlight_weight_default,
    )


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
