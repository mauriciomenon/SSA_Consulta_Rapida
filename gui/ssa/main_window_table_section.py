"""Main-table UI construction for SSAMainWindow."""

from __future__ import annotations

import logging
from typing import Any, cast

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QAbstractItemView, QHeaderView, QTableWidget

logger = logging.getLogger(__name__)


def build_main_table_widget(window: Any) -> QTableWidget:
    table_widget = QTableWidget()
    table_widget.setEditTriggers(cast(Any, QTableWidget.EditTrigger.NoEditTriggers))
    table_widget.setSelectionBehavior(
        cast(Any, QAbstractItemView.SelectionBehavior.SelectRows)
    )
    window._set_widget_min_height_safe(table_widget, 220, "tabela principal")

    header = table_widget.horizontalHeader()
    vertical_header = table_widget.verticalHeader()
    if header is not None and vertical_header is not None:
        header.setSectionResizeMode(cast(Any, QHeaderView.ResizeMode.Interactive))
        vertical_header.setVisible(False)
        vertical_header.setSectionResizeMode(cast(Any, QHeaderView.ResizeMode.Fixed))
        vertical_header.setDefaultSectionSize(24)
        header.sectionResized.connect(window._on_header_section_resized)
    else:
        logger.warning(
            "Header da tabela indisponivel; configuracao avancada de colunas ignorada."
        )

    table_widget.doubleClicked.connect(window.on_table_double_click)
    table_widget.cellClicked.connect(window.on_table_cell_clicked)
    table_widget.itemSelectionChanged.connect(window.update_details_from_selection)

    _configure_table_header(window, header)
    table_widget.setContextMenuPolicy(cast(Any, Qt.ContextMenuPolicy.CustomContextMenu))
    table_widget.customContextMenuRequested.connect(window.show_context_menu)
    return table_widget


def _configure_table_header(window: Any, header: Any) -> None:
    if header is None:
        return
    try:
        header.setSectionsClickable(True)
        header.setSortIndicatorShown(True)
        try:
            header.setSectionsMovable(True)
        except Exception as exc:
            logger.debug("Falha ao habilitar drag and drop no header da tabela: %s", exc)
        try:
            header.setFirstSectionMovable(False)
        except Exception as exc:
            logger.debug("Falha ao fixar primeira secao do header da tabela: %s", exc)
        try:
            header.setMinimumSectionSize(26)
            header.setDefaultSectionSize(92)
        except Exception as exc:
            logger.debug(
                "Falha ao configurar tamanho minimo/default do header da tabela: %s",
                exc,
            )
        try:
            font = header.font()
            font.setBold(False)
            header.setFont(font)
            header.setStyleSheet("QHeaderView::section{font-weight: normal;}")
        except Exception as exc:
            logger.debug("Falha ao aplicar estilo/fonte no header da tabela: %s", exc)
        header.sectionClicked.connect(window.on_header_clicked)
        header.sectionMoved.connect(window._on_header_section_moved)
        header.setContextMenuPolicy(cast(Any, Qt.ContextMenuPolicy.CustomContextMenu))
        header.customContextMenuRequested.connect(window.show_header_context_menu)
        header.installEventFilter(window)
    except Exception as exc:
        logger.warning("Falha ao configurar comportamento do header da tabela: %s", exc)
