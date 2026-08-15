"""Qt widget construction for the SSA details dialog."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from gui.ssa.details_dialog_constants import (
    DERIVADAS_DIALOG_BOTTOM_TARGET_MIN_HEIGHT,
    DERIVADAS_DIALOG_DETAILS_INITIAL_HEIGHT,
    DERIVADAS_DIALOG_DETAILS_MIN_WIDTH,
    DERIVADAS_DIALOG_GRAPH_PANEL_MIN_HEIGHT,
    DERIVADAS_DIALOG_MIN_HEIGHT,
    DERIVADAS_DIALOG_MIN_WIDTH,
    DERIVADAS_DIALOG_GRAPH_RATIO,
    DERIVADAS_DIALOG_TREE_RATIO,
    DERIVADAS_DIALOG_TREE_MIN_WIDTH,
    DERIVADAS_SPLITTER_HANDLE_WIDTH,
)


@dataclass
class DetailsDialogWidgets:
    close_button: Any
    details_browser: Any
    details_splitter: Any
    dialog: Any
    export_button: Any
    root_layout: Any
    tree_graph_browser: Any
    tree_graph_label: Any
    tree_graph_panel: Any
    tree_graph_text_browser: Any
    tree_browser: Any


def build_details_dialog_widgets(window, target: str, *, svg_render_deps):
    from PyQt6.QtCore import Qt
    from PyQt6.QtWidgets import (
        QDialog,
        QGridLayout,
        QPushButton,
        QSplitter,
        QTextBrowser,
        QToolButton,
        QVBoxLayout,
        QWidget,
    )

    dialog = QDialog(window)
    dialog.setWindowTitle(f"Detalhes da SSA #{target}")
    dialog.setMinimumWidth(DERIVADAS_DIALOG_MIN_WIDTH)
    dialog.setMinimumHeight(DERIVADAS_DIALOG_MIN_HEIGHT)
    root_layout = QVBoxLayout(dialog)
    details_splitter = QSplitter(Qt.Orientation.Vertical)
    details_splitter.setChildrenCollapsible(False)
    details_splitter.setHandleWidth(DERIVADAS_SPLITTER_HANDLE_WIDTH)
    details_browser = _readonly_browser(
        QTextBrowser(), min_width=DERIVADAS_DIALOG_DETAILS_MIN_WIDTH
    )
    tree_browser = _readonly_browser(
        QTextBrowser(),
        min_width=DERIVADAS_DIALOG_TREE_MIN_WIDTH,
        min_height=DERIVADAS_DIALOG_GRAPH_PANEL_MIN_HEIGHT,
    )
    tree_graph_label = None
    tree_graph_text_browser = None
    if svg_render_deps is not None:
        from gui.ssa.main_window_bottom_section import DerivadasGraphLabel

        tree_graph_label = DerivadasGraphLabel(window)
        tree_graph_label.setParent(dialog)
        tree_graph_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        tree_graph_label.setStyleSheet("border:none; background:transparent;")
        tree_graph_label.setMinimumHeight(DERIVADAS_DIALOG_GRAPH_PANEL_MIN_HEIGHT)
        tree_graph_browser = tree_graph_label
    else:
        tree_graph_text_browser = _readonly_browser(
            QTextBrowser(), min_height=DERIVADAS_DIALOG_GRAPH_PANEL_MIN_HEIGHT
        )
        tree_graph_browser = tree_graph_text_browser
    tree_graph_panel = QWidget(dialog)
    tree_graph_panel_layout = QGridLayout(tree_graph_panel)
    tree_graph_panel_layout.setContentsMargins(0, 0, 0, 0)
    tree_graph_panel_layout.setSpacing(0)
    tree_graph_panel_layout.addWidget(
        tree_graph_browser,
        0,
        0,
        alignment=Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
    )
    export_button = QToolButton(tree_graph_panel)
    export_button.setText("Exportar")
    export_button.setAutoRaise(True)
    export_button.setToolTip("Exportar grafo em PNG, SVG ou Mermaid")
    tree_graph_panel_layout.addWidget(
        export_button,
        0,
        0,
        alignment=Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignRight,
    )
    close_button = QPushButton("Fechar")
    close_button.setMinimumWidth(180)
    close_button.setMaximumWidth(240)
    return DetailsDialogWidgets(
        close_button=close_button,
        details_browser=details_browser,
        details_splitter=details_splitter,
        dialog=dialog,
        export_button=export_button,
        root_layout=root_layout,
        tree_graph_browser=tree_graph_browser,
        tree_graph_label=tree_graph_label,
        tree_graph_panel=tree_graph_panel,
        tree_graph_text_browser=tree_graph_text_browser,
        tree_browser=tree_browser,
    )


def assemble_details_dialog_layout(widgets, *, qt_cls) -> None:
    from PyQt6.QtWidgets import QHBoxLayout, QSplitter

    details_derivadas_splitter = QSplitter(qt_cls.Orientation.Horizontal)
    details_derivadas_splitter.setChildrenCollapsible(False)
    details_derivadas_splitter.setHandleWidth(DERIVADAS_SPLITTER_HANDLE_WIDTH)
    widgets.details_splitter.addWidget(widgets.details_browser)
    details_derivadas_splitter.addWidget(widgets.tree_browser)
    details_derivadas_splitter.addWidget(widgets.tree_graph_panel)
    details_derivadas_splitter.setStretchFactor(0, DERIVADAS_DIALOG_TREE_RATIO)
    details_derivadas_splitter.setStretchFactor(1, DERIVADAS_DIALOG_GRAPH_RATIO)
    details_derivadas_splitter.setSizes(
        [DERIVADAS_DIALOG_TREE_RATIO * 10, DERIVADAS_DIALOG_GRAPH_RATIO * 10]
    )
    widgets.details_splitter.addWidget(details_derivadas_splitter)
    widgets.details_splitter.setStretchFactor(0, 1)
    widgets.details_splitter.setStretchFactor(1, 1)
    widgets.details_splitter.setSizes(
        [DERIVADAS_DIALOG_DETAILS_INITIAL_HEIGHT, DERIVADAS_DIALOG_BOTTOM_TARGET_MIN_HEIGHT]
    )
    widgets.root_layout.addWidget(widgets.details_splitter)
    close_row = QHBoxLayout()
    close_row.addStretch(1)
    close_row.addWidget(widgets.close_button)
    close_row.addStretch(1)
    widgets.root_layout.addLayout(close_row)


def _readonly_browser(browser, *, min_width=None, min_height=None):
    browser.setReadOnly(True)
    browser.setOpenLinks(False)
    browser.setOpenExternalLinks(False)
    if min_width is not None:
        browser.setMinimumWidth(min_width)
    if min_height is not None:
        browser.setMinimumHeight(min_height)
    return browser
