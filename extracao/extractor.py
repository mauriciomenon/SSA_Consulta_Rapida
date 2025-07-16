# extracao/extractor.py (v6.1 - Refatoracao de data)
import pandas as pd
import json
import os
from typing import Tuple, Optional, Dict

CONFIG_PATH = os.path.join('config', 'column_mappings.json')

def _load_column_mappings() -> dict:
    """Carrega o mapeamento de nomes de colunas a partir do arquivo JSON."""
    try:
        with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
            mappings = json.load(f)
        # Inverte o mapa para {alias: canonical} para uso no rename()
        return {alias: canonical for canonical, aliases in mappings.items() for alias in aliases}
    except (FileNotFoundError, json.JSONDecodeError):
        print("AVISO: Arquivo 'column_mappings.json' nao encontrado ou invalido. A normalizacao de colunas pode falhar.")
        return {}

def _normalize_datatypes(df: pd.DataFrame) -> pd.DataFrame:
    """Converte colunas-chave para tipos de dados padronizados, especialmente datas."""
    if 'data_cadastro' in df.columns:
        # REFATORACAO: Adicionado dayfirst=True para interpretar corretamente
        # formatos de data brasileiros (dd/mm/yyyy) e silenciar o UserWarning.
        df['data_cadastro'] = pd.to_datetime(
            df['data_cadastro'], 
            errors='coerce',
            dayfirst=True
        )
        # O print foi removido para deixar a saida do importador mais limpa.
        # A operacao e confiavel e nao precisa ser anunciada a cada arquivo.
    return df

def read_report(file_path: str) -> Tuple[Optional[pd.DataFrame], Optional[Dict[str, int]]]:
    """
    Le um relatorio Excel, normaliza os nomes das colunas e os tipos de dados.
    """
    rename_map = _load_column_mappings()
    try:
        # O cabecalho esta na segunda linha (indice 1)
        df = pd.read_excel(file_path, header=1)
        df.rename(columns=rename_map, inplace=True)
        
        # Remove colunas que so contem valores nulos (comuns em relatorios mal formatados)
        df.dropna(axis=1, how='all', inplace=True)

        df = _normalize_datatypes(df)
        
        return df, {name: i for i, name in enumerate(df.columns)}
    except Exception as e:
        print(f"ERRO ao processar o arquivo '{file_path}': {e}")
        return None, None
