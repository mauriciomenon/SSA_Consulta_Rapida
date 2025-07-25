# interface/table_printer.py 20250724 160000 (v1.15 - Consolidado Final)

import pandas as pd
from tabulate import tabulate
from typing import Dict, Any, List
import os
import re
import unicodedata
import math

def get_terminal_size():
    """Obtem a altura e largura do terminal."""
    try:
        size = os.get_terminal_size()
        return size.lines, size.columns
    except OSError:
        # Valores padrão conservadores
        return 24, 80

def _estimate_column_width(series: pd.Series, header: str) -> int:
    """Estima a largura necessária para uma coluna."""
    max_header_width = len(str(header))
    # Amostra para performance
    sample_data = series.dropna().astype(str).head(100)
    if len(sample_data) == 0:
        return max_header_width
    # Considera o 95º percentil para evitar outliers muito largos
    max_data_width = sample_data.str.len().quantile(0.95, interpolation='lower')
    estimated_width = max(max_header_width, int(max_data_width) if pd.notna(max_data_width) else 0, 5)
    # Limite máximo para evitar colunas extremamente largas
    return min(estimated_width, 70)

def _select_columns_for_width(
    df: pd.DataFrame,
    display_map: Dict[str, str],
    available_width: int,
    essential_columns: List[str],
    priority_order: List[str]
) -> list:
    """Seleciona colunas priorizando as essenciais e distribuindo o espaço."""
    valid_cols = [col for col in df.columns if not col.startswith('Unnamed:')]

    # Cria lista ordenada: essenciais primeiro, depois prioridade, depois o resto
    ordered_cols = []
    seen = set()
    # 1. Adiciona colunas essenciais na ordem EXATA
    for col in essential_columns:
        if col in valid_cols and col not in seen:
            ordered_cols.append(col)
            seen.add(col)
    # 2. Adiciona colunas prioritárias na ordem
    for col in priority_order:
        if col in valid_cols and col not in seen:
            ordered_cols.append(col)
            seen.add(col)
    # 3. Adiciona colunas restantes
    for col in valid_cols:
        if col not in seen:
            ordered_cols.append(col)

    # Calcula larguras estimadas
    estimated_widths = {'#': 4} # Largura fixa para '#'
    for col in valid_cols:
        renamed_col = display_map.get(col, col)
        estimated_widths[col] = _estimate_column_width(df[col], renamed_col)

    selected_columns = ['#'] # Sempre inclui '#'
    total_width = estimated_widths['#'] + 3 # Espaço inicial

    # Itera pela ordem definida para selecionar colunas
    for col in ordered_cols:
        col_width = estimated_widths.get(col, 10) + 3 # +3 para separador
        # Se couber, adiciona
        if total_width + col_width <= available_width:
            selected_columns.append(col)
            total_width += col_width
        else:
            # Se for a primeira coluna de dados e não couber, força adicioná-la
            # para evitar tabela vazia
            if len(selected_columns) == 1: # So tem '#'
                selected_columns.append(col)
            # Se ja tem colunas de dados, para de adicionar
            break

    return selected_columns

def paginate_dataframe(df: pd.DataFrame, page_size: int):
    """Gera pedaços (chunks) de um DataFrame."""
    if df.empty:
        return
    total_pages = math.ceil(len(df) / page_size)
    for page_num in range(total_pages):
        start_idx = page_num * page_size
        end_idx = min(start_idx + page_size, len(df))
        yield df.iloc[start_idx:end_idx]

