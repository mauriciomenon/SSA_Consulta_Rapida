# exportacao/exporter.py 20250725 175000 (v3.1 - Tratamento de Erros e Logging)
"""
Modulo para exportar DataFrames para diferentes formatos de arquivo.
"""

import pandas as pd
import os
import logging
import re
from pathlib import Path
from typing import Dict

logger = logging.getLogger(__name__)
SAFE_EXPORT_BASENAME_RE = re.compile(r"^[A-Za-z0-9_. -]+$")
SPREADSHEET_FORMULA_PREFIXES = ("=", "+", "-", "@")
SPREADSHEET_CONTROL_PREFIXES = ("\t", "\r", "\n")


def sanitize_spreadsheet_cell(value):
    if not isinstance(value, str):
        return value
    if value.startswith(SPREADSHEET_CONTROL_PREFIXES):
        return "'" + value
    stripped = value.lstrip(" \t\r\n")
    if stripped.startswith(SPREADSHEET_FORMULA_PREFIXES):
        return "'" + value
    return value


def sanitize_spreadsheet_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    sanitized = df.copy()
    sanitized.columns = [
        sanitize_spreadsheet_cell(str(column)) for column in sanitized.columns
    ]
    for column in sanitized.columns:
        if pd.api.types.is_object_dtype(sanitized[column]) or pd.api.types.is_string_dtype(
            sanitized[column]
        ):
            sanitized[column] = sanitized[column].map(sanitize_spreadsheet_cell)
    return sanitized

def export_dataframe(df: pd.DataFrame, base_filename: str, output_dir: str, display_map: Dict[str, str]):
    """
    Exporta um DataFrame para CSV, XLSX e JSON.

    Args:
        df (pd.DataFrame): O DataFrame a ser exportado.
        base_filename (str): O nome base para os arquivos de exportacao.
        output_dir (str): O diretorio onde os arquivos serao salvos.
        display_map (Dict[str, str]): Mapeamento de colunas internas para nomes de exibicao.
    """
    if df.empty:
        logger.warning("DataFrame vazio fornecido para exportação.")
        print("Aviso: Nenhum dado para exportar.")
        return

    safe_base_filename = str(base_filename or "").strip()
    if (
        not safe_base_filename
        or "/" in safe_base_filename
        or "\\" in safe_base_filename
        or safe_base_filename in {".", ".."}
        or not SAFE_EXPORT_BASENAME_RE.fullmatch(safe_base_filename)
    ):
        logger.error("Nome base de exportacao invalido: %r", base_filename)
        print("Erro: Nome de exportacao invalido.")
        return

    # --- Preparacao ---
    try:
        os.makedirs(output_dir, exist_ok=True)
        logger.debug(f"Diretório de saída garantido: {output_dir}")
    except OSError as e:
        logger.error(f"Falha ao criar diretório de saída '{output_dir}': {e}")
        print(f"Erro: Não foi possível criar o diretório de saída '{output_dir}'.")
        return

    # Renomeia colunas para nomes de exibição
    df_to_export = df.rename(columns=display_map)
    spreadsheet_df = sanitize_spreadsheet_dataframe(df_to_export)

    # --- Exportacao ---
    formats_and_paths = {
        'CSV': (f"{safe_base_filename}.csv", lambda path: spreadsheet_df.to_csv(path, index=False, encoding='utf-8-sig')),
        'XLSX': (f"{safe_base_filename}.xlsx", lambda path: spreadsheet_df.to_excel(path, index=False, engine='openpyxl')),
        'JSON': (f"{safe_base_filename}.json", lambda path: df_to_export.to_json(path, orient='records', indent=4, force_ascii=False, date_format='iso'))
    }

    success_count = 0
    output_root = Path(output_dir).resolve()
    for format_name, (filename, export_func) in formats_and_paths.items():
        path_obj = (output_root / filename).resolve()
        try:
            path_obj.relative_to(output_root)
        except ValueError:
            logger.error(
                "Destino de exportacao fora do diretorio permitido: %s", path_obj
            )
            print(f"Erro: destino invalido para {format_name}.")
            continue
        path = str(path_obj)
        try:
            export_func(path)
            logger.info(f"Exportação para {format_name} concluída: {path}")
            success_count += 1
        except pd.errors.EmptyDataError:
            logger.warning(f"Dados vazios ao exportar para {format_name}. Arquivo pode estar vazio ou corrompido.")
            print(f"Aviso: Dados vazios ao exportar para {format_name}.")
        except (IOError, PermissionError) as e:
            logger.error(f"Erro de E/S ao exportar para {format_name} ({path}): {e}")
            print(f"Erro: Permissão negada ou erro de E/S ao salvar {format_name} em '{path}'.")
        except Exception as e:
            logger.error(f"Erro inesperado ao exportar para {format_name} ({path}): {e}")
            print(f"Erro: Falha ao exportar para {format_name}. Consulte os logs para mais detalhes.")

    if success_count > 0:
        print(f"Exportação concluída com sucesso para {success_count} formato(s).")
    else:
        print("Erro: Nenhum arquivo foi exportado com sucesso.")
