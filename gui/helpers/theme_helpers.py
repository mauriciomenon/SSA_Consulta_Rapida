# gui/helpers/theme_helpers.py
# Pure stylesheet builder functions for theme application

import re

from PyQt6.QtGui import QPalette

_HEX_COLOR_RE = re.compile(r"^#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6}|[0-9a-fA-F]{8})$")
_COLOR_NAME_RE = re.compile(r"^[a-zA-Z][a-zA-Z0-9_-]*$")


def _is_css_color(value: str) -> bool:
    text = value.strip()
    if not text:
        return False
    return bool(_HEX_COLOR_RE.fullmatch(text) or _COLOR_NAME_RE.fullmatch(text))


def pick_css_color(*candidates: object, fallback: str) -> str:
    """Return first valid CSS color candidate, fallback, or safe default."""
    for candidate in candidates:
        if isinstance(candidate, str):
            value = candidate.strip()
            if value and _is_css_color(value):
                return value
    if isinstance(fallback, str) and _is_css_color(fallback):
        return fallback.strip()
    return "#000000"


def build_global_widget_qss(palette: QPalette) -> str:
    """
    Build global QSS for QMenu, QToolTip, and QComboBox widgets.

    This stylesheet ensures consistent colors across all dropdown menus,
    tooltips, and combo boxes, preventing white backgrounds with light text.

    Args:
        palette: QPalette with theme colors loaded

    Returns:
        QSS string with SSA_THEME_QSS markers for replacement
    """
    win = palette.color(QPalette.ColorRole.Window).name()
    wtxt = palette.color(QPalette.ColorRole.WindowText).name()
    base = palette.color(QPalette.ColorRole.Base).name()
    text = palette.color(QPalette.ColorRole.Text).name()
    mid = palette.color(QPalette.ColorRole.Mid).name()
    hi = palette.color(QPalette.ColorRole.Highlight).name()
    hitxt = palette.color(QPalette.ColorRole.HighlightedText).name()
    ttbase = palette.color(QPalette.ColorRole.ToolTipBase).name()
    tttext = palette.color(QPalette.ColorRole.ToolTipText).name()

    return (
        "/* SSA_THEME_QSS_START */\n"
        f"QMenu {{ background-color: {win}; color: {wtxt}; border:1px solid {mid}; }}\n"
        f"QMenu::separator {{ height:1px; background: {mid}; margin:4px 8px; }}\n"
        f"QMenu::item:selected {{ background-color: {hi}; color: {hitxt}; }}\n"
        f"QToolTip {{ background-color: {ttbase}; color: {tttext}; border:1px solid {mid}; }}\n"
        f"QComboBox {{ background-color: {base}; color: {text}; border:1px solid {mid}; }}\n"
        f"QComboBox QAbstractItemView {{ background-color: {base}; color: {text}; selection-background-color: {hi}; selection-color: {hitxt}; border:1px solid {mid}; }}\n"
        f"QCheckBox {{ color: {text}; }}\n"
        f"QCheckBox::indicator {{ width: 14px; height: 14px; border:1px solid {mid}; background: {base}; }}\n"
        f"QCheckBox::indicator:checked {{ background: {hi}; border:1px solid {hi}; }}\n"
        "/* SSA_THEME_QSS_END */"
    )


def build_central_widget_qss(bg_color: str) -> str:
    """
    Build QSS for central widget background.

    Used in dark themes to ensure the central widget background matches
    the theme and prevents white boxes from appearing.

    Args:
        bg_color: Hex color string (e.g., '#2c2c2c')

    Returns:
        QSS string with SSA_MAIN_BG markers for replacement
    """
    return (
        "/* SSA_MAIN_BG_START */\n"
        f"QWidget {{ background-color: {bg_color}; }}\n"
        "/* SSA_MAIN_BG_END */"
    )


def replace_tagged_qss_block(
    existing: str, *, start_marker: str, end_marker: str, block: str
) -> str:
    current = str(existing or "")
    start = current.find(start_marker)
    if start != -1:
        end = current.find(end_marker, start)
        if end != -1:
            end += len(end_marker)
            current = (current[:start] + current[end:]).rstrip()
        else:
            current = current[:start].rstrip()
    block = str(block or "").strip()
    if not block:
        return current
    if current and not current.endswith("\n"):
        current += "\n"
    return (current + block).strip()


def build_group_box_qss(panel_text: str, panel_border: str, panel_bg: str) -> str:
    """
    Build QSS for QGroupBox styling.

    Used for details_group and col_filters_group to ensure proper
    borders and title positioning.

    Args:
        panel_text: Hex color for text (e.g., '#e0e0e0')
        panel_border: Hex color for border (e.g., '#555555')
        panel_bg: Hex color for background (e.g., '#2a2a2a')

    Returns:
        QSS string for QGroupBox
    """
    return (
        "QGroupBox {"
        f" color: {panel_text}; border:1px solid {panel_border}; border-radius:4px; margin-top: 10px;"
        " }"
        "QGroupBox::title {"
        " subcontrol-origin: margin;"
        " subcontrol-position: top left;"
        f" background-color: {panel_bg};"
        " left: 8px; padding:0 6px;"
        " }"
    )


def build_line_edit_qss(
    input_text: str,
    input_bg: str,
    input_border: str,
    input_focus: str,
    input_placeholder: str,
) -> str:
    """
    Build QSS for QLineEdit styling with focus and placeholder.

    Used for search_input and other line edit widgets.

    Args:
        input_text: Hex color for text
        input_bg: Hex color for background
        input_border: Hex color for normal border
        input_focus: Hex color for focus border
        input_placeholder: Hex color for placeholder text

    Returns:
        QSS string for QLineEdit
    """
    return (
        "QLineEdit {"
        f" color: {input_text}; background: {input_bg}; border:1px solid {input_border}; border-radius:4px; padding:3px 6px;"
        " }"
        "QLineEdit::placeholder {"
        f" color: {input_placeholder};"
        " }"
        "QLineEdit:focus {"
        f" border:1px solid {input_focus};"
        " }"
    )
