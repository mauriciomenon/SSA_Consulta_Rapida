# interface/cli.py (v5.0 - Arquitetura e Exportacao Refatoradas)
import os
import sys
import pandas as pd
import json

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(project_root)

from armazenamento.database import query_db
from interface.display import pretty_print_df
from exportacao.exporter import export_dataframe

def _load_mappings(file_name: str) -> dict:
    path = os.path.join('config', file_name)
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

def filter_dataframe(df: pd.DataFrame, search_terms: list) -> pd.DataFrame:
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

def print_help():
    print("\n" + "="*50 + "\nAJUDA DE COMANDOS\n" + "="*50)
    print("O uso principal é digitar termos para filtrar os dados.")
    print("  Exemplo de busca: 'cisco, painel'\n")
    print("Comandos especiais:")
    print("  -e <nome_arquivo> : Exporta os resultados para CSV, Excel e JSON.")
    print("                      (Ex: -e meu_relatorio)")
    print("  -v, voltar        : Desfaz o último filtro.")
    print("  -r, resetar       : Limpa todos os filtros.")
    print("  -ord <N>          : Ordena pela coluna Nº (crescente).")
    print("  -ordi <N>         : Ordena pela coluna Nº (inversa).")
    print("  -h, ajuda         : Exibe esta ajuda.")
    print("  -s, sair          : Encerra o programa.")
    print("="*50)

def start_cli_loop(db_path: str, table_name: str, output_dir: str):
    display_map = _load_mappings('display_mappings.json')
    try:
        initial_df = query_db(db_path, table_name)
        if initial_df.empty:
            print("A base de dados está vazia ou não foi encontrada."); return
    except Exception as e:
        print(f"Erro fatal ao carregar o banco de dados: {e}"); return
        
    results_stack = [initial_df]
    
    print(f"\n--- Consulta Rápida de SSAs (v10.0 - Final) ---")
    print(f"Banco de dados carregado com {len(initial_df)} SSAs.")
    print("Digite termos para pesquisar ou '-h' para ajuda.")
    
    VALID_COMMANDS = ['-e', '-exportar', '-s', 'sair', '-h', 'ajuda', '-v', 'voltar', '-r', 'resetar', '-ord', '-ordi']

    while True:
        current_results = results_stack[-1]
        
        prompt = (f"\nFiltrando {len(current_results)} SSAs | "
                  f"Ajuda: -v(voltar), -r(reset), -e(exportar), -h(ajuda), -s(sair)\n"
                  f"Pesquisar: ")
        
        try:
            user_input = input(prompt).strip()
        except KeyboardInterrupt:
            print("\nSaindo..."); break
            
        if not user_input: continue
        
        parts = user_input.lower().split()
        command = parts[0]
        
        if command in VALID_COMMANDS:
            if command in ['-s', 'sair']:
                print("Saindo..."); break
            elif command in ['-h', 'ajuda']:
                print_help()
            elif command in ['-e', '-exportar']:
                if len(parts) < 2:
                    print("Erro: Forneça um nome base para os arquivos. Ex: -e meu_relatorio")
                    continue
                base_filename = parts[1]
                print(f"\nIniciando exportação para arquivos com base '{base_filename}'...")
                export_dataframe(current_results, base_filename, output_dir, display_map)
            elif command in ['-v', 'voltar']:
                if len(results_stack) > 1:
                    results_stack.pop()
                    print("...filtro anterior restaurado.")
                    pretty_print_df(results_stack[-1], display_map)
                else:
                    print("Não há filtros para voltar.")
            elif command in ['-r', 'resetar']:
                results_stack = [initial_df]
                print("...todos os filtros foram removidos.")
            elif command in ['-ord', '-ordi']:
                try:
                    if len(parts) < 2 or not parts[1].isdigit():
                        print("Erro: use -ord <Nº> ou -ordi <Nº>."); continue
                    col_index = int(parts[1])
                    ascending = (command == '-ord')
                    temp_display_df = current_results[[col for col in display_map.keys() if col in current_results.columns]]
                    if col_index == 1:
                        sorted_df = current_results.sort_index(ascending=ascending)
                    elif 2 <= col_index <= len(temp_display_df.columns) + 1:
                        col_to_sort = temp_display_df.columns[col_index - 2]
                        sorted_df = current_results.sort_values(by=col_to_sort, ascending=ascending, na_position='last')
                    else:
                        print(f"Erro: Índice de coluna '{col_index}' inválido."); continue
                    results_stack[-1] = sorted_df
                    print(f"Resultados ordenados pela coluna {col_index}.")
                    pretty_print_df(sorted_df, display_map)
                except Exception as e:
                    print(f"Erro ao ordenar: {e}")
        else: 
            search_terms = [term.strip() for term in user_input.split(',')]
            new_filtered_df = filter_dataframe(current_results, search_terms)
            results_stack.append(new_filtered_df)
            pretty_print_df(new_filtered_df, display_map)
