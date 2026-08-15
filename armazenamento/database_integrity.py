"""Funcoes de verificacao e reparo extraidas de `database.py`.

Publicadas novamente atraves de `database` para compatibilidade.

CIRCULAR DEPENDENCY MITIGATION:
This module is imported lazily by database.py (inside functions). This module imports
from database.py using lazy imports (inside functions) to avoid circular import errors.
All imports from database.py must be lazy (inside functions).
DO NOT add top-level imports from database.py.
"""

# Last modified: 2025-10-29T11:05:00 (circular import documentation)
from __future__ import annotations

import os
import shutil
import sqlite3
from datetime import datetime
from typing import Any

import pandas as pd

from shared.db_names import ALL_SSA_TABLE_NAMES, CANONICAL_SSA_TABLE
from utils.robust_logging import get_robust_logger

from .identifier_utils import is_valid_identifier

# Lazy imports from database.py to avoid circular dependency (see lines 82, 100, 117, etc.)

logger = get_robust_logger().get_logger(__name__, "storage")

MIN_FREE_SPACE_GB_WARN = 0.1


def _quote_identifier(name: str) -> str:
    safe_name = str(name or "").strip()
    if not is_valid_identifier(safe_name):
        raise ValueError(f"Invalid SQL identifier: {name!r}")
    return '"' + safe_name.replace('"', '""') + '"'


def _build_explicit_select_all_query(conn: sqlite3.Connection, table_name: str) -> str:
    quoted_table = _quote_identifier(table_name)
    rows = conn.execute(f"PRAGMA table_info({quoted_table})").fetchall()  # nosec B608
    columns = [str(row[1]) for row in rows if len(row) > 1 and row[1]]
    if not columns:
        raise ValueError(f"No columns found for table: {table_name}")
    projection = ", ".join(_quote_identifier(column) for column in columns)
    return f"SELECT {projection} FROM {quoted_table}"  # nosec B608


def _resolve_report_table_name(conn, requested_table_name: str) -> str:
    safe_table_name = str(requested_table_name or "").strip()
    if not is_valid_identifier(safe_table_name):
        raise ValueError(f"Invalid SQL identifier: {requested_table_name!r}")

    table_candidates = list(
        dict.fromkeys([safe_table_name, CANONICAL_SSA_TABLE, *ALL_SSA_TABLE_NAMES])
    )
    for object_type in ("table", "view"):
        for candidate in table_candidates:
            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type=? AND name=?",
                (object_type, candidate),
            )
            if cursor.fetchone():
                return candidate
    return safe_table_name


