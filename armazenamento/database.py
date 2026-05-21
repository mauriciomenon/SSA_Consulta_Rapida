# armazenamento/database.py 20250725 161500 (v2.1 - Boas Praticas Confirmadas)
# Last modified: 2025-10-29T11:15:00 (circular import documentation)
"""
Modulo para interacao com o banco de dados SQLite.

Responsavel por criar tabelas, inserir DataFrames e consultar dados.
"""

import logging
import os
import re
import sqlite3
import time
from contextlib import contextmanager
from typing import Any, Literal, cast

import pandas as pd

# Importacoes refatoradas serao carregadas de forma lazy dentro dos wrappers para evitar ciclos.
from shared.db_names import CANONICAL_SSA_TABLE, LEGACY_SSA_TABLE_ALIASES

from . import numero_ssa_utils as _numero_ssa_utils
from .identifier_utils import is_valid_identifier
from .numero_ssa_utils import normalize_numero_ssa as _normalize_numero_ssa_display
from .numero_ssa_utils import (
    normalize_numero_ssa_dataframe as _normalize_numero_ssa_dataframe,
)
from .numero_ssa_utils import (
    normalize_numero_ssa_dataframe_storage as _normalize_numero_ssa_dataframe_storage,
)

logger = logging.getLogger(__name__)

# Constantes (evitam "magic numbers" em validacoes)
MIN_FREE_SPACE_GB_WARN = 0.1  # 100MB
MAX_TEXT_LEN = 1000

# Normalizacao agora centralizada em armazenamento.numero_ssa_utils. Mantemos apenas
# constantes realmente usadas localmente. As regras detalhadas vivem em
# core.numero_ssa.normalize_strict e no util compartilhado.

# --- Optimized Mode Dispatch ---
# Flag global para controlar modo otimizado (substituiu monkey-patching)
_use_optimized_mode = False
_resolved_table_cache: dict[tuple[str, str], str] = {}
_VALID_COLUMN_DEFINITIONS = frozenset({"TEXT", "INTEGER", "REAL", "NUMERIC", "BLOB"})


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


def _clear_resolved_table_cache(db_path: str | None = None) -> None:
    if db_path is None:
        _resolved_table_cache.clear()
        return

    normalized_path = ":memory:" if db_path == ":memory:" else os.path.abspath(db_path)
    stale_keys = [key for key in _resolved_table_cache if key[0] == normalized_path]
    for key in stale_keys:
        _resolved_table_cache.pop(key, None)


# --- Gerenciamento de Conexao ---

# Nome do arquivo de schema padrao
DEFAULT_SCHEMA_FILE = "schema.sql"


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
    except Exception as e:
        logger.error(f"Erro durante uso da conexao de banco de dados: {e}")
        if conn:
            conn.rollback()
        raise
    finally:
        if conn:
            conn.close()


# --- Funcoes de Banco de Dados ---

# armazenamento/database.py


