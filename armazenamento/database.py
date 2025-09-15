# armazenamento/database.py 20250725 161500 (v2.1 - Boas Praticas Confirmadas)
"""
Módulo para interação com o banco de dados SQLite.

Responsável por criar tabelas, inserir DataFrames e consultar dados.
"""

import logging
import os
import re
import shutil
import sqlite3
from contextlib import contextmanager, suppress
import sqlite3 as _sqlite3_typehint  # alias para type checking leve
from datetime import datetime
from typing import Any, Literal

import pandas as pd  # type: ignore[import-not-found]

logger = logging.getLogger(__name__)

# Constantes (evitam "magic numbers" em validações)
NUMERO_SSA_LEN = 9
NUMERO_SSA_ANO_MIN = 1980
NUMERO_SSA_ANO_MAX = 2050
MIN_FREE_SPACE_GB_WARN = 0.1  # 100MB
MAX_TEXT_LEN = 1000
SHORT_TRIM_MAX = 5
SPECIAL_TRIM_LEN = 7

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

def initialize_database(db_path: str | _sqlite3_typehint.Connection, schema_file: str = 'schema.sql'):
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
    elif os.path.exists(schema_file):  # 2) relativo direto
        schema_path = schema_file
    else:  # 3) fallback config
        current_file_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(current_file_dir)
        candidate = os.path.join(project_root, 'config', os.path.basename(schema_file))
        if os.path.exists(candidate):
            schema_path = candidate
        else:
            config_dir = os.path.join(project_root, 'config')
            if os.path.isdir(config_dir):
                with suppress(Exception):
                    logger.info("Conteúdo da pasta config: %s", os.listdir(config_dir))
            raise FileNotFoundError(
                "Arquivo de schema não encontrado. Tentativas: '\n"
                f"- relativo ao CWD: {os.path.abspath(schema_file)}\n"
                f"- em config do projeto: {candidate}"
            )

    logger.info(f"Aplicando schema a partir de: '{schema_path}'")
    with open(schema_path, encoding='utf-8') as f:
        schema_sql = f.read()

    # Permitir que testes passem uma conexão já aberta (retrocompatibilidade)
    if isinstance(db_path, _sqlite3_typehint.Connection):
        conn = db_path
        conn.executescript(schema_sql)
        conn.commit()
        return True

    with get_db_connection(db_path) as conn:  # caminho normal (string)
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
        query = f"SELECT * FROM {table_name}"  # noqa: S608 table name trusted

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

IfExistsPolicy = Literal['fail', 'replace', 'append']

