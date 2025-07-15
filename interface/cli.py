# interface/cli.py (versão 3)
import os
import sys
import pandas as pd
import json

# Adiciona a raiz do projeto para encontrar outros módulos
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(project_root)

from armazenamento.database import query_db
from interface.display import pretty_print_df # <-- IMPORTA NOSSA NOVA FUNÇÃO

def _load_display_mappings():
    """Carrega os mapeamentos de nomes de coluna para exibição."""
    path = os.path.join('config', 'display_mappings.json')
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        print(f"AVISO: Não foi possível carregar o mapa de exibição de '{path}'.")
        return {}


def filter_dataframe(df: pd.DataFrame, search_terms: list) -> pd.DataFrame:
    # (Esta função permanece exatamente a mesma da versão anterior)
    final_mask = pd.Series(True, index=df.index)
    string_columns = df.select_dtypes(include=[object]).columns
    for term in search_terms:
        term_mask = df[string_columns].apply(
            lambda col: col.str.contains(term, case=False, na=False)
        ).any(axis=1)
        final_mask &= term_mask
    return df[final_mask]


def start_cli_loop(db_path: str, table_name: str):
    """Inicia o loop principal da interface de linha de comando."""
    
    print("\n--- Consulta Rápida de SSAs (v3) ---")
    
    display_map = _load_display_mappings()
    initial_df = query_db(db_path, table_name, [])

    if initial_df.empty:
        print("A base de dados está vazia. Execute um importador primeiro.")
        return
        
    results_stack = [initial_df]
    
    while True:
        current_results = results_stack[-1]
        
        # O banner de ajuda agora está integrado ao prompt
        prompt = (f"\nFiltrando sobre {len(current_results)} resultados | "
                  f"Comandos: [voltar], [resetar], [ajuda], [sair]\n"
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
        elif user_input.lower() == 'ajuda':
            print("\n- Digite termos separados por vírgula para filtrar os resultados atuais.")
            print("- 'voltar': Desfaz o último filtro.")
            print("- 'resetar': Limpa todos os filtros e volta ao conjunto de dados completo.")
            print("- 'sair': Encerra o programa.")
            continue
        else:
            search_terms = [term.strip() for term in user_input.split(',') if term.strip()]
            if not search_terms:
                print("Nenhum termo de pesquisa inserido.")
                continue
            new_filtered_df = filter_dataframe(current_results, search_terms)
            results_stack.append(new_filtered_df)

        final_results = results_stack[-1]
        print(f"\nExibindo {len(final_results)} de {len(initial_df)} registros totais:")
        
        # MUDANÇA PRINCIPAL: Usa nossa nova função para imprimir a tabela!
        pretty_print_df(final_results, display_map)