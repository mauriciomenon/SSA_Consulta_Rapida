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
import time
from datetime import datetime
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
from shared.db_names import CANONICAL_SSA_TABLE  # noqa: E402
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

    def __init__(self, message: str, error_code: str | None = None):
        super().__init__(message)
        self.error_code = error_code


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

    except Exception as exc:
        logger.error("Erro ao determinar arquivos para processamento: %s", exc)
        raise CacheError(f"Falha na verificacao de arquivos: {exc}") from exc


def _import_single_file(
    file_path: str,
    db_path: str,
    table_name: str,
    should_cancel: Optional[Callable[[], bool]] = None,
    _metrics_out: Optional[Dict[str, Any]] = None,
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
    metrics: Dict[str, Any] = {"file": os.path.basename(file_path)}
    try:
        extraction_started = time.perf_counter()
        df = extractor.extract_data_from_excel(file_path, should_cancel=should_cancel)
        extraction_duration = time.perf_counter() - extraction_started
        if df is None:
            raise ExtractionError(f"Extractor retornou None para '{file_path}'")
        invalid_row_summary_raw = df.attrs.get("invalid_row_summary")
        invalid_row_summary = (
            dict(invalid_row_summary_raw)
            if isinstance(invalid_row_summary_raw, dict)
            else {}
        )
        row_count_before_invalid_filter_raw = df.attrs.get(
            "row_count_before_invalid_filter"
        )
        row_count_before_invalid_filter = (
            int(row_count_before_invalid_filter_raw)
            if isinstance(row_count_before_invalid_filter_raw, int)
            else int(len(df))
        )
        metrics["durations"] = {"extraction_seconds": round(extraction_duration, 3)}
        metrics["counts"] = {
            "rows_extracted": int(len(df)),
            "rows_before_invalid_filter": row_count_before_invalid_filter,
            "rows_removed_invalid_identity": int(
                invalid_row_summary.get("total_removed", 0)
            ),
            "rows_ready_for_insert": int(len(df)),
            "rows_inserted": 0,
        }
        metrics["invalid_identity"] = invalid_row_summary
        metrics["invalid_identity_tracked"] = bool(invalid_row_summary)
        if should_cancel and should_cancel():
            raise ExtractionError("operation cancelled", error_code="OPERATION_CANCELLED")
        if not df.empty:
            df = df.copy()
            if should_cancel and should_cancel():
                raise ExtractionError("operation cancelled", error_code="OPERATION_CANCELLED")
            # NOVA: Validar dados antes da insercao
            logger.info(f"Validando dados extraidos de '{file_path}'...")
            validation_started = time.perf_counter()
            validation_report = database.validate_dataframe_before_insert(
                df, table_name
            )

            validation_rule_labels = {
                "duplicate_numero_ssa_exact": "Duplicidade exata no export",
                "duplicate_numero_ssa_conflict": "Duplicidade conflitante no export",
            }
            for violation in validation_report.get("violations", []):
                rule = violation.get("rule")
                count = violation.get("count")
                severity = violation.get("severity", "warning")
                sample = violation.get("sample_ssa") or []
                sample_txt = f" (ex.: {', '.join(sample)})" if sample else ""
                rule_txt = str(rule or "regra_desconhecida").replace("_", " ")
                rule_label = validation_rule_labels.get(
                    rule,
                    f"Violacao de validacao [{rule_txt}]",
                )
                message = f"{rule_label} atingiu {count} linha(s){sample_txt}"
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
            metrics["durations"]["validation_seconds"] = round(
                time.perf_counter() - validation_started, 3
            )
            metrics["counts"]["rows_ready_for_insert"] = int(len(df))
            metrics["counts"]["rows_removed_required_validation"] = int(len(rows_to_drop))

            if df.empty:
                logger.error(
                    "Nenhuma linha valida restou apos validacao de '%s'; nada sera inserido.",
                    os.path.basename(file_path),
                )
                return False, 0

            # Se ha problemas criticos, pode escolher entre falhar ou continuar
            if not validation_report["is_valid"]:
                critical_issues = validation_report["issues"]
                critical_summary = "; ".join(str(issue) for issue in critical_issues[:5])
                logger.error(
                    "Validacao critica em '%s': %s",
                    os.path.basename(file_path),
                    critical_summary or "sem detalhe",
                )
                logger.warning(
                    "Validacao critica em '%s': seguindo com insercao por politica atual.",
                    os.path.basename(file_path),
                )
            else:
                logger.info(
                    "Validacao concluida para '%s': %s linhas prontas para insercao",
                    os.path.basename(file_path),
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
            insertion_started = time.perf_counter()

            # CORRECAO CRITICA: Usar smart_upsert para evitar duplicatas
            if should_cancel and should_cancel():
                raise ExtractionError("operation cancelled", error_code="OPERATION_CANCELLED")
            success = database.insert_dataframe_with_smart_upsert(
                df, db_path, table_name
            )
            metrics["durations"]["insert_seconds"] = round(
                time.perf_counter() - insertion_started, 3
            )
            metrics["counts"]["rows_inserted"] = int(record_count if success else 0)
            if success:
                logger.info(
                    "Resumo do arquivo '%s': extracao=%ss, validacao=%ss, insercao=%ss, linhas=%s, invalidos_sem_identidade=%s, prontas=%s",
                    os.path.basename(file_path),
                    metrics["durations"].get("extraction_seconds", 0),
                    metrics["durations"].get("validation_seconds", 0),
                    metrics["durations"].get("insert_seconds", 0),
                    metrics["counts"].get("rows_extracted", 0),
                    metrics["counts"].get("rows_removed_invalid_identity", 0),
                    metrics["counts"].get("rows_ready_for_insert", 0),
                )
                logger.info(
                    "Importacao finalizada para '%s': inseridas=%s, removidas_validacao=%s, invalidos_sem_identidade=%s",
                    os.path.basename(file_path),
                    record_count,
                    metrics["counts"].get("rows_removed_required_validation", 0),
                    metrics["counts"].get("rows_removed_invalid_identity", 0),
                )
                return True, record_count
            else:
                logger.error(
                    "Falha ao inserir dados validados de '%s' no banco de dados.",
                    os.path.basename(file_path),
                )
                raise DatabaseError(f"Erro ao inserir dados do arquivo {file_path}")
        else:
            logger.warning(
                "Arquivo '%s' sem linhas validas apos extracao; importacao ignorada.",
                os.path.basename(file_path),
            )
            return True, 0  # Nao e um erro critico, apenas nao ha dados
    except extractor.ExtractionError as e:
        # Normalize extractor error type into core.app_logic.ExtractionError
        message = str(e).strip() or "Erro de extracao sem detalhe"
        raise ExtractionError(
            message,
            error_code=getattr(e, "error_code", None),
        ) from e
    except ExtractionError:
        raise
    except DatabaseError:
        raise
    except ImporterError:
        raise
    except Exception as e:
        error_type = type(e).__name__
        logger.exception(
            "Erro inesperado (%s) ao importar '%s': %s",
            error_type,
            file_path,
            e,
        )
        raise ExtractionError(f"{error_type} ao importar {file_path}: {e}") from e
    finally:
        if _metrics_out is not None:
            _metrics_out.clear()
            _metrics_out.update(metrics)


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


def _needs_db_only_derivadas_sync(
    db_path: str,
    table_name: str,
    *,
    should_cancel: Optional[Callable[[], bool]] = None,
) -> bool:
    """Decide if derivadas sync should run with DB-only source when no files changed."""

    if should_cancel and should_cancel():
        logger.info("Cancelamento solicitado antes do preflight DB-only de derivadas.")
        return False

    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", str(table_name or "")):
        logger.warning("Nome de tabela invalido para preflight de derivadas: %r", table_name)
        return False

    try:
        with database.get_db_connection(db_path) as conn:
            if should_cancel and should_cancel():
                logger.info("Cancelamento solicitado durante preflight DB-only de derivadas.")
                return False
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

            if should_cancel and should_cancel():
                logger.info("Cancelamento solicitado durante preflight DB-only de derivadas.")
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

            if should_cancel and should_cancel():
                logger.info("Cancelamento solicitado durante preflight DB-only de derivadas.")
                return False

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
    def _has_sheet_parse_evidence(entry: Dict[str, Any]) -> bool:
        raw_stats = entry.get("stats")
        stats: Dict[str, Any] = raw_stats if isinstance(raw_stats, dict) else {}
        has_flag = bool(entry.get("has_parse_evidence"))
        accepted = int(stats.get("accepted_edges", 0) or 0)
        special_layout = int(stats.get("special_layout_detected", 0) or 0)
        informational = int(stats.get("informational_rows_skipped", 0) or 0)
        return has_flag or accepted > 0 or special_layout > 0 or informational > 0

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
    sheet_file_reports = report.get("sheet_file_reports") or []
    sheet_evidence = report.get("sheet_evidence") or {}
    accepted_edges = int(sheet_stats.get("accepted_edges", 0) or 0)
    special_layout_detected = int(sheet_stats.get("special_layout_detected", 0) or 0)
    has_sheet_evidence = accepted_edges > 0 or special_layout_detected > 0
    db_stats = report.get("db_stats") or {}
    db_edges = int(db_stats.get("accepted_edges", 0) or 0)
    merge_stats = report.get("merge_stats") or {}
    merged_edges = int(merge_stats.get("merged_edges", 0) or 0)
    has_graph_evidence = db_edges > 0 or merged_edges > 0

    expected_files_set = {os.path.abspath(path) for path in existing_files}
    reported_files_set = {os.path.abspath(str(path)) for path in reported_files}
    if existing_files and reported_files_set != expected_files_set:
        logger.error(
            "Sync de derivadas especiais sem cobertura completa de arquivos (esperado=%s, recebido=%s).",
            len(existing_files),
            len(reported_files),
        )
        return False, existing_files, report
    if existing_files and len(sheet_file_reports) != len(existing_files):
        logger.error(
            "Sync de derivadas especiais sem relatorio individual por arquivo (esperado=%s, recebido=%s).",
            len(existing_files),
            len(sheet_file_reports),
        )
        return False, existing_files, report

    files_without_evidence: list[str] = []
    if existing_files:
        reports_by_file: dict[str, Dict[str, Any]] = {}
        for entry in sheet_file_reports:
            if not isinstance(entry, dict):
                continue
            raw_sheet_file = str(entry.get("sheet_file") or "").strip()
            if not raw_sheet_file:
                continue
            reports_by_file[os.path.abspath(raw_sheet_file)] = entry
        for expected_file in existing_files:
            normalized = os.path.abspath(expected_file)
            current = reports_by_file.get(normalized)
            if current is None or not _has_sheet_parse_evidence(current):
                files_without_evidence.append(os.path.basename(expected_file))
    if files_without_evidence:
        logger.error(
            "Sync de derivadas especiais sem evidencia individual em %s arquivo(s): %s",
            len(files_without_evidence),
            ", ".join(sorted(files_without_evidence)),
        )
        report = dict(report)
        report["sheet_files_without_evidence"] = sorted(files_without_evidence)
        return False, existing_files, report
    if existing_files and not bool(sheet_evidence.get("is_complete", True)):
        report = dict(report)
        report["sheet_files_without_evidence"] = sorted(
            os.path.basename(str(path))
            for path in (sheet_evidence.get("files_without_evidence") or [])
            if str(path).strip()
        )
        missing_count = len(report["sheet_files_without_evidence"])
        logger.error(
            "Sync de derivadas especiais reportou evidencia incompleta no sumario agregado (%s arquivo(s)).",
            missing_count,
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
    except Exception as exc:
        logger.error("Erro ao atualizar o cache: %s", exc)
        raise CacheError("Falha ao atualizar o cache apos importacao.") from exc


def _update_cache_for_deterministic_failures(
    failed_files: List[str], cache_file: str
) -> None:
    """Atualiza cache para arquivos com falha deterministica para evitar retrabalho inutil."""
    if not failed_files:
        return
    deduped = list(dict.fromkeys([f for f in failed_files if isinstance(f, str) and f.strip()]))
    if not deduped:
        return
    try:
        caching.update_cache_for_files(deduped, cache_file)
        logger.info(
            "Cache atualizado para %s arquivo(s) com falha deterministica (aguardando mudanca de hash).",
            len(deduped),
        )
    except Exception as exc:
        logger.warning(
            "Falha ao atualizar cache para arquivos com erro deterministico: %s", exc
        )


def _recreate_database_for_full_rescan(db_path: str) -> None:
    """Create a clean DB for full rescan by rotating the previous file."""
    _rotate_database_for_full_rescan(db_path)


def _rotate_database_for_full_rescan(db_path: str) -> Optional[str]:
    """Rotate the current DB file to a timestamped backup and return the backup path."""
    if not os.path.exists(db_path):
        return None
    logger.info("Preparando full rescan: checkpoint WAL e rotacao de banco.")
    last_error: Optional[Exception] = None
    for attempt in range(1, 4):
        try:
            with sqlite3.connect(db_path, timeout=2) as conn:
                conn.execute("PRAGMA busy_timeout = 2000")
                conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
            last_error = None
            break
        except sqlite3.Error as exc:
            last_error = exc
            if "locked" in str(exc).lower() and attempt < 3:
                logger.warning(
                    "Banco bloqueado na preparacao do full rescan (tentativa %s/3).",
                    attempt,
                )
                time.sleep(0.35 * attempt)
                continue
            break
    if last_error is not None:
        raise DatabaseError(
            "Falha ao preparar full rescan por lock ativo no banco. "
            f"Feche acessos concorrentes e tente novamente: {last_error}"
        ) from last_error
    wal_path = f"{db_path}-wal"
    if os.path.exists(wal_path):
        try:
            wal_size = int(os.path.getsize(wal_path))
        except OSError as exc:
            raise DatabaseError(
                f"Falha ao validar estado do WAL antes do full rescan: {exc}"
            ) from exc
        if wal_size > 0:
            raise DatabaseError(
                "WAL ativo detectado antes da rotacao do banco. "
                "Feche acessos concorrentes e tente novamente."
            )
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = f"{db_path}.full_rescan_backup_{timestamp}"
    try:
        os.replace(db_path, backup_path)
        logger.info(
            "Banco anterior movido para backup de full rescan: %s",
            os.path.basename(backup_path),
        )
        for suffix in ("-wal", "-shm"):
            sidecar = f"{db_path}{suffix}"
            if not os.path.exists(sidecar):
                continue
            sidecar_backup = f"{backup_path}{suffix}"
            os.replace(sidecar, sidecar_backup)
            logger.info(
                "Arquivo auxiliar do banco movido para backup: %s",
                os.path.basename(sidecar_backup),
            )
    except OSError as exc:
        raise DatabaseError(
            f"Falha ao preparar banco limpo para full rescan: {exc}"
        ) from exc
    return backup_path


def _build_full_rescan_candidate_path(db_path: str, run_id: str) -> str:
    """Build an isolated DB path for a full-rescan candidate run."""
    return f"{db_path}.full_rescan_candidate_{run_id}"


def _cleanup_sqlite_sidecars(db_path: str) -> None:
    """Remove sqlite sidecars for a detached database file when they exist."""
    for suffix in ("-wal", "-shm"):
        sidecar = f"{db_path}{suffix}"
        if not os.path.exists(sidecar):
            continue
        os.remove(sidecar)
        logger.info("Arquivo auxiliar temporario removido: %s", os.path.basename(sidecar))


def _promote_full_rescan_candidate(primary_db_path: str, candidate_db_path: str) -> Optional[str]:
    """Promote a validated full-rescan candidate DB into the primary path."""
    if not os.path.exists(candidate_db_path):
        raise DatabaseError(f"DB candidato ausente para promocao final: {candidate_db_path}")

    logger.info(
        "Promovendo DB candidato de full rescan para principal: %s",
        os.path.basename(candidate_db_path),
    )
    last_error: Optional[Exception] = None
    for attempt in range(1, 4):
        try:
            with sqlite3.connect(candidate_db_path, timeout=2) as conn:
                conn.execute("PRAGMA busy_timeout = 2000")
                conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
            last_error = None
            break
        except sqlite3.Error as exc:
            last_error = exc
            if "locked" in str(exc).lower() and attempt < 3:
                logger.warning(
                    "DB candidato bloqueado na promocao final (tentativa %s/3).",
                    attempt,
                )
                time.sleep(0.35 * attempt)
                continue
            break
    if last_error is not None:
        raise DatabaseError(
            "Falha ao preparar DB candidato para promocao final. "
            f"Feche acessos concorrentes e tente novamente: {last_error}"
        ) from last_error

    candidate_wal_path = f"{candidate_db_path}-wal"
    if os.path.exists(candidate_wal_path):
        try:
            wal_size = int(os.path.getsize(candidate_wal_path))
        except OSError as exc:
            raise DatabaseError(
                f"Falha ao validar estado do WAL do DB candidato: {exc}"
            ) from exc
        if wal_size > 0:
            raise DatabaseError(
                "WAL ativo detectado no DB candidato antes da promocao final."
            )

    _cleanup_sqlite_sidecars(candidate_db_path)
    backup_path = _rotate_database_for_full_rescan(primary_db_path)
    try:
        os.replace(candidate_db_path, primary_db_path)
    except OSError as exc:
        raise DatabaseError(
            f"Falha ao promover DB candidato para o caminho principal: {exc}"
        ) from exc
    logger.info(
        "DB candidato promovido com sucesso para o caminho principal: %s",
        os.path.basename(primary_db_path),
    )
    return backup_path


def _write_import_run_report(payload: Dict[str, Any]) -> Optional[str]:
    """Grava resumo estruturado de uma execucao de importacao em JSON."""
    try:
        logs_dir = os.path.join(project_root, "logs")
        os.makedirs(logs_dir, exist_ok=True)
        run_id = str(payload.get("run_id") or datetime.now().strftime("%Y%m%d_%H%M%S_%f"))
        report_path = os.path.join(logs_dir, f"import_run_{run_id}.json")
        with open(report_path, "w", encoding="utf-8") as fp:
            json.dump(payload, fp, ensure_ascii=False, indent=2, default=str)
        return report_path
    except Exception as exc:
        logger.warning("Falha ao gravar relatorio JSON de importacao: %s", exc)
        return None


def _build_import_run_payload(
    *,
    run_id: str,
    run_started_at: datetime,
    finished_at: datetime,
    result: bool,
    status: str,
    reason: str,
    force_import: bool,
    table_name: str,
    db_name: str,
    docs_dir: str,
    data_dir: str,
    primary_db_path: str,
    working_db_path: str,
    candidate_db_path: Optional[str],
    promoted_backup_path: Optional[str],
    cache_file: str,
    total_files: int,
    successfully_processed_files: List[str],
    critical_errors: List[tuple[str, str, str]],
    deterministic_failed_files: List[str],
    derivadas_sheet_files: List[str],
    db_only_derivadas_sync: bool,
    derivadas_sync_blocking_error: bool,
    sync_materialized: bool,
    files_to_process: List[str],
    ignored_legacy_excel_files: List[str],
    integrity_report: Dict[str, Any],
    file_reports: List[Dict[str, Any]],
) -> Dict[str, Any]:
    total_rows_extracted = 0
    total_rows_removed_invalid_identity = 0
    total_rows_ready_for_insert = 0
    total_rows_inserted = 0
    for entry in file_reports:
        counts = entry.get("counts") or {}
        total_rows_extracted += int(counts.get("rows_extracted", 0) or 0)
        total_rows_removed_invalid_identity += int(
            counts.get("rows_removed_invalid_identity", 0) or 0
        )
        total_rows_ready_for_insert += int(
            counts.get("rows_ready_for_insert", 0) or 0
        )
        total_rows_inserted += int(counts.get("rows_inserted", 0) or 0)
    return {
        "run_id": run_id,
        "started_at": run_started_at.isoformat(timespec="seconds"),
        "finished_at": finished_at.isoformat(timespec="seconds"),
        "duration_seconds": round((finished_at - run_started_at).total_seconds(), 3),
        "result": bool(result),
        "status": status,
        "reason": reason,
        "inputs": {
            "force_import": bool(force_import),
            "table_name": table_name,
            "db_name": db_name,
        },
        "paths": {
            "docs_dir": docs_dir,
            "data_dir": data_dir,
            "db_path": primary_db_path,
            "primary_db_path": primary_db_path,
            "working_db_path": working_db_path,
            "candidate_db_path": candidate_db_path,
            "promoted_backup_path": promoted_backup_path,
            "candidate_preserved": bool(
                candidate_db_path
                and os.path.exists(candidate_db_path)
                and candidate_db_path != primary_db_path
            ),
            "cache_file": cache_file,
        },
        "counts": {
            "total_candidates": int(total_files),
            "success_count": len(successfully_processed_files),
            "error_count": len(critical_errors),
            "deterministic_failure_count": len(deterministic_failed_files),
            "derivadas_sheet_count": len(derivadas_sheet_files),
            "db_only_derivadas_sync": bool(db_only_derivadas_sync),
            "derivadas_sync_blocking_error": bool(derivadas_sync_blocking_error),
            "sync_materialized": bool(sync_materialized),
            "ignored_legacy_excel_count": len(ignored_legacy_excel_files),
            "rows_extracted_total": total_rows_extracted,
            "rows_removed_invalid_identity_total": total_rows_removed_invalid_identity,
            "rows_ready_for_insert_total": total_rows_ready_for_insert,
            "rows_inserted_total": total_rows_inserted,
        },
        "files": {
            "candidates": [os.path.basename(p) for p in files_to_process],
            "success": [os.path.basename(p) for p in successfully_processed_files],
            "deterministic_failed": [os.path.basename(p) for p in deterministic_failed_files],
            "derivadas_sheet_files": [os.path.basename(p) for p in derivadas_sheet_files],
            "ignored_legacy_excel": [os.path.basename(p) for p in ignored_legacy_excel_files],
        },
        "errors": [
            {
                "type": error_type,
                "file": os.path.basename(file_path),
                "message": message,
            }
            for error_type, file_path, message in critical_errors
        ],
        "integrity": {
            "is_valid": integrity_report.get("is_valid"),
            "issue_count": len(integrity_report.get("issues", [])),
            "warning_count": len(integrity_report.get("warnings", [])),
        },
        "file_reports": file_reports,
    }


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
    primary_db_path = db_path
    working_db_path = db_path
    cache_file = os.path.join(str(data_dir_path), "file_cache.json")
    docs_dir = str(docs_dir_path)
    data_dir = str(data_dir_path)
    run_started_at = datetime.now()
    run_id = run_started_at.strftime("%Y%m%d_%H%M%S_%f")
    files_to_process: List[str] = []
    derivadas_sheet_files: List[str] = []
    total_files = 0
    ignored_legacy_excel_files: List[str] = []
    successfully_processed_files: List[str] = []
    critical_errors: List[tuple[str, str, str]] = []
    deterministic_failed_files: List[str] = []
    integrity_report: Dict[str, Any] = {}
    candidate_db_path: Optional[str] = None
    promoted_backup_path: Optional[str] = None
    cancelled_full_rescan = False
    db_only_derivadas_sync = False
    sync_materialized = False
    derivadas_sync_blocking_error = False
    file_reports: List[Dict[str, Any]] = []

    def _finalize_and_return(result: bool, status: str, reason: str = "") -> bool:
        finished_at = datetime.now()
        payload = _build_import_run_payload(
            run_id=run_id,
            run_started_at=run_started_at,
            finished_at=finished_at,
            result=result,
            status=status,
            reason=reason,
            force_import=force_import,
            table_name=table_name,
            db_name=db_name,
            docs_dir=docs_dir,
            data_dir=data_dir,
            primary_db_path=primary_db_path,
            working_db_path=working_db_path,
            candidate_db_path=candidate_db_path,
            promoted_backup_path=promoted_backup_path,
            cache_file=cache_file,
            total_files=total_files,
            successfully_processed_files=successfully_processed_files,
            critical_errors=critical_errors,
            deterministic_failed_files=deterministic_failed_files,
            derivadas_sheet_files=derivadas_sheet_files,
            db_only_derivadas_sync=db_only_derivadas_sync,
            derivadas_sync_blocking_error=derivadas_sync_blocking_error,
            sync_materialized=sync_materialized,
            files_to_process=files_to_process,
            ignored_legacy_excel_files=ignored_legacy_excel_files,
            integrity_report=integrity_report,
            file_reports=file_reports,
        )
        report_path = _write_import_run_report(payload)
        if report_path:
            logger.info("Resumo JSON da importacao gravado em '%s'", report_path)
        return result

    try:
        # --- 0. Verificar e reparar integridade do banco de dados ---
        logger.info("Verificando integridade do banco de dados...")

        # Criar diretorio de dados se nao existir
        os.makedirs(data_dir, exist_ok=True)
        if force_import:
            candidate_db_path = _build_full_rescan_candidate_path(primary_db_path, run_id)
            working_db_path = candidate_db_path
            logger.info(
                "Full rescan configurado para DB candidato isolado: %s",
                os.path.basename(candidate_db_path),
            )

        # Verificar e reparar banco se necessario
        if not database.repair_database_if_needed(working_db_path, table_name=table_name):
            logger.error(
                "Falha critica: nao foi possivel garantir integridade do banco de dados"
            )
            raise DatabaseCorruptionError("Banco de dados inacessivel ou corrompido")

        # Verificacao adicional de integridade
        integrity_report = database.verify_database_integrity(working_db_path, table_name)
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
        ignored_legacy_excel_files = caching.get_ignored_legacy_excel_files(docs_dir)
        if ignored_legacy_excel_files:
            logger.warning(
                "Pipeline principal ignorou %s arquivo(s) .xls legado(s): %s",
                len(ignored_legacy_excel_files),
                ", ".join(os.path.basename(path) for path in ignored_legacy_excel_files[:5]),
            )
        files_to_process = _get_files_to_process(docs_dir, cache_file, force_import)
        derivadas_sheet_files = _discover_derivadas_sheet_files(docs_dir)
        db_only_derivadas_sync = False
        auto_derivadas_sync_enabled = bool(force_import)
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
            if should_cancel and should_cancel():
                logger.info("Cancelamento solicitado antes do preflight de derivadas.")
                _emit_progress("finish", {"total": 0, "processed": 0, "errors": []})
                return _finalize_and_return(
                    False,
                    "cancelled_preflight",
                    "cancelled_before_derivadas_preflight",
                )
            if auto_derivadas_sync_enabled:
                db_only_derivadas_sync = _needs_db_only_derivadas_sync(
                    db_path=working_db_path,
                    table_name=table_name,
                    should_cancel=should_cancel,
                )
            if not db_only_derivadas_sync:
                logger.info(
                    "Nenhum arquivo novo/modificado nem planilha especial de derivadas encontrada."
                )
                _emit_progress("finish", {"total": 0, "processed": 0, "errors": []})
                return _finalize_and_return(
                    False,
                    "no_changes",
                    "no_new_or_modified_files",
                )
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
        try:
            for index, file_path in enumerate(files_to_process):
                if should_cancel and should_cancel():
                    logger.info("Cancelamento solicitado; interrompendo importacao.")
                    if candidate_db_path is not None:
                        cancelled_full_rescan = True
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
                    file_metrics: Dict[str, Any] = {}
                    success, record_count = _import_single_file(
                        file_path,
                        working_db_path,
                        table_name,
                        should_cancel=should_cancel,
                        _metrics_out=file_metrics,
                    )
                    if file_metrics:
                        file_metrics["status"] = "success" if success else "no_rows"
                        file_reports.append(file_metrics)
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
                    file_reports.append({"file": base_name, "status": "connection_error", "error": str(e)})
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
                    file_reports.append({"file": base_name, "status": "corruption_error", "error": str(e)})
                    if database.repair_database_if_needed(
                        working_db_path, table_name=table_name
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
                    file_reports.append({"file": base_name, "status": "space_error", "error": str(e)})
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
                    file_reports.append({"file": base_name, "status": "schema_error", "error": str(e)})
                    if database.initialize_database(working_db_path):
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
                    file_reports.append({"file": base_name, "status": "validation_error", "error": str(e)})
                    _emit_progress(
                        "file_error", {"filename": base_name, "error": str(e)}
                    )
                    continue
                except ExtractionError as e:
                    error_code = getattr(e, "error_code", None)
                    if error_code == "OPERATION_CANCELLED" and should_cancel:
                        logger.info("Cancelamento solicitado; interrompendo importacao.")
                        if candidate_db_path is not None:
                            cancelled_full_rescan = True
                        break
                    if error_code == "MISSING_REQUIRED_COLUMNS":
                        deterministic_failed_files.append(file_path)
                    logger.warning(
                        f"Erro de extracao em '{file_path}': {e}. Pulando arquivo..."
                    )
                    critical_errors.append(("extraction", file_path, str(e)))
                    file_reports.append(
                        {
                            "file": base_name,
                            "status": "extraction_error",
                            "error": str(e),
                            "error_code": error_code,
                        }
                    )
                    _emit_progress(
                        "file_error", {"filename": base_name, "error": str(e)}
                    )
                    continue
                except DatabaseError as e:
                    logger.error(
                        f"Erro de banco ao processar '{file_path}': {e}. Continuando..."
                    )
                    critical_errors.append(("database_generic", file_path, str(e)))
                    file_reports.append({"file": base_name, "status": "database_error", "error": str(e)})
                    _emit_progress(
                        "file_error", {"filename": base_name, "error": str(e)}
                    )
                    continue
                except Exception as e:
                    logger.error(
                        f"Erro inesperado ao processar '{file_path}': {e}. Continuando..."
                    )
                    critical_errors.append(("unexpected", file_path, str(e)))
                    file_reports.append({"file": base_name, "status": "unexpected_error", "error": str(e)})
                    _emit_progress(
                        "file_error", {"filename": base_name, "error": str(e)}
                    )
                    continue
            sync_materialized = False
            derivadas_sync_blocking_error = False
            should_run_derivadas_sync = auto_derivadas_sync_enabled and (
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
                            db_path=working_db_path,
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
                            missing_files = sorted(sync_report.get("sheet_files_without_evidence") or [])
                            issue_text = json.dumps(issue_counts, ensure_ascii=True)
                            error_message = (
                                f"Sync de derivadas sem evidencia valida (consistency={issue_text})"
                                if issue_counts
                                else "Sync de derivadas sem evidencia valida"
                            )
                            if missing_files:
                                error_message += f" | files_without_evidence={','.join(missing_files)}"
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
            return _finalize_and_return(
                False,
                "derivadas_sync_error",
                "blocking_derivadas_sync_error",
            )

        if cancelled_full_rescan:
            logger.warning(
                "Full rescan cancelado apos inicio do processamento. "
                "DB principal foi preservado; DB candidato mantido para evidencia."
            )
            return _finalize_and_return(
                False,
                "cancelled_partial",
                "full_rescan_cancelled_before_final_promotion",
            )

        _update_cache_for_deterministic_failures(
            deterministic_failed_files, cache_file
        )

        # --- 3. Atualizar cache apenas se houve sucesso ---
        if successfully_processed_files:
            if candidate_db_path is not None:
                integrity_report = database.verify_database_integrity(
                    working_db_path,
                    table_name,
                )
                if not integrity_report.get("is_valid", False):
                    logger.error(
                        "DB candidato falhou na validacao final antes da promocao: %s",
                        integrity_report.get("issues", []),
                    )
                    critical_errors.append(
                        (
                            "candidate_validation",
                            candidate_db_path,
                            str(integrity_report.get("issues", [])),
                        )
                    )
                    return _finalize_and_return(
                        False,
                        "candidate_invalid",
                        "candidate_failed_final_integrity",
                    )
                try:
                    promoted_backup_path = _promote_full_rescan_candidate(
                        primary_db_path,
                        working_db_path,
                    )
                    working_db_path = primary_db_path
                except DatabaseError as exc:
                    logger.error("Falha ao promover DB candidato: %s", exc)
                    critical_errors.append(("promotion", candidate_db_path, str(exc)))
                    return _finalize_and_return(
                        False,
                        "candidate_promotion_failed",
                        str(exc),
                    )
            _update_cache_after_import(
                successfully_processed_files, cache_file, docs_dir
            )
            logger.info("=== Processo de importacao concluido com atualizacoes ===")
            return _finalize_and_return(
                True,
                "updated",
                "files_processed_or_cache_updated",
            )
        elif sync_materialized:
            if candidate_db_path is not None:
                integrity_report = database.verify_database_integrity(
                    working_db_path,
                    table_name,
                )
                if not integrity_report.get("is_valid", False):
                    logger.error(
                        "DB candidato falhou na validacao final antes da promocao: %s",
                        integrity_report.get("issues", []),
                    )
                    critical_errors.append(
                        (
                            "candidate_validation",
                            candidate_db_path,
                            str(integrity_report.get("issues", [])),
                        )
                    )
                    return _finalize_and_return(
                        False,
                        "candidate_invalid",
                        "candidate_failed_final_integrity",
                    )
                try:
                    promoted_backup_path = _promote_full_rescan_candidate(
                        primary_db_path,
                        working_db_path,
                    )
                    working_db_path = primary_db_path
                except DatabaseError as exc:
                    logger.error("Falha ao promover DB candidato: %s", exc)
                    critical_errors.append(("promotion", candidate_db_path, str(exc)))
                    return _finalize_and_return(
                        False,
                        "candidate_promotion_failed",
                        str(exc),
                    )
            logger.info("=== Processo de importacao concluiu sync de derivadas materializado (sem novos arquivos em cache) ===")
            return _finalize_and_return(
                True,
                "derivadas_materialized",
                "derivadas_sync_materialized_without_cache_update",
            )
        else:
            logger.info("Nenhum arquivo foi processado com sucesso.")
            return _finalize_and_return(
                False,
                "no_success",
                "no_file_processed_successfully",
            )

    except ImporterError:
        # Re-levanta excecoes personalizadas
        _finalize_and_return(False, "importer_error", "importer_exception_raised")
        raise
    except Exception as e:
        logger.critical(
            f"Erro inesperado no processo de importacao: {e}", exc_info=True
        )
        _finalize_and_return(False, "unexpected_exception", str(e))
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

    SIMPLIFIED RAW STRING CONTRACT:
    - Raw strings do not parse logical operators such as OU/OR/AND/E.
    - General search applies implicit AND between terms (all raw terms stay in group=0).
    - Each term may match any searched field; grouped OR is only preserved when the
      caller provides pre-parsed dict terms with explicit group metadata.

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

    Contrato atual:
    - termos brutos (str) seguem o parser simplificado atual: AND implicito entre termos
    - cada termo e satisfeito quando qualquer campo pesquisavel da linha corresponder
    - termos ja parseados (dict) ainda podem carregar grupos legados para OR entre grupos
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

    search_cache_key = "_filter_search_cache"
    search_cache_token = (id(getattr(df, "_mgr", None)), tuple(available_search_cols))
    cached_search_data = df.attrs.get(search_cache_key)

    if (
        isinstance(cached_search_data, dict)
        and cached_search_data.get("token") == search_cache_token
    ):
        base_lower_df = cached_search_data["base_lower_df"]
        row_search_text = cached_search_data["row_search_text"]
    else:
        base_str_df = (
            df[available_search_cols]
            .select_dtypes(include=["object", "string"])
            .fillna("")
            .astype(str)
        )
        if base_str_df.shape[1] == 0:
            # Sem colunas de texto, nao ha onde buscar: retorna DataFrame vazio
            return df.iloc[0:0]
        base_lower_df = base_str_df.apply(lambda col: col.str.casefold())
        row_search_text = base_lower_df.agg("\n".join, axis=1)
        df.attrs[search_cache_key] = {
            "token": search_cache_token,
            "base_lower_df": base_lower_df,
            "row_search_text": row_search_text,
        }

    if base_lower_df.shape[1] == 0:
        # Sem colunas de texto, nao ha onde buscar: retorna DataFrame vazio
        return df.iloc[0:0]

    logger.debug(
        "Buscando em %s colunas: %s",
        len(base_lower_df.columns),
        list(base_lower_df.columns),
    )

    # Permite tanto termos brutos (str) quanto parseados (dict)
    if search_terms and isinstance(search_terms[0], dict):
        terms = search_terms  # ja parseados
    else:
        terms = parse_search_terms(search_terms)

    if not terms:
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
            if regex:
                return row_search_text.str.contains(pattern, case=False, na=False, regex=True)

            lowered = str(pattern).casefold()
            return row_search_text.str.contains(lowered, regex=False, na=False)

        if mode == "regex":
            try:
                return _contains(pattern, regex=True)
            except re.error:
                return _contains(pattern, regex=False)

        lowered = str(value).casefold()
        if mode == "prefix":
            # Raw-term contract: one term matches when any searched field matches.
            return base_lower_df.apply(
                lambda col: col.str.startswith(lowered, na=False)
            ).any(axis=1)
        if mode == "suffix":
            return base_lower_df.apply(
                lambda col: col.str.endswith(lowered, na=False)
            ).any(axis=1)
        if mode == "exact":
            return base_lower_df.eq(lowered).any(axis=1)

        return _contains(pattern, regex=use_regex)

    grouped_terms: Dict[int, List[Dict[str, Any]]] = {}
    for term in terms:
        group_idx = term.get("group", 0)
        grouped_terms.setdefault(int(group_idx), []).append(term)

    final_mask = pd.Series(False, index=df.index)
    for group_terms in grouped_terms.values():
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
    return df.iloc[0:0]


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
        df = database.query_db(
            str(safe_db_path),
            CANONICAL_SSA_TABLE,
            raise_on_error=True,
        )

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
