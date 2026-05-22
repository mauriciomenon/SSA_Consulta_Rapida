# gui/helpers/__init__.py
# Helper functions for GUI operations

from gui.helpers.formatting_helpers import (
    format_search_display,
    highlight_text,
    normalize_chunk_for_parse,
)
from gui.helpers.theme_helpers import (
    build_central_widget_qss,
    build_global_widget_qss,
    build_group_box_qss,
    build_line_edit_qss,
    replace_tagged_qss_block,
)

__all__ = [
    "build_global_widget_qss",
    "build_central_widget_qss",
    "build_group_box_qss",
    "build_line_edit_qss",
    "replace_tagged_qss_block",
    "normalize_chunk_for_parse",
    "format_search_display",
    "highlight_text",
]
