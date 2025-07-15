# interface/cli.py (versão 2)
import os
import sys
import pandas as pd
import numpy as np
from typing import List

# Adiciona a raiz do projeto para encontrar outros módulos
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(project_root)

from armazenamento.database import query_db

def filter_dataframe(df: pd.DataFrame, search_terms: List[str]) -> pd.DataFrame:
    """
    Filtra um DataFrame em memória com base em uma lista de termos de pesquisa.
    Aplica uma lógica 'E' entre os termos.
    """
    # Começa com uma máscara que seleciona todas as linhas
    final_mask = pd.Series(True, index=df.index)
    
    # Seleciona apenas colunas do tipo string/object para a busca
    string_columns = df.select_dtypes(include=[object]).columns
    
    for term in search_terms:
        # Para cada termo, cria uma máscara que busca em todas as colunas de texto
        # A busca é case-insensitive (case=False)
        term_mask = df[string_columns].apply(
            lambda col: col.str.contains(term, case=False, na=False)
        ).any(axis=1)
        # Combina a máscara do termo atual com a máscara final usando AND
        final_mask &= term_mask
        
    return df[final_mask]

def start_cli_loop(db_path: str, table_name: str):
    """Inicia o loop principal da CLI, agora com gerenciamento de estado."""
    
    print("\n--- Consulta Rápida de SSAs (v2) ---")
    print("Comandos: [voltar], [resetar], [ajuda], [sair]")
    
    # Carrega todos os dados iniciais do banco para a memória
    initial_df = query_db(db_path, table_name, [])
    if initial_df.empty:
        print("A base de dados está vazia. Execute um importador primeiro.")
        return
        
    # Pilha de resultados para o histórico de filtros
    results_stack = [initial_df]
    
    while True:
        current_results = results_stack[-1]
        prompt = f"\nFiltrando sobre {len(current_results)} resultados | Pesquisar ou comando: "
        user_input = input(prompt)
        
        # --- Lógica de Comandos ---
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
            continue # Pula a exibição de resultados e pede novo input
            
        # --- Lógica de Filtragem ---
        else:
            search_terms = [term.strip() for term in user_input.split(',') if term.strip()]
            if not search_terms:
                print("Nenhum termo de pesquisa inserido.")
                continue

            # Filtra o DataFrame que está no topo da pilha (o resultado atual)
            new_filtered_df = filter_dataframe(current_results, search_terms)
            results_stack.append(new_filtered_df)

        # --- Exibição de Resultados ---
        final_results = results_stack[-1]
        if not final_results.empty:
            print(f"\nExibindo {len(final_results)} de {len(initial_df)} registros totais:")
            with pd.option_context('display.max_rows', None, 'display.max_columns', None, 'display.width', 1000):
                print(final_results)
        else:
            print("Nenhum resultado encontrado para o filtro aplicado.")