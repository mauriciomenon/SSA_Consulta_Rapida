# extracao/extractor.py 20250725 101500 (v6.4 - Melhorias de Tipo, Sanitizacao, Logging)
"""
Módulo responsável pela extração e normalização inicial de dados de arquivos Excel.

Lê arquivos .xlsx, identifica cabeçalhos, normaliza nomes de colunas usando
`config/column_mappings.json` e converte tipos de dados fundamentais.
"""

import pandas as pd
import json
import os
from typing import Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)

CONFIG_PATH = os.path.join('config', 'column_mappings.json')

class ExtractionError(Exception):
    """Erro durante a extração de dados de um arquivo."""
    pass

def _load_column_mappings() -> dict:
    """
    Carrega o mapeamento de nomes de colunas a partir do arquivo JSON.

    Returns:
        dict: Um dicionário {alias: nome_canonico}.
              Retorna um dicionário vazio se o arquivo não for encontrado.
    """
    try:
        with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
            mappings = json.load(f)
        # Inverte o mapa para {alias: canonical}
        inverted_map = {alias: canonical for canonical, aliases in mappings.items() for alias in aliases}
        logger.debug(f"Mapeamento de colunas carregado com {len(inverted_map)} entradas.")
        return inverted_map
    except FileNotFoundError:
        logger.warning(f"Arquivo de mapeamento '{CONFIG_PATH}' não encontrado. "
                       "A normalização de colunas pode falhar.")
        return {}
    except json.JSONDecodeError as e:
        logger.error(f"Erro ao decodificar '{CONFIG_PATH}': {e}")
        return {}

def _normalize_datatypes(df: pd.DataFrame) -> pd.DataFrame:
    """
    Converte colunas-chave para tipos de dados padronizados.

    Args:
        df (pd.DataFrame): O DataFrame bruto após combinar planilhas.

    Returns:
        pd.DataFrame: O DataFrame com tipos de dados normalizados.
    """
    logger.debug("Iniciando normalização de tipos de dados...")
    df_normalized = df.copy() # Trabalha em uma cópia

    # --- Conversao de numero_ssa para Int64 nullable ---
    if 'numero_ssa' in df_normalized.columns:
        logger.debug("Convertendo 'numero_ssa' para Int64...")
        df_normalized['numero_ssa'] = pd.to_numeric(df_normalized['numero_ssa'], errors='coerce').astype('Int64')

    # --- Conversao de data_cadastro para datetime ---
    if 'data_cadastro' in df_normalized.columns:
        logger.debug("Convertendo 'data_cadastro' para datetime...")
        df_normalized['data_cadastro'] = pd.to_datetime(
            df_normalized['data_cadastro'],
            errors='coerce',
            dayfirst=True # Assume DD/MM/YYYY
        )

    # --- Conversao de colunas de semana para Int64 nullable ---
    # Identifica colunas que representam semanas
    semana_columns = [col for col in df_normalized.columns if 'semana' in col.lower()]
    for col in semana_columns:
        logger.debug(f"Convertendo coluna de semana '{col}' para Int64...")
        df_normalized[col] = pd.to_numeric(df_normalized[col], errors='coerce').astype('Int64')
        
    # --- Conversao de outras colunas numericas conhecidas ---
    # Pode ser expandido ou movido para um config file
    # numeric_columns = ['num_reprogramacoes', 'total_horas_programadas']
    # for col in numeric_columns:
    #     if col in df_normalized.columns:
    #         logger.debug(f"Convertendo '{col}' para Int64...")
    #         df_normalized[col] = pd.to_numeric(df_normalized[col], errors='coerce').astype('Int64')

    logger.debug("Normalização de tipos concluída.")
    return df_normalized

