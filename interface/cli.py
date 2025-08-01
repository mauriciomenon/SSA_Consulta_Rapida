# interface/cli.py
import sys
import logging
import pandas as pd
from typing import Dict

# Importações da estrutura do projeto
from utils.pagination import Paginator
from interface.table_printer import format_dataframe_for_cli
from core.app_logic import filter_dataframe
from exportacao.exporter import export_dataframe
from interface.display import pretty_print_details
from core.config_manager import handle_config_command

logger = logging.getLogger(__name__)

def start_cli_loop(initial_df: pd.DataFrame, display_map: Dict[str, str], output_dir: str):
    """
    Inicia o loop principal da interface de linha de comando.
    """
    if initial_df.empty:
        print("A base de dados está vazia. Importe dados primeiro.")
        return

    df_completo = initial_df
    df_filtrado = df_completo.copy()
    
    print(f"--- Consulta Rápida de SSAs ---")
    print(f"Base de dados carregada com {len(df_completo)} registros.")

    while True:
        paginator = Paginator(df_filtrado, page_size=20)
        
        print(f"\nExibindo {len(df_filtrado)} registros.")
        
        if paginator.total_items == 0:
            print("Nenhum resultado encontrado para o filtro atual.")
        else:
            is_paginating = True
            while is_paginating:
                page_df = paginator.get_current_page_data()
                print(format_dataframe_for_cli(page_df, display_map))
                
                if paginator.total_pages <= paginator.current_page:
                    is_paginating = False
                else:
                    prompt = f"\n-- Pág {paginator.current_page}/{paginator.total_pages} | Enter: próxima, 'q': parar --\n> "
                    cmd = input(prompt).strip().lower()
                    if cmd == 'q':
                        is_paginating = False
                    else:
                        paginator.next_page()

        # Prompt de comando principal
        prompt = "\n> Pesquise, ou use comandos (-h para ajuda, -q para sair): "
        user_input = input(prompt).strip()
        parts = user_input.split()
        command = parts[0].lower() if parts else ""

        if not command:
            continue
        
        if command in ['-q', 'sair', 'exit']:
            print("Encerrando...")
            break
        elif command in ['-h', '-help', 'ajuda']:
            # Você pode mover isso para command_handlers se preferir
            print("\n-h: Ajuda | -q: Sair | -r: Resetar Filtro | -e <nome>: Exportar | -c: Config")
        elif command == '-r':
            df_filtrado = df_completo.copy()
            print("Filtro resetado.")
        elif command == '-e':
            if len(parts) > 1:
                filename = parts[1]
                export_dataframe(df_filtrado, filename, output_dir, display_map)
            else:
                print("Uso: -e <nome_base_arquivo>")
        elif command == '-c':
            handle_config_command()
            print("\nConfigurações alteradas. Para ver o efeito, reinicie a busca ou a aplicação.")
        elif command == '-d':
            # Detalhes: esta funcionalidade pode ser adicionada aqui
            print("Funcionalidade de detalhes (-d) a ser implementada.")
        else:
            # Assume que é uma busca
            df_filtrado = filter_dataframe(df_completo, user_input.split(','))