# gui/workers/data_loader_worker.py
# Worker thread for loading data from database asynchronously

import logging

import pandas as pd
from PyQt6.QtCore import QThread, pyqtSignal

from armazenamento.database import query_db

logger = logging.getLogger(__name__)


class DataLoaderWorker(QThread):
    """Thread para carregar dados do banco com suporte a paginação lazy loading."""

    data_loaded = pyqtSignal(pd.DataFrame)
    error_occurred = pyqtSignal(str)

    # Lista branca de colunas permitidas para ORDER BY (previne injeção SQL)
    _ALLOWED_ORDER_COLUMNS = {
        "numero_ssa",
        "situacao",
        "data_cadastro",
        "semana_cadastro",
        "semana_programada",
        "semana_executada",
        "setor_emissor",
        "setor_executor",
        "descricao_ssa",
        "localizacao_codigo",
        "equipamento",
        "solicitante",
        "grau_prioridade_emissao",
        "grau_prioridade_planejamento",
    }

    def __init__(self, db_path, table_name, limit=None, offset=0, order_by=None):
        """
        Inicializa worker de carregamento com suporte a paginação.

        Args:
            db_path: Caminho para o arquivo SQLite
            table_name: Nome da tabela (para compatibilidade, usa ssa_table internamente)
            limit: Quantidade máxima de registros (None = sem limite)
            offset: Quantidade de registros a pular (padrão 0)
            order_by: Cláusula ORDER BY (ex: "numero_ssa DESC")
        """
        super().__init__()
        self.db_path = db_path
        self.table_name = table_name
        self.limit = limit
        self.offset = offset
        self.order_by = order_by

    def _validate_order_by(self, order_by: str) -> bool:
        """
        Valida que order_by contém apenas identificadores SQL permitidos.
        Protege contra injeção SQL via whitelist de colunas.

        Args:
            order_by: String como 'coluna [ASC|DESC]' ou 'coluna1, coluna2'

        Returns:
            True se válido, False caso contrário
        """
        if not order_by:
            return True
        # Extrai nomes de colunas (remove direções ASC/DESC e espaços)
        for part in order_by.split(","):
            col_part = part.strip().split()[0].lower()  # Pega só nome da coluna
            if col_part not in self._ALLOWED_ORDER_COLUMNS:
                logger.warning(f"Coluna ORDER BY não permitida: {col_part}")
                return False
        return True

    def run(self):
        try:
            # NOTA: ssa_table é o nome real da tabela no schema
            # TABLE_NAME="ssas" em gui_ssa.py é uma VIEW que aponta para ssa_table
            query = "SELECT * FROM ssa_table"

            # Valida e adiciona ORDER BY se especificado
            if self.order_by:
                if not self._validate_order_by(self.order_by):
                    raise ValueError(f"ORDER BY inválido: {self.order_by}")
                query += f" ORDER BY {self.order_by}"

            # Adiciona LIMIT e OFFSET para paginação (lazy loading)
            # int() garante que são valores inteiros seguros
            if self.limit is not None:
                query += f" LIMIT {int(self.limit)}"
            if self.offset > 0:
                query += f" OFFSET {int(self.offset)}"

            # query_db(db_path, table_name, query) - table_name usado só se query vazia
            # Como query não está vazia, o segundo parâmetro é ignorado
            df = query_db(self.db_path, "", query)

            if not df.empty:
                self.data_loaded.emit(df)
            else:
                self.error_occurred.emit("Falha ao carregar dados do banco.")
        except Exception as e:
            self.error_occurred.emit(f"Erro ao carregar dados: {e}")