def verify_database_integrity(
    db_path: str,
    table_name: str = CANONICAL_SSA_TABLE,
) -> dict[str, Any]:  # noqa: PLR0912, PLR0915
    report: dict[str, Any] = {
        "table_name": str(table_name or "").strip() or CANONICAL_SSA_TABLE,
        "is_valid": True,
        "issues": [],
        "warnings": [],
        "database_exists": False,
        "database_accessible": False,
        "table_exists": False,
        "schema_valid": False,
        "data_consistent": False,
        "disk_space_sufficient": False,
        "file_permissions_ok": False,
        "needs_creation": False,
        "missing_required_columns": [],
        "missing_optional_columns": [],
        "repair_suggestion": None,
    }
    try:
        if not is_valid_identifier(report["table_name"]):
            report["issues"].append(f"Invalid SQL identifier: {table_name!r}")
            report["is_valid"] = False
            return report
        if not os.path.exists(db_path):
            report["issues"].append(
                f"Arquivo do banco de dados nao encontrado: {db_path}"
            )
            report["needs_creation"] = True
            report["is_valid"] = False
            return report
        report["database_exists"] = True
        # Tamanho do arquivo
        try:
            if os.path.getsize(db_path) == 0:
                report["issues"].append(
                    "Arquivo de banco encontrado mas vazio (0 bytes) - invalido"
                )
                report["needs_creation"] = True
                report["is_valid"] = False
                return report
        except Exception as e:  # pragma: no cover
            report["warnings"].append(f"Falha ao obter tamanho do arquivo: {e}")
        # Permissoes
        try:
            if not os.access(db_path, os.R_OK | os.W_OK):
                report["issues"].append(
                    f"Permissoes insuficientes para o banco: {db_path}"
                )
                report["is_valid"] = False
            else:
                report["file_permissions_ok"] = True
        except Exception as e:
            report["issues"].append(f"Erro ao verificar permissoes: {e}")
            report["is_valid"] = False
        # Espaco em disco
        try:
            db_dir = os.path.dirname(db_path) or "."
            try:
                free_space_gb = shutil.disk_usage(db_dir).free / (1024**3)
            except Exception:
                statvfs = os.statvfs(db_dir) if hasattr(os, "statvfs") else None
                if statvfs is None:
                    raise
                free_space_gb = (statvfs.f_frsize * statvfs.f_bavail) / (1024**3)
            if free_space_gb >= MIN_FREE_SPACE_GB_WARN:
                report["disk_space_sufficient"] = True
            else:
                report["warnings"].append(
                    f"Pouco espaco em disco: {free_space_gb:.2f}GB disponivel"
                )
        except Exception as e:
            report["warnings"].append(
                f"Nao foi possivel verificar espaco em disco: {e}"
            )
        # PRAGMA integrity_check
        try:
            from .database import get_db_connection  # lazy

            with get_db_connection(db_path) as conn:
                cursor = conn.execute("PRAGMA integrity_check")
                integrity_result = cursor.fetchone()
                if not integrity_result or integrity_result[0] != "ok":
                    report["issues"].append(
                        f"Falha na verificacao de integridade SQLite: {integrity_result}"
                    )
                    report["is_valid"] = False
                    return report
                report["database_accessible"] = True
                report["data_consistent"] = True
                resolved_table_name = _resolve_report_table_name(
                    conn, report["table_name"]
                )
                report["table_name"] = resolved_table_name
                cursor = conn.execute(
                    "SELECT name FROM sqlite_master WHERE type IN ('table','view') AND name=?",
                    (resolved_table_name,),
                )
                if cursor.fetchone():
                    report["table_exists"] = True
                else:
                    report["issues"].append(
                        f"Tabela '{resolved_table_name}' nao encontrada"
                    )
                    report["is_valid"] = False

                if report["table_exists"]:
                    quoted_table_name = _quote_identifier(resolved_table_name)
                    required_columns = [
                        "numero_ssa",
                        "situacao",
                        "data_cadastro",
                        "descricao_ssa",
                    ]
                    cursor = conn.execute(f"PRAGMA table_info({quoted_table_name})")
                    existing_columns = [row[1] for row in cursor.fetchall()]
                    if "arquivo_origem" not in existing_columns:
                        report["missing_optional_columns"].append("arquivo_origem")
                        report["warnings"].append(
                            "Coluna 'arquivo_origem' ausente; reparo explicito pode adiciona-la."
                        )
                    if "data_planilha" not in existing_columns:
                        report["missing_optional_columns"].append("data_planilha")
                        report["warnings"].append(
                            "Coluna 'data_planilha' ausente; reparo explicito pode adiciona-la."
                        )

                    missing = [c for c in required_columns if c not in existing_columns]
                    if missing:
                        report["missing_required_columns"] = missing
                        report["issues"].append(
                            f"Colunas obrigatorias ausentes: {missing}"
                        )
                        report["repair_suggestion"] = (
                            "Execute repair_database_if_needed() ou migracao de schema "
                            f"para adicionar: {missing}"
                        )
                        report["is_valid"] = False
                    else:
                        report["schema_valid"] = True
        except (sqlite3.Error, OSError, ValueError) as e:
            report["issues"].append(
                f"Erro ao verificar integridade/schema do banco: {e}"
            )
            report["is_valid"] = False
            return report
        status_text = "Valido" if report["is_valid"] else "Problemas encontrados"
        logger.info("Verificacao de integridade concluida. Status: %s", status_text)
    except Exception as e:  # pragma: no cover
        report["issues"].append(f"Erro inesperado na verificacao: {e}")
        report["is_valid"] = False
    return report


