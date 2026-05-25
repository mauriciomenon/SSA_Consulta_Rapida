"""Bottom details and filter-panel construction for SSAMainWindow."""

from __future__ import annotations

import logging
from typing import Any, cast

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSplitter,
    QStackedWidget,
    QTabBar,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

logger = logging.getLogger(__name__)


class DerivadasGraphLabel(QLabel):
    def __init__(self, window: Any) -> None:
        super().__init__()
        self._window = window
        self._ssa_hitboxes: list[tuple[str, float, float, float, float]] = []
        self.setMouseTracking(True)

    def set_ssa_hitboxes(
        self, hitboxes: list[tuple[str, float, float, float, float]]
    ) -> None:
        self._ssa_hitboxes = list(hitboxes)
        self._set_node_cursor(False)

    def mouseMoveEvent(self, ev: Any) -> None:  # noqa: N802
        self._set_node_cursor(bool(self._ssa_at_event(ev)))
        super().mouseMoveEvent(ev)

    def leaveEvent(self, a0: Any) -> None:  # noqa: N802
        self._set_node_cursor(False)
        super().leaveEvent(a0)

    def _set_node_cursor(self, active: bool) -> None:
        try:
            self.setCursor(
                Qt.CursorShape.PointingHandCursor
                if active
                else Qt.CursorShape.ArrowCursor
            )
        except Exception as exc:
            logger.debug("Falha ao ajustar cursor do grafo de derivadas: %s", exc)

    def mousePressEvent(self, ev: Any) -> None:  # noqa: N802
        button_getter = getattr(ev, "button", None)
        if callable(button_getter) and button_getter() != Qt.MouseButton.LeftButton:
            super().mousePressEvent(ev)
            return
        ssa = self._ssa_at_event(ev)
        if ssa:
            jump = getattr(self._window, "_jump_to_ssa", None)
            if callable(jump):
                jump(ssa)
                return
        super().mousePressEvent(ev)

    def _ssa_at_event(self, event: Any) -> str:
        position_getter = getattr(event, "position", None)
        point = position_getter() if callable(position_getter) else event.pos()
        x = float(point.x())
        y = float(point.y())
        pixmap_getter = getattr(self, "pixmap", None)
        pixmap = pixmap_getter() if callable(pixmap_getter) else None
        if pixmap is not None:
            is_null = getattr(pixmap, "isNull", None)
            width_getter = getattr(pixmap, "width", None)
            height_getter = getattr(pixmap, "height", None)
            if (
                callable(width_getter)
                and callable(height_getter)
                and not (callable(is_null) and is_null())
            ):
                pixmap_w = float(width_getter())
                pixmap_h = float(height_getter())
                x -= max(0.0, (float(self.width()) - pixmap_w) / 2.0)
                y -= max(0.0, (float(self.height()) - pixmap_h) / 2.0)
        for ssa, left, top, right, bottom in self._ssa_hitboxes:
            if left <= x <= right and top <= y <= bottom:
                return ssa
        return ""


def build_bottom_filter_section(window: Any) -> dict[str, Any]:
    bottom_layout = QHBoxLayout()

    details_group, details_context = _build_details_panel(window)
    bottom_layout.addWidget(cast(Any, details_group), 2)
    bottom_layout.setAlignment(cast(Any, details_group), Qt.AlignmentFlag.AlignTop)

    column_context = _build_column_filters_panel_shell(window)
    col_filters_group = column_context["col_filters_group"]

    right_col_widget = QWidget()
    right_col = QVBoxLayout(cast(Any, right_col_widget))
    right_col.setContentsMargins(0, 0, 0, 0)

    filters_panel_group = QGroupBox("")
    filters_panel_layout = QVBoxLayout(cast(Any, filters_panel_group))
    filters_panel_layout.setContentsMargins(4, 2, 4, 4)
    filters_panel_layout.setSpacing(2)

    filter_panel_header, filter_panel_tab_bar, filter_panel_title = (
        _build_filter_panel_header(window)
    )
    filters_panel_layout.addWidget(cast(Any, filter_panel_header), 0)

    adv_group, adv_ctx = window._build_advanced_filters_panel()
    try:
        adv_group.setTitle("")
    except Exception as exc:
        logger.debug("Falha ao limpar titulo do grupo de filtros avancados: %s", exc)

    filters_panel_stack = QStackedWidget()
    filters_panel_stack.addWidget(col_filters_group)
    filters_panel_stack.addWidget(adv_group)
    filters_panel_layout.addWidget(cast(Any, filters_panel_stack), 1)

    right_col.addWidget(cast(Any, filters_panel_group), 1)
    bottom_layout.addWidget(cast(Any, right_col_widget), 3)

    _connect_filter_panel_tabs(
        window,
        filter_panel_tab_bar,
        filter_panel_title,
        filters_panel_stack,
    )

    return {
        "_bottom_layout": bottom_layout,
        "_adv_ctx": adv_ctx,
        "details_group": details_group,
        "filters_panel_group": filters_panel_group,
        "filter_panel_tab_bar": filter_panel_tab_bar,
        "filter_panel_title": filter_panel_title,
        "filters_panel_stack": filters_panel_stack,
        **details_context,
        **column_context,
    }


