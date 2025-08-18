# gui_ssa_poc.py 20250818 - Versão melhorada com funcionalidades adicionais
"""
Prova de Conceito de uma Interface Gráfica (GUI) para o projeto SSA_Consulta_Rapida usando PyQt6.

Esta GUI demonstra:
1. Integração com a lógica existente do projeto (core/app_logic.py, armazenamento/database.py).
2. Exibição de dados em uma tabela (QTableWidget).
3. Barra de pesquisa simples.
4. Carregamento automático de dados do banco de dados SQLite.
5. Ordenação por clique nos cabeçalhos.
6. Funcionalidade de copiar célula.
7. Botão de ajuda para filtros.

Para executar: python gui_ssa_poc.py
(Requer que o projeto ja tenha sido executado uma vez para criar o banco de dados ssas.db)
"""

import sys
import os
import pandas as pd
import json

# --- Configuração do Path do Projeto ---
# Adiciona o diretório raiz do projeto ao sys.path para poder importar os módulos
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# --- Importações do Projeto ---
from core.app_logic import filter_dataframe
from armazenamento.database import query_db

# --- Importações do PyQt6 ---
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLineEdit, QLabel, QTableWidget, QTableWidgetItem,
    QHeaderView, QMessageBox, QProgressBar, QFileDialog, QDialog,
    QTextEdit, QDialogButtonBox, QMenu, QAbstractItemView
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QPoint
from PyQt6.QtGui import QClipboard, QFont, QAction

# --- Constantes ---
DB_PATH = os.path.join(project_root, 'data', 'ssas.db')
TABLE_NAME = 'ssas'

# Mapeamento de títulos das colunas conforme especificado
COLUMN_DISPLAY_NAMES = {
    'numero_ssa': 'Número SSA',
    'situacao': 'Situação', 
    'derivada_de': 'Derivada de',
    'localizacao_codigo': 'Localização',
    'descricao_localizacao': 'Descrição Localização',
    'equipamento': 'Equipamento',
    'semana_cadastro': 'Cadastro',  # Encurtado conforme solicitado
    'data_cadastro': 'Data Cadastro',
    'descricao_ssa': 'Descrição da SSA',
    'setor_executor': 'Executor',
    'setor_emissor': 'Emissor',
    'solicitante': 'Solicitante',  # Corrigido conforme solicitado
    'servico_origem': 'Origem',  # Encurtado conforme solicitado
    'grau_prioridade_emissao': 'Prio. Emissão',  # Encurtado conforme solicitado
    'execucao_simples': 'Exec. Simples',  # Encurtado conforme solicitado
    'semana_programada': 'Sem. Prog.',  # Encurtado conforme solicitado
    'tempo_disponivel': 'Tempo Disponível',
    'data_limite': 'Data Limite',
    'tempo_excedido': 'Tempo Excedido',
    'desde': 'Desde',
    'tempo_total': 'Tempo Total',
    'desde_1': 'Desde1'  # Conforme solicitado
}

# Colunas que não devem ser exibidas
HIDDEN_COLUMNS = ['descricao_localizacao', 'equipamento']

