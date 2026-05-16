from __future__ import annotations

import logging
from typing import Any, cast

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSpacerItem,
    QWidget,
)

logger = logging.getLogger(__name__)


def _set_min_height(window: Any, widget: Any, height: int, label: str) -> None:
    setter = getattr(window, "_set_widget_min_height_safe", None)
    if callable(setter):
        setter(widget, height, label)
        return
    widget.setMinimumHeight(height)


def _set_fixed_height(window: Any, widget: Any, height: int, label: str) -> None:
    setter = getattr(window, "_set_widget_fixed_height_safe", None)
    if callable(setter):
        setter(widget, height, label)
        return
    widget.setFixedHeight(height)


def _create_search_controls(window: Any) -> dict[str, Any]:
    search_input = QLineEdit()
    search_input.setPlaceholderText(
        "Termos cumulativos separados por virgula; ! exclui termo"
    )
    search_input.setToolTip(
        "Na busca rapida, virgulas separam termos cumulativos (logica E).\n"
        "Todos os termos digitados devem ser satisfeitos na mesma linha.\n\n"
        "A busca pesquisa nas colunas relevantes da GUI; datas puras ficam nos filtros especificos.\n\n"
        "Modos por termo: \n"
        "- contem (padrao): foo\n- comeca com: ^foo\n- termina com: foo$\n- igual: =foo\n- regex seguro: ~^foo ou ~foo$\n- negativos: prefixe ! (ex.: !^adm, !$2025)"
    )
    search_input.setMinimumWidth(360)
    _set_min_height(window, search_input, 26, "campo de pesquisa")
    try:
        search_input.setFrame(False)
    except Exception as exc:
        logger.debug("Falha ao remover frame interno da pesquisa: %s", exc)
    search_input.returnPressed.connect(window._on_general_search_apply_clicked)
    search_input.textChanged.connect(window._on_search_text_changed)

    search_button = QPushButton("↵")
    _set_fixed_height(
        window,
        search_button, 22, "botao Aplicar da pesquisa geral"
    )
    try:
        search_button.setFixedWidth(26)
    except Exception as exc:
        logger.debug("Falha ao aplicar estilo no botao Aplicar da pesquisa: %s", exc)
    search_button.setToolTip("Aplicar busca (Enter)")
    search_button.clicked.connect(window._on_general_search_apply_clicked)

    clear_filter_button = QPushButton("⌫")
    _set_fixed_height(window, clear_filter_button, 22, "botao Limpar Busca")
    try:
        clear_filter_button.setFixedWidth(26)
    except Exception as exc:
        logger.debug(
            "Falha ao aplicar estilo no botao Limpar Busca da pesquisa: %s", exc
        )
    clear_filter_button.clicked.connect(window._on_general_search_clear_clicked)
    clear_filter_button.setToolTip(
        "Limpa apenas a busca e cancela a busca em andamento. "
        "Filtros de coluna e avancados continuam ativos."
    )
    clear_filter_button.setEnabled(False)

    search_box = QFrame()
    search_box.setObjectName("quickSearchBox")
    _set_fixed_height(window, search_box, 26, "caixa de pesquisa rapida")
    search_box.setMinimumWidth(425)
    search_box.setMaximumWidth(950)
    search_box.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
    search_box_layout = QHBoxLayout(cast(Any, search_box))
    search_box_layout.setContentsMargins(3, 2, 3, 2)
    search_box_layout.setSpacing(2)
    search_box_layout.addWidget(cast(Any, clear_filter_button), 0)
    search_box_layout.addWidget(cast(Any, search_input), 1)
    search_box_layout.addWidget(cast(Any, search_button), 0)
    _apply_quick_search_box_style(search_box)

    return {
        "search_input": search_input,
        "quick_search_box": search_box,
        "search_button": search_button,
        "clear_filter_button": clear_filter_button,
    }


