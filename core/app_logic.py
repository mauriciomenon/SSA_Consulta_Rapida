# core/app_logic.py 20250725 103000 (v3.1 - Refatorado, Excecoes, Logging)
# Last modified: 2025-10-30T15:50:00 (simplified search: removed ALL logical operators, only commas)
"""
Logica central da aplicacao para importacao e atualizacao do banco de dados.

Coordena a verificacao de arquivos modificados, a extracao de dados,
a atualizacao do banco de dados SQLite e o gerenciamento do cache.
"""

# Module contract:
# - Orchestrates the main import pipeline and filter/search entry points.
# - Full rescan is schema-first and promotes a DB candidate only at the end.
# - Search/filter semantics are shared by CLI and GUI; do not change lightly.
# - Related modules: extracao.extractor, armazenamento.database,
#   armazenamento.database_validation, armazenamento.database_integrity.

import json
import logging
import os
import re
import shutil
import sqlite3
import sys
import time
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Sequence, cast

import pandas as pd

# Adiciona o diretorio raiz do projeto ao sys.path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
project_root_path = Path(project_root)
sys.path.insert(0, project_root)

from armazenamento import database  # noqa: E402
from armazenamento.derivadas_sync import (  # noqa: E402
    scan_derivadas_consistency,
    sync_derivadas,
)
from core.config_defaults import DEFAULT_COLUMN_MAPPINGS  # noqa: E402
from core.config_manager import load_settings  # noqa: E402
from core.import_errors import (  # noqa: E402
    CacheError,
    DataValidationError,
    DatabaseConnectionError,
    DatabaseCorruptionError,
    DatabaseError,
    DatabaseSchemaError,
    DatabaseSpaceError,
    ExtractionError,
    ImporterError,
)
from core.import_formats import (  # noqa: E402
    SUPPORTED_IMPORT_SUFFIXES,
    supported_import_suffixes_text,
)
from core.import_run_report import (  # noqa: E402
    _build_import_run_payload,
    _write_import_run_report,
)
from core.import_single_file import (  # noqa: E402
    ImportSingleFileServices,
    ensure_source_metadata_columns,
    import_single_file as _import_single_file_impl,
)
from core.search_filter import (  # noqa: E402
    FILTER_SEARCH_CACHE_ATTR,
    FILTER_SEARCH_MARKER_ATTR,
    filter_dataframe,
    parse_search_terms,
)
from extracao import extractor  # noqa: E402
from shared.db_names import CANONICAL_SSA_TABLE  # noqa: E402
from utils import caching  # noqa: E402
from utils.file_metadata import best_datetime_for_file  # noqa: E402
from utils.path_safety import PathSafetyError  # noqa: E402
from utils.path_safety import ensure_path_is_allowed  # noqa: E402

# Configura logger especifico para este modulo
logger = logging.getLogger(__name__)

QUERYABLE_FILTER_COLUMNS = frozenset(DEFAULT_COLUMN_MAPPINGS)
SQLITE_CHECKPOINT_BUSY_INDEX = 0
SQLITE_CHECKPOINT_LOG_INDEX = 1
SQLITE_CHECKPOINT_CHECKPOINTED_INDEX = 2
SQLITE_FILE_REPLACE_RETRY_DELAYS_SECONDS = (0.0, 0.1, 0.35, 0.75)
SQL_LIKE_ESCAPE_CHAR = "\\"

_DB_ONLY_DERIVADAS_EDGE_COUNT_QUERY_BY_TABLE: Dict[str, str] = {
    "ssa_table": """
        SELECT COUNT(*)
        FROM (
            SELECT numero_ssa, derivada_de
            FROM "ssa_table"
            WHERE derivada_de IS NOT NULL
            GROUP BY numero_ssa, derivada_de
        ) AS db_edges
    """,
}
_DB_ONLY_DERIVADAS_PREFLIGHT_CACHE: dict[
    tuple[str, str, tuple[tuple[str, int, int], ...]], bool
] = {}
_DB_ONLY_DERIVADAS_PREFLIGHT_CACHE_LIMIT = 128


class FileProcessAction(str, Enum):
    CONTINUE = "ok"
    BREAK = "break"
    CANCELLED = "cancelled"


def _sqlite_file_state_key(db_path: str) -> tuple[tuple[str, int, int], ...]:
    states: list[tuple[str, int, int]] = []
    for suffix in ("", "-wal", "-shm"):
        side_path = f"{db_path}{suffix}"
        try:
            stat = os.stat(side_path)
        except FileNotFoundError:
            states.append((suffix, -1, -1))
            continue
        states.append((suffix, int(stat.st_size), int(stat.st_mtime_ns)))
    return tuple(states)

__all__ = [
    "FILTER_SEARCH_CACHE_ATTR",
    "FILTER_SEARCH_MARKER_ATTR",
    "filter_dataframe",
    "parse_search_terms",
]


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


def _resolve_explicit_import_files(
    file_paths: Sequence[str | os.PathLike[str]],
    *,
    docs_dir_path: Path,
) -> List[str]:
    """Resolve explicit import files and ensure they stay under docs_dir."""
    docs_dir_resolved = docs_dir_path.resolve()
    resolved_files: List[tuple[str, datetime | None, str]] = []
    seen: set[str] = set()
    for raw_path in file_paths:
        if raw_path is None:
            continue
        candidate = ensure_path_is_allowed(
            raw_path,
            purpose="explicit_import_file",
            base=docs_dir_resolved,
            must_exist=True,
            expect_directory=False,
        )
        if candidate.suffix.casefold() not in SUPPORTED_IMPORT_SUFFIXES:
            raise PathSafetyError(
                "explicit_import_file: "
                f"'{candidate}' deve ser um arquivo {supported_import_suffixes_text()}."
            )
        try:
            candidate.relative_to(docs_dir_resolved)
        except ValueError as exc:
            raise PathSafetyError(
                f"explicit_import_file: '{candidate}' fora de docs_dir '{docs_dir_resolved}'."
            ) from exc
        normalized = str(candidate)
        if normalized in seen:
            continue
        seen.add(normalized)
        resolved_files.append(
            (normalized, best_datetime_for_file(normalized), candidate.name.casefold())
        )

    def _sort_key(
        item: tuple[str, datetime | None, str],
    ) -> tuple[bool, datetime, str, str]:
        path, file_dt, basename = item
        return (
            file_dt is None,
            file_dt or datetime.min,
            basename,
            path.casefold(),
        )

    # Keep explicit import deterministic and aligned with diff/full ordering:
    # older snapshots first, newest snapshot last.
    return [path for path, _file_dt, _basename in sorted(resolved_files, key=_sort_key)]


# --- Funcoes Auxiliares Refatoradas ---


