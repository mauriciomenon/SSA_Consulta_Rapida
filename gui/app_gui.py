# gui/app_gui.py
import sys
import pandas as pd
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QLineEdit, QTableView, QLabel, 
                             QPushButton, QStatusBar, QHeaderView)
from PyQt6.QtGui import QStandardItemModel, QStandardItem
from PyQt6.QtCore import Qt

from utils.pagination import Paginator
from core.app_logic import filter_dataframe

class PandasModel(QStandardItemModel):
    def __init__(self, df=pd.DataFrame()):
        super().__init__()
        self.set_dataframe(df)

    def set_dataframe(self, df):
        self.beginResetModel()
        self.clear()
        if not df.empty:
            self.setHorizontalHeaderLabels(df.columns)
            for _, row in df.iterrows():
                items = [QStandardItem(str(val)) for val in row.values]
                self.appendRow(items)
        self.endResetModel()

class AppGuiWindow(QMainWindow):
    def __init__(self, initial_df: pd.DataFrame, display_map: dict):
        super().__init__()
        self.df_completo = initial_df
        self.display_map = display_map
        
        df_display = self.df_completo.rename(columns=self.display_map)
        self.paginator = Paginator(df_display, page_size=50)
        
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("SSA Consulta Rápida")
        self.setGeometry(100, 100, 1200, 700)
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QVBoxLayout(main_widget)

        self.filter_input = QLineEdit()
        self.filter_input.setPlaceholderText("Filtrar por (termos separados por vírgula)...")
        self.filter_input.textChanged.connect(self.apply_filter)
        layout.addWidget(self.filter_input)

        self.table_view = QTableView()
        self.table_view.setSortingEnabled(True)
        self.table_view.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table_model = PandasModel()
        self.table_view.setModel(self.table_model)
        layout.addWidget(self.table_view)

        paginator_layout = QHBoxLayout()
        self.prev_button = QPushButton("Anterior")
        self.prev_button.clicked.connect(self.prev_page)
        self.page_info_label = QLabel()
        self.next_button = QPushButton("Próximo")
        self.next_button.clicked.connect(self.next_page)
        
        paginator_layout.addWidget(self.prev_button)
        paginator_layout.addStretch()
        paginator_layout.addWidget(self.page_info_label)
        paginator_layout.addStretch()
        paginator_layout.addWidget(self.next_button)
        layout.addLayout(paginator_layout)

        self.setStatusBar(QStatusBar(self))
        self.apply_filter()

    def apply_filter(self):
        filter_text = self.filter_input.text()
        # Filtra o DataFrame original (com nomes internos)
        filtered_df = filter_dataframe(self.df_completo, filter_text.split(','))
        # Renomeia as colunas para exibição antes de passar para o paginador
        filtered_df_display = filtered_df.rename(columns=self.display_map)
        
        self.paginator.set_data(filtered_df_display)
        self.update_view()

    def update_view(self):
        page_df = self.paginator.get_current_page_data()
        self.table_model.set_dataframe(page_df)
        self.statusBar().showMessage(f"Exibindo {len(page_df)} de {self.paginator.total_items} registros.")
        self.page_info_label.setText(f"Página {self.paginator.current_page} de {self.paginator.total_pages}")
        self.prev_button.setEnabled(self.paginator.current_page > 1)
        self.next_button.setEnabled(self.paginator.current_page < self.paginator.total_pages)

    def prev_page(self):
        if self.paginator.prev_page(): self.update_view()

    def next_page(self):
        if self.paginator.next_page(): self.update_view()