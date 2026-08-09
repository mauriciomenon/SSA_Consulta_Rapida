"""SQLite integrity verification and conservative repair boundaries."""

from __future__ import annotations

import os
import re
import shutil
import sqlite3
import time
from contextlib import closing
from datetime import datetime
from pathlib import Path
from typing import Any

from shared.db_names import (
    ALL_SSA_TABLE_NAMES,
    CANONICAL_SSA_TABLE,
    SSA_READ_REQUIRED_COLUMNS,
)
from shared.ssa_status import SSA_ACCEPTED_STATUS_VALUES, get_status_code
from utils.robust_logging import get_robust_logger

from .database_lock import database_writer_lock
from .identifier_utils import is_valid_identifier, quote_identifier as _quote_identifier

logger = get_robust_logger().get_logger(__name__, "storage")

MIN_FREE_SPACE_GB_WARN = 0.1
INTEGRITY_SNAPSHOT_MAX_COUNT = 2
INTEGRITY_SNAPSHOT_MIN_INTERVAL_SECONDS = 7 * 24 * 60 * 60
_OPTIONAL_REPAIR_COLUMNS = {
    "arquivo_origem": "TEXT",
    "data_planilha": "TEXT",
}
_FILE_REPLACE_RETRY_DELAYS = (0.0, 0.05, 0.15, 0.35)
_BACKUP_TIMESTAMP_PATTERN = re.compile(r"\d{8}_\d{6}_\d{6}")


def _is_ssa_table_name(table_name: str) -> bool:
    lookup = str(table_name or "").strip().casefold()
    return lookup in {name.casefold() for name in ALL_SSA_TABLE_NAMES}


def _resolve_report_table_name(
    conn: sqlite3.Connection, requested_table_name: str
) -> str:
    safe_table_name = str(requested_table_name or "").strip()
    if not is_valid_identifier(safe_table_name):
        raise ValueError(f"Invalid SQL identifier: {requested_table_name!r}")
    if not _is_ssa_table_name(safe_table_name):
        return safe_table_name

    from .database import resolve_target_table

    return resolve_target_table(conn, safe_table_name)


def _read_only_connection(path: str | Path) -> sqlite3.Connection:
    uri = Path(path).resolve().as_uri() + "?mode=ro"
    return sqlite3.connect(uri, uri=True, timeout=5)


def _raw_sqlite_integrity_ok(path: str | Path) -> bool:
    try:
        with closing(_read_only_connection(path)) as conn:
            row = conn.execute("PRAGMA quick_check").fetchone()
        return bool(row and row[0] == "ok")
    except (OSError, sqlite3.Error):
        return False


def _replace_file_with_retry(source: str | Path, target: str | Path) -> None:
    last_error: OSError | None = None
    for delay in _FILE_REPLACE_RETRY_DELAYS:
        if delay:
            time.sleep(delay)
        try:
            os.replace(source, target)
            return
        except OSError as exc:
            last_error = exc
    if last_error is not None:
        raise last_error


def _backup_paths(db_path: str, marker: str) -> list[Path]:
    db = Path(db_path).resolve()
    backup_dir = db.parent / "historico_backups"
    prefix = f"{db.name}.{marker}_"
    try:
        paths = [
            path
            for path in backup_dir.iterdir()
            if path.is_file()
            and path.name.startswith(prefix)
            and path.name.endswith(".db")
            and _BACKUP_TIMESTAMP_PATTERN.fullmatch(
                path.name[len(prefix) : -len(".db")]
            )
        ]
    except FileNotFoundError:
        return []
    return sorted(paths, key=lambda path: path.stat().st_mtime)


def _snapshot_paths(db_path: str) -> list[Path]:
    return _backup_paths(db_path, "integrity")


def _prune_integrity_snapshots(db_path: str) -> None:
    snapshots = _snapshot_paths(db_path)
    for stale in snapshots[:-INTEGRITY_SNAPSHOT_MAX_COUNT]:
        try:
            stale.unlink()
        except OSError as exc:
            logger.warning("Falha ao remover snapshot antigo '%s': %s", stale, exc)


