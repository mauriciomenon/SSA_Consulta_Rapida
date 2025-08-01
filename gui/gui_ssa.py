# gui/gui_ssa.py
import sys
import os

# --- INÍCIO DA CORREÇÃO DE IMPORT ---
# Adiciona o diretório raiz do projeto ao sys.path.
# Isso garante que o script, mesmo dentro da pasta 'gui',
# consiga encontrar outros módulos como 'utils'.
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(project_root)
# --- FIM DA CORREÇÃO DE IMPORT ---

import pandas as pd
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QLineEdit, QTableView, QLabel,
                             QPushButton, QStatusBar, QHeaderView)
from PyQt6.QtGui import QStandardItemModel, QStandardItem
from PyQt6.QtCore import Qt

# Agora este import vai funcionar
from utils.pagination import Paginator

# --- Funções de Lógica (Mock para teste, substitua pelas suas reais de core/app_logic) ---
def load_database():
    """Função mock para carregar dados. Substitua pela sua implementação real."""
    data = {'setor_executor': ['MEL4']*5, 'situacao': ['SPG']*5, 'descricao_ssa': ['Teste de descrição SSA']*5}
    return pd.DataFrame(data)

def filter_dataframe(df, text):
    """Função mock para filtrar dados. Substitua pela sua implementação real."""
    if not text:
        return df
    return df[df.apply(lambda row: text.lower() in ' '.join(row.astype(str)).lower(), axis=1)]
# --- Fim das Funções de Lógica Mock ---

class PandasModel(QStandardItemModel):
    def __init__(self, df=pd.DataFrame()):
        super().__init__()
        self.set_dataframe(df)

    def set_dataframe(self, df):
        self.clear()
        if df.empty:
            return
        self.setHorizontalHeaderLabels(df.columns)
        for i, row in df.iterrows():
            items = [QStandardItem(str(val)) for val in row.values]
            self.appendRow(items)

class SSAMainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.df_completo = load_database()
        self.paginator = Paginator(self.df_completo, page_size=25)
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("Consulta Rápida de SSAs (PyQt6)")
        self.setGeometry(100, 100, 1000, 600)

        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QVBoxLayout(main_widget)

        self.filter_input = QLineEdit()
        self.filter_input.setPlaceholderText("Digite para filtrar...")
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
        filtered_df = filter_dataframe(self.df_completo, filter_text)
        self.paginator.set_data(filtered_df)
        self.update_table_view()
        self.update_paginator_ui()

    def update_table_view(self):
        page_df = self.paginator.get_current_page_data()
        self.table_model.set_dataframe(page_df)
        self.statusBar().showMessage(f"Exibindo {len(page_df)} de {self.paginator.total_items} registros filtrados.")

    def update_paginator_ui(self):
        info_text = f"Página {self.paginator.current_page} de {self.paginator.total_pages}"
        self.page_info_label.setText(info_text)
        self.prev_button.setEnabled(self.paginator.current_page > 1)
        self.next_button.setEnabled(self.paginator.current_page < self.paginator.total_pages)

    def prev_page(self):
        if self.paginator.prev_page():
            self.update_table_view()
            self.update_paginator_ui()

    def next_page(self):
        if self.paginator.next_page():
            self.update_table_view()
            self.update_paginator_ui()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = SSAMainWindow()
    window.show()
    sys.exit(app.exec())