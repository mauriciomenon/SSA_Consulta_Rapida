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

# --- Função para Carregar Configurações da GUI PoC ---
def load_gui_preferences():
    """Carrega configurações específicas da GUI PoC do arquivo JSON"""
    config_path = os.path.join(project_root, 'config', 'gui_poc_preferences.json')
    
    # Configurações padrão caso o arquivo não exista
    default_config = {
        "display_columns": [
            "numero_ssa", "situacao", "derivada_de", "localizacao_codigo",
            "semana_cadastro", "data_cadastro", "descricao_ssa",
            "setor_executor", "setor_emissor", "solicitante", "semana_programada",
            "descricao_execucao"
        ],
        "hidden_columns": ["descricao_localizacao", "equipamento", "servico_origem"],
        "column_display_names": {
            "numero_ssa": "Número SSA", "situacao": "Situação", 
            "derivada_de": "Derivada de", "localizacao_codigo": "Localização",
            "semana_cadastro": "Cadastro", "data_cadastro": "Data Cadastro",
            "descricao_ssa": "Descrição da SSA", "setor_executor": "Executor",
            "setor_emissor": "Emissor", "solicitante": "Solicitante",
            "semana_programada": "Sem. Prog.", "descricao_execucao": "Descrição Execução"
        },
        "column_widths": {
            "numero_ssa": 85, "situacao": 65, "derivada_de": 85,
            "localizacao_codigo": 85, "semana_cadastro": 65, "data_cadastro": 85,
            "setor_executor": 65, "setor_emissor": 60, "solicitante": 120,
            "semana_programada": 75, "descricao_ssa": 350, "descricao_execucao": 130
        },
        "stretch_columns": ["descricao_ssa"]
    }
    
    try:
        if os.path.exists(config_path):
            with open(config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        else:
            print(f"Arquivo de configuração não encontrado em {config_path}, usando padrões.")
            return default_config
    except Exception as e:
        print(f"Erro ao carregar configurações: {e}, usando padrões.")
        return default_config

# Carrega as configurações globalmente
GUI_PREFERENCES = load_gui_preferences()

# --- Importações do Projeto ---
from core.app_logic import filter_dataframe
from armazenamento.database import query_db

# --- Importações do PyQt6 (com fallback headless para CI) ---
QT_AVAILABLE = True
try:
    from PyQt6.QtWidgets import (
        QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
        QPushButton, QLineEdit, QLabel, QTableWidget, QTableWidgetItem,
        QHeaderView, QMessageBox, QProgressBar, QFileDialog, QDialog,
        QTextEdit, QDialogButtonBox, QMenu, QAbstractItemView
    )
    from PyQt6.QtCore import Qt, QThread, pyqtSignal, QPoint
except Exception:
    QT_AVAILABLE = False
    class _Sig:
        def emit(self, *a, **k): pass
        def connect(self, *a, **k): pass
    def pyqtSignal(*a, **k): return _Sig()
    class QWidget: pass
    class QMainWindow: pass
    class QApplication:
        def __init__(self, *a, **k): pass
        def exec(self): return 0
    class QVBoxLayout:
        def __init__(self, *a, **k): pass
    class QHBoxLayout(QVBoxLayout): pass
    class QLabel: 
        def __init__(self, *a, **k): pass
    class QPushButton: 
        def __init__(self, *a, **k): pass
    class QLineEdit:
        def __init__(self, *a, **k): pass
        def text(self): return ""
    class QTableWidget: pass
    class QTableWidgetItem: 
        def __init__(self, *a, **k): pass
    class QHeaderView: Stretch = 1
    class QMessageBox: pass
    class QProgressBar: pass
    class QFileDialog: pass
    class QDialog: pass
    class QTextEdit: pass
    class QDialogButtonBox: Ok=1; Cancel=2
    class QMenu: pass
    class QAbstractItemView: NoEditTriggers=0
    class Qt: AlignLeft=0
from PyQt6.QtGui import QClipboard, QFont, QAction

# --- Constantes ---
DB_PATH = os.path.join(project_root, 'data', 'ssas.db')
TABLE_NAME = 'ssa_table'

# --- Configurações Dinâmicas da GUI PoC (carregadas do JSON) ---
COLUMN_DISPLAY_NAMES = GUI_PREFERENCES.get("column_display_names", {})
PRIORITY_COLUMNS = GUI_PREFERENCES.get("display_columns", [])
HIDDEN_COLUMNS = GUI_PREFERENCES.get("hidden_columns", [])

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
        # Botão About (antigo carregar dados)
        self.about_button = QPushButton("About")
        self.about_button.clicked.connect(self.show_about)
        
        # Botão de ajuda para filtros (mesmo tamanho que about)
        self.help_button = QPushButton("Ajuda Filtros")
        self.help_button.clicked.connect(self.show_filter_help)
        self.help_button.setMinimumWidth(self.about_button.sizeHint().width())
        
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

        toolbar_layout.addWidget(self.about_button)
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
        
        # Conecta duplo clique na linha para mostrar detalhes completos
        self.table_widget.cellDoubleClicked.connect(self.show_row_details)
        
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
    
    def show_about(self):
        """Mostra informações sobre o programa e funcionalidades implementadas."""
        about_dialog = QDialog(self)
        about_dialog.setWindowTitle("Sobre - Consulta Rápida SSAs PoC")
        about_dialog.setFixedSize(600, 500)
        
        layout = QVBoxLayout()
        
        # Título
        title = QLabel("Consulta Rápida de SSAs - PoC Melhorada")
        title.setFont(self._bold_font(14))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        
        # Conteúdo
        content = QTextEdit()
        content.setReadOnly(True)
        content.setHtml("""
        <h3>Funcionalidades Implementadas</h3>
        <ul>
            <li><b>Carregamento Automático:</b> Dados carregados automaticamente na inicialização</li>
            <li><b>Sistema de Filtros Avançado:</b> Busca por múltiplos termos (vírgula ou espaço)</li>
            <li><b>Ajuda de Filtros:</b> Instruções detalhadas sobre como usar os filtros</li>
            <li><b>Ordenação por Colunas:</b> Clique no cabeçalho para ordenar</li>
            <li><b>Cópia de Dados:</b> Menu botão direito - Copiar valor ou linha inteira</li>
            <li><b>Títulos Personalizados:</b> Nomes de colunas otimizados e encurtados</li>
            <li><b>Otimizações de Performance:</b> Limitação inteligente a 300 registros</li>
            <li><b>Barra de Progresso:</b> Feedback visual para operações longas</li>
            <li><b>Otimização de Colunas:</b> Duplo clique no divisor ajusta largura</li>
            <li><b>Interface Responsiva:</b> Carregamento em lotes para evitar travamentos</li>
            <li><b>Detalhes de Linha:</b> Duplo clique na linha mostra todos os dados da SSA</li>
        </ul>
        
        <h3>Melhorias de Performance</h3>
        <ul>
            <li><b>Limitação Inteligente:</b> Exibe máximo 300 registros, busca em todo o dataset</li>
            <li><b>Carregamento em Lotes:</b> Processamento em batches para UI responsiva</li>
            <li><b>Colunas Prioritárias:</b> Mostra apenas colunas essenciais até 'Descrição Execução'</li>
            <li><b>Threading:</b> Operações de I/O em threads separadas</li>
            <li><b>Números Otimizados:</b> Remove decimais desnecessários (202542.0 → 202542)</li>
        </ul>
        
        <h3>Como Usar</h3>
        <ul>
            <li><b>Filtros:</b> Digite termos separados por vírgula ou espaço</li>
            <li><b>Cópia:</b> Botão direito → Copiar Valor ou Copiar Linha</li>
            <li><b>Ordenação:</b> Clique no cabeçalho da coluna</li>
            <li><b>Ajuste de Colunas:</b> Duplo clique entre divisores</li>
            <li><b>Banco Externo:</b> Use 'Abrir DB...' para carregar outro banco</li>
            <li><b>Detalhes Completos:</b> Duplo clique na linha para ver todos os campos da SSA</li>
        </ul>
        
        <p><b>Versão:</b> PoC Otimizada v2.0<br>
        <b>Data:</b> 2025-08-18<br>
        <b>Repositório:</b> <a href="https://github.com/mauriciomenon/SSA_Consulta_Rapida">https://github.com/mauriciomenon/SSA_Consulta_Rapida</a></p>
        """)
        layout.addWidget(content)
        
        # Botão OK
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok)
        button_box.accepted.connect(about_dialog.accept)
        layout.addWidget(button_box)
        
        about_dialog.setLayout(layout)
        about_dialog.exec()
    
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
        if (item := self.table_widget.item(row, column)):
            clipboard = QApplication.clipboard()
            clipboard.setText(item.text())
            
            # Mostra uma mensagem breve (opcional)
            column_name = self.table_widget.horizontalHeaderItem(column).text()
            self.status_label.setText(f"Status: Copiado '{item.text()[:50]}...' da coluna '{column_name}'")
    
    def get_display_name(self, column_name):
        """Retorna o nome de exibição para uma coluna."""
        return COLUMN_DISPLAY_NAMES.get(column_name, column_name)

    # Helpers internos (métodos únicos; remoção de duplicatas)

    def _populate_table(self, df_display: pd.DataFrame, batch_size: int, show_progress: bool) -> None:
        """Preenche a tabela em lotes, mantendo a UI responsiva."""
        for start_row in range(0, len(df_display), batch_size):
            end_row = min(start_row + batch_size, len(df_display))

            for row_idx in range(start_row, end_row):
                for col_idx, col_name in enumerate(df_display.columns):
                    value = df_display.iloc[row_idx, col_idx]
                    item_text = self._format_value(col_name, value)

                    item = QTableWidgetItem(item_text)
                    item.setTextAlignment(Qt.AlignmentFlag.AlignVCenter)
                    self.table_widget.setItem(row_idx, col_idx, item)

            if show_progress:
                QApplication.processEvents()

        if show_progress:
            self.progress_bar.setVisible(False)

    def load_data(self):
        """Inicia o processo de carregamento de dados em uma thread separada."""
        if not os.path.exists(DB_PATH):
             QMessageBox.warning(self, "Erro", f"Banco de dados '{DB_PATH}' não encontrado. Execute o programa principal primeiro.")
             return

        # OTIMIZAÇÃO: Verifica se já existe uma thread rodando
        if getattr(self, 'data_loader_thread', None) and self.data_loader_thread.isRunning():
            self.status_label.setText("Status: Carregamento já em andamento...")
            return
            
        self.status_label.setText("Status: Carregando dados...")
        self.progress_bar.setVisible(True)
        self.about_button.setEnabled(False)
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
        self.about_button.setEnabled(True)
        self.search_button.setEnabled(True)
        # Limpa a referencia da thread
        self.data_loader_thread = None

    def filter_data(self):
        """Filtra os dados com base no texto da barra de pesquisa."""
        if self.df_completo.empty:
            QMessageBox.information(self, "Aviso", "Nenhum dado carregado para filtrar.")
            return

        search_text = self.search_input.text().strip()

        # Limita tamanho do texto de busca para evitar problemas
        if len(search_text) > 100:
            QMessageBox.warning(self, "Filtro muito longo", "O filtro foi limitado a 100 caracteres para evitar problemas de performance.")
            search_text = search_text[:100]
            self.search_input.setText(search_text)

        # Sem filtro: aplica exibição limitada
        if not search_text:
            self._show_unfiltered_preview()
            return

        try:
            terms = self._parse_search_terms(search_text)

            if not terms:
                # Nada útil após sanitização
                self._show_unfiltered_preview()
                self.status_label.setText(f"Status: {len(self.df_exibido)} SSAs exibidas (filtro vazio).")
                return

            long_op = len(self.df_completo) > 5000
            if long_op:
                self.progress_bar.setVisible(True)
                QApplication.processEvents()

            try:
                df_filtrado = filter_dataframe(self.df_completo, terms)
            except Exception as filter_error:
                if long_op:
                    self.progress_bar.setVisible(False)
                QMessageBox.critical(self, "Erro de Filtro",
                                     f"Erro durante a filtragem: {filter_error}\n\n"
                                     f"Termos de busca: {terms}")
                self.status_label.setText("Status: Erro ao aplicar filtro.")
                return

            # Limita exibição de resultados
            MAX_FILTERED_DISPLAY = 300
            total_complete = len(self.df_completo)
            if len(df_filtrado) > MAX_FILTERED_DISPLAY:
                self.df_exibido = df_filtrado.head(MAX_FILTERED_DISPLAY).copy()
                total_filtered = len(df_filtrado)
                self.status_label.setText(
                    f"Status: Exibindo {MAX_FILTERED_DISPLAY} de {total_filtered} SSAs encontradas (de {total_complete} total) com '{search_text}'."
                )
            else:
                self.df_exibido = df_filtrado.copy()
                self.status_label.setText(
                    f"Status: {len(self.df_exibido)} SSAs encontradas (de {total_complete} total) com '{search_text}'."
                )

            self.display_data(self.df_exibido)

            if long_op:
                self.progress_bar.setVisible(False)
        except Exception as e:
            self.progress_bar.setVisible(False)
            QMessageBox.critical(self, "Erro de Filtro",
                                 f"Ocorreu um erro inesperado ao aplicar o filtro: {e}\n\n"
                                 f"Texto de busca: '{search_text}'\n"
                                 f"Se o problema persistir, tente termos mais simples.")
            self.status_label.setText("Status: Erro ao aplicar filtro.")
            # Recupera estado seguro
            self.df_exibido = self.df_completo.head(300).copy()
            self.display_data(self.df_exibido)

    def _parse_search_terms(self, search_text: str) -> list:
        """Converte o texto de busca em lista de termos sanitizados."""
        import re
        safe_text = re.sub(r'[^\w\s,!.-]', '', search_text)
        raw_terms = re.split(r'[,\s]+', safe_text)
        terms = []
        for term in raw_terms:
            t = term.strip()
            if t and len(t) >= 1:
                terms.append(t)
        return terms

    def _show_unfiltered_preview(self) -> None:
        """Mostra amostra limitada quando não há filtro fornecido."""
        MAX_DISPLAY = 300
        if len(self.df_completo) > MAX_DISPLAY:
            self.df_exibido = self.df_completo.head(MAX_DISPLAY).copy()
            total = len(self.df_completo)
            self.status_label.setText(
                f"Status: Exibindo {MAX_DISPLAY} de {total} SSAs (use filtros para refinar)."
            )
        else:
            self.df_exibido = self.df_completo.copy()
            self.status_label.setText(
                f"Status: {len(self.df_exibido)} SSAs exibidas (sem filtro)."
            )
        self.display_data(self.df_exibido)

    # Helpers internos
    def _bold_font(self, size: int) -> QFont:
        """Cria um QFont negrito com o tamanho indicado."""
        f = QFont()
        f.setPointSize(size)
        f.setBold(True)
        return f

    def _format_value(self, col_name: str, value) -> str:
        """Formata valores para exibição uniforme na tabela e diálogos."""
        if pd.isna(value):
            return ""
        if isinstance(value, float) and value.is_integer():
            value = int(value)
        text = str(value)
        # Formatação especial para datas com hora
        if col_name == 'data_cadastro' and ' ' in text and len(text) > 10:
            text = text.split(' ')[0]
        return text

    def display_data(self, df: pd.DataFrame):
        """Exibe o DataFrame em QTableWidget com mapeamento de colunas e ocultação de colunas."""
        if df.empty:
            self.table_widget.setRowCount(0)
            self.table_widget.setColumnCount(0)
            return

        # Use PRIORITY_COLUMNS para definir quais colunas exibir
        # Filtra apenas colunas que existem no DataFrame e não estão ocultas
        # CORREÇÃO: Tenta variações de nomes de colunas para pegar os dados corretos
        available_columns = []
        
        # Mapeamento de colunas prioritárias com alternativas
        column_alternatives = {
            'numero_ssa': ['Número da SSA', 'numero_ssa'],
            'semana_cadastro': ['Semana de Cadastro', 'semana_cadastro'], 
            'descricao_execucao': ['Descrição Execução', 'descricao_execucao']
        }
        
        for col in PRIORITY_COLUMNS:
            column_found = None
            
            # Se a coluna tem alternativas, tenta encontrar a melhor
            if col in column_alternatives:
                for alt_col in column_alternatives[col]:
                    if alt_col in df.columns and alt_col not in HIDDEN_COLUMNS:
                        column_found = alt_col
                        break
            # Senão, usa o nome original
            elif col in df.columns and col not in HIDDEN_COLUMNS:
                column_found = col
                
            if column_found:
                available_columns.append(column_found)
        
        df_display = df[available_columns].copy()

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
            self._populate_table(df_display, batch_size, show_progress)
            # Desabilitado: loop legacy mantido como referência
            if False:
                # Bloco legado desabilitado
                pass
            """
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
                            
                        # CORREÇÃO: Formatação especial para data_cadastro (remove hora/minuto/segundo)
                        if col_name == 'data_cadastro' and ' ' in item_text and len(item_text) > 10:
                                item_text = item_text.split(' ')[0]  # Pega só a data
                        
                        # Texto completo sem limitações para melhor visualização
                        # (As colunas agora são largas o suficiente para mostrar mais conteúdo)
                        
                        # Cria um item da tabela
                        item = QTableWidgetItem(item_text)
                        # Alinha o texto ao centro verticalmente
                        item.setTextAlignment(Qt.AlignmentFlag.AlignVCenter)
                        # Define o item na tabela
                        self.table_widget.setItem(row_idx, col_idx, item)
                
                # Atualiza UI periodicamente para manter responsividade
                if show_progress:
                    QApplication.processEvents()
            """
            
            if show_progress:
                self.progress_bar.setVisible(False)
                
        finally:
            # Sempre reativa as atualizações
            self.table_widget.setUpdatesEnabled(True)
        
        # CONFIGURAÇÃO DE LARGURAS DAS COLUNAS DINÂMICA (do JSON)
        column_widths = GUI_PREFERENCES.get("column_widths", {})
        stretch_columns = GUI_PREFERENCES.get("stretch_columns", [])
        
        # Aplica larguras configuradas no JSON
        for i, col_name in enumerate(df_display.columns):
            # Verifica primeiro por nome exato, depois por alternativas
            width = column_widths.get(col_name)
            if width is None:
                # Tenta alternativas comuns
                if col_name == 'Número da SSA':
                    width = column_widths.get('numero_ssa', 85)
                elif col_name == 'Semana de Cadastro':
                    width = column_widths.get('semana_cadastro', 65)
                elif col_name == 'Descrição Execução':
                    width = column_widths.get('descricao_execucao', 130)
                else:
                    width = 100  # Largura padrão
            
            self.table_widget.setColumnWidth(i, width)
        
        # Configura modo de resize para colunas que devem crescer
        for stretch_col in stretch_columns:
            if stretch_col in df_display.columns:
                stretch_idx = list(df_display.columns).index(stretch_col)
                self.table_widget.horizontalHeader().setSectionResizeMode(
                    stretch_idx, QHeaderView.ResizeMode.Stretch
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

    def show_row_details(self, row: int, column: int):
        """Mostra uma janela com todos os detalhes da SSA selecionada."""
        if row < 0 or row >= len(self.df_exibido):
            return
            
        # Obtém todos os dados da linha (do dataset completo, não apenas exibido)
        ssa_data = self.df_exibido.iloc[row]
        
        # Cria o diálogo de detalhes
        details_dialog = QDialog(self)
        details_dialog.setWindowTitle(f"Detalhes da SSA - {ssa_data.get('numero_ssa', 'N/A')}")
        details_dialog.setFixedSize(700, 600)
        
        layout = QVBoxLayout()
        
        # Título
        title = QLabel(f"📋 SSA #{ssa_data.get('numero_ssa', 'N/A')} - {ssa_data.get('situacao', 'N/A')}")
        title.setFont(self._bold_font(12))
        layout.addWidget(title)
        
        # Conteúdo detalhado
        content = QTextEdit()
        content.setReadOnly(True)
        
        # Monta o HTML com todos os dados
        html_content = "<table border='1' cellpadding='5' cellspacing='0' width='100%'>"
        
        for col_name, value in ssa_data.items():
            if pd.notna(value):
                display_name = self.get_display_name(col_name)
                display_value = self._format_value(col_name, value)
                    
                html_content += f"""
                <tr>
                    <td width='30%'><b>{display_name}:</b></td>
                    <td width='70%'>{display_value}</td>
                </tr>
                """
        
        html_content += "</table>"
        content.setHtml(html_content)
        layout.addWidget(content)
        
        # Botões
        button_layout = QHBoxLayout()
        
        # Botão copiar todos os dados
        copy_all_button = QPushButton("Copiar Todos os Dados")
        copy_all_button.clicked.connect(lambda: self.copy_all_ssa_data(ssa_data))
        button_layout.addWidget(copy_all_button)
        
        # Botão fechar
        close_button = QPushButton("Fechar")
        close_button.clicked.connect(details_dialog.accept)
        button_layout.addWidget(close_button)
        
        layout.addLayout(button_layout)
        details_dialog.setLayout(layout)
        details_dialog.exec()
    
    def copy_all_ssa_data(self, ssa_data):
        """Copia todos os dados da SSA para a área de transferência."""
        data_text = ""
        for col_name, value in ssa_data.items():
            if pd.notna(value):
                display_name = self.get_display_name(col_name)
                display_value = self._format_value(col_name, value)
                data_text += f"{display_name}: {display_value}\n"
        
        clipboard = QApplication.clipboard()
        clipboard.setText(data_text)
        self.status_label.setText("Status: Todos os dados da SSA copiados para área de transferência.")

# --- Ponto de Entrada da Aplicacao ---
if __name__ == '__main__':
    # Cria a aplicacao Qt
    app = QApplication(sys.argv)
    
    # Cria e mostra a janela principal
    window = SSAMainWindow()
    window.show()
    
    # Inicia o loop de eventos da aplicacao
    sys.exit(app.exec())