def _create_filter_action_controls(
    window: Any, action_button_style: str
) -> dict[str, Any]:
    undo_filter_btn = QPushButton("↺")
    _set_fixed_height(window, undo_filter_btn, 26, "botao desfazer filtros")
    try:
        undo_filter_btn.setFixedWidth(34)
        undo_filter_btn.setStyleSheet(action_button_style)
    except Exception as exc:
        logger.debug("Falha ao configurar botao undo de filtros: %s", exc)
    undo_filter_btn.setToolTip("Desfaz o ultimo filtro aplicado")
    undo_filter_btn.clicked.connect(window._restore_last_filter_state)

    export_list_btn = QPushButton("Exportar Filtros")
    _set_fixed_height(
        window,
        export_list_btn, 26, "botao Exportar Filtros"
    )
    export_list_btn.setMaximumWidth(150)
    export_list_btn.setToolTip("Exportar a lista filtrada atual para arquivo txt")
    export_list_btn.clicked.connect(window._export_current_list_txt)
    try:
        export_list_btn.setStyleSheet(action_button_style)
    except Exception as exc:
        logger.debug("Falha ao aplicar estilo no botao exportar filtros: %s", exc)

    save_filter_button = QPushButton("Salvar Filtros")
    _set_fixed_height(
        window,
        save_filter_button, 26, "botao Salvar Filtros"
    )
    save_filter_button.setMaximumWidth(140)
    save_filter_button.setToolTip(
        "Salva o estado atual: busca, filtros de coluna, filtros avancados e perfil."
    )
    try:
        save_filter_button.setStyleSheet(action_button_style)
    except Exception as exc:
        logger.debug("Falha ao aplicar estilo no botao Salvar Filtros: %s", exc)
    save_filter_button.clicked.connect(window.save_current_filter)

    filter_tags_widget = QWidget()
    _set_fixed_height(
        window,
        filter_tags_widget, 26, "area de filtros salvos"
    )
    filter_tags_widget.setMaximumWidth(280)
    filter_tags_widget.setSizePolicy(
        QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Fixed
    )
    filter_tags_layout = QHBoxLayout(cast(Any, filter_tags_widget))
    filter_tags_layout.setContentsMargins(0, 0, 0, 0)
    filter_tags_layout.setSpacing(5)

    return {
        "undo_filter_btn": undo_filter_btn,
        "export_list_btn": export_list_btn,
        "save_filter_button": save_filter_button,
        "filter_tags_widget": filter_tags_widget,
        "filter_tags_layout": filter_tags_layout,
    }


def _apply_quick_search_box_style(search_box: QFrame) -> None:
    try:
        search_box.setStyleSheet(
            "QFrame#quickSearchBox {"
            "border:1px solid palette(mid);"
            "border-radius:4px;"
            "background:palette(base);"
            "}"
            "QFrame#quickSearchBox QPushButton {"
            "border:0;"
            "background:transparent;"
            "padding:0;"
            "font-weight:700;"
            "font-size:12px;"
            "}"
            "QFrame#quickSearchBox QPushButton:hover {"
            "background:palette(alternate-base);"
            "}"
        )
    except Exception as exc:
        logger.debug("Falha ao aplicar estilo inicial da caixa de pesquisa: %s", exc)


