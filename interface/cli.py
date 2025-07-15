# interface/cli.py
import os
import sys
import pandas as pd

# Adiciona a raiz do projeto para encontrar outros módulos
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(project_root)

from armazenamento.database import query_db

def start_cli_loop(db_path: str, table_name: str):
    """Inicia o loop principal da interface de linha de comando."""
    
    print("\n--- Consulta Rápida de SSAs ---")
    print("Digite os termos de pesquisa separados por vírgula.")
    print("Exemplo: 'ruído, vazamento, SVP-07'")
    print("Digite 'sair' para terminar.")
    
    while True:
        # Pede a entrada do usuário
        user_input = input("\nPesquisar: ")
        
        if user_input.lower() == 'sair':
            print("Saindo...")
            break
            
        # Separa os termos pela vírgula e remove espaços extras
        search_terms = [term.strip() for term in user_input.split(',') if term.strip()]
        
        # Executa a consulta
        results_df = query_db(db_path, table_name, search_terms)
        
        # Exibe os resultados
        if not results_df.empty:
            print(f"\nEncontrados {len(results_df)} resultados:")
            # Configura o pandas para mostrar todas as linhas/colunas se o resultado for pequeno
            with pd.option_context('display.max_rows', None, 'display.max_columns', None, 'display.width', 1000):
                print(results_df)
        else:
            print("Nenhum resultado encontrado para os termos informados.")
