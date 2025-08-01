# extracao/extractor.py
import pandas as pd
import json
import os
from typing import Optional
import logging

logger = logging.getLogger(__name__)

CONFIG_PATH = os.path.join('config', 'column_mappings.json')

class ExtractionError(Exception):
    """Erro durante a extração de dados de um arquivo."""
    pass

def _load_column_mappings() -> dict:
    try:
        with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
            mappings = json.load(f)
        inverted_map = {alias.strip(): canonical for canonical, aliases in mappings.items() for alias in aliases}
        logger.debug(f"Mapeamento de colunas carregado com {len(inverted_map)} entradas.")
        return inverted_map
    except FileNotFoundError:
        logger.warning(f"Arquivo de mapeamento '{CONFIG_PATH}' não encontrado.")
        return {}
    except json.JSONDecodeError as e:
        logger.error(f"Erro ao decodificar '{CONFIG_PATH}': {e}")
        return {}

def _normalize_datatypes(df: pd.DataFrame) -> pd.DataFrame:
    logger.debug("Iniciando normalização de tipos de dados...")
    df_normalized = df.copy()

    if 'numero_ssa' in df_normalized.columns:
        df_normalized['numero_ssa'] = pd.to_numeric(df_normalized['numero_ssa'], errors='coerce').astype('Int64')

    if 'data_cadastro' in df_normalized.columns:
        df_normalized['data_cadastro'] = pd.to_datetime(df_normalized['data_cadastro'], errors='coerce', dayfirst=True)

    # CORREÇÃO: Garante que o nome da coluna é string antes de chamar .lower()
    semana_columns = [col for col in df_normalized.columns if isinstance(col, str) and 'semana' in col.lower()]
    for col in semana_columns:
        logger.debug(f"Convertendo coluna de semana '{col}' para Int64...")
        df_normalized[col] = pd.to_numeric(df_normalized[col], errors='coerce').astype('Int64')

    logger.debug("Normalização de tipos concluída.")
    return df_normalized

def extract_data_from_excel(file_path: str) -> Optional[pd.DataFrame]:
    logger.info(f"Iniciando extração de dados de '{file_path}'...")
    try:
        all_sheets_data = []
        xl_file = pd.ExcelFile(file_path, engine='openpyxl')
        
        for sheet_name in xl_file.sheet_names:
            logger.debug(f"Processando planilha '{sheet_name}'...")
            sheet_df = xl_file.parse(sheet_name, header=None)
            
            header_row_idx = None
            for idx, value in enumerate(sheet_df.iloc[:, 0]):
                if pd.notna(value) and str(value).strip() != '':
                    header_row_idx = idx
                    break
            
            if header_row_idx is not None:
                sheet_df.columns = sheet_df.iloc[header_row_idx]
                sheet_df = sheet_df.drop(sheet_df.index[:header_row_idx + 1]).reset_index(drop=True)
                sheet_df = sheet_df.dropna(axis=1, how='all')
                
                # CORREÇÃO: Remove colunas duplicadas que causam o InvalidIndexError
                sheet_df = sheet_df.loc[:, ~sheet_df.columns.duplicated()]

                if not sheet_df.empty:
                    all_sheets_data.append(sheet_df)
            else:
                 logger.warning(f"Planilha '{sheet_name}' em '{file_path}' não possui cabeçalho identificável.")

        if not all_sheets_data:
             logger.warning(f"Nenhum dado válido encontrado em '{file_path}'.")
             return None

        combined_df = pd.concat(all_sheets_data, ignore_index=True, sort=False)
        combined_df.dropna(how='all', inplace=True)
        
        if combined_df.empty:
            logger.warning(f"Nenhum dado válido encontrado em '{file_path}' após combinação.")
            return None
            
        column_mappings = _load_column_mappings()
        
        # CORREÇÃO: Garante que os nomes das colunas são strings antes de mapear
        combined_df.columns = [str(c).strip() for c in combined_df.columns]
        combined_df.rename(columns=column_mappings, inplace=True)
        
        combined_df = _normalize_datatypes(combined_df)
        
        logger.info(f"Extração concluída com sucesso. {len(combined_df)} linhas extraídas.")
        return combined_df

    except Exception as e:
        logger.error(f"Erro inesperado ao processar '{file_path}': {e}", exc_info=True)
        return None