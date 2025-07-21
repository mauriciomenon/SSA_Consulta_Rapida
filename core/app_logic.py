# core/app_logic.py (v1.0 - Lógica de Negócio Centralizada)
import os
import pandas as pd

from extracao.extractor import read_report
from armazenamento.database import save_to_db, query_db
from utils.caching import load_cache, save_cache, get_files_to_process, _calculate_hash

def filter_dataframe(df: pd.DataFrame, search_terms: list) -> pd.DataFrame:
    """
    Filtra um DataFrame em memória com base em uma lista de termos de pesquisa.
    (Movido de interface/cli.py)
    """
    if not search_terms or (len(search_terms) == 1 and not search_terms[0]):
        return df
    
    combined_mask = pd.Series(True, index=df.index)
    string_columns = df.select_dtypes(include=['object', 'string']).columns
    
    if string_columns.empty:
        return pd.DataFrame(columns=df.columns)

    for term in search_terms:
        term_mask = df[string_columns].apply(
            lambda col: col.astype(str).str.contains(term, case=False, na=False)
        ).any(axis=1)
        combined_mask &= term_mask
    
    return df[combined_mask]


def run_importer_logic(docs_dir: str, data_dir: str, db_path: str, table_name: str, force_rescan: bool = False) -> bool:
    """
    Lógica principal de importação. Retorna True se novos dados foram importados, False caso contrário.
    (Lógica extraída de main.py)
    """
    all_report_files = [os.path.join(docs_dir, f) for f in os.listdir(docs_dir) if f.endswith('.xlsx') and not f.startswith('~$')]
    if not all_report_files:
        if force_rescan: # Só mostra a mensagem se o usuário pediu um rescan
            print(f"\nNenhum relatório (.xlsx) encontrado na pasta '{docs_dir}'.")
        return False

    current_cache = load_cache(data_dir)
    files_to_process = all_report_files if force_rescan else get_files_to_process(docs_dir, current_cache)

    if not files_to_process:
        print("Nenhum relatório novo ou modificado encontrado.")
        return False

    print(f"\nEncontrados {len(files_to_process)} relatórios para importar. Iniciando processo...")
    
    new_dataframes = [df for file_path in files_to_process if (df := read_report(file_path)[0]) is not None and not df.empty]
    
    if not new_dataframes:
        print("Nenhum dado válido foi extraído dos novos relatórios.")
        return False

    all_dataframes = new_dataframes
    if not force_rescan and os.path.exists(db_path):
        print("Carregando dados existentes para consolidação...")
        try:
            existing_df = query_db(db_path, table_name)
            if not existing_df.empty:
                all_dataframes.append(existing_df)
        except Exception as e:
            print(f"AVISO: Não foi possível carregar dados antigos do DB. Erro: {e}")

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
    
    save_to_db(final_df, table_name, db_path)

    print("Atualizando cache de importação...")
    new_cache = {os.path.basename(f): _calculate_hash(f) for f in all_report_files}
    save_cache(data_dir, new_cache)
    
    return True