def initialize_database(
    db_path: str | sqlite3.Connection, schema_file: str = DEFAULT_SCHEMA_FILE
):  # pylint: disable=redefined-outer-name  # skipcq: PYL-W0621
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
    candidate = ""
    config_dir = ""
    # 1) Se for absoluto, deve existir; caso contrario, erro imediato
    if os.path.isabs(schema_file):
        if not os.path.exists(schema_file):
            raise FileNotFoundError(
                f"Arquivo de schema absoluto nao encontrado: '{schema_file}'"
            )
        schema_path = schema_file
    elif os.path.exists(schema_file):  # 2) relativo direto
        schema_path = schema_file
    else:  # 3) fallback config
        current_file_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(current_file_dir)
        candidate = os.path.join(project_root, "config", os.path.basename(schema_file))
        if os.path.exists(candidate):
            schema_path = candidate
        else:
            config_dir = os.path.join(project_root, "config")
            if os.path.isdir(config_dir):
                try:
                    logger.info("Conteudo da pasta config: %s", os.listdir(config_dir))
                except OSError as exc:
                    logger.warning(
                        "Falha ao listar pasta config '%s': %s", config_dir, exc
                    )
            raise FileNotFoundError(
                "Arquivo de schema nao encontrado. Tentativas:\n"
                f"- relativo ao CWD: {os.path.abspath(schema_file)}\n"
                f"- em config do projeto: {candidate}"
            )

    logger.info(f"Aplicando schema a partir de: '{schema_path}'")
    with open(schema_path, encoding="utf-8") as f:
        schema_sql = f.read()

    # Permitir que testes passem uma conexao ja aberta (retrocompatibilidade)
    if isinstance(db_path, sqlite3.Connection):
        conn = db_path
        conn.executescript(schema_sql)
        conn.commit()
        _clear_resolved_table_cache(_get_connection_db_path(conn))
        return True

    with get_db_connection(db_path) as conn:  # caminho normal (string)
        conn.executescript(schema_sql)
        conn.commit()
    _clear_resolved_table_cache(str(db_path))

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
    try:
        with get_db_connection(db_path) as conn:
            effective_query = query
            if not effective_query:
                resolved_table = _resolve_target_table(conn, table_name)
                effective_query = f"SELECT * FROM {_quote_identifier(resolved_table)}"  # nosec B608  # skipcq: BAN-B608

            logger.debug(
                "Executando consulta: %s com params: %s", effective_query, params
            )
            # pd.read_sql_query e otimo para SELECTs
            df = pd.read_sql_query(
                effective_query,
                conn,
                params=cast(Any, params),
                dtype_backend="numpy_nullable",
            )
        logger.debug(f"Consulta retornou {len(df)} linhas.")
        return df
    except (ValueError, sqlite3.Error, pd.errors.DatabaseError) as e:
        logger.exception(
            "Erro ao executar consulta '%s' com params=%s: %s",
            query or table_name,
            params,
            e,
        )
        if raise_on_error:
            raise
        logger.warning(
            "query_db retornando DataFrame vazio apos falha (raise_on_error=False). "
            "Ative raise_on_error para falhar explicitamente."
        )
        return pd.DataFrame()


def vacuum_analyze_database(db_path: str, *, timeout: float = 30.0) -> dict[str, Any]:
    """Run SQLite VACUUM and ANALYZE for a local database file."""
    if db_path != ":memory:" and not os.path.isfile(db_path):
        error = f"Banco de dados nao encontrado: {db_path}"
        logger.error(error)
        return {"ok": False, "error": error, "db_path": db_path}
    try:
        with sqlite3.connect(db_path, timeout=float(timeout)) as conn:
            conn.execute("VACUUM")
            conn.execute("ANALYZE")
        _clear_resolved_table_cache(str(db_path))
        return {"ok": True, "db_path": db_path}
    except sqlite3.Error as exc:
        logger.exception("Falha ao compactar DB e atualizar estatisticas: %s", exc)
        return {"ok": False, "error": str(exc), "db_path": db_path}


IfExistsPolicy = Literal["fail", "replace", "append"]


def _is_ssa_target_alias(name: str) -> bool:
    return name in {CANONICAL_SSA_TABLE, *LEGACY_SSA_TABLE_ALIASES}


def get_ssa_query(table_name: str = CANONICAL_SSA_TABLE) -> str:
    """Retorna a query canonica de leitura de SSAs para CLI e loaders."""
    if table_name in LEGACY_SSA_TABLE_ALIASES:
        table_name = CANONICAL_SSA_TABLE
    elif table_name != CANONICAL_SSA_TABLE:
        raise ValueError(f"Unsupported table for CLI query: {table_name!r}")
    quoted_table_name = _quote_identifier(table_name)
    query_template = """
    SELECT
        numero_ssa,
        situacao,
        derivada_de,
        localizacao_codigo,
        descricao_localizacao,
        equipamento,
        semana_cadastro,
        data_cadastro,
        descricao_ssa,
        setor_emissor,
        setor_executor,
        solicitante,
        servico_origem,
        grau_prioridade_emissao,
        grau_prioridade_planejamento,
        execucao_simples,
        responsavel_programacao,
        semana_programada,
        responsavel_execucao,
        descricao_execucao,
        id,
        sistema_origem,
        prazo_limite,
        tempo_disponivel,
        data_limite,
        tempo_excedido,
        desde,
        tempo_total,
        desde_1,
        total_tempo_tpe_planejado,
        total_tempo_tex_planejado,
        total_tempo_tpo_planejado,
        total_horas_programadas,
        execucao_parcial,
        anomalia,
        semana_executada,
        num_reprogramacoes
    FROM {table_name}
    """
    return query_template.format(table_name=quoted_table_name)  # nosec B608


