# gui/workers/data_loader_worker.py
# Worker thread for loading data from database asynchronously

import pandas as pd
from PyQt6.QtCore import QThread, pyqtSignal
from armazenamento.database import query_db


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
            # Use SELECT * para schema dinamico
            # O schema pode variar dependendo dos arquivos importados
            # Garantimos que todas as colunas disponiveis sejam carregadas
            query = 'SELECT * FROM ssa_table'

            df = query_db(self.db_path, '', query)
            if not df.empty:
                self.data_loaded.emit(df)
            else:
                self.error_occurred.emit("Falha ao carregar dados do banco.")
        except Exception as e:
            self.error_occurred.emit(f"Erro ao carregar dados: {e}")
