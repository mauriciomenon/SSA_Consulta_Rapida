# armazenamento/database.py 20250725 161500 (v2.1 - Boas Praticas Confirmadas)
# Last modified: 2025-10-29T11:15:00 (circular import documentation)
"""
Modulo para interacao com o banco de dados SQLite.

Responsavel por criar tabelas, inserir DataFrames e consultar dados.
"""

import logging
import os
import sqlite3
import time
from contextlib import contextmanager
import sqlite3 as _sqlite3_typehint  # alias para type checking leve
from typing import Any, Literal, cast

import pandas as pd  # type: ignore[import-not-found]

# Importacoes refatoradas serao carregadas de forma lazy dentro dos wrappers para evitar ciclos.

logger = logging.getLogger(__name__)
from .identifier_utils import is_valid_identifier  # noqa: E402

# Constantes (evitam "magic numbers" em validacoes)
MIN_FREE_SPACE_GB_WARN = 0.1  # 100MB
MAX_TEXT_LEN = 1000

# Normalizacao agora centralizada em armazenamento.numero_ssa_utils. Mantemos apenas
# constantes realmente usadas localmente. As regras detalhadas vivem em
# core.numero_ssa.normalize_strict e no util compartilhado.

# --- Optimized Mode Dispatch ---
# Flag global para controlar modo otimizado (substituiu monkey-patching)
_use_optimized_mode = False

def set_optimized_mode(enabled: bool) -> None:
    """
    Ativa ou desativa o modo otimizado de importacao.

    Quando ativado, insert_dataframe_with_smart_upsert usa a implementacao
    otimizada de database_optimized.py. Quando desativado, usa a implementacao
    padrao de database_upsert_logic.py.

    Args:
        enabled: True para ativar modo otimizado, False para modo padrao
    """
    global _use_optimized_mode
    _use_optimized_mode = enabled
    logger.info(f"Modo otimizado {'ativado' if enabled else 'desativado'}")

# --- Gerenciamento de Conexao ---

# Nome do arquivo de schema (exposto para testes)
schema_file = 'schema.sql'

@contextmanager
def get_db_connection(db_path: str):
    """
    Gerenciador de contexto para obter uma conexao com o banco de dados.

    Args:
        db_path (str): Caminho para o arquivo do banco de dados SQLite.

    Yields:
        sqlite3.Connection: Uma conexao ativa com o banco de dados.
    """
    conn = None
    try:
        # Verifica se o diretorio do DB existe
        db_dir = os.path.dirname(db_path)
        if db_dir:
            os.makedirs(db_dir, exist_ok=True)

        conn = sqlite3.connect(db_path)
        # Configuracoes recomendadas para performance e seguranca (FKs, etc.)
        conn.execute("PRAGMA foreign_keys = ON")
        yield conn
    except sqlite3.Error as e:
        logger.error(f"Erro de banco de dados: {e}")
        if conn:
            conn.rollback()
        raise
    finally:
        if conn:
            conn.close()

# --- Funcoes de Banco de Dados ---

# armazenamento/database.py

def initialize_database(db_path: str | _sqlite3_typehint.Connection, schema_file: str = 'schema.sql'):
    """
    Inicializa o banco de dados aplicando o schema SQL informado.

    Args:
        db_path: Caminho para o arquivo SQLite a ser criado/alterado.
        schema_file: Caminho para o arquivo .sql do schema. Pode ser absoluto ou relativo.
            - Se relativo e existir no diretorio atual, sera usado.
            - Caso nao exista no CWD, sera buscado em <raiz_projeto>/config/<schema_file>.

    Returns:
        True em caso de sucesso.

    Raises:
        FileNotFoundError: Se o arquivo de schema nao for encontrado.
        Exception: Erros ao aplicar o schema serao propagados.
    """
    # Resolve o caminho do schema respeitando o parametro
    # 1) Se for absoluto, deve existir; caso contrario, erro imediato
    if os.path.isabs(schema_file):
        if not os.path.exists(schema_file):
            raise FileNotFoundError(f"Arquivo de schema absoluto nao encontrado: '{schema_file}'")
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
                try:
                    logger.info("Conteudo da pasta config: %s", os.listdir(config_dir))
                except OSError as exc:
                    logger.warning("Falha ao listar pasta config '%s': %s", config_dir, exc)
            raise FileNotFoundError(
                "Arquivo de schema nao encontrado. Tentativas: '\n"
                f"- relativo ao CWD: {os.path.abspath(schema_file)}\n"
                f"- em config do projeto: {candidate}"
            )

    logger.info(f"Aplicando schema a partir de: '{schema_path}'")
    with open(schema_path, encoding='utf-8') as f:
        schema_sql = f.read()

    # Permitir que testes passem uma conexao ja aberta (retrocompatibilidade)
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