def _validate_insert_policy(table_name: str, if_exists: IfExistsPolicy) -> None:
    if if_exists == "replace" and _is_ssa_target_alias(table_name):
        raise ValueError(
            "if_exists='replace' e proibido para a tabela canonica de SSA; "
            "use reset/schema-first antes da insercao"
        )


def _prepare_dataframe_for_simple_insert(
    df: pd.DataFrame, *, legacy_mode: bool
) -> pd.DataFrame:
    if df.empty:
        if legacy_mode:
            raise ValueError("DataFrame vazio fornecido (modo legado)")
        logger.warning(
            "DataFrame vazio fornecido para insercao (modo novo). Nada a fazer."
        )
        return df.copy()

    work_df = df
    try:
        from .database_upsert_logic import (
            prepare_dataframe_for_storage as _prepare_storage_df,
        )

        work_df = _prepare_storage_df(work_df, normalize_derivada=False)
    except Exception as exc:  # pragma: no cover
        logger.exception(
            "Falha ao preparar DataFrame antes da insercao simples: %s",
            exc,
        )
        raise

    if "numero_ssa" in work_df.columns:
        work_df = work_df[work_df["numero_ssa"].notna()].reset_index(drop=True)

    if work_df.empty and legacy_mode:
        raise ValueError("DataFrame sem linhas validas apos normalizacao")

    return work_df


def _calculate_simple_insert_batch_size(column_count: int) -> int:
    return min(500, max(1, 999 // column_count)) if column_count > 0 else 500


def _execute_simple_insert(
    conn: sqlite3.Connection,
    work_df: pd.DataFrame,
    final_table: str,
    if_exists: IfExistsPolicy,
    *,
    mode_label: str,
) -> bool:
    batch_size = _calculate_simple_insert_batch_size(len(work_df.columns))
    logger.debug(
        "Batch size calculado (%s): %s linhas para %s colunas",
        mode_label,
        batch_size,
        len(work_df.columns),
    )
    work_df.reset_index(drop=True, inplace=True)

    if "numero_ssa" in work_df.columns:
        ssa_count = work_df["numero_ssa"].notna().sum()
        logger.info(
            "Registros com SSA (%s): %s/%s", mode_label, ssa_count, len(work_df)
        )

    insert_start = time.time()
    work_df.to_sql(
        final_table, conn, if_exists=if_exists, index=False, chunksize=batch_size
    )
    insert_time = time.time() - insert_start

    conn.commit()
    commit_time = time.time() - insert_start - insert_time
    total_time = time.time() - insert_start
    logger.info(
        "Desempenho insercao %s: insercao=%.2fs, commit=%.2fs, total=%.2fs, throughput=%.1f registros/s",
        mode_label,
        insert_time,
        commit_time,
        total_time,
        (len(work_df) / total_time) if total_time else 0.0,
    )
    return True


def _quote_identifier(name: str) -> str:
    safe_name = str(name or "").strip()
    if not is_valid_identifier(safe_name):
        raise ValueError(f"Invalid SQL identifier: {name!r}")
    return f'"{safe_name}"'


def _normalize_column_definition(column_definition: str) -> str:
    safe_definition = re.sub(r"\s+", " ", str(column_definition or "").strip()).upper()
    if safe_definition not in _VALID_COLUMN_DEFINITIONS:
        raise ValueError(f"Invalid SQL column definition: {column_definition!r}")
    return safe_definition


def _get_connection_db_path(conn: sqlite3.Connection) -> str:
    row = conn.execute("PRAGMA database_list").fetchone()
    if row and len(row) >= 3 and row[2]:
        return os.path.abspath(str(row[2]))
    return ":memory:"


def _resolve_target_table(conn: sqlite3.Connection, table_name: str) -> str:
    safe_table_name = str(table_name or "").strip()
    if not is_valid_identifier(safe_table_name):
        raise ValueError(f"Invalid SQL identifier for table: {table_name!r}")

    lookup_name = safe_table_name.casefold()
    cache_key = (_get_connection_db_path(conn), lookup_name)
    if cache_key in _resolved_table_cache:
        return _resolved_table_cache[cache_key]

    if lookup_name == CANONICAL_SSA_TABLE.casefold() or lookup_name in {
        alias.casefold() for alias in LEGACY_SSA_TABLE_ALIASES
    }:
        canonical_row = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
            (CANONICAL_SSA_TABLE,),
        ).fetchone()
        if canonical_row:
            _resolved_table_cache[cache_key] = CANONICAL_SSA_TABLE
            return CANONICAL_SSA_TABLE

    row = conn.execute(
        "SELECT name, type FROM sqlite_master WHERE lower(name)=?",
        (lookup_name,),
    ).fetchone()
    if row and row[1] == "view":
        canonical_row = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
            (CANONICAL_SSA_TABLE,),
        ).fetchone()
        if canonical_row:
            _resolved_table_cache[cache_key] = CANONICAL_SSA_TABLE
            return CANONICAL_SSA_TABLE
    _resolved_table_cache[cache_key] = safe_table_name
    return safe_table_name


