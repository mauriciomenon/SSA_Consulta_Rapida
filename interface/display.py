# interface/display.py 20250721 120515 (v4.0 - com Configurações Dinâmicas)
import pandas as pd
from tabulate import tabulate
from typing import Dict, Any
import os

def get_terminal_height():
    try:
        return os.get_terminal_size().lines
    except OSError:
        return 25

def pretty_print_details(series: pd.Series, display_map: Dict[str, str]):
    """Imprime os detalhes de uma única linha (SSA) de forma legível."""
    print("\n" + "="*50)
    print(f" DETALHES DA SSA: {series.get('numero_ssa', 'N/A')}")
    print("="*50)
    
    for key, value in series.items():
        header = display_map.get(key, key)
        display_value = value if pd.notna(value) else '-'
        print(f"{header+':':<20} {display_value}")
        
    print("="*50)

def pretty_print_df(df: pd.DataFrame, display_map: Dict[str, str], settings: dict):
    if df.empty:
        print("Nenhum resultado para exibir.")
        return

    # Carrega as configurações de exibição do dicionário de settings
    display_settings = settings.get('display_settings', {})
    suppressed_cols = display_settings.get('suppress_columns', [])
    width_map = display_settings.get('column_widths', {})

    # Filtra as colunas a serem exibidas, removendo as que estão na lista 'suppress_columns'
    cols_to_display = [
        col for col in display_map.keys() 
        if col in df.columns and col not in suppressed_cols
    ]
    
    if not cols_to_display:
        print("Nenhuma coluna para exibição foi encontrada (verifique 'suppress_columns' nas configurações).")
        return
        
    display_df = df[cols_to_display].copy()

    if 'data_cadastro' in display_df.columns:
        display_df['data_cadastro'] = pd.to_datetime(display_df['data_cadastro'], errors='coerce').dt.strftime('%d/%m/%Y')

    display_df.fillna('-', inplace=True)

    cols_to_truncate = ['descricao_ssa', 'descricao_execucao']
    for col in cols_to_truncate:
        if col in display_df.columns:
            display_df[col] = display_df[col].astype(str).str.slice(0, 40) + '...'

    display_df.insert(0, '#', range(1, len(display_df) + 1))
    display_df.rename(columns=display_map, inplace=True)

    wrapped_headers = [h.replace(' ', '\n', 1) if ' ' in h and len(h) > 8 else h for h in display_df.columns]
    # Usa o width_map carregado das configurações
    max_widths = [width_map.get(h, None) for h in wrapped_headers]

    page_size = get_terminal_height() - 7
    total_rows = len(display_df)
    start_row = 0

    # Lógica de paginação
    auto_scroll = settings.get('user_preferences', {}).get('auto_scroll_to_end', False)
    
    while start_row < total_rows:
        end_row = min(start_row + page_size, total_rows)
        page_df = display_df.iloc[start_row:end_row]

        table = tabulate(page_df, headers=wrapped_headers, tablefmt='presto', showindex=False, maxcolwidths=max_widths)
        print(table)

        start_row = end_row
        if start_row < total_rows:
            if auto_scroll:
                continue # Pula para a próxima página automaticamente
            
            remaining = total_rows - start_row
            prompt = f"\n-- Mais ({remaining} restantes) | Pressione Enter para continuar ou 'q' para sair --"
            try:
                if input(prompt).lower() == 'q':
                    print("...exibição interrompida.")
                    break
            except KeyboardInterrupt:
                print("\n...exibição interrompida."); break
