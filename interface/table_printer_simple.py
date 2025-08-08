# interface/table_printer_simple.py
import pandas as pd
from tabulate import tabulate
from typing import Dict
import os
import textwrap
import re
import logging

logger = logging.getLogger(__name__)

def get_terminal_width(default: int = 120) -> int:
    """Obtém a largura atual do terminal, com fallback para um valor padrão"""
    try:
        return os.get_terminal_size().columns
    except OSError:
        return default

def clean_text(text):
    """Remove caracteres especiais e limpa o texto para exibição"""
    if not isinstance(text, str):
        return str(text)
    # Remove caracteres de controle
    text = re.sub(r'[\x00-\x1F\x7F]', '', text)
    # Substitui múltiplos espaços por um único
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

def format_dataframe_for_cli(df: pd.DataFrame, display_map: Dict[str, str]) -> str:
    """
    Formata um DataFrame para exibição no CLI de forma simples e robusta.
    """
    if df.empty:
        return "Nenhum dado para exibir."

    try:
        terminal_width = get_terminal_width()
        df_display = df.copy()

        # Adiciona coluna # se não existir
        if '#' not in df_display.columns:
            df_display.insert(0, '#', range(1, len(df_display) + 1))
        
        # Aplica o mapeamento de exibição se existir
        if display_map:
            df_display.rename(columns=display_map, inplace=True)
        
        # Define colunas prioritárias em ordem de importância
        priority_cols = [
            '#', 'Nº SSA', 'numero_ssa', 'Executor', 'setor_executor', 
            'Situação', 'situacao', 'Data Cadastro', 'data_cadastro'
        ]
        
        # Colunas descritivas que podem ser truncadas
        desc_cols = ['Descrição da SSA', 'descricao_ssa', 'Descrição Execução', 'descricao_execucao']
        
        # Filtrar apenas colunas que existem
        available_cols = [col for col in df_display.columns]
        
        # Seleção automática baseada na largura do terminal
        if terminal_width < 100:  # Terminal pequeno
            selected_cols = []
            for col in priority_cols:
                if col in available_cols:
                    selected_cols.append(col)
                    if len(selected_cols) >= 4:  # Máximo 4 colunas em tela pequena
                        break
        elif terminal_width < 150:  # Terminal médio
            selected_cols = []
            for col in priority_cols:
                if col in available_cols:
                    selected_cols.append(col)
                    if len(selected_cols) >= 6:  # Máximo 6 colunas
                        break
            # Adiciona uma coluna descritiva se houver espaço
            for col in desc_cols:
                if col in available_cols and col not in selected_cols:
                    selected_cols.append(col)
                    break
        else:  # Terminal grande
            selected_cols = []
            # Adiciona todas as colunas prioritárias
            for col in priority_cols:
                if col in available_cols:
                    selected_cols.append(col)
            # Adiciona colunas descritivas
            for col in desc_cols:
                if col in available_cols and col not in selected_cols:
                    selected_cols.append(col)
                    if len(selected_cols) >= 8:  # Máximo 8 colunas
                        break
            # Adiciona outras colunas importantes
            other_cols = ['Emissor', 'setor_emissor', 'Sem. Programada', 'semana_programada']
            for col in other_cols:
                if col in available_cols and col not in selected_cols:
                    selected_cols.append(col)
                    if len(selected_cols) >= 10:
                        break
        
        # Se não conseguiu selecionar nenhuma coluna, usa as primeiras disponíveis
        if not selected_cols:
            selected_cols = available_cols[:5]  # Máximo 5 colunas como fallback
        
        # Limita as colunas selecionadas
        df_display = df_display[selected_cols]
        
        # Limpa o texto de todas as colunas
        for col in df_display.columns:
            df_display[col] = df_display[col].apply(clean_text)
        
        # Trunca colunas descritivas para evitar quebra de layout
        max_desc_width = max(30, terminal_width // len(selected_cols) - 10)
        for col in selected_cols:
            if any(desc in col for desc in ['Descrição', 'descricao']):
                df_display[col] = df_display[col].astype(str).apply(
                    lambda x: x[:max_desc_width] + '...' if len(x) > max_desc_width else x
                )
        
        # Formata usando tabulate
        return tabulate(
            df_display,
            headers="keys",
            tablefmt="simple",  # Formato mais simples e compatível
            showindex=False,
            maxcolwidths=[max_desc_width if any(desc in col for desc in ['Descrição', 'descricao']) 
                         else None for col in selected_cols]
        )
    
    except Exception as e:
        logger.error(f"Erro ao formatar DataFrame para CLI: {e}")
        # Fallback para exibição básica
        try:
            # Exibição de emergência - apenas as primeiras 3 colunas
            emergency_cols = df.columns[:3].tolist()
            df_emergency = df[emergency_cols].head(20)
            return tabulate(df_emergency, headers="keys", tablefmt="simple", showindex=False)
        except:
            return f"Erro na exibição. Dados disponíveis: {len(df)} registros, {len(df.columns)} colunas."
