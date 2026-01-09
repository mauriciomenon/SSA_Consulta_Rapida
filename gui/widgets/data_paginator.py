# gui/widgets/data_paginator.py
# Widget for data pagination controls

import pandas as pd
from PyQt6.QtWidgets import QWidget, QHBoxLayout, QPushButton, QLabel, QSpinBox
from PyQt6.QtCore import pyqtSignal


class DataPaginator(QWidget):
    """Widget para paginacao de dados."""
    page_changed = pyqtSignal(int)  # Emite o numero da nova pagina (1-based)

    def __init__(self, df, page_size=50):
        super().__init__()
        self.df = df
        self.page_size = page_size
        self.current_page = 1
        self.total_pages = 1
        self.init_ui()
        self.update_pagination_info()

    def init_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.prev_button = QPushButton("Pagina Anterior")
        self.prev_button.clicked.connect(self.prev_page)
        self.prev_button.setEnabled(False)

        self.page_info_label = QLabel("Pagina 1 de 1")

        self.next_button = QPushButton("Proxima Pagina")
        self.next_button.clicked.connect(self.next_page)
        self.next_button.setEnabled(False)

        # Controle de tamanho da pagina
        page_size_layout = QHBoxLayout()
        page_size_layout.addWidget(QLabel("Linhas por Pagina:"))
        self.page_size_spinbox = QSpinBox()
        self.page_size_spinbox.setRange(10, 500)
        self.page_size_spinbox.setSingleStep(10)
        self.page_size_spinbox.setValue(self.page_size)
        self.page_size_spinbox.valueChanged.connect(self.change_page_size)
        # UIREFACTOR 2026-01-09: Altura fixa para alinhar com botao Colunas visiveis
        self.page_size_spinbox.setFixedHeight(self.prev_button.sizeHint().height())
        page_size_layout.addWidget(self.page_size_spinbox)

        layout.addWidget(self.prev_button)
        layout.addWidget(self.page_info_label)
        layout.addWidget(self.next_button)
        layout.addStretch()
        layout.addLayout(page_size_layout)

    def set_dataframe(self, df):
        self.df = df
        self.current_page = 1
        self.update_pagination_info()
        self.update_buttons()

    def update_pagination_info(self):
        # Calcula total de paginas com guard rails (df pode estar vazio ou ainda nao definido)
        if getattr(self, 'df', None) is not None and not self.df.empty:
            self.total_pages = (len(self.df) + self.page_size - 1) // self.page_size
        else:
            self.total_pages = 1
        
        # Garante que a pagina atual esteja sempre dentro dos limites validos (clamping)
        if self.current_page > self.total_pages:
            self.current_page = self.total_pages
        elif self.current_page < 1:
            self.current_page = 1

        # Pode ser chamado antes do init_ui terminar em alguns cenarios; proteja acesso
        if hasattr(self, 'page_info_label'):
            self.page_info_label.setText(f"Pagina {self.current_page} de {self.total_pages}")

    def update_buttons(self):
        self.prev_button.setEnabled(self.current_page > 1)
        self.next_button.setEnabled(self.current_page < self.total_pages)

    def next_page(self):
        if self.current_page < self.total_pages:
            self.current_page += 1
            self.update_pagination_info()
            self.update_buttons()
            self.page_changed.emit(self.current_page)

    def prev_page(self):
        if self.current_page > 1:
            self.current_page -= 1
            self.update_pagination_info()
            self.update_buttons()
            self.page_changed.emit(self.current_page)

    def change_page_size(self, new_size):
        self.page_size = new_size
        # Reset para a pagina 1 ao mudar o tamanho
        self.current_page = 1
        self.update_pagination_info()
        self.update_buttons()
        # Notifica que a pagina 1 (com novo tamanho) deve ser carregada
        self.page_changed.emit(self.current_page)

    def get_current_slice(self):
        """Retorna o slice do DataFrame para a pagina atual."""
        if self.df is None or self.df.empty:
            return pd.DataFrame()
        start_idx = (self.current_page - 1) * self.page_size
        end_idx = start_idx + self.page_size
        return self.df.iloc[start_idx:end_idx]