# --- Diálogo de Ajuda para Filtros ---
class FilterHelpDialog(QDialog):
    """
    Diálogo que mostra informações sobre como usar os filtros.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Ajuda - Funcionalidade dos Filtros")
        self.setModal(True)
        self.resize(500, 400)
        
        layout = QVBoxLayout()
        
        # Texto explicativo
        help_text = QTextEdit()
        help_text.setReadOnly(True)
        help_text.setHtml("""
        <h3>Como usar os filtros na Consulta Rápida de SSAs</h3>
        
        <h4>Filtros Básicos:</h4>
        <ul>
            <li><b>Vírgula (,)</b>: Separa múltiplos termos de busca</li>
            <li><b>Espaço</b>: Também separa termos (equivalente à vírgula)</li>
            <li><b>Termos simples</b>: Digite qualquer palavra para buscar em todas as colunas</li>
        </ul>
        
        <h4>Filtros Especiais:</h4>
        <ul>
            <li><b>! (exclamação)</b>: Exclui registros que contenham o termo</li>
            <li><b>Exemplo</b>: "mel3, !cancelada" - busca MEL3 mas exclui canceladas</li>
        </ul>
        
        <h4>Exemplos de Uso:</h4>
        <ul>
            <li><b>mel3</b> - Busca todas as SSAs relacionadas a MEL3</li>
            <li><b>pendente, programar</b> - Busca SSAs pendentes de programar</li>
            <li><b>executada, !mel4</b> - Busca executadas, exceto MEL4</li>
            <li><b>g076, amp</b> - Busca G076 com situação AMP</li>
        </ul>
        
        <h4>Dicas:</h4>
        <ul>
            <li>A busca não diferencia maiúsculas de minúsculas</li>
            <li>Termos parciais funcionam (ex: "exec" encontra "executada")</li>
            <li>Deixe vazio para mostrar todas as SSAs</li>
        </ul>
        """)
        
        layout.addWidget(help_text)
        
        # Botões
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok)
        button_box.accepted.connect(self.accept)
        layout.addWidget(button_box)
        
        self.setLayout(layout)

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
        self.setWindowTitle("Consulta Rápida de SSAs - GUI (PoC) v2.0")
        self.setGeometry(100, 100, 1200, 800) # x, y, width, height

        # DataFrame que armazena os dados carregados
        self.df_completo = pd.DataFrame()
        # DataFrame que armazena os dados filtrados/exibidos
        self.df_exibido = pd.DataFrame()
        
        # Para ordenação
        self.sort_column = None
        self.sort_ascending = True

        # Inicializa a UI
        self.init_ui()
        
        # Carrega dados automaticamente se o banco existir
        self.auto_load_data()

    def init_ui(self):
        """Inicializa os componentes da interface do usuario."""
        # --- Widget Central ---
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        # --- Barra de Ferramentas Superior ---
        toolbar_layout = QHBoxLayout()
        
        # Botão de carregar dados
        self.load_button = QPushButton("Carregar Dados")
        self.load_button.clicked.connect(self.load_data)
        
        # Botão de ajuda para filtros (mesmo tamanho que carregar dados)
        self.help_button = QPushButton("Ajuda Filtros")
        self.help_button.clicked.connect(self.show_filter_help)
        self.help_button.setMinimumWidth(self.load_button.sizeHint().width())
        
        # Botão para navegar e carregar outro DB
        self.browse_button = QPushButton("Abrir DB...")
        self.browse_button.clicked.connect(self.browse_database)
        
        self.search_label = QLabel("Pesquisar:")
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Digite termos separados por vírgula ou espaço...")
        self.search_input.returnPressed.connect(self.filter_data) # Enter aciona a busca
        
        self.search_button = QPushButton("Buscar")
        self.search_button.clicked.connect(self.filter_data)
        
        self.status_label = QLabel("Status: Carregando dados automaticamente...")
        
        # Barra de progresso (inicialmente oculta)
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setRange(0, 0) # Modo indeterminado

        toolbar_layout.addWidget(self.load_button)
        toolbar_layout.addWidget(self.help_button)
        toolbar_layout.addWidget(self.browse_button)
        toolbar_layout.addStretch() # Espaco vazio
        toolbar_layout.addWidget(self.search_label)
        toolbar_layout.addWidget(self.search_input)
        toolbar_layout.addWidget(self.search_button)
        
        main_layout.addLayout(toolbar_layout)
        
        # Segunda linha com status e progresso
        status_layout = QHBoxLayout()
        status_layout.addWidget(self.status_label)
        status_layout.addWidget(self.progress_bar)
        status_layout.addStretch()
        main_layout.addLayout(status_layout)

        # --- Tabela de Dados ---
        self.table_widget = QTableWidget()
        self.table_widget.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers) # Torna a tabela somente leitura
        # Configura o comportamento de redimensionamento das colunas
        self.table_widget.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.table_widget.verticalHeader().setVisible(False) # Oculta o cabecalho vertical
        
        # Conecta clique no cabeçalho para ordenação
        self.table_widget.horizontalHeader().sectionClicked.connect(self.sort_by_column)
        
        # Conecta duplo clique no divisor para otimizar largura da coluna
        self.table_widget.horizontalHeader().sectionDoubleClicked.connect(self.optimize_column_width)
        
        # Configura menu de contexto
        self.table_widget.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table_widget.customContextMenuRequested.connect(self.show_context_menu)
        
        # Conecta clique em célula para copiar
        self.table_widget.cellClicked.connect(self.copy_cell_to_clipboard)
        
        main_layout.addWidget(self.table_widget)

        # --- Conecta o Worker ---
        self.data_loader_thread = None
    
    def auto_load_data(self):
        """Carrega dados automaticamente se o banco de dados existir."""
        if os.path.exists(DB_PATH):
            self.load_data()
        else:
            self.status_label.setText("Status: Banco de dados não encontrado. Use 'Abrir DB...' ou execute o programa principal primeiro.")
    
    def show_filter_help(self):
        """Mostra o diálogo de ajuda para filtros."""
        help_dialog = FilterHelpDialog(self)
        help_dialog.exec()
    
    def browse_database(self):
        """Permite navegar e selecionar um arquivo de banco de dados."""
        file_path, _ = QFileDialog.getOpenFileName(
            self, 
            "Selecionar arquivo de banco de dados",
            os.path.join(project_root, 'data'),
            "Arquivos SQLite (*.db);;Todos os arquivos (*)"
        )
        if file_path:
            global DB_PATH
            DB_PATH = file_path
            self.load_data()
    
    def sort_by_column(self, logical_index):
        """Ordena a tabela pelo cabeçalho clicado."""
        if self.df_exibido.empty:
            return
        
        column_name = self.df_exibido.columns[logical_index]
        
        # Se é a mesma coluna, inverte a ordem
        if self.sort_column == column_name:
            self.sort_ascending = not self.sort_ascending
        else:
            self.sort_column = column_name
            self.sort_ascending = True
        
        # Ordena o DataFrame
        self.df_exibido = self.df_exibido.sort_values(
            by=column_name, 
            ascending=self.sort_ascending,
            na_position='last'
        )
        
        # Atualiza a exibição
        self.display_data(self.df_exibido)
        
        # Atualiza o status
        sort_direction = "crescente" if self.sort_ascending else "decrescente"
        self.status_label.setText(f"Status: {len(self.df_exibido)} SSAs - Ordenado por '{column_name}' ({sort_direction})")
    
    def copy_cell_to_clipboard(self, row, column):
        """Copia o conteúdo da célula clicada para o clipboard."""
        item = self.table_widget.item(row, column)
        if item:
            clipboard = QApplication.clipboard()
            clipboard.setText(item.text())
            
            # Mostra uma mensagem breve (opcional)
            column_name = self.table_widget.horizontalHeaderItem(column).text()
            self.status_label.setText(f"Status: Copiado '{item.text()[:50]}...' da coluna '{column_name}'")
    
    def get_display_name(self, column_name):
        """Retorna o nome de exibição para uma coluna."""
        return COLUMN_DISPLAY_NAMES.get(column_name, column_name)

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
        
        # OTIMIZAÇÃO: Limita exibição inicial a 300 registros para melhor performance
        MAX_INITIAL_DISPLAY = 300
        if len(df) > MAX_INITIAL_DISPLAY:
            self.df_exibido = df.head(MAX_INITIAL_DISPLAY).copy()
            total_records = len(df)
            self.status_label.setText(f"Status: Exibindo {MAX_INITIAL_DISPLAY} de {total_records} SSAs (use filtros para refinar).")
        else:
            self.df_exibido = df.copy()
            self.status_label.setText(f"Status: {len(self.df_exibido)} SSAs carregadas.")
            
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
            # OTIMIZAÇÃO: Se vazio, limita a 300 registros para evitar travamento
            MAX_DISPLAY = 300
            if len(self.df_completo) > MAX_DISPLAY:
                self.df_exibido = self.df_completo.head(MAX_DISPLAY).copy()
                total = len(self.df_completo)
                self.status_label.setText(f"Status: Exibindo {MAX_DISPLAY} de {total} SSAs (use filtros para refinar).")
            else:
                self.df_exibido = self.df_completo.copy()
                self.status_label.setText(f"Status: {len(self.df_exibido)} SSAs exibidas (sem filtro).")
            self.display_data(self.df_exibido)
            return

        try:
            # Divide os termos de busca por vírgula ou espaço
            import re
            search_terms = [term.strip() for term in re.split(r'[,\s]+', search_text) if term.strip()]
            
            if search_terms:
                # Mostra progresso para operações longas
                if len(self.df_completo) > 5000:
                    self.progress_bar.setVisible(True)
                    QApplication.processEvents()  # Atualiza a UI
                
                # IMPORTANTE: Usa a funcao de filtragem existente do projeto em TODO o dataset
                df_filtrado_completo = filter_dataframe(self.df_completo, search_terms)
                
                # OTIMIZAÇÃO: Limita exibição dos resultados filtrados a 300 para performance
                MAX_FILTERED_DISPLAY = 300
                if len(df_filtrado_completo) > MAX_FILTERED_DISPLAY:
                    self.df_exibido = df_filtrado_completo.head(MAX_FILTERED_DISPLAY).copy()
                    total_filtered = len(df_filtrado_completo)
                    total_complete = len(self.df_completo)
                    self.status_label.setText(f"Status: Exibindo {MAX_FILTERED_DISPLAY} de {total_filtered} SSAs encontradas (de {total_complete} total) com '{search_text}'.")
                else:
                    self.df_exibido = df_filtrado_completo.copy()
                    total_complete = len(self.df_completo)
                    self.status_label.setText(f"Status: {len(self.df_exibido)} SSAs encontradas (de {total_complete} total) com '{search_text}'.")
                
                self.display_data(self.df_exibido)
                
                if len(self.df_completo) > 5000:
                    self.progress_bar.setVisible(False)
            else:
                 # Caso todos os termos sejam vazios apos o strip
                 self.df_exibido = self.df_completo.copy()
                 self.display_data(self.df_exibido)
                 self.status_label.setText(f"Status: {len(self.df_exibido)} SSAs exibidas (sem filtro).")
        except Exception as e:
            self.progress_bar.setVisible(False)
            QMessageBox.critical(self, "Erro de Filtro", f"Ocorreu um erro ao aplicar o filtro: {e}")
            self.status_label.setText("Status: Erro ao aplicar filtro.")

    def display_data(self, df: pd.DataFrame):
        """Exibe o DataFrame em QTableWidget com mapeamento de colunas e ocultação de colunas."""
        if df.empty:
            self.table_widget.setRowCount(0)
            self.table_widget.setColumnCount(0)
            return

        # Filtra colunas para exibição (remove as ocultas)
        visible_columns = [col for col in df.columns if col not in HIDDEN_COLUMNS]
        df_display = df[visible_columns].copy()

        # Otimização: desativa atualizações durante o preenchimento
        self.table_widget.setUpdatesEnabled(False)
        
        try:
            # Configura o numero de linhas e colunas
            self.table_widget.setRowCount(len(df_display))
            self.table_widget.setColumnCount(len(df_display.columns))
            
            # Define os cabecalhos das colunas usando mapeamento
            header_labels = [self.get_display_name(col) for col in df_display.columns]
            self.table_widget.setHorizontalHeaderLabels(header_labels)

            # Mostra progresso para datasets grandes
            show_progress = len(df_display) > 1000
            if show_progress:
                self.progress_bar.setVisible(True)
                QApplication.processEvents()

            # Preenche a tabela com os dados em lotes para melhor performance
            batch_size = 300 if len(df_display) > 1000 else len(df_display)
            
            for start_row in range(0, len(df_display), batch_size):
                end_row = min(start_row + batch_size, len(df_display))
                
                for row_idx in range(start_row, end_row):
                    for col_idx, col_name in enumerate(df_display.columns):
                        # Obtem o valor da celula
                        value = df_display.iloc[row_idx, col_idx]
                        
                        # Tratamento especial para valores numéricos
                        if pd.isna(value):
                            item_text = ""
                        elif isinstance(value, float) and value.is_integer():
                            # Remove .0 desnecessário (ex: 202542.0 → 202542)
                            item_text = str(int(value))
                        else:
                            item_text = str(value)
                        
                        # Limite de tamanho para descrições longas
                        if col_name == 'descricao_ssa' and len(item_text) > 120:  # Aumentei o limite
                            item_text = item_text[:117] + "..."
                        elif col_name == 'descricao_execucao' and len(item_text) > 80:  # Novo limite para descrição execução
                            item_text = item_text[:77] + "..."
                        
                        # Cria um item da tabela
                        item = QTableWidgetItem(item_text)
                        # Alinha o texto ao centro verticalmente
                        item.setTextAlignment(Qt.AlignmentFlag.AlignVCenter)
                        # Define o item na tabela
                        self.table_widget.setItem(row_idx, col_idx, item)
                
                # Atualiza UI periodicamente para manter responsividade
                if show_progress:
                    QApplication.processEvents()
            
            if show_progress:
                self.progress_bar.setVisible(False)
                
        finally:
            # Sempre reativa as atualizações
            self.table_widget.setUpdatesEnabled(True)
        
        # Ajusta o cabecalho horizontal para o conteudo, mas com limites
        self.table_widget.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        
        # Define larguras máximas para colunas específicas
        column_max_widths = {
            'numero_ssa': 120,
            'situacao': 80,
            'derivada_de': 100,
            'localizacao_codigo': 120,
            'semana_cadastro': 100,
            'data_cadastro': 120,
            'descricao_ssa': 300,
            'setor_executor': 80,
            'setor_emissor': 80
        }
        
        for i, col_name in enumerate(df_display.columns):
            width = self.table_widget.columnWidth(i)
            max_width = column_max_widths.get(col_name, 200)
            if width > max_width:
                self.table_widget.setColumnWidth(i, max_width)
                
        # Permite que a descrição da SSA use mais espaço se disponível
        if 'descricao_ssa' in df_display.columns:
            desc_col_idx = list(df_display.columns).index('descricao_ssa')
            self.table_widget.horizontalHeader().setSectionResizeMode(
                desc_col_idx, QHeaderView.ResizeMode.Stretch
            )

    def show_context_menu(self, position: QPoint):
        """Mostra menu de contexto para copiar dados."""
        item = self.table_widget.itemAt(position)
        if item is None:
            return
            
        # Cria o menu de contexto
        context_menu = QMenu(self)
        
        # Ação para copiar o valor da célula
        copy_cell_action = QAction("Copiar Valor", self)
        copy_cell_action.triggered.connect(lambda: self.copy_cell_value(item))
        context_menu.addAction(copy_cell_action)
        
        # Ação para copiar a linha inteira
        copy_row_action = QAction("Copiar Linha", self)
        copy_row_action.triggered.connect(lambda: self.copy_row_data(item.row()))
        context_menu.addAction(copy_row_action)
        
        # Mostra o menu na posição do cursor
        context_menu.exec(self.table_widget.mapToGlobal(position))
    
    def copy_cell_value(self, item: QTableWidgetItem):
        """Copia o valor de uma célula específica."""
        if item is not None:
            clipboard = QApplication.clipboard()
            clipboard.setText(item.text())
            self.status_label.setText(f"Status: Valor copiado: '{item.text()[:50]}{'...' if len(item.text()) > 50 else ''}'")
    
    def copy_row_data(self, row: int):
        """Copia todos os dados de uma linha."""
        if row >= 0 and row < self.table_widget.rowCount():
            row_data = []
            for col in range(self.table_widget.columnCount()):
                item = self.table_widget.item(row, col)
                row_data.append(item.text() if item else "")
            
            # Cria uma string separada por tabs (compatível com Excel)
            row_text = "\t".join(row_data)
            clipboard = QApplication.clipboard()
            clipboard.setText(row_text)
            self.status_label.setText(f"Status: Linha {row + 1} copiada para área de transferência.")

    def optimize_column_width(self, logical_index: int):
        """Otimiza a largura de uma coluna específica com base no conteúdo."""
        if logical_index >= 0 and logical_index < self.table_widget.columnCount():
            # Calcula a largura ideal baseada no conteúdo
            self.table_widget.resizeColumnToContents(logical_index)
            
            # Aplica limites razoáveis para evitar colunas muito largas ou pequenas
            current_width = self.table_widget.columnWidth(logical_index)
            min_width = 60
            max_width = 400
            
            # Se a coluna contém descrições, permite largura maior
            header_text = self.table_widget.horizontalHeaderItem(logical_index)
            if header_text and 'Descrição' in header_text.text():
                max_width = 600
            
            optimized_width = max(min_width, min(current_width, max_width))
            self.table_widget.setColumnWidth(logical_index, optimized_width)
            
            self.status_label.setText(f"Status: Coluna otimizada para largura {optimized_width}px.")

# --- Ponto de Entrada da Aplicacao ---
if __name__ == '__main__':
    # Cria a aplicacao Qt
    app = QApplication(sys.argv)
    
    # Cria e mostra a janela principal
    window = SSAMainWindow()
    window.show()
    
    # Inicia o loop de eventos da aplicacao
    sys.exit(app.exec())
