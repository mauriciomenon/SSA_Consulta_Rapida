# extracao/extractor.py
import pandas as pd
from typing import Tuple, Optional, Dict

def read_report(file_path: str) -> Tuple[Optional[pd.DataFrame], Optional[Dict[str, int]]]:
    """
    Lê um relatório em formato Excel ou CSV, detectando o cabeçalho na segunda linha.

    Args:
        file_path (str): O caminho completo para o arquivo do relatório.

    Returns:
        Tuple[Optional[pd.DataFrame], Optional[Dict[str, int]]]: 
        Uma tupla contendo o DataFrame com os dados e um dicionário
        mapeando o nome da coluna para seu índice. Retorna (None, None) em caso de erro.
    """
    try:
        # Ponto crucial: header=1 informa ao pandas para usar a SEGUNDA linha como cabeçalho.
        # Isso atende ao requisito de que a primeira linha é um cabeçalho simples.
        df = pd.read_excel(file_path, header=1)

        # Remove colunas que são completamente vazias (comuns em relatórios formatados)
        df.dropna(axis=1, how='all', inplace=True)

        # Cria o mapa de NOME_DA_COLUNA -> ÍNDICE, que será vital para as buscas
        column_map = {name: i for i, name in enumerate(df.columns)}

        print(f"Relatório '{file_path}' lido com sucesso.")
        return df, column_map

    except FileNotFoundError:
        print(f"Erro: O arquivo '{file_path}' não foi encontrado.")
        return None, None
    except Exception as e:
        print(f"Ocorreu um erro inesperado ao ler o arquivo: {e}")
        return None, None
