# interface/cli.py (versão 4 - com ordenação)
import os
import sys
import pandas as pd
import json

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(project_root)

from armazenamento.database import query_db
from interface.display import pretty_print_df

def _load_mappings(file_name: str) -> dict:
    """Carrega um arquivo de mapeamento JSON da pasta de configuração."""
    path = os.path.join('config', file_name)
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        print(f"AVISO: Não foi possível carregar o mapa de '{path}'.")
        return {}

def filter_dataframe(df: pd.DataFrame, search_terms: list) -> pd.DataFrame:
    # (Esta função permanece a mesma)
    final_mask = pd.Series(True, index=df.index)
    string_columns = df.select_dtypes(include=[object]).columns
    for term in search_terms:
        term_mask = df[string_columns].apply(
            lambda col: col.str.contains(term, case=False, na=False)
        ).any(axis=1)
        final_mask &= term_mask
    return df[final_mask]

def start_cli_loop(db_path: str, table_name: str):
    print("\n--- Consulta Rápida de SSAs (v3.1) ---")
    
    display_map = _load_mappings('display_mappings.json')
    # Inverte o mapa para encontrar o nome interno a partir do nome de exibição
    internal_name_map = {v: k for k, v in display_map.items()}

    initial_df = query_db(db_path, table_name, [])
    if initial_df.empty:
        print("A base de dados está vazia.")
        return
        
    results_stack = [initial_df]
    
    while True:
        current_results = results_stack[-1]
        
        prompt = (f"\nFiltrando sobre {len(current_results)} resultados | "
                  f"Comandos: [ordenar <col>], [voltar], [resetar], [sair]\n"
                  f"Pesquisar: ")
        
        user_input = input(prompt)
        
        if user_input.lower() == 'sair':
            print("Saindo...")
            break
        elif user_input.lower() == 'voltar':
            if len(results_stack) > 1:
                results_stack.pop()
                print("...filtro anterior restaurado.")
            else:
                print("Não há filtros anteriores para voltar.")
        elif user_input.lower() == 'resetar':
            results_stack = [initial_df]
            print("...todos os filtros foram removidos.")
        elif user_input.lower().startswith('ordenar'):
            # --- NOVA LÓGICA DE ORDENAÇÃO ---
            parts = user_input.split()
            if len(parts) < 2:
                print("Erro: use 'ordenar <nome_da_coluna> [asc|desc]'.")
                continue
            
            col_display_name = parts[1]
            # Mapeia o nome de exibição de volta para o nome interno (canônico)
            col_internal_name = internal_name_map.get(col_display_name)

            if col_display_name == '#' : # Permite ordenar pelo índice de exibição
                col_internal_name = '#' # Tratamento especial
            
            if not col_internal_name:
                print(f"Erro: Coluna '{col_display_name}' não encontrada.")
                continue

            order = 'asc'
            if len(parts) > 2 and parts[2].lower() == 'desc':
                order = 'desc'
            
            # Ordena o DataFrame atual
            sorted_df = current_results.sort_values(
                by=col_internal_name,
                ascending=(order == 'asc'),
                na_position='last' # Coloca valores nulos no final
            )
            results_stack[-1] = sorted_df # Substitui o resultado atual pelo ordenado
            print(f"Resultados ordenados por '{col_display_name}' em ordem {order.upper()}.")

        else: # Lógica de filtragem
            search_terms = [term.strip() for term in user_input.split(',') if term.strip()]
            if not search_terms:
                continue
            new_filtered_df = filter_dataframe(current_results, search_terms)
            results_stack.append(new_filtered_df)

        final_results = results_stack[-1]
        
        print(f"\nExibindo {len(final_results)} de {len(initial_df)} registros totais:")
        pretty_print_df(final_results, display_map)