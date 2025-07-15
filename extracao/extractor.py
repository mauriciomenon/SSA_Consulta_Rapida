# extracao/extractor.py (versão 6 - estável)
import pandas as pd
import json
import os
from typing import Tuple, Optional, Dict

CONFIG_PATH = os.path.join('config', 'column_mappings.json')

def _load_column_mappings() -> dict:
    try:
        with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
            mappings = json.load(f)
        return {alias: canonical for canonical, aliases in mappings.items() for alias in aliases}
    except:
        return {}

def _normalize_datatypes(df: pd.DataFrame) -> pd.DataFrame:
    """Converte colunas-chave para tipos de dados padronizados."""
    if 'data_cadastro' in df.columns:
        # pd.to_datetime é poderoso. 'coerce' transforma erros em NaT (Not a Time).
        # Removido 'dayfirst=True' para deixar o pandas inferir o formato e evitar warnings.
        df['data_cadastro'] = pd.to_datetime(
            df['data_cadastro'], 
            errors='coerce'
        )
        print("Coluna 'data_cadastro' normalizada para datetime.")
    return df

def read_report(file_path: str) -> Tuple[Optional[pd.DataFrame], Optional[Dict[str, int]]]:
    """Lê, normaliza nomes de colunas e normaliza tipos de dados de um relatório."""
    rename_map = _load_column_mappings()
    try:
        df = pd.read_excel(file_path, header=1)
        df.rename(columns=rename_map, inplace=True)
        df = _normalize_datatypes(df)
        df.dropna(axis=1, how='all', inplace=True)
        return df, {name: i for i, name in enumerate(df.columns)}
    except Exception as e:
        print(f"ERRO ao processar o arquivo '{file_path}': {e}")
        return None, None