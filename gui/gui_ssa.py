# gui_ssa.py 20250725 173000 (PoC - GUI PyQt6 para SSA_Consulta_Rapida)
"""
Prova de Conceito Refinada de uma Interface Gráfica (GUI) para o projeto SSA_Consulta_Rapida usando PyQt6.

Refinamentos em relação à PoC básica:
1. Seleção de colunas com base em display_mappings.json e prioridade.
2. Paginação simples para lidar com grandes conjuntos de dados.
3. Uso de nomes de exibição para colunas.
4. Feedback mais detalhado ao usuário.
5. Estrutura mais preparada para expansão (ordenação, exportação).

Para executar: python gui_ssa.py
(Requer que o projeto ja tenha sido executado uma vez para criar o banco de dados ssas.db)
"""

import sys
import os
import pandas as pd
import json

# --- Configuração do Path do Projeto ---
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

# --- Importações do Projeto ---
from core.app_logic import filter_dataframe
from armazenamento.database import query_db
from core.config_manager import load_settings # Para carregar display_mappings

# --- Importações do PyQt6 ---
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QPushButton, QLineEdit, QLabel, QTableWidget, QTableWidgetItem,
    QHeaderView, QMessageBox, QProgressBar, QComboBox, QSpinBox, QAbstractItemView,
    QMenu, QGroupBox, QTextEdit
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QItemSelectionModel
from PyQt6.QtGui import QAction

# --- Constantes ---
DB_PATH = os.path.join(project_root, 'data', 'ssas.db')
TABLE_NAME = 'ssas'
CONFIG_DIR = os.path.join(project_root, 'config')
DISPLAY_MAPPINGS_FILE = os.path.join(CONFIG_DIR, 'display_mappings.json')

# --- Funções Auxiliares ---

def load_display_mappings():
    """Carrega o mapeamento de nomes internos para nomes de exibição."""
    try:
        with open(DISPLAY_MAPPINGS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"Aviso: Erro ao carregar display_mappings.json: {e}. Usando nomes internos.")
        return {}

# --- Worker Threads ---

class DataLoaderWorker(QThread):
    """Thread para carregar dados do banco."""
    data_loaded = pyqtSignal(pd.DataFrame)
    error_occurred = pyqtSignal(str)

    def __init__(self, db_path, table_name):
        super().__init__()
        self.db_path = db_path
        self.table_name = table_name

    def run(self):
        try:
            df = query_db(self.db_path, self.table_name)
            if df is not None:
                self.data_loaded.emit(df)
            else:
                self.error_occurred.emit("Falha ao carregar dados do banco.")
        except Exception as e:
            self.error_occurred.emit(f"Erro ao carregar dados: {e}")

class FilterWorker(QThread):
    """Thread para filtrar dados."""
    filter_finished = pyqtSignal(pd.DataFrame) # Emite o DataFrame filtrado
    error_occurred = pyqtSignal(str)

    def __init__(self, df_completo, search_terms):
        super().__init__()
        self.df_completo = df_completo
        self.search_terms = search_terms

    def run(self):
        try:
            if self.search_terms:
                df_filtrado = filter_dataframe(self.df_completo, self.search_terms)
            else:
                df_filtrado = self.df_completo.copy()
            self.filter_finished.emit(df_filtrado)
        except Exception as e:
            self.error_occurred.emit(f"Erro ao filtrar dados: {e}")

# --- Componentes da GUI ---

class ColumnSelector(QWidget):
    """Widget para selecionar colunas a serem exibidas."""
    columns_changed = pyqtSignal(list) # Emite a lista de colunas selecionadas

    def __init__(self, display_map, initial_columns):
        super().__init__()
        self.display_map = display_map
        self.internal_to_display = {k: v for k, v in display_map.items()}
        self.display_to_internal = {v: k for k, v in display_map.items()}
        
        # Colunas iniciais (internas)
        self.selected_internal_columns = initial_columns
        
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Grupo para seleção
        group_box = QGroupBox("Colunas Visíveis")
        group_layout = QVBoxLayout(group_box)
        
        # ComboBox para adicionar colunas
        self.add_column_combo = QComboBox()
        # Preenche com todas as colunas possíveis (baseadas no display_map)
        all_display_names = sorted(self.display_to_internal.keys())
        self.add_column_combo.addItems(all_display_names)
        
        add_button = QPushButton("Adicionar Coluna")
        add_button.clicked.connect(self.add_column)

        # Lista de colunas selecionadas (usando um ComboBox por simplicidade)
        # Uma implementação mais completa usaria uma QListWidget
        self.selected_columns_label = QLabel("Colunas Atuais: " + ", ".join([self.internal_to_display.get(c, c) for c in self.selected_internal_columns]))
        
        remove_button = QPushButton("Remover Última Coluna")
        remove_button.clicked.connect(self.remove_column)

        group_layout.addWidget(QLabel("Adicionar Coluna:"))
        group_layout.addWidget(self.add_column_combo)
        group_layout.addWidget(add_button)
        group_layout.addWidget(self.selected_columns_label)
        group_layout.addWidget(remove_button)
        
        layout.addWidget(group_box)

    def add_column(self):
        display_name = self.add_column_combo.currentText()
        internal_name = self.display_to_internal.get(display_name)
        if internal_name and internal_name not in self.selected_internal_columns:
            self.selected_internal_columns.append(internal_name)
            self.update_label()
            self.columns_changed.emit(self.selected_internal_columns)

    def remove_column(self):
        if self.selected_internal_columns:
            self.selected_internal_columns.pop()
            self.update_label()
            self.columns_changed.emit(self.selected_internal_columns)

    def update_label(self):
        display_names = [self.internal_to_display.get(c, c) for c in self.selected_internal_columns]
        self.selected_columns_label.setText("Colunas Atuais: " + ", ".join(display_names))

    def get_selected_columns(self):
        return self.selected_internal_columns


