# interface/display.py
import pandas as pd
from tabulate import tabulate
from typing import Dict

def pretty_print_df(df: pd.DataFrame, display_map: Dict[str, str]):
    """
    Imprime um DataFrame de forma formatada e legível no terminal.

    - Adiciona um índice numérico.
    - Trunca colunas de texto longas para evitar quebra de layout.
    - Renomeia colunas para nomes amigáveis antes de exibir.
    - Usa a biblioteca 'tabulate' para desenhar a tabela.
    """
    if df.empty:
        print("Nenhum resultado para exibir.")
        return

    # Cria uma cópia para não alterar o DataFrame original
    display_df = df.copy()

    # Adiciona a coluna de índice numérico na primeira posição
    display_df.insert(0, '#', range(1, len(display_df) + 1))

    # Trunca o texto de colunas longas para exibição
    # Apenas para as colunas que efetivamente existem no df
    cols_to_truncate = ['descricao_ssa', 'descricao_execucao']
    for col in cols_to_truncate:
        if col in display_df.columns:
            display_df[col] = display_df[col].str.slice(0, 50) + '...'

    # Renomeia as colunas para seus nomes de exibição
    display_df.rename(columns=display_map, inplace=True)

    # Usa tabulate para criar uma tabela bonita com quebra de linha
    # 'grid' é um formato que desenha todas as bordas
    table = tabulate(
        display_df,
        headers='keys',
        tablefmt='grid',
        showindex=False
    )

    print(table)