def extract_data_from_excel(file_path: str) -> Optional[pd.DataFrame]:
    """
    Extrai dados de um único arquivo Excel (.xlsx).

    Args:
        file_path (str): Caminho completo para o arquivo Excel.

    Returns:
        Optional[pd.DataFrame]: Um DataFrame com os dados extraídos e normalizados,
                                ou None em caso de erro.
    """
    logger.info(f"Iniciando extração de dados de '{file_path}'...")
    try:
        all_sheets_data = []
        xl_file = pd.ExcelFile(file_path, engine='openpyxl') 
        
        for sheet_name in xl_file.sheet_names:
            logger.debug(f"Processando planilha '{sheet_name}'...")
            # Le a planilha inteira
            sheet_df = xl_file.parse(sheet_name, header=None) 
            
            # Encontra a linha do cabecalho (primeira celula nao vazia na coluna 0)
            header_row_idx = None
            for idx, value in enumerate(sheet_df.iloc[:, 0]):
                if pd.notna(value) and str(value).strip() != '':
                    header_row_idx = idx
                    break
            
            if header_row_idx is not None:
                # Define os cabecalhos
                sheet_df.columns = sheet_df.iloc[header_row_idx] 
                # Remove linhas anteriores ao cabecalho e o proprio cabecalho
                sheet_df = sheet_df.drop(sheet_df.index[:header_row_idx + 1]) 
                # Reseta o indice
                sheet_df = sheet_df.reset_index(drop=True) 
                
                # Remove colunas completamente vazias
                sheet_df = sheet_df.dropna(axis=1, how='all')
                
                if not sheet_df.empty:
                    all_sheets_data.append(sheet_df)
                else:
                    logger.debug(f"Planilha '{sheet_name}' está vazia após processamento.")
            else:
                 logger.warning(f"Planilha '{sheet_name}' em '{file_path}' não possui cabeçalho identificável.")

        if not all_sheets_data:
             logger.warning(f"Nenhum dado válido encontrado em '{file_path}'.")
             return None

        # Combina dados de todas as planilhas
        combined_df = pd.concat(all_sheets_data, ignore_index=True, sort=False)
        
        # Remove linhas completamente vazias
        initial_len = len(combined_df)
        combined_df.dropna(how='all', inplace=True)
        final_len = len(combined_df)
        if initial_len != final_len:
            logger.debug(f"Removidas {initial_len - final_len} linhas completamente vazias.")
        
        if combined_df.empty:
            logger.warning(f"Nenhum dado válido encontrado em '{file_path}' após combinação.")
            return None
            
        # Carrega o mapeamento de colunas
        column_mappings = _load_column_mappings()
        
        # Normaliza os nomes das colunas
        combined_df.rename(columns=column_mappings, inplace=True)
        logger.debug(f"Colunas renomeadas. Novas colunas: {list(combined_df.columns)}")
        
        # Normaliza os tipos de dados
        combined_df = _normalize_datatypes(combined_df)
        
        # --- Sanitizacao Basica e Robusta de Strings ---
        logger.debug("Iniciando sanitização de strings...")
        for col in combined_df.columns:
            # Verifica se a coluna é de tipo 'object' (pandas usa para strings e mixed types)
            if pd.api.types.is_object_dtype(combined_df[col]):
                # 1. Converte para string, tratando valores NA
                combined_df[col] = combined_df[col].astype(str)
                
                # 2. Substitui strings que representam valores nulos por pd.NA
                # Isso é importante para consistência após a conversão para string
                combined_df[col] = combined_df[col].replace(['nan', 'None', 'NaN', '<NA>'], pd.NA)
                
                # 3. Remove espaços extras no início e no fim
                combined_df[col] = combined_df[col].str.strip()
                
                # 4. Substitui strings vazias resultantes por pd.NA
                combined_df[col] = combined_df[col].replace({'': pd.NA})
                
                # Nota: A normalização Unicode e remoção de caracteres de controle
                # podem ser feitas aqui se necessário, mas o table_printer.py
                # já faz uma sanitização agressiva para exibição.
                # Manter a original no DB pode ser útil.
                
        logger.info(f"Extração concluída com sucesso. {len(combined_df)} linhas extraídas.")
        return combined_df

    except FileNotFoundError:
        logger.error(f"Arquivo '{file_path}' não encontrado.")
        return None
    except pd.errors.ParserError as e:
        logger.error(f"Erro ao ler '{file_path}': Problema ao analisar o arquivo Excel. Detalhes: {e}")
        return None
    except Exception as e:
        logger.error(f"Erro inesperado ao processar '{file_path}': {e}", exc_info=True)
        return None