def _get_files_to_process(
    docs_dir: str,
    cache_file: str,
    force_import: bool,
    *,
    include_processadas: bool = False,
    processadas_subdir: str = "processadas",
    ignore_subdirs: Optional[List[str]] = None,
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
            all_files = caching.get_all_xlsx_files(
                docs_dir,
                include_processadas=include_processadas,
                processadas_subdir=processadas_subdir,
                ignore_subdirs=ignore_subdirs,
            )
            return all_files

        # Verifica se o cache existe
        if not os.path.exists(cache_file):
            logger.info(
                "Arquivo de cache nao encontrado. Todos os arquivos serao processados."
            )
            all_files = caching.get_all_xlsx_files(
                docs_dir,
                include_processadas=include_processadas,
                processadas_subdir=processadas_subdir,
                ignore_subdirs=ignore_subdirs,
            )
            return all_files

        # Compara arquivos usando o cache
        files_to_process = caching.get_files_to_process(
            docs_dir,
            cache_file,
            include_processadas=include_processadas,
            processadas_subdir=processadas_subdir,
            ignore_subdirs=ignore_subdirs,
        )
        logger.debug(
            f"Arquivos identificados para processamento: {len(files_to_process)}"
        )
        return files_to_process

    except (OSError, RuntimeError, TimeoutError, ValueError, TypeError) as exc:
        logger.error("Erro ao determinar arquivos para processamento: %s", exc)
        raise CacheError(f"Falha na verificacao de arquivos: {exc}") from exc


def _import_single_file(
    file_path: str,
    db_path: str,
    table_name: str,
    should_cancel: Optional[Callable[[], bool]] = None,
    _metrics_out: Optional[Dict[str, Any]] = None,
    *,
    metadata_columns_ready: bool = False,
) -> tuple[bool, int]:
    return _import_single_file_impl(
        file_path,
        db_path,
        table_name,
        should_cancel=should_cancel,
        _metrics_out=_metrics_out,
        services=ImportSingleFileServices(
            extract_data_from_excel=extractor.extract_data_from_excel,
            extractor_error_type=extractor.ExtractionError,
            validate_dataframe_before_insert=database.validate_dataframe_before_insert,
            ensure_column_exists=database.ensure_column_exists,
            insert_dataframe_with_smart_upsert=database.insert_dataframe_with_smart_upsert,
        ),
        metadata_columns_ready=metadata_columns_ready,
    )



def _is_derivadas_sheet_file(file_path: str) -> bool:
    base_name = os.path.basename(file_path).strip().casefold()
    return base_name.startswith("ssas derivadas e relacionadas") and base_name.endswith(
        ".xlsx"
    )


def _discover_derivadas_sheet_files(
    docs_dir: str,
    *,
    include_processadas: bool = False,
    processadas_subdir: str = "processadas",
    ignore_subdirs: Optional[List[str]] = None,
) -> List[str]:
    try:
        all_xlsx_files = caching.get_all_xlsx_files(
            docs_dir,
            include_processadas=include_processadas,
            processadas_subdir=processadas_subdir,
            ignore_subdirs=ignore_subdirs,
        )
    except (OSError, RuntimeError, TimeoutError, ValueError, TypeError) as exc:
        logger.warning(
            "Falha ao listar planilhas especiais de derivadas em '%s': %s",
            docs_dir,
            exc,
        )
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

    if not isinstance(db_path, (str, os.PathLike)) or not str(db_path).strip():
        logger.warning(
            "Caminho de banco invalido para preflight de derivadas: %r", db_path
        )
        return False

    normalized_table_name = str(table_name or "").strip()

    if should_cancel and should_cancel():
        logger.info("Cancelamento solicitado antes do preflight DB-only de derivadas.")
        return False

    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", normalized_table_name):
        logger.warning(
            "Nome de tabela invalido para preflight de derivadas: %r", table_name
        )
        return False

    cache_key: tuple[str, str, tuple[tuple[str, int, int], ...]] | None = None
    try:
        resolved_db_path = str(Path(db_path).resolve())
        cache_key = (
            resolved_db_path,
            normalized_table_name,
            _sqlite_file_state_key(resolved_db_path),
        )
        cached_result = _DB_ONLY_DERIVADAS_PREFLIGHT_CACHE.get(cache_key)
        if cached_result is not None:
            return cached_result
    except OSError as exc:
        logger.debug("Cache de preflight DB-only de derivadas indisponivel: %s", exc)

    def _finish(result: bool) -> bool:
        if cache_key is not None:
            if (
                cache_key not in _DB_ONLY_DERIVADAS_PREFLIGHT_CACHE
                and len(_DB_ONLY_DERIVADAS_PREFLIGHT_CACHE)
                >= _DB_ONLY_DERIVADAS_PREFLIGHT_CACHE_LIMIT
            ):
                _DB_ONLY_DERIVADAS_PREFLIGHT_CACHE.clear()
            _DB_ONLY_DERIVADAS_PREFLIGHT_CACHE[cache_key] = result
        return result

    try:
        with database.get_db_connection(db_path) as conn:
            resolved_table_name = database.resolve_target_table(
                cast(sqlite3.Connection, conn),
                normalized_table_name,
            )
            if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", resolved_table_name):
                logger.warning(
                    "Tabela resolvida invalida para preflight DB-only de derivadas: %r",
                    resolved_table_name,
                )
                return _finish(False)
            if should_cancel and should_cancel():
                logger.info(
                    "Cancelamento solicitado durante preflight DB-only de derivadas."
                )
                return False
            db_edges_count = int(
                database.count_distinct_derivada_edges(
                    cast(sqlite3.Connection, conn),
                    normalized_table_name,
                )
            )
            if db_edges_count <= 0:
                return _finish(False)

            if should_cancel and should_cancel():
                logger.info(
                    "Cancelamento solicitado durante preflight DB-only de derivadas."
                )
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
                return _finish(True)

            if should_cancel and should_cancel():
                logger.info(
                    "Cancelamento solicitado durante preflight DB-only de derivadas."
                )
                return False

            matrix_active = int(
                conn.execute(
                    "SELECT COUNT(*) FROM ssa_derivada_matrix WHERE active = 1"
                ).fetchone()[0]
            )
            summary_total = int(
                conn.execute("SELECT COUNT(*) FROM ssa_derivada_summary").fetchone()[0]
            )
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
                return _finish(True)
            latest_db_edges = int(latest[0] or 0)
            return _finish(
                matrix_active <= 0
                or summary_total <= 0
                or latest_db_edges != db_edges_count
            )
    except sqlite3.Error as exc:
        logger.warning(
            "Preflight DB-only de derivadas falhou com sqlite error: %s", exc
        )
        return False
    except (OSError, RuntimeError, TimeoutError, TypeError, ValueError) as exc:
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
    if not isinstance(sheet_evidence, dict):
        sheet_evidence = {}
    accepted_edges = int(sheet_stats.get("accepted_edges", 0) or 0)
    special_layout_detected = int(sheet_stats.get("special_layout_detected", 0) or 0)
    has_sheet_evidence = accepted_edges > 0 or special_layout_detected > 0
    db_stats = report.get("db_stats") or {}
    db_edges = int(db_stats.get("accepted_edges", 0) or 0)
    merge_stats = report.get("merge_stats") or {}
    merged_edges = int(merge_stats.get("merged_edges", 0) or 0)
    has_graph_evidence = db_edges > 0 or merged_edges > 0

    expected_file_paths = {
        path: os.path.abspath(path)
        for path in existing_files
    }
    expected_files_set = set(expected_file_paths.values())
    reported_files_set = {
        os.path.abspath(str(path))
        for path in reported_files
    }
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
        for expected_file, normalized in expected_file_paths.items():
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
        logger.warning(
            "Sync de derivadas concluido sem arestas materializadas no grafo."
        )

    consistency = scan_derivadas_consistency(db_path=db_path)
    report = dict(report)
    report["consistency_scan"] = consistency
    if not bool(consistency.get("schema_ready")) or not bool(
        consistency.get("is_consistent")
    ):
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
        caching.update_cache_for_files(processed_files, cache_file, docs_dir=docs_dir)
        logger.info("Cache atualizado com sucesso.")
    except (OSError, RuntimeError, TimeoutError, ValueError, TypeError) as exc:
        logger.error("Erro ao atualizar o cache: %s", exc)
        raise CacheError("Falha ao atualizar o cache apos importacao.") from exc


def _update_cache_for_deterministic_failures(
    failed_files: List[str], cache_file: str, docs_dir: str
) -> None:
    """Atualiza cache para arquivos com falha deterministica para evitar retrabalho inutil."""
    if not failed_files:
        return
    deduped = list(
        dict.fromkeys([f for f in failed_files if isinstance(f, str) and f.strip()])
    )
    if not deduped:
        return
    try:
        caching.update_cache_for_files(deduped, cache_file, docs_dir=docs_dir)
        logger.info(
            "Cache atualizado para %s arquivo(s) com falha deterministica (aguardando mudanca de hash).",
            len(deduped),
        )
    except (OSError, RuntimeError, TimeoutError, ValueError, TypeError) as exc:
        logger.warning(
            "Falha ao atualizar cache para arquivos com erro deterministico: %s", exc
        )


def _has_only_deterministic_rejections(
    *,
    files_to_process: List[str],
    successfully_processed_files: List[str],
    deterministic_failed_files: List[str],
    critical_errors: List[tuple[str, str, str]],
) -> bool:
    """Return True when every regular candidate was rejected by deterministic rules."""
    if successfully_processed_files or not deterministic_failed_files:
        return False

    regular_candidates = [
        file_path
        for file_path in files_to_process
        if not os.path.basename(file_path).startswith("~$")
        and not _is_derivadas_sheet_file(file_path)
    ]
    if not regular_candidates:
        return False

    regular_candidate_set = set(regular_candidates)
    deterministic_failed_set = set(deterministic_failed_files)
    if deterministic_failed_set != regular_candidate_set:
        return False

    if not critical_errors:
        return False

    extraction_error_paths = {
        file_path
        for error_type, file_path, _message in critical_errors
        if error_type == "extraction"
    }
    if extraction_error_paths != regular_candidate_set:
        return False

    return len(extraction_error_paths) == len(critical_errors)


def _load_import_discovery_settings() -> Dict[str, Any]:
    """Load import discovery flags from settings.json with safe defaults."""
    allowed_upsert_policies = {"consulta_only", "no_short", "all_short"}
    defaults: Dict[str, Any] = {
        "include_processadas": True,
        "processadas_subdir": "processadas",
        "ignore_subdirs": ["nosurvivor"],
        "nosurvivor_subdir": "nosurvivor",
        "move_processed_after_import": False,
        "route_zero_survivor_to_nosurvivor": True,
        "upsert_short_circuit_policy": "consulta_only",
    }
    try:
        settings = load_settings()
        import_settings = settings.get("import_settings") or {}
        include_processadas = bool(
            import_settings.get("include_processadas_in_full_rescan", True)
        )
        processadas_subdir = (
            str(import_settings.get("processadas_subdir", "processadas")).strip()
            or "processadas"
        )
        ignore_nosurvivor = bool(
            import_settings.get("ignore_nosurvivor_in_full_rescan", True)
        )
        nosurvivor_subdir = (
            str(import_settings.get("nosurvivor_subdir", "nosurvivor")).strip()
            or "nosurvivor"
        )
        move_processed_after_import = bool(
            import_settings.get("move_processed_after_import", False)
        )
        route_zero_survivor_to_nosurvivor = bool(
            import_settings.get("route_zero_survivor_to_nosurvivor", True)
        )
        upsert_short_circuit_policy = (
            str(import_settings.get("upsert_short_circuit_policy", "consulta_only"))
            .strip()
            .lower()
            or "consulta_only"
        )
        if upsert_short_circuit_policy not in allowed_upsert_policies:
            logger.warning(
                "Politica de short-circuit invalida em import_settings: %s. Usando consulta_only.",
                upsert_short_circuit_policy,
            )
            upsert_short_circuit_policy = "consulta_only"
        ignore_subdirs = [nosurvivor_subdir] if ignore_nosurvivor else []
        return {
            "include_processadas": include_processadas,
            "processadas_subdir": processadas_subdir,
            "ignore_subdirs": ignore_subdirs,
            "nosurvivor_subdir": nosurvivor_subdir,
            "move_processed_after_import": move_processed_after_import,
            "route_zero_survivor_to_nosurvivor": route_zero_survivor_to_nosurvivor,
            "upsert_short_circuit_policy": upsert_short_circuit_policy,
        }
    except (AttributeError, KeyError, OSError, TypeError, ValueError) as exc:
        logger.warning(
            "Falha ao carregar import_settings; usando defaults de discovery: %s",
            exc,
        )
        return defaults


def _build_nonconflicting_destination(
    path: Path,
    *,
    existing_names: Optional[set[str]] = None,
) -> Path:
    """Return a non-conflicting destination path by suffixing __N when needed."""
    names = existing_names
    if names is None:
        names = {candidate.name for candidate in path.parent.iterdir()}
    if path.name not in names and not path.exists():
        return path
    stem = path.stem
    suffix = path.suffix
    for idx in range(1, 10000):
        candidate = path.with_name(f"{stem}__{idx}{suffix}")
        if candidate.name not in names:
            return candidate
    raise OSError(f"Nao foi possivel resolver destino unico para '{path}'")


def _move_file_after_import(
    *,
    file_path: str,
    docs_dir: str,
    processadas_subdir: str,
    nosurvivor_subdir: str,
    route_to_nosurvivor: bool,
    existing_destination_names: Optional[set[str]] = None,
) -> str:
    """Move processed file to processadas (or processadas/nosurvivor) and return final path."""
    source = Path(file_path).resolve()
    docs_root = Path(docs_dir).resolve()
    processadas_root = (docs_root / processadas_subdir).resolve()
    if not source.exists():
        logger.warning("Arquivo para pos-processamento nao encontrado: %s", file_path)
        return file_path
    try:
        source.relative_to(docs_root)
    except ValueError:
        logger.warning(
            "Arquivo fora de docs_dir nao sera movido no pos-processamento: %s",
            file_path,
        )
        return file_path
    if source.is_relative_to(processadas_root):
        return str(source)

    destination_root = processadas_root
    if route_to_nosurvivor:
        destination_root = processadas_root / nosurvivor_subdir
    destination_root.mkdir(parents=True, exist_ok=True)
    destination = _build_nonconflicting_destination(
        destination_root / source.name,
        existing_names=existing_destination_names,
    )
    if destination == source:
        return str(source)
    try:
        shutil.move(str(source), str(destination))
    except (OSError, RuntimeError, shutil.Error, ValueError) as exc:
        logger.warning(
            "Falha ao mover arquivo pos-importacao '%s' para '%s': %s",
            file_path,
            destination,
            exc,
        )
        return file_path
    try:
        src_rel = source.relative_to(docs_root).as_posix()
    except ValueError:
        src_rel = str(source)
    try:
        dst_rel = destination.relative_to(docs_root).as_posix()
    except ValueError:
        dst_rel = str(destination)
    logger.info(
        "Arquivo pos-importacao movido: %s -> %s",
        src_rel,
        dst_rel,
    )
    if existing_destination_names is not None:
        existing_destination_names.add(destination.name)
    return str(destination)


def _apply_postprocess_file_moves(
    *,
    successful_files_with_records: List[tuple[str, int]],
    docs_dir: str,
    processadas_subdir: str,
    nosurvivor_subdir: str,
    route_zero_survivor_to_nosurvivor: bool,
) -> Dict[str, str]:
    """Apply post-import moves and return old_path -> final_path mapping."""
    moved_paths: Dict[str, str] = {}
    destination_name_cache: dict[Path, set[str]] = {}
    for file_path, record_count in successful_files_with_records:
        try:
            normalized_record_count = int(record_count)
        except (TypeError, ValueError):
            logger.warning(
                "Contagem invalida para movimentacao pos-importacao de '%s': %r",
                os.path.basename(file_path),
                record_count,
            )
            normalized_record_count = 0
        route_to_nosurvivor = bool(
            route_zero_survivor_to_nosurvivor and normalized_record_count <= 0
        )
        docs_root = Path(docs_dir).resolve()
        destination_root = (docs_root / processadas_subdir).resolve()
        if route_to_nosurvivor:
            destination_root = (destination_root / nosurvivor_subdir).resolve()
        existing_names = destination_name_cache.setdefault(
            destination_root,
            {candidate.name for candidate in destination_root.iterdir()}
            if destination_root.exists()
            else set(),
        )
        final_path = _move_file_after_import(
            file_path=file_path,
            docs_dir=docs_dir,
            processadas_subdir=processadas_subdir,
            nosurvivor_subdir=nosurvivor_subdir,
            route_to_nosurvivor=route_to_nosurvivor,
            existing_destination_names=existing_names,
        )
        moved_paths[file_path] = final_path
    return moved_paths


def _rotate_preexisting_database_for_full_rescan(db_path: str) -> None:
    """Rotate the previous DB before a full rescan creates a clean candidate."""
    _rotate_database_for_full_rescan(db_path)


def _checkpoint_is_fully_truncated(checkpoint: Any) -> bool:
    if not checkpoint or len(checkpoint) < 3:
        return False
    busy = int(checkpoint[SQLITE_CHECKPOINT_BUSY_INDEX] or 0)
    log_frames = int(checkpoint[SQLITE_CHECKPOINT_LOG_INDEX] or 0)
    checkpointed_frames = int(checkpoint[SQLITE_CHECKPOINT_CHECKPOINTED_INDEX] or 0)
    return busy == 0 and log_frames == checkpointed_frames


def _force_wal_checkpoint(db_path: str, *, log_label: str) -> Optional[Exception]:
    last_error: Optional[Exception] = None
    for attempt in range(1, 4):
        conn: Optional[sqlite3.Connection] = None
        try:
            conn = sqlite3.connect(db_path, timeout=2)
            conn.execute("PRAGMA busy_timeout = 2000")
            checkpoint = conn.execute("PRAGMA wal_checkpoint(TRUNCATE)").fetchone()
            if not _checkpoint_is_fully_truncated(checkpoint):
                last_error = sqlite3.OperationalError(
                    f"WAL checkpoint incompleto: {checkpoint}"
                )
                if attempt < 3:
                    logger.warning(
                        "%s ocupado no checkpoint (tentativa %s/3).",
                        log_label,
                        attempt,
                    )
                    time.sleep(0.35 * attempt)
                    continue
            last_error = None
            break
        except sqlite3.Error as exc:
            last_error = exc
            if "locked" in str(exc).lower() and attempt < 3:
                logger.warning(
                    "%s bloqueado no checkpoint (tentativa %s/3).",
                    log_label,
                    attempt,
                )
                time.sleep(0.35 * attempt)
                continue
            break
        finally:
            if conn is not None:
                conn.close()
    return last_error


def _replace_sqlite_file_with_retry(source: str, target: str) -> None:
    last_error: OSError | None = None
    for delay in SQLITE_FILE_REPLACE_RETRY_DELAYS_SECONDS:
        if delay:
            time.sleep(delay)
        try:
            os.replace(source, target)
            return
        except OSError as exc:
            last_error = exc
    if last_error is not None:
        raise last_error


def _rotate_database_for_full_rescan(db_path: str) -> Optional[str]:
    """Rotate the current DB file to a timestamped backup and return the backup path."""
    if not os.path.exists(db_path):
        return None
    logger.info("Preparando full rescan: checkpoint WAL e rotacao de banco.")
    preexisting_sidecars = {
        suffix: os.path.exists(f"{db_path}{suffix}") for suffix in ("-wal", "-shm")
    }
    last_error = _force_wal_checkpoint(db_path, log_label="Banco de full rescan")
    if last_error is not None:
        logger.warning(
            "Checkpoint WAL do full rescan permaneceu ocupado; "
            "rotacao sera bloqueada se o WAL ainda tiver dados: %s",
            last_error,
        )
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
                "WAL ainda ativo apos checkpoint antes do full rescan; "
                "rotacao bloqueada para evitar backup inconsistente."
            )
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = f"{db_path}.full_rescan_backup_{timestamp}"
    try:
        _replace_sqlite_file_with_retry(db_path, backup_path)
        logger.info(
            "Banco anterior movido para backup de full rescan: %s",
            os.path.basename(backup_path),
        )
        for suffix in ("-wal", "-shm"):
            sidecar = f"{db_path}{suffix}"
            sidecar_backup = f"{backup_path}{suffix}"
            if os.path.exists(sidecar):
                _replace_sqlite_file_with_retry(sidecar, sidecar_backup)
                logger.info(
                    "Arquivo auxiliar do banco movido para backup: %s",
                    os.path.basename(sidecar_backup),
                )
                continue
            if preexisting_sidecars.get(suffix):
                Path(sidecar_backup).touch(exist_ok=True)
                logger.info(
                    "Arquivo auxiliar preexistente foi registrado vazio no backup "
                    "apos checkpoint consumir o sidecar: %s",
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
        logger.info(
            "Arquivo auxiliar temporario removido: %s", os.path.basename(sidecar)
        )


def _promote_full_rescan_candidate(
    candidate_db_path: str, primary_db_path: str
) -> Optional[str]:
    """Promote a validated full-rescan candidate DB into the primary path."""
    if not os.path.exists(candidate_db_path):
        raise DatabaseError(
            f"DB candidato ausente para promocao final: {candidate_db_path}"
        )

    logger.info(
        "Promovendo DB candidato de full rescan para principal: %s",
        os.path.basename(candidate_db_path),
    )
    last_error = _force_wal_checkpoint(
        candidate_db_path, log_label="DB candidato de full rescan"
    )
    if last_error is not None:
        logger.warning(
            "Checkpoint WAL do DB candidato permaneceu ocupado; "
            "promocao vai preservar sidecars se existirem: %s",
            last_error,
        )

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
                "WAL do DB candidato ainda ativo apos checkpoint; "
                "promocao bloqueada para evitar banco inconsistente."
            )

    _cleanup_sqlite_sidecars(candidate_db_path)
    backup_path = _rotate_database_for_full_rescan(primary_db_path)
    try:
        _replace_sqlite_file_with_retry(candidate_db_path, primary_db_path)
    except OSError as exc:
        try:
            shutil.move(candidate_db_path, primary_db_path)
        except (OSError, shutil.Error) as move_exc:
            raise DatabaseError(
                "Falha ao promover DB candidato para o caminho principal: "
                f"{move_exc}"
            ) from move_exc
        logger.warning(
            "Promocao de DB candidato usou shutil.move apos falha de os.replace: %s",
            exc,
        )
    logger.info(
        "DB candidato promovido com sucesso para o caminho principal: %s",
        os.path.basename(primary_db_path),
    )
    return backup_path