class DataPaginator(QWidget):
    """Widget para paginação de dados."""
    page_changed = pyqtSignal(int) # Emite o número da nova página (1-based)

    def __init__(self, df, page_size=50):
        super().__init__()
        self.df = df
        self.page_size = page_size
        self.current_page = 1
        self.total_pages = 1
        self.update_pagination_info()
        self.init_ui()

    def init_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.prev_button = QPushButton("Página Anterior")
        self.prev_button.clicked.connect(self.prev_page)
        self.prev_button.setEnabled(False)

        self.page_info_label = QLabel("Página 1 de 1")

        self.next_button = QPushButton("Próxima Página")
        self.next_button.clicked.connect(self.next_page)
        self.next_button.setEnabled(False)

        # Controle de tamanho da página
        page_size_layout = QHBoxLayout()
        page_size_layout.addWidget(QLabel("Linhas por Página:"))
        self.page_size_spinbox = QSpinBox()
        self.page_size_spinbox.setRange(10, 500)
        self.page_size_spinbox.setSingleStep(10)
        self.page_size_spinbox.setValue(self.page_size)
        self.page_size_spinbox.valueChanged.connect(self.change_page_size)
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
        if self.df is not None and not self.df.empty:
            self.total_pages = (len(self.df) + self.page_size - 1) // self.page_size
        else:
            self.total_pages = 1
            self.current_page = 1
        self.page_info_label.setText(f"Página {self.current_page} de {self.total_pages}")

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
        # Reset para a página 1 ao mudar o tamanho
        self.current_page = 1
        self.update_pagination_info()
        self.update_buttons()
        # Notifica que a página 1 (com novo tamanho) deve ser carregada
        self.page_changed.emit(self.current_page)

    def get_current_slice(self):
        """Retorna o slice do DataFrame para a página atual."""
        if self.df is None or self.df.empty:
            return pd.DataFrame()
        start_idx = (self.current_page - 1) * self.page_size
        end_idx = start_idx + self.page_size
        return self.df.iloc[start_idx:end_idx]