def build_search_bar(
    window: Any, tab_layout: Any, *, action_button_style: str
) -> dict[str, Any]:
    search_row = QHBoxLayout()
    search_row.setContentsMargins(0, 0, 0, 0)
    search_row.setSpacing(6)

    left = QHBoxLayout()
    left.setContentsMargins(0, 0, 0, 0)
    search_controls = _create_search_controls(window)
    action_controls = _create_filter_action_controls(window, action_button_style)
    search_box = search_controls["quick_search_box"]
    undo_filter_btn = action_controls["undo_filter_btn"]
    export_list_btn = action_controls["export_list_btn"]
    save_filter_button = action_controls["save_filter_button"]
    filter_tags_widget = action_controls["filter_tags_widget"]

    left.addWidget(undo_filter_btn)
    left.addWidget(search_box)
    left.addWidget(export_list_btn)
    left.addWidget(save_filter_button)
    left.addSpacing(8)
    left.addWidget(filter_tags_widget)

    search_row.addLayout(cast(Any, left))
    search_row.addItem(
        QSpacerItem(0, 0, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
    )
    tab_layout.addLayout(cast(Any, search_row))

    search_help = QLabel(
        "Use termos positivos e ! para excluir. A busca vale para qualquer coluna."
    )
    search_help.setWordWrap(False)
    try:
        search_help.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
    except Exception as exc:
        logger.debug("Falha ao aplicar size policy na ajuda de pesquisa: %s", exc)
    search_help.setStyleSheet("color: palette(mid); margin:0; padding:0;")
    try:
        search_help.setVisible(False)
    except Exception as exc:
        logger.debug("Falha ao ocultar texto de ajuda da pesquisa: %s", exc)
    tab_layout.addSpacing(4)

    return {
        **search_controls,
        **action_controls,
        "search_help": search_help,
    }


def build_filters_summary_bar(
    window: Any, tab_layout: Any, *, action_button_style: str
) -> dict[str, Any]:
    filters_summary_frame = QFrame()
    filters_summary_frame.setObjectName("filtersSummaryFrame")
    filters_summary_frame.setFrameShape(QFrame.Shape.StyledPanel)
    _set_fixed_height(
        window,
        filters_summary_frame, 44, "barra de filtros ativos"
    )
    summary_layout = QHBoxLayout(cast(Any, filters_summary_frame))
    summary_layout.setContentsMargins(6, 4, 6, 4)
    summary_layout.setSpacing(8)
    try:
        align_middle = cast(Any, Qt).AlignmentFlag.AlignVCenter
        cast(Any, summary_layout).setAlignment(align_middle)
    except Exception as exc:
        logger.debug("Falha ao centralizar resumo de filtros: %s", exc)
        align_middle = None

    filters_summary_label = QLabel("Nenhum filtro ativo")
    filters_summary_label.setAutoFillBackground(False)
    if window._info_font is not None:
        try:
            filters_summary_label.setFont(cast(Any, QFont(window._info_font)))
        except Exception as exc:
            logger.debug("Falha ao aplicar fonte no resumo de filtros: %s", exc)

    filters_summary_items_widget = QWidget()
    filters_summary_items_layout = QHBoxLayout(cast(Any, filters_summary_items_widget))
    filters_summary_items_layout.setContentsMargins(0, 0, 0, 0)
    filters_summary_items_layout.setSpacing(6)

    filters_summary_scroll = QScrollArea()
    filters_summary_scroll.setWidgetResizable(False)
    filters_summary_scroll.setWidget(cast(Any, filters_summary_items_widget))
    filters_summary_scroll.setFrameShape(QFrame.Shape.NoFrame)
    _set_fixed_height(
        window,
        filters_summary_scroll, 36, "area rolavel de filtros ativos"
    )
    try:
        scroll_policy = cast(Any, Qt).ScrollBarPolicy
        filters_summary_scroll.setHorizontalScrollBarPolicy(
            scroll_policy.ScrollBarAsNeeded
        )
        filters_summary_scroll.setVerticalScrollBarPolicy(scroll_policy.ScrollBarAlwaysOff)
    except Exception as exc:
        logger.debug("Falha ao configurar scroll horizontal de filtros ativos: %s", exc)
    try:
        filters_summary_scroll.setStyleSheet(
            "QScrollArea { border:0; background:transparent; }"
            "QScrollArea > QWidget > QWidget { background:transparent; }"
        )
        filters_summary_viewport = filters_summary_scroll.viewport()
        if filters_summary_viewport is not None:
            filters_summary_viewport.setAutoFillBackground(False)
    except Exception as exc:
        logger.debug("Falha ao aplicar estilo no scroll de filtros ativos: %s", exc)

    clear_all_filters_btn = QPushButton("⌫")
    clear_all_filters_btn.setFixedWidth(34)
    clear_all_filters_btn.setToolTip("Limpar Filtros")
    clear_all_filters_btn.clicked.connect(window._on_clear_all_filters_clicked)
    try:
        clear_all_filters_btn.setStyleSheet(action_button_style)
    except Exception as exc:
        logger.debug("Falha ao aplicar estilo no botao limpar todos os filtros: %s", exc)

    summary_text_layout = QHBoxLayout()
    summary_text_layout.setContentsMargins(0, 0, 0, 0)
    summary_text_layout.setSpacing(8)
    summary_text_layout.addWidget(cast(Any, filters_summary_label), 0)
    summary_text_layout.addWidget(cast(Any, filters_summary_scroll), 1)
    if align_middle is None:
        summary_layout.addWidget(cast(Any, clear_all_filters_btn), 0)
    else:
        summary_layout.addWidget(cast(Any, clear_all_filters_btn), 0, align_middle)
    summary_layout.addLayout(cast(Any, summary_text_layout), 1)
    tab_layout.addWidget(cast(Any, filters_summary_frame))
    filters_summary_frame.setVisible(True)
    try:
        window._update_undo_button_state()
    except Exception as exc:
        logger.debug("Falha ao atualizar estado inicial do botao undo: %s", exc)

    return {
        "filters_summary_frame": filters_summary_frame,
        "filters_summary_label": filters_summary_label,
        "filters_summary_items_widget": filters_summary_items_widget,
        "filters_summary_items_layout": filters_summary_items_layout,
        "filters_summary_scroll": filters_summary_scroll,
        "clear_all_filters_btn": clear_all_filters_btn,
    }