def query_db(
    db_path: str,
    table_name: str,
    query: str = "",
    params: tuple = (),
    raise_on_error: bool = False,
) -> pd.DataFrame:
    """
    Consulta o banco de dados e retorna um DataFrame.

    Args:
        db_path (str): Caminho para o banco de dados.
        table_name (str): Nome da tabela (usado se `query` estiver vazio).
        query (str, optional): Query SQL customizada. Se vazia, seleciona tudo da tabela.
        params (tuple, optional): Parametros para a query.
        raise_on_error (bool, optional): Se True, propaga excecao em caso de erro.

    Returns:
        pd.DataFrame: Resultado da consulta.
    """
    if not query:
        safe_table_name = str(table_name or "").strip()
        if not is_valid_identifier(safe_table_name):
            error_msg = f"Nome de tabela invalido para query_db: {table_name!r}"
            logger.error(error_msg)
            if raise_on_error:
                raise ValueError(error_msg)
            return pd.DataFrame()
        query = f'SELECT * FROM "{safe_table_name}"'

    logger.debug(f"Executando consulta: {query} com params: {params}")
    try:
        with get_db_connection(db_path) as conn:
            # pd.read_sql_query e otimo para SELECTs
            df = pd.read_sql_query(query, conn, params=cast(Any, params))
        logger.debug(f"Consulta retornou {len(df)} linhas.")
        return df
    except (sqlite3.Error, pd.errors.DatabaseError) as e:
        logger.exception("Erro ao executar consulta '%s' com params=%s: %s", query, params, e)
        if raise_on_error:
            raise
        logger.warning(
            "query_db retornando DataFrame vazio apos falha (raise_on_error=False). "
            "Ative raise_on_error para falhar explicitamente."
        )
        return pd.DataFrame()

IfExistsPolicy = Literal['fail', 'replace', 'append']

