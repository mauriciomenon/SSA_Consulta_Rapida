# armazenamento/database.py (v2.1 - Correcao de NameError)
import sqlite3
import pandas as pd
from typing import List

def _get_existing_columns(conn: sqlite3.Connection, table_name: str) -> List[str]:
    """
    Busca e retorna a lista de nomes de colunas existentes em uma tabela.
    Usa o comando PRAGMA table_info, que e eficiente e seguro.
    """
    try:
        cursor = conn.execute(f"PRAGMA table_info({table_name})")
        return [row[1] for row in cursor.fetchall()]
    except sqlite3.Error:
        # A tabela pode nao existir ainda na primeira execucao
        return []

def _add_missing_columns(conn: sqlite3.Connection, table_name: str, df_columns: List[str]):
    """
    Compara as colunas do DataFrame com as da tabela e adiciona as que faltam.
    """
    existing_columns = _get_existing_columns(conn, table_name)
    missing_columns = [col for col in df_columns if col not in existing_columns]

    if not missing_columns:
        return # Nenhuma alteracao necessaria

    cursor = conn.cursor()
    print(f"Novas colunas encontradas. Atualizando banco de dados: {', '.join(missing_columns)}")
    for column in missing_columns:
        try:
            # Adiciona a coluna. Usamos TEXT como um tipo de dado universal e seguro.
            # A sanitizacao do nome da coluna evita injecao de SQL.
            safe_column_name = f'"{column}"'
            cursor.execute(f"ALTER TABLE {table_name} ADD COLUMN {safe_column_name} TEXT")
            print(f" -> Coluna '{column}' adicionada com sucesso.")
        except sqlite3.Error as e:
            print(f"AVISO: Nao foi possivel adicionar a coluna '{column}'. Erro: {e}")
    conn.commit()

def save_to_db(df: pd.DataFrame, table_name: str, db_path: str):
    """
    Salva um DataFrame em uma tabela SQLite, garantindo que todas as colunas
    do DataFrame existam na tabela antes da insercao.
    """
    if df.empty:
        print("DataFrame vazio, nada para salvar no banco de dados.")
        return

    try:
        with sqlite3.connect(db_path) as conn:
            # A abordagem com if_exists='replace' e mais simples e robusta.
            # Ela recria a tabela a cada importacao, garantindo que o schema
            # esteja sempre perfeitamente sincronizado com os dados mais recentes.
            # Isso elimina a necessidade de chamar a funcao _add_missing_columns
            # e evita potenciais conflitos de tipo de dados.
            df.to_sql(table_name, conn, if_exists='replace', index=False)
            
            print(f"\nOperacao concluida: {len(df)} registros foram salvos com sucesso na tabela '{table_name}'.")
            print(f"O banco de dados '{db_path}' esta atualizado.")

    except sqlite3.Error as e:
        print(f"ERRO CRITICO ao interagir com o banco de dados: {e}")
    except Exception as e:
        print(f"ERRO INESPERADO durante a operacao com o banco de dados: {e}")


def query_db(db_path: str, table_name: str, columns: List[str] = None) -> pd.DataFrame:
    """
    Consulta uma tabela SQLite e retorna os dados como um DataFrame pandas.
    Se 'columns' for uma lista vazia ou None, seleciona todas as colunas.
    """
    if not columns:
        select_clause = "*"
    else:
        # Garante que os nomes das colunas sejam seguros para a consulta
        safe_columns = [f'"{col}"' for col in columns]
        select_clause = ", ".join(safe_columns)

    try:
        with sqlite3.connect(db_path) as conn:
            # Verifica se a tabela existe antes de consultar
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table_name,))
            if cursor.fetchone() is None:
                print(f"AVISO: A tabela '{table_name}' nao existe no banco de dados '{db_path}'.")
                return pd.DataFrame()

            query = f"SELECT {select_clause} FROM {table_name}"
            df = pd.read_sql_query(query, conn)

            # Normaliza os tipos de dados que sao lidos do banco
            if 'data_cadastro' in df.columns:
                df['data_cadastro'] = pd.to_datetime(df['data_cadastro'], errors='coerce')

            return df
    except sqlite3.Error as e:
        print(f"ERRO ao consultar o banco de dados: {e}")
        return pd.DataFrame()
    except Exception as e:
        print(f"ERRO INESPERADO ao ler o banco de dados: {e}")
        return pd.DataFrame()
