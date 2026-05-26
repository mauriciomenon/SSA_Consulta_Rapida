# gui/widgets/data_paginator.py
# Widget for data pagination controls

import pandas as pd
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QSpinBox, QWidget

PAGE_SIZE_MIN = 10
PAGE_SIZE_MAX = 500
DEFAULT_PAGE_SIZE = 50


class DataPaginator(QWidget):
    """Widget para paginacao de dados."""

    page_changed = pyqtSignal(int)  # Emite o numero da nova pagina (1-based)

    def __init__(self, df, page_size=50, *, show_page_size_controls=True):
        super().__init__()
        self.df = df
        self.show_page_size_controls = bool(show_page_size_controls)
        try:
            page_size_value = int(page_size)
        except (TypeError, ValueError):
            page_size_value = DEFAULT_PAGE_SIZE
        self.page_size = min(max(page_size_value, PAGE_SIZE_MIN), PAGE_SIZE_MAX)
        self.current_page = 1
        self.total_pages = 1
        self.init_ui()
        self.update_pagination_info()

    def init_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        self.prev_button = QPushButton("←")
        self.prev_button.setToolTip("Pagina anterior")
        self.prev_button.clicked.connect(self.prev_page)
        self.prev_button.setEnabled(False)
        self.prev_button.setFixedWidth(22)
        self.prev_button.setFixedHeight(22)

        self.page_info_label = QLabel("Pagina 1 de 1")
        self.page_info_label.setAlignment(
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
        )

        self.next_button = QPushButton("→")
        self.next_button.setToolTip("Proxima pagina")
        self.next_button.clicked.connect(self.next_page)
        self.next_button.setEnabled(False)
        self.next_button.setFixedWidth(22)
        self.next_button.setFixedHeight(22)

        self.page_size_spinbox = QSpinBox()
        self.page_size_spinbox.setRange(PAGE_SIZE_MIN, PAGE_SIZE_MAX)
        self.page_size_spinbox.setSingleStep(10)
        self.page_size_spinbox.setValue(self.page_size)
        self.page_size_spinbox.valueChanged.connect(self.change_page_size)
        self.page_size_spinbox.setFixedHeight(22)
        self.page_size_label = QLabel("Linhas por Pagina:")

        layout.addWidget(self.prev_button)
        layout.addWidget(self.page_info_label)
        layout.addWidget(self.next_button)
        layout.addStretch()
        if self.show_page_size_controls:
            page_size_layout = QHBoxLayout()
            page_size_layout.addWidget(self.page_size_label)
            page_size_layout.addWidget(self.page_size_spinbox)
            layout.addLayout(page_size_layout)

    def set_dataframe(self, df):
        self.df = df
        self.current_page = 1
        self.update_pagination_info()
        self.page_changed.emit(self.current_page)

    def update_pagination_info(self):
        # Calcula total de paginas com guard rails (df pode estar vazio ou ainda nao definido)
        if getattr(self, "df", None) is not None and not self.df.empty:
            self.total_pages = (len(self.df) + self.page_size - 1) // self.page_size
        else:
            self.total_pages = 1
        if self.current_page > self.total_pages:
            self.current_page = self.total_pages
        elif self.current_page < 1:
            self.current_page = 1
        # Pode ser chamado antes do init_ui terminar em alguns cenarios; proteja acesso
        if hasattr(self, "page_info_label"):
            self.page_info_label.setText(
                f"Pagina {self.current_page} de {self.total_pages}"
            )
        if hasattr(self, "prev_button") and hasattr(self, "next_button"):
            self.update_buttons()

    def update_buttons(self):
        self.prev_button.setEnabled(self.current_page > 1)
        self.next_button.setEnabled(self.current_page < self.total_pages)

    def next_page(self):
        if self.current_page < self.total_pages:
            self.current_page += 1
            self.update_pagination_info()
            self.page_changed.emit(self.current_page)

    def prev_page(self):
        if self.current_page > 1:
            self.current_page -= 1
            self.update_pagination_info()
            self.page_changed.emit(self.current_page)

    def change_page_size(self, new_size):
        try:
            page_size_value = int(new_size)
        except (TypeError, ValueError):
            return
        self.page_size = min(max(page_size_value, PAGE_SIZE_MIN), PAGE_SIZE_MAX)
        if (
            hasattr(self, "page_size_spinbox")
            and self.page_size_spinbox.value() != self.page_size
        ):
            self.page_size_spinbox.blockSignals(True)
            self.page_size_spinbox.setValue(self.page_size)
            self.page_size_spinbox.blockSignals(False)
        # Reset para a pagina 1 ao mudar o tamanho
        self.current_page = 1
        self.update_pagination_info()
        # Notifica que a pagina 1 (com novo tamanho) deve ser carregada
        self.page_changed.emit(self.current_page)

    def get_current_slice(self):
        """Retorna o slice do DataFrame para a pagina atual."""
        if self.df is None:
            return pd.DataFrame()
        if self.df.empty:
            return self.df.iloc[0:0]
        start_idx = (self.current_page - 1) * self.page_size
        end_idx = start_idx + self.page_size
        return self.df.iloc[start_idx:end_idx]