def repair_database_if_needed(
    db_path: str,
    schema_file: str = "schema.sql",
    table_name: str = CANONICAL_SSA_TABLE,
) -> bool:  # noqa: PLR0912
    logger.info("Iniciando verificacao e reparo do banco de dados...")
    try:
        integrity_report = verify_database_integrity(db_path, table_name)
        missing_optional_columns = integrity_report.get("missing_optional_columns", [])
        missing_required_columns = integrity_report.get("missing_required_columns", [])
        if integrity_report["is_valid"] and not missing_optional_columns:
            logger.info("Banco de dados integro - nenhum reparo necessario")
            return True
        if integrity_report["is_valid"] and missing_optional_columns:
            logger.info(
                "Banco integro com colunas opcionais pendentes de reparo: %s",
                missing_optional_columns,
            )
        expected_creation = integrity_report.get("needs_creation", False)
        if expected_creation and integrity_report.get("database_exists", False):
            logger.info("Banco invalido em estado recriavel; schema sera recriado.")
        elif expected_creation:
            logger.info("Banco ausente em bootstrap; criacao inicial sera executada.")
        elif integrity_report["issues"]:
            logger.warning(
                "Problemas detectados no banco: %s", integrity_report["issues"]
            )
        else:
            logger.info(
                "Nenhum problema critico detectado; aplicando apenas reparos opcionais."
            )
        repaired = False
        if expected_creation:
            logger.info("Recriando schema do banco de dados...")
            from .database import initialize_database  # lazy

            initialize_database(db_path, schema_file)
            repaired = True
        elif not integrity_report["data_consistent"]:
            logger.warning("Detectada corrupcao no banco - tentando backup/restore...")
            backup_path = f"{db_path}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            try:
                shutil.copy2(db_path, backup_path)
                logger.info("Backup criado em: %s", backup_path)
                from . import database_upsert_logic as _up
                from .database import get_db_connection  # lazy
                from .database import initialize_database

                df_backup = pd.DataFrame()
                with get_db_connection(db_path) as conn:
                    try:
                        table_candidates = list(
                            dict.fromkeys([table_name, *ALL_SSA_TABLE_NAMES])
                        )
                        source_table = None
                        for candidate in table_candidates:
                            cursor = conn.execute(
                                "SELECT name FROM sqlite_master WHERE type IN ('table','view') AND name=?",
                                (candidate,),
                            )
                            if cursor.fetchone():
                                source_table = candidate
                                break
                        if source_table is None:
                            raise ValueError(
                                "No compatible SSA table found for repair backup."
                            )
                        if not is_valid_identifier(source_table):
                            raise ValueError(f"Invalid SQL identifier: {source_table}")
                        df_backup = pd.read_sql_query(
                            _build_explicit_select_all_query(conn, source_table),
                            conn,
                        )
                    except Exception as e:  # pragma: no cover
                        logger.error(
                            "Nao foi possivel extrair dados do banco corrompido: %s", e
                        )
                if not df_backup.empty:
                    repair_path = (
                        f"{db_path}.repair_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                    )
                    try:
                        initialize_database(repair_path, schema_file)
                        if _up.insert_dataframe_with_smart_upsert_impl(
                            df_backup,
                            repair_path,
                            CANONICAL_SSA_TABLE,
                        ):
                            repair_check = verify_database_integrity(
                                repair_path, table_name
                            )
                            if repair_check["is_valid"]:
                                os.replace(repair_path, db_path)
                                final_repair_check = verify_database_integrity(
                                    db_path, table_name
                                )
                                if final_repair_check["is_valid"]:
                                    logger.info(
                                        "Dados restaurados com sucesso apos correcao"
                                    )
                                    repaired = True
                                else:
                                    logger.error(
                                        "Banco substituido falhou na validacao final: %s",
                                        final_repair_check["issues"],
                                    )
                                    shutil.copy2(backup_path, db_path)
                                    logger.warning(
                                        "Backup original restaurado apos falha na validacao final."
                                    )
                            else:
                                logger.error(
                                    "Banco reparado temporario falhou na validacao final: %s",
                                    repair_check["issues"],
                                )
                    finally:
                        if os.path.exists(repair_path) and not repaired:
                            try:
                                os.remove(repair_path)
                            except OSError as cleanup_error:  # pragma: no cover
                                logger.warning(
                                    "Nao foi possivel remover banco temporario de reparo: %s",
                                    cleanup_error,
                                )
                else:
                    logger.warning(
                        "Nenhum dado foi extraido do banco corrompido para restauracao."
                    )
            except Exception as e:  # pragma: no cover
                logger.error("Falha no processo de backup/restore: %s", e)
        elif not integrity_report["table_exists"]:
            logger.info("Recriando schema do banco...")
            from .database import initialize_database  # lazy

            initialize_database(db_path, schema_file)
            repaired = True
        elif integrity_report["table_exists"]:
            from .database import ensure_column_exists  # lazy

            required_column_types = {
                "numero_ssa": "TEXT",
                "situacao": "TEXT",
                "data_cadastro": "TEXT",
                "descricao_ssa": "TEXT",
            }
            repaired_columns: list[str] = []
            for column_name in missing_required_columns:
                column_type = required_column_types.get(column_name)
                if not column_type:
                    logger.warning(
                        "Tipo de coluna obrigatoria nao mapeado para reparo: %s",
                        column_name,
                    )
                    continue
                if ensure_column_exists(
                    db_path,
                    integrity_report["table_name"],
                    column_name,
                    column_type,
                ):
                    repaired_columns.append(column_name)
            if repaired_columns:
                logger.info(
                    "Colunas obrigatorias adicionadas no reparo: %s", repaired_columns
                )
                repaired = True

            repaired_optional_columns: list[str] = []
            if "arquivo_origem" in missing_optional_columns and ensure_column_exists(
                db_path, integrity_report["table_name"], "arquivo_origem", "TEXT"
            ):
                repaired_optional_columns.append("arquivo_origem")
            if "data_planilha" in missing_optional_columns and ensure_column_exists(
                db_path, integrity_report["table_name"], "data_planilha", "TEXT"
            ):
                repaired_optional_columns.append("data_planilha")
            if repaired_optional_columns:
                logger.info(
                    "Colunas opcionais adicionadas no reparo: %s",
                    repaired_optional_columns,
                )
                repaired = True
        if repaired:
            final_check = verify_database_integrity(db_path, table_name)
            if final_check["is_valid"]:
                logger.info("Reparo do banco de dados concluido com sucesso")
                return True
            logger.error("Reparo falhou - problemas persistem")
            return False
        logger.error("Nenhum reparo foi possivel para os problemas detectados")
        return False
    except Exception as e:  # pragma: no cover
        logger.error("Erro durante tentativa de reparo: %s", e)
        return False
