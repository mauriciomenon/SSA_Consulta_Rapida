from __future__ import annotations

import logging
from collections import OrderedDict
from typing import Any, cast

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QFrame,
    QCheckBox,
    QComboBox,
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


def build_pagination_filter_bar(
    window: Any,
    tab_layout: Any,
    *,
    column_selector_cls: Any,
    paginator_cls: Any,
) -> dict[str, Any]:
    column_selector = column_selector_cls(
        window.display_map,
        window.visible_columns,
        default_columns=window.default_columns,
        available_columns=window._get_canonical_available_columns(),
        info_font=window._info_font,
    )
    column_selector.columns_changed.connect(window.on_columns_changed)

    quick_setor_executor_label = QLabel("Setor Executor:")
    quick_setor_executor_combo = QComboBox()
    quick_setor_executor_combo.setToolTip(
        "Filtro rapido de Setor Executor (aplica junto com os demais filtros)."
    )
    _configure_quick_setor_combo(window, quick_setor_executor_combo)
    selected_setor = str(
        OrderedDict(window._active_column_filters or {}).get("setor_executor", "")
    ).strip()
    window._populate_quick_setor_executor_combo(
        quick_setor_executor_combo,
        selected_value=selected_setor,
    )
    quick_setor_executor_combo.currentIndexChanged.connect(
        lambda _idx, combo=quick_setor_executor_combo: (
            window._on_quick_setor_executor_changed(combo)
        )
    )

    pagination_filters_layout = QHBoxLayout()
    pagination_filters_layout.setContentsMargins(0, 0, 0, 0)

    paginator = paginator_cls(window.df_para_tabela)
    paginator.page_changed.connect(window.display_current_page)
    pagination_filters_layout.addWidget(paginator)
    pagination_filters_layout.addSpacing(8)
    pagination_filters_layout.addWidget(column_selector)

    profile_selector = None
    pagination_filters_layout.addSpacing(12)

    persistent_filters_layout = QHBoxLayout()
    persistent_filters_layout.setContentsMargins(0, 0, 0, 0)

    exclude_ste_checkbox = _build_exclude_ste_checkbox(window)
    persistent_filters_layout.addWidget(cast(Any, exclude_ste_checkbox))

    pagination_filters_layout.addLayout(cast(Any, persistent_filters_layout))
    pagination_filters_layout.addStretch()
    pagination_filters_layout.addWidget(cast(Any, quick_setor_executor_label))
    pagination_filters_layout.addSpacing(8)
    pagination_filters_layout.addWidget(cast(Any, quick_setor_executor_combo))

    col_filter_indicator = _build_column_filter_indicator(window)

    tab_layout.addLayout(cast(Any, pagination_filters_layout))

    return {
        "column_selector": column_selector,
        "quick_setor_executor_label": quick_setor_executor_label,
        "quick_setor_executor_combo": quick_setor_executor_combo,
        "paginator": paginator,
        "profile_selector": profile_selector,
        "persistent_filters_layout": persistent_filters_layout,
        "exclude_ste_checkbox": exclude_ste_checkbox,
        "col_filter_indicator": col_filter_indicator,
    }


def _configure_quick_setor_combo(window: Any, combo: QComboBox) -> None:
    try:
        combo.setMinimumWidth(138)
        combo.setMaximumWidth(188)
        combo.setMinimumContentsLength(9)
        combo.setMaxVisibleItems(14)
        _set_fixed_height(window, combo, 26, "combo rapido de setor executor")
        adjust_policy = getattr(
            QComboBox.SizeAdjustPolicy,
            "AdjustToMinimumContentsLengthWithIcon",
            None,
        )
        if adjust_policy is None:
            adjust_policy = getattr(QComboBox.SizeAdjustPolicy, "AdjustToContents", None)
        if adjust_policy is not None:
            combo.setSizeAdjustPolicy(cast(Any, adjust_policy))
        combo.setStyleSheet("QComboBox { combobox-popup: 0; }")
        combo_view = combo.view()
        if combo_view is not None:
            scroll_policy = getattr(
                getattr(Qt, "ScrollBarPolicy", None), "ScrollBarAsNeeded", None
            )
            if scroll_policy is not None:
                combo_view.setVerticalScrollBarPolicy(cast(Any, scroll_policy))
    except Exception as exc:
        logger.debug("Falha ao configurar combo rapido de setor executor: %s", exc)


def _build_exclude_ste_checkbox(window: Any) -> QCheckBox:
    checkbox = QCheckBox("Nao esta em SCA/SES/STE")
    checkbox.setToolTip("Oculta SSAs com situacao SCA, SES ou STE")
    try:
        checkbox.setChecked(False)
        checkbox.setVisible(False)
        checkbox.toggled.connect(window._on_exclude_ste_sca_toggled)
    except Exception as exc:
        logger.warning("Falha ao configurar checkbox excluir STE/SCA: %s", exc)
    return checkbox


def _build_column_filter_indicator(window: Any) -> QLabel:
    indicator = QLabel("")
    try:
        if window._info_font is not None:
            indicator.setFont(cast(Any, QFont(window._info_font)))
    except Exception as exc:
        logger.debug("Falha ao aplicar fonte no indicador de filtro por coluna: %s", exc)
    indicator.setToolTip(
        "Busca rapida: virgulas separam termos cumulativos (logica E). "
        "Filtros por coluna: virgulas representam alternativas dentro da mesma coluna. "
        "Entre filtros diferentes, as restricoes continuam cumulativas."
    )
    try:
        indicator.setVisible(False)
    except Exception as exc:
        logger.debug("Falha ao ocultar indicador de filtro por coluna: %s", exc)
    return indicator
