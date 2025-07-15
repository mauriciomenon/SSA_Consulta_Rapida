# interface/cli.py (versão FINAL ESTÁVEL)
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
        return {}

def filter_dataframe(df: pd.DataFrame, search_terms: list) -> pd.DataFrame:
    """Filtra um DataFrame em memória com base em uma lista de termos de pesquisa."""
    if not search_terms:
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
    """Imprime a mensagem de ajuda detalhada."""
    print("\n" + "="*40 + "\nAJUDA DE COMANDOS\n" + "="*40)
    print("O uso principal é digitar termos para filtrar os dados.")
    print("  Exemplo de busca simples: 'svp'")
    print("  Exemplo de busca múltipla: 'cisco, painel'\n")
    print("Comandos especiais:")
    print("  -v, voltar    : Desfaz o último filtro.")
    print("  -r, resetar   : Limpa todos os filtros.")
    print("  -ord <N>      : Ordena pela coluna Nº (crescente).")
    print("  -ordi <N>     : Ordena pela coluna Nº (inversa).")
    print("  -h, ajuda     : Exibe esta ajuda.")
    print("  -s, sair      : Encerra o programa.")
    print("="*40)

def start_cli_loop(db_path: str, table_name: str):
    """Inicia o loop principal da interface de linha de comando."""
    display_map = _load_mappings('display_mappings.json')
    try:
        initial_df = query_db(db_path, table_name, [])
        if initial_df.empty:
            print("A base de dados está vazia ou não foi encontrada."); return
    except Exception as e:
        print(f"Erro fatal ao carregar o banco de dados: {e}"); return
        
    results_stack = [initial_df]
    
    print("\n--- Consulta Rápida de SSAs (v5.3 - Final Estável) ---")
    print(f"Banco de dados carregado com {len(initial_df)} SSAs.")
    print("Digite termos para pesquisar ou '-h' para ajuda.")
    
    while True:
        current_results = results_stack[-1]
        
        # --- PROMPT FINAL E CONSISTENTE ---
        prompt = (f"\nFiltrando {len(current_results)} SSAs | "
                  f"Ajuda: -v(voltar), -r(reset), -ord N(ord), -h(ajuda), -s(sair)\n"
                  f"Pesquisar: ")
        
        user_input = input(prompt).strip()
        if not user_input: continue
        
        parts = user_input.lower().split()
        command = parts[0]
        
        # Lógica de ação -> exibição
        action_taken = False
        
        if command in ['-s', 'sair']:
            print("Saindo..."); break
        elif command in ['-v', 'voltar']:
            if len(results_stack) > 1:
                results_stack.pop()
                print("...filtro anterior restaurado.")
                action_taken = True
            else:
                print("Não há filtros para voltar.")
        elif command in ['-r', 'resetar']:
            results_stack = [initial_df]
            print("...todos os filtros foram removidos.")
            action_taken = True
        elif command in ['-h', 'ajuda']:
            print_help()
        elif command in ['-ord', '-ordi']:
            try:
                if len(parts) < 2 or not parts[1].isdigit():
                    print("Erro: use -ord <Nº> ou -ordi <Nº>."); continue
                
                col_index = int(parts[1])
                ascending = (command == '-ord')

                if col_index == 1:
                    sorted_df = current_results.sort_index(ascending=ascending)
                elif 2 <= col_index <= len(current_results.columns) + 1:
                    col_to_sort = current_results.columns[col_index - 2]
                    sorted_df = current_results.sort_values(by=col_to_sort, ascending=ascending, na_position='last')
                else:
                    print(f"Erro: Índice de coluna '{col_index}' inválido."); continue
                
                results_stack[-1] = sorted_df
                print(f"Resultados ordenados pela coluna {col_index}.")
                action_taken = True
            except Exception as e:
                print(f"Erro ao ordenar: {e}")
        else: 
            search_terms = [term.strip() for term in user_input.split(',')]
            new_filtered_df = filter_dataframe(current_results, search_terms)
            results_stack.append(new_filtered_df)
            action_taken = True

        if action_taken:
            final_results = results_stack[-1]
            pretty_print_df(final_results, display_map)