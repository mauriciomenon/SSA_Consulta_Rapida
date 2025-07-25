# exportacao/exporter.py 20250725 175000 (v3.1 - Tratamento de Erros e Logging)
"""
Modulo para exportar DataFrames para diferentes formatos de arquivo.
"""

import pandas as pd
import os
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

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

    # --- Exportacao ---
    formats_and_paths = {
        'CSV': (f"{base_filename}.csv", lambda path: df_to_export.to_csv(path, index=False, encoding='utf-8-sig')),
        'XLSX': (f"{base_filename}.xlsx", lambda path: df_to_export.to_excel(path, index=False, engine='openpyxl')),
        'JSON': (f"{base_filename}.json", lambda path: df_to_export.to_json(path, orient='records', indent=4, force_ascii=False, date_format='iso'))
    }

    success_count = 0
    for format_name, (filename, export_func) in formats_and_paths.items():
        path = os.path.join(output_dir, filename)
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
