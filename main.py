# main.py (versão final)
import os
import sys
import glob
import pandas as pd

# Garante que os módulos do projeto sejam encontrados
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.append(project_root)

from extracao.extractor import read_report
from armazenamento.database import save_to_db
from interface.cli import start_cli_loop

# --- Configurações ---
DOCS_DIR = 'docs'
DB_PATH = os.path.join('data', 'ssas.db')
TABLE_NAME = 'ssa'

# Colunas que queremos garantir que existam no nosso banco de dados final.
# O importador irá selecionar apenas estas colunas dos relatórios.
COLUNAS_FINAIS = [
    "Número da SSA", "Localização", "Setor Emissor", 
    "Setor Executor", "Descrição da SSA", "Descrição Execução"
]

def run_importer():
    """
    Verifica a pasta /docs por relatórios .xlsx e oferece a importação.
    Combina dados de múltiplos relatórios, remove duplicatas e salva no BD.
    """
    # Encontra todos os arquivos .xlsx na pasta de documentos
    report_files = glob.glob(os.path.join(DOCS_DIR, '*.xlsx'))
    
    if not report_files:
        print("Nenhum relatório (.xlsx) encontrado na pasta /docs.")
        return

    print(f"Foram encontrados {len(report_files)} relatórios na pasta /docs.")
    # Pergunta ao usuário se deseja importar
    answer = input("Deseja importá-los agora? (Isso substituirá os dados existentes) [S/n]: ")

    # Se a resposta não for 'n' ou 'N', prossegue com a importação
    if answer.lower().strip() == 'n':
        print("Importação pulada pelo usuário.")
        return

    all_dataframes = []
    print("\nIniciando processo de importação...")
    for file in report_files:
        df, _ = read_report(file) # O mapa de colunas não é necessário aqui
        if df is not None:
            all_dataframes.append(df)
            
    if not all_dataframes:
        print("Nenhum dado pôde ser extraído dos relatórios.")
        return

    # Combina todos os DataFrames lidos em um só
    print("Combinando dados de todos os relatórios...")
    combined_df = pd.concat(all_dataframes, ignore_index=True)

    # Garante que apenas as colunas que queremos existam
    colunas_para_salvar = [col for col in COLUNAS_FINAIS if col in combined_df.columns]
    final_df = combined_df[colunas_para_salvar]

    # Remove SSAs duplicadas, mantendo a última ocorrência (a mais recente)
    # Verificamos se a coluna chave existe antes de tentar remover duplicatas
    if "Número da SSA" in final_df.columns:
        linhas_antes = len(final_df)
        final_df.drop_duplicates(subset=["Número da SSA"], keep='last', inplace=True)
        linhas_depois = len(final_df)
        if linhas_antes > linhas_depois:
            print(f"Removidas {linhas_antes - linhas_depois} SSAs duplicadas.")

    # Salva o DataFrame final e limpo no banco de dados
    save_to_db(final_df, TABLE_NAME, DB_PATH)


def main():
    """Função principal que orquestra a aplicação."""
    print("--- Iniciando SSA Consulta Rápida ---")
    
    # 1. Executa a rotina de importação
    run_importer()
    
    # 2. Inicia a interface de consulta interativa
    start_cli_loop(db_path=DB_PATH, table_name=TABLE_NAME)


if __name__ == "__main__":
    main()