def resolve_target_table(conn: sqlite3.Connection, table_name: str) -> str:
    """Public wrapper for canonical table resolution across runtime entry points."""
    return _resolve_target_table(conn, table_name)


def count_table_rows(db_path: str, table_name: str) -> int:
    """Count rows in a resolved runtime table."""
    with get_db_connection(db_path) as conn:
        resolved_table_name = resolve_target_table(conn, table_name)
        query = f"SELECT COUNT(*) FROM {_quote_identifier(resolved_table_name)}"  # nosec B608 # nosemgrep: python.lang.security.audit.formatted-sql-query.formatted-sql-query, python.sqlalchemy.security.sqlalchemy-execute-raw-query.sqlalchemy-execute-raw-query
        row = conn.execute(query).fetchone()  # nosemgrep: python.lang.security.audit.formatted-sql-query.formatted-sql-query, python.sqlalchemy.security.sqlalchemy-execute-raw-query.sqlalchemy-execute-raw-query
    return int(row[0] if row else 0)


def count_distinct_derivada_edges(
    conn: sqlite3.Connection,
    table_name: str,
) -> int:
    """Count distinct derivada edges on the resolved runtime table/view."""
    resolved_table_name = resolve_target_table(conn, table_name)
    quoted_table_name = _quote_identifier(resolved_table_name)
    query_template = """
        SELECT COUNT(*)
        FROM (
            SELECT numero_ssa, derivada_de
            FROM {table_name}
            WHERE derivada_de IS NOT NULL
            GROUP BY numero_ssa, derivada_de
        ) AS db_edges
    """
    query = query_template.format(table_name=quoted_table_name)  # nosec B608 # nosemgrep: python.lang.security.audit.formatted-sql-query.formatted-sql-query
    row = conn.execute(query).fetchone()  # nosemgrep: python.lang.security.audit.formatted-sql-query.formatted-sql-query, python.sqlalchemy.security.sqlalchemy-execute-raw-query.sqlalchemy-execute-raw-query
    return int(row[0] or 0) if row is not None else 0


