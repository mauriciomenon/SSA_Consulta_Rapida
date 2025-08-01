# extracao/extractor.py
import pandas as pd
import json
import os
import re
from typing import Optional, List
import logging

logger = logging.getLogger(__name__)

CONFIG_PATH = os.path.join('config', 'column_mappings.json')
SCHEMA_PATH = os.path.join('config', 'schema.sql')

class ExtractionError(Exception):
    pass

def _get_valid_columns_from_schema(schema_path: str) -> List[str]:
    """Lê o arquivo schema.sql e extrai os nomes das colunas válidas."""
    try:
        with open(schema_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Usa regex para encontrar nomes de colunas na instrução CREATE TABLE
        # Isso é mais robusto que parsing simples.
        matches = re.findall(r'^\s*(\w+)\s+(?:INTEGER|TEXT|REAL)', content, re.MULTILINE)
        if matches:
            logger.debug(f"Colunas válidas extraídas do schema: {matches}")
            return matches
        else:
            logger.warning(f"Nenhuma coluna encontrada no schema.sql em '{schema_path}'")
            return []
    except FileNotFoundError:
        logger.error(f"Arquivo de schema '{schema_path}' não encontrado.")
        return []

def _load_column_mappings() -> dict:
    try:
        with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
            mappings = json.load(f)
        inverted_map = {alias.strip().lower(): canonical for canonical, aliases in mappings.items() for alias in aliases}
        return inverted_map
    except Exception as e:
        logger.error(f"Falha ao carregar mapeamento de colunas: {e}")
        return {}

def extract_data_from_excel(file_path: str) -> Optional[pd.DataFrame]:
    logger.info(f"Iniciando extração de dados de '{file_path}'...")
    try:
        valid_db_columns = _get_valid_columns_from_schema(SCHEMA_PATH)
        if not valid_db_columns:
            raise ExtractionError("Não foi possível determinar as colunas válidas do banco de dados.")

        column_mappings = _load_column_mappings()
        
        all_sheets_data = []
        xl_file = pd.ExcelFile(file_path, engine='openpyxl')
        
        for sheet_name in xl_file.sheet_names:
            sheet_df = xl_file.parse(sheet_name, header=None)
            
            header_row_idx = None
            for idx, value in enumerate(sheet_df.iloc[:, 0]):
                if pd.notna(value) and str(value).strip() != '':
                    header_row_idx = idx
                    break
            
            if header_row_idx is not None:
                headers = sheet_df.iloc[header_row_idx].tolist()
                
                # CORREÇÃO: Limpa e valida os cabeçalhos antes de usá-los
                cleaned_headers = []
                for h in headers:
                    if pd.isna(h):
                        cleaned_headers.append(f"unnamed_{len(cleaned_headers)}")
                    else:
                        # Converte para string e remove espaços extras
                        cleaned_h = str(h).strip()
                        # Filtra cabeçalhos malformados como "Incluir:"
                        if len(cleaned_h) > 30 or ':' in cleaned_h: 
                            cleaned_headers.append(f"malformed_{len(cleaned_headers)}")
                        else:
                            cleaned_headers.append(cleaned_h)

                sheet_df.columns = cleaned_headers
                sheet_df = sheet_df.drop(sheet_df.index[:header_row_idx + 1]).reset_index(drop=True)
                sheet_df = sheet_df.dropna(axis=1, how='all')
                
                if not sheet_df.empty:
                    all_sheets_data.append(sheet_df)
            else:
                 logger.warning(f"Planilha '{sheet_name}' em '{file_path}' não possui cabeçalho identificável.")

        if not all_sheets_data:
             logger.warning(f"Nenhum dado válido encontrado em '{file_path}'.")
             return None

        # CORREÇÃO: Usa 'outer' join para manter todas as colunas de todas as planilhas
        combined_df = pd.concat(all_sheets_data, ignore_index=True, sort=False, join='outer')
        combined_df.dropna(how='all', inplace=True)
        
        if combined_df.empty:
            return None
        
        # Renomeia colunas para o padrão canônico
        rename_map = {
            col: column_mappings.get(str(col).strip().lower(), str(col).strip())
            for col in combined_df.columns
        }
        combined_df.rename(columns=rename_map, inplace=True)
        
        # CORREÇÃO CRÍTICA: Filtra o DataFrame para conter APENAS as colunas que existem no banco.
        final_cols = [col for col in valid_db_columns if col in combined_df.columns]
        final_df = combined_df[final_cols]
        
        # Normalização de tipos (agora em um DF já filtrado)
        if 'numero_ssa' in final_df.columns:
            final_df['numero_ssa'] = pd.to_numeric(final_df['numero_ssa'], errors='coerce').astype('Int64')
        if 'data_cadastro' in final_df.columns:
            final_df['data_cadastro'] = pd.to_datetime(final_df['data_cadastro'], errors='coerce', dayfirst=True)
        
        logger.info(f"Extração concluída com sucesso. {len(final_df)} linhas extraídas e validadas contra o schema.")
        return final_df

    except Exception as e:
        logger.error(f"Erro inesperado ao processar '{file_path}': {e}", exc_info=True)
        return None