def _process_file_with_resilience(
    *,
    file_path: str,
    base_name: str,
    working_db_path: str,
    table_name: str,
    should_cancel: Optional[Callable[[], bool]],
    candidate_db_path: Optional[str],
    successfully_processed_files: List[str],
    successful_regular_files_with_records: List[tuple[str, int]],
    critical_errors: List[tuple[str, str, str]],
    deterministic_failed_files: List[str],
    file_reports: List[Dict[str, Any]],
    emit_progress: Callable[[str, Dict[str, Any]], None],
) -> FileProcessAction:
    """Processa um arquivo regular com tratamento de erros padrao.

    Retorna acao de controle do loop de importacao.
    """
    try:
        file_metrics: Dict[str, Any] = {}
        success, record_count = _import_single_file(
            file_path,
            working_db_path,
            table_name,
            should_cancel=should_cancel,
            _metrics_out=file_metrics,
            metadata_columns_ready=True,
        )
        if file_metrics:
            file_metrics["status"] = "success" if success else "no_rows"
            file_reports.append(file_metrics)
        if success:
            normalized_record_count = int(record_count)
            successfully_processed_files.append(file_path)
            successful_regular_files_with_records.append(
                (file_path, normalized_record_count)
            )
            emit_progress(
                "file_success",
                {"filename": base_name, "records": normalized_record_count},
            )
        return FileProcessAction.CONTINUE
    except DatabaseConnectionError as exc:
        logger.error(
            "Erro de conexao com banco ao processar '%s': %s",
            file_path,
            exc,
        )
        logger.error("Interrompendo processamento devido a falha de conexao")
        critical_errors.append(("connection", file_path, str(exc)))
        file_reports.append(
            {"file": base_name, "status": "connection_error", "error": str(exc)}
        )
        emit_progress("file_error", {"filename": base_name, "error": str(exc)})
        return FileProcessAction.BREAK
    except DatabaseCorruptionError as exc:
        logger.error("Corrupcao detectada ao processar '%s': %s", file_path, exc)
        logger.info("Tentando reparo automatico do banco...")
        emit_progress("file_error", {"filename": base_name, "error": str(exc)})
        file_reports.append(
            {"file": base_name, "status": "corruption_error", "error": str(exc)}
        )
        if database.repair_database_if_needed(working_db_path, table_name=table_name):
            logger.info("Reparo bem-sucedido, continuando processamento...")
            critical_errors.append(("corruption_repaired", file_path, str(exc)))
            return FileProcessAction.CONTINUE
        logger.error("Falha no reparo automatico")
        critical_errors.append(("corruption_failed", file_path, str(exc)))
        return FileProcessAction.BREAK
    except DatabaseSpaceError as exc:
        logger.error(
            "Espaco em disco insuficiente ao processar '%s': %s", file_path, exc
        )
        critical_errors.append(("space", file_path, str(exc)))
        file_reports.append(
            {"file": base_name, "status": "space_error", "error": str(exc)}
        )
        emit_progress("file_error", {"filename": base_name, "error": str(exc)})
        return FileProcessAction.BREAK
    except DatabaseSchemaError as exc:
        logger.error("Erro de schema ao processar '%s': %s", file_path, exc)
        logger.info("Tentando recriacao do schema...")
        emit_progress("file_error", {"filename": base_name, "error": str(exc)})
        file_reports.append(
            {"file": base_name, "status": "schema_error", "error": str(exc)}
        )
        if database.initialize_database(working_db_path):
            logger.info("Schema recriado, continuando processamento...")
            critical_errors.append(("schema_repaired", file_path, str(exc)))
            return FileProcessAction.CONTINUE
        logger.error("Falha na recriacao do schema")
        critical_errors.append(("schema_failed", file_path, str(exc)))
        return FileProcessAction.BREAK
    except DataValidationError as exc:
        logger.warning(
            "Dados invalidos em '%s': %s. Pulando arquivo...", file_path, exc
        )
        critical_errors.append(("validation", file_path, str(exc)))
        file_reports.append(
            {"file": base_name, "status": "validation_error", "error": str(exc)}
        )
        emit_progress("file_error", {"filename": base_name, "error": str(exc)})
        return FileProcessAction.CONTINUE
    except ExtractionError as exc:
        error_code = getattr(exc, "error_code", None)
        if error_code == "OPERATION_CANCELLED" and should_cancel:
            logger.info("Cancelamento solicitado; interrompendo importacao.")
            return FileProcessAction.CANCELLED
        if error_code == "MISSING_REQUIRED_COLUMNS":
            deterministic_failed_files.append(file_path)
        logger.warning(
            "Erro de extracao em '%s': %s. Pulando arquivo...", file_path, exc
        )
        critical_errors.append(("extraction", file_path, str(exc)))
        file_reports.append(
            {
                "file": base_name,
                "status": "extraction_error",
                "error": str(exc),
                "error_code": error_code,
            }
        )
        emit_progress("file_error", {"filename": base_name, "error": str(exc)})
        return FileProcessAction.CONTINUE
    except DatabaseError as exc:
        logger.error(
            "Erro de banco ao processar '%s': %s. Continuando...", file_path, exc
        )
        critical_errors.append(("database_generic", file_path, str(exc)))
        file_reports.append(
            {"file": base_name, "status": "database_error", "error": str(exc)}
        )
        emit_progress("file_error", {"filename": base_name, "error": str(exc)})
        return FileProcessAction.CONTINUE
    except (AttributeError, KeyError, TypeError, ValueError) as exc:
        logger.error(
            "Erro inesperado ao processar '%s': %s. Continuando...", file_path, exc
        )
        critical_errors.append(("unexpected", file_path, str(exc)))
        file_reports.append(
            {"file": base_name, "status": "unexpected_error", "error": str(exc)}
        )
        emit_progress("file_error", {"filename": base_name, "error": str(exc)})
        return FileProcessAction.CONTINUE


