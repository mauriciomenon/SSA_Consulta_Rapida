# core/app_logic.py 20250725 103000 (v3.1 - Refatorado, Excecoes, Logging)
# Last modified: 2025-10-30T15:50:00 (simplified search: removed ALL logical operators, only commas)
"""
Logica central da aplicacao para importacao e atualizacao do banco de dados.

Coordena a verificacao de arquivos modificados, a extracao de dados,
a atualizacao do banco de dados SQLite e o gerenciamento do cache.
"""

import os
import sys
import logging
import json
import sqlite3
import pandas as pd
import re
from pathlib import Path
from typing import List, Dict, Any, Callable, Optional

# Adiciona o diretorio raiz do projeto ao sys.path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
project_root_path = Path(project_root)
sys.path.insert(0, project_root)

from utils import caching  # noqa: E402
from extracao import extractor  # noqa: E402
from armazenamento import database  # noqa: E402
from armazenamento.derivadas_sync import scan_derivadas_consistency, sync_derivadas  # noqa: E402
from utils.path_safety import PathSafetyError, ensure_path_is_allowed  # noqa: E402

# Configura logger especifico para este modulo
logger = logging.getLogger(__name__)

# --- Excecoes Personalizadas ---


class ImporterError(Exception):
    """Excecao base para erros no processo de importacao."""

    pass


class CacheError(ImporterError):
    """Erro relacionado ao sistema de cache."""

    pass


class ExtractionError(ImporterError):
    """Erro durante a extracao de dados de um arquivo."""

    pass


class DatabaseError(ImporterError):
    """Erro durante operacoes no banco de dados."""

    pass


class DatabaseConnectionError(DatabaseError):
    """Erro de conexao com o banco de dados."""

    pass


class DatabaseCorruptionError(DatabaseError):
    """Erro indicando corrupcao no banco de dados."""

    pass


class DatabaseSchemaError(DatabaseError):
    """Erro relacionado ao schema do banco de dados."""

    pass


class DatabaseSpaceError(DatabaseError):
    """Erro de espaco insuficiente em disco."""

    pass


class DataValidationError(ImporterError):
    """Erro de validacao de dados antes da insercao."""

    pass


def _resolve_import_targets(docs_dir: str, db_path: str) -> tuple[Path, Path]:
    """Normaliza e valida caminhos sensiveis antes da importacao."""
    docs_dir_path = ensure_path_is_allowed(
        docs_dir,
        purpose="docs_dir",
        base=project_root_path,
        must_exist=True,
        expect_directory=True,
    )
    db_path_path = ensure_path_is_allowed(
        db_path,
        purpose="db_path",
        base=project_root_path,
        must_exist=False,
        expect_directory=False,
    )
    return docs_dir_path, db_path_path


# --- Funcoes Auxiliares Refatoradas ---


def _get_files_to_process(
    docs_dir: str, cache_file: str, force_import: bool
) -> List[str]:
    """
    Determina quais arquivos precisam ser processados.

    Args:
        docs_dir (str): Diretorio de entrada dos arquivos Excel.
        cache_file (str): Caminho para o arquivo de cache.
        force_import (bool): Se True, forca o reprocessamento de todos os arquivos.

    Returns:
        List[str]: Lista de caminhos completos para os arquivos que precisam ser processados.

    Raises:
        CacheError: Se houver um problema ao acessar ou ler o arquivo de cache.
    """
    try:
        if force_import:
            logger.info(
                "Modo 'force_import' ativado. Todos os arquivos serao reprocessados."
            )
            all_files = caching.get_all_xlsx_files(docs_dir)
            return all_files

        # Verifica se o cache existe
        if not os.path.exists(cache_file):
            logger.info(
                "Arquivo de cache nao encontrado. Todos os arquivos serao processados."
            )
            all_files = caching.get_all_xlsx_files(docs_dir)
            return all_files

        # Compara arquivos usando o cache
        files_to_process = caching.get_files_to_process(docs_dir, cache_file)
        logger.debug(
            f"Arquivos identificados para processamento: {len(files_to_process)}"
        )
        return files_to_process

    except Exception as e:
        logger.error(f"Erro ao determinar arquivos para processamento: {e}")
        raise CacheError(f"Falha na verificacao de arquivos: {e}") from e