def _create_integrity_snapshot(db_path: str, *, force: bool = False) -> Path | None:
    db = Path(db_path).resolve()
    if ".full_rescan_candidate_" in db.name:
        return None
    snapshots = _snapshot_paths(db_path)
    if snapshots and not force:
        age_seconds = time.time() - snapshots[-1].stat().st_mtime
        if age_seconds < INTEGRITY_SNAPSHOT_MIN_INTERVAL_SECONDS:
            return snapshots[-1]

    backup_dir = db.parent / "historico_backups"
    backup_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    snapshot = backup_dir / f"{db.name}.integrity_{timestamp}.db"
    temporary = snapshot.with_suffix(".tmp")
    try:
        with closing(_read_only_connection(db)) as source_conn:
            with closing(sqlite3.connect(temporary)) as destination_conn:
                source_conn.backup(destination_conn, pages=1000)
        if not _raw_sqlite_integrity_ok(temporary):
            raise sqlite3.DatabaseError("snapshot failed PRAGMA quick_check")
        os.replace(temporary, snapshot)
        _prune_integrity_snapshots(db_path)
        logger.info("Snapshot SQLite consistente criado: %s", snapshot)
        return snapshot
    except (OSError, sqlite3.Error) as exc:
        logger.error("Falha ao criar snapshot SQLite consistente: %s", exc)
        try:
            temporary.unlink(missing_ok=True)
        except OSError as cleanup_error:
            logger.warning(
                "Falha ao remover snapshot temporario '%s': %s",
                temporary,
                cleanup_error,
            )
        return None


def _prune_forensic_backups(db_path: str) -> None:
    backups = _backup_paths(db_path, "corrupt")
    for stale in backups[:-INTEGRITY_SNAPSHOT_MAX_COUNT]:
        for candidate in (stale, Path(f"{stale}-wal"), Path(f"{stale}-shm")):
            try:
                candidate.unlink(missing_ok=True)
            except OSError as exc:
                logger.warning(
                    "Falha ao remover backup forense antigo '%s': %s", candidate, exc
                )


def _restore_latest_valid_snapshot(db_path: str, table_name: str) -> bool:
    with database_writer_lock(db_path):
        return _restore_latest_valid_snapshot_locked(db_path, table_name)


def _restore_latest_valid_snapshot_locked(db_path: str, table_name: str) -> bool:
    db = Path(db_path).resolve()
    backup_dir = db.parent / "historico_backups"
    backup_dir.mkdir(parents=True, exist_ok=True)
    for snapshot in reversed(_snapshot_paths(db_path)):
        if not _raw_sqlite_integrity_ok(snapshot):
            logger.error("Snapshot ignorado por falha de integridade: %s", snapshot)
            continue

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        temporary = Path(f"{db}.restore_{timestamp}.tmp")
        forensic = backup_dir / f"{db.name}.corrupt_{timestamp}.db"
        moved_sidecars: list[tuple[Path, Path]] = []
        try:
            shutil.copy2(snapshot, temporary)
            shutil.copy2(db, forensic)
            for suffix in ("-wal", "-shm"):
                sidecar = Path(f"{db}{suffix}")
                if sidecar.exists():
                    forensic_sidecar = Path(f"{forensic}{suffix}")
                    _replace_file_with_retry(sidecar, forensic_sidecar)
                    moved_sidecars.append((sidecar, forensic_sidecar))
            _replace_file_with_retry(temporary, db)
        except (OSError, sqlite3.Error) as exc:
            logger.error("Falha ao preparar restauracao do snapshot '%s': %s", snapshot, exc)
            temporary.unlink(missing_ok=True)
            try:
                for original, archived in moved_sidecars:
                    if archived.exists():
                        _replace_file_with_retry(archived, original)
            except OSError as rollback_error:
                logger.critical(
                    "Falha ao recompor sidecars apos restauracao abortada: %s",
                    rollback_error,
                )
                return False
            continue

        final_report = verify_database_integrity(str(db), table_name)
        if final_report["is_valid"]:
            _prune_forensic_backups(db_path)
            logger.warning(
                "Banco restaurado do ultimo snapshot valido; original preservado em: %s",
                forensic,
            )
            return True

        logger.error(
            "Snapshot restaurado falhou na validacao funcional: %s",
            final_report["issues"],
        )
        rollback_temporary = Path(f"{db}.rollback_{timestamp}.tmp")
        restored_sidecars: list[tuple[Path, Path]] = []
        try:
            for original, archived in moved_sidecars:
                if archived.exists():
                    _replace_file_with_retry(archived, original)
                    restored_sidecars.append((original, archived))
            shutil.copy2(forensic, rollback_temporary)
            _replace_file_with_retry(rollback_temporary, db)
        except OSError as exc:
            rollback_temporary.unlink(missing_ok=True)
            for original, archived in restored_sidecars:
                if original.exists():
                    _replace_file_with_retry(original, archived)
            logger.critical("Falha ao restaurar banco original apos rollback: %s", exc)
            return False
    return False


