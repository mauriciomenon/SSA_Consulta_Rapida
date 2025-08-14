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
import re
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)

# --- Gerenciamento de Conexão ---

# Nome do arquivo de schema (exposto para testes)
schema_file = 'schema.sql'

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
    Inicializa o banco de dados aplicando o schema SQL informado.

    Args:
        db_path: Caminho para o arquivo SQLite a ser criado/alterado.
        schema_file: Caminho para o arquivo .sql do schema. Pode ser absoluto ou relativo.
            - Se relativo e existir no diretório atual, será usado.
            - Caso não exista no CWD, será buscado em <raiz_projeto>/config/<schema_file>.

    Returns:
        True em caso de sucesso.

    Raises:
        FileNotFoundError: Se o arquivo de schema não for encontrado.
        Exception: Erros ao aplicar o schema serão propagados.
    """
    # Resolve o caminho do schema respeitando o parâmetro
    # 1) Se for absoluto, deve existir; caso contrário, erro imediato
    if os.path.isabs(schema_file):
        if not os.path.exists(schema_file):
            raise FileNotFoundError(f"Arquivo de schema absoluto não encontrado: '{schema_file}'")
        schema_path = schema_file
    else:
        # 2) Relativo: primeiro tenta no CWD
        if os.path.exists(schema_file):
            schema_path = schema_file
        else:
            # 3) Fallback para <project_root>/config/<basename>
            current_file_dir = os.path.dirname(os.path.abspath(__file__))
            project_root = os.path.dirname(current_file_dir)
            candidate = os.path.join(project_root, 'config', os.path.basename(schema_file))
            if os.path.exists(candidate):
                schema_path = candidate
            else:
                # Log auxiliar com conteúdo de config, se houver
                config_dir = os.path.join(project_root, 'config')
                if os.path.isdir(config_dir):
                    try:
                        logger.info(f"Conteúdo da pasta config: {os.listdir(config_dir)}")
                    except Exception:
                        pass
                raise FileNotFoundError(
                    f"Arquivo de schema não encontrado. Tentativas: '\n"
                    f"- relativo ao CWD: {os.path.abspath(schema_file)}\n"
                    f"- em config do projeto: {candidate}"
                )

    logger.info(f"Aplicando schema a partir de: '{schema_path}'")
    with open(schema_path, 'r', encoding='utf-8') as f:
        schema_sql = f.read()

    with get_db_connection(db_path) as conn:
        conn.executescript(schema_sql)
        conn.commit()

    logger.info("Banco de dados inicializado com sucesso.")
    return True

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
        # Normaliza coluna numero_ssa se existir
        if 'numero_ssa' in df.columns:
            df = df.copy()
            df['numero_ssa'] = df['numero_ssa'].apply(_normalize_numero_ssa_value)
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


def reset_database(db_path: str, mode: str = 'table', table_name: str = 'ssas', schema_path: str | None = None) -> bool:
    """Reseta o banco de dados.

    - mode = 'file': remove o arquivo de banco por completo (se existir).
    - mode = 'table': recria somente a tabela alvo usando o schema.
    """
    try:
        if mode == 'file':
            if os.path.exists(db_path):
                os.remove(db_path)
            return True
        elif mode == 'table':
            # Reaplica o schema
            if schema_path is None:
                schema_path = schema_file  # usa padrão e resolução em initialize_database
            initialize_database(db_path, schema_path)
            return True
        else:
            logger.error(f"Modo de reset desconhecido: {mode}")
            return False
    except Exception as e:
        logger.error(f"Falha ao resetar database ({mode}): {e}")
        return False


def ensure_indexes(db_path: str, table_name: str = 'ssas') -> bool:
    """Garante índices úteis para consultas comuns."""
    try:
        with get_db_connection(db_path) as conn:
            cur = conn.cursor()
            # Descobre colunas existentes para evitar erros ao criar índices
            cur.execute(f"PRAGMA table_info({table_name})")
            cols_info = cur.fetchall() or []
            existing_cols = {row[1] for row in cols_info}  # nome da coluna na posição 1

            # Índices candidatos e suas colunas
            candidate_indexes = [
                (f"idx_{table_name}_numero_ssa", "numero_ssa"),
                (f"idx_{table_name}_setor_executor", "setor_executor"),
                (f"idx_{table_name}_semana_cadastro", "semana_cadastro"),
                (f"idx_{table_name}_situacao", "situacao"),
            ]

            for idx_name, col in candidate_indexes:
                if col in existing_cols:
                    cur.execute(f"CREATE INDEX IF NOT EXISTS {idx_name} ON {table_name} ({col})")
            conn.commit()
        return True
    except Exception as e:
        logger.error(f"Erro criando índices: {e}")
        return False


def insert_dataframe_with_smart_upsert(df: pd.DataFrame, db_path: str, table_name: str = 'ssas') -> bool:
    """Insere DataFrame com upsert por numero_ssa, escolhendo a versão mais nova por data_cadastro.

    Regras:
    - Normaliza numero_ssa
    - Chave de upsert: numero_ssa (linhas com numero_ssa None são apenas append)
    - Compara por data_cadastro (parse dd/mm/yyyy ou yyyy-mm-dd); maiores datas vencem
    - Empate: prefere linha nova
    """
    if df is None or df.empty:
        return True

    work = df.copy()
    if 'numero_ssa' in work.columns:
        work['numero_ssa'] = work['numero_ssa'].apply(_normalize_numero_ssa_value)

    # Linhas sem chave -> inserção direta
    append_only = work[work.get('numero_ssa').isna()] if 'numero_ssa' in work.columns else work.iloc[0:0]
    upsert_rows = work[work.get('numero_ssa').notna()] if 'numero_ssa' in work.columns else work.iloc[0:0]

    try:
        with get_db_connection(db_path) as conn:
            if not upsert_rows.empty:
                keys = sorted(set(upsert_rows['numero_ssa'].tolist()))
                # Busca existentes
                placeholders = ','.join(['?'] * len(keys))
                existing = pd.read_sql_query(
                    f"SELECT * FROM {table_name} WHERE numero_ssa IN ({placeholders})",
                    conn,
                    params=tuple(keys)
                ) if keys else pd.DataFrame()

                # Merge por chave
                def parse_dt(s) -> Optional[datetime]:
                    try:
                        return pd.to_datetime(s, errors='coerce', dayfirst=True).to_pydatetime()
                    except Exception:
                        return None

                chosen_rows = []
                grouped_new = upsert_rows.groupby('numero_ssa', as_index=False)
                for k, new_group in grouped_new:
                    new_best = new_group.copy()
                    # Se houver várias novas para mesma chave, escolhe a mais recente
                    if 'data_cadastro' in new_best.columns:
                        new_best['_dt'] = new_best['data_cadastro'].apply(parse_dt)
                        new_best = new_best.sort_values('_dt').tail(1).drop(columns=['_dt'])
                    else:
                        new_best = new_best.tail(1)
                    new_row = new_best.iloc[0]

                    if existing is not None and not existing.empty:
                        old_group = existing[existing['numero_ssa'] == k]
                    else:
                        old_group = pd.DataFrame()

                    if old_group.empty:
                        chosen_rows.append(new_row)
                        continue

                    # Escolhe entre old e new por data
                    old_row = old_group.copy()
                    if 'data_cadastro' in old_row.columns:
                        old_row['_dt'] = old_row['data_cadastro'].apply(parse_dt)
                        old_row = old_row.sort_values('_dt').tail(1).drop(columns=['_dt'])
                    old_row = old_row.iloc[0]

                    new_dt = parse_dt(new_row.get('data_cadastro')) if 'data_cadastro' in new_row else None
                    old_dt = parse_dt(old_row.get('data_cadastro')) if 'data_cadastro' in old_row else None

                    if (new_dt and not old_dt) or (new_dt and old_dt and new_dt >= old_dt) or (not new_dt and not old_dt):
                        chosen_rows.append(new_row)
                    else:
                        chosen_rows.append(old_row)

                # Remove existentes para essas chaves e insere escolhidos
                if keys:
                    conn.execute(f"DELETE FROM {table_name} WHERE numero_ssa IN ({placeholders})", tuple(keys))
                if chosen_rows:
                    pd.DataFrame(chosen_rows).to_sql(table_name, conn, if_exists='append', index=False)

            # Insere linhas sem chave
            if append_only is not None and not append_only.empty:
                append_only.to_sql(table_name, conn, if_exists='append', index=False)

            conn.commit()
        return True
    except Exception as e:
        logger.error(f"Falha no smart upsert: {e}")
        return False


def _normalize_numero_ssa_value(v) -> int | None:
    """Normaliza um valor de numero_ssa para inteiro.

    Regras conservadoras:
    - Remove tudo que não seja dígito
    - Se vazio após limpeza: None
    - Se 7-8 dígitos: completa com zeros à esquerda até 9 e converte para int
    - Se 9+ dígitos: usa os últimos 9 dígitos (para capturar sufixos usuais) e converte para int
    - Caso 1-6 dígitos: mantém como int desses dígitos
    """
    try:
        if v is None or (isinstance(v, float) and pd.isna(v)):
            return None
        s = re.sub(r"\D", "", str(v))
        if not s:
            return None
        if len(s) < 8:
            return int(s)
        # Para 8+ dígitos, mantém apenas os últimos 8
        return int(s[-8:])
    except Exception:
        return None


def normalize_numero_ssa_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """Retorna uma cópia do DataFrame com coluna numero_ssa normalizada (se existir)."""
    if 'numero_ssa' not in df.columns:
        return df
    out = df.copy()
    values = out['numero_ssa'].tolist()
    normalized = [ _normalize_numero_ssa_value(v) for v in values ]
    out['numero_ssa'] = pd.Series(normalized, dtype='object')
    return out


def normalize_numero_ssa(value) -> str | None:
    """Normaliza numero_ssa para um formato de 9 dígitos em string.

    Regras (compatíveis com testes históricos):
    - None/"" -> None
    - Remove caracteres não numéricos
    - Se exatamente 9 dígitos: retorna como está
    - Se após remover zeros à esquerda restarem <= 5 dígitos: prefixa ano corrente "2025"
      e completa para 9 dígitos (2025 + 5 dígitos)
    - Caso < 9 dígitos: completa à esquerda com zeros até 9
    - Caso > 9 dígitos: usa os últimos 9 dígitos
    """
    if value is None:
        return None
    s = re.sub(r"\D", "", str(value))
    if not s:
        return None
    if len(s) == 9:
        return s
    stripped = s.lstrip('0')
    if len(stripped) <= 5:
        # 2025 + 5 dígitos
        return f"2025{stripped.zfill(5)}"
    if len(s) < 9:
        return s.zfill(9)
    # > 9 dígitos
    return s[-9:]
