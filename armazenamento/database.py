# armazenamento/database.py
import sqlite3
import pandas as pd
from typing import List

def save_to_db(df: pd.DataFrame, table_name: str, db_path: str):
    """
    Salva um DataFrame em uma tabela de um banco de dados SQLite.

    Se a tabela já existir, ela será substituída completamente.

    Args:
        df (pd.DataFrame): O DataFrame a ser salvo.
        table_name (str): O nome da tabela onde os dados serão salvos.
        db_path (str): O caminho para o arquivo do banco de dados SQLite.
    """
    try:
        conn = sqlite3.connect(db_path)
        
        # Usamos o método to_sql do pandas, que é extremamente eficiente.
        # if_exists='replace': apaga a tabela antiga e cria uma nova.
        # index=False: não salva o índice do DataFrame como uma coluna no BD.
        df.to_sql(name=table_name, con=conn, if_exists='replace', index=False)
        
        print(f"DataFrame salvo com sucesso na tabela '{table_name}' do banco '{db_path}'.")
        print(f"Total de {len(df)} linhas inseridas.")
        
    except Exception as e:
        print(f"Ocorreu um erro ao salvar os dados no banco: {e}")
    finally:
        if conn:
            conn.close()
