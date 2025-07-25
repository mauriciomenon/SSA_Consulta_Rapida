# gui_ssa_poc.py 20250725 170000 (PoC - GUI PyQt6 Basica para SSA_Consulta_Rapida)
"""
Prova de Conceito de uma Interface Gráfica (GUI) para o projeto SSA_Consulta_Rapida usando PyQt6.

Esta GUI demonstra:
1. Integração com a lógica existente do projeto (core/app_logic.py, armazenamento/database.py).
2. Exibição de dados em uma tabela (QTableWidget).
3. Barra de pesquisa simples.
4. Carregamento de dados do banco de dados SQLite.

Para executar: python gui_ssa_poc.py
(Requer que o projeto ja tenha sido executado uma vez para criar o banco de dados ssas.db)
"""

import sys
import os
import pandas as pd

# --- Configuração do Path do Projeto ---
# Adiciona o diretório raiz do projeto ao sys.path para poder importar os módulos
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

# --- Importações do Projeto ---
from core.app_logic import filter_dataframe
from armazenamento.database import query_db

# --- Importações do PyQt6 ---
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLineEdit, QLabel, QTableWidget, QTableWidgetItem,
    QHeaderView, QMessageBox, QProgressBar
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal

# --- Constantes ---
DB_PATH = os.path.join(project_root, 'data', 'ssas.db')
TABLE_NAME = 'ssas'

# --- Worker Thread para Carregar Dados ---
# Carregar grandes DataFrames na thread principal pode travar a GUI.
# Usar uma thread separada melhora a responsividade.
class DataLoaderWorker(QThread):
    """
    Thread de trabalho para carregar dados do banco de dados sem bloquear a GUI.
    """
    data_loaded = pyqtSignal(pd.DataFrame)  # Sinal emitido quando os dados sao carregados
    error_occurred = pyqtSignal(str)       # Sinal emitido em caso de erro

    def __init__(self, db_path, table_name):
        super().__init__()
        self.db_path = db_path
        self.table_name = table_name

    def run(self):
        """Metodo executado na thread de trabalho."""
        try:
            # Carrega o DataFrame do banco de dados
            df = query_db(self.db_path, self.table_name)
            if df is not None:
                # Emite o sinal com o DataFrame carregado
                self.data_loaded.emit(df)
            else:
                self.error_occurred.emit("Falha ao carregar dados do banco.")
        except Exception as e:
            # Em caso de erro, emite o sinal de erro
            self.error_occurred.emit(f"Erro ao carregar dados: {e}")

