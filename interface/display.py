# interface/display.py (versão 2 - com paginação e formato otimizado)
import pandas as pd
from tabulate import tabulate
from typing import Dict
import os

def get_terminal_height():
    """Retorna a altura do terminal em número de linhas."""
    try:
        # os.get_terminal_size() retorna (colunas, linhas)
        return os.get_terminal_size().lines
    except OSError:
        # Em ambientes onde o tamanho não pode ser determinado, retorna um padrão.
        return 25

def pretty_print_df(df: pd.DataFrame, display_map: Dict[str, str]):
    """
    Imprime um DataFrame de forma paginada e otimizada para o terminal.
    """
    if df.empty:
        print("Nenhum resultado para exibir.")
        return

    display_df = df.copy()
    display_df.insert(0, '#', range(1, len(display_df) + 1))

    # Truncar descrições continua sendo uma boa prática para largura
    cols_to_truncate = ['descricao_ssa', 'descricao_execucao']
    for col in cols_to_truncate:
        if col in display_df.columns:
            # Garante que a coluna seja string antes de usar .str
            display_df[col] = display_df[col].astype(str).str.slice(0, 50) + '...'

    display_df.rename(columns=display_map, inplace=True)
    
    # --- LÓGICA DE PAGINAÇÃO ---
    page_size = get_terminal_height() - 5  # Deixa espaço para cabeçalho e prompts
    total_rows = len(display_df)
    start_row = 0

    while start_row < total_rows:
        end_row = min(start_row + page_size, total_rows)
        page_df = display_df.iloc[start_row:end_row]

        # MUDANÇA PRINCIPAL: Usando um formato de tabela compacto e profissional
        table = tabulate(
            page_df,
            headers='keys',
            tablefmt='psql',  # <-- O formato que muda tudo!
            showindex=False
        )
        print(table)

        start_row = end_row
        
        # Se ainda houver linhas a serem mostradas, exibe o prompt de paginação
        if start_row < total_rows:
            remaining = total_rows - start_row
            prompt = f"\n-- Mais ({remaining} restantes) | Pressione Enter para continuar ou 'q' para sair --"
            try:
                user_choice = input(prompt)
                if user_choice.lower() == 'q':
                    print("...exibição interrompida.")
                    break
            except KeyboardInterrupt: # Permite sair com Ctrl+C
                print("\n...exibição interrompida.")
                break