def _validate_ssa_data(
    conn: sqlite3.Connection, table_name: str, report: dict[str, Any]
) -> None:
    quoted_table = _quote_identifier(table_name)
    missing_numero = int(
        conn.execute(
            f"SELECT COUNT(*) FROM {quoted_table} "  # nosec B608
            "WHERE numero_ssa IS NULL OR trim(CAST(numero_ssa AS TEXT)) = ''"
        ).fetchone()[0]
    )
    invalid_numero = int(
        conn.execute(
            f"SELECT COUNT(*) FROM {quoted_table} "  # nosec B608
            "WHERE numero_ssa IS NOT NULL "
            "AND trim(CAST(numero_ssa AS TEXT)) <> '' "
            "AND (length(trim(CAST(numero_ssa AS TEXT))) <> 9 "
            "OR trim(CAST(numero_ssa AS TEXT)) GLOB '*[^0-9]*'"
            ")"
        ).fetchone()[0]
    )
    duplicate_numero = int(
        conn.execute(
            f"SELECT COUNT(*) FROM (SELECT trim(CAST(numero_ssa AS TEXT)) AS key "  # nosec B608
            f"FROM {quoted_table} WHERE numero_ssa IS NOT NULL "  # nosec B608
            "AND trim(CAST(numero_ssa AS TEXT)) <> '' "
            "GROUP BY key HAVING COUNT(*) > 1)"
        ).fetchone()[0]
    )
    invalid_date = int(
        conn.execute(
            f"SELECT COUNT(*) FROM {quoted_table} "  # nosec B608
            "WHERE (data_cadastro IS NULL OR trim(CAST(data_cadastro AS TEXT)) = '') "
            "AND upper(substr(trim(COALESCE(CAST(situacao AS TEXT), '')), 1, 3)) "
            "NOT IN ('SCC', 'ADI', 'ASE') "
            "OR (data_cadastro IS NOT NULL "
            "AND trim(CAST(data_cadastro AS TEXT)) <> '' "
            "AND (length(trim(CAST(data_cadastro AS TEXT))) <> 19 "
            "OR datetime(replace(trim(CAST(data_cadastro AS TEXT)), 'T', ' ')) IS NULL "
            "OR strftime('%Y-%m-%d %H:%M:%S', "
            "replace(trim(CAST(data_cadastro AS TEXT)), 'T', ' ')) "
            "<> replace(trim(CAST(data_cadastro AS TEXT)), 'T', ' ')))"
        ).fetchone()[0]
    )
    missing_status = int(
        conn.execute(
            f"SELECT COUNT(*) FROM {quoted_table} "  # nosec B608
            "WHERE situacao IS NULL OR trim(CAST(situacao AS TEXT)) = ''"
        ).fetchone()[0]
    )
    raw_statuses = conn.execute(  # nosec B608
        f"SELECT DISTINCT situacao FROM {quoted_table} "  # nosec B608
        "WHERE situacao IS NOT NULL AND trim(CAST(situacao AS TEXT)) <> ''"
    ).fetchall()
    unknown_statuses = sorted(
        {
            str(row[0]).strip()
            for row in raw_statuses
            if get_status_code(row[0]) not in SSA_ACCEPTED_STATUS_VALUES
        }
    )

    report["invalid_data"] = {
        "missing_numero_ssa": missing_numero,
        "invalid_numero_ssa": invalid_numero,
        "duplicate_numero_ssa": duplicate_numero,
        "invalid_data_cadastro": invalid_date,
        "missing_situacao": missing_status,
        "unknown_situacao": unknown_statuses[:10],
    }
    if missing_numero:
        report["warnings"].append(
            f"numero_ssa ausente em {missing_numero} linha(s) tolerada(s)"
        )
    if missing_status:
        report["warnings"].append(
            f"situacao ausente em {missing_status} linha(s) tolerada(s)"
        )
    if invalid_numero:
        report["issues"].append(
            f"numero_ssa fora do formato canonico em {invalid_numero} linha(s)"
        )
    if duplicate_numero:
        report["issues"].append(
            f"numero_ssa duplicado em {duplicate_numero} grupo(s)"
        )
    if invalid_date:
        report["issues"].append(
            f"data_cadastro fora do formato canonico em {invalid_date} linha(s)"
        )
    if unknown_statuses:
        report["issues"].append(
            "situacao fora do catalogo canonico: " + ", ".join(unknown_statuses[:10])
        )
    if invalid_numero or duplicate_numero or invalid_date or unknown_statuses:
        report["is_valid"] = False
        report["data_consistent"] = False


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
        "sqlite_integrity_ok": False,
        "table_exists": False,
        "schema_valid": False,
        "data_consistent": False,
        "disk_space_sufficient": False,
        "file_permissions_ok": False,
        "needs_creation": False,
        "missing_required_columns": [],
        "missing_optional_columns": [],
        "invalid_data": {},
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
        if os.path.getsize(db_path) == 0:
            report["issues"].append(
                "Arquivo de banco encontrado mas vazio (0 bytes) - invalido"
            )
            report["needs_creation"] = True
            report["is_valid"] = False
            return report

        if os.access(db_path, os.R_OK | os.W_OK):
            report["file_permissions_ok"] = True
        else:
            report["issues"].append(f"Permissoes insuficientes para o banco: {db_path}")
            report["is_valid"] = False

        try:
            free_space_gb = shutil.disk_usage(os.path.dirname(db_path) or ".").free / (
                1024**3
            )
            if free_space_gb >= MIN_FREE_SPACE_GB_WARN:
                report["disk_space_sufficient"] = True
            else:
                report["warnings"].append(
                    f"Pouco espaco em disco: {free_space_gb:.2f}GB disponivel"
                )
        except OSError as exc:
            report["warnings"].append(
                f"Nao foi possivel verificar espaco em disco: {exc}"
            )

        with closing(_read_only_connection(db_path)) as conn:
            integrity_result = conn.execute("PRAGMA integrity_check").fetchone()
            if not integrity_result or integrity_result[0] != "ok":
                report["issues"].append(
                    f"Falha na verificacao de integridade SQLite: {integrity_result}"
                )
                report["is_valid"] = False
                return report
            report["database_accessible"] = True
            report["sqlite_integrity_ok"] = True

            resolved_table_name = _resolve_report_table_name(conn, report["table_name"])
            report["table_name"] = resolved_table_name
            object_row = conn.execute(
                "SELECT type FROM sqlite_master WHERE name=? AND type IN ('table','view')",
                (resolved_table_name,),
            ).fetchone()
            if not object_row:
                report["issues"].append(
                    f"Tabela fisica '{resolved_table_name}' nao encontrada"
                )
                report["is_valid"] = False
                return report
            if _is_ssa_table_name(resolved_table_name) and object_row[0] != "table":
                report["issues"].append(
                    f"Objeto SSA '{resolved_table_name}' e view sem tabela fisica valida"
                )
                report["is_valid"] = False
                return report
            report["table_exists"] = True

            quoted_table = _quote_identifier(resolved_table_name)
            existing_columns = {
                str(row[1])
                for row in conn.execute(
                    f"PRAGMA table_info({quoted_table})"  # nosec B608
                ).fetchall()
            }
            required_columns = (
                SSA_READ_REQUIRED_COLUMNS
                if _is_ssa_table_name(resolved_table_name)
                else ("numero_ssa", "situacao", "data_cadastro", "descricao_ssa")
            )
            missing_required = [
                column for column in required_columns if column not in existing_columns
            ]
            report["missing_required_columns"] = missing_required
            for optional_column in _OPTIONAL_REPAIR_COLUMNS:
                if optional_column not in existing_columns:
                    report["missing_optional_columns"].append(optional_column)
                    report["warnings"].append(
                        f"Coluna opcional '{optional_column}' ausente"
                    )
            if missing_required:
                report["issues"].append(
                    f"Colunas obrigatorias ausentes: {missing_required}"
                )
                report["repair_suggestion"] = (
                    "Restaure um snapshot valido ou execute migracao explicita de schema"
                )
                report["is_valid"] = False
                return report
            report["schema_valid"] = True
            report["data_consistent"] = True
            if _is_ssa_table_name(resolved_table_name):
                _validate_ssa_data(conn, resolved_table_name, report)
    except (OSError, sqlite3.Error, ValueError) as exc:
        report["issues"].append(f"Erro ao verificar integridade/schema do banco: {exc}")
        report["is_valid"] = False
    except Exception as exc:  # pragma: no cover
        report["issues"].append(f"Erro inesperado na verificacao: {exc}")
        report["is_valid"] = False

    status_text = "Valido" if report["is_valid"] else "Problemas encontrados"
    logger.info("Verificacao de integridade concluida. Status: %s", status_text)
    return report


