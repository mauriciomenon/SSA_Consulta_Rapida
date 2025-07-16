# exportacao/exporter.py (v2.0 - Cabeçalhos Amigáveis)
import os
import pandas as pd
from typing import Dict

def export_dataframe(df: pd.DataFrame, base_filename: str, export_dir: str, display_map: Dict[str, str]):
    """
    Exporta um DataFrame para múltiplos formatos (CSV, Excel, JSON)
    usando nomes de coluna amigáveis.

    Args:
        df (pd.DataFrame): O DataFrame a ser exportado.
        base_filename (str): O nome base para os arquivos, sem extensão.
        export_dir (str): O diretório onde os arquivos serão salvos.
        display_map (Dict[str, str]): O mapa para renomear as colunas.
    """
    if df.empty:
        print("Nenhum dado para exportar.")
        return

    os.makedirs(export_dir, exist_ok=True)

    df_to_export = df.copy()

    # Remove a coluna de índice '#', que é apenas para exibição na tela
    if '#' in df_to_export.columns:
        df_to_export.drop(columns=['#'], inplace=True)
    
    # Renomeia as colunas para os nomes amigáveis antes de exportar
    df_to_export.rename(columns=display_map, inplace=True)

    path_csv = os.path.join(export_dir, f"{base_filename}.csv")
    path_xlsx = os.path.join(export_dir, f"{base_filename}.xlsx")
    path_json = os.path.join(export_dir, f"{base_filename}.json")

    try:
        df_to_export.to_csv(path_csv, index=False, encoding='utf-8-sig')
        print(f" -> Sucesso: Arquivo salvo em '{path_csv}'")

        df_to_export.to_excel(path_xlsx, index=False, engine='openpyxl')
        print(f" -> Sucesso: Arquivo salvo em '{path_xlsx}'")

        df_to_export.to_json(path_json, orient='records', indent=4, force_ascii=False, date_format='iso')
        print(f" -> Sucesso: Arquivo salvo em '{path_json}'")

        print("\nExportação concluída com sucesso!")

    except Exception as e:
        print(f"\nERRO CRÍTICO durante a exportação: {e}")
        print("Verifique se tem permissão para escrever no diretório e se as bibliotecas (openpyxl) estão instaladas.")