def _process_regular_files_phase(
    *,
    files_to_process: List[str],
    total_files: int,
    should_cancel: Optional[Callable[[], bool]],
    candidate_db_path: Optional[str],
    working_db_path: str,
    table_name: str,
    successfully_processed_files: List[str],
    successful_regular_files_with_records: List[tuple[str, int]],
    critical_errors: List[tuple[str, str, str]],
    deterministic_failed_files: List[str],
    file_reports: List[Dict[str, Any]],
    emit_progress: Callable[[str, Dict[str, Any]], None],
) -> bool:
    """Processa arquivos regulares e retorna flag de cancelamento parcial do full rescan."""
    cancelled_full_rescan = False
    has_regular_import_candidate = any(
        not os.path.basename(file_path).startswith("~$")
        and not _is_derivadas_sheet_file(file_path)
        for file_path in files_to_process
    )
    if has_regular_import_candidate:
        ensure_source_metadata_columns(
            working_db_path,
            table_name,
            database.ensure_column_exists,
        )
    for index, file_path in enumerate(files_to_process):
        action = _process_regular_file_step(
            file_path=file_path,
            index=index,
            total_files=total_files,
            working_db_path=working_db_path,
            table_name=table_name,
            should_cancel=should_cancel,
            candidate_db_path=candidate_db_path,
            successfully_processed_files=successfully_processed_files,
            successful_regular_files_with_records=successful_regular_files_with_records,
            critical_errors=critical_errors,
            deterministic_failed_files=deterministic_failed_files,
            file_reports=file_reports,
            emit_progress=emit_progress,
        )
        if action is FileProcessAction.CANCELLED:
            if candidate_db_path is not None:
                cancelled_full_rescan = True
            break
        if action is FileProcessAction.BREAK:
            break
    return cancelled_full_rescan


