# main.py (versão 3 - com verificação de estrutura)
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
DATA_DIR = 'data'
CONFIG_DIR = 'config' # Nova pasta para a V3
DB_PATH = os.path.join(DATA_DIR, 'ssas.db')
TABLE_NAME = 'ssa'
COLUNAS_FINAIS = [
    "Número da SSA", "Localização", "Setor Emissor", 
    "Setor Executor", "Descrição da SSA", "Descrição Execução"
]

def ensure_project_structure():
    """Verifica se as pastas essenciais existem e oferece para criá-las."""
    print("Verificando estrutura de pastas do projeto...")
    required_dirs = [DOCS_DIR, DATA_DIR, CONFIG_DIR]
    all_ok = True
    for directory in required_dirs:
        if not os.path.exists(directory):
            print(f"AVISO: A pasta necessária '{directory}' não foi encontrada.")
            answer = input(f"Deseja criá-la agora? [S/n]: ")
            if answer.lower().strip() == 'n':
                all_ok = False
                break
            else:
                os.makedirs(directory)
                print(f"Pasta '{directory}' criada.")
    
    if not all_ok:
        print("Estrutura de pastas necessária ausente. O programa não pode continuar.")
        sys.exit() # Encerra o programa se o usuário recusar a criação
    print("Estrutura de pastas OK.")


def run_importer():
    """
    Verifica a pasta /docs por relatórios .xlsx e oferece a importação.
    Combina dados de múltiplos relatórios, remove duplicatas e salva no BD.
    """
    # (O código desta função permanece o mesmo da última versão)
    report_files = glob.glob(os.path.join(DOCS_DIR, '*.xlsx'))
    
    if not report_files:
        print("\nNenhum relatório (.xlsx) encontrado na pasta /docs para importar.")
        return

    print(f"\nForam encontrados {len(report_files)} relatórios na pasta /docs.")
    answer = input("Deseja importá-los agora? (Isso substituirá os dados existentes) [S/n]: ")

    if answer.lower().strip() == 'n':
        print("Importação pulada pelo usuário.")
        return

    all_dataframes = []
    print("\nIniciando processo de importação...")
    for file in report_files:
        if not os.path.basename(file).startswith('~$'):
            df, _ = read_report(file)
            if df is not None:
                all_dataframes.append(df)
            
    if not all_dataframes:
        print("Nenhum dado pôde ser extraído dos relatórios.")
        return

    print("Combinando dados de todos os relatórios...")
    combined_df = pd.concat(all_dataframes, ignore_index=True)
    
    colunas_para_salvar = [col for col in COLUNAS_FINAIS if col in combined_df.columns]
    
    final_df = combined_df[colunas_para_salvar].copy()

    if "Número da SSA" in final_df.columns:
        linhas_antes = len(final_df)
        final_df = final_df.drop_duplicates(subset=["Número da SSA"], keep='last')
        linhas_depois = len(final_df)
        if linhas_antes > linhas_depois:
            print(f"Removidas {linhas_antes - linhas_depois} SSAs duplicadas.")

    save_to_db(final_df, TABLE_NAME, DB_PATH)


def main():
    """Função principal que orquestra a aplicação."""
    print("--- Iniciando SSA Consulta Rápida ---")
    
    # 1. Garante que a estrutura de pastas exista
    ensure_project_structure()
    
    # 2. Executa a rotina de importação
    run_importer()
    
    # 3. Inicia a interface de consulta interativa
    start_cli_loop(db_path=DB_PATH, table_name=TABLE_NAME)


if __name__ == "__main__":
    main()