def insert_dataframe_to_db(*args, **kwargs) -> bool:  # noqa: C901, PLR0912
    """Insere um DataFrame em uma tabela do banco (modo simples).

    Suporta chamadas modernas e legadas usadas nos testes:

    Formatos aceitos:
      1. (df, db_path, table_name, if_exists='append')  -> novo
      2. (connection, df)                               -> legado (tabela padrao)
      3. (connection, df, table_name)                   -> legado

    Regras adicionais:
      * Se ``table_name`` for uma VIEW legada ("ssas" / "ssa_chamados") redireciona para tabela fisica ``ssa_table`` se existir
      * Filtra (descarta) linhas cujo numero_ssa normalizado resulte em None
      * DataFrame vazio:
          - modo legado: levanta ValueError (test_dataframe_validation_rejects_empty)
          - modo novo: retorna True apenas logando aviso
    """
    if len(args) == 0:
        raise TypeError("insert_dataframe_to_db requer ao menos um argumento")

    # Detecta formato pela primeira posicao
    # Caso novo: primeiro argumento e DataFrame
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
            raise TypeError("Primeiro argumento legado deve ser conexao sqlite3")
        if len(args) < 2:
            raise TypeError("Uso legado requer (conn, df [, table_name])")
        df = args[1]
        if not isinstance(df, pd.DataFrame):  # pragma: no cover
            raise TypeError("Segundo argumento legado deve ser DataFrame")
        table_name = args[2] if len(args) >= 3 else 'ssas'
        db_path = None  # type: ignore[assignment]
        if_exists = kwargs.get('if_exists', 'append')
        legacy_mode = True

    # Normalizacao / validacao DataFrame
    if df.empty:
        if legacy_mode:
            raise ValueError("DataFrame vazio fornecido (modo legado)")
        logger.warning("DataFrame vazio fornecido para insercao (modo novo). Nada a fazer.")
        return True

    work_df = df.copy()
    # Aplicacao de whitelist unificada (evita duplicacao com smart upsert)
    try:
        from .database_upsert_logic import apply_column_whitelist as _apply_wl
        work_df = _apply_wl(work_df)
    except Exception:  # pragma: no cover
        pass
    if 'numero_ssa' in work_df.columns:
        work_df['numero_ssa'] = work_df['numero_ssa'].apply(_normalize_numero_ssa_value)
        # Descarta linhas sem numero_ssa valido (regra implicita dos testes de importacao)
        work_df = work_df[work_df['numero_ssa'].notna()].reset_index(drop=True)

    # Apos normalizacao, se ficar vazio em modo legado, tambem gera ValueError
    if work_df.empty and legacy_mode:
        raise ValueError("DataFrame sem linhas validas apos normalizacao")

    # Redireciona view -> tabela fisica se necessario
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
            # Caminho novo: abrir conexao via caminho
            start_time = time.time()
            logger.info("Iniciando insercao padrao: %s registros em '%s'", len(work_df), table_name)

            with get_db_connection(db_path) as conn:  # type: ignore[arg-type]
                cur = conn.cursor()
                cur.execute("PRAGMA journal_mode")
                journal_mode = cur.fetchone()[0]
                cur.execute("PRAGMA cache_size")
                cache_size = cur.fetchone()[0]
                logger.info("Configuracoes SQLite: journal_mode=%s, cache_size=%s", journal_mode, cache_size)

                final_table = _resolve_target_table(conn, table_name)
                batch_size = min(500, max(1, 999 // len(work_df.columns))) if len(work_df.columns) > 0 else 500
                logger.debug("Batch size calculado: %s linhas para %s colunas", batch_size, len(work_df.columns))
                work_df.reset_index(drop=True, inplace=True)

                if 'numero_ssa' in work_df.columns:
                    ssa_count = work_df['numero_ssa'].notna().sum()
                    logger.info("Registros com SSA: %s/%s", ssa_count, len(work_df))

                insert_start = time.time()
                work_df.to_sql(final_table, conn, if_exists=if_exists, index=False, chunksize=batch_size)  # type: ignore[arg-type]
                insert_time = time.time() - insert_start

                conn.commit()
                commit_time = time.time() - insert_start - insert_time

                total_time = time.time() - start_time
                logger.info("Desempenho insercao padrao: insercao=%.2fs, commit=%.2fs, total=%.2fs, throughput=%.1f registros/s",
                            insert_time, commit_time, total_time, (len(work_df) / total_time) if total_time else 0.0)

            logger.info("%s linhas inseridas (modo padrao) em '%s'", len(work_df), table_name)
            return True
        # Legado: ja temos conexao aberta
        start_time = time.time()
        logger.info("Iniciando insercao legado: %s registros em '%s'", len(work_df), table_name)

        final_table = _resolve_target_table(conn, table_name)  # type: ignore[arg-type]
        batch_size = min(500, max(1, 999 // len(work_df.columns))) if len(work_df.columns) > 0 else 500
        work_df.reset_index(drop=True, inplace=True)

        if 'numero_ssa' in work_df.columns:
            ssa_count = work_df['numero_ssa'].notna().sum()
            logger.info("Registros com SSA: %s/%s", ssa_count, len(work_df))

        insert_start = time.time()
        work_df.to_sql(final_table, conn, if_exists=if_exists, index=False, chunksize=batch_size)  # type: ignore[arg-type]
        insert_time = time.time() - insert_start

        conn.commit()  # type: ignore[union-attr]
        commit_time = time.time() - insert_start - insert_time

        total_time = time.time() - start_time
        logger.info("Desempenho insercao legado: insercao=%.2fs, commit=%.2fs, total=%.2fs, throughput=%.1f registros/s",
                    insert_time, commit_time, total_time, (len(work_df) / total_time) if total_time else 0.0)

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
    _table_name: str = 'ssas',  # parametro legado nao usado
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
                schema_path = schema_file  # usa padrao e resolucao em initialize_database
            initialize_database(db_path, schema_path)
            return True
        logger.error(f"Modo de reset desconhecido: {mode}")
        return False
    except Exception as e:
        logger.error(f"Falha ao resetar database ({mode}): {e}")
        return False


def ensure_indexes(db_path: str, table_name: str = 'ssas') -> bool:
    """Garante indices uteis para consultas comuns."""
    try:
        if not is_valid_identifier(table_name):
            raise ValueError(f"Invalid SQL identifier for table: {table_name}")
        with get_db_connection(db_path) as conn:
            cur = conn.cursor()
            # Descobre colunas existentes para evitar erros ao criar indices
            cur.execute(f"PRAGMA table_info({table_name})")
            cols_info = cur.fetchall() or []
            existing_cols = {row[1] for row in cols_info}  # nome da coluna na posicao 1

            # Indices candidatos e suas colunas
            candidate_indexes = [
                (f"idx_{table_name}_numero_ssa", "numero_ssa"),
                (f"idx_{table_name}_setor_executor", "setor_executor"),
                (f"idx_{table_name}_semana_cadastro", "semana_cadastro"),
                (f"idx_{table_name}_situacao", "situacao"),
            ]

            for idx_name, col in candidate_indexes:
                if not is_valid_identifier(col):
                    logger.warning("Ignorando coluna invalida para indice: %s", col)
                    continue
                if not is_valid_identifier(idx_name):
                    logger.warning("Ignorando nome de indice invalido: %s", idx_name)
                    continue
                if col in existing_cols:
                    cur.execute(f"CREATE INDEX IF NOT EXISTS {idx_name} ON {table_name} ({col})")
            conn.commit()
        return True
    except Exception as e:
        logger.error(f"Erro criando indices: {e}")
        return False


def ensure_column_exists(
    db_path: str,
    table_name: str,
    column_name: str,
    column_definition: str,
) -> bool:
    """Garante que uma coluna exista na tabela fisica alvo."""
    try:
        physical_table = table_name
        # Redireciona somente se a tabela fisica realmente existir para evitar
        # logs de erro "no such table: ssa_table" em cenarios de teste minimo.
        if table_name in {'ssas', 'ssa_chamados'}:
            with get_db_connection(db_path) as _conn:
                cur = _conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name='ssa_table'"
                )
                if cur.fetchone():  # ssa_table existe
                    physical_table = 'ssa_table'

        if not is_valid_identifier(physical_table):
            raise ValueError(f"Invalid SQL identifier for table: {physical_table}")
        if not is_valid_identifier(column_name):
            raise ValueError(f"Invalid SQL identifier for column: {column_name}")

        with get_db_connection(db_path) as conn:
            cursor = conn.execute(f"PRAGMA table_info({physical_table})")  # noqa: S608
            existing_columns = {row[1] for row in cursor.fetchall()}
            if column_name in existing_columns:
                return False
            conn.execute(
                f"ALTER TABLE {physical_table} ADD COLUMN {column_name} {column_definition}"
            )
            conn.commit()
            logger.info(
                "Coluna '%s' adicionada a tabela '%s' com definicao %s",
                column_name,
                physical_table,
                column_definition,
            )
            return True
    except Exception as exc:
        logger.error(
            "Falha ao garantir coluna '%s' na tabela '%s': %s",
            column_name,
            table_name,
            exc,
        )
        return False


# ---- Helpers extraidos para reduzir complexidade da funcao publica ----

# CIRCULAR DEPENDENCY MITIGATION:
# This module has circular dependencies with database_upsert_logic, database_integrity,
# and database_optimized. We use lazy imports (inside functions) for most imports to
# avoid import-time errors. Only database_upsert_logic is imported at top level because
# it only uses lazy imports from this module.
# DO NOT convert lazy imports to top-level imports without testing.

from . import database_upsert_logic as _up  # noqa: E402  # import unico para usar diretamente funcoes refatoradas



def insert_dataframe_with_smart_upsert(
    df: pd.DataFrame | _sqlite3_typehint.Connection,
    db_path: str | pd.DataFrame | None = None,
    table_name: str = 'ssas',
) -> bool:  # noqa: PLR0912, PLR0915, PLR0915, PLR0913, PLR0914
    """Insere DataFrame com logica de upsert (por ``numero_ssa``) em baixo
    nivel. Esta versao foi refatorada para reduzir complexidade mantendo a
    mesma semantica relevante:

    - Linhas sem ``numero_ssa``: insercao direta (append/replace se primeira)
    - Linhas com ``numero_ssa``: upsert simples (delete + insert) se data nova
      for mais recente ou se empatar/ausente.
    - Normalizacao de ``numero_ssa`` e conversao resiliente de colunas de data.

    Dispatcher: Se modo otimizado estiver ativo, delega para implementacao
    otimizada. Modo legado (conn, df) sempre usa implementacao padrao.
    """
    # Suporte retrocompativel:
    #  - Novo contrato: (df, db_path, table_name)
    #  - Contrato legado usado em testes: (conn, df) ou (conn, df, table_name)
    if isinstance(df, _sqlite3_typehint.Connection):  # padrao antigo: primeiro arg e conexao
        conn = df
        real_df = db_path  # neste formato, segundo argumento e o DataFrame
        if not isinstance(real_df, pd.DataFrame):  # tipo incorreto
            logger.error("Uso legado invalido: segundo argumento deve ser DataFrame quando primeiro e conexao")
            return False
        # real_df ja garantido DataFrame acima; apenas verificar vazio
        if real_df.empty:
            return True
        # Modo legado sempre usa implementacao padrao (nao suportado por optimized)
        try:
            return _up.insert_dataframe_with_smart_upsert_impl(real_df, conn, table_name)
        except Exception as e:  # pragma: no cover
            logger.error(f"Falha na insercao (legacy conn mode): {e}")
            return False

    # caminho novo normal
    real_df = df  # type: ignore[assignment]
    if isinstance(real_df, pd.DataFrame) and real_df.empty:
        return True

    # Dispatch: verificar se modo otimizado esta ativo
    if _use_optimized_mode:
        try:
            assert isinstance(real_df, pd.DataFrame)
            assert isinstance(db_path, str)
            from .database_optimized import insert_dataframe_optimized
            return insert_dataframe_optimized(real_df, db_path, table_name)
        except Exception as e:  # pragma: no cover
            logger.error(f"Falha na insercao otimizada: {e}")
            return False
    else:
        # Modo padrao
        try:
            assert isinstance(real_df, pd.DataFrame)
            assert isinstance(db_path, str)
            return _up.insert_dataframe_with_smart_upsert_impl(real_df, db_path, table_name)
        except Exception as e:  # pragma: no cover
            logger.error(f"Falha na insercao: {e}")
            return False


from .numero_ssa_utils import (  # noqa: E402
    _normalize_numero_ssa_value,  # legado (int)
    normalize_numero_ssa as _normalize_numero_ssa_display,
    normalize_numero_ssa_dataframe as _normalize_numero_ssa_dataframe,
)


def normalize_numero_ssa_dataframe(df: pd.DataFrame) -> pd.DataFrame:  # retrocompat
    return _normalize_numero_ssa_dataframe(df)


def normalize_numero_ssa(value) -> str | None:  # retrocompat
    return _normalize_numero_ssa_display(value)


# --- Funcoes de Verificacao e Integridade do Banco ---

def verify_database_integrity(db_path: str, table_name: str = 'ssas') -> dict[str, Any]:  # compat wrapper
    from . import database_integrity as _int
    return _int.verify_database_integrity(db_path, table_name)


def validate_dataframe_before_insert(df: pd.DataFrame, table_name: str = 'ssas') -> dict[str, Any]:  # compat wrapper
    from . import database_validation as _val
    return _val.validate_dataframe_before_insert(df, table_name)


def repair_database_if_needed(
    db_path: str, schema_file: str = 'schema.sql', table_name: str = 'ssas'
) -> bool:  # compat wrapper
    from . import database_integrity as _int
    return _int.repair_database_if_needed(db_path, schema_file, table_name)