def _process_regular_file_step(
    *,
    file_path: str,
    index: int,
    total_files: int,
    working_db_path: str,
    table_name: str,
    should_cancel: Optional[Callable[[], bool]],
    candidate_db_path: Optional[str],
    successfully_processed_files: List[str],
    successful_regular_files_with_records: List[tuple[str, int]],
    critical_errors: List[tuple[str, str, str]],
    deterministic_failed_files: List[str],
    file_reports: List[Dict[str, Any]],
    emit_progress: Callable[[str, Dict[str, Any]], None],
) -> FileProcessAction:
    if should_cancel and should_cancel():
        logger.info("Cancelamento solicitado; interrompendo importacao.")
        return FileProcessAction.CANCELLED

    base_name = os.path.basename(file_path)
    emit_progress(
        "file_start",
        {
            "current": index + 1,
            "total": total_files,
            "filename": base_name,
        },
    )
    if base_name.startswith("~$"):
        logger.info("Ignorando arquivo temporario '%s'", base_name)
        return FileProcessAction.CONTINUE
    if _is_derivadas_sheet_file(file_path):
        logger.info(
            "Planilha especial de derivadas detectada: '%s' (fase dedicada separada).",
            base_name,
        )
        return FileProcessAction.CONTINUE
    return _process_file_with_resilience(
        file_path=file_path,
        base_name=base_name,
        working_db_path=working_db_path,
        table_name=table_name,
        should_cancel=should_cancel,
        candidate_db_path=candidate_db_path,
        successfully_processed_files=successfully_processed_files,
        successful_regular_files_with_records=successful_regular_files_with_records,
        critical_errors=critical_errors,
        deterministic_failed_files=deterministic_failed_files,
        file_reports=file_reports,
        emit_progress=emit_progress,
    )


def _run_optional_derivadas_sync(
    *,
    auto_derivadas_sync_enabled: bool,
    successfully_processed_files: List[str],
    derivadas_sheet_files: List[str],
    db_only_derivadas_sync: bool,
    should_cancel: Optional[Callable[[], bool]],
    working_db_path: str,
    table_name: str,
    docs_dir: str,
    critical_errors: List[tuple[str, str, str]],
    emit_progress: Callable[[str, Dict[str, Any]], None],
) -> tuple[bool, bool, list[str]]:
    """Executa sync opcional de derivadas e retorna resultado e arquivos especiais."""
    sync_materialized = False
    derivadas_sync_blocking_error = False
    synced_success_files: list[str] = []
    should_run_derivadas_sync = auto_derivadas_sync_enabled and (
        bool(successfully_processed_files)
        or bool(derivadas_sheet_files)
        or bool(db_only_derivadas_sync)
    )
    if not should_run_derivadas_sync:
        return sync_materialized, derivadas_sync_blocking_error, synced_success_files
    if should_cancel and should_cancel():
        logger.info(
            "Cancelamento solicitado; sync de derivadas especiais nao sera executado."
        )
        return sync_materialized, derivadas_sync_blocking_error, synced_success_files
    try:
        sync_ok, synced_sheets, sync_report = _run_derivadas_sync_phase(
            db_path=working_db_path,
            table_name=table_name,
            derivadas_sheet_files=derivadas_sheet_files,
        )
        if sync_ok and not derivadas_sync_blocking_error:
            existing_success = set(successfully_processed_files)
            synced_success_files = [
                special_file
                for special_file in synced_sheets
                if special_file not in existing_success
            ]
            db_edges = int(
                ((sync_report.get("db_stats") or {}).get("accepted_edges", 0) or 0)
            )
            merged_edges = int(
                ((sync_report.get("merge_stats") or {}).get("merged_edges", 0) or 0)
            )
            if db_edges > 0 or merged_edges > 0:
                sync_materialized = True
            if len(synced_sheets) == 1:
                progress_filename = os.path.basename(synced_sheets[0])
            elif synced_sheets:
                progress_filename = (
                    f"SSAs Derivadas e Relacionadas ({len(synced_sheets)} arquivos)"
                )
            else:
                progress_filename = "SSAs Derivadas e Relacionadas (banco atual)"
            emit_progress(
                "file_success",
                {
                    "filename": progress_filename,
                    "records": int(
                        (sync_report.get("merge_stats") or {}).get("merged_edges", 0)
                    ),
                },
            )
        if not sync_ok:
            derivadas_sync_blocking_error = True
            consistency_scan = sync_report.get("consistency_scan") or {}
            issue_counts = consistency_scan.get("issue_counts") or {}
            missing_files = sorted(
                sync_report.get("sheet_files_without_evidence") or []
            )
            issue_text = json.dumps(issue_counts, ensure_ascii=True)
            error_message = (
                f"Sync de derivadas sem evidencia valida (consistency={issue_text})"
                if issue_counts
                else "Sync de derivadas sem evidencia valida"
            )
            if missing_files:
                error_message += f" | files_without_evidence={','.join(missing_files)}"
            critical_errors.append(("derivadas_sync", docs_dir, error_message))
            emit_progress(
                "file_error",
                {
                    "filename": "SSAs Derivadas e Relacionadas",
                    "error": error_message,
                },
            )
    except (
        OSError,
        RuntimeError,
        TimeoutError,
        TypeError,
        ValueError,
        sqlite3.Error,
    ) as exc:
        derivadas_sync_blocking_error = True
        logger.error(
            "Falha ao sincronizar derivadas a partir de planilhas especiais: %s",
            exc,
            exc_info=True,
        )
        critical_errors.append(("derivadas_sync", docs_dir, str(exc)))
        emit_progress(
            "file_error",
            {"filename": "SSAs Derivadas e Relacionadas", "error": str(exc)},
        )
    return sync_materialized, derivadas_sync_blocking_error, synced_success_files


def _validate_and_promote_candidate_if_needed(
    *,
    candidate_db_path: Optional[str],
    working_db_path: str,
    primary_db_path: str,
    table_name: str,
) -> Dict[str, Any]:
    """Valida e promove DB candidato quando full rescan usa caminho isolado."""
    result: Dict[str, Any] = {
        "ok": True,
        "integrity_report": {},
        "promoted_backup_path": None,
        "working_db_path": working_db_path,
        "failure_type": "",
        "failure_message": "",
    }
    if candidate_db_path is None:
        return result
    integrity_report = database.verify_database_integrity(working_db_path, table_name)
    result["integrity_report"] = integrity_report
    if not integrity_report.get("is_valid", False):
        logger.error(
            "DB candidato falhou na validacao final antes da promocao: %s",
            integrity_report.get("issues", []),
        )
        result["ok"] = False
        result["failure_type"] = "candidate_validation"
        result["failure_message"] = str(integrity_report.get("issues", []))
        return result
    try:
        promoted_backup_path = _promote_full_rescan_candidate(
            working_db_path,
            primary_db_path,
        )
    except DatabaseError as exc:
        logger.error("Falha ao promover DB candidato: %s", exc)
        result["ok"] = False
        result["failure_type"] = "promotion"
        result["failure_message"] = str(exc)
        return result
    result["promoted_backup_path"] = promoted_backup_path
    result["working_db_path"] = primary_db_path
    return result


def _prepare_working_database_for_import(
    *,
    data_dir: str,
    primary_db_path: str,
    run_id: str,
    force_import: bool,
    table_name: str,
) -> tuple[str, Optional[str], Dict[str, Any]]:
    """Prepara o DB de trabalho e valida integridade antes da importacao."""
    working_db_path = primary_db_path
    candidate_db_path: Optional[str] = None

    logger.info("Verificando integridade do banco de dados...")
    os.makedirs(data_dir, exist_ok=True)
    if force_import:
        candidate_db_path = _build_full_rescan_candidate_path(primary_db_path, run_id)
        working_db_path = candidate_db_path
        logger.info(
            "Full rescan configurado para DB candidato isolado: %s",
            os.path.basename(candidate_db_path),
        )
        if not os.path.exists(working_db_path):
            if not database.initialize_database(working_db_path):
                raise DatabaseSchemaError(
                    f"Falha ao inicializar DB candidato de full rescan: {working_db_path}"
                )

    if not database.repair_database_if_needed(working_db_path, table_name=table_name):
        logger.error(
            "Falha critica: nao foi possivel garantir integridade do banco de dados"
        )
        raise DatabaseCorruptionError("Banco de dados inacessivel ou corrompido")

    integrity_report = database.verify_database_integrity(working_db_path, table_name)
    if not integrity_report["is_valid"]:
        issues = integrity_report["issues"]
        if not integrity_report["database_accessible"]:
            raise DatabaseConnectionError(f"Banco de dados inacessivel: {issues}")
        if not integrity_report["table_exists"] or not integrity_report["schema_valid"]:
            raise DatabaseSchemaError(f"Problemas de schema: {issues}")
        if not integrity_report["data_consistent"]:
            raise DatabaseCorruptionError(f"Dados corrompidos: {issues}")
        if not integrity_report["disk_space_sufficient"]:
            raise DatabaseSpaceError(f"Espaco em disco insuficiente: {issues}")
        raise DatabaseError(f"Problemas gerais no banco: {issues}")

    if integrity_report["warnings"]:
        for warning in integrity_report["warnings"]:
            logger.warning(f"Aviso do banco: {warning}")

    logger.info(" Integridade do banco de dados verificada")
    return working_db_path, candidate_db_path, integrity_report


