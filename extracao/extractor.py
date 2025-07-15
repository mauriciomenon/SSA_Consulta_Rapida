# extracao/extractor.py (versão 3 - com mapeamento de colunas)
import pandas as pd
import json
import os
from typing import Tuple, Optional, Dict

CONFIG_PATH = os.path.join('config', 'column_mappings.json')

def _load_column_mappings() -> dict:
    """Carrega os mapeamentos de coluna do arquivo JSON."""
    try:
        with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
            mappings = json.load(f)
        
        # Inverte o mapa para o formato {alias: canonical_name} para o rename
        rename_map = {}
        for canonical_name, aliases in mappings.items():
            for alias in aliases:
                rename_map[alias] = canonical_name
        return rename_map
    except FileNotFoundError:
        print(f"AVISO: Arquivo de mapeamento '{CONFIG_PATH}' não encontrado. Usando nomes de coluna originais.")
        return {}
    except json.JSONDecodeError:
        print(f"ERRO: Arquivo de mapeamento '{CONFIG_PATH}' contém um JSON inválido.")
        return {}


def read_report(file_path: str) -> Tuple[Optional[pd.DataFrame], Optional[Dict[str, int]]]:
    """
    Lê um relatório, aplica o mapeamento de colunas para padronizá-las e
    retorna o DataFrame e o mapa de colunas padronizadas.
    """
    rename_map = _load_column_mappings()

    try:
        df = pd.read_excel(file_path, header=1)
        
        # Renomeia as colunas com base no mapa carregado
        df.rename(columns=rename_map, inplace=True)
        
        df.dropna(axis=1, how='all', inplace=True)

        # O mapa de colunas agora é criado com os nomes canônicos
        column_map = {name: i for i, name in enumerate(df.columns)}

        print(f"Relatório '{file_path}' lido e normalizado com sucesso.")
        return df, column_map

    except FileNotFoundError:
        print(f"Erro: O arquivo '{file_path}' não foi encontrado.")
        return None, None
    except Exception as e:
        print(f"Ocorreu um erro inesperado ao ler o arquivo '{file_path}': {e}")
        return None, None