from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from PyQt6.QtGui import QPalette

from gui.helpers import build_group_box_qss, build_line_edit_qss

LIGHT_THEME_KEYS = {
    "windows7",
    "classico",
    "solarized-light",
    "mint-light",
    "paper",
}


@dataclass(frozen=True, slots=True)
class ThemeWidgetStyleBundle:
    styles: dict[str, str]
    group_css: str
    panel_text: str
    panel_bg: str
    highlight_bg: str
    highlight_text: str | None
    highlight_font_weight: str


def build_theme_widget_style_bundle(
    palette: QPalette,
    roles: dict[str, Any],
    *,
    highlight_bg_default: str,
    highlight_weight_default: str,
) -> ThemeWidgetStyleBundle:
    txt = palette.color(QPalette.ColorRole.WindowText).name()
    base = palette.color(QPalette.ColorRole.Base).name()
    mid = palette.color(QPalette.ColorRole.Mid).name()
    high = palette.color(QPalette.ColorRole.Highlight).name()
    label_color = roles.get("label_color", txt)
    support_color = roles.get("support_text_color", label_color)
    indicator_color = roles.get("indicator_text_color", support_color)
    summary_color = roles.get("summary_text_color", label_color)
    summary_bg = roles.get("summary_frame_bg", roles.get("panel_bg", base))
    summary_border = roles.get("summary_frame_border", roles.get("panel_border", mid))
    accent = roles.get("accent", high)
    accent_soft = roles.get("accent_soft", support_color)
    input_bg = roles.get("input_bg", base)
    input_text = roles.get("input_text", txt)
    input_border = roles.get("input_border", mid)
    input_focus = roles.get("input_border_focus", accent)
    input_placeholder = roles.get("input_placeholder", support_color)
    panel_bg = roles.get("panel_bg", palette.color(QPalette.ColorRole.Window).name())
    panel_text = roles.get("panel_text", txt)
    panel_border = roles.get("panel_border", input_border)
    try:
        highlight_text = palette.color(QPalette.ColorRole.HighlightedText).name()
    except Exception:
        highlight_text = None
    styles = _build_theme_style_map(
        label_color=label_color,
        input_text=input_text,
        input_bg=input_bg,
        input_border=input_border,
        input_focus=input_focus,
        input_placeholder=input_placeholder,
        accent=accent,
        accent_soft=accent_soft,
        support_color=support_color,
        panel_text=panel_text,
        panel_bg=panel_bg,
        panel_border=panel_border,
        indicator_color=indicator_color,
        summary_color=summary_color,
        summary_bg=summary_bg,
        summary_border=summary_border,
    )
    return ThemeWidgetStyleBundle(
        styles=styles,
        group_css=build_group_box_qss(panel_text, panel_border, panel_bg),
        panel_text=panel_text,
        panel_bg=panel_bg,
        highlight_bg=high or highlight_bg_default,
        highlight_text=highlight_text,
        highlight_font_weight=highlight_weight_default,
    )


def get_details_text_theme_font(window):
    from PyQt6.QtGui import QFont

    details_group = getattr(window, "details_group", None)
    if details_group is None:
        return None
    base_font = details_group.font()
    resolved_size = _resolve_theme_font_size(base_font)
    if resolved_size is None:
        return None
    unit, size = resolved_size
    font_signature = (unit, float(size), base_font.family(), int(base_font.weight()))
    cached_font = getattr(window, "_details_text_small_font_cached", None)
    cached_signature = getattr(window, "_details_text_small_font_signature", None)
    should_rebuild = not isinstance(cached_font, QFont) or (
        cached_signature != font_signature
    )
    if should_rebuild:
        cached_font = QFont(base_font)
        if unit == "pixel":
            cached_font.setPixelSize(max(int(round(size)) - 2, 1))
        else:
            cached_font.setPointSizeF(max(size - 1.5, 1.0))
        window._details_text_small_font_cached = cached_font
        window._details_text_small_font_signature = font_signature
        window._details_text_small_font_base_size = float(size)
        window._details_text_small_font_base_family = font_signature[2]
        window._details_text_small_font_base_weight = font_signature[3]
    return getattr(window, "_details_text_small_font_cached", None)


def _resolve_theme_font_size(base_font) -> tuple[str, float] | None:
    point_size = base_font.pointSizeF()
    if point_size <= 0:
        point_size = float(base_font.pointSize())
    if point_size > 0:
        return "point", float(point_size)
    pixel_size = base_font.pixelSize()
    if pixel_size > 0:
        return "pixel", float(pixel_size)
    return None


def _build_theme_style_map(
    *,
    label_color: str,
    input_text: str,
    input_bg: str,
    input_border: str,
    input_focus: str,
    input_placeholder: str,
    accent: str,
    accent_soft: str,
    support_color: str,
    panel_text: str,
    panel_bg: str,
    panel_border: str,
    indicator_color: str,
    summary_color: str,
    summary_bg: str,
    summary_border: str,
) -> dict[str, str]:
    line_edit_css = build_line_edit_qss(
        input_text, input_bg, input_border, input_focus, input_placeholder
    )
    return {
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
        "highlight_style": (
            f"font-weight:600; color:{accent}; background:{panel_bg}; "
            f"border:1px solid {panel_border}; border-radius:4px; padding:2px 6px;"
        ),
        "status_label_css": (
            f"color:{accent}; background:{panel_bg}; border:1px solid {panel_border}; "
            "border-radius:4px; padding:2px 6px;"
        ),
        "search_help_css": (
            f"font-size:10px; color:{support_color}; margin:0; padding:0;"
        ),
        "indicator_css": f"color:{indicator_color};",
        "filters_summary_label_css": (
            f"color:{summary_color}; background:transparent; padding:0 2px;"
        ),
        "filters_summary_frame_css": (
            "QFrame#filtersSummaryFrame {"
            f" background:{summary_bg}; border:1px solid {summary_border}; border-radius:4px;"
            " }"
        ),
        "filters_summary_scroll_css": (
            "QScrollArea { border:0; background:transparent; }"
            "QScrollArea > QWidget > QWidget { background:transparent; }"
        ),
        "tab_bar_css": (
            "QTabBar::tab {"
            f"font-weight:400; color:{panel_text}; background:{panel_bg}; "
            f"border:1px solid {panel_border}; border-bottom:0; "
            "min-width:96px; padding:1px 10px; margin-right:1px;"
            "}"
            "QTabBar::tab:selected {"
            f"background:{accent}; color:{panel_bg}; font-weight:700; border:1px solid {accent};"
            "border-bottom:0;"
            "}"
            "QTabBar::tab:!selected {"
            f"background:{panel_bg}; color:{panel_text}; font-weight:400; border:1px solid {panel_border};"
            "border-bottom:0;"
            "}"
        ),
        "footer_btn_css": (
            f"QPushButton {{ color:{panel_text}; background:{panel_bg}; "
            f"border:1px solid {panel_border}; border-radius:4px; padding:4px 10px; }}\n"
            f"QPushButton:hover {{ border:1px solid {accent}; }}\n"
        ),
        "hint_css": f"color:{support_color}; font-size: 11px;",
    }