def _resolve_import_work_items(
    *,
    docs_dir: str,
    docs_dir_path: Path,
    cache_file: str,
    force_import: bool,
    explicit_files: Optional[Sequence[str | os.PathLike[str]]],
) -> Dict[str, Any]:
    """Resolve arquivos de trabalho e politicas de discovery para a rodada."""
    ignored_legacy_excel_files = caching.get_ignored_legacy_excel_files(docs_dir)
    if ignored_legacy_excel_files:
        logger.warning(
            "Pipeline principal ignorou %s arquivo(s) .xls legado(s): %s",
            len(ignored_legacy_excel_files),
            ", ".join(os.path.basename(path) for path in ignored_legacy_excel_files[:5]),
        )

    discovery_settings = _load_import_discovery_settings()
    upsert_policy = str(
        discovery_settings.get("upsert_short_circuit_policy", "consulta_only")
    )
    database.configure_upsert_short_circuit_policy(upsert_policy)

    include_processadas = bool(discovery_settings.get("include_processadas", False))
    ignore_subdirs = list(discovery_settings.get("ignore_subdirs", []))
    move_processed_after_import = bool(
        discovery_settings.get("move_processed_after_import", False)
    )
    if force_import:
        nosurvivor_subdir = str(discovery_settings.get("nosurvivor_subdir", "nosurvivor"))
        if nosurvivor_subdir not in ignore_subdirs:
            logger.warning(
                "Politica ativa: ignore_nosurvivor_in_full_rescan foi forcado no full rescan."
            )
            ignore_subdirs = [nosurvivor_subdir, *ignore_subdirs]
        if move_processed_after_import:
            logger.warning(
                "Politica ativa: move_processed_after_import foi desativado em full rescan."
            )
            move_processed_after_import = False

    if explicit_files is not None:
        files_to_process = _resolve_explicit_import_files(
            explicit_files,
            docs_dir_path=docs_dir_path,
        )
        logger.info(
            "Modo de importacao explicita ativado com %s arquivo(s).",
            len(files_to_process),
        )
        derivadas_sheet_files = [
            file_path for file_path in files_to_process if _is_derivadas_sheet_file(file_path)
        ]
    else:
        files_to_process = _get_files_to_process(
            docs_dir,
            cache_file,
            force_import,
            include_processadas=include_processadas,
            processadas_subdir=str(discovery_settings["processadas_subdir"]),
            ignore_subdirs=ignore_subdirs,
        )
        derivadas_sheet_files = _discover_derivadas_sheet_files(
            docs_dir,
            include_processadas=include_processadas,
            processadas_subdir=str(discovery_settings["processadas_subdir"]),
            ignore_subdirs=ignore_subdirs,
        )

    return {
        "ignored_legacy_excel_files": ignored_legacy_excel_files,
        "discovery_settings": discovery_settings,
        "files_to_process": files_to_process,
        "derivadas_sheet_files": derivadas_sheet_files,
        "move_processed_after_import": move_processed_after_import,
    }


def _finalize_import_run_outcome(
    *,
    successfully_processed_files: List[str],
    successful_regular_files_with_records: List[tuple[str, int]],
    deterministic_failed_files: List[str],
    critical_errors: List[tuple[str, str, str]],
    files_to_process: List[str],
    sync_materialized: bool,
    candidate_db_path: Optional[str],
    working_db_path: str,
    primary_db_path: str,
    table_name: str,
    docs_dir: str,
    cache_file: str,
    move_processed_after_import: bool,
    discovery_settings: Dict[str, Any],
    phase_durations: Dict[str, float],
) -> Dict[str, Any]:
    """Fecha promocao/cache e devolve a decisao final da rodada."""
    deterministic_cache_started = time.perf_counter()
    _update_cache_for_deterministic_failures(
        deterministic_failed_files,
        cache_file,
        docs_dir,
    )
    phase_durations["run_deterministic_cache_update_seconds"] = (
        time.perf_counter() - deterministic_cache_started
    )

    rejection_only = _has_only_deterministic_rejections(
        files_to_process=files_to_process,
        successfully_processed_files=successfully_processed_files,
        deterministic_failed_files=deterministic_failed_files,
        critical_errors=critical_errors,
    )
    if rejection_only:
        logger.info(
            "Todos os arquivos candidatos foram rejeitados por regra deterministica; "
            "nenhum arquivo elegivel foi importado nesta execucao."
        )
        return {
            "result": True,
            "status": "deterministic_rejections_only",
            "reason": "all_candidates_rejected_by_deterministic_rules",
            "integrity_report": {},
            "promoted_backup_path": None,
            "working_db_path": working_db_path,
        }

    if successfully_processed_files:
        cache_success_paths = list(successfully_processed_files)
        promotion_result = _validate_and_promote_candidate_if_needed(
            candidate_db_path=candidate_db_path,
            working_db_path=working_db_path,
            primary_db_path=primary_db_path,
            table_name=table_name,
        )
        if not bool(promotion_result.get("ok", False)):
            failure_type = str(promotion_result.get("failure_type", "") or "promotion")
            failure_message = str(
                promotion_result.get("failure_message", "") or "promotion_failed"
            )
            critical_errors.append(
                (failure_type, candidate_db_path or working_db_path, failure_message)
            )
            status = (
                "candidate_invalid"
                if failure_type == "candidate_validation"
                else "candidate_promotion_failed"
            )
            reason = (
                "candidate_failed_final_integrity"
                if failure_type == "candidate_validation"
                else failure_message
            )
            return {
                "result": False,
                "status": status,
                "reason": reason,
                "integrity_report": {},
                "promoted_backup_path": None,
                "working_db_path": working_db_path,
            }

        next_integrity_report = promotion_result.get("integrity_report")
        promoted_backup_path = cast(
            Optional[str],
            promotion_result.get("promoted_backup_path"),
        )
        next_working_db_path = str(
            promotion_result.get("working_db_path", working_db_path)
        )
        if move_processed_after_import and successful_regular_files_with_records:
            move_started = time.perf_counter()
            moved_paths = _apply_postprocess_file_moves(
                successful_files_with_records=successful_regular_files_with_records,
                docs_dir=docs_dir,
                processadas_subdir=str(discovery_settings["processadas_subdir"]),
                nosurvivor_subdir=str(discovery_settings["nosurvivor_subdir"]),
                route_zero_survivor_to_nosurvivor=bool(
                    discovery_settings["route_zero_survivor_to_nosurvivor"]
                ),
            )
            phase_durations["run_postprocess_move_seconds"] = (
                time.perf_counter() - move_started
            )
            cache_success_paths = [moved_paths.get(path, path) for path in cache_success_paths]

        cache_update_started = time.perf_counter()
        _update_cache_after_import(cache_success_paths, cache_file, docs_dir)
        phase_durations["run_success_cache_update_seconds"] = (
            time.perf_counter() - cache_update_started
        )
        logger.info("=== Processo de importacao concluido com atualizacoes ===")
        return {
            "result": True,
            "status": "updated",
            "reason": "files_processed_or_cache_updated",
            "integrity_report": (
                next_integrity_report
                if isinstance(next_integrity_report, dict) and next_integrity_report
                else {}
            ),
            "promoted_backup_path": promoted_backup_path,
            "working_db_path": next_working_db_path,
        }

    if sync_materialized:
        promotion_result = _validate_and_promote_candidate_if_needed(
            candidate_db_path=candidate_db_path,
            working_db_path=working_db_path,
            primary_db_path=primary_db_path,
            table_name=table_name,
        )
        if not bool(promotion_result.get("ok", False)):
            failure_type = str(promotion_result.get("failure_type", "") or "promotion")
            failure_message = str(
                promotion_result.get("failure_message", "") or "promotion_failed"
            )
            critical_errors.append(
                (failure_type, candidate_db_path or working_db_path, failure_message)
            )
            status = (
                "candidate_invalid"
                if failure_type == "candidate_validation"
                else "candidate_promotion_failed"
            )
            reason = (
                "candidate_failed_final_integrity"
                if failure_type == "candidate_validation"
                else failure_message
            )
            return {
                "result": False,
                "status": status,
                "reason": reason,
                "integrity_report": {},
                "promoted_backup_path": None,
                "working_db_path": working_db_path,
            }

        next_integrity_report = promotion_result.get("integrity_report")
        promoted_backup_path = cast(
            Optional[str],
            promotion_result.get("promoted_backup_path"),
        )
        next_working_db_path = str(
            promotion_result.get("working_db_path", working_db_path)
        )
        logger.info(
            "=== Processo de importacao concluiu sync de derivadas materializado (sem novos arquivos em cache) ==="
        )
        return {
            "result": True,
            "status": "derivadas_materialized",
            "reason": "derivadas_sync_materialized_without_cache_update",
            "integrity_report": (
                next_integrity_report
                if isinstance(next_integrity_report, dict) and next_integrity_report
                else {}
            ),
            "promoted_backup_path": promoted_backup_path,
            "working_db_path": next_working_db_path,
        }

    logger.info("Nenhum arquivo foi processado com sucesso.")
    return {
        "result": False,
        "status": "no_success",
        "reason": "no_file_processed_successfully",
        "integrity_report": {},
        "promoted_backup_path": None,
        "working_db_path": working_db_path,
    }