def _build_details_panel(window: Any) -> tuple[QGroupBox, dict[str, Any]]:
    details_group = QGroupBox("")
    details_group.setObjectName("detailsPanelGroup")
    details_layout = QVBoxLayout(cast(Any, details_group))
    details_layout.setContentsMargins(4, 2, 4, 4)
    details_layout.setSpacing(2)

    details_header, details_tab_bar, details_title = _build_details_panel_header(window)
    details_layout.addWidget(cast(Any, details_header), 0)

    details_stack = QStackedWidget()
    details_text = QTextBrowser()
    try:
        details_group.setSizePolicy(
            QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding
        )
    except Exception as exc:
        logger.debug("Falha ao configurar expansao do painel de detalhes: %s", exc)
    try:
        details_text.setFrameShape(QFrame.Shape.NoFrame)
    except Exception as exc:
        logger.debug("Falha ao remover frame do painel de detalhes: %s", exc)
    try:
        details_viewport = details_text.viewport()
        if details_viewport is not None:
            details_viewport.setAutoFillBackground(False)
            details_viewport.installEventFilter(window)
            window._details_text_viewport = details_viewport
    except Exception as exc:
        logger.debug("Falha ao configurar preenchimento do viewport de detalhes: %s", exc)
    details_text.setReadOnly(True)
    try:
        details_text.setOpenLinks(False)
        details_text.setOpenExternalLinks(False)
        details_text.anchorClicked.connect(window._on_details_anchor_clicked)
    except Exception as exc:
        logger.debug("Falha ao configurar links no painel de detalhes: %s", exc)
    details_stack.addWidget(cast(Any, details_text))

    details_derivadas_splitter = QSplitter(Qt.Orientation.Horizontal)
    details_derivadas_splitter.setChildrenCollapsible(False)
    details_tree_text = QTextBrowser()
    details_graph_label = DerivadasGraphLabel(window)
    details_tree_text.setReadOnly(True)
    details_tree_text.setOpenLinks(False)
    details_tree_text.setOpenExternalLinks(False)
    try:
        details_tree_text.setFrameShape(QFrame.Shape.NoFrame)
        details_tree_text.anchorClicked.connect(window._on_details_anchor_clicked)
    except Exception as exc:
        logger.debug("Falha ao configurar arvore de derivadas no painel principal: %s", exc)
    try:
        details_graph_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        details_graph_label.setTextFormat(Qt.TextFormat.RichText)
        details_graph_label.setStyleSheet("border:none; background:transparent;")
        details_graph_label.setMinimumHeight(120)
        details_graph_label.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
    except Exception as exc:
        logger.debug("Falha ao configurar grafo de derivadas no painel principal: %s", exc)
    details_derivadas_splitter.addWidget(cast(Any, details_tree_text))
    details_derivadas_splitter.addWidget(cast(Any, details_graph_label))
    details_derivadas_splitter.setStretchFactor(0, 1)
    details_derivadas_splitter.setStretchFactor(1, 2)
    details_stack.addWidget(cast(Any, details_derivadas_splitter))
    details_layout.addWidget(cast(Any, details_stack), 1)

    def _activate_details_panel(index: int) -> None:
        active_index = 1 if int(index) == 1 else 0
        try:
            details_stack.setCurrentIndex(active_index)
            details_title.setText("Derivadas" if active_index == 1 else "Detalhes")
            if active_index == 1:
                refresh_derivadas = getattr(
                    window,
                    "_refresh_main_details_derivadas_panel",
                    None,
                ) or getattr(window, "refresh_main_details_derivadas_panel", None)
                if callable(refresh_derivadas):
                    refresh_derivadas()
        except Exception as exc:
            logger.debug("Falha ao trocar aba local de detalhes: %s", exc)

    try:
        details_tab_bar.currentChanged.connect(_activate_details_panel)
        details_tab_bar.setCurrentIndex(0)
    except Exception as exc:
        logger.debug("Falha ao conectar abas de detalhes: %s", exc)

    return details_group, {
        "details_text": details_text,
        "details_tab_bar": details_tab_bar,
        "details_title": details_title,
        "details_stack": details_stack,
        "details_tree_text": details_tree_text,
        "details_graph_label": details_graph_label,
    }