def _import_single_file(
    file_path: str,
    db_path: str,
    table_name: str,
    should_cancel: Optional[Callable[[], bool]] = None,
) -> tuple[bool, int]:
    """
    Importa um unico arquivo Excel para o banco de dados.

    Args:
        file_path (str): Caminho completo para o arquivo Excel.
        db_path (str): Caminho para o banco de dados SQLite.
        table_name (str): Nome da tabela no banco de dados.
        should_cancel (Optional[Callable[[], bool]]): Callback consultivo para cancelar a operacao.

    Returns:
        tuple[bool, int]: (sucesso, numero_de_registros_processados)

    Raises:
        ExtractionError: Se houver falha na extracao.
        DatabaseError: Se houver falha na insercao no DB.
    """
    logger.info(f"Iniciando importacao de '{file_path}'...")
    try:
        df = extractor.extract_data_from_excel(file_path, should_cancel=should_cancel)
        if not df.empty:
            df = df.copy()
            if should_cancel and should_cancel():
                raise ExtractionError("operation cancelled")
            # NOVA: Validar dados antes da insercao
            logger.info(f"Validando dados extraidos de '{file_path}'...")
            validation_report = database.validate_dataframe_before_insert(
                df, table_name
            )

            for violation in validation_report.get("violations", []):
                rule = violation.get("rule")
                count = violation.get("count")
                severity = violation.get("severity", "warning")
                sample = violation.get("sample_ssa") or []
                sample_txt = f" (ex.: {', '.join(sample)})" if sample else ""
                message = f"Regra {rule} atingiu {count} linha(s){sample_txt}"
                if severity == "error":
                    logger.error(
                        "Validacao - %s: %s", os.path.basename(file_path), message
                    )
                else:
                    logger.warning(
                        "Validacao - %s: %s", os.path.basename(file_path), message
                    )

            invalid_by_column = validation_report.get("invalid_by_column", {})
            critical_columns = {"numero_ssa", "data_cadastro"}
            rows_to_drop: set[int] = set()
            for column, indices in invalid_by_column.items():
                if column in critical_columns:
                    rows_to_drop.update(indices)

            if rows_to_drop:
                bad_subset = df.loc[list(rows_to_drop)].copy()
                sample_ssas = (
                    bad_subset["numero_ssa"].astype(str).head(5).tolist()
                    if "numero_ssa" in bad_subset.columns
                    else [str(idx) for idx in list(rows_to_drop)[:5]]
                )
                logger.error(
                    "Removendo %s linha(s) com dados obrigatorios ausentes em '%s' (amostra: %s)",
                    len(rows_to_drop),
                    os.path.basename(file_path),
                    ", ".join(sample_ssas),
                )
                df.drop(index=list(rows_to_drop), inplace=True)

            if df.empty:
                logger.error(
                    "Nenhuma linha valida restou apos validacao de '%s'; nada sera inserido.",
                    os.path.basename(file_path),
                )
                return False, 0

            # Se ha problemas criticos, pode escolher entre falhar ou continuar
            if not validation_report["is_valid"]:
                critical_issues = validation_report["issues"]
                logger.error(
                    f"Dados com problemas criticos em '{file_path}': {critical_issues}"
                )

                # Para problemas criticos de validacao, pode escolher:
                # Opcao 1: Falhar imediatamente
                # raise DataValidationError(f"Dados invalidos: {critical_issues}")

                # Opcao 2: Tentar inserir mesmo assim (atual)
                logger.warning("Tentando insercao apesar dos problemas criticos...")
            else:
                logger.info(
                    " Dados validados: %s linhas prontas para insercao",
                    len(df),
                )

            # Garante coluna de rastreio de origem no banco
            database.ensure_column_exists(db_path, table_name, "arquivo_origem", "TEXT")
            if "arquivo_origem" not in df.columns:
                df["arquivo_origem"] = os.path.basename(file_path)
            else:
                df["arquivo_origem"] = df["arquivo_origem"].fillna(
                    os.path.basename(file_path)
                )

            # Conta registros antes de inserir
            record_count = len(df)

            # CORRECAO CRITICA: Usar smart_upsert para evitar duplicatas
            if should_cancel and should_cancel():
                raise ExtractionError("operation cancelled")
            success = database.insert_dataframe_with_smart_upsert(
                df, db_path, table_name
            )
            if success:
                logger.info(
                    f"Importacao de '{file_path}' concluida com sucesso (sem duplicatas)."
                )
                return True, record_count
            else:
                logger.error(
                    f"Falha ao inserir dados de '{file_path}' no banco de dados."
                )
                raise DatabaseError(f"Erro ao inserir dados do arquivo {file_path}")
        else:
            logger.warning(f"Nenhum dado valido extraido de '{file_path}'. Pulando.")
            return True, 0  # Nao e um erro critico, apenas nao ha dados
    except extractor.ExtractionError as e:
        # Normalize extractor error type into core.app_logic.ExtractionError
        raise ExtractionError(str(e)) from e
    except ImporterError:
        raise
    except Exception as e:
        logger.error(f"Erro inesperado ao importar '{file_path}': {e}")
        raise ExtractionError(f"Erro ao importar {file_path}: {e}") from e


def _is_derivadas_sheet_file(file_path: str) -> bool:
    base_name = os.path.basename(file_path).strip().casefold()
    return base_name.startswith("ssas derivadas e relacionadas") and base_name.endswith(".xlsx")


def _discover_derivadas_sheet_files(docs_dir: str) -> List[str]:
    try:
        all_xlsx_files = caching.get_all_xlsx_files(docs_dir)
    except Exception as exc:
        logger.warning("Falha ao listar planilhas especiais de derivadas em '%s': %s", docs_dir, exc)
        return []
    return sorted(
        {path for path in all_xlsx_files if _is_derivadas_sheet_file(path)},
        key=lambda path: os.path.basename(path).casefold(),
    )


