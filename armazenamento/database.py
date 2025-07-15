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

def query_db(db_path: str, table_name: str, search_terms: List[str]) -> pd.DataFrame:
    """
    Consulta o banco de dados com uma lista de termos de pesquisa.
    A busca é feita em todas as colunas de texto com um 'E' lógico entre os termos.

    Args:
        db_path (str): Caminho para o arquivo do banco de dados.
        table_name (str): Nome da tabela a ser consultada.
        search_terms (List[str]): Lista de strings para buscar.

    Returns:
        pd.DataFrame: DataFrame com os resultados da consulta.
    """
    conn = None
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Pega o nome de todas as colunas da tabela
        cursor.execute(f"PRAGMA table_info({table_name});")
        columns = [row[1] for row in cursor.fetchall()]

        # Constrói a query dinamicamente
        base_query = f"SELECT * FROM {table_name}"
        
        if search_terms:
            where_clauses = []
            params = []
            for term in search_terms:
                # Para cada termo, cria uma busca em todas as colunas (condição OR)
                term_clause = " OR ".join([f'"{col}" LIKE ?' for col in columns])
                where_clauses.append(f"({term_clause})")
                # Adiciona o parâmetro para cada coluna
                params.extend([f"%{term}%"] * len(columns))

            # Junta todas as buscas de termos com AND
            base_query += " WHERE " + " AND ".join(where_clauses)
            
            # pd.read_sql_query é a forma mais segura e fácil de executar
            df = pd.read_sql_query(base_query, conn, params=params)
        else:
            # Se não houver termos, retorna a tabela inteira
            df = pd.read_sql_query(base_query, conn)
            
        return df

    except Exception as e:
        print(f"Erro ao consultar o banco de dados: {e}")
        return pd.DataFrame() # Retorna um DataFrame vazio em caso de erro
    finally:
        if conn:
            conn.close()
