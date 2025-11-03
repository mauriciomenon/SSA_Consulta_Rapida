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
            # Query customizada que mapeia os nomes corretos das colunas
            query = '''
            SELECT
                numero_ssa,
                situacao,
                derivada_de,
                localizacao_codigo,
                descricao_localizacao,
                equipamento,
                semana_cadastro,
                data_cadastro,
                descricao_ssa,
                setor_emissor,
                setor_executor,
                solicitante,
                servico_origem,
                grau_prioridade_emissao,
                grau_prioridade_planejamento,
                execucao_simples,
                responsavel_programacao,
                semana_programada,
                responsavel_execucao,
                descricao_execucao,
                id,
                sistema_origem,
                prazo_limite,
                tempo_disponivel,
                data_limite,
                tempo_excedido,
                desde,
                tempo_total,
                desde_1,
                total_tempo_tpe_planejado,
                total_tempo_tex_planejado,
                total_tempo_tpo_planejado,
                total_horas_programadas,
                execucao_parcial,
                anomalia,
                semana_executada,
                num_reprogramacoes
            FROM ssa_table
            '''

            df = query_db(self.db_path, '', query)
            if not df.empty:
                self.data_loaded.emit(df)
            else:
                self.error_occurred.emit("Falha ao carregar dados do banco.")
        except Exception as e:
            self.error_occurred.emit(f"Erro ao carregar dados: {e}")
