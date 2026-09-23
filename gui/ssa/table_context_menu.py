"""Context menu actions for the main SSA table."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Callable

from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import QMenu

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class TableContextMenuCallbacks:
    copy_cell_value: Callable[[str], Any]
    copy_row_data: Callable[[int], Any]
    export_current_list_txt: Callable[[], Any]
    get_series_from_row: Callable[[int], Any]
    open_details_dialog: Callable[[str, Any], Any]
    jump_to_ssa: Callable[[str], Any]
    filter_by_derivadas: Callable[[str], Any]
    clear_derivadas_filter: Callable[[], Any]
    remove_column_by_index: Callable[[int], Any]
    auto_fit_column: Callable[[int], Any]
    last_derivada_origem: Callable[[], Any]


def show_table_context_menu(
    parent: Any,
    table_widget: Any,
    position: Any,
    callbacks: TableContextMenuCallbacks,
    *,
    action_cls: Any = QAction,
    menu_cls: Any = QMenu,
) -> None:
    if table_widget is None:
        return

    try:
        row = int(table_widget.rowAt(position.y()))
        column = int(table_widget.columnAt(position.x()))
    except (AttributeError, RuntimeError, TypeError, ValueError) as exc:
        logger.warning("Falha no hit-test do menu de contexto da tabela: %s", exc)
        return
    if row < 0 and column <= 0:
        return

    cell_text = None
    row_series = None
    if row >= 0:
        if column >= 0:
            try:
                current_item = table_widget.item(row, column)
                if current_item is not None:
                    cell_text = str(current_item.text())
            except (AttributeError, RuntimeError, TypeError, ValueError) as exc:
                logger.warning(
                    "Falha ao obter celula do menu de contexto: row=%s column=%s error=%s",
                    row,
                    column,
                    exc,
                )
        row_series = _get_context_row_series(callbacks, row)

    menu = menu_cls(parent)
    if row >= 0:
        if cell_text is not None:
            copy_cell_action = action_cls("Copiar Valor da Celula", parent)
            copy_cell_action.triggered.connect(
                lambda _checked=False, value=cell_text: callbacks.copy_cell_value(value)
            )
            menu.addAction(copy_cell_action)

        copy_row_action = action_cls("Copiar Linha Completa", parent)
        copy_row_action.triggered.connect(
            lambda _checked=False, row_index=row: callbacks.copy_row_data(row_index)
        )
        menu.addAction(copy_row_action)

        export_action = action_cls("Exportar lista (txt)", parent)
        export_action.triggered.connect(callbacks.export_current_list_txt)
        menu.addAction(export_action)
        menu.addSeparator()

        if row_series is not None:
            _add_details_action(
                parent, menu, row_series, callbacks, action_cls=action_cls
            )
            _add_derivadas_actions(
                parent, menu, row_series, callbacks, action_cls=action_cls
            )
    if column > 0:
        _add_column_actions(
            parent, table_widget, menu, column, callbacks, action_cls=action_cls
        )

    try:
        menu.exec(table_widget.viewport().mapToGlobal(position))
    except (AttributeError, RuntimeError, TypeError) as exc:
        logger.warning("Falha ao exibir menu de contexto da tabela: %s", exc)


def _get_context_row_series(
    callbacks: TableContextMenuCallbacks, row: int
) -> Any:
    try:
        return callbacks.get_series_from_row(row)
    except (
        AttributeError,
        IndexError,
        KeyError,
        RuntimeError,
        TypeError,
        ValueError,
    ) as exc:
        logger.warning(
            "Falha ao obter dados da linha no menu de contexto: row=%s error=%s",
            row,
            exc,
        )
        return None


def _add_details_action(
    parent: Any,
    menu: QMenu,
    row_series: Any,
    callbacks: TableContextMenuCallbacks,
    *,
    action_cls: Any,
) -> None:
    numero_ssa = _context_text_value(row_series, "numero_ssa")
    if not numero_ssa:
        return
    details_action = action_cls("Abrir detalhes da SSA", parent)
    details_action.triggered.connect(
        lambda: callbacks.open_details_dialog(numero_ssa, row_series)
    )
    menu.addAction(details_action)


def _add_derivadas_actions(
    parent: Any,
    menu: QMenu,
    row_series: Any,
    callbacks: TableContextMenuCallbacks,
    *,
    action_cls: Any,
) -> None:
    numero_ssa = _context_text_value(row_series, "numero_ssa")
    derivada_de = _context_text_value(row_series, "derivada_de")
    if derivada_de:
        origem_action = action_cls("Ir para SSA origem", parent)
        origem_action.triggered.connect(lambda: callbacks.jump_to_ssa(derivada_de))
        menu.addAction(origem_action)
    if numero_ssa:
        derivadas_action = action_cls("Mostrar derivadas", parent)
        derivadas_action.triggered.connect(
            lambda: callbacks.filter_by_derivadas(numero_ssa)
        )
        menu.addAction(derivadas_action)
    if callbacks.last_derivada_origem():
        voltar_action = action_cls("Limpar filtro de derivadas", parent)
        voltar_action.triggered.connect(callbacks.clear_derivadas_filter)
        menu.addAction(voltar_action)
    menu.addSeparator()


def _context_text_value(row_series: Any, key: str) -> str:
    raw_value = row_series.get(key, None)
    if raw_value is None:
        return ""
    try:
        if raw_value != raw_value:
            return ""
    except (TypeError, ValueError) as exc:
        logger.warning(
            "Falha ao verificar valor NaN no menu de contexto: key=%s tipo=%s",
            key,
            type(exc).__name__,
        )
        return ""
    value = str(raw_value).strip()
    if value.casefold() in {"nan", "none", "<na>"}:
        return ""
    return value


def _add_column_actions(
    parent: Any,
    table_widget: Any,
    menu: QMenu,
    column: int,
    callbacks: TableContextMenuCallbacks,
    *,
    action_cls: Any,
) -> None:
    # Column 0 is the synthetic row-number/SAM link column, not removable data.
    if column <= 0:
        return
    try:
        header_item = table_widget.horizontalHeaderItem(column)
        column_name = header_item.text() if header_item is not None else str(column)
    except (AttributeError, RuntimeError, TypeError) as exc:
        logger.warning(
            "Falha ao obter header da coluna no menu de contexto: "
            "column=%s error=%s",
            column,
            exc,
        )
        column_name = str(column)

    remove_column_action = action_cls(f"Ocultar Coluna '{column_name}'", parent)
    remove_column_action.triggered.connect(
        lambda _checked=False: callbacks.remove_column_by_index(column)
    )
    menu.addAction(remove_column_action)

    auto_fit_action = action_cls(f"Ajustar Largura '{column_name}'", parent)
    auto_fit_action.triggered.connect(
        lambda _checked=False: callbacks.auto_fit_column(column)
    )
    menu.addAction(auto_fit_action)
