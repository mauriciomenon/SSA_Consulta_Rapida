# gui/app_gui.py
import sys
import os
import pandas as pd
import json
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QLineEdit, QTableView, QLabel, 
                             QPushButton, QStatusBar, QHeaderView, QComboBox,
                             QFormLayout, QGroupBox, QDateEdit, QCheckBox)
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
from interface.display import pretty_print_details
from interface.table_printer import format_cell_data
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
        # Verbose display map (from display_mappings.json) for details view
        self.display_map_verbose = display_map or {}

        # Load priorities and short labels from config
        self.short_labels = {}
        self.priority_order = []
        try:
            config_path = os.path.join(PROJECT_ROOT, 'config', 'column_priority.json')
            with open(config_path, 'r', encoding='utf-8') as f:
                cfg = json.load(f)
            self.short_labels = cfg.get('short_labels', {})
            self.priority_order = cfg.get('priority_order', [])
        except Exception:
            self.short_labels = {}
            self.priority_order = []

        # Prepare initial display DataFrame honoring priority and short labels
        df_display = self._prepare_display_df(self.df_completo)
        self.paginator = Paginator(df_display, page_size=50)
        # Keep a raw paginator aligned for details view
        self.paginator_raw = Paginator(self.df_completo.copy(), page_size=50)
        
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

        # Date range filter (optional)
        date_layout = QHBoxLayout()
        self.use_date_filter_cb = QCheckBox("Filtrar por data de cadastro")
        self.use_date_filter_cb.stateChanged.connect(self.apply_filter)
        self.data_inicio_edit = QDateEdit()
        self.data_inicio_edit.setDisplayFormat("dd/MM/yyyy")
        self.data_inicio_edit.setCalendarPopup(True)
        self.data_inicio_edit.setDate(QDate.currentDate().addMonths(-1))
        self.data_inicio_edit.dateChanged.connect(self.apply_filter)

        self.data_fim_edit = QDateEdit()
        self.data_fim_edit.setDisplayFormat("dd/MM/yyyy")
        self.data_fim_edit.setCalendarPopup(True)
        self.data_fim_edit.setDate(QDate.currentDate())
        self.data_fim_edit.dateChanged.connect(self.apply_filter)

        # Initially disabled until checkbox checked
        self.data_inicio_edit.setEnabled(False)
        self.data_fim_edit.setEnabled(False)

        def _toggle_date_edits(_state):
            enabled = self.use_date_filter_cb.isChecked()
            self.data_inicio_edit.setEnabled(enabled)
            self.data_fim_edit.setEnabled(enabled)

        self.use_date_filter_cb.stateChanged.connect(_toggle_date_edits)

        date_layout.addWidget(self.use_date_filter_cb)
        date_layout.addWidget(QLabel("Início:"))
        date_layout.addWidget(self.data_inicio_edit)
        date_layout.addWidget(QLabel("Fim:"))
        date_layout.addWidget(self.data_fim_edit)
        filter_layout.addLayout(date_layout)

        layout.addWidget(filter_group)

        # Table view and model
        self.table_view = QTableView()
        self.table_view.setSortingEnabled(True)
        self.table_view.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table_model = PandasModel()
        self.table_view.setModel(self.table_model)
        # Open details on double click
        self.table_view.doubleClicked.connect(self.open_details_for_selected)
        layout.addWidget(self.table_view)

        # Paginator controls
        paginator_layout = QHBoxLayout()
        self.prev_button = QPushButton("Anterior")
        self.prev_button.clicked.connect(self.prev_page)
        self.page_info_label = QLabel()
        # Details button
        self.details_button = QPushButton("Detalhes")
        self.details_button.clicked.connect(self.open_details_for_selected)
        self.next_button = QPushButton("Próximo")
        self.next_button.clicked.connect(self.next_page)

        paginator_layout.addWidget(self.prev_button)
        paginator_layout.addStretch()
        paginator_layout.addWidget(self.page_info_label)
        paginator_layout.addStretch()
        paginator_layout.addWidget(self.details_button)
        paginator_layout.addWidget(self.next_button)
        layout.addLayout(paginator_layout)

        self.setStatusBar(QStatusBar(self))
        self.update_view()

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

        # Date filters (if enabled)
        if hasattr(self, 'use_date_filter_cb') and self.use_date_filter_cb.isChecked():
            try:
                data_ini = self.data_inicio_edit.date().toPyDate()
                data_fim = self.data_fim_edit.date().toPyDate()
                if data_ini:
                    filters['data_inicio'] = data_ini
                if data_fim:
                    filters['data_fim'] = data_fim
            except Exception:
                pass

        # Apply advanced filtering
        filtered_df = advanced_filter_dataframe(self.df_completo, filters)

        # Update both paginators: raw and display
        self.paginator_raw.set_data(filtered_df)
        filtered_df_display = self._prepare_display_df(filtered_df)
        self.paginator.set_data(filtered_df_display)
        self.update_view()

    def update_view(self):
        page_df = self.paginator.get_current_page_data()
        self.table_model.set_dataframe(page_df)
        self.statusBar().showMessage(f"Exibindo {len(page_df)} de {self.paginator.total_items} registros.")
        self.page_info_label.setText(f"Página {self.paginator.current_page} de {self.paginator.total_pages}")
        self.prev_button.setEnabled(self.paginator.current_page > 1)
        self.next_button.setEnabled(self.paginator.current_page < self.paginator.total_pages)

    def _prepare_display_df(self, df: pd.DataFrame) -> pd.DataFrame:
        """Return a reordered and renamed DataFrame for display.
        - Reorders columns per priority_order (keeping only those present), then others.
        - Applies short labels for headers if available; else keeps original.
        - Applies shared cell formatting (SSA 9 dígitos, datas sem horário, semana sem .0, suprime NaN).
        """
        if df is None or df.empty:
            return df

        # Reorder columns: priority first, then the rest
        cols = list(df.columns)
        prio = [c for c in self.priority_order if c in cols]
        rest = [c for c in cols if c not in prio]
        ordered = prio + rest
        df2 = df[ordered].copy()

        # Apply shared formatting to all visible columns for consistent GUI/CLI behavior
        try:
            for col in df2.columns:
                df2[col] = df2[col].apply(lambda v, c=col: format_cell_data(v, c))
        except Exception:
            pass

        # Apply short labels for headers
        if self.short_labels:
            df2 = df2.rename(columns=self.short_labels)
        elif self.display_map_verbose:
            df2 = df2.rename(columns=self.display_map_verbose)

        return df2

    def open_details_for_selected(self):
        """Open a details dialog for the currently selected row."""
        try:
            selection = self.table_view.selectionModel().currentIndex()
            if not selection.isValid():
                return
            row_idx = selection.row()
            # Align with raw data page
            raw_page = self.paginator_raw.get_current_page_data()
            if row_idx < 0 or row_idx >= len(raw_page):
                return
            series = raw_page.iloc[row_idx]
            # Render details using verbose display map for readability
            # Capture stdout to a string to show in a dialog
            from io import StringIO
            import contextlib
            buf = StringIO()
            with contextlib.redirect_stdout(buf):
                pretty_print_details(series, self.display_map_verbose)
            details_text = buf.getvalue()

            # Show dialog
            from PyQt6.QtWidgets import QDialog, QVBoxLayout, QTextEdit, QPushButton
            dlg = QDialog(self)
            dlg.setWindowTitle("Detalhes da SSA")
            dlg.resize(800, 600)
            v = QVBoxLayout(dlg)
            text = QTextEdit()
            text.setReadOnly(True)
            text.setPlainText(details_text)
            v.addWidget(text)
            btn = QPushButton("Fechar")
            btn.clicked.connect(dlg.accept)
            v.addWidget(btn)
            dlg.exec()
        except Exception:
            pass

    def prev_page(self):
        if self.paginator.prev_page():
            self.paginator_raw.prev_page()
            self.update_view()

    def next_page(self):
        if self.paginator.next_page():
            self.paginator_raw.next_page()
            self.update_view()