# --- Janela Principal da Aplicacao ---
class SSAMainWindow(QMainWindow):
    """
    Janela principal da aplicacao GUI.
    """
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Consulta Rápida de SSAs - GUI (PoC)")
        self.setGeometry(100, 100, 1000, 700) # x, y, width, height

        # DataFrame que armazena os dados carregados
        self.df_completo = pd.DataFrame()
        # DataFrame que armazena os dados filtrados/exibidos
        self.df_exibido = pd.DataFrame()

        # Inicializa a UI
        self.init_ui()

    def init_ui(self):
        """Inicializa os componentes da interface do usuario."""
        # --- Widget Central ---
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        # --- Barra de Ferramentas Superior ---
        toolbar_layout = QHBoxLayout()
        
        self.load_button = QPushButton("Carregar Dados")
        self.load_button.clicked.connect(self.load_data)
        
        self.search_label = QLabel("Pesquisar:")
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Digite termos separados por virgula...")
        self.search_input.returnPressed.connect(self.filter_data) # Enter aciona a busca
        
        self.search_button = QPushButton("Buscar")
        self.search_button.clicked.connect(self.filter_data)
        
        self.status_label = QLabel("Status: Aguardando carregamento dos dados...")
        
        # Barra de progresso (inicialmente oculta)
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setRange(0, 0) # Modo indeterminado

        toolbar_layout.addWidget(self.load_button)
        toolbar_layout.addStretch() # Espaco vazio
        toolbar_layout.addWidget(self.search_label)
        toolbar_layout.addWidget(self.search_input)
        toolbar_layout.addWidget(self.search_button)
        toolbar_layout.addWidget(self.status_label)
        toolbar_layout.addWidget(self.progress_bar)
        
        main_layout.addLayout(toolbar_layout)

        # --- Tabela de Dados ---
        self.table_widget = QTableWidget()
        self.table_widget.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers) # Torna a tabela somente leitura
        # Configura o comportamento de redimensionamento das colunas
        self.table_widget.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.table_widget.verticalHeader().setVisible(False) # Oculta o cabecalho vertical
        
        main_layout.addWidget(self.table_widget)

        # --- Conecta o Worker ---
        self.data_loader_thread = None

    def load_data(self):
        """Inicia o processo de carregamento de dados em uma thread separada."""
        if not os.path.exists(DB_PATH):
             QMessageBox.warning(self, "Erro", f"Banco de dados '{DB_PATH}' não encontrado. Execute o programa principal primeiro.")
             return

        self.status_label.setText("Status: Carregando dados...")
        self.progress_bar.setVisible(True)
        self.load_button.setEnabled(False)
        self.search_button.setEnabled(False)

        # Cria e inicia a thread de carregamento
        self.data_loader_thread = DataLoaderWorker(DB_PATH, TABLE_NAME)
        self.data_loader_thread.data_loaded.connect(self.on_data_loaded)
        self.data_loader_thread.error_occurred.connect(self.on_load_error)
        self.data_loader_thread.finished.connect(self.on_load_finished)
        self.data_loader_thread.start()

    def on_data_loaded(self, df: pd.DataFrame):
        """Callback chamado quando os dados sao carregados com sucesso pela thread."""
        self.df_completo = df.copy()
        self.df_exibido = df.copy()
        self.display_data(self.df_exibido)
        self.status_label.setText(f"Status: {len(self.df_completo)} SSAs carregadas.")

    def on_load_error(self, error_msg: str):
        """Callback chamado se ocorrer um erro durante o carregamento."""
        QMessageBox.critical(self, "Erro de Carregamento", error_msg)
        self.status_label.setText("Status: Erro ao carregar dados.")

    def on_load_finished(self):
        """Callback chamado quando a thread de carregamento termina."""
        self.progress_bar.setVisible(False)
        self.load_button.setEnabled(True)
        self.search_button.setEnabled(True)
        # Limpa a referencia da thread
        self.data_loader_thread = None

    def filter_data(self):
        """Filtra os dados com base no texto da barra de pesquisa."""
        if self.df_completo.empty:
            QMessageBox.information(self, "Aviso", "Nenhum dado carregado para filtrar.")
            return

        search_text = self.search_input.text().strip()
        if not search_text:
            # Se o campo de busca estiver vazio, mostra todos os dados
            self.df_exibido = self.df_completo.copy()
            self.display_data(self.df_exibido)
            self.status_label.setText(f"Status: {len(self.df_exibido)} SSAs exibidas (sem filtro).")
            return

        try:
            # Divide os termos de busca por virgula
            search_terms = [term.strip() for term in search_text.split(',') if term.strip()]
            if search_terms:
                # Usa a funcao de filtragem existente do projeto
                self.df_exibido = filter_dataframe(self.df_completo, search_terms)
                self.display_data(self.df_exibido)
                self.status_label.setText(f"Status: {len(self.df_exibido)} SSAs encontradas.")
            else:
                 # Caso todos os termos sejam vazios apos o strip
                 self.df_exibido = self.df_completo.copy()
                 self.display_data(self.df_exibido)
                 self.status_label.setText(f"Status: {len(self.df_exibido)} SSAs exibidas (sem filtro).")
        except Exception as e:
            QMessageBox.critical(self, "Erro de Filtro", f"Ocorreu um erro ao aplicar o filtro: {e}")
            self.status_label.setText("Status: Erro ao aplicar filtro.")

    def display_data(self, df: pd.DataFrame):
        """Exibe o DataFrame em QTableWidget."""
        if df.empty:
            self.table_widget.setRowCount(0)
            self.table_widget.setColumnCount(0)
            return

        # Configura o numero de linhas e colunas
        self.table_widget.setRowCount(len(df))
        self.table_widget.setColumnCount(len(df.columns))
        
        # Define os cabecalhos das colunas
        self.table_widget.setHorizontalHeaderLabels(df.columns.tolist())

        # Preenche a tabela com os dados
        for row_idx in range(len(df)):
            for col_idx, col_name in enumerate(df.columns):
                # Obtem o valor da celula
                value = df.iloc[row_idx, col_idx]
                # Converte para string, tratando valores NA/NaN
                item_text = "" if pd.isna(value) else str(value)
                # Cria um item da tabela
                item = QTableWidgetItem(item_text)
                # Alinha o texto ao centro verticalmente
                item.setTextAlignment(Qt.AlignmentFlag.AlignVCenter)
                # Define o item na tabela
                self.table_widget.setItem(row_idx, col_idx, item)
        
        # Ajusta o cabecalho horizontal para o conteudo
        self.table_widget.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        # Mas limita o tamanho maximo para evitar colunas muito largas
        # Isso pode ser ajustado ou feito de forma mais dinamica
        for i in range(self.table_widget.columnCount()):
             width = self.table_widget.columnWidth(i)
             if width > 200: # Limite maximo de 200 pixels
                 self.table_widget.setColumnWidth(i, 200)

# --- Ponto de Entrada da Aplicacao ---
if __name__ == '__main__':
    # Cria a aplicacao Qt
    app = QApplication(sys.argv)
    
    # Cria e mostra a janela principal
    window = SSAMainWindow()
    window.show()
    
    # Inicia o loop de eventos da aplicacao
    sys.exit(app.exec())
