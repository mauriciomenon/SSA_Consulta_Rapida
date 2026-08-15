"""Style helpers for the active filters summary."""

from __future__ import annotations


def build_summary_button_stylesheet(
    *,
    border: str,
    accent: str,
    background: str,
    text_color: str,
) -> str:
    return (
        "QPushButton {"
        f"border:1px solid {border};"
        "border-radius:4px;"
        "padding:2px 6px;"
        "font-weight:600;"
        f"background:{background};"
        f"color:{text_color};"
        "text-align:left;"
        "}"
        "QPushButton:hover {"
        f"border-color:{accent};"
        "}"
    )