def insert_dataframe_to_db(*args, **kwargs) -> bool:  # noqa: C901, PLR0912
    """Insere um DataFrame em uma tabela do banco (modo simples).

    Suporta chamadas modernas e legadas usadas nos testes:

    Formatos aceitos:
      1. (df, db_path, table_name, if_exists='append')  -> novo
      2. (connection, df)                               -> legado (tabela padrão)
      3. (connection, df, table_name)                   -> legado

    Regras adicionais:
      * Se ``table_name`` for uma VIEW legada ("ssas" / "ssa_chamados") redireciona para tabela física ``ssa_table`` se existir
      * Filtra (descarta) linhas cujo numero_ssa normalizado resulte em None
      * DataFrame vazio:
          - modo legado: levanta ValueError (test_dataframe_validation_rejects_empty)
          - modo novo: retorna True apenas logando aviso
    """
    if len(args) == 0:
        raise TypeError("insert_dataframe_to_db requer ao menos um argumento")

    # Detecta formato pela primeira posição
    # Caso novo: primeiro argumento é DataFrame
    if isinstance(args[0], pd.DataFrame):
        if len(args) < 3:
            raise TypeError("Uso novo requer (df, db_path, table_name)")
        df: pd.DataFrame = args[0]
        db_path: str = args[1]
        table_name: str = args[2]
        if_exists: IfExistsPolicy = kwargs.get('if_exists', 'append')
        legacy_mode = False
    else:
        # Legado: (conn, df [, table])
        conn = args[0]
        if not isinstance(conn, _sqlite3_typehint.Connection):  # pragma: no cover
            raise TypeError("Primeiro argumento legado deve ser conexão sqlite3")
        if len(args) < 2:
            raise TypeError("Uso legado requer (conn, df [, table_name])")
        df = args[1]
        if not isinstance(df, pd.DataFrame):  # pragma: no cover
            raise TypeError("Segundo argumento legado deve ser DataFrame")
        table_name = args[2] if len(args) >= 3 else 'ssas'
        db_path = None  # type: ignore[assignment]
        if_exists = kwargs.get('if_exists', 'append')
        legacy_mode = True

    # Normalização / validação DataFrame
    if df.empty:
        if legacy_mode:
            raise ValueError("DataFrame vazio fornecido (modo legado)")
        logger.warning("DataFrame vazio fornecido para inserção (modo novo). Nada a fazer.")
        return True

    work_df = df.copy()
    # Optional whitelist via env var (comma-separated). If defined, drop unknown columns.
    wl = os.environ.get("SSA_ALLOWED_COLUMNS")
    if wl:
        allowed = {c.strip() for c in wl.split(',') if c.strip()}
        drop_cols = [c for c in work_df.columns if c not in allowed]
        if drop_cols:
            logger.info("Colunas removidas por whitelist (insert_dataframe_to_db): %s", drop_cols)
            work_df = work_df[[c for c in work_df.columns if c in allowed]]
    if 'numero_ssa' in work_df.columns:
        work_df['numero_ssa'] = work_df['numero_ssa'].apply(_normalize_numero_ssa_value)
        # Descarta linhas sem numero_ssa válido (regra implícita dos testes de importação)
        work_df = work_df[work_df['numero_ssa'].notna()].reset_index(drop=True)

    # Após normalização, se ficar vazio em modo legado, também gera ValueError
    if work_df.empty and legacy_mode:
        raise ValueError("DataFrame sem linhas válidas após normalização")

    # Redireciona view -> tabela física se necessário
    def _resolve_target_table(c: _sqlite3_typehint.Connection, name: str) -> str:
        try:
            cur = c.execute("SELECT name, type FROM sqlite_master WHERE name=?", (name,))
            row = cur.fetchone()
            if row and row[1] == 'view':
                # Preferir ssa_table se existir
                cur2 = c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='ssa_table'")
                if cur2.fetchone():
                    return 'ssa_table'
            return name
        except Exception:  # pragma: no cover
            return name

    try:
        if not legacy_mode:
            # Caminho novo: abrir conexão via caminho
            with get_db_connection(db_path) as conn:  # type: ignore[arg-type]
                final_table = _resolve_target_table(conn, table_name)
                batch_size = min(500, max(1, 999 // len(work_df.columns))) if len(work_df.columns) > 0 else 500
                work_df.reset_index(drop=True, inplace=True)
                work_df.to_sql(final_table, conn, if_exists=if_exists, index=False, chunksize=batch_size)  # type: ignore[arg-type]
                conn.commit()
            logger.info("%s linhas inseridas (novo modo) em '%s'", len(work_df), table_name)
            return True
        # Legado: já temos conexão aberta
        final_table = _resolve_target_table(conn, table_name)  # type: ignore[arg-type]
        batch_size = min(500, max(1, 999 // len(work_df.columns))) if len(work_df.columns) > 0 else 500
        work_df.reset_index(drop=True, inplace=True)
        work_df.to_sql(final_table, conn, if_exists=if_exists, index=False, chunksize=batch_size)  # type: ignore[arg-type]
        conn.commit()  # type: ignore[union-attr]
        logger.info("%s linhas inseridas (modo legado) em '%s'", len(work_df), final_table)
        return True
    except ValueError:
        raise
    except Exception as e:  # pragma: no cover
        logger.error(f"Falha ao inserir dados na tabela '{table_name}': {e}")
        return False


def reset_database(
    db_path: str,
    mode: str = 'table',
    _table_name: str = 'ssas',  # parâmetro legado não usado
    schema_path: str | None = None,
) -> bool:
    """Reseta o banco de dados.

    - mode = 'file': remove o arquivo de banco por completo (se existir).
    - mode = 'table': recria somente a tabela alvo usando o schema.
    """
    try:
        if mode == 'file':
            if os.path.exists(db_path):
                os.remove(db_path)
            return True
        if mode == 'table':
            # Reaplica o schema
            if schema_path is None:
                schema_path = schema_file  # usa padrão e resolução em initialize_database
            initialize_database(db_path, schema_path)
            return True
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


# ---- Helpers extraídos para reduzir complexidade da função pública ----

def _prepare_dataframe_for_upsert(frame: pd.DataFrame) -> pd.DataFrame:
    """Normaliza DataFrame para operação de upsert.

    - Copia valores (evita carregar índices problemáticos)
    - Normaliza numero_ssa
    - Converte colunas de data para string canônica ou None
    """
    work_local = pd.DataFrame(frame.values, columns=frame.columns).reset_index(drop=True)
    if 'numero_ssa' in work_local.columns:
        work_local['numero_ssa'] = work_local['numero_ssa'].apply(_normalize_numero_ssa_value)
    date_columns = ['data_cadastro', 'prazo_limite', 'data_limite', 'desde', 'desde_1']

    def _to_string_date(val) -> str | None:
        try:
            if pd.isna(val) or val in (None, ''):
                return None
            # Detecta formato ISO (YYYY-MM-DD) para evitar inversão com dayfirst
            val_str = str(val)
            iso_like = bool(re.match(r"^\d{4}-\d{2}-\d{2}", val_str))
            if iso_like:
                dt = pd.to_datetime(val_str, errors='coerce', dayfirst=False)
            else:
                dt = pd.to_datetime(val_str, errors='coerce', dayfirst=True)
            if pd.isna(dt):
                return None
            return dt.strftime('%Y-%m-%d %H:%M:%S')
        except Exception:  # pragma: no cover
            return None

    for c in date_columns:
        if c in work_local.columns:
            try:
                work_local[c] = [_to_string_date(v) for v in work_local[c]]
            except Exception as exc:  # pragma: no cover
                logger.warning(f"Erro ao converter coluna {c}: {exc}")
    return work_local


def _split_dataframe_by_numero_ssa(work_local: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    if 'numero_ssa' not in work_local.columns:
        return pd.DataFrame(), work_local.copy()
    return (
        work_local[work_local['numero_ssa'].notna()].copy(),
        work_local[work_local['numero_ssa'].isna()].copy(),
    )


def _should_update_existing(existing_row: pd.Series, new_row: pd.Series) -> bool:
    """Decide se deve atualizar o registro existente baseando-se em data.

    Regras:
      * Ambas sem data -> atualiza (empate, assume novo dado relevante)
      * Existente tem data e novo não -> NÃO atualiza
      * Existente sem data e novo tem -> atualiza
      * Ambos com data -> atualiza apenas se nova >= existente (não regride)
    """
    # existing_row é sempre uma Series aqui, logo verificação de None é redundante
    existing_date = existing_row.get('data_cadastro')
    new_date = new_row.get('data_cadastro')
    try:
        def _parse(dt):
            if dt in (None, '') or pd.isna(dt):
                return None
            return pd.to_datetime(dt, errors='coerce')
        e_dt = _parse(existing_date)
        n_dt = _parse(new_date)
        existing_missing = e_dt is None
        new_missing = n_dt is None
        if existing_missing and new_missing:
            return True
        if new_missing and not existing_missing:
            return False
        if not new_missing and existing_missing:
            return True
        # ambos válidos
        if e_dt is not None and n_dt is not None:
            return n_dt >= e_dt
        # fallback defensivo (já coberto pelos casos anteriores)
        return True
    except Exception:  # pragma: no cover
        return True


def _perform_upsert(has_ssa: pd.DataFrame, table_name: str, conn, *, chunk_size: int = 100) -> int:  # type: ignore[no-untyped-def]
    """Executa upsert linha-a-linha.

    Modo padrão (compat): segue a lógica original (_should_update_existing + merge
    simples em que valores novos não vazios sobrescrevem antigos).

    Modo complementar (ativado com env SSA_ENABLE_COMPLEMENTARY=1):
      * Sempre tenta "fundir" a linha nova com a existente mesmo que a data
        seja mais antiga, desde que adicione informação não presente.
      * Regras de fusão:
          - numero_ssa: preservado (não altera)
          - situacao: aplica progressão de status se ordem for superior; nunca regride
          - Colunas de data: mantém a mais recente (comparação datetime parse)
          - Campos de descrição/texto (configuráveis): escolhe o texto mais longo
            se o novo acrescentar conteúdo relevante (>10 chars a mais) ou se antigo vazio
          - Demais campos: só preenche se antigo vazio e novo não-vazio
      * Terminal statuses (ex.: STE, SCA) não são rebaixados; porém podem receber
        preenchimento de campos vazios.
    """
    complementary_mode = os.environ.get("SSA_ENABLE_COMPLEMENTARY") == "1"
    # Configurações (podem ser sobrescritas via env vars)
    status_order_env = os.environ.get("SSA_STATUS_ORDER")  # ex: "ABERTO,EM_ANALISE,EM_EXECUCAO,SCA,STE"
    if status_order_env:
        status_order_list = [s.strip() for s in status_order_env.split(',') if s.strip()]
    else:
        status_order_list = ["ABERTO", "EM_ANALISE", "EM_EXECUCAO", "SCA", "STE"]
    status_rank = {s: i for i, s in enumerate(status_order_list)}
    terminal_statuses_env = os.environ.get("SSA_TERMINAL_STATUSES")
    if terminal_statuses_env:
        terminal_statuses = {s.strip() for s in terminal_statuses_env.split(',') if s.strip()}
    else:
        terminal_statuses = {"STE", "SCA"}
    desc_cols_env = os.environ.get("SSA_DESC_COLUMNS")  # ex: "descricao_ssa,detalhes,comentarios"
    if desc_cols_env:
        description_columns = [c.strip() for c in desc_cols_env.split(',') if c.strip()]
    else:
        description_columns = ["descricao_ssa", "descricao", "detalhes", "comentarios"]

    date_columns = ["data_cadastro", "prazo_limite", "data_limite", "desde", "desde_1"]

    def _is_empty(val) -> bool:
        if val is None:
            return True
        if isinstance(val, float) and pd.isna(val):
            return True
        if isinstance(val, str):
            if val.strip() == "" or val.strip().lower() in {"n/a", "na", "null", "-"}:
                return True
        return False

    def _parse_dt(v):
        try:
            if _is_empty(v):
                return None
            return pd.to_datetime(v, errors='coerce')
        except Exception:
            return None

    def _merge_complement(existing_row: pd.Series, new_row: pd.Series) -> pd.Series:
        # Copiamos para dict mutável
        result = existing_row.copy()
        for col in new_row.index:
            new_val = new_row[col]
            if col == 'numero_ssa':
                continue  # imutável
            # Status progression
            if col == 'situacao':
                old_val = result.get(col)
                if _is_empty(old_val) and not _is_empty(new_val):
                    result[col] = new_val
                else:
                    # Progressão apenas se rank superior
                    old_rank = status_rank.get(str(old_val), -1)
                    new_rank = status_rank.get(str(new_val), -1)
                    if new_rank > old_rank:
                        result[col] = new_val
                continue
            # Datas: escolher a mais recente (se comparáveis)
            if col in date_columns:
                old_dt = _parse_dt(result.get(col))
                new_dt = _parse_dt(new_val)
                if old_dt is None and new_dt is not None:
                    result[col] = new_val
                elif old_dt is not None and new_dt is not None and new_dt > old_dt:
                    result[col] = new_val
                continue
            # Descrições: escolher maior se acrescenta conteúdo
            if col in description_columns:
                old_val = result.get(col)
                if _is_empty(old_val) and not _is_empty(new_val):
                    result[col] = new_val
                else:
                    if isinstance(new_val, str) and isinstance(old_val, str):
                        if len(new_val) > len(old_val) + 10:  # heurística: ganho significativo
                            result[col] = new_val
                continue
            # Genérico: preencher vazio
            old_val = result.get(col)
            if _is_empty(old_val) and not _is_empty(new_val):
                result[col] = new_val
        return result

    total_inserted = 0
    for start in range(0, len(has_ssa), chunk_size):
        chunk = has_ssa.iloc[start:start + chunk_size]
        for _, row in chunk.iterrows():
            numero_ssa = row['numero_ssa']
            existing = pd.read_sql_query(
                f"SELECT * FROM {table_name} WHERE numero_ssa = ?",  # noqa: S608
                conn,
                params=[numero_ssa],
            )
            # Cria DataFrame alvo (merge preservando valores antigos não-nulos se novos vierem vazios)
            if not complementary_mode:
                if existing.empty:
                    target_df = row.to_frame().T
                else:
                    old = existing.iloc[0]
                    merged = {}
                    for col in existing.columns:
                        new_val = row[col] if col in row.index else None
                        is_empty_new = (
                            pd.isna(new_val) or new_val in (None, '') or (isinstance(new_val, str) and new_val.strip() == '')
                        )
                        if is_empty_new:
                            merged[col] = old[col]
                        else:
                            merged[col] = new_val
                    for col in row.index:
                        if col not in merged:
                            merged[col] = row[col]
                    target_df = pd.DataFrame([merged])
                if existing.empty or _should_update_existing(existing.iloc[0], row):
                    if not existing.empty:
                        conn.execute(
                            f"DELETE FROM {table_name} WHERE numero_ssa = ?",  # noqa: S608
                            [numero_ssa],
                        )
                    target_df.to_sql(
                        table_name,
                        conn,
                        if_exists='append',
                        index=False,
                    )
                    total_inserted += 1
            else:
                # Complementary mode
                if existing.empty:
                    target_df = row.to_frame().T
                    perform_update = True
                else:
                    old_row = existing.iloc[0]
                    merged_series = _merge_complement(old_row, row)
                    # Detecta se algo mudou
                    perform_update = not merged_series.equals(old_row)
                    target_df = merged_series.to_frame().T
                if perform_update:
                    if not existing.empty:
                        conn.execute(
                            f"DELETE FROM {table_name} WHERE numero_ssa = ?",  # noqa: S608
                            [numero_ssa],
                        )
                    target_df.to_sql(
                        table_name,
                        conn,
                        if_exists='append',
                        index=False,
                    )
                    total_inserted += 1
    return total_inserted


def _insert_dataframe_with_smart_upsert_impl(
    df: pd.DataFrame, db_path: str | _sqlite3_typehint.Connection, table_name: str
) -> bool:
    work = _prepare_dataframe_for_upsert(df)
    wl = os.environ.get("SSA_ALLOWED_COLUMNS")
    if wl:
        allowed = {c.strip() for c in wl.split(',') if c.strip()}
        drop_cols = [c for c in work.columns if c not in allowed]
        if drop_cols:
            logger.info("Colunas removidas por whitelist (smart_upsert): %s", drop_cols)
            work = work[[c for c in work.columns if c in allowed]]
    has_ssa, no_ssa = _split_dataframe_by_numero_ssa(work)
    conn_cm = None  # ensure defined for finally block
    if isinstance(db_path, _sqlite3_typehint.Connection):
        conn = db_path  # external connection provided
        close_after = False
    else:
        conn_cm = get_db_connection(db_path)
        conn = conn_cm.__enter__()
        close_after = True
    try:
        cursor = conn.cursor()
        # Detecta alias legado se a tabela informada não existir
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        existing_tables = {r[0] for r in cursor.fetchall()}
        if table_name not in existing_tables:
            # tentativas de alias
            for alias in ("ssa_table", "ssas", "ssa_chamados"):
                if alias in existing_tables:
                    table_name = alias  # type: ignore[assignment]
                    break
        table_exists = table_name in existing_tables
        if not no_ssa.empty:
            mode = 'append' if table_exists else 'replace'
            no_ssa.to_sql(
                table_name,
                conn,
                if_exists=mode,
                index=False,
                chunksize=500,
            )
            logger.info("Inseridos %s registros sem numero_ssa", len(no_ssa))
            table_exists = True
        if not has_ssa.empty:
            if not table_exists:
                has_ssa.iloc[0:1].to_sql(
                    table_name, conn, if_exists='replace', index=False
                )
                table_exists = True
                logger.info("Tabela criada com primeiro registro (numero_ssa)")
            inserted = _perform_upsert(has_ssa, table_name, conn)
            logger.info(
                "Processados %s registros com numero_ssa via upsert", inserted
            )
        conn.commit()
        logger.info("Inserção completada com sucesso")
        return True
    finally:
        if close_after and conn_cm is not None:
            try:
                conn_cm.__exit__(None, None, None)
            except Exception:  # pragma: no cover
                pass


def insert_dataframe_with_smart_upsert(
    df: pd.DataFrame | _sqlite3_typehint.Connection,
    db_path: str | pd.DataFrame | None = None,
    table_name: str = 'ssas',
) -> bool:  # noqa: PLR0912, PLR0915, PLR0915, PLR0913, PLR0914
    """Insere DataFrame com lógica de upsert (por ``numero_ssa``) em baixo
    nível. Esta versão foi refatorada para reduzir complexidade mantendo a
    mesma semântica relevante:

    - Linhas sem ``numero_ssa``: inserção direta (append/replace se primeira)
    - Linhas com ``numero_ssa``: upsert simples (delete + insert) se data nova
      for mais recente ou se empatar/ausente.
    - Normalização de ``numero_ssa`` e conversão resiliente de colunas de data.
    """
    # Suporte retrocompatível:
    #  - Novo contrato: (df, db_path, table_name)
    #  - Contrato legado usado em testes: (conn, df) ou (conn, df, table_name)
    if isinstance(df, _sqlite3_typehint.Connection):  # padrão antigo: primeiro arg é conexão
        conn = df
        real_df = db_path  # neste formato, segundo argumento é o DataFrame
        if not isinstance(real_df, pd.DataFrame):  # tipo incorreto
            logger.error("Uso legado invalido: segundo argumento deve ser DataFrame quando primeiro e conexao")
            return False
        # real_df já garantido DataFrame acima; apenas verificar vazio
        if real_df.empty:
            return True
        try:
            return _insert_dataframe_with_smart_upsert_impl(real_df, conn, table_name)
        except Exception as e:  # pragma: no cover
            logger.error(f"Falha na inserção (legacy conn mode): {e}")
            return False

    # caminho novo normal
    real_df = df  # type: ignore[assignment]
    if isinstance(real_df, pd.DataFrame) and real_df.empty:
        return True
    try:
        assert isinstance(real_df, pd.DataFrame)
        assert isinstance(db_path, str)
        return _insert_dataframe_with_smart_upsert_impl(real_df, db_path, table_name)
    except Exception as e:  # pragma: no cover
        logger.error(f"Falha na inserção: {e}")
        return False


def _normalize_numero_ssa_value(v) -> int | None:
    """Normaliza numero_ssa para inteiro (YYYY + 5).

    Compatibilidade com testes legados que esperam inteiro:
      * Remove não dígitos
      * Usa primeiros 9 dígitos se exceder
      * Exige exatamente 9 dígitos
      * Ano 1980-2050
      * Retorna int (ex.: 202512345)
    """
    try:
        if v is None or (isinstance(v, float) and pd.isna(v)):
            return None
        s = re.sub(r"\D", "", str(v))
        if not s:
            return None
        if len(s) > NUMERO_SSA_LEN:
            s = s[:NUMERO_SSA_LEN]
        if len(s) != NUMERO_SSA_LEN:
            return None
        ano = int(s[:4])
        if not (NUMERO_SSA_ANO_MIN <= ano <= NUMERO_SSA_ANO_MAX):
            return None
        return int(s)
    except Exception as e:  # pragma: no cover
        logger.warning(f"Erro ao normalizar numero_ssa '{v}': {e}")
        return None


def normalize_numero_ssa_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    if 'numero_ssa' not in df.columns:
        return df
    out = df.copy()
    norm_vals = [ _normalize_numero_ssa_value(v) for v in out['numero_ssa'] ]
    # Usar dtype object para preservar None em vez de converter para float/NaN
    out['numero_ssa'] = pd.Series(norm_vals, dtype='object')
    return out


def normalize_numero_ssa(value) -> str | None:  # noqa: PLR0911
    """Formata para exibição: sempre 9 dígitos (YYYY + 5).

    - None/"" → None
    - Remove não‑dígitos; remove zeros à esquerda para decidir os casos curtos
    - Se, após remover zeros à esquerda, tiver 1..5 dígitos → "2025" + zfill(5)
    - Se 7 dígitos e começar com 21–25 → prefixa "20"
    - Se ainda < 9 → zfill(9)
    - Se > 9 → usa os primeiros 9
    - Se 9 → retorna como está
    """
    if value is None:
        return None
    raw = re.sub(r"\D", "", str(value))
    if not raw:
        return None
    trimmed = raw.lstrip('0')
    if not trimmed:
        return None
    n_trim = len(trimmed)
    if n_trim <= SHORT_TRIM_MAX:
        return "2025" + trimmed.zfill(SHORT_TRIM_MAX)
    if n_trim == SPECIAL_TRIM_LEN and trimmed.startswith(("21", "22", "23", "24", "25")):
        return "20" + trimmed
    # Volta ao valor bruto (com zeros) para completar até 9 quando aplicável
    if len(raw) < NUMERO_SSA_LEN:
        return raw.zfill(NUMERO_SSA_LEN)
    if len(raw) > NUMERO_SSA_LEN:
        return raw[:NUMERO_SSA_LEN]
    return raw


# --- Funções de Verificação e Integridade do Banco ---

def verify_database_integrity(db_path: str, table_name: str = 'ssas') -> dict[str, Any]:  # noqa: PLR0912, PLR0915
    """
    Verifica a integridade do banco de dados e retorna relatório detalhado.
    
    Args:
        db_path: Caminho para o arquivo do banco de dados
        table_name: Nome da tabela principal a verificar
        
    Returns:
        Dict com status da verificação e detalhes dos problemas encontrados
    """
    verification_report = {
        'is_valid': True,
        'issues': [],
        'warnings': [],
        'database_exists': False,
        'database_accessible': False,
        'table_exists': False,
        'schema_valid': False,
        'data_consistent': False,
        'disk_space_sufficient': False,
        'file_permissions_ok': False,
        'needs_creation': False
    }
    
    try:
        # 1. Verificar se o arquivo do banco existe
        if not os.path.exists(db_path):
            verification_report['issues'].append(
                f"Arquivo do banco de dados não encontrado: {db_path}"
            )
            # Banco inexistente é considerado válido pois será criado na sequência
            verification_report['is_valid'] = True
            verification_report['needs_creation'] = True
            return verification_report
        
        verification_report['database_exists'] = True
        
        # 1.b Arquivo existe porém vazio (0 bytes) -> considerado inválido / não acessível
        try:
            file_size = os.path.getsize(db_path)
            if file_size == 0:
                verification_report['issues'].append(
                    "Arquivo de banco encontrado mas vazio (0 bytes) - inválido"
                )
                verification_report['is_valid'] = False
                verification_report['database_accessible'] = False
                verification_report['data_consistent'] = False
                # Não prossegue com demais verificações pois PRAGMA falhará / é irrelevante
                return verification_report
        except Exception as e:  # pragma: no cover
            verification_report['warnings'].append(f"Falha ao obter tamanho do arquivo: {e}")
        
        # 2. Verificar permissões de arquivo
        try:
            if not os.access(db_path, os.R_OK | os.W_OK):
                verification_report['issues'].append(
                    f"Permissões insuficientes para o banco: {db_path}"
                )
                verification_report['is_valid'] = False
            else:
                verification_report['file_permissions_ok'] = True
        except Exception as e:
            verification_report['issues'].append(f"Erro ao verificar permissões: {e}")
            verification_report['is_valid'] = False
        
        # 3. Verificar espaço em disco
        try:
            db_dir = os.path.dirname(db_path) or '.'
            statvfs = os.statvfs(db_dir) if hasattr(os, 'statvfs') else None
            if statvfs:
                free_space_gb = (statvfs.f_frsize * statvfs.f_bavail) / (1024**3)
                if free_space_gb < MIN_FREE_SPACE_GB_WARN:  # Menos de 100MB disponível
                    verification_report['warnings'].append(
                        f"Pouco espaço em disco: {free_space_gb:.2f}GB disponível"
                    )
                else:
                    verification_report['disk_space_sufficient'] = True
            else:
                # Ambiente sem statvfs - usar shutil
                free_space_gb = shutil.disk_usage(db_dir).free / (1024**3)
                if free_space_gb < MIN_FREE_SPACE_GB_WARN:
                    verification_report['warnings'].append(
                        f"Pouco espaço em disco: {free_space_gb:.2f}GB disponível"
                    )
                else:
                    verification_report['disk_space_sufficient'] = True
        except Exception as e:
            verification_report['warnings'].append(
                f"Não foi possível verificar espaço em disco: {e}"
            )
        
        # 4. Verificar acessibilidade e integridade básica (PRAGMA integrity_check)
        try:
            with get_db_connection(db_path) as conn:
                try:
                    cursor = conn.execute("PRAGMA integrity_check")
                    integrity_result = cursor.fetchone()
                except Exception as e:
                    raise RuntimeError(f"Falha ao executar integrity_check: {e}") from e
                if not integrity_result:
                    verification_report['issues'].append("integrity_check não retornou resultado")
                    verification_report['is_valid'] = False
                    # Não marcar como acessível
                    return verification_report
                if integrity_result[0] != 'ok':
                    verification_report['issues'].append(
                        f"Falha na verificação de integridade SQLite: {integrity_result[0]}"
                    )
                    verification_report['is_valid'] = False
                    # Não marcar acessível em caso de falha
                    return verification_report
                # Se chegou aqui, integridade básica OK
                verification_report['database_accessible'] = True
                verification_report['data_consistent'] = True
        except Exception as e:
            verification_report['issues'].append(f"Banco de dados não acessível: {e}")
            verification_report['is_valid'] = False
            return verification_report
        
        # 5. Verificar se a tabela principal existe
        try:
            with get_db_connection(db_path) as conn:
                cursor = conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name=?", 
                    (table_name,)
                )
                if cursor.fetchone():
                    verification_report['table_exists'] = True
                else:
                    verification_report['issues'].append(f"Tabela '{table_name}' não encontrada")
                    verification_report['is_valid'] = False
        except Exception as e:
            verification_report['issues'].append(f"Erro ao verificar tabela: {e}")
            verification_report['is_valid'] = False
        
        # 6. Verificar schema da tabela (colunas obrigatórias)
        if verification_report['table_exists']:
            try:
                required_columns = ['numero_ssa', 'situacao', 'data_cadastro', 'descricao_ssa']
                with get_db_connection(db_path) as conn:
                    cursor = conn.execute(f"PRAGMA table_info({table_name})")  # noqa: S608 table name trusted
                    existing_columns = [row[1] for row in cursor.fetchall()]
                    
                    missing_columns = [
                        col for col in required_columns if col not in existing_columns
                    ]
                    if missing_columns:
                        verification_report['issues'].append(
                            f"Colunas obrigatórias ausentes: {missing_columns}"
                        )
                        verification_report['is_valid'] = False
                    else:
                        verification_report['schema_valid'] = True
            except Exception as e:
                verification_report['issues'].append(f"Erro ao verificar schema: {e}")
                verification_report['is_valid'] = False
        
        # (Integridade detalhada já verificada no passo 4 com PRAGMA integrity_check)
        
        status_text = (
            "✓ Válido" if verification_report['is_valid'] else "✗ Problemas encontrados"
        )
        logger.info(
            "Verificação de integridade concluída. Status: %s", status_text
        )
        
    except Exception as e:
        verification_report['issues'].append(f"Erro inesperado na verificação: {e}")
        verification_report['is_valid'] = False
        logger.error(f"Erro na verificação de integridade: {e}")
    
    return verification_report


def validate_dataframe_before_insert(df: pd.DataFrame, table_name: str = 'ssas') -> dict[str, Any]:  # noqa: PLR0912, PLR0915
    """
    Valida um DataFrame antes da inserção no banco de dados.
    
    Args:
        df: DataFrame a ser validado
        table_name: Nome da tabela de destino
        
    Returns:
        Dict com resultado da validação e problemas encontrados
    """
    validation_report = {
        'is_valid': True,
        'issues': [],
        'warnings': [],
        'row_count': len(df),
        'invalid_rows': [],
        'fixed_rows': 0,
        'table_name': table_name,
    }
    
    try:
        if df.empty:
            validation_report['warnings'].append("DataFrame vazio - nada para validar")
            return validation_report
        
        # 1. Verificar colunas críticas
        critical_columns = ['numero_ssa', 'situacao']
        for col in critical_columns:
            if col in df.columns:
                null_count = df[col].isnull().sum()
                if null_count > 0:
                    validation_report['warnings'].append(
                        f"Coluna '{col}' tem {null_count} valores nulos"
                    )
        
        # 2. Validar números SSA
        if 'numero_ssa' in df.columns:
            invalid_ssa_mask = df['numero_ssa'].apply(
                lambda x: _normalize_numero_ssa_value(x) is None if pd.notna(x) else True
            )
            invalid_ssa_count = invalid_ssa_mask.sum()
            
            if invalid_ssa_count > 0:
                validation_report['warnings'].append(
                    f"{invalid_ssa_count} números SSA inválidos encontrados"
                )
                # Marcar linhas com SSA inválido
                invalid_indices = df[invalid_ssa_mask].index.tolist()
                validation_report['invalid_rows'].extend(invalid_indices)
        
        # 3. Validar datas
        date_columns = ['data_cadastro', 'prazo_limite', 'data_limite']
        for col in date_columns:
            if col in df.columns:
                invalid_dates = 0
                for idx, value in df[col].items():
                    if pd.notna(value) and value != '':
                        try:
                            pd.to_datetime(value, errors='raise', dayfirst=True)
                        except Exception:
                            invalid_dates += 1
                            if idx not in validation_report['invalid_rows']:
                                validation_report['invalid_rows'].append(idx)
                
                if invalid_dates > 0:
                    validation_report['warnings'].append(
                        f"Coluna '{col}' tem {invalid_dates} datas inválidas"
                    )
        
        # 4. Verificar duplicatas por numero_ssa
        if 'numero_ssa' in df.columns:
            valid_ssa_df = df[df['numero_ssa'].notna()]
            if not valid_ssa_df.empty:
                # Pandas stub antigo pode omitir 'subset'; ignorar para type checking
                duplicated_ssa = valid_ssa_df.duplicated(subset=['numero_ssa'], keep=False)  # type: ignore[call-arg]
                duplicate_count = duplicated_ssa.sum()
                
                if duplicate_count > 0:
                    validation_report['warnings'].append(
                        f"{duplicate_count} números SSA duplicados encontrados"
                    )
        
        # 5. Verificar tamanhos de string (evitar truncamento)
        text_columns = ['descricao_ssa', 'descricao_execucao', 'solicitante']
        for col in text_columns:
            if col in df.columns:
                long_values = df[col].astype(str).str.len() > MAX_TEXT_LEN  # Limite
                long_count = long_values.sum()
                
                if long_count > 0:
                    validation_report['warnings'].append(
                        f"Coluna '{col}' tem {long_count} valores muito longos (>" \
                        f"{MAX_TEXT_LEN} chars)"
                    )
        
        # Considerar válido mesmo com warnings (apenas issues críticos invalidam)
        if not validation_report['issues']:
            validation_report['is_valid'] = True
            
        logger.info(
            "Validação concluída: %s linhas, %s problemas críticos, %s avisos",
            validation_report['row_count'],
            len(validation_report['issues']),
            len(validation_report['warnings']),
        )
        
    except Exception as e:
        validation_report['issues'].append(f"Erro na validação: {e}")
        validation_report['is_valid'] = False
        logger.error(f"Erro na validação do DataFrame: {e}")
    
    return validation_report


def repair_database_if_needed(
    db_path: str,
    schema_file: str = 'schema.sql',
    table_name: str = 'ssas',
) -> bool:  # noqa: PLR0912
    """
    Tenta reparar o banco de dados se problemas forem detectados.
    
    Args:
        db_path: Caminho para o banco de dados
        schema_file: Arquivo de schema para recriação se necessário
        table_name: Nome da tabela para verificação
        
    Returns:
        True se reparo foi bem-sucedido ou não necessário
    """
    logger.info("Iniciando verificação e reparo do banco de dados...")
    
    try:
        # Verificar integridade
        integrity_report = verify_database_integrity(db_path, table_name)
        
        if integrity_report['is_valid']:
            logger.info("Banco de dados íntegro - nenhum reparo necessário")
            return True
        
        logger.warning(f"Problemas detectados no banco: {integrity_report['issues']}")
        
        # Tentar reparos básicos
        repaired = False
        
        # 1. Se banco não existe, criar novo
        if not integrity_report['database_exists']:
            logger.info("Criando novo banco de dados...")
            initialize_database(db_path, schema_file)
            repaired = True
        
        # 2. Se tabela não existe, recriar schema
        elif not integrity_report['table_exists']:
            logger.info("Recriando schema do banco...")
            initialize_database(db_path, schema_file)
            repaired = True
        
        # 3. Se há problemas de integridade SQLite, tentar backup/restore
        elif not integrity_report['data_consistent']:
            logger.warning("Detectada corrupção no banco - tentando backup/restore...")
            backup_path = f"{db_path}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            try:
                # Fazer backup do que for possível
                shutil.copy2(db_path, backup_path)
                logger.info(f"Backup criado em: {backup_path}")
                
                # Tentar extrair dados válidos
                with get_db_connection(db_path) as conn:
                    try:
                        df_backup = pd.read_sql_query("SELECT * FROM ssas", conn)
                        if not df_backup.empty:
                            # Recriar banco limpo
                            os.remove(db_path)
                            initialize_database(db_path, schema_file)
                            
                            # Reinserir dados
                            success = insert_dataframe_with_smart_upsert(df_backup, db_path)
                            if success:
                                logger.info(
                                    "Dados restaurados com sucesso após correção de corrupção"
                                )
                                repaired = True
                    except Exception as e:
                        logger.error(f"Não foi possível extrair dados do banco corrompido: {e}")
            except Exception as e:
                logger.error(f"Falha no processo de backup/restore: {e}")
        
        # Verificar se reparo foi bem-sucedido
        if repaired:
            final_check = verify_database_integrity(db_path)
            if final_check['is_valid']:
                logger.info("✓ Reparo do banco de dados concluído com sucesso")
                return True
            logger.error("✗ Reparo falhou - problemas persistem")
            return False
        logger.error("Nenhum reparo foi possível para os problemas detectados")
        return False
            
    except Exception as e:
        logger.error(f"Erro durante tentativa de reparo: {e}")
        return False
