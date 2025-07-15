# interface/cli.py (versão 9 - ESTÁVEL E À PROVA DE FALHAS)
import os
import sys
import pandas as pd
import json

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(project_root)

from armazenamento.database import query_db
from interface.display import pretty_print_df

def _load_mappings(file_name: str) -> dict:
    path = os.path.join('config', file_name)
    try:
        with open(path, 'r', encoding='utf-8') as f: return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError): return {}

def filter_dataframe(df: pd.DataFrame, search_terms: list) -> pd.DataFrame:
    # --- CORREÇÃO DO ValueError ---
    # Garante que a busca seja feita apenas em colunas de texto
    string_columns = df.select_dtypes(include=['object', 'string']).columns
    if string_columns.empty:
        return pd.DataFrame(columns=df.columns) # Retorna vazio se não houver colunas de texto

    # Aplica o filtro de forma segura
    final_mask = pd.Series(True, index=df.index)
    for term in search_terms:
        term_mask = df[string_columns].apply(lambda col: col.astype(str).str.contains(term, case=False, na=False)).any(axis=1)
        final_mask &= term_mask
    return df[final_mask]

def print_help():
    print("\n" + "="*30 + "\nAJUDA DE COMANDOS\n" + "="*30)
    print("O uso principal é digitar termos de busca para filtrar os dados.")
    print("Exemplo: 'cisco, painel'\n")
    print("Comandos especiais (iniciam com '-'):")
    print("  -v, voltar    : Desfaz o último filtro.")
    print("  -r, resetar   : Limpa todos os filtros e volta à lista completa.")
    print("  -ord <Nº>     : Ordena pela coluna Nº (crescente).")
    print("  -ordi <Nº>    : Ordena pela coluna Nº (inversa).")
    print("  -h, ajuda     : Exibe esta ajuda.")
    print("  -s, sair      : Encerra o programa.")
    print("="*30)

def start_cli_loop(db_path: str, table_name: str):
    display_map = _load_mappings('display_mappings.json')
    initial_df = query_db(db_path, table_name, [])
    if initial_df.empty:
        print("A base de dados está vazia."); return
        
    results_stack = [initial_df]
    
    print("\n--- Consulta Rápida de SSAs (v4.1 - Estável) ---")
    print(f"Banco de dados carregado com {len(initial_df)} SSAs.")
    print("Digite termos para pesquisar ou um comando. Use '-h' para ajuda.")
    
    while True:
        current_results = results_stack[-1]
        
        prompt = (f"\nFiltrando sobre {len(current_results)} SSAs | "
                  f"Comandos: [-v=voltar, -r=reset, -ord <N>=ordenar, -h=ajuda, -s=sair]\n"
                  f"Pesquisar: ")
        
        user_input = input(prompt).strip()
        if not user_input: continue
        
        parts = user_input.lower().split()
        command = parts[0]
        
        # --- LÓGICA DE COMANDOS ---
        if command in ['-s', 'sair']:
            print("Saindo..."); break
        elif command in ['-v', 'voltar']:
            if len(results_stack) > 1: results_stack.pop(); print("...filtro anterior restaurado.")
            else: print("Não há filtros para voltar.")
        elif command in ['-r', 'resetar']:
            results_stack = [initial_df]; print("...todos os filtros foram removidos.")
        elif command in ['-h', 'ajuda']:
            print_help(); continue
        elif command in ['-ord', '-ordi']:
            try:
                if len(parts) < 2 or not parts[1].isdigit():
                    print("Erro: use -ord <Nº da coluna> ou -ordi <Nº da coluna>."); continue
                col_index = int(parts[1])
                ascending = (command == '-ord')

                temp_df_with_index = current_results.copy()
                temp_df_with_index.insert(0, '#', range(1, len(temp_df_with_index) + 1))
                
                if 1 <= col_index <= len(temp_df_with_index.columns):
                    col_to_sort = temp_df_with_index.columns[col_index - 1]
                    if col_to_sort == '#':
                        sorted_df = current_results.sort_index(ascending=ascending)
                    else:
                        sorted_df = current_results.sort_values(by=col_to_sort, ascending=ascending, na_position='last')
                    results_stack[-1] = sorted_df
                    print(f"Resultados ordenados pela coluna {col_index}.")
                else:
                    print(f"Erro: Índice de coluna '{col_index}' inválido."); continue
            except (ValueError, IndexError):
                print("Erro de formato. Use: -ord <Nº da coluna>")
        else: 
            search_terms = [term.strip() for term in user_input.split(',') if term.strip()]
            new_filtered_df = filter_dataframe(current_results, search_terms)
            results_stack.append(new_filtered_df)

        final_results = results_stack[-1]
        print(f"\nExibindo {len(final_results)} de {len(initial_df)} registros totais:")
        pretty_print_df(final_results, display_map)