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

from utils import data_validation
from utils.file_metadata import get_file_metadata, should_update_ssa

# Configura logger específico para este módulo
logger = logging.getLogger(__name__)

# --- Gerenciamento de Conexão ---

def normalize_numero_ssa(value):
    """Normaliza o número da SSA para 9 dígitos conforme regras de exibição.
    - Remove zeros à esquerda
    - Se até 5 dígitos, prefixa ano corrente (2025) e completa 5 dígitos
    - Se menos de 9 dígitos, completa à esquerda até 9
    - Se já tiver 9 dígitos numéricos, mantém
    Caso não seja numérico, retorna como string original.
    """
    try:
        # Trata nulos explicitamente
        if value is None or (isinstance(value, float) and pd.isna(value)):
            return None
        s = str(value).strip()
        if s == "" or s.lower() in {"nan", "none", "null"}:
            return None
        s = s.lstrip('0')
        if s.isdigit() and len(s) <= 5:
            return f"2025{s.zfill(5)}"
        if s.isdigit() and len(s) == 9:
            return s
        if s.isdigit() and len(s) < 9:
            return s.zfill(9)
        return s
    except Exception:
        return value

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
        conn.execute("PRAGMA foreign_keys = ON")  # Se estiver usando FKs
        # PRAGMAs seguros para melhorar performance sem comprometer integridade
        try:
            conn.execute("PRAGMA journal_mode = WAL")
            conn.execute("PRAGMA synchronous = NORMAL")
            conn.execute("PRAGMA temp_store = MEMORY")
            conn.execute("PRAGMA busy_timeout = 3000")  # 3s de espera para locks
        except sqlite3.Error:
            # Ignora falhas em PRAGMAs (ambiente pode não suportar todos)
            pass
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

def prepare_dataframe_for_sqlite(df):
    """
    Prepara um DataFrame para inserção no SQLite, convertendo tipos problemáticos.
    
    Args:
        df (pd.DataFrame): DataFrame original
        
    Returns:
        pd.DataFrame: DataFrame com tipos convertidos para SQLite
    """
    df_prepared = df.copy()
    
    for col in df_prepared.columns:
        # Verifica se a coluna contém objetos Timestamp
        if df_prepared[col].dtype == 'object':
            # Detecta se há Timestamp objects na coluna
            sample_non_null = df_prepared[col].dropna()
            if len(sample_non_null) > 0:
                first_value = sample_non_null.iloc[0]
                if hasattr(first_value, 'strftime'):  # É um objeto de data/hora
                    try:
                        # Converte Timestamp para string
                        df_prepared[col] = df_prepared[col].apply(
                            lambda x: x.strftime('%Y-%m-%d %H:%M:%S') if pd.notna(x) and hasattr(x, 'strftime') else x
                        )
                        logger.debug(f"Coluna '{col}' convertida de Timestamp para string")
                    except Exception as e:
                        logger.warning(f"Erro ao processar coluna '{col}': {e}. Convertendo para string.")
                        df_prepared[col] = df_prepared[col].astype(str)
    
    return df_prepared

# --- Funções de Banco de Dados ---

