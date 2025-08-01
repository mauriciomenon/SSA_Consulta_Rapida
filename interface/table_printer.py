# interface/table_printer.py
import pandas as pd
from tabulate import tabulate
from typing import Dict
import os
import textwrap

def get_terminal_width(default: int = 120) -> int:
    try:
        return os.get_terminal_size().columns
    except OSError:
        return default

def format_dataframe_for_cli(df: pd.DataFrame, display_map: Dict[str, str]) -> str:
    """
    Formata um DataFrame para exibição no CLI, ajustando as colunas
    dinamicamente para preencher a largura do terminal.
    """
    if df.empty:
        return "Nenhum dado para exibir."

    terminal_width = get_terminal_width()
    df_display = df.copy()

    # Prepara o DataFrame para exibição
    if '#' not in df_display.columns:
        df_display.insert(0, '#', range(1, len(df_display) + 1))
    
    df_display.rename(columns=display_map, inplace=True)
    
    # Colunas que queremos exibir e sua ordem de prioridade
    priority_cols = [
        '#', 'Nº SSA', 'Executor', 'Situação', 'Descrição da SSA', 
        'Data Cadastro', 'Sem. Programada', 'Descrição Execução', 'Emissor'
    ]
    
    available_cols = [col for col in priority_cols if col in df_display.columns]
    
    # Calcula a largura fixa para colunas não-descritivas
    fixed_width = 0
    stretch_cols = ['Descrição da SSA', 'Descrição Execução']
    col_widths = {}

    for col_name in available_cols:
        if col_name not in stretch_cols:
            max_len = max(df_display[col_name].astype(str).str.len().max(), len(col_name))
            col_widths[col_name] = max_len
            fixed_width += max_len + 3  # +3 para padding ' | '

    # Distribui o espaço restante para as colunas de descrição
    remaining_width = terminal_width - fixed_width - (len(available_cols) + 1)
    
    if len(stretch_cols) > 0 and remaining_width > 20:
        stretch_width = remaining_width // len(stretch_cols)
        for col_name in stretch_cols:
            if col_name in available_cols:
                col_widths[col_name] = max(15, stretch_width) # Largura mínima de 15

    # Aplica a quebra de linha (wrapping)
    for col_name, width in col_widths.items():
        if col_name in df_display.columns and col_name in stretch_cols:
            df_display[col_name] = df_display[col_name].astype(str).apply(
                lambda x: '\n'.join(textwrap.wrap(x, width=width))
            )

    return tabulate(
        df_display[available_cols], 
        headers="keys", 
        tablefmt="grid", 
        showindex=False
    )