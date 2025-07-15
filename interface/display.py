# interface/display.py (versão 3 - com quebra de cabeçalho)
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
            display_df[col] = display_df[col].astype(str).str.slice(0, 50) + '...'

    display_df.rename(columns=display_map, inplace=True)
    
    # --- NOVA LÓGICA DE QUEBRA DE CABEÇALHO ---
    wrapped_headers = []
    for header in display_df.columns:
        # Se o cabeçalho for longo e tiver um espaço, quebramos em duas linhas
        if len(header) > 8 and ' ' in header:
            wrapped_headers.append(header.replace(' ', '\n', 1))
        else:
            wrapped_headers.append(header)
    # -----------------------------------------

    page_size = get_terminal_height() - 7 # Mais espaço para cabeçalhos de 2 linhas
    total_rows = len(display_df)
    start_row = 0

    while start_row < total_rows:
        end_row = min(start_row + page_size, total_rows)
        page_df = display_df.iloc[start_row:end_row]

        table = tabulate(
            page_df,
            headers=wrapped_headers, # <-- Usa os cabeçalhos com quebra de linha
            tablefmt='psql',
            showindex=False
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