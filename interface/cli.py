# interface/cli.py (versão 5 - ordenação por índice)
import os
import sys
import pandas as pd
import json

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(project_root)

from armazenamento.database import query_db
from interface.display import pretty_print_df

def _load_mappings(file_name: str) -> dict:
    # (Esta função permanece a mesma)
    path = os.path.join('config', file_name)
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
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
    print("\n--- Consulta Rápida de SSAs (v3.2) ---")
    
    display_map = _load_mappings('display_mappings.json')
    initial_df = query_db(db_path, table_name, [])
    if initial_df.empty:
        print("A base de dados está vazia.")
        return
        
    results_stack = [initial_df]
    
    while True:
        current_results = results_stack[-1]
        
        prompt = (f"\nFiltrando sobre {len(current_results)} resultados | "
                  f"Comandos: [Nº col [i|d]], [voltar], [resetar], [sair]\n" # <-- Novo banner de ajuda
                  f"Pesquisar: ")
        
        user_input = input(prompt)
        
        # --- LÓGICA DE COMANDOS REATORADA ---
        parts = user_input.lower().split()
        if not parts: continue # Ignora entrada vazia

        command = parts[0]
        
        if command == 'sair':
            print("Saindo...")
            break
        elif command == 'voltar':
            if len(results_stack) > 1: results_stack.pop(); print("...filtro anterior restaurado.")
            else: print("Não há filtros anteriores para voltar.")
        elif command == 'resetar':
            results_stack = [initial_df]; print("...todos os filtros foram removidos.")
        elif command.isdigit(): # <-- NOVO COMANDO DE ORDENAÇÃO
            try:
                # O usuário vê o índice a partir de 1, o pandas usa a partir de 0
                col_index = int(command) - 1
                
                # O DataFrame para ordenar inclui a coluna '#' adicionada na exibição
                # Portanto, o número de colunas é len(current_results.columns) + 1
                if 0 <= col_index < (len(current_results.columns) + 1):
                    # O nome da coluna a ser ordenada é pego do DataFrame *antes* de adicionar '#'
                    # Se o índice for 0, usamos '#'
                    col_to_sort = '#' if col_index == 0 else current_results.columns[col_index - 1]

                    ascending = True
                    if len(parts) > 1 and parts[1].startswith('i'):
                        ascending = False
                    
                    sorted_df = current_results.sort_values(by=col_to_sort, ascending=ascending, na_position='last')
                    results_stack[-1] = sorted_df
                    print(f"Resultados ordenados pela coluna {command}.")
                else:
                    print(f"Erro: Índice de coluna '{command}' inválido.")
            except (ValueError, IndexError):
                print("Erro de formato. Use: <Nº da coluna> [i|d]")
        else: # Lógica de filtragem padrão
            search_terms = [term.strip() for term in user_input.split(',') if term.strip()]
            new_filtered_df = filter_dataframe(current_results, search_terms)
            results_stack.append(new_filtered_df)

        final_results = results_stack[-1]
        
        print(f"\nExibindo {len(final_results)} de {len(initial_df)} registros totais:")
        pretty_print_df(final_results, display_map)