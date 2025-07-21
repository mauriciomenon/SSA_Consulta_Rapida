# interface/display.py 20250722 120000 (v5.1 - Correção de Exibição e NameError)
import pandas as pd
from tabulate import tabulate
from typing import Dict, Any
import os

def get_terminal_height():
    """Obtem a altura do terminal para ajustar a paginação."""
    try:
        return os.get_terminal_size().lines
    except OSError:
        return 25 # Valor padrão se não conseguir determinar

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
    # suppress_columns nao esta em settings.json, entao usaremos column_visibility
    column_visibility = display_settings.get('column_visibility', {})
    width_map = display_settings.get('column_widths', {})

    # Filtra as colunas a serem exibidas com base em column_visibility
    cols_to_display = []
    for col_internal in display_map.keys():
        # Apenas inclui a coluna se ela existe no DataFrame e esta marcada como visível
        if col_internal in df.columns and column_visibility.get(col_internal, True):
            cols_to_display.append(col_internal)
    
    if not cols_to_display:
        print("Nenhuma coluna para exibição foi encontrada (verifique 'column_visibility' nas configurações).")
        return
        
    display_df = df[cols_to_display].copy()

    # Formata a coluna 'data_cadastro'
    if 'data_cadastro' in display_df.columns:
        display_df['data_cadastro'] = pd.to_datetime(display_df['data_cadastro'], errors='coerce').dt.strftime('%d/%m/%Y')

    # Preenche valores nulos para exibição
    display_df.fillna('-', inplace=True)

    # TRUNCAMENTO DE TEXTO REINTRODUZIDO PARA MANTER O LAYOUT
    cols_to_truncate = ['descricao_ssa', 'descricao_execucao']
    for col in cols_to_truncate:
        if col in display_df.columns:
            display_df[col] = display_df[col].astype(str).str.slice(0, 40) + '...'

    # Adiciona a coluna '#' e renomeia as colunas para os nomes de exibição
    display_df.insert(0, '#', range(1, len(display_df) + 1))
    # Renomeia as colunas visíveis para seus nomes amigáveis para exibição
    # Mantém os nomes originais para as colunas '#', se não estiverem no display_map
    renamed_columns = {'#': '#'}
    for internal_col in cols_to_display:
        renamed_columns[internal_col] = display_map.get(internal_col, internal_col)

    display_df.rename(columns=renamed_columns, inplace=True)

    # Prepara os cabeçalhos para o tabulate (sem quebra de linha forcada, a menos que ja exista)
    wrapped_headers = [display_map.get(col, col) for col in cols_to_display]
    wrapped_headers.insert(0, '#') # Adiciona o cabeçalho para a coluna '#'

    # Garante que as larguras de coluna sejam aplicadas corretamente aos nomes de exibicao
    final_max_widths = []
    for h in wrapped_headers:
        # Se for o '#' ou um cabeçalho que veio do display_map, usa a largura configurada
        final_max_widths.append(width_map.get(h, None))

    page_size = get_terminal_height() - 7
    total_rows = len(display_df)
    start_row = 0

    # Lógica de paginação
    auto_scroll = settings.get('user_preferences', {}).get('auto_scroll_to_end', False)
    
    while start_row < total_rows:
        end_row = min(start_row + page_size, total_rows)
        page_df = display_df.iloc[start_row:end_row]

        # Garantir que o cabecalho de '#'' tenha sua largura
        current_max_widths_for_tabulate = [width_map.get('#', 4)] # Largura fixa para '#'
        # Adiciona as larguras para as colunas de dados
        for col_display_name in [renamed_columns[col] for col in cols_to_display]:
             current_max_widths_for_tabulate.append(width_map.get(col_display_name, None))

        table = tabulate(page_df, headers=wrapped_headers, tablefmt='presto', showindex=False, maxcolwidths=current_max_widths_for_tabulate)
        print(table)

        start_row = end_row
        if start_row < total_rows:
            if auto_scroll:
                continue # Pula para a próxima página automaticamente
            
            remaining = total_rows - start_row
            prompt = f"\n-- Mais ({remaining} restantes) | Pressione Enter para continuar, 's' para rolar até o final, 'q' para sair --"
            try:
                user_input = input(prompt).strip().lower()
                if user_input == 'q':
                    print("...exibição interrompida.")
                    break
                elif user_input == 's':
                    auto_scroll = True # Ativa a rolagem automática para o restante
                    continue
                elif user_input == '': # Enter
                    continue # Continua para a proxima pagina
                else:
                    print("Comando inválido. Pressione Enter, 's' ou 'q'.")
                    # Nao avanca a pagina se o comando for invalido
                    start_row -= page_size # Volta a start_row para exibir a mesma pagina
                    continue
            except KeyboardInterrupt:
                print("\n...exibição interrompida."); break