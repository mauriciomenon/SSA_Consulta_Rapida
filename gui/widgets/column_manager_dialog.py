# gui/widgets/column_manager_dialog.py
# Dialog for managing column visibility and order

import logging

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
)


class ColumnManagerDialog(QDialog):
    """Dialogo para marcar e reordenar colunas visiveis."""

    def __init__(
        self,
        display_map,
        selected_columns,
        default_columns=None,
        available_columns=None,
        parent=None,
    ):
        super().__init__(parent)
        self.setWindowTitle("Configurar colunas visiveis")
        self.resize(420, 500)
        self.display_map = display_map or {}
        self.default_columns = list(default_columns or [])
        all_from_map = list(self.display_map.keys())
        explicit_available = list(available_columns or [])
        self.available_columns = explicit_available or all_from_map
        self._missing_alias_logged = set()
        if not self.available_columns:
            self.available_columns = list(selected_columns)
        if explicit_available:
            self.available_columns = list(dict.fromkeys(self.available_columns))
        else:
            self.available_columns = list(
                dict.fromkeys(
                    self.available_columns
                    + [c for c in all_from_map if c not in self.available_columns]
                )
            )
        self._build_ui(selected_columns)

    def _build_ui(self, selected_columns):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        hint = QLabel(
            "Marque as colunas que deseja ver. Arraste as linhas marcadas para reordenar."
        )
        hint.setWordWrap(True)
        layout.addWidget(hint)

        search_row = QHBoxLayout()
        search_row.addWidget(QLabel("Buscar:"))
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Filtrar por nome da coluna")
        self.search_edit.textChanged.connect(self._apply_filter)
        search_row.addWidget(self.search_edit)
        layout.addLayout(search_row)

        self.list_widget = QListWidget()
        try:
            self.list_widget.setAlternatingRowColors(True)
            self.list_widget.setSelectionMode(
                QAbstractItemView.SelectionMode.ExtendedSelection
            )
            self.list_widget.setDragDropMode(
                QAbstractItemView.DragDropMode.InternalMove
            )
            self.list_widget.setDefaultDropAction(Qt.DropAction.MoveAction)
        except (AttributeError, RuntimeError, TypeError) as exc:
            logging.getLogger(__name__).debug(
                "Falha ao configurar QListWidget do gerenciador de colunas: %s", exc
            )
        layout.addWidget(self.list_widget, 1)

        self._populate_list(selected_columns)

        tools_row = QHBoxLayout()
        self.restore_btn = QPushButton("Restaurar padrao")
        self.restore_btn.clicked.connect(self.restore_defaults)
        tools_row.addWidget(self.restore_btn)

        self.select_all_btn = QPushButton("Selecionar tudo")
        self.select_all_btn.clicked.connect(self.select_all)
        tools_row.addWidget(self.select_all_btn)

        self.clear_all_btn = QPushButton("Limpar selecao")
        self.clear_all_btn.clicked.connect(self.clear_all)
        tools_row.addStretch()
        tools_row.addWidget(self.clear_all_btn)
        layout.addLayout(tools_row)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _ordered_columns(self, selected_columns):
        selection = [c for c in selected_columns if c in self.available_columns]
        if not selection and self.default_columns:
            selection = [c for c in self.default_columns if c in self.available_columns]
        remaining = [c for c in self.available_columns if c not in selection]
        return selection + remaining

    def _populate_list(self, selected_columns):
        self.list_widget.clear()
        for col in self._ordered_columns(selected_columns):
            display_name = self.display_map.get(col, col)
            if display_name == col:
                if col not in self._missing_alias_logged:
                    self._missing_alias_logged.add(col)
                    logging.getLogger(__name__).debug(
                        "Coluna sem alias canonico no gerenciador de colunas: %s", col
                    )
            item = QListWidgetItem(display_name)
            try:
                flags = (
                    item.flags()
                    | Qt.ItemFlag.ItemIsUserCheckable
                    | Qt.ItemFlag.ItemIsDragEnabled
                    | Qt.ItemFlag.ItemIsSelectable
                )
                item.setFlags(flags)
            except Exception as e:
                # Avoid silent failure (B110): log at debug, continue rendering list
                logging.getLogger(__name__).debug(
                    "Nao foi possivel ajustar flags do item '%s': %s", display_name, e
                )
            item.setData(Qt.ItemDataRole.UserRole, col)
            if selected_columns:
                state = (
                    Qt.CheckState.Checked
                    if col in selected_columns
                    else Qt.CheckState.Unchecked
                )
            else:
                state = (
                    Qt.CheckState.Checked
                    if col in self.default_columns
                    else Qt.CheckState.Unchecked
                )
            item.setCheckState(state)
            self.list_widget.addItem(item)

    def _apply_filter(self, text):
        text = (text or "").strip().casefold()
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            if not item:
                continue
            display = item.text().casefold()
            internal = str(item.data(Qt.ItemDataRole.UserRole) or "").casefold()
            visible = not text or text in display or text in internal
            try:
                item.setHidden(not visible)
            except Exception as e:
                logging.getLogger(__name__).debug(
                    "Falha ao ocultar/mostrar item '%s': %s", display, e
                )

    def restore_defaults(self):
        self._populate_list(self.default_columns)

    def select_all(self):
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            if item:
                item.setCheckState(Qt.CheckState.Checked)

    def clear_all(self):
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            if item:
                item.setCheckState(Qt.CheckState.Unchecked)

    def get_selected_columns(self):
        selected = []
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            if not item:
                continue
            if item.checkState() == Qt.CheckState.Checked:
                col = item.data(Qt.ItemDataRole.UserRole)
                if col and col not in selected:
                    selected.append(col)
        return selected
