# interface/cli.py (v7.1 - Correção de Import e Lógica)
import os
import sys
import pandas as pd
import json # CORREÇÃO: Import que estava faltando foi adicionado.

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(project_root)

from armazenamento.database import query_db
# Lógica de negócio agora vem do 'core'
from core.app_logic import filter_dataframe, run_importer_logic
from interface.display import pretty_print_df, pretty_print_details
from exportacao.exporter import export_dataframe

def _load_mappings(file_name: str) -> dict:
    path = os.path.join('config', file_name)
    try:
        with open(path, 'r', encoding='utf-8') as f: return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError): 
        # Usando exceptions mais específicas para melhor depuração
        return {}

def print_help():
    print("\n" + "="*50 + "\nAJUDA DE COMANDOS\n" + "="*50)
    print("O uso principal é digitar termos para filtrar os dados.\n")
    print("Comandos especiais:")
    print("  -d <N>            : Mostra os DETALHES completos da SSA na linha N.")
    print("  -e <nome_arquivo> : EXPORTA os resultados atuais para CSV, Excel e JSON.")
    print("  -rescan           : Força uma nova verificação da pasta de relatórios.")
    print("  -v, voltar        : Desfaz o último filtro.")
    print("  -r, resetar       : Limpa todos os filtros.")
    print("  -ord <N>          : ORDENA pela coluna Nº (crescente).")
    print("  -ordi <N>         : ORDENA pela coluna Nº (inversa).")
    print("  -h, ajuda         : Exibe esta ajuda.")
    print("  -s, sair          : Encerra o programa.")
    print("="*50)

def start_cli_loop(db_path: str, table_name: str, output_dir: str):
    display_map = _load_mappings('display_mappings.json')
    try:
        initial_df = query_db(db_path, table_name)
        if initial_df.empty:
            print("A base de dados está vazia. Coloque relatórios na pasta 'docs_entrada' e reinicie."); return
    except Exception as e:
        print(f"Erro fatal ao carregar o banco de dados: {e}"); return
        
    results_stack = [initial_df]
    
    print(f"\n--- Consulta Rápida de SSAs (v13.1 - Estável) ---")
    print(f"Banco de dados carregado com {len(initial_df)} SSAs.")
    print("Digite termos para pesquisar ou '-h' para ajuda.")
    
    VALID_COMMANDS = ['-d', '-detalhe', '-e', '-exportar', '-rescan', '-s', 'sair', 'exit', 'quit', '-h', 'ajuda', '-v', 'voltar', '-r', 'resetar', '-ord', '-ordi']

    while True:
        current_results = results_stack[-1]
        prompt = (f"\nFiltrando {len(current_results)} SSAs | "
                  f"Ajuda: -d(etalhe), -r(eset), -e(xportar), -h(ajuda), -s(air)\n"
                  f"Pesquisar: ")
        
        try: user_input = input(prompt).strip()
        except KeyboardInterrupt: print("\nSaindo..."); break
        if not user_input: continue
        
        parts = user_input.lower().split()
        command = parts[0]
        
        if command in VALID_COMMANDS:
            if command in ['-s', 'sair', 'exit', 'quit']:
                print("Saindo..."); break
            elif command in ['-h', 'ajuda']:
                print_help()
            elif command in ['-rescan']:
                print("Forçando reanálise dos relatórios...")
                if run_importer_logic('docs_entrada', 'data', db_path, table_name, force_rescan=True):
                    print("Base de dados atualizada. Recarregando...")
                    initial_df = query_db(db_path, table_name)
                    results_stack = [initial_df]
                    pretty_print_df(results_stack[-1], display_map)
                else:
                    print("Nenhuma alteração detectada.")
            elif command in ['-d', '-detalhe']:
                try:
                    if len(parts) < 2 or not parts[1].isdigit(): print("Erro: use -d <Nº da linha>."); continue
                    row_index = int(parts[1]) - 1
                    if 0 <= row_index < len(current_results):
                        pretty_print_details(current_results.iloc[row_index], display_map)
                    else: print("Erro: Número da linha inválido.")
                except Exception as e: print(f"Erro ao exibir detalhes: {e}")
            elif command in ['-e', '-exportar']:
                if len(parts) < 2: print("Erro: Forneça um nome para os arquivos. Ex: -e meu_relatorio"); continue
                base_filename = parts[1]
                print(f"\nIniciando exportação para arquivos com base '{base_filename}'...")
                export_dataframe(current_results, base_filename, output_dir, display_map)
            elif command in ['-v', 'voltar']:
                if len(results_stack) > 1:
                    results_stack.pop()
                    print("...filtro anterior restaurado.")
                    pretty_print_df(results_stack[-1], display_map)
                else: print("Não há filtros para voltar.")
            elif command in ['-r', 'resetar']:
                results_stack = [initial_df]
                print("...todos os filtros foram removidos.")
            elif command in ['-ord', '-ordi']:
                # CORREÇÃO: Lógica de ordenação completa restaurada.
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
            if new_filtered_df.empty:
                print("Nenhum resultado encontrado para o filtro. Voltando ao anterior.")
            else:
                results_stack.append(new_filtered_df)
                pretty_print_df(new_filtered_df, display_map)