def _needs_db_only_derivadas_sync(db_path: str, table_name: str) -> bool:
    """Decide if derivadas sync should run with DB-only source when no files changed."""

    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", str(table_name or "")):
        logger.warning("Nome de tabela invalido para preflight de derivadas: %r", table_name)
        return False

    try:
        with database.get_db_connection(db_path) as conn:
            db_edges_count = int(
                conn.execute(
                    f"""
                    SELECT COUNT(*)
                    FROM (
                        SELECT numero_ssa, derivada_de
                        FROM "{table_name}"
                        WHERE derivada_de IS NOT NULL
                        GROUP BY numero_ssa, derivada_de
                    ) AS db_edges
                    """
                ).fetchone()[0]
            )
            if db_edges_count <= 0:
                return False

            ready_tables = {
                "ssa_derivada_matrix",
                "ssa_derivada_summary",
                "ssa_derivada_sync_run",
            }
            existing_tables = {
                row[0]
                for row in conn.execute(
                    "SELECT name FROM sqlite_master WHERE type = 'table'"
                ).fetchall()
            }
            if not ready_tables.issubset(existing_tables):
                return True

            matrix_active = int(
                conn.execute("SELECT COUNT(*) FROM ssa_derivada_matrix WHERE active = 1").fetchone()[0]
            )
            summary_total = int(conn.execute("SELECT COUNT(*) FROM ssa_derivada_summary").fetchone()[0])
            latest = conn.execute(
                """
                SELECT db_edges
                FROM ssa_derivada_sync_run
                WHERE status = 'ok'
                ORDER BY sync_run_id DESC
                LIMIT 1
                """
            ).fetchone()

            if latest is None:
                return True
            latest_db_edges = int(latest[0] or 0)
            return matrix_active <= 0 or summary_total <= 0 or latest_db_edges != db_edges_count
    except sqlite3.Error as exc:
        logger.warning("Preflight DB-only de derivadas falhou com sqlite error: %s", exc)
        return False
    except Exception as exc:
        logger.warning("Preflight DB-only de derivadas falhou: %s", exc)
        return False


def _run_derivadas_sync_phase(
    db_path: str,
    table_name: str,
    derivadas_sheet_files: List[str],
) -> tuple[bool, List[str], Dict[str, Any]]:
    existing_files = sorted(
        {path for path in derivadas_sheet_files if os.path.exists(path)},
        key=lambda path: os.path.basename(path).casefold(),
    )
    sync_kwargs: Dict[str, Any] = {
        "db_path": db_path,
        "table_name": table_name,
        "include_db_source": True,
        "actor": "importer-derivadas-sync",
    }
    if existing_files:
        sync_kwargs["sheet_files"] = existing_files

    report = sync_derivadas(**sync_kwargs)
    sheet_stats = report.get("sheet_stats") or {}
    reported_files = report.get("sheet_files") or []
    accepted_edges = int(sheet_stats.get("accepted_edges", 0) or 0)
    special_layout_detected = int(sheet_stats.get("special_layout_detected", 0) or 0)
    has_sheet_evidence = accepted_edges > 0 or special_layout_detected > 0
    db_stats = report.get("db_stats") or {}
    db_edges = int(db_stats.get("accepted_edges", 0) or 0)
    merge_stats = report.get("merge_stats") or {}
    merged_edges = int(merge_stats.get("merged_edges", 0) or 0)
    has_graph_evidence = db_edges > 0 or merged_edges > 0

    if existing_files and len(reported_files) != len(existing_files):
        logger.error(
            "Sync de derivadas especiais sem cobertura completa de arquivos (esperado=%s, recebido=%s).",
            len(existing_files),
            len(reported_files),
        )
        return False, existing_files, report
    if existing_files and not has_sheet_evidence and not has_graph_evidence:
        logger.error(
            "Sync de derivadas especiais sem evidencia de parse valido (accepted_edges=0, special_layout_detected=0)."
        )
        return False, existing_files, report
    if not has_graph_evidence:
        logger.warning("Sync de derivadas concluido sem arestas materializadas no grafo.")

    consistency = scan_derivadas_consistency(db_path=db_path)
    report = dict(report)
    report["consistency_scan"] = consistency
    if not bool(consistency.get("schema_ready")) or not bool(consistency.get("is_consistent")):
        issue_counts = consistency.get("issue_counts") or {}
        logger.error(
            "Sync de derivadas finalizou com inconsistencias no scan pos-sync. issue_counts=%s",
            json.dumps(issue_counts, ensure_ascii=True),
        )
        return False, existing_files, report

    cached_sheets = list(existing_files) if has_sheet_evidence else []
    logger.info(
        "Sync de derivadas concluido (planilhas=%s, merged_edges=%s, db_edges=%s, sheet_edges=%s).",
        len(existing_files),
        merged_edges,
        db_edges,
        accepted_edges,
    )
    return True, cached_sheets, report


def _update_cache_after_import(
    processed_files: List[str], cache_file: str, docs_dir: str
) -> None:
    """
    Atualiza o arquivo de cache apos uma importacao bem-sucedida.

    Args:
        processed_files (List[str]): Lista de arquivos processados com sucesso.
        cache_file (str): Caminho para o arquivo de cache.
        docs_dir (str): Diretorio de entrada dos arquivos Excel.

    Raises:
        CacheError: Se houver falha ao atualizar o cache.
    """
    logger.debug("Atualizando cache...")
    try:
        # Atualiza o cache apenas para os arquivos processados com sucesso
        caching.update_cache_for_files(processed_files, cache_file)
        logger.info("Cache atualizado com sucesso.")
    except Exception as e:
        logger.error(f"Erro ao atualizar o cache: {e}")
        raise CacheError("Falha ao atualizar o cache apos importacao.") from e


