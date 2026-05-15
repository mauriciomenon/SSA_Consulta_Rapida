# gui/widgets/column_selector.py
# Widget for column selection with manager dialog

import logging

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import QDialog, QHBoxLayout, QPushButton, QWidget

from gui.widgets.column_manager_dialog import ColumnManagerDialog


class ColumnSelector(QWidget):
    """Widget compacto que abre o gerenciador de colunas."""

    columns_changed = pyqtSignal(list)

    def __init__(
        self,
        display_map,
        initial_columns,
        default_columns=None,
        available_columns=None,
        info_font=None,
    ):
        super().__init__()
        self.display_map = display_map or {}
        self.default_columns = list(default_columns or initial_columns)
        self.selected_internal_columns = list(initial_columns)
        self.available_columns = list(available_columns or self.display_map.keys())
        self._missing_alias_logged = set()
        for col in self.selected_internal_columns:
            if col not in self.available_columns:
                self.available_columns.append(col)
        self._info_font = info_font
        self.init_ui()
        if self._info_font is not None:
            self.set_summary_font(self._info_font)
        self._update_summary()

    def init_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        self.manage_button = QPushButton()
        self.manage_button.setToolTip(
            "Configurar colunas rapidas (marcar, ordenar e restaurar padrao)"
        )
        self.manage_button.clicked.connect(self.open_dialog)
        layout.addWidget(self.manage_button)
        layout.addStretch()

    def open_dialog(self):
        dialog = ColumnManagerDialog(
            self.display_map,
            self.selected_internal_columns,
            default_columns=self.default_columns,
            available_columns=self.available_columns,
            parent=self,
        )
        try:
            result = dialog.exec()
        except Exception:
            result = dialog.accept() or QDialog.DialogCode.Accepted
        if result == QDialog.DialogCode.Accepted:
            new_columns = dialog.get_selected_columns()
            if not new_columns:
                new_columns = list(self.default_columns)
            self.selected_internal_columns = new_columns
            for col in self.selected_internal_columns:
                if col not in self.available_columns:
                    self.available_columns.append(col)
            self._update_summary()
            self.columns_changed.emit(self.selected_internal_columns)

    def _update_summary(self):
        translated = []
        for col in self.selected_internal_columns:
            label = self.display_map.get(col, col)
            if label == col:
                if col not in self._missing_alias_logged:
                    self._missing_alias_logged.add(col)
                    logging.getLogger(__name__).debug(
                        "Coluna sem alias canonico no resumo de colunas: %s", col
                    )
            translated.append(label)
        total = len(translated)
        button_text = f"Colunas Visiveis: {total}"
        tooltip = ", ".join(translated) if translated else "Nenhuma coluna selecionada"
        self.manage_button.setText(button_text)
        self.manage_button.setToolTip(
            "Configurar colunas rapidas (marcar, ordenar e restaurar padrao)\n"
            f"Ativas: {tooltip}"
        )
        try:
            fm = self.manage_button.fontMetrics()
            text_width = fm.horizontalAdvance(button_text)
            self.manage_button.setMinimumWidth(text_width + 36)
        except Exception as exc:
            logging.getLogger(__name__).debug(
                "Falha ao ajustar largura do resumo de colunas: %s", exc
            )

    def get_selected_columns(self):
        return self.selected_internal_columns

    def set_selected_columns(self, columns):
        self.selected_internal_columns = list(columns)
        for col in self.selected_internal_columns:
            if col not in self.available_columns:
                self.available_columns.append(col)
        self._update_summary()

    def set_summary_font(self, font):
        """Aplica fonte compartilhada para o resumo (harmoniza com outros indicadores)."""
        if font is None:
            return
        try:
            self.manage_button.setFont(QFont(font))
        except Exception as e1:
            try:
                self.manage_button.setFont(font)
            except Exception as e2:
                logging.getLogger(__name__).debug(
                    "Falha ao aplicar fonte do resumo: %s | fallback=%s", e1, e2
                )
