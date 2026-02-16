# gui/ssa/gui_theme.py
# Relation: used by gui/gui_ssa.py (SSAMainWindow facade).
# Relation: depends on gui/helpers/theme_helpers.py and utils/themes.py.
# Relation: does not touch data loading or filters.

from __future__ import annotations

import logging
import os
import sys

from core.config_manager import atomic_write_json_file
from utils.themes import get_palette, get_theme_roles, normalize_theme

logger = logging.getLogger(__name__)


def get_theme_catalog():
    light_themes = [
        ("Classico", 'classico'),
        ("Mint Light", 'mint-light'),
        ("Paper", 'paper'),
        ("Solarized Light", 'solarized-light'),
        ("Windows 7", 'windows7'),
    ]
    dark_themes = [
        ("Catppuccin (Mocha)", 'catppuccin'),
        ("Dark", 'dark'),
        ("Dracula", 'dracula'),
        ("Grayscale", 'grayscale'),
        ("Gruvbox", 'gruvbox'),
        ("Nord", 'nord'),
        ("Solarized Dark", 'solarized-dark'),
        ("Tokyo Night", 'tokyo-night'),
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


def persist_gui_preferences(gui_prefs: dict, project_root: str, *, retries: int = 1) -> bool:
    attempts = max(0, int(retries or 0)) + 1
    for attempt in range(attempts):
        try:
            atomic_write_json_file(
                os.path.join(project_root, "config", "gui_main_preferences.json"),
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


def toggle_theme_menu(window, *, gui_prefs: dict, project_root: str) -> None:
    from PyQt6.QtWidgets import QMenu, QWidgetAction, QCheckBox
    from functools import partial

    menu = QMenu(window)
    # Em alguns estilos (Windows), QMenu ignora QPalette; aplique paleta/QSS com cores hex calculadas
    try:
        from PyQt6.QtWidgets import QApplication
        from PyQt6.QtCore import Qt as _Qt
        from PyQt6.QtGui import QPalette as _QPal

        app = QApplication.instance()
        pal = app.palette() if app is not None else window.palette()
        if app is not None:
            menu.setPalette(pal)
        try:
            menu.setAttribute(_Qt.WidgetAttribute.WA_StyledBackground, True)
        except Exception as exc:
            logger.debug("Falha ao habilitar styled background no menu de temas: %s", exc)
        win = pal.color(_QPal.ColorRole.Window).name()
        wtxt = pal.color(_QPal.ColorRole.WindowText).name()
        mid = pal.color(_QPal.ColorRole.Mid).name()
        hi = pal.color(_QPal.ColorRole.Highlight).name()
        hitxt = pal.color(_QPal.ColorRole.HighlightedText).name()
        menu.setStyleSheet(
            f"QMenu {{ background-color: {win}; color: {wtxt}; border:1px solid {mid}; }}"
            f"QMenu::item:selected {{ background-color: {hi}; color: {hitxt}; }}"
            f"QMenu::separator {{ height:1px; background: {mid}; margin:4px 8px; }}"
        )
    except Exception as exc:
        logger.debug("Falha ao aplicar estilo/paleta no menu de temas: %s", exc)
    light_themes, dark_themes = get_theme_catalog()
    gui_settings = gui_prefs.get("gui_settings", {})
    theme_default = gui_settings.get("theme_default")
    current_theme = normalize_theme(getattr(window, "_current_theme", "") or theme_default or "gruvbox")
    roles = get_theme_roles(current_theme)
    try:
        from PyQt6.QtGui import QPalette as _QPal

        pal = menu.palette()
        wtxt = pal.color(_QPal.ColorRole.WindowText).name()
        win = pal.color(_QPal.ColorRole.Window).name()
    except Exception as exc:
        logger.debug("Falha ao ler cores da paleta no menu de temas; usando fallback: %s", exc)
        wtxt = "#ffffff"
        win = "#000000"
    support_color = roles.get("support_text_color") or roles.get("label_color") or wtxt
    if support_color.lower() == win.lower():
        support_color = wtxt

    def _set_theme_default(checked: bool) -> None:
        gui_settings = gui_prefs.setdefault("gui_settings", {})
        if checked:
            active_theme = normalize_theme(getattr(window, "_current_theme", "") or "gruvbox")
            gui_settings["theme_default"] = active_theme
        else:
            gui_settings.pop("theme_default", None)
        persist_gui_preferences(gui_prefs, project_root)

    try:
        check_action = QWidgetAction(menu)
        check_widget = QCheckBox("Usar tema atual como padrao")
        check_widget.setChecked(normalize_theme(theme_default or "") == current_theme)
        try:
            check_widget.setStyleSheet(f"color: {wtxt}; padding: 4px 10px;")
        except Exception as exc:
            logger.debug("Falha ao estilizar checkbox do menu de temas: %s", exc)
        check_widget.toggled.connect(_set_theme_default)
        check_action.setDefaultWidget(check_widget)
        menu.addAction(check_action)
    except Exception as exc:
        logger.debug("Falha ao construir checkbox de tema padrao; usando fallback de action: %s", exc)
        default_action = menu.addAction("Usar tema atual como padrao")
        if default_action is not None:
            try:
                default_action.setCheckable(True)
                default_action.setChecked(normalize_theme(theme_default or "") == current_theme)
                default_action.triggered.connect(_set_theme_default)
            except Exception as fallback_exc:
                logger.debug("Falha no fallback de action para tema padrao: %s", fallback_exc)
    menu.addSeparator()

    def _add_label(text: str):
        try:
            from PyQt6.QtWidgets import QWidgetAction, QLabel

            label = QLabel(text)
            try:
                label_color = support_color
                label.setStyleSheet(
                    f"color: {label_color}; font-weight: 600; padding: 4px 10px;"
                )
            except Exception as exc:
                logger.debug("Falha ao estilizar label de grupo no menu de temas: %s", exc)
            action = QWidgetAction(menu)
            action.setDefaultWidget(label)
            menu.addAction(action)
        except Exception as exc:
            logger.debug("Falha ao criar label custom no menu de temas; usando action simples: %s", exc)
            act = menu.addAction(text)
            if act is not None:
                try:
                    act.setEnabled(False)
                except Exception as disable_exc:
                    logger.debug("Falha ao desabilitar action de label no menu de temas: %s", disable_exc)

    def _add_group(items):
        for label, key in items:
            act = menu.addAction(label)
            if act is not None:
                trigger = getattr(act, "triggered", None)
                if trigger is not None:
                    try:
                        trigger.connect(partial(window.apply_theme, key))
                    except Exception as exc:
                        logger.warning("Falha ao conectar action de tema %s: %s", key, exc)

    _add_label("Light")
    _add_group(sorted(light_themes, key=lambda item: item[0].lower()))
    menu.addSeparator()
    _add_label("Dark")
    _add_group(sorted(dark_themes, key=lambda item: item[0].lower()))

    try:
        labels = [name for name, _ in light_themes + dark_themes]
        fm = menu.fontMetrics()
        widest = max(fm.horizontalAdvance(lbl) for lbl in labels)
        menu.setMinimumWidth(widest + 48)
    except Exception as exc:
        logger.debug("Falha ao calcular largura minima do menu de temas: %s", exc)
    btn = window.sender()
    try:
        if btn is not None:
            menu.exec(btn.mapToGlobal(btn.rect().bottomLeft()))
    except Exception as exc:
        logger.warning("Falha ao abrir menu de temas: %s", exc)


def _apply_global_palette(window, normalized: str, same_theme: bool):
    from gui.helpers import build_global_widget_qss

    if same_theme:
        return window.palette()
    try:
        from PyQt6.QtWidgets import QApplication, QStyleFactory
        app = QApplication.instance()
        pal = get_palette(normalized)
        try:
            if app is not None:
                styles = QStyleFactory.keys()
                if styles and 'Fusion' in styles:
                    app.setStyle('Fusion')
        except Exception as exc:
            logger.debug("Falha ao forcar estilo Fusion na aplicacao: %s", exc)
        if app is not None:
            app.setPalette(pal)
            try:
                block = build_global_widget_qss(pal)
                if getattr(window, "_last_global_theme_qss", None) != block:
                    app.setStyleSheet(block)
                    window._last_global_theme_qss = block
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
                'grayscale',
                'gruvbox',
                'dark',
                'dracula',
                'solarized-dark',
                'tokyo-night',
                'catppuccin',
                'nord',
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
            accent = roles.get('accent', tab_text)
            support_color = roles.get('support_text_color', tab_text)
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
        logger.debug("Falha ao aplicar estilo no header da tabela durante apply_theme: %s", exc)


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
                if active_search is not None and ctx.get("search_input") is active_search:
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
        light_themes = {'windows7', 'classico', 'solarized-light', 'mint-light', 'paper'}
        selector = getattr(window, 'column_selector', None)
        pal_active = window.palette()
        from PyQt6.QtGui import QPalette as _QPal
        txt = pal_active.color(_QPal.ColorRole.WindowText).name()
        base = pal_active.color(_QPal.ColorRole.Base).name()
        mid = pal_active.color(_QPal.ColorRole.Mid).name()
        high = pal_active.color(_QPal.ColorRole.Highlight).name()
        label_color = roles.get('label_color', txt)
        support_color = roles.get('support_text_color', label_color)
        indicator_color = roles.get('indicator_text_color', support_color)
        summary_color = roles.get('summary_text_color', label_color)
        summary_bg = roles.get('summary_frame_bg', roles.get('panel_bg', base))
        summary_border = roles.get('summary_frame_border', roles.get('panel_border', mid))
        accent = roles.get('accent', high)
        accent_soft = roles.get('accent_soft', support_color)
        input_bg = roles.get('input_bg', base)
        input_text = roles.get('input_text', txt)
        input_border = roles.get('input_border', mid)
        input_focus = roles.get('input_border_focus', accent)
        input_placeholder = roles.get('input_placeholder', support_color)
        panel_bg = roles.get('panel_bg', pal_active.color(_QPal.ColorRole.Window).name())
        panel_text = roles.get('panel_text', txt)
        panel_border = roles.get('panel_border', input_border)
        try:
            highlight_fg = pal_active.color(_QPal.ColorRole.HighlightedText).name()
        except Exception as exc:
            logger.debug("Falha ao obter cor de texto destacado da paleta: %s", exc)
            highlight_fg = None
        window._highlight_bg_color = high or highlight_bg_default
        window._highlight_text_color = highlight_fg or None
        window._highlight_font_weight = highlight_weight_default

        if hasattr(window, 'search_label'):
            window.search_label.setStyleSheet(f"color: {label_color}; font-weight: 600;")

        if hasattr(window, 'search_input') and window.search_input is not None:
            window.search_input.setStyleSheet(
                build_line_edit_qss(input_text, input_bg, input_border, input_focus, input_placeholder)
            )

        tool_btn_css = (
            "QToolButton {"
            f" color: {input_text}; background: {input_bg}; border:1px solid {input_border};"
            " border-radius:4px; padding:2px 6px; }"
            "QToolButton:pressed {"
            f" background: {accent_soft}; }}"
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
            "adv_responsavel_solicitante_button",
            "adv_responsavel_programacao_button",
            "adv_responsavel_execucao_button",
            "adv_responsavel_emissor_button",
        ]
        for name in adv_buttons:
            btn = getattr(window, name, None)
            if btn is not None:
                try:
                    btn.setStyleSheet(tool_btn_css)
                except Exception as exc:
                    logger.debug("Falha ao aplicar estilo no botao avancado %s: %s", name, exc)
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
                    widget.setStyleSheet(
                        build_line_edit_qss(input_text, input_bg, input_border, input_focus, input_placeholder)
                    )
                except Exception as exc:
                    logger.debug("Falha ao aplicar estilo no campo avancado %s: %s", name, exc)

        if hasattr(window, 'details_text'):
            if hasattr(window, 'details_group'):
                try:
                    from PyQt6.QtGui import QFont
                    base_font = window.details_group.font()
                    small_font = QFont(base_font)
                    size = small_font.pointSizeF()
                    if size <= 0:
                        size = float(small_font.pointSize())
                    if size > 0:
                        small_font.setPointSizeF(max(size - 1.5, 1.0))
                    window.details_text.setFont(small_font)
                except Exception as exc:
                    logger.debug("Falha ao ajustar fonte reduzida no painel de detalhes: %s", exc)
            if normalized in light_themes:
                window.details_text.setStyleSheet('')
            else:
                window.details_text.setStyleSheet(
                    "QTextEdit {"
                    f" color: {panel_text}; background: {panel_bg}; border: none; padding:4px;"
                    " }"
                )

        group_css = build_group_box_qss(panel_text, panel_border, panel_bg)

        if hasattr(window, 'details_group'):
            if normalized in light_themes:
                window.details_group.setStyleSheet('')
            else:
                window.details_group.setStyleSheet(group_css)

        if hasattr(window, 'col_filters_group'):
            if normalized in light_themes:
                window.col_filters_group.setStyleSheet('')
            else:
                window.col_filters_group.setStyleSheet(group_css)
        if hasattr(window, 'adv_filters_group'):
            if normalized in light_themes:
                window.adv_filters_group.setStyleSheet('')
            else:
                window.adv_filters_group.setStyleSheet(group_css)

        highlight_style = (
            f"font-weight:600; color:{accent}; background:{panel_bg}; "
            f"border:1px solid {panel_border}; border-radius:4px; padding:2px 6px;"
        )
        window._week_label_style = highlight_style
        if hasattr(window, 'week_label'):
            window.week_label.setStyleSheet(highlight_style)

        if hasattr(window, 'status_label'):
            window.status_label.setStyleSheet(
                f"color:{accent}; background:{panel_bg}; border:1px solid {panel_border}; border-radius:4px; padding:2px 6px;"
            )

        if hasattr(window, 'search_help'):
            css = f"font-size:10px; color:{support_color}; margin:0; padding:0;"
            if hasattr(window, 'status_label'):
                try:
                    window.search_help.setFont(window.status_label.font())
                except Exception as exc:
                    logger.debug("Falha ao sincronizar fonte de search_help com status_label: %s", exc)
            window.search_help.setStyleSheet(css)

        if hasattr(window, 'col_filter_indicator'):
            window.col_filter_indicator.setStyleSheet(f"color:{indicator_color};")

        if hasattr(window, 'filters_summary_label'):
            window.filters_summary_label.setStyleSheet(f"color:{summary_color};")

        if hasattr(window, 'filters_summary_frame'):
            window.filters_summary_frame.setStyleSheet(
                "QFrame {"
                f" background:{summary_bg}; border:1px solid {summary_border}; border-radius:4px; padding:4px;"
                " }"
            )
        if hasattr(window, 'clear_all_filters_btn'):
            window.clear_all_filters_btn.setStyleSheet(highlight_style)
        if hasattr(window, 'export_list_btn'):
            window.export_list_btn.setStyleSheet(highlight_style)
        if hasattr(window, 'undo_filter_btn'):
            window.undo_filter_btn.setStyleSheet(highlight_style)
        if hasattr(window, 'clear_all_btn'):
            window.clear_all_btn.setStyleSheet(highlight_style)

        if selector is not None and hasattr(selector, 'summary_label'):
            selector.summary_label.setStyleSheet(f"color:{indicator_color};")

        if hasattr(window, 'col_filters_hint'):
            window.col_filters_hint.setStyleSheet(f"color:{support_color}; font-size: 11px;")
    except Exception as exc:
        logger.warning("Falha no bloco principal de estilizacao do tema: %s", exc)


def _refresh_filter_widgets_for_theme(window, normalized: str) -> None:
    try:
        if getattr(window, "_current_tab_kind", None) == "filters":
            window._pending_theme_refresh_column_filters = normalized
        else:
            window._refresh_column_filter_widgets()
            window._pending_theme_refresh_column_filters = None
    except Exception as exc:
        logger.debug("Falha ao atualizar widgets dinamicos de filtro por coluna no tema: %s", exc)


def _persist_theme_selection(window, normalized: str, gui_prefs: dict, project_root: str) -> None:
    try:
        gui_settings = gui_prefs.setdefault('gui_settings', {})
        if gui_settings.get('theme') != normalized:
            gui_settings['theme'] = normalized
            ok = persist_gui_preferences(gui_prefs, project_root, retries=1)
            if not ok:
                if not os.environ.get("PYTEST_CURRENT_TEST"):
                    try:
                        window.status_label.setText("Status: Tema aplicado; falha ao salvar preferencia.")
                    except Exception:
                        pass
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


def apply_macos_contrast(window, theme_name: str) -> None:
    if sys.platform != 'darwin':
        return
    normalized = normalize_theme(theme_name)
    roles = get_theme_roles(normalized)
    text_color = roles.get('panel_text')
    bg_color = roles.get('panel_bg')
    border_color = roles.get('panel_border')
    label_color = roles.get('label_color')
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
            new_qss = (existing + ("\n" if existing and not existing.endswith("\n") else "") + block).strip()
            central.setStyleSheet(new_qss)
    except Exception as exc:
        logger.debug("Falha ao aplicar ajustes de contraste macOS no tema %s: %s", normalized, exc)
