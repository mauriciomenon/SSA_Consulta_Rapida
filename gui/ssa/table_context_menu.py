"""Context menu actions for the main SSA table."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import QMenu


@dataclass(frozen=True)
class TableContextMenuCallbacks:
    copy_cell_value: Callable[[], Any]
    copy_row_data: Callable[[], Any]
    export_current_list_txt: Callable[[], Any]
    get_series_from_row: Callable[[int], Any]
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
    if table_widget is None or not table_widget.itemAt(position):
        return

    menu = menu_cls(parent)
    copy_cell_action = action_cls("Copiar Valor da Celula", parent)
    copy_cell_action.triggered.connect(callbacks.copy_cell_value)
    menu.addAction(copy_cell_action)

    copy_row_action = action_cls("Copiar Linha Completa", parent)
    copy_row_action.triggered.connect(callbacks.copy_row_data)
    menu.addAction(copy_row_action)

    export_action = action_cls("Exportar lista (txt)", parent)
    export_action.triggered.connect(callbacks.export_current_list_txt)
    menu.addAction(export_action)
    menu.addSeparator()

    current_item = table_widget.itemAt(position)
    row_series = _get_context_row_series(callbacks, current_item)
    if row_series is not None:
        _add_derivadas_actions(
            parent, menu, row_series, callbacks, action_cls=action_cls
        )
    if current_item is not None:
        _add_column_actions(
            parent, table_widget, menu, current_item, callbacks, action_cls=action_cls
        )

    menu.exec(table_widget.mapToGlobal(position))


def _get_context_row_series(
    callbacks: TableContextMenuCallbacks, current_item: Any
) -> Any:
    if current_item is None:
        return None
    try:
        return callbacks.get_series_from_row(current_item.row())
    except Exception:
        return None


def _add_derivadas_actions(
    parent: Any,
    menu: QMenu,
    row_series: Any,
    callbacks: TableContextMenuCallbacks,
    *,
    action_cls: Any,
) -> None:
    numero_ssa = str(row_series.get("numero_ssa", "")).strip()
    derivada_de = str(row_series.get("derivada_de", "")).strip()
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


def _add_column_actions(
    parent: Any,
    table_widget: Any,
    menu: QMenu,
    current_item: Any,
    callbacks: TableContextMenuCallbacks,
    *,
    action_cls: Any,
) -> None:
    column = current_item.column()
    # Column 0 is the synthetic row-number/SAM link column, not removable data.
    if column <= 0:
        return
    header_item = table_widget.horizontalHeaderItem(column)
    column_name = header_item.text() if header_item is not None else str(column)

    remove_column_action = action_cls(f"Remover Coluna '{column_name}'", parent)
    remove_column_action.triggered.connect(
        lambda: callbacks.remove_column_by_index(column)
    )
    menu.addAction(remove_column_action)

    auto_fit_action = action_cls(f"Ajustar Largura '{column_name}'", parent)
    auto_fit_action.triggered.connect(lambda: callbacks.auto_fit_column(column))
    menu.addAction(auto_fit_action)