def insert_dataframe_to_db(*args, **kwargs) -> bool:  # noqa: C901, PLR0912
    """Insere um DataFrame em uma tabela do banco (modo simples).

    Suporta chamadas modernas e legadas usadas nos testes:

    Formatos aceitos:
      1. (df, db_path, table_name, if_exists='append')  -> novo
      2. (connection, df)                               -> legado (tabela padrao)
      3. (connection, df, table_name)                   -> legado

    Regras adicionais:
      * Se ``table_name`` for uma VIEW legada ("ssas" / "ssa_chamados") redireciona para tabela fisica ``ssa_table`` se existir
      * ``if_exists='replace'`` e proibido para ``ssa_table`` e aliases legados; schema de SSA nasce via schema canonico, nunca por DataFrame
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
        if_exists: IfExistsPolicy = kwargs.get("if_exists", "append")
        legacy_mode = False
        legacy_conn: sqlite3.Connection | None = None
    else:
        # Legado: (conn, df [, table])
        legacy_conn = args[0]
        if not isinstance(legacy_conn, sqlite3.Connection):  # pragma: no cover
            raise TypeError("Primeiro argumento legado deve ser conexao sqlite3")
        if len(args) < 2:
            raise TypeError("Uso legado requer (conn, df [, table_name])")
        df = args[1]
        if not isinstance(df, pd.DataFrame):  # pragma: no cover
            raise TypeError("Segundo argumento legado deve ser DataFrame")
        table_name = args[2] if len(args) >= 3 else "ssas"
        db_path = None
        if_exists = kwargs.get("if_exists", "append")
        legacy_mode = True

    work_df = _prepare_dataframe_for_simple_insert(df, legacy_mode=legacy_mode)
    if work_df.empty:
        return True

    active_conn: sqlite3.Connection | None = legacy_conn

    try:
        if not legacy_mode:
            # Caminho novo: abrir conexao via caminho
            start_time = time.time()
            logger.info(
                "Iniciando insercao padrao: %s registros em '%s'",
                len(work_df),
                table_name,
            )
            if db_path is None:
                raise ValueError("db_path ausente no caminho padrao de insercao")

            with get_db_connection(db_path) as conn:
                active_conn = conn
                cur = conn.cursor()
                cur.execute("PRAGMA journal_mode")
                journal_mode = cur.fetchone()[0]
                cur.execute("PRAGMA cache_size")
                cache_size = cur.fetchone()[0]
                logger.info(
                    "Configuracoes SQLite: journal_mode=%s, cache_size=%s",
                    journal_mode,
                    cache_size,
                )

                final_table = _resolve_target_table(conn, table_name)
                _validate_insert_policy(final_table, if_exists)
                _execute_simple_insert(
                    conn,
                    work_df,
                    final_table,
                    if_exists,
                    mode_label="padrao",
                )
                total_time = time.time() - start_time
                logger.debug(
                    "Tempo total com setup (%s): %.2fs", final_table, total_time
                )

            logger.info(
                "%s linhas inseridas (modo padrao) em '%s'", len(work_df), table_name
            )
            return True
        # Legado: ja temos conexao aberta
        start_time = time.time()
        logger.info(
            "Iniciando insercao legado: %s registros em '%s'", len(work_df), table_name
        )

        if legacy_conn is None:  # pragma: no cover
            raise RuntimeError("Conexao legado ausente em insert_dataframe_to_db")

        final_table = _resolve_target_table(legacy_conn, table_name)
        _validate_insert_policy(final_table, if_exists)
        _execute_simple_insert(
            legacy_conn,
            work_df,
            final_table,
            if_exists,
            mode_label="legado",
        )
        total_time = time.time() - start_time
        logger.debug("Tempo total com setup (%s): %.2fs", final_table, total_time)

        logger.info(
            "%s linhas inseridas (modo legado) em '%s'", len(work_df), final_table
        )
        return True
    except ValueError:
        raise
    except Exception as e:  # pragma: no cover
        if active_conn is not None:
            try:
                if bool(getattr(active_conn, "in_transaction", False)):
                    active_conn.rollback()
            except sqlite3.ProgrammingError:
                logger.debug(
                    "Rollback explicito ignorado em insert_dataframe_to_db: conexao encerrada."
                )
            except Exception as rollback_exc:
                logger.warning(
                    "Falha ao executar rollback explicito em insert_dataframe_to_db: %s",
                    rollback_exc,
                )
        logger.error(f"Falha ao inserir dados na tabela '{table_name}': {e}")
        return False


def reset_database(
    db_path: str,
    mode: str = "table",
    _table_name: str = CANONICAL_SSA_TABLE,  # parametro legado nao usado
    schema_path: str | None = None,
) -> bool:
    """Reseta o banco de dados.

    - mode = 'file': remove o arquivo de banco por completo (se existir).
    - mode = 'table': recria somente a tabela alvo usando o schema.
    """
    try:
        if mode == "file":
            if os.path.exists(db_path):
                os.remove(db_path)
            _clear_resolved_table_cache(db_path)
            return True
        if mode == "table":
            # Reaplica o schema
            if schema_path is None:
                schema_path = (
                    DEFAULT_SCHEMA_FILE  # usa padrao e resolucao em initialize_database
                )
            initialize_database(db_path, schema_path)
            _clear_resolved_table_cache(db_path)
            return True
        logger.error(f"Modo de reset desconhecido: {mode}")
        return False
    except Exception as e:
        logger.error(f"Falha ao resetar database ({mode}): {e}")
        return False


def ensure_indexes(db_path: str, table_name: str = CANONICAL_SSA_TABLE) -> bool:
    """Garante indices uteis para consultas comuns."""
    try:
        with get_db_connection(db_path) as conn:
            cur = conn.cursor()
            resolved_table = _resolve_target_table(conn, table_name)
            quoted_table = _quote_identifier(resolved_table)
            # Descobre colunas existentes para evitar erros ao criar indices
            cur.execute(  # nosemgrep: python.lang.security.audit.formatted-sql-query.formatted-sql-query, python.sqlalchemy.security.sqlalchemy-execute-raw-query.sqlalchemy-execute-raw-query
                f"PRAGMA table_info({quoted_table})"
            )
            cols_info = cur.fetchall() or []
            existing_cols = {row[1] for row in cols_info}  # nome da coluna na posicao 1

            # Indices candidatos e suas colunas
            candidate_indexes = [
                (f"idx_{resolved_table}_numero_ssa", "numero_ssa"),
                (f"idx_{resolved_table}_setor_executor", "setor_executor"),
                (f"idx_{resolved_table}_semana_cadastro", "semana_cadastro"),
                (f"idx_{resolved_table}_situacao", "situacao"),
            ]

            for idx_name, col in candidate_indexes:
                if not is_valid_identifier(col):
                    logger.warning("Ignorando coluna invalida para indice: %s", col)
                    continue
                if not is_valid_identifier(idx_name):
                    logger.warning("Ignorando nome de indice invalido: %s", idx_name)
                    continue
                if col in existing_cols:
                    cur.execute(
                        f"CREATE INDEX IF NOT EXISTS {_quote_identifier(idx_name)} "
                        f"ON {quoted_table} ({_quote_identifier(col)})"
                    )
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
        with get_db_connection(db_path) as conn:
            physical_table = _resolve_target_table(conn, table_name)
            quoted_table = _quote_identifier(physical_table)
            quoted_column = _quote_identifier(column_name)
            safe_column_definition = _normalize_column_definition(column_definition)
            table_exists_row = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
                (physical_table,),
            ).fetchone()
            if not table_exists_row:
                logger.debug(
                    "Tabela '%s' ainda nao existe em '%s'; coluna '%s' sera aplicada apos criacao da tabela.",
                    physical_table,
                    db_path,
                    column_name,
                )
                return False

            cursor = conn.execute(  # nosemgrep: python.lang.security.audit.formatted-sql-query.formatted-sql-query, python.sqlalchemy.security.sqlalchemy-execute-raw-query.sqlalchemy-execute-raw-query
                f"PRAGMA table_info({quoted_table})"
            )
            existing_columns = {row[1] for row in cursor.fetchall()}
            if column_name in existing_columns:
                return False
            conn.execute(  # nosemgrep: python.lang.security.audit.formatted-sql-query.formatted-sql-query, python.sqlalchemy.security.sqlalchemy-execute-raw-query.sqlalchemy-execute-raw-query
                f"ALTER TABLE {quoted_table} ADD COLUMN {quoted_column} {safe_column_definition}"
            )
            conn.commit()
            _clear_resolved_table_cache(db_path)
            logger.info(
                "Coluna '%s' adicionada a tabela '%s' com definicao %s",
                column_name,
                physical_table,
                safe_column_definition,
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


def configure_upsert_short_circuit_policy(policy: str | None) -> None:
    """Configura politica de short-circuit usada no upsert do processo atual."""
    _up.set_runtime_short_circuit_policy(policy)


def insert_dataframe_with_smart_upsert(
    df: pd.DataFrame | sqlite3.Connection,
    db_path: str | pd.DataFrame | None = None,
    table_name: str = CANONICAL_SSA_TABLE,
) -> bool:  # noqa: PLR0912, PLR0914, PLR0915
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
    if isinstance(df, sqlite3.Connection):  # padrao antigo: primeiro arg e conexao
        conn = df
        real_df = db_path  # neste formato, segundo argumento e o DataFrame
        if not isinstance(real_df, pd.DataFrame):  # tipo incorreto
            logger.error(
                "Uso legado invalido: segundo argumento deve ser DataFrame quando primeiro e conexao"
            )
            return False
        # real_df ja garantido DataFrame acima; apenas verificar vazio
        if real_df.empty:
            return True
        # Modo legado sempre usa implementacao padrao (nao suportado por optimized)
        try:
            return _up.insert_dataframe_with_smart_upsert_impl(
                real_df, conn, table_name
            )
        except Exception as e:  # pragma: no cover
            logger.error(f"Falha na insercao (legacy conn mode): {e}")
            return False

    # caminho novo normal
    real_df = df
    if isinstance(real_df, pd.DataFrame) and real_df.empty:
        return True

    if not isinstance(real_df, pd.DataFrame):
        logger.error(
            "insert_dataframe_with_smart_upsert requer DataFrame no caminho novo; recebido: %s",
            type(real_df).__name__,
        )
        return False
    if not isinstance(db_path, str) or not db_path.strip():
        logger.error(
            "insert_dataframe_with_smart_upsert requer db_path str nao vazio; recebido: %r",
            db_path,
        )
        return False
    if not isinstance(table_name, str) or not table_name.strip():
        logger.error(
            "insert_dataframe_with_smart_upsert requer table_name str nao vazio; recebido: %r",
            table_name,
        )
        return False

    # Dispatch: verificar se modo otimizado esta ativo
    if _use_optimized_mode:
        try:
            from .database_optimized import insert_dataframe_optimized

            return insert_dataframe_optimized(real_df, db_path, table_name)
        except Exception as e:  # pragma: no cover
            logger.error(f"Falha na insercao otimizada: {e}")
            return False
    else:
        # Modo padrao
        try:
            # A implementacao de upsert aplica prepare_dataframe_for_upsert()
            # internamente, incluindo whitelist e normalizacao canonica.
            return _up.insert_dataframe_with_smart_upsert_impl(
                real_df, db_path, table_name
            )
        except Exception as e:  # pragma: no cover
            logger.error(f"Falha na insercao: {e}")
            return False


_normalize_numero_ssa_value = _numero_ssa_utils.normalize_numero_ssa_int_legacy_bridge


def normalize_numero_ssa_dataframe(df: pd.DataFrame) -> pd.DataFrame:  # retrocompat
    return _normalize_numero_ssa_dataframe(df)


def normalize_numero_ssa_dataframe_storage(
    df: pd.DataFrame,
) -> pd.DataFrame:  # retrocompat
    return _normalize_numero_ssa_dataframe_storage(df)


def normalize_numero_ssa(value) -> str | None:  # retrocompat
    return _normalize_numero_ssa_display(value)


# --- Funcoes de Verificacao e Integridade do Banco ---


def verify_database_integrity(
    db_path: str,
    table_name: str = CANONICAL_SSA_TABLE,
) -> dict[str, Any]:  # compat wrapper
    from . import database_integrity as _int

    return _int.verify_database_integrity(db_path, table_name)


def validate_dataframe_before_insert(
    df: pd.DataFrame,
    table_name: str = CANONICAL_SSA_TABLE,
) -> dict[str, Any]:  # compat wrapper
    from . import database_validation as _val

    return _val.validate_dataframe_before_insert(df, table_name)


def repair_database_if_needed(
    db_path: str,
    schema_file: str = "schema.sql",
    table_name: str = CANONICAL_SSA_TABLE,
) -> (
    bool
):  # compat wrapper  # pylint: disable=redefined-outer-name  # skipcq: PYL-W0621
    from . import database_integrity as _int

    return _int.repair_database_if_needed(db_path, schema_file, table_name)
