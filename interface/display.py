# interface/display.py (v2.0 - Exibicao Robusta)
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

    # CORRECAO CRITICA: So vamos exibir as colunas que estao no nosso mapa.
    # Isso impede que colunas inesperadas do schema dinamico quebrem a tabela.
    cols_to_display = [col for col in display_map.keys() if col in df.columns]
    if not cols_to_display:
        print("Nenhuma coluna mapeada para exibicao foi encontrada nos resultados.")
        return
        
    display_df = df[cols_to_display].copy()

    if 'data_cadastro' in display_df.columns:
        display_df['data_cadastro'] = pd.to_datetime(
            display_df['data_cadastro'], errors='coerce'
        ).dt.strftime('%d/%m/%Y')

    cols_to_truncate = ['descricao_ssa', 'descricao_execucao']
    for col in cols_to_truncate:
        if col in display_df.columns:
            display_df[col] = display_df[col].astype(str).str.slice(0, 40) + '...'

    display_df.insert(0, '#', range(1, len(display_df) + 1))
    display_df.rename(columns=display_map, inplace=True)
    display_df.fillna('', inplace=True)

    wrapped_headers = [h.replace(' ', '\n', 1) if ' ' in h and len(h) > 8 else h for h in display_df.columns]
    width_map = {'#': 4, 'Nº SSA': 9, 'Loc.': 10, 'Emissor': 8, 'Executor': 8, 'Sem.\nCadastro': 8, 'Data\nCadastro': 10}
    max_widths = [width_map.get(h, None) for h in wrapped_headers]

    page_size = get_terminal_height() - 7
    total_rows = len(display_df)
    start_row = 0

    while start_row < total_rows:
        end_row = min(start_row + page_size, total_rows)
        page_df = display_df.iloc[start_row:end_row]

        table = tabulate(
            page_df,
            headers=wrapped_headers,
            tablefmt='presto',
            showindex=False,
            maxcolwidths=max_widths
        )
        print(table)

        start_row = end_row
        
        if start_row < total_rows:
            remaining = total_rows - start_row
            prompt = f"\n-- Mais ({remaining} restantes) | Pressione Enter para continuar ou 'q' para sair --"
            try:
                if input(prompt).lower() == 'q':
                    print("...exibicao interrompida.")
                    break
            except KeyboardInterrupt:
                print("\n...exibicao interrompida."); break