# --- Funcao Principal Refatorada ---


def run_importer_logic(
    docs_dir: str = "docs_entrada",
    data_dir: str = "data",
    db_name: str = "ssas.db",
    table_name: str = "ssa_table",
    force_import: bool = False,
    should_cancel: Optional[Callable[[], bool]] = None,
    progress_callback: Optional[Callable[[str, Dict[str, Any]], None]] = None,
) -> bool:
    """
    Executa a logica principal de importacao de dados.

    Args:
        docs_dir (str): Diretorio de entrada dos arquivos Excel.
        data_dir (str): Diretorio para armazenamento do banco de dados e cache.
        db_name (str): Nome do arquivo do banco de dados SQLite.
        table_name (str): Nome da tabela no banco de dados.
        force_import (bool): Se True, forca a reimportacao de todos os arquivos.
        should_cancel (Optional[Callable[[], bool]]): Callback consultivo que indica
            se a importacao deve ser interrompida. Deve retornar True para cancelar.
        progress_callback (Optional[Callable]): Callback para reportar progresso da importacao.

    Returns:
        bool: True se o banco de dados foi atualizado, False caso contrario.
    """
    logger.info("=== Iniciando processo de importacao ===")

    # --- Configuracao de Caminhos ---
    try:
        docs_dir_path = ensure_path_is_allowed(
            docs_dir,
            purpose="docs_dir",
            base=project_root_path,
            must_exist=True,
            expect_directory=True,
        )
        data_dir_path = ensure_path_is_allowed(
            data_dir,
            purpose="data_dir",
            base=project_root_path,
            must_exist=False,
            expect_directory=True,
        )
    except PathSafetyError as e:
        logger.error(f"Caminho bloqueado na importacao: {e}")
        raise

    try:
        db_path_obj = ensure_path_is_allowed(
            os.path.join(str(data_dir_path), db_name),
            purpose="db_path",
            base=project_root_path,
            must_exist=False,
            expect_directory=False,
        )
    except PathSafetyError as e:
        logger.error(f"Caminho de DB bloqueado: {e}")
        raise

    db_path = str(db_path_obj)
    cache_file = os.path.join(str(data_dir_path), "file_cache.json")
    docs_dir = str(docs_dir_path)
    data_dir = str(data_dir_path)

    try:
        # --- 0. Verificar e reparar integridade do banco de dados ---
        logger.info("Verificando integridade do banco de dados...")

        # Criar diretorio de dados se nao existir
        os.makedirs(data_dir, exist_ok=True)

        # Verificar e reparar banco se necessario
        if not database.repair_database_if_needed(db_path, table_name=table_name):
            logger.error(
                "Falha critica: nao foi possivel garantir integridade do banco de dados"
            )
            raise DatabaseCorruptionError("Banco de dados inacessivel ou corrompido")

        # Verificacao adicional de integridade
        integrity_report = database.verify_database_integrity(db_path, table_name)
        if not integrity_report["is_valid"]:
            # Classificar tipo de erro baseado no relatorio
            issues = integrity_report["issues"]

            if not integrity_report["database_accessible"]:
                raise DatabaseConnectionError(f"Banco de dados inacessivel: {issues}")
            elif (
                not integrity_report["table_exists"]
                or not integrity_report["schema_valid"]
            ):
                raise DatabaseSchemaError(f"Problemas de schema: {issues}")
            elif not integrity_report["data_consistent"]:
                raise DatabaseCorruptionError(f"Dados corrompidos: {issues}")
            elif not integrity_report["disk_space_sufficient"]:
                raise DatabaseSpaceError(f"Espaco em disco insuficiente: {issues}")
            else:
                raise DatabaseError(f"Problemas gerais no banco: {issues}")

        # Log de avisos se houver
        if integrity_report["warnings"]:
            for warning in integrity_report["warnings"]:
                logger.warning(f"Aviso do banco: {warning}")

        logger.info(" Integridade do banco de dados verificada")

        # --- 1. Determinar arquivos a serem processados ---
        files_to_process = _get_files_to_process(docs_dir, cache_file, force_import)
        derivadas_sheet_files = _discover_derivadas_sheet_files(docs_dir)
        db_only_derivadas_sync = False
        total_files = len(files_to_process)
        progress_cb = progress_callback

        def _emit_progress(event_type: str, data: Dict[str, Any]) -> None:
            nonlocal progress_cb
            if not progress_cb:
                return
            try:
                progress_cb(event_type, data)
            except Exception as exc:
                logger.warning(
                    "Progress callback failed for event '%s': %s. Disabling progress callback.",
                    event_type,
                    exc,
                    exc_info=True,
                )
                progress_cb = None

        _emit_progress("start", {"total": total_files})

        if not files_to_process and not derivadas_sheet_files:
            db_only_derivadas_sync = _needs_db_only_derivadas_sync(db_path=db_path, table_name=table_name)
            if not db_only_derivadas_sync:
                logger.info(
                    "Nenhum arquivo novo/modificado nem planilha especial de derivadas encontrada."
                )
                _emit_progress("finish", {"total": 0, "processed": 0, "errors": []})
                return False
            logger.info("Nenhum arquivo novo detectado; executando sync DB-only de derivadas por preflight.")

        if derivadas_sheet_files:
            logger.info(
                "Fase dedicada de derivadas habilitada com %s planilha(s) especial(is).",
                len(derivadas_sheet_files),
            )

        logger.info(
            f"{len(files_to_process)} arquivo(s) identificado(s) para importacao."
        )

        # --- 2. Processar cada arquivo ---
        successfully_processed_files = []
        critical_errors = []

        try:
            for index, file_path in enumerate(files_to_process):
                if should_cancel and should_cancel():
                    logger.info("Cancelamento solicitado; interrompendo importacao.")
                    break
                base_name = os.path.basename(file_path)

                # Notify file start
                _emit_progress(
                    "file_start",
                    {
                        "current": index + 1,
                        "total": total_files,
                        "filename": base_name,
                    },
                )

                if base_name.startswith("~$"):
                    logger.info("Ignorando arquivo temporario '%s'", base_name)
                    continue
                if _is_derivadas_sheet_file(file_path):
                    logger.info(
                        "Planilha especial de derivadas detectada: '%s' (fase dedicada separada).",
                        base_name,
                    )
                    continue
                try:
                    success, record_count = _import_single_file(
                        file_path,
                        db_path,
                        table_name,
                        should_cancel=should_cancel,
                    )
                    if success:
                        successfully_processed_files.append(file_path)
                        # Notify file success
                        _emit_progress(
                            "file_success",
                            {"filename": base_name, "records": record_count},
                        )
                except DatabaseConnectionError as e:
                    logger.error(
                        f"Erro de conexao com banco ao processar '{file_path}': {e}"
                    )
                    logger.error(
                        "Interrompendo processamento devido a falha de conexao"
                    )
                    critical_errors.append(("connection", file_path, str(e)))
                    _emit_progress(
                        "file_error", {"filename": base_name, "error": str(e)}
                    )
                    break
                except DatabaseCorruptionError as e:
                    logger.error(f"Corrupcao detectada ao processar '{file_path}': {e}")
                    logger.info("Tentando reparo automatico do banco...")
                    _emit_progress(
                        "file_error", {"filename": base_name, "error": str(e)}
                    )
                    if database.repair_database_if_needed(
                        db_path, table_name=table_name
                    ):
                        logger.info("Reparo bem-sucedido, continuando processamento...")
                        critical_errors.append(
                            ("corruption_repaired", file_path, str(e))
                        )
                        continue
                    else:
                        logger.error("Falha no reparo automatico")
                        critical_errors.append(("corruption_failed", file_path, str(e)))
                        break
                except DatabaseSpaceError as e:
                    logger.error(
                        f"Espaco em disco insuficiente ao processar '{file_path}': {e}"
                    )
                    critical_errors.append(("space", file_path, str(e)))
                    _emit_progress(
                        "file_error", {"filename": base_name, "error": str(e)}
                    )
                    break
                except DatabaseSchemaError as e:
                    logger.error(f"Erro de schema ao processar '{file_path}': {e}")
                    logger.info("Tentando recriacao do schema...")
                    _emit_progress(
                        "file_error", {"filename": base_name, "error": str(e)}
                    )
                    if database.initialize_database(db_path):
                        logger.info("Schema recriado, continuando processamento...")
                        critical_errors.append(("schema_repaired", file_path, str(e)))
                        continue
                    else:
                        logger.error("Falha na recriacao do schema")
                        critical_errors.append(("schema_failed", file_path, str(e)))
                        break
                except DataValidationError as e:
                    logger.warning(
                        f"Dados invalidos em '{file_path}': {e}. Pulando arquivo..."
                    )
                    critical_errors.append(("validation", file_path, str(e)))
                    _emit_progress(
                        "file_error", {"filename": base_name, "error": str(e)}
                    )
                    continue
                except ExtractionError as e:
                    msg = str(e).lower()
                    if "operation cancelled" in msg and should_cancel:
                        logger.info("Cancelamento solicitado; interrompendo importacao.")
                        break
                    logger.warning(
                        f"Erro de extracao em '{file_path}': {e}. Pulando arquivo..."
                    )
                    critical_errors.append(("extraction", file_path, str(e)))
                    _emit_progress(
                        "file_error", {"filename": base_name, "error": str(e)}
                    )
                    continue
                except DatabaseError as e:
                    logger.error(
                        f"Erro de banco ao processar '{file_path}': {e}. Continuando..."
                    )
                    critical_errors.append(("database_generic", file_path, str(e)))
                    _emit_progress(
                        "file_error", {"filename": base_name, "error": str(e)}
                    )
                    continue
                except Exception as e:
                    logger.error(
                        f"Erro inesperado ao processar '{file_path}': {e}. Continuando..."
                    )
                    critical_errors.append(("unexpected", file_path, str(e)))
                    _emit_progress(
                        "file_error", {"filename": base_name, "error": str(e)}
                    )
                    continue
            sync_materialized = False
            derivadas_sync_blocking_error = False
            should_run_derivadas_sync = (
                bool(successfully_processed_files)
                or bool(derivadas_sheet_files)
                or bool(db_only_derivadas_sync)
            )
            if should_run_derivadas_sync:
                if should_cancel and should_cancel():
                    logger.info("Cancelamento solicitado; sync de derivadas especiais nao sera executado.")
                else:
                    try:
                        sync_ok, synced_sheets, sync_report = _run_derivadas_sync_phase(
                            db_path=db_path,
                            table_name=table_name,
                            derivadas_sheet_files=derivadas_sheet_files,
                        )
                        if sync_ok and not derivadas_sync_blocking_error:
                            for special_file in synced_sheets:
                                if special_file not in successfully_processed_files:
                                    successfully_processed_files.append(special_file)
                            db_edges = int(((sync_report.get("db_stats") or {}).get("accepted_edges", 0) or 0))
                            merged_edges = int(((sync_report.get("merge_stats") or {}).get("merged_edges", 0) or 0))
                            if db_edges > 0 or merged_edges > 0:
                                sync_materialized = True
                            _emit_progress(
                                "file_success",
                                {
                                    "filename": (
                                        os.path.basename(synced_sheets[0])
                                        if len(synced_sheets) == 1
                                        else f"SSAs Derivadas e Relacionadas ({len(synced_sheets)} arquivos)"
                                    ),
                                    "records": int((sync_report.get("merge_stats") or {}).get("merged_edges", 0)),
                                },
                            )
                        if not sync_ok:
                            derivadas_sync_blocking_error = True
                            consistency_scan = sync_report.get("consistency_scan") or {}
                            issue_counts = consistency_scan.get("issue_counts") or {}
                            issue_text = json.dumps(issue_counts, ensure_ascii=True)
                            error_message = (
                                f"Sync de derivadas sem evidencia valida (consistency={issue_text})"
                                if issue_counts
                                else "Sync de derivadas sem evidencia valida"
                            )
                            critical_errors.append(("derivadas_sync", docs_dir, error_message))
                            _emit_progress(
                                "file_error",
                                {
                                    "filename": "SSAs Derivadas e Relacionadas",
                                    "error": error_message,
                                },
                            )
                    except Exception as e:
                        derivadas_sync_blocking_error = True
                        logger.error(
                            "Falha ao sincronizar derivadas a partir de planilhas especiais: %s",
                            e,
                            exc_info=True,
                        )
                        critical_errors.append(("derivadas_sync", docs_dir, str(e)))
                        _emit_progress(
                            "file_error",
                            {"filename": "SSAs Derivadas e Relacionadas", "error": str(e)},
                        )
        finally:
            _emit_progress(
                "finish",
                {
                    "total": total_files,
                    "processed": len(successfully_processed_files),
                    "errors": critical_errors,
                },
            )

        # Log de resumo de erros
        if critical_errors:
            logger.warning(
                f"Processamento concluido com {len(critical_errors)} erro(s):"
            )
            for error_type, file_path, message in critical_errors:
                logger.warning(
                    f"  - {error_type}: {os.path.basename(file_path)} -> {message}"
                )

        if derivadas_sync_blocking_error:
            logger.error(
                "Importacao concluida com falha bloqueante de integridade em derivadas. "
                "Cache nao sera atualizado nesta execucao."
            )
            return False

        # --- 3. Atualizar cache apenas se houve sucesso ---
        if successfully_processed_files:
            _update_cache_after_import(
                successfully_processed_files, cache_file, docs_dir
            )
            logger.info("=== Processo de importacao concluido com atualizacoes ===")
            return True
        elif sync_materialized:
            logger.info("=== Processo de importacao concluiu sync de derivadas materializado (sem novos arquivos em cache) ===")
            return True
        else:
            logger.info("Nenhum arquivo foi processado com sucesso.")
            return False

    except ImporterError:
        # Re-levanta excecoes personalizadas
        raise
    except Exception as e:
        logger.critical(
            f"Erro inesperado no processo de importacao: {e}", exc_info=True
        )
        raise ImporterError("Erro critico no processo de importacao.") from e


