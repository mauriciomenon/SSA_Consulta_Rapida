# interface/display.py (versão 3 - com larguras de coluna controladas)
import pandas as pd
from tabulate import tabulate
from typing import Dict
import os

def get_terminal_height():
    try:
        return os.get_terminal_size().lines
    except OSError:
        return 25

def pretty_print_df(df: pd.DataFrame, display_map: Dict[str, str]):
    if df.empty:
        print("Nenhum resultado para exibir.")
        return

    display_df = df.copy()
    display_df.insert(0, '#', range(1, len(display_df) + 1))

    cols_to_truncate = ['descricao_ssa', 'descricao_execucao']
    for col in cols_to_truncate:
        if col in display_df.columns:
            display_df[col] = display_df[col].astype(str).str.slice(0, 45) + '...'

    display_df.rename(columns=display_map, inplace=True)
    
    wrapped_headers = []
    for header in display_df.columns:
        if len(header) > 8 and ' ' in header:
            wrapped_headers.append(header.replace(' ', '\n', 1))
        else:
            wrapped_headers.append(header)
    
    # --- NOVA LÓGICA DE LARGURA DE COLUNA ---
    # Define larguras máximas para colunas específicas para compactar a tabela
    # O número de elementos deve corresponder ao número de colunas em display_df
    max_widths = []
    for col_name in display_df.columns:
        if col_name in ['Emissor', 'Executor', 'Localização', 'Sem.\nCadastro']:
            max_widths.append(12)  # Define uma largura máxima menor
        else:
            max_widths.append(None) # Deixa o tabulate decidir
    # ----------------------------------------

    page_size = get_terminal_height() - 7
    total_rows = len(display_df)
    start_row = 0

    while start_row < total_rows:
        end_row = min(start_row + page_size, total_rows)
        page_df = display_df.iloc[start_row:end_row]

        table = tabulate(
            page_df,
            headers=wrapped_headers,
            tablefmt='psql',
            showindex=False,
            maxcolwidths=max_widths # <-- Aplica as novas larguras
        )
        print(table)

        start_row = end_row
        
        if start_row < total_rows:
            remaining = total_rows - start_row
            prompt = f"\n-- Mais ({remaining} restantes) | Pressione Enter para continuar ou 'q' para sair --"
            try:
                user_choice = input(prompt)
                if user_choice.lower() == 'q':
                    print("...exibição interrompida.")
                    break
            except KeyboardInterrupt:
                print("\n...exibição interrompida.")
                break