def _build_details_panel_header(window: Any) -> tuple[QWidget, QTabBar, QLabel]:
    details_panel_header = QWidget()
    window._set_widget_fixed_height_safe(
        details_panel_header, 24, "cabecalho de abas de detalhes"
    )
    details_header_layout = QHBoxLayout(cast(Any, details_panel_header))
    details_header_layout.setContentsMargins(0, 0, 0, 0)
    details_header_layout.setSpacing(6)

    details_tab_bar = QTabBar()
    details_tab_bar.addTab("Detalhes")
    details_tab_bar.addTab("Derivadas")
    details_tab_bar.setToolTip("Alternar entre detalhes da SSA e relacoes de derivadas")
    try:
        details_tab_bar.setExpanding(False)
        details_tab_bar.setDrawBase(False)
        details_tab_bar.setUsesScrollButtons(False)
        details_tab_bar.setElideMode(Qt.TextElideMode.ElideNone)
        details_tab_bar.setMinimumWidth(244)
        details_tab_bar.setFixedHeight(22)
        details_tab_bar.setStyleSheet(
            "QTabBar::tab {"
            "min-width:112px; padding:1px 10px;"
            "border:1px solid palette(mid);"
            "border-bottom:0;"
            "margin-right:1px;"
            "}"
            "QTabBar::tab:selected {"
            "background:palette(highlight);"
            "color:palette(highlighted-text);"
            "}"
            "QTabBar::tab:!selected {"
            "background:palette(window);"
            "color:palette(windowText);"
            "}"
        )
    except Exception as exc:
        logger.debug("Falha ao configurar abas de detalhes: %s", exc)

    details_title = QLabel("")
    try:
        details_title.setVisible(False)
        details_title.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
    except Exception as exc:
        logger.debug("Falha ao configurar titulo de detalhes: %s", exc)

    details_header_layout.addWidget(cast(Any, details_tab_bar), 0)
    details_header_layout.addWidget(cast(Any, details_title), 0)
    details_header_layout.addStretch(1)
    return details_panel_header, details_tab_bar, details_title


def _build_column_filters_panel_shell(window: Any) -> dict[str, Any]:
    col_filters_group = QGroupBox("")
    col_filters_outer = QVBoxLayout(cast(Any, col_filters_group))
    col_filters_outer.setContentsMargins(1, 1, 1, 1)
    col_filters_outer.setSpacing(1)

    col_filters_scroll = QScrollArea()
    col_filters_scroll.setWidgetResizable(True)
    col_filters_container = QWidget()
    col_filters_list_layout = QVBoxLayout(cast(Any, col_filters_container))
    col_filters_scroll.setWidget(cast(Any, col_filters_container))
    col_filters_outer.addWidget(cast(Any, col_filters_scroll), 1)

    footer = QHBoxLayout()
    footer.addStretch()
    add_column_filter_btn = QPushButton("Adicionar filtro de coluna")
    add_column_filter_btn.setMaximumWidth(260)
    add_column_filter_btn.setToolTip(
        "Selecionar qualquer coluna para ativar filtro dedicado"
    )
    add_column_filter_btn.clicked.connect(window._open_add_column_filter_menu)
    footer.addWidget(cast(Any, add_column_filter_btn))
    footer.addSpacing(8)
    clear_all_btn = QPushButton("Limpar todos filtros de colunas")
    clear_all_btn.setMaximumWidth(260)
    clear_all_btn.clicked.connect(window._clear_all_column_filters)
    footer.addWidget(cast(Any, clear_all_btn))
    footer.addStretch()
    col_filters_outer.addLayout(cast(Any, footer))

    return {
        "col_filters_group": col_filters_group,
        "col_filters_scroll": col_filters_scroll,
        "col_filters_container": col_filters_container,
        "col_filters_list_layout": col_filters_list_layout,
        "add_column_filter_btn": add_column_filter_btn,
        "clear_all_btn": clear_all_btn,
    }