def initialize_database(db_path: str, schema_file: str = 'schema.sql'):
    """
    Inicializa o banco de dados, criando tabelas conforme o schema.
    Esta versao usa um caminho explicito para evitar problemas de resolucao.
    """
    import os

    # 1) Se schema_file for um caminho existente (absoluto ou relativo), usar diretamente
    schema_path = None
    if schema_file:
        # caminho absoluto fornecido e existente
        if os.path.isabs(schema_file) and os.path.exists(schema_file):
            schema_path = schema_file
        else:
            # relativo ao cwd
            rel_path = os.path.abspath(schema_file)
            if os.path.exists(rel_path):
                schema_path = rel_path

    # 2) Caso contrário, tenta caminho padrão no projeto: <root>/config/schema.sql
    if not schema_path:
        current_file_dir = os.path.dirname(os.path.abspath(__file__))  # .../SSA_Consulta_Rapida/armazenamento
        project_root = os.path.dirname(current_file_dir)               # .../SSA_Consulta_Rapida
        schema_path = os.path.join(project_root, 'config', 'schema.sql')

    logger.info(f"[SCHEMA] Usando schema em: '{schema_path}'")

    # --- VERIFICA SE O ARQUIVO EXISTE ---
    if not os.path.exists(schema_path):
        logger.critical(f"[SCHEMA] ARQUIVO NAO ENCONTRADO: '{schema_path}'")
        # Lista conteudo da pasta config para depuracao
        try:
            config_dir = os.path.join(project_root, 'config') if 'project_root' in locals() else None
            if config_dir and os.path.exists(config_dir):
                logger.info(f"[SCHEMA] Conteudo da pasta config: {os.listdir(config_dir)}")
        except Exception:
            pass
        raise FileNotFoundError(f"Schema nao encontrado em '{schema_path}'")

    # --- LE O CONTEUDO ---
    try:
        with open(schema_path, 'r', encoding='utf-8') as f:
            schema_sql = f.read()
        logger.debug(f"[SCHEMA] Schema lido com sucesso. Tamanho: {len(schema_sql)} chars.")
    except Exception as e:
        logger.critical(f"[SCHEMA] Erro ao ler schema: {e}")
        raise

    # --- APLICA O SCHEMA ---
    logger.info("[SCHEMA] Aplicando schema ao banco de dados...")
    try:
        with get_db_connection(db_path) as conn:
            conn.executescript(schema_sql)
            conn.commit()
        logger.info("[SCHEMA] Banco de dados inicializado com sucesso.")
        return True
    except Exception as e:
        logger.critical(f"[SCHEMA] Falha ao aplicar schema: {e}")
        raise

def create_indexes(db_path: str) -> bool:
    """
    Cria índices para melhorar o desempenho das consultas.
    
    Args:
        db_path (str): Caminho para o banco de dados.
        
    Returns:
        bool: True se os índices foram criados com sucesso, False caso contrário.
    """
    try:
        with get_db_connection(db_path) as conn:
            conn.execute("CREATE INDEX IF NOT EXISTS idx_ssas_setor_executor ON ssas(setor_executor)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_ssas_situacao ON ssas(situacao)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_ssas_data_cadastro ON ssas(data_cadastro)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_ssas_numero_ssa ON ssas(numero_ssa)")
            conn.commit()
        logger.info("Índices criados com sucesso.")
        return True
    except Exception as e:
        logger.error(f"Falha ao criar índices: {e}")
        return False
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
    Insere um DataFrame em uma tabela do banco de dados em lotes (chunks)
    para evitar erros de limite de variáveis do SQLite.

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

    # CORREÇÃO: Define um chunksize para dividir grandes inserções.
    # 900 é um valor seguro, pois o limite do SQLite é geralmente 999
    # e depende do número de colunas.
    chunk_size = 900 // max(1, len(df.columns))
    
    logger.debug(f"Inserindo {len(df)} linhas em lotes de {chunk_size} no banco de dados '{db_path}', tabela '{table_name}'...")
    try:
        # Prepara DataFrame para SQLite (converte Timestamp e outros tipos problemáticos)
        df_prepared = prepare_dataframe_for_sqlite(df)

        with get_db_connection(db_path) as conn:
            # Usa to_sql com chunksize
            df_prepared.to_sql(
                table_name,
                conn,
                if_exists=if_exists,
                index=False,
                method='multi',
                chunksize=chunk_size,  # <--- a estratégia consolidada
                dtype='TEXT'  # Força todos os campos como texto para evitar problemas de tipo
            )
            conn.commit()
        logger.info(f"{len(df)} linhas inseridas com sucesso na tabela '{table_name}'.")
        return True
    except Exception as e:
        logger.error(f"Falha ao inserir dados na tabela '{table_name}': {e}")
        return False