def _initialize_import_run_context(
    *,
    docs_dir: str,
    data_dir: str,
    db_name: str,
    extra_allowed_roots: Optional[Sequence[str | os.PathLike[str]]] = None,
) -> Dict[str, Any]:
    """Resolve caminhos e inicializa o estado mutavel da rodada de importacao."""
    try:
        docs_dir_path = ensure_path_is_allowed(
            docs_dir,
            purpose="docs_dir",
            base=project_root_path,
            must_exist=True,
            expect_directory=True,
            extra_allowed_roots=extra_allowed_roots,
        )
        data_dir_path = ensure_path_is_allowed(
            data_dir,
            purpose="data_dir",
            base=project_root_path,
            must_exist=False,
            expect_directory=True,
            extra_allowed_roots=extra_allowed_roots,
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
            extra_allowed_roots=extra_allowed_roots,
        )
    except PathSafetyError as e:
        logger.error(f"Caminho de DB bloqueado: {e}")
        raise

    run_started_at = datetime.now()
    return {
        "docs_dir_path": docs_dir_path,
        "data_dir_path": data_dir_path,
        "db_path": str(db_path_obj),
        "cache_file": os.path.join(str(data_dir_path), "file_cache.json"),
        "docs_dir": str(docs_dir_path),
        "data_dir": str(data_dir_path),
        "run_started_at": run_started_at,
        "run_id": run_started_at.strftime("%Y%m%d_%H%M%S_%f"),
        "files_to_process": [],
        "derivadas_sheet_files": [],
        "total_files": 0,
        "ignored_legacy_excel_files": [],
        "successfully_processed_files": [],
        "successful_regular_files_with_records": [],
        "critical_errors": [],
        "deterministic_failed_files": [],
        "integrity_report": {},
        "candidate_db_path": None,
        "promoted_backup_path": None,
        "cancelled_full_rescan": False,
        "db_only_derivadas_sync": False,
        "sync_materialized": False,
        "derivadas_sync_blocking_error": False,
        "file_reports": [],
        "phase_durations": {
            "run_file_processing_seconds": 0.0,
            "run_postprocess_move_seconds": 0.0,
            "run_success_cache_update_seconds": 0.0,
            "run_deterministic_cache_update_seconds": 0.0,
        },
    }


def _handle_derivadas_preflight_without_regular_files(
    *,
    files_to_process: List[str],
    derivadas_sheet_files: List[str],
    auto_derivadas_sync_enabled: bool,
    working_db_path: str,
    table_name: str,
    should_cancel: Optional[Callable[[], bool]],
    emit_progress: Callable[[str, Dict[str, Any]], None],
) -> Dict[str, Any]:
    """Decide cancelamento, no-op ou sync DB-only quando nao ha arquivos regulares."""
    if files_to_process or derivadas_sheet_files:
        return {"should_return": False, "db_only_derivadas_sync": False}

    if should_cancel and should_cancel():
        logger.info("Cancelamento solicitado antes do preflight de derivadas.")
        emit_progress(
            "finish",
            {
                "total": 0,
                "processed": 0,
                "errors": [],
                "deterministic_failure_count": 0,
                "rejection_only": False,
            },
        )
        return {
            "should_return": True,
            "result": False,
            "status": "cancelled_preflight",
            "reason": "cancelled_before_derivadas_preflight",
            "db_only_derivadas_sync": False,
        }

    db_only_derivadas_sync = False
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
        emit_progress(
            "finish",
            {
                "total": 0,
                "processed": 0,
                "errors": [],
                "deterministic_failure_count": 0,
                "rejection_only": False,
            },
        )
        return {
            "should_return": True,
            "result": False,
            "status": "no_changes",
            "reason": "no_new_or_modified_files",
            "db_only_derivadas_sync": False,
        }

    logger.info(
        "Nenhum arquivo novo detectado; executando sync DB-only de derivadas por preflight."
    )
    return {
        "should_return": False,
        "db_only_derivadas_sync": db_only_derivadas_sync,
    }


def _build_progress_emitter(
    progress_callback: Optional[Callable[[str, Dict[str, Any]], None]],
) -> Callable[[str, Dict[str, Any]], None]:
    """Envolve o callback de progresso sem transformar falha de UI em falha core."""

    def _emit_progress(event_type: str, data: Dict[str, Any]) -> None:
        if not progress_callback:
            return
        try:
            progress_callback(event_type, data)
        except Exception as exc:
            logger.warning(
                "Progress callback failed for event '%s': %s.",
                event_type,
                exc,
                exc_info=True,
            )

    return _emit_progress


# --- Funcao Principal Refatorada ---