# --- Janela Principal da Aplicacao ---
class SSAMainWindow(QMainWindow):
    """
    Janela principal da aplicacao GUI.
    """
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Consulta Rápida de SSAs - GUI (PoC)")
        self.setGeometry(100, 100, 1200, 800)

        self.df_completo = pd.DataFrame()
        self.df_exibido = pd.DataFrame() # DataFrame filtrado
        self.df_para_tabela = pd.DataFrame() # DataFrame paginado para exibição

        # Carrega mapeamentos de exibição
        self.display_map = load_display_mappings()
        self.internal_to_display = {k: v for k, v in self.display_map.items()}
        
        # Colunas padrão para exibição (prioritárias)
        self.default_columns = [
            'numero_ssa', 'setor_executor', 'situacao', 'descricao_ssa',
            'data_cadastro', 'semana_cadastro'
        ]
        # Garante que colunas padrão existam no mapeamento
        self.visible_columns = [col for col in self.default_columns if col in self.internal_to_display or col == '#']

        self.init_ui()

    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        # --- Barra de Ferramentas Superior ---
        toolbar_layout = QHBoxLayout()
        
        self.load_button = QPushButton("1. Carregar Dados")
        self.load_button.clicked.connect(self.load_data)
        
        self.status_label = QLabel("Status: Aguardando carregamento dos dados...")

        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setRange(0, 0)

        toolbar_layout.addWidget(self.load_button)
        toolbar_layout.addWidget(self.status_label)
        toolbar_layout.addWidget(self.progress_bar)
        toolbar_layout.addStretch()
        
        main_layout.addLayout(toolbar_layout)

        # --- Barra de Pesquisa e Filtros ---
        search_layout = QHBoxLayout()
        self.search_label = QLabel("2. Pesquisar:")
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Digite termos separados por virgula...")
        self.search_input.returnPressed.connect(self.initiate_filtering)
        
        self.search_button = QPushButton("Buscar")
        self.search_button.clicked.connect(self.initiate_filtering)
        
        self.clear_filter_button = QPushButton("Limpar Filtro")
        self.clear_filter_button.clicked.connect(self.clear_filter)
        self.clear_filter_button.setEnabled(False)

        search_layout.addWidget(self.search_label)
        search_layout.addWidget(self.search_input)
        search_layout.addWidget(self.search_button)
        search_layout.addWidget(self.clear_filter_button)
        main_layout.addLayout(search_layout)

        # --- Seletor de Colunas ---
        self.column_selector = ColumnSelector(self.display_map, self.visible_columns)
        self.column_selector.columns_changed.connect(self.on_columns_changed)
        main_layout.addWidget(self.column_selector)

        # --- Paginador ---
        self.paginator = DataPaginator(self.df_para_tabela)
        self.paginator.page_changed.connect(self.display_current_page)
        main_layout.addWidget(self.paginator)

        # --- Tabela de Dados ---
        self.table_widget = QTableWidget()
        self.table_widget.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table_widget.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table_widget.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.table_widget.verticalHeader().setVisible(False)
        
        # Conecta clique duplo para mostrar detalhes (placeholder)
        self.table_widget.doubleClicked.connect(self.on_table_double_click)

        main_layout.addWidget(self.table_widget)

        # --- Conecta Workers ---
        self.data_loader_thread = None
        self.filter_thread = None

    # --- Slots e Handlers ---

    def load_data(self):
        if not os.path.exists(DB_PATH):
             QMessageBox.warning(self, "Erro", f"Banco de dados '{DB_PATH}' não encontrado. Execute o programa principal primeiro.")
             return

        self.status_label.setText("Status: Carregando dados...")
        self.progress_bar.setVisible(True)
        self.load_button.setEnabled(False)
        self.search_button.setEnabled(False)

        self.data_loader_thread = DataLoaderWorker(DB_PATH, TABLE_NAME)
        self.data_loader_thread.data_loaded.connect(self.on_data_loaded)
        self.data_loader_thread.error_occurred.connect(self.on_load_error)
        self.data_loader_thread.finished.connect(self.on_load_finished)
        self.data_loader_thread.start()

    def on_data_loaded(self, df: pd.DataFrame):
        self.df_completo = df.copy()
        # Inicialmente, exibimos todos os dados
        self.df_exibido = df.copy() 
        # Atualiza o paginador com o DataFrame completo
        self.paginator.set_dataframe(self.df_exibido)
        # Exibe a primeira página
        self.display_current_page(1)
        self.status_label.setText(f"Status: {len(self.df_completo)} SSAs carregadas. Pronto para filtrar.")
        self.clear_filter_button.setEnabled(True)

    def on_load_error(self, error_msg: str):
        QMessageBox.critical(self, "Erro de Carregamento", error_msg)
        self.status_label.setText("Status: Erro ao carregar dados.")
        self.load_button.setEnabled(True)
        self.search_button.setEnabled(True)
        self.progress_bar.setVisible(False)

    def on_load_finished(self):
        self.progress_bar.setVisible(False)
        self.load_button.setEnabled(True)
        self.search_button.setEnabled(True)
        self.data_loader_thread = None

    def initiate_filtering(self):
        if self.df_completo.empty:
            QMessageBox.information(self, "Aviso", "Nenhum dado carregado para filtrar.")
            return

        search_text = self.search_input.text().strip()
        search_terms = []
        if search_text:
            search_terms = [term.strip() for term in search_text.split(',') if term.strip()]

        self.status_label.setText("Status: Filtrando dados...")
        self.progress_bar.setVisible(True)
        self.load_button.setEnabled(False)
        self.search_button.setEnabled(False)

        # Inicia a thread de filtragem
        self.filter_thread = FilterWorker(self.df_completo, search_terms)
        self.filter_thread.filter_finished.connect(self.on_filter_finished)
        self.filter_thread.error_occurred.connect(self.on_filter_error)
        self.filter_thread.finished.connect(self.on_filter_finished_cleanup)
        self.filter_thread.start()

    def on_filter_finished(self, df_filtrado: pd.DataFrame):
        self.df_exibido = df_filtrado
        # Atualiza o paginador com o DataFrame filtrado
        self.paginator.set_dataframe(self.df_exibido)
        # Exibe a primeira página dos resultados filtrados
        self.display_current_page(1)
        self.status_label.setText(f"Status: {len(self.df_exibido)} SSAs encontradas.")

    def on_filter_error(self, error_msg: str):
        QMessageBox.critical(self, "Erro de Filtro", error_msg)
        self.status_label.setText("Status: Erro ao aplicar filtro.")

    def on_filter_finished_cleanup(self):
        self.progress_bar.setVisible(False)
        self.load_button.setEnabled(True)
        self.search_button.setEnabled(True)
        self.filter_thread = None

    def clear_filter(self):
        """Limpa o filtro e mostra todos os dados."""
        self.search_input.clear()
        self.df_exibido = self.df_completo.copy()
        self.paginator.set_dataframe(self.df_exibido)
        self.display_current_page(1)
        self.status_label.setText(f"Status: Filtro limpo. {len(self.df_exibido)} SSAs exibidas.")

    def on_columns_changed(self, new_columns):
        """Chamado quando a seleção de colunas muda."""
        self.visible_columns = new_columns
        # Reexibe a página atual com as novas colunas
        self.display_current_page(self.paginator.current_page)

    def display_current_page(self, page_number):
        """Exibe a página especificada do DataFrame filtrado."""
        # Obtem o slice de dados para a página atual do paginator
        self.df_para_tabela = self.paginator.get_current_slice()
        
        if self.df_para_tabela.empty:
            self.table_widget.setRowCount(0)
            self.table_widget.setColumnCount(0)
            return

        # Seleciona apenas as colunas visíveis
        cols_to_show = [col for col in self.visible_columns if col in self.df_para_tabela.columns]
        if not cols_to_show:
            # Se nenhuma coluna selecionada for valida, mostra as padroes
            cols_to_show = [col for col in self.default_columns if col in self.df_para_tabela.columns]
            if not cols_to_show:
                 # Ultimo recurso: mostra todas
                 cols_to_show = self.df_para_tabela.columns.tolist()
        
        display_df = self.df_para_tabela[cols_to_show].copy()

        # Adiciona a coluna de índice '#'
        if '#' not in display_df.columns:
            display_df.insert(0, '#', range((self.paginator.current_page - 1) * self.paginator.page_size + 1, 
                                            (self.paginator.current_page - 1) * self.paginator.page_size + 1 + len(display_df)))

        # Configura a tabela
        self.table_widget.setRowCount(len(display_df))
        self.table_widget.setColumnCount(len(display_df.columns))
        
        # Define cabeçalhos de exibição
        display_headers = []
        for col in display_df.columns:
            if col == '#':
                display_headers.append('#')
            else:
                display_headers.append(self.internal_to_display.get(col, col))
        self.table_widget.setHorizontalHeaderLabels(display_headers)

        # Preenche os dados
        for row_idx in range(len(display_df)):
            for col_idx, col_name in enumerate(display_df.columns):
                value = display_df.iloc[row_idx, col_idx]
                item_text = "" if pd.isna(value) else str(value)
                
                # Trunca texto muito longo para a tabela
                if len(item_text) > 50:
                    item_text = item_text[:47] + "..."
                    
                item = QTableWidgetItem(item_text)
                item.setTextAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
                # Armazena o índice da linha original nos dados filtrados para referência
                if col_name == '#': 
                    item.setData(Qt.ItemDataRole.UserRole, row_idx + (self.paginator.current_page - 1) * self.paginator.page_size)
                self.table_widget.setItem(row_idx, col_idx, item)
        
        # Ajusta largura das colunas
        self.table_widget.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        for i in range(self.table_widget.columnCount()):
             width = self.table_widget.columnWidth(i)
             if width > 250:
                 self.table_widget.setColumnWidth(i, 250)

    def on_table_double_click(self, index):
        """Placeholder para ação de clique duplo (ex: mostrar detalhes)."""
        row = index.row()
        # O item da coluna '#' contém o índice da linha original
        index_item = self.table_widget.item(row, 0) # Assume '#' é a primeira coluna
        if index_item:
            original_index = index_item.data(Qt.ItemDataRole.UserRole)
            if original_index is not None and 0 <= original_index < len(self.df_exibido):
                # Aqui você chamaria uma função para mostrar detalhes
                # Ex: show_details_window(self.df_exibido.iloc[original_index])
                QMessageBox.information(self, "Detalhes", 
                    f"Detalhes para SSA na linha {original_index + 1} (página {self.paginator.current_page})\n"
                    f"Dados: {self.df_exibido.iloc[original_index].to_dict()}")
            else:
                 QMessageBox.information(self, "Info", "Não foi possível encontrar os dados detalhados para esta linha.")

# --- Ponto de Entrada ---
if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = SSAMainWindow()
    window.show()
    sys.exit(app.exec())