def get_filter_alias_map() -> Dict[str, Any]:
    """
    Carrega mapeamento de aliases para filtros, consistente com GUI.
    Busca em config/filter_aliases.json para sincronização entre interfaces.

    Returns:
        Dicionário com aliases globais e por coluna
    """
    # Resolve config path relative to repository root
    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    cfg_path = os.path.join(repo_root, "config", "filter_aliases.json")

    if not os.path.exists(cfg_path):
        return {}

    try:
        with open(cfg_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError, ValueError, TypeError) as exc:
        logger.warning("Falha ao carregar aliases de filtro de '%s': %s", cfg_path, exc)
        return {}

    if isinstance(data, dict):
        return data
    logger.warning("Arquivo de aliases em formato invalido: '%s'.", cfg_path)
    return {}


def apply_filter_aliases(search_terms: List[str]) -> List[str]:
    """
    Aplica aliases de filtro aos termos de busca para consistência entre interfaces.

    Args:
        search_terms: Lista de termos brutos

    Returns:
        Lista de termos com aliases aplicados
    """
    if not search_terms:
        return search_terms

    alias_map = get_filter_alias_map()
    global_aliases = alias_map.get("_global", {})

    if not isinstance(global_aliases, dict):
        global_aliases = {}

    mapped_terms = []
    for term in search_terms:
        if isinstance(term, str):
            key = term.strip().casefold()
            # Busca alias global (case-insensitive)
            mapped = None
            for alias_key, alias_value in global_aliases.items():
                if alias_key.casefold() == key:
                    mapped = alias_value
                    break
            mapped_terms.append(mapped if mapped else term)
        else:
            mapped_terms.append(term)

    return mapped_terms


