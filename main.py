# main.py (v7.0 - Arquitetura de Pastas Refatorada)
import os
import sys
import glob
import pandas as pd

project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.append(project_root)

from extracao.extractor import read_report
from armazenamento.database import save_to_db
from interface.cli import start_cli_loop
from utils.caching import load_cache, save_cache, get_files_to_process, _calculate_hash

# --- Configurações com Nomenclatura Refatorada ---
DOCS_ENTRADA = 'docs_entrada'
DOCS_SAIDA = 'docs_saida'
DATA_DIR = 'data'
CONFIG_DIR = 'config'
DB_PATH = os.path.join(DATA_DIR, 'ssas.db')
TABLE_NAME = 'ssa'

def ensure_project_structure():
    """Verifica e cria a estrutura de pastas do projeto."""
    required_dirs = [DOCS_ENTRADA, DOCS_SAIDA, DATA_DIR, CONFIG_DIR, 'utils']
    for directory in required_dirs:
        if not os.path.exists(directory):
            print(f"AVISO: Pasta '{directory}' não encontrada. Criando...")
            os.makedirs(directory)
    
    for pkg_dir in ['utils', 'exportacao', 'armazenamento', 'config', 'extracao', 'interface']:
        init_path = os.path.join(pkg_dir, '__init__.py')
        if not os.path.exists(init_path):
            try:
                open(init_path, 'a').close()
            except OSError:
                pass
    print("Estrutura de pastas verificada.")

def run_importer(force_rescan: bool = False):
    """Processa relatórios usando cache."""
    all_report_files = glob.glob(os.path.join(DOCS_ENTRADA, '*.xlsx'))
    if not all_report_files:
        print(f"\nNenhum relatório (.xlsx) encontrado na pasta '{DOCS_ENTRADA}'.")
        return

    current_cache = load_cache(DATA_DIR)

    if force_rescan:
        print("\nOpção '--rescan' ativada. Forçando reanálise de todos os relatórios...")
        files_to_process = all_report_files
    else:
        print("\nVerificando relatórios novos ou modificados...")
        files_to_process = get_files_to_process(DOCS_ENTRADA, current_cache)

    if not files_to_process:
        print("Nenhum relatório novo ou modificado encontrado.")
        return

    print(f"Encontrados {len(files_to_process)} relatórios para importar. Iniciando processo...")
    
    all_dataframes = []
    for file_path in files_to_process:
        if not os.path.basename(file_path).startswith('~$'):
            df, _ = read_report(file_path)
            if df is not None and not df.empty:
                all_dataframes.append(df)
    
    if not all_dataframes and not force_rescan:
        print("Nenhum dado válido foi extraído dos novos relatórios.")
        return

    if not force_rescan and os.path.exists(DB_PATH):
        print("Carregando dados existentes para consolidação...")
        try:
            existing_df = query_db(DB_PATH, TABLE_NAME)
            if not existing_df.empty:
                all_dataframes.append(existing_df)
        except Exception as e:
            print(f"AVISO: Não foi possível carregar dados antigos do DB. Erro: {e}")

    if not all_dataframes:
        print("Nenhum dado para consolidar. Operação abortada.")
        return

    print("Combinando todos os dados...")
    combined_df = pd.concat(all_dataframes, ignore_index=True)
    
    if "numero_ssa" in combined_df.columns:
        combined_df.dropna(subset=['numero_ssa'], inplace=True)
        linhas_antes = len(combined_df)
        final_df = combined_df.drop_duplicates(subset=["numero_ssa"], keep='last')
        linhas_depois = len(final_df)
        if (linhas_antes - linhas_depois) > 0:
            print(f"Removidas {linhas_antes - linhas_depois} SSAs duplicadas.")
    else:
        final_df = combined_df
    
    save_to_db(final_df, TABLE_NAME, DB_PATH)

    print("Atualizando cache de importação...")
    new_cache = {os.path.basename(f): _calculate_hash(f) for f in all_report_files if not os.path.basename(f).startswith('~$')}
    save_cache(DATA_DIR, new_cache)

def main():
    """Função principal que orquestra a aplicação."""
    print("--- Iniciando SSA Consulta Rápida (v10.0 - Final) ---")
    force_rescan = '--rescan' in sys.argv
    ensure_project_structure()
    run_importer(force_rescan=force_rescan)
    start_cli_loop(db_path=DB_PATH, table_name=TABLE_NAME, output_dir=DOCS_SAIDA)

if __name__ == "__main__":
    main()