def pretty_print_df(df: pd.DataFrame, display_map: Dict[str, str], settings: dict):
    """Imprime o DataFrame de forma paginada e formatada."""
    if df.empty:
        print("Nenhum resultado para exibir.")
        return

    # --- Configuração e Detecção do Terminal ---
    terminal_height, terminal_width = get_terminal_size()
    # Deixa uma margem de segurança
    available_width = max(terminal_width - 10, 20)

    # --- Definição de Ordem de Colunas ---
    # Ordem EXATA solicitada para as colunas mais importantes
    essential_columns_in_order = [
        'numero_ssa', 'setor_executor', 'situacao', 'descricao_ssa',
        'data_cadastro', 'semana_cadastro', 'semana_programada', 'descricao_execucao'
    ]
    # Demais colunas em ordem de importância
    subsequent_priority = [
        'setor_emissor', 'derivada_de', 'data_limite', 'execucao_parcial',
        'anomalia', 'sistema_origem', 'grau_prioridade_emissao',
        'grau_prioridade_planejamento', 'solicitante', 'servico_origem',
        'responsavel_programacao', 'responsavel_execucao', 'prazo_limite',
        'tempo_disponivel', 'tempo_excedido', 'desde', 'tempo_total',
        'desde_1', 'total_tempo_tpe_planejado', 'total_tempo_tex_planejado',
        'total_tempo_tpo_planejado', 'total_horas_programadas',
        'semana_executada', 'num_reprogramacoes', 'execucao_simples'
    ]

    # --- Seleção Inteligente de Colunas ---
    selected_cols = _select_columns_for_width(
        df, display_map, available_width, essential_columns_in_order, subsequent_priority
    )

    if not selected_cols or (len(selected_cols) == 1 and selected_cols[0] == '#'):
        print("Nenhuma coluna para exibição foi encontrada ou selecionada.")
        return

    cols_to_display = [col for col in selected_cols if col != '#']
    if not cols_to_display:
        print("Nenhuma coluna de dados para exibição foi encontrada.")
        return

    # --- Processamento Inicial dos Dados ---
    working_df = df[cols_to_display].copy()

    # Formatação específica para data_cadastro
    if 'data_cadastro' in working_df.columns:
        working_df['data_cadastro'] = pd.to_datetime(working_df['data_cadastro'], errors='coerce').dt.strftime('%d/%m/%Y')

    # Sanitização agressiva de strings
    for col in working_df.columns:
        if pd.api.types.is_object_dtype(working_df[col]) or pd.api.types.is_string_dtype(working_df[col]):
            # Converte para string, substitui valores nulos/inválidos
            working_df[col] = working_df[col].apply(
                lambda x: '-' if pd.isna(x) or str(x).strip().lower() in ['none', 'nan', 'nat', ''] else str(x)
            )
            # Normalização Unicode
            working_df[col] = working_df[col].apply(
                lambda x: unicodedata.normalize('NFKD', x).encode('ascii', 'ignore').decode('utf-8')
            )
            # Remove caracteres de controle e substitui quebras por espaço
            working_df[col] = working_df[col].apply(
                lambda x: re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F\n\r\t]+', ' ', x)
            )
            # Normaliza espaços e remove bordas
            working_df[col] = working_df[col].str.replace(r'\s+', ' ', regex=True).str.strip()

    # Truncar colunas de descrição de forma mais inteligente
    cols_to_truncate = ['descricao_ssa', 'descricao_execucao']
    for col in cols_to_truncate:
        if col in working_df.columns:
             # Calcula largura máxima com base no espaço disponível e número de colunas
             # Prioriza um mínimo de 30 caracteres para descrições
             base_width = max(30, (terminal_width // max(2, len(cols_to_display))))
             max_len = min(base_width, 100) # Limite máximo
             working_df[col] = working_df[col].str.slice(0, max_len) + '...'

    # --- Preparação Final para Exibição ---
    # Adiciona coluna de índice
    working_df.insert(0, '#', range(1, len(working_df) + 1))
    
    # Renomeia colunas para exibição
    renamed_columns = {'#': '#'}
    for internal_col in cols_to_display:
        renamed_columns[internal_col] = display_map.get(internal_col, internal_col)
    working_df.rename(columns=renamed_columns, inplace=True)

    # Prepara cabeçalhos e larguras para `tabulate`
    final_headers = [renamed_columns.get(col, col) for col in selected_cols]
    
    # Calcula larguras máximas para `tabulate`
    # Tenta distribuir o espaço igualmente, mas respeita limites
    num_cols = len(final_headers)
    # Espaço médio por coluna, com mínimo e máximo
    avg_width_per_col = max(8, min(50, (terminal_width - 10) // max(1, num_cols)))
    final_max_widths = [avg_width_per_col] * num_cols
    # Ajusta colunas específicas se necessário
    # Por exemplo, dá um pouco mais de espaço para descrições se elas estiverem presentes
    desc_indices = [i for i, h in enumerate(final_headers) if 'descricao' in h.lower()]
    if desc_indices:
        extra_space = 10 # Espaço extra total para descrições
        extra_per_desc = extra_space // len(desc_indices)
        for i in desc_indices:
            final_max_widths[i] = min(60, final_max_widths[i] + extra_per_desc)


    # --- Paginação ---
    page_size_data_lines = max(1, terminal_height - 5) # Linhas para dados
    auto_scroll = settings.get('user_preferences', {}).get('auto_scroll_to_end', False)
    
    # Controle de auto-scroll para muitas páginas
    total_pages = math.ceil(len(working_df) / page_size_data_lines) if page_size_data_lines > 0 else 1
    max_auto_scroll_pages = settings.get('display_settings', {}).get('max_auto_scroll_pages', 3)
    
    if auto_scroll and total_pages > max_auto_scroll_pages:
        # print(f"Aviso: Muitas páginas ({total_pages}). Scroll automático desativado temporariamente.")
        # print("Use o comando 'f' após a primeira página se desejar rolar até o final.")
        auto_scroll = False # Desativa silenciosamente ou com aviso sutil

    # Gera páginas
    page_generator = paginate_dataframe(working_df, page_size_data_lines)
    pages = list(page_generator)

    if not pages:
        print("Nenhum dado para exibir após o processamento.")
        return

    # Loop de exibição
    current_page_index = 0
    while current_page_index < len(pages):
        try:
            current_page_df = pages[current_page_index]
            
            # Gera e imprime a tabela para a página atual
            page_table_str = tabulate(
                current_page_df,
                headers=final_headers if current_page_index == 0 else [], # Cabeçalho só na 1ª
                tablefmt='presto',
                showindex=False,
                maxcolwidths=final_max_widths
            )
            print(page_table_str)

            current_page_index += 1

            # Verifica se há mais páginas
            if current_page_index < len(pages):
                if auto_scroll:
                    continue # Vai para a próxima página automaticamente
                else:
                    remaining_pages = len(pages) - current_page_index
                    prompt_text = f"\n-- Mais ({remaining_pages} pág. restante(s)) | Enter: continuar, 'f': até o final, 'q': sair --"
                    try:
                        user_input = input(prompt_text).strip().lower()
                    except KeyboardInterrupt:
                        print("\n...exibição interrompida.")
                        break

                    if user_input == 'q':
                        print("\n...exibição interrompida.")
                        break
                    elif user_input == 'f':
                        auto_scroll = True # Ativa scroll automático para o restante
                    elif user_input == '':
                        continue # Vai para a próxima página
                    else:
                        print("Comando inválido.")
                        current_page_index -= 1 # Refaz a página atual

        except KeyboardInterrupt:
            print("\n...exibição interrompida.")
            break
        except Exception as e:
            # Erro silencioso ou log simples para não quebrar a interface
            # print(f"\nErro durante exibição página {current_page_index + 1}: {e}")
            current_page_index += 1 # Tenta continuar com a próxima página