def insert_dataframe_with_smart_upsert(
    df: pd.DataFrame, 
    db_path: str, 
    table_name: str, 
    file_path: str
) -> bool:
    """
    Insere um DataFrame com controle inteligente de duplicatas baseado na data do arquivo.
    
    Para cada SSA, verifica se já existe no banco e se o arquivo atual é mais recente.
    Só atualiza se o arquivo for mais recente que o registro existente.
    
    Args:
        df (pd.DataFrame): O DataFrame a ser inserido.
        db_path (str): Caminho para o banco de dados.
        table_name (str): Nome da tabela de destino.
        file_path (str): Caminho do arquivo Excel de origem (para extrair metadados).
        
    Returns:
        bool: True se a inserção foi bem-sucedida, False caso contrário.
    """
    if df.empty:
        logger.warning("DataFrame vazio fornecido para inserção. Nada a fazer.")
        return True
        
    # Extrai metadados do arquivo
    filename, file_datetime_iso, import_datetime_iso = get_file_metadata(file_path)
    
    # Adiciona colunas de metadados ao DataFrame
    df_with_metadata = df.copy()
    df_with_metadata['arquivo_origem'] = filename
    df_with_metadata['data_arquivo_origem'] = file_datetime_iso
    df_with_metadata['data_importacao'] = import_datetime_iso
    df_with_metadata['versao_dados'] = 1  # Será atualizado se necessário
    
    # Se não tem numero_ssa, usa inserção normal
    if 'numero_ssa' not in df_with_metadata.columns:
        logger.debug("DataFrame sem coluna 'numero_ssa', usando inserção normal")
        return insert_dataframe_to_db(df_with_metadata, db_path, table_name)
    
    # Remove SSAs inválidas (sem número)
    # Normaliza numero_ssa para consistência no banco (sem alterar outros campos)
    try:
        if 'numero_ssa' in df_with_metadata.columns:
            df_with_metadata['numero_ssa'] = df_with_metadata['numero_ssa'].apply(normalize_numero_ssa)
    except Exception:
        pass

    df_valid = df_with_metadata.dropna(subset=['numero_ssa'])
    if df_valid.empty:
        logger.warning("Nenhuma SSA válida encontrada (todas sem número)")
        return True
    
    logger.info(f"Processando {len(df_valid)} SSAs com controle de duplicatas inteligente...")
    
    try:
        with get_db_connection(db_path) as conn:
            # Para cada SSA, verifica se deve atualizar
            updates_count = 0
            inserts_count = 0
            skipped_count = 0
            
            for index, row in df_valid.iterrows():
                numero_ssa = row['numero_ssa']
                
                # Verifica se a SSA já existe no banco
                existing_query = f"""
                    SELECT data_arquivo_origem, versao_dados 
                    FROM {table_name} 
                    WHERE numero_ssa = ?
                """
                existing = pd.read_sql_query(existing_query, conn, params=[numero_ssa])
                
                should_process = False
                
                if existing.empty:
                    # SSA não existe, insere
                    should_process = True
                    inserts_count += 1
                    logger.debug(f"SSA {numero_ssa}: Nova, será inserida")
                else:
                    # SSA existe, verifica se deve atualizar
                    existing_file_date = existing.iloc[0]['data_arquivo_origem']
                    existing_version = existing.iloc[0]['versao_dados']
                    
                    if should_update_ssa(existing_file_date, file_datetime_iso):
                        should_process = True
                        updates_count += 1
                        # Incrementa versão
                        df_valid.at[index, 'versao_dados'] = existing_version + 1
                        logger.debug(f"SSA {numero_ssa}: Arquivo mais recente, será atualizada (v{existing_version + 1})")
                    else:
                        skipped_count += 1
                        logger.debug(f"SSA {numero_ssa}: Arquivo mais antigo, pulando")
                
                if should_process:
                    # Converte a linha para DataFrame
                    single_row_df = pd.DataFrame([row])
                    
                    # Prepara para SQLite
                    prepared_df = prepare_dataframe_for_sqlite(single_row_df)
                    
                    # Insere/atualiza (REPLACE do SQLite)
                    prepared_df.to_sql(
                        table_name,
                        conn,
                        if_exists='append',
                        index=False,
                        method='multi',
                        dtype='TEXT'
                    )
            
            conn.commit()
            
            logger.info(
                f"Processamento concluído: {inserts_count} inserções, "
                f"{updates_count} atualizações, {skipped_count} ignoradas"
            )
            
            return True
            
    except Exception as e:
        logger.error(f"Erro no upsert inteligente: {e}")
        return False