def parse_search_terms(
    search_terms: List[str],
    default_mode: str = "contains",
) -> List[Dict[str, Any]]:
    """
    Converte termos brutos em uma estrutura padronizada com modo e polaridade.

    APLICA ALIASES: Termos são normalizados usando config/filter_aliases.json
    para consistência entre GUI e CLI.

    SIMPLIFIED: No logical operators (OU/OR/AND/E) - ONLY commas separate terms.
    - General search: all terms are required (AND logic implicit, all group=0)
    - Column filters: any term matches (OR logic handled in column filter code)

    Modos aceitos por termo:
    - contem (padrao): foo
    - comeca com: ^foo
    - termina com: foo$
    - igual: =foo
    - regex: ~foo.*bar
    Negativo: prefixar ! (ou -) antes do termo (ex.: !^adm, !=fechado, !$2025, !~regex)
    """
    # APLICA ALIASES PRIMEIRO para consistência com GUI
    search_terms = apply_filter_aliases(search_terms)

    parsed: List[Dict[str, Any]] = []
    if not search_terms:
        return parsed
    if not isinstance(search_terms, list):
        return parsed

    allowed_modes = {"contains", "prefix", "suffix", "exact", "regex"}
    fallback_mode = default_mode if default_mode in allowed_modes else "contains"

    # Simplified: process all terms directly, all with group=0 (AND logic)
    for raw in search_terms:
        if not isinstance(raw, str):
            continue
        t = raw.strip()
        if not t:
            continue
        negative = False
        if (t.startswith("!") or t.startswith("-")) and len(t) > 1:
            negative = True
            t = t[1:]
        mode = fallback_mode
        value = t
        if t.startswith("~") and len(t) > 1:
            mode = "regex"
            value = t[1:]
        elif t.startswith("=") and len(t) > 1:
            mode = "exact"
            value = t[1:]
        elif t.startswith("$") and len(t) > 1:
            mode = "suffix"
            value = t[1:]
        elif fallback_mode != "regex" and t.startswith("^") and len(t) > 1:
            mode = "prefix"
            value = t[1:]
        elif fallback_mode != "regex" and t.endswith("$") and len(t) > 1:
            mode = "suffix"
            value = t[:-1]
        parsed.append(
            {
                "raw": raw,
                "mode": mode,
                "value": value,
                "negative": negative,
                "group": 0,  # All terms in same group (AND logic)
            }
        )
    return parsed