def run_importer_logic(
    docs_dir: str = "docs_entrada",
    data_dir: str = "data",
    db_name: str = "ssas.db",
    table_name: str = "ssa_table",
    force_import: bool = False,
    should_cancel: Optional[Callable[[], bool]] = None,
    progress_callback: Optional[Callable[[str, Dict[str, Any]], None]] = None,
    explicit_files: Optional[Sequence[str | os.PathLike[str]]] = None,
    extra_allowed_roots: Optional[Sequence[str | os.PathLike[str]]] = None,
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
        explicit_files (Optional[Sequence[str | os.PathLike[str]]]): Se informado,
            processa apenas esses arquivos .xlsx ja presentes em docs_dir.
        extra_allowed_roots: Bases adicionais explicitas para data_dir/db_path.

    Returns:
        bool: True se o banco de dados foi atualizado, False caso contrario.
    """
    logger.info("=== Iniciando processo de importacao ===")

    context = _initialize_import_run_context(
        docs_dir=docs_dir,
        data_dir=data_dir,
        db_name=db_name,
        extra_allowed_roots=extra_allowed_roots,
    )
    docs_dir_path = cast(Path, context["docs_dir_path"])
    db_path = str(context["db_path"])
    primary_db_path = db_path
    working_db_path = db_path
    cache_file = str(context["cache_file"])
    docs_dir = str(context["docs_dir"])
    data_dir = str(context["data_dir"])
    run_started_at = cast(datetime, context["run_started_at"])
    run_id = str(context["run_id"])
    files_to_process: List[str] = cast(List[str], context["files_to_process"])
    derivadas_sheet_files: List[str] = cast(List[str], context["derivadas_sheet_files"])
    total_files = int(context["total_files"])
    ignored_legacy_excel_files: List[str] = cast(List[str], context["ignored_legacy_excel_files"])
    successfully_processed_files: List[str] = cast(List[str], context["successfully_processed_files"])
    successful_regular_files_with_records: List[tuple[str, int]] = cast(
        List[tuple[str, int]],
        context["successful_regular_files_with_records"],
    )
    critical_errors: List[tuple[str, str, str]] = cast(List[tuple[str, str, str]], context["critical_errors"])
    deterministic_failed_files: List[str] = cast(List[str], context["deterministic_failed_files"])
    integrity_report: Dict[str, Any] = cast(Dict[str, Any], context["integrity_report"])
    candidate_db_path: Optional[str] = None
    promoted_backup_path: Optional[str] = None
    cancelled_full_rescan = bool(context["cancelled_full_rescan"])
    db_only_derivadas_sync = bool(context["db_only_derivadas_sync"])
    sync_materialized = bool(context["sync_materialized"])
    derivadas_sync_blocking_error = bool(context["derivadas_sync_blocking_error"])
    file_reports: List[Dict[str, Any]] = cast(List[Dict[str, Any]], context["file_reports"])
    phase_durations: Dict[str, float] = cast(Dict[str, float], context["phase_durations"])

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
            phase_durations=phase_durations,
        )
        report_path = _write_import_run_report(payload)
        if report_path:
            logger.info("Resumo JSON da importacao gravado em '%s'", report_path)
        return result

    try:
        working_db_path, candidate_db_path, integrity_report = (
            _prepare_working_database_for_import(
                data_dir=data_dir,
                primary_db_path=primary_db_path,
                run_id=run_id,
                force_import=force_import,
                table_name=table_name,
            )
        )

        work_items = _resolve_import_work_items(
            docs_dir=docs_dir,
            docs_dir_path=docs_dir_path,
            cache_file=cache_file,
            force_import=force_import,
            explicit_files=explicit_files,
        )
        ignored_legacy_excel_files = cast(
            List[str],
            work_items["ignored_legacy_excel_files"],
        )
        discovery_settings = cast(Dict[str, Any], work_items["discovery_settings"])
        files_to_process = cast(List[str], work_items["files_to_process"])
        derivadas_sheet_files = cast(List[str], work_items["derivadas_sheet_files"])
        move_processed_after_import = bool(work_items["move_processed_after_import"])
        db_only_derivadas_sync = False
        auto_derivadas_sync_enabled = True
        total_files = len(files_to_process)
        _emit_progress = _build_progress_emitter(progress_callback)
        _emit_progress("start", {"total": total_files})

        preflight_result = _handle_derivadas_preflight_without_regular_files(
            files_to_process=files_to_process,
            derivadas_sheet_files=derivadas_sheet_files,
            auto_derivadas_sync_enabled=auto_derivadas_sync_enabled,
            working_db_path=working_db_path,
            table_name=table_name,
            should_cancel=should_cancel,
            emit_progress=_emit_progress,
        )
        db_only_derivadas_sync = bool(preflight_result["db_only_derivadas_sync"])
        if bool(preflight_result["should_return"]):
            return _finalize_and_return(
                bool(preflight_result["result"]),
                str(preflight_result["status"]),
                str(preflight_result["reason"]),
            )

        if derivadas_sheet_files:
            logger.info(
                "Fase dedicada de derivadas habilitada com %s planilha(s) especial(is).",
                len(derivadas_sheet_files),
            )

        logger.info(
            f"{len(files_to_process)} arquivo(s) identificado(s) para importacao."
        )

        # --- 2. Processar cada arquivo ---
        file_processing_started = time.perf_counter()
        try:
            cancelled_full_rescan = _process_regular_files_phase(
                files_to_process=files_to_process,
                total_files=total_files,
                should_cancel=should_cancel,
                candidate_db_path=candidate_db_path,
                working_db_path=working_db_path,
                table_name=table_name,
                successfully_processed_files=successfully_processed_files,
                successful_regular_files_with_records=successful_regular_files_with_records,
                critical_errors=critical_errors,
                deterministic_failed_files=deterministic_failed_files,
                file_reports=file_reports,
                emit_progress=_emit_progress,
            )
            (
                sync_materialized,
                derivadas_sync_blocking_error,
                synced_special_files,
            ) = (
                _run_optional_derivadas_sync(
                    auto_derivadas_sync_enabled=auto_derivadas_sync_enabled,
                    successfully_processed_files=successfully_processed_files,
                    derivadas_sheet_files=derivadas_sheet_files,
                    db_only_derivadas_sync=db_only_derivadas_sync,
                    should_cancel=should_cancel,
                    working_db_path=working_db_path,
                    table_name=table_name,
                    docs_dir=docs_dir,
                    critical_errors=critical_errors,
                    emit_progress=_emit_progress,
                )
            )
            successfully_processed_files.extend(synced_special_files)
        finally:
            phase_durations["run_file_processing_seconds"] = (
                time.perf_counter() - file_processing_started
            )
            rejection_only = _has_only_deterministic_rejections(
                files_to_process=files_to_process,
                successfully_processed_files=successfully_processed_files,
                deterministic_failed_files=deterministic_failed_files,
                critical_errors=critical_errors,
            )
            _emit_progress(
                "finish",
                {
                    "total": total_files,
                    "processed": len(successfully_processed_files),
                    "errors": critical_errors,
                    "deterministic_failure_count": len(deterministic_failed_files),
                    "rejection_only": rejection_only,
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

        final_decision = _finalize_import_run_outcome(
            successfully_processed_files=successfully_processed_files,
            successful_regular_files_with_records=successful_regular_files_with_records,
            deterministic_failed_files=deterministic_failed_files,
            critical_errors=critical_errors,
            files_to_process=files_to_process,
            sync_materialized=sync_materialized,
            candidate_db_path=candidate_db_path,
            working_db_path=working_db_path,
            primary_db_path=primary_db_path,
            table_name=table_name,
            docs_dir=docs_dir,
            cache_file=cache_file,
            move_processed_after_import=move_processed_after_import,
            discovery_settings=discovery_settings,
            phase_durations=phase_durations,
        )
        final_integrity_report = final_decision.get("integrity_report")
        if isinstance(final_integrity_report, dict) and final_integrity_report:
            integrity_report = final_integrity_report
        promoted_backup_path = cast(
            Optional[str],
            final_decision.get("promoted_backup_path"),
        )
        working_db_path = str(final_decision.get("working_db_path", working_db_path))
        return _finalize_and_return(
            bool(final_decision["result"]),
            str(final_decision["status"]),
            str(final_decision["reason"]),
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
    except (ImporterError, OSError, ValueError, sqlite3.Error, pd.errors.DatabaseError) as e:
        logger.error(f"Erro na importacao de arquivos: {e}")
        if raise_on_error:
            raise
        return False


def import_explicit_files_to_database(
    file_paths: Sequence[str | os.PathLike[str]],
    *,
    docs_dir: str = "docs_entrada",
    db_path: str = "data/ssas.db",
    raise_on_error: bool = False,
) -> bool:
    """Import explicit supported files already staged under docs_dir into the database."""
    try:
        safe_docs_dir, safe_db_path = _resolve_import_targets(docs_dir, db_path)
        explicit_resolved = _resolve_explicit_import_files(
            file_paths,
            docs_dir_path=safe_docs_dir,
        )
        if not explicit_resolved:
            logger.info(
                "Nenhum arquivo explicito valido foi fornecido para importacao."
            )
            return False
        data_dir = safe_db_path.parent
        db_name = safe_db_path.name
        os.makedirs(data_dir, exist_ok=True)
        return run_importer_logic(
            docs_dir=str(safe_docs_dir),
            data_dir=str(data_dir),
            db_name=db_name,
            table_name="ssa_table",
            force_import=False,
            explicit_files=explicit_resolved,
        )
    except PathSafetyError as e:
        logger.error(f"Caminho rejeitado na importacao explicita: {e}")
        if raise_on_error:
            raise
        return False
    except (ImporterError, OSError, ValueError, sqlite3.Error, pd.errors.DatabaseError) as e:
        logger.error(f"Erro na importacao explicita de arquivos: {e}")
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
        sql_filter = _build_get_filtered_data_sql_filter(filters)
        if sql_filter is not None:
            where_clause, params = sql_filter
            table_sql = _quote_sql_identifier(CANONICAL_SSA_TABLE)
            query = f"SELECT * FROM {table_sql} WHERE {where_clause}"  # nosec B608
            return database.query_db(
                str(safe_db_path),
                CANONICAL_SSA_TABLE,
                query=query,
                params=params,
                raise_on_error=True,
            )

        df = database.query_db(
            str(safe_db_path),
            CANONICAL_SSA_TABLE,
            raise_on_error=True,
        )

        if filters:
            for column, value in filters.items():
                column_name = str(column)
                if (
                    column_name in QUERYABLE_FILTER_COLUMNS
                    and column_name in df.columns
                    and value is not None
                ):
                    terms = parse_search_terms(str(value))
                    if terms:
                        df = filter_dataframe(df, terms, [column_name])

        return df

    except (ValueError, sqlite3.Error, pd.errors.DatabaseError) as e:
        logger.error(f"Erro ao obter dados filtrados: {e}")
        return pd.DataFrame()  # Retorna DataFrame vazio em caso de erro


def _quote_sql_identifier(identifier: str) -> str:
    return '"' + identifier.replace('"', '""') + '"'


def _escape_sql_like(value: str) -> str:
    return (
        value.replace(SQL_LIKE_ESCAPE_CHAR, SQL_LIKE_ESCAPE_CHAR * 2)
        .replace("%", SQL_LIKE_ESCAPE_CHAR + "%")
        .replace("_", SQL_LIKE_ESCAPE_CHAR + "_")
    )


def _build_get_filtered_data_sql_filter(
    filters: Dict[str, Any] | None,
) -> tuple[str, tuple[Any, ...]] | None:
    if not filters:
        return None
    clauses: list[str] = []
    params: list[Any] = []
    for column, value in filters.items():
        column_name = str(column)
        if column_name not in QUERYABLE_FILTER_COLUMNS or value is None:
            continue
        terms = parse_search_terms(str(value))
        if not terms:
            continue
        column_expr = (
            f"LOWER(COALESCE(CAST({_quote_sql_identifier(column_name)} AS TEXT), ''))"
        )
        for term in terms:
            mode = str(term.get("mode") or "contains")
            if mode == "regex":
                return None
            term_value = str(term.get("value") or "")
            if not term_value.isascii():
                return None
            raw_value = term_value.lower()
            if mode == "exact":
                clause = f"{column_expr} = ?"
                param = raw_value
            elif mode == "prefix":
                clause = (
                    f"{column_expr} LIKE ? ESCAPE '{SQL_LIKE_ESCAPE_CHAR}'"
                )
                param = f"{_escape_sql_like(raw_value)}%"
            elif mode == "suffix":
                clause = (
                    f"{column_expr} LIKE ? ESCAPE '{SQL_LIKE_ESCAPE_CHAR}'"
                )
                param = f"%{_escape_sql_like(raw_value)}"
            else:
                clause = (
                    f"{column_expr} LIKE ? ESCAPE '{SQL_LIKE_ESCAPE_CHAR}'"
                )
                param = f"%{_escape_sql_like(raw_value)}%"
            if bool(term.get("negative")):
                clause = f"NOT ({clause})"
            clauses.append(clause)
            params.append(param)
    if not clauses:
        return None
    return " AND ".join(clauses), tuple(params)
