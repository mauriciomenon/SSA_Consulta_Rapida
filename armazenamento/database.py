# armazenamento/database.py 20250725 161500 (v2.1 - Boas Praticas Confirmadas)
"""
Módulo para interação com o banco de dados SQLite.

Responsável por criar tabelas, inserir DataFrames e consultar dados.
"""

import sqlite3
import pandas as pd
import os
import logging
from contextlib import contextmanager

logger = logging.getLogger(__name__)

# --- Gerenciamento de Conexão ---

@contextmanager
def get_db_connection(db_path: str):
    """
    Gerenciador de contexto para obter uma conexão com o banco de dados.

    Args:
        db_path (str): Caminho para o arquivo do banco de dados SQLite.

    Yields:
        sqlite3.Connection: Uma conexão ativa com o banco de dados.
    """
    conn = None
    try:
        # Verifica se o diretório do DB existe
        db_dir = os.path.dirname(db_path)
        if db_dir:
            os.makedirs(db_dir, exist_ok=True)
            
        conn = sqlite3.connect(db_path)
        # Configurações recomendadas para performance e segurança
        conn.execute("PRAGMA foreign_keys = ON") # Se estiver usando FKs
        yield conn
    except sqlite3.Error as e:
        logger.error(f"Erro de banco de dados: {e}")
        if conn:
            conn.rollback()
        raise
    finally:
        if conn:
            conn.close()

# --- Funções de Banco de Dados ---

# armazenamento/database.py

def initialize_database(db_path: str, schema_file: str = 'schema.sql'):
    """
    Inicializa o banco de dados, criando tabelas conforme o schema.
    Esta versao usa um caminho explicito para evitar problemas de resolucao.
    """
    import os
    
    # --- CAMINHO EXPLICITO E ABSOLUTO PARA O SCHEMA ---
    # Determina a raiz do projeto de forma robusta
    current_file_dir = os.path.dirname(os.path.abspath(__file__)) # .../SSA_Consulta_Rapida/armazenamento
    project_root = os.path.dirname(current_file_dir)              # .../SSA_Consulta_Rapida
    # Constroi o caminho absoluto esperado para o schema
    expected_schema_path = os.path.join(project_root, 'config', 'schema.sql')
    
    logger.info(f"[FORCANDO_SCHEMA] Tentando usar schema em: '{expected_schema_path}'")
    
    # --- VERIFICA SE O ARQUIVO EXISTE ---
    if not os.path.exists(expected_schema_path):
        logger.critical(f"[FORCANDO_SCHEMA] ARQUIVO NAO ENCONTRADO: '{expected_schema_path}'")
        # Lista conteudo da pasta config para depuracao
        config_dir = os.path.join(project_root, 'config')
        if os.path.exists(config_dir):
            logger.info(f"[FORCANDO_SCHEMA] Conteudo da pasta config: {os.listdir(config_dir)}")
        raise FileNotFoundError(f"Schema nao encontrado em '{expected_schema_path}'")
        
    # --- LE O CONTEUDO ---
    try:
        with open(expected_schema_path, 'r', encoding='utf-8') as f:
            schema_sql = f.read()
        logger.debug(f"[FORCANDO_SCHEMA] Schema lido com sucesso. Tamanho: {len(schema_sql)} chars.")
    except Exception as e:
        logger.critical(f"[FORCANDO_SCHEMA] Erro ao ler schema: {e}")
        raise

    # --- APLICA O SCHEMA ---
    logger.info("[FORCANDO_SCHEMA] Aplicando schema ao banco de dados...")
    try:
        with get_db_connection(db_path) as conn:
            conn.executescript(schema_sql)
            conn.commit()
        logger.info("[FORCANDO_SCHEMA] Banco de dados inicializado com sucesso.")
        return True
    except Exception as e:
        logger.critical(f"[FORCANDO_SCHEMA] Falha ao aplicar schema: {e}")
        raise

def query_db(db_path: str, table_name: str, query: str = "", params: tuple = ()) -> pd.DataFrame:
    """
    Consulta o banco de dados e retorna um DataFrame.

    Args:
        db_path (str): Caminho para o banco de dados.
        table_name (str): Nome da tabela (usado se `query` estiver vazio).
        query (str, optional): Query SQL customizada. Se vazia, seleciona tudo da tabela.
        params (tuple, optional): Parâmetros para a query.

    Returns:
        pd.DataFrame: Resultado da consulta.
    """
    if not query:
        query = f"SELECT * FROM {table_name}"

    logger.debug(f"Executando consulta: {query} com params: {params}")
    try:
        with get_db_connection(db_path) as conn:
            # pd.read_sql_query é ótimo para SELECTs
            df = pd.read_sql_query(query, conn, params=params)
        logger.debug(f"Consulta retornou {len(df)} linhas.")
        return df
    except Exception as e:
        logger.error(f"Erro ao executar consulta '{query}': {e}")
        # Retorna DataFrame vazio em caso de erro
        return pd.DataFrame()

def insert_dataframe_to_db(df: pd.DataFrame, db_path: str, table_name: str, if_exists: str = 'append') -> bool:
    """
    Insere um DataFrame em uma tabela do banco de dados.

    Args:
        df (pd.DataFrame): O DataFrame a ser inserido.
        db_path (str): Caminho para o banco de dados.
        table_name (str): Nome da tabela de destino.
        if_exists (str): O que fazer se a tabela já existir ('fail', 'replace', 'append').

    Returns:
        bool: True se a inserção foi bem-sucedida, False caso contrário.
    """
    if df.empty:
        logger.warning("DataFrame vazio fornecido para inserção. Nada a fazer.")
        return True

    logger.debug(f"Inserindo {len(df)} linhas no banco de dados '{db_path}', tabela '{table_name}'...")
    try:
        with get_db_connection(db_path) as conn:
            # to_sql é o método recomendado do Pandas
            # index=False evita inserir a coluna de índice do DataFrame
            df.to_sql(table_name, conn, if_exists=if_exists, index=False, method='multi')
            conn.commit()
        logger.info(f"{len(df)} linhas inseridas com sucesso na tabela '{table_name}'.")
        return True
    except Exception as e:
        logger.error(f"Falha ao inserir dados na tabela '{table_name}': {e}")
        return False
