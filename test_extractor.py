# test_extractor.py (versão 2 - agora um importador completo)
import os
import sys

# Garante que os módulos do projeto sejam encontrados
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.append(project_root)

from extracao.extractor import read_report
from armazenamento.database import save_to_db # <-- Importa a nova função

# --- Configurações ---
DOCS_DIR = 'docs'
REPORT_FILE = 'IEE3_Emissor__202401_20250715_Todas as SSAs - 15-07-2025_1033AM.xlsx'
DB_PATH = os.path.join('data', 'ssas.db')
TABLE_NAME = 'ssa'

# --- Execução ---
print("--- Iniciando processo de importação de relatório ---")

# Passo 1: Extração
report_path = os.path.join(DOCS_DIR, REPORT_FILE)
dataframe, columns = read_report(report_path)

# Passo 2: Carregamento (se a extração funcionou)
if dataframe is not None:
    print("\n--- Iniciando carregamento para o banco de dados ---")
    
    # Apenas as colunas que definimos no nosso BD de teste
    # Isso garante que mesmo relatórios com mais colunas não quebrem a importação
    colunas_desejadas = [
        "Número da SSA", "Localização", "Setor Emissor", 
        "Setor Executor", "Descrição da SSA", "Descrição Execução"
    ]
    
    # Filtra o dataframe para ter apenas as colunas que existem no BD
    # e que também estão no relatório lido.
    colunas_para_salvar = [col for col in colunas_desejadas if col in dataframe.columns]
    df_filtrado = dataframe[colunas_para_salvar]

    save_to_db(df_filtrado, TABLE_NAME, DB_PATH)
else:
    print("Processo de importação falhou na fase de extração.")

print("\n--- Processo de importação finalizado ---")