def filter_dataframe(
    df: pd.DataFrame, search_terms: list, search_columns: Optional[list] = None
) -> pd.DataFrame:
    """
    Filtra um DataFrame com base em uma lista de termos de busca (strings) ou
    termos ja parseados por parse_search_terms().

     OTIMIZACAO: Agora permite especificar colunas de busca para melhor performance.

    Args:
        df: DataFrame para filtrar
        search_terms: Lista de termos de busca ou termos parseados
        search_columns: Lista de colunas especificas para buscar. Se None, busca em
                       colunas prioritarias: ['numero_ssa', 'situacao', 'setor_executor',
                       'setor_emissor', 'descricao_servico']

    Modos por termo: contem (padrao), comeca (^), termina ($), igual (=), regex (~),
    com suporte a negativos (! ou -).
    """
    if df is None or df.empty or not search_terms:
        return df

    #  OTIMIZACAO: Usar apenas colunas prioritarias se nao especificado
    if search_columns is None:
        # Colunas mais frequentemente pesquisadas (ordem por relevancia)
        # Inclui campos de descricao utilizados na GUI: descricao_ssa e descricao_execucao
        priority_columns = [
            "numero_ssa",
            "situacao",
            "setor_executor",
            "setor_emissor",
            "descricao_ssa",
            "descricao_execucao",
            "descricao_servico",
            "observacao",
            "prazo_limite_str",
            "data_cadastro_str",
        ]
        # Filtrar apenas colunas que existem no DataFrame
        search_columns = [col for col in priority_columns if col in df.columns]

        # Se nenhuma coluna prioritaria existe, usar todas as de texto como fallback
        if not search_columns:
            search_columns = df.select_dtypes(include=["object", "string"]).columns.tolist()

    # Criar DataFrame base apenas com colunas de busca
    available_search_cols = [col for col in search_columns if col in df.columns]
    if not available_search_cols:
        logger.warning("Nenhuma coluna de busca valida encontrada")
        return df

    base_str_df = (
        df[available_search_cols]
        .select_dtypes(include=["object", "string"])
        .fillna("")
        .astype(str)
    )
    if base_str_df.shape[1] == 0:
        # Sem colunas de texto, nao ha onde buscar: retorna DataFrame vazio
        return df.iloc[0:0]

    logger.debug(
        f" Buscando em {len(base_str_df.columns)} colunas: {list(base_str_df.columns)}"
    )

    # Permite tanto termos brutos (str) quanto parseados (dict)
    if search_terms and isinstance(search_terms[0], dict):
        terms = search_terms  # ja parseados
    else:
        terms = parse_search_terms(search_terms)

    # Agrupa termos por disjuncao (OR). Cada grupo e uma conjuncao interna (AND).
    grouped_terms: Dict[int, List[Dict[str, Any]]] = {}
    for term in terms:
        group_idx = term.get("group")
        if group_idx is None:
            group_idx = 0
        grouped_terms.setdefault(int(group_idx), []).append(term)

    if not grouped_terms:
        return df

    # Cache de patterns: pre-compila patterns para evitar re.escape repetido
    pattern_cache = {}
    for term in terms:
        mode = term.get("mode", "contains")
        value = term.get("value", "") or ""
        cache_key = (mode, value)

        if cache_key not in pattern_cache:
            if mode == "contains":
                pattern_cache[cache_key] = (value, False)
            elif mode == "prefix":
                pattern_cache[cache_key] = (f"^{re.escape(value)}", True)
            elif mode == "suffix":
                pattern_cache[cache_key] = (f"{re.escape(value)}$", True)
            elif mode == "exact":
                pattern_cache[cache_key] = (f"^{re.escape(value)}$", True)
            elif mode == "regex":
                pattern_cache[cache_key] = (value, True)
            else:
                pattern_cache[cache_key] = (value, False)

    def _mask_for_term(term: Dict[str, Any]) -> pd.Series:
        mode = term.get("mode", "contains")
        value = term.get("value", "") or ""
        cache_key = (mode, value)

        pattern, use_regex = pattern_cache.get(cache_key, (value, False))

        def _contains(pattern: str, *, regex: bool) -> pd.Series:
            return base_str_df.apply(
                lambda col: col.str.contains(pattern, case=False, na=False, regex=regex)
            ).any(axis=1)

        if mode == "regex":
            try:
                return _contains(pattern, regex=True)
            except re.error:
                return _contains(pattern, regex=False)

        return _contains(pattern, regex=use_regex)

    final_mask = pd.Series(False, index=df.index)

    for group_terms in grouped_terms.values():
        if not group_terms:
            continue
        group_mask = pd.Series(True, index=df.index)
        positives = [t for t in group_terms if not t.get("negative")]
        negatives = [t for t in group_terms if t.get("negative")]

        for term in positives:
            group_mask = group_mask & _mask_for_term(term)

        for term in negatives:
            group_mask = group_mask & (~_mask_for_term(term))

        final_mask = final_mask | group_mask

    if final_mask.any():
        return df[final_mask]
    return df.iloc[0:0] if grouped_terms else df