def repair_database_if_needed(
    db_path: str,
    schema_file: str = "schema.sql",
    table_name: str = CANONICAL_SSA_TABLE,
) -> bool:
    with database_writer_lock(db_path):
        return _repair_database_if_needed_locked(db_path, schema_file, table_name)


def _repair_database_if_needed_locked(
    db_path: str,
    schema_file: str,
    table_name: str,
) -> bool:
    logger.info("Iniciando verificacao conservadora do banco de dados...")
    try:
        report = verify_database_integrity(db_path, table_name)
        if report["is_valid"] and not report["missing_optional_columns"]:
            _create_integrity_snapshot(db_path)
            return True

        if report["needs_creation"]:
            logger.info("Banco ausente em bootstrap; criacao inicial sera executada")
            from .database import initialize_database

            initialize_database(db_path, schema_file)
            final_report = verify_database_integrity(db_path, table_name)
            if final_report["is_valid"]:
                _create_integrity_snapshot(db_path, force=True)
                return True
            logger.error("Schema criado falhou na validacao: %s", final_report["issues"])
            return False

        sqlite_integrity_ok = bool(
            report.get("sqlite_integrity_ok", report.get("data_consistent", False))
        )
        if not sqlite_integrity_ok:
            if _restore_latest_valid_snapshot(db_path, table_name):
                return True
            logger.error("Banco corrompido sem snapshot valido para restauracao")
            return False

        if not report["table_exists"]:
            logger.error("Tabela SSA fisica ausente; reparo automatico foi bloqueado")
            return False

        missing_required = list(report["missing_required_columns"])
        missing_optional = list(report["missing_optional_columns"])
        if not missing_required and not missing_optional:
            logger.error("Inconsistencia de dados exige reimportacao, nao reparo automatico")
            return False

        snapshot = _create_integrity_snapshot(db_path, force=True)
        if snapshot is None:
            logger.error("Reparo bloqueado porque o snapshot preventivo falhou")
            return False

        from .database import get_db_connection

        resolved_table = str(report["table_name"])
        if missing_required and missing_required != ["situacao"]:
            logger.error(
                "Colunas obrigatorias ausentes exigem migracao explicita: %s",
                missing_required,
            )
            return False

        with get_db_connection(db_path, write=True) as conn:
            quoted_table = _quote_identifier(resolved_table)
            columns = {
                str(row[1])
                for row in conn.execute(
                    f"PRAGMA table_info({quoted_table})"  # nosec B608
                ).fetchall()
            }
            if missing_required and "status" not in columns:
                logger.error(
                    "Coluna situacao ausente sem coluna legada status para migracao segura"
                )
                return False
            conn.execute("BEGIN IMMEDIATE")
            if missing_required:
                conn.execute(
                    f"ALTER TABLE {quoted_table} RENAME COLUMN "  # nosec B608
                    f"{_quote_identifier('status')} TO {_quote_identifier('situacao')}"  # nosec B608
                )
                logger.warning("Coluna legada status renomeada para situacao com valores preservados")
            for column_name in missing_optional:
                definition = _OPTIONAL_REPAIR_COLUMNS[column_name]
                conn.execute(
                    f"ALTER TABLE {quoted_table} ADD COLUMN "  # nosec B608
                    f"{_quote_identifier(column_name)} {definition}"  # nosec B608
                )
            conn.commit()

        final_report = verify_database_integrity(db_path, table_name)
        if not final_report["is_valid"]:
            logger.error("Reparo conservador falhou: %s", final_report["issues"])
            return False
        _create_integrity_snapshot(db_path, force=True)
        logger.info("Reparo conservador concluido com sucesso")
        return True
    except (OSError, sqlite3.Error, ValueError) as exc:
        logger.error("Erro durante tentativa de reparo: %s", exc)
        return False
