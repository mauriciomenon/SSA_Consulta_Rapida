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
        # Corrigido para usar .loc e evitar SettingWithCopyWarning
        if 'numero_ssa' in final_df.columns:
            final_df.loc[:, 'numero_ssa'] = pd.to_numeric(final_df['numero_ssa'], errors='coerce').astype('Int64')
        if 'data_cadastro' in final_df.columns:
            final_df.loc[:, 'data_cadastro'] = pd.to_datetime(final_df['data_cadastro'], errors='coerce', dayfirst=True)
        
        logger.info(f"Extração concluída com sucesso. {len(final_df)} linhas extraídas e validadas contra o schema.")
        return final_df

    except Exception as e:
        logger.error(f"Erro inesperado ao processar '{file_path}': {e}", exc_info=True)
        raise ExtractionError(f"Erro ao extrair dados do arquivo {file_path}") from e

def read_report(file_path: str):
    """
    Lê um relatório Excel e retorna um DataFrame com colunas normalizadas (canônicas)
    sem filtrar estritamente pelo schema do banco. Retorna também um pequeno
    dicionário de metadados.

    Retorno: (df, info)
      - df: pandas.DataFrame com colunas renomeadas conforme mapeamento
      - info: dict com metadados simples (não utilizado nos testes)
    """
    logger.info(f"Lendo relatório: {file_path}")
    try:
        # Carrega mapeamentos e garante chaves normalizadas para robustez a mocks de teste
        column_mappings = _load_column_mappings() or {}
        column_mappings = {str(k).strip().lower(): v for k, v in column_mappings.items()}

        all_sheets_data = []
        xl_file = pd.ExcelFile(file_path, engine='openpyxl')
        sheet_names = list(xl_file.sheet_names)

        for sheet_name in sheet_names:
            sheet_df = xl_file.parse(sheet_name, header=None)

            # Detecta a linha de cabeçalho como a primeira linha com valor não vazio na 1ª coluna
            header_row_idx = None
            for idx, value in enumerate(sheet_df.iloc[:, 0]):
                if pd.notna(value) and str(value).strip() != '':
                    header_row_idx = idx
                    break

            if header_row_idx is not None:
                headers = sheet_df.iloc[header_row_idx].tolist()

                # Limpa cabeçalhos
                cleaned_headers = []
                for h in headers:
                    if pd.isna(h):
                        cleaned_headers.append(f"unnamed_{len(cleaned_headers)}")
                    else:
                        cleaned_h = str(h).strip()
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
            return None, {"sheets": sheet_names, "rows": 0, "columns": []}

        # Concatena mantendo todas as colunas
        combined_df = pd.concat(all_sheets_data, ignore_index=True, sort=False, join='outer')
        combined_df.dropna(how='all', inplace=True)

        if combined_df.empty:
            return None, {"sheets": sheet_names, "rows": 0, "columns": []}

        # Renomeia colunas conforme mapeamento (case-insensitive)
        rename_map = {
            col: column_mappings.get(str(col).strip().lower(), str(col).strip())
            for col in combined_df.columns
        }
        combined_df.rename(columns=rename_map, inplace=True)

        # Remove colunas totalmente vazias após renomear
        combined_df = combined_df.dropna(axis=1, how='all')

        # Normalização de tipos
        if 'numero_ssa' in combined_df.columns:
            combined_df.loc[:, 'numero_ssa'] = pd.to_numeric(combined_df['numero_ssa'], errors='coerce').astype('Int64')
        if 'data_cadastro' in combined_df.columns:
            # Converte para datetime e garante dtype numpy datetime64[ns]
            s_dt = pd.to_datetime(combined_df['data_cadastro'], errors='coerce', dayfirst=True)
            try:
                combined_df.loc[:, 'data_cadastro'] = s_dt.values.astype('datetime64[ns]')
            except Exception:
                combined_df.loc[:, 'data_cadastro'] = s_dt

        # Garantia final de dtype para testes/confiança
        if 'data_cadastro' in combined_df.columns:
            try:
                combined_df.loc[:, 'data_cadastro'] = pd.DatetimeIndex(
                    pd.to_datetime(combined_df['data_cadastro'], errors='coerce', dayfirst=True)
                )
            except Exception:
                pass

        # Refino final de tipos exigidos pelos testes
        try:
            if 'numero_ssa' in combined_df.columns:
                combined_df['numero_ssa'] = pd.to_numeric(combined_df['numero_ssa'], errors='coerce').astype('Int64')
        except Exception:
            pass
        try:
            if 'data_cadastro' in combined_df.columns:
                combined_df['data_cadastro'] = pd.to_datetime(combined_df['data_cadastro'], errors='coerce', dayfirst=True)
                combined_df['data_cadastro'] = combined_df['data_cadastro'].astype('datetime64[ns]')
        except Exception:
            pass

        info = {
            "sheets": sheet_names,
            "rows": int(len(combined_df)),
            "columns": list(combined_df.columns),
        }
        logger.info(f"Relatório lido com sucesso. Linhas: {info['rows']}")
        return combined_df, info

    except Exception as e:
        logger.error(f"Erro ao ler relatório '{file_path}': {e}", exc_info=True)
        raise ExtractionError(f"Erro ao ler relatório do arquivo {file_path}") from e