def import_files_to_database(
    docs_dir: str,
    db_path: str = "data/ssas.db",
    force_import: bool = False,
    raise_on_error: bool = False,
) -> bool:
    """
    Importa arquivos de um diretorio para o banco de dados.

    Args:
        docs_dir: Diretorio contendo arquivos Excel
        db_path: Caminho para o banco de dados
        force_import: Se True, forca reimportacao de todos os arquivos

    Returns:
        bool: True se importacao foi bem-sucedida
    """
    try:
        safe_docs_dir, safe_db_path = _resolve_import_targets(docs_dir, db_path)

        # Extrair diretorio e nome do banco
        data_dir = safe_db_path.parent
        db_name = safe_db_path.name

        # Criar diretorio de dados se nao existir
        os.makedirs(data_dir, exist_ok=True)

        # Executar logica de importacao
        success = run_importer_logic(
            docs_dir=str(safe_docs_dir),
            data_dir=str(data_dir),
            db_name=db_name,
            table_name="ssa_table",
            force_import=force_import,
        )

        return success

    except PathSafetyError as e:
        logger.error(f"Caminho rejeitado na importacao: {e}")
        if raise_on_error:
            raise
        return False
    except Exception as e:
        logger.error(f"Erro na importacao de arquivos: {e}")
        if raise_on_error:
            raise
        return False


def get_filtered_data(
    db_path: str = "data/ssas.db",
    filters: Dict[str, Any] | None = None,
) -> pd.DataFrame:
    """
    Obtem dados filtrados do banco de dados.

    Args:
        db_path: Caminho para o banco de dados
        filters: Dicionario com filtros a aplicar

    Returns:
        DataFrame com dados filtrados
    """
    try:
        safe_db_path = ensure_path_is_allowed(
            db_path,
            purpose="db_path",
            base=project_root_path,
            must_exist=False,
            expect_directory=False,
        )
    except PathSafetyError as e:
        logger.error(f"Caminho rejeitado ao acessar banco: {e}")
        return pd.DataFrame()

    try:
        # Conectar ao banco e obter dados
        with database.get_db_connection(str(safe_db_path)) as conn:
            query = "SELECT * FROM ssas"
            df = pd.read_sql_query(query, conn)

        # Aplicar filtros se fornecidos
        if filters:
            for column, value in filters.items():
                if column in df.columns and value is not None:
                    # Aplicar filtro case-insensitive
                    df = df[
                        df[column]
                        .astype(str)
                        .str.contains(str(value), case=False, na=False)
                    ]

        return df

    except Exception as e:
        logger.error(f"Erro ao obter dados filtrados: {e}")
        return pd.DataFrame()  # Retorna DataFrame vazio em caso de erro
