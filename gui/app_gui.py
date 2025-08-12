# gui/app_gui.py
import sys
import os
import pandas as pd
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QLineEdit, QTableView, QLabel, 
                             QPushButton, QStatusBar, QHeaderView, QComboBox,
                             QFormLayout, QGroupBox, QDateEdit)
from PyQt6.QtGui import QStandardItemModel, QStandardItem
from PyQt6.QtCore import Qt, QDate

# Garante que o diretório raiz do projeto esteja no sys.path
try:
    CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
    PROJECT_ROOT = os.path.dirname(CURRENT_DIR)
    if PROJECT_ROOT not in sys.path:
        sys.path.insert(0, PROJECT_ROOT)
except Exception:
    pass

from utils.pagination import Paginator
from core.app_logic import filter_dataframe, advanced_filter_dataframe

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
        self.setup_filters()

    def init_ui(self):
        self.setWindowTitle("SSA Consulta Rápida")
        self.setGeometry(100, 100, 1200, 700)
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QVBoxLayout(main_widget)

        # Create filter group
        filter_group = QGroupBox("Filtros")
        filter_layout = QVBoxLayout(filter_group)
        
        # Text filter
        self.filter_input = QLineEdit()
        self.filter_input.setPlaceholderText("Filtrar por (termos separados por vírgula)...")
        self.filter_input.textChanged.connect(self.apply_filter)
        filter_layout.addWidget(QLabel("Busca Geral:"))
        filter_layout.addWidget(self.filter_input)
        
        # Advanced filters layout
        advanced_filter_layout = QHBoxLayout()
        
        # Setor Executor filter
        self.executor_combo = QComboBox()
        self.executor_combo.setEditable(True)
        self.executor_combo.setPlaceholderText("Selecione ou digite o setor executor")
        self.executor_combo.currentTextChanged.connect(self.apply_filter)
        advanced_filter_layout.addWidget(QLabel("Executor:"))
        advanced_filter_layout.addWidget(self.executor_combo)
        
        # Situacao filter
        self.situacao_combo = QComboBox()
        self.situacao_combo.setEditable(True)
        self.situacao_combo.setPlaceholderText("Selecione ou digite a situação")
        self.situacao_combo.currentTextChanged.connect(self.apply_filter)
        advanced_filter_layout.addWidget(QLabel("Situação:"))
        advanced_filter_layout.addWidget(self.situacao_combo)
        
        filter_layout.addLayout(advanced_filter_layout)
        layout.addWidget(filter_group)

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

    def setup_filters(self):
        """Populate filter dropdowns with unique values"""
        if not self.df_completo.empty:
            # Populate executor combo
            if 'setor_executor' in self.df_completo.columns:
                executores = self.df_completo['setor_executor'].dropna().unique()
                self.executor_combo.addItem("")  # Empty option for no filter
                self.executor_combo.addItems(sorted([str(e) for e in executores if str(e).strip()]))
            
            # Populate situacao combo
            if 'situacao' in self.df_completo.columns:
                situacoes = self.df_completo['situacao'].dropna().unique()
                self.situacao_combo.addItem("")  # Empty option for no filter
                self.situacao_combo.addItems(sorted([str(s) for s in situacoes if str(s).strip()]))

    def apply_filter(self):
        # Prepare filters dictionary
        filters = {}
        
        # Text filter
        filter_text = self.filter_input.text()
        if filter_text:
            filters['search_terms'] = filter_text.split(',')
        
        # Executor filter
        executor_filter = self.executor_combo.currentText()
        if executor_filter:
            filters['setor_executor'] = executor_filter
        
        # Situacao filter
        situacao_filter = self.situacao_combo.currentText()
        if situacao_filter:
            filters['situacao'] = situacao_filter
        
        # Apply advanced filtering
        filtered_df = advanced_filter_dataframe(self.df_completo, filters)
        
        # Rename columns for display
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