def _build_filter_panel_header(window: Any) -> tuple[QWidget, QTabBar, QLabel]:
    filter_panel_header = QWidget()
    window._set_widget_fixed_height_safe(
        filter_panel_header, 24, "cabecalho de abas de filtros"
    )
    filter_panel_header_layout = QHBoxLayout(cast(Any, filter_panel_header))
    filter_panel_header_layout.setContentsMargins(0, 0, 0, 0)
    filter_panel_header_layout.setSpacing(6)

    filter_panel_tab_bar = QTabBar()
    filter_panel_tab_bar.addTab("Por coluna")
    filter_panel_tab_bar.addTab("Avancados")
    filter_panel_tab_bar.setToolTip("Alternar entre filtros por coluna e avancados")
    try:
        filter_panel_tab_bar.setExpanding(False)
        filter_panel_tab_bar.setDrawBase(False)
        filter_panel_tab_bar.setFixedHeight(22)
        filter_panel_tab_bar.setStyleSheet(
            "QTabBar::tab {"
            "min-width:96px; padding:1px 10px;"
            "border:1px solid palette(mid);"
            "border-bottom:0;"
            "margin-right:1px;"
            "}"
            "QTabBar::tab:selected {"
            "background:palette(highlight);"
            "color:palette(highlighted-text);"
            "}"
            "QTabBar::tab:!selected {"
            "background:palette(window);"
            "color:palette(windowText);"
            "}"
        )
    except Exception as exc:
        logger.debug("Falha ao configurar barra local de abas de filtros: %s", exc)

    filter_panel_title = QLabel("Filtros por Coluna")
    try:
        filter_panel_title.setAlignment(cast(Any, Qt).AlignmentFlag.AlignCenter)
        filter_panel_title.setStyleSheet("font-weight:600; color:palette(windowText);")
        filter_panel_title.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
        )
    except Exception as exc:
        logger.debug("Falha ao configurar titulo da area de filtros: %s", exc)

    filter_panel_header_layout.addWidget(cast(Any, filter_panel_tab_bar), 0)
    filter_panel_header_layout.addWidget(cast(Any, filter_panel_title), 1)
    right_balance = QWidget()
    try:
        right_balance.setFixedWidth(202)
    except Exception as exc:
        logger.debug("Falha ao configurar balanceador da area de filtros: %s", exc)
    filter_panel_header_layout.addWidget(cast(Any, right_balance), 0)
    return filter_panel_header, filter_panel_tab_bar, filter_panel_title


def _connect_filter_panel_tabs(
    window: Any,
    filter_panel_tab_bar: QTabBar,
    filter_panel_title: QLabel,
    filters_panel_stack: QStackedWidget,
) -> None:
    def _activate_filter_panel(index: int) -> None:
        active_index = 1 if int(index) == 1 else 0
        window._active_filter_panel_kind = (
            "advanced" if active_index == 1 else "columns"
        )
        try:
            filters_panel_stack.setCurrentIndex(active_index)
            filter_panel_title.setText(
                "Filtros Avancados" if active_index == 1 else "Filtros por Coluna"
            )
        except Exception as exc:
            logger.debug("Falha ao trocar painel local de filtros: %s", exc)
        if active_index == 1:
            try:
                window._adv_options_dirty = True
                window._schedule_adv_options_refresh()
                window._reorganize_advanced_filters_grid(
                    window.adv_filters_group.width()
                )
            except Exception as exc:
                logger.debug("Falha ao atualizar filtros avancados locais: %s", exc)
        try:
            window._queue_bottom_panel_height_sync()
        except Exception as exc:
            logger.debug(
                "Falha ao sincronizar altura apos troca local de filtro: %s", exc
            )

    try:
        filter_panel_tab_bar.currentChanged.connect(_activate_filter_panel)
    except Exception as exc:
        logger.debug("Falha ao conectar aba local de filtros: %s", exc)
