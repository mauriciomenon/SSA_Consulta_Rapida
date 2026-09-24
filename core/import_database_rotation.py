"""SQLite rotation helpers for full rescan imports."""

from __future__ import annotations

import json
import logging
import os
import re
import sqlite3
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from armazenamento.database_lock import database_writer_lock
from armazenamento.database_publication import (
    restore_journal_mode,
    snapshot_database_for_replace,
)
from core.import_errors import DatabaseError

logger = logging.getLogger(__name__)

SQLITE_CHECKPOINT_BUSY_INDEX = 0
SQLITE_CHECKPOINT_LOG_INDEX = 1
SQLITE_CHECKPOINT_CHECKPOINTED_INDEX = 2
SQLITE_FILE_REPLACE_RETRY_DELAYS_SECONDS = (0.0, 0.1, 0.35, 0.75)


def rotate_preexisting_database_for_full_rescan(db_path: str) -> Optional[str]:
    """Rotate the previous DB before a full rescan creates a clean candidate."""
    return rotate_database_for_full_rescan(db_path)


FULL_RESCAN_ARTIFACT_KEEP_COUNT = 2
_FULL_RESCAN_ARTIFACT_MARKERS = ("full_rescan_candidate_", "full_rescan_backup_")
_SQLITE_SIDECAR_SUFFIXES = ("-wal", "-shm", "-journal")
_FULL_RESCAN_RUN_ID_RE = re.compile(r"[0-9]{8}_[0-9]{6}_[0-9]{6}")


def build_full_rescan_candidate_path(db_path: str, run_id: str) -> str:
    """Build an isolated DB path for a full-rescan candidate run."""
    return f"{db_path}.full_rescan_candidate_{run_id}"


def _full_rescan_marker_path(artifact_path: Path) -> Path:
    return artifact_path.with_name(f".ssa-full-rescan-{artifact_path.name}.json")


def register_full_rescan_artifact(db_path: str, artifact_db_path: str) -> None:
    """Registra a identidade de um artefato novo sem comprometer a rotacao."""
    artifact = Path(artifact_db_path)
    try:
        if artifact.is_symlink() or not artifact.is_file():
            raise OSError("artefato nao e arquivo regular proprio")
        identity = artifact.stat()
        if not identity.st_ino:
            raise OSError("filesystem nao fornece identidade persistente")
        record = {
            "version": 1,
            "primary_db": os.path.realpath(db_path),
            "artifact": artifact.name,
            "device": identity.st_dev,
            "inode": identity.st_ino,
        }
        with _full_rescan_marker_path(artifact).open("x", encoding="utf-8") as marker:
            json.dump(record, marker)
    except OSError as exc:
        logger.warning(
            "Artefato preservado sem novo registro de propriedade '%s': %s",
            artifact,
            exc,
        )


def _read_full_rescan_marker(db_path: str, artifact: Path) -> Optional[dict[str, Any]]:
    marker_path = _full_rescan_marker_path(artifact)
    try:
        if marker_path.is_symlink():
            return None
        with marker_path.open(encoding="utf-8") as marker:
            record = json.load(marker)
        if (
            isinstance(record, dict)
            and record.get("version") == 1
            and record.get("primary_db") == os.path.realpath(db_path)
            and record.get("artifact") == artifact.name
        ):
            return record
        logger.warning("Registro de propriedade invalido: %s", marker_path)
    except FileNotFoundError:
        return None
    except (OSError, ValueError) as exc:
        logger.warning("Falha lendo registro de propriedade '%s': %s", marker_path, exc)
    return None


def discard_full_rescan_artifact_marker(db_path: str, artifact_db_path: str) -> None:
    """Descarta somente um registro reconhecido apos mover/remover o artefato."""
    artifact = Path(artifact_db_path)
    if _read_full_rescan_marker(db_path, artifact) is None:
        return
    try:
        _full_rescan_marker_path(artifact).unlink(missing_ok=True)
    except OSError as exc:
        logger.warning("Falha removendo registro de propriedade '%s': %s", artifact, exc)


def prune_full_rescan_artifacts(
    db_path: str,
    *,
    keep: int = FULL_RESCAN_ARTIFACT_KEEP_COUNT,
    preserve: Optional[str] = None,
) -> None:
    """Remove artefatos antigos de full rescan, mantendo os `keep` mais recentes.

    Exige registro persistente e identidade atual; legado e orfaos sem
    identidade verificavel sao preservados. A chamada ocorre sob writer
    lock; `preserve` protege o candidato da rodada corrente.
    """
    parent = Path(os.path.dirname(db_path) or ".")
    base_name = os.path.basename(db_path)
    preserved = os.path.realpath(preserve) if preserve else None

    try:
        siblings = list(parent.iterdir())
    except OSError as exc:
        logger.warning("Falha ao listar artefatos de full rescan '%s': %s", parent, exc)
        return
    for marker in _FULL_RESCAN_ARTIFACT_MARKERS:
        prefix = f"{base_name}.{marker}"
        artifacts: list[tuple[float, Path]] = []
        for path in siblings:
            if (
                not path.name.startswith(prefix)
                or not _FULL_RESCAN_RUN_ID_RE.fullmatch(path.name[len(prefix):])
                or path.is_symlink()
                or not path.is_file()
                or os.path.realpath(path) == preserved
            ):
                continue
            record = _read_full_rescan_marker(db_path, path)
            if record is None:
                continue
            try:
                identity = path.stat()
            except OSError as exc:
                logger.warning("Falha validando artefato '%s': %s", path, exc)
                continue
            if (record.get("device"), record.get("inode")) != (
                identity.st_dev, identity.st_ino
            ):
                logger.warning("Artefato preservado por identidade alterada: %s", path)
                continue
            artifacts.append((identity.st_mtime, path))
        artifacts.sort(reverse=True)
        for _, stale in artifacts[max(0, keep):]:
            if any(Path(f"{stale}{suffix}").is_symlink() for suffix in _SQLITE_SIDECAR_SUFFIXES):
                logger.warning("Artefato preservado por sidecar simbolico: %s", stale)
                continue
            for suffix in (*_SQLITE_SIDECAR_SUFFIXES, ""):
                partial = Path(f"{stale}{suffix}")
                try:
                    partial.unlink(missing_ok=True)
                except OSError as exc:
                    logger.warning(
                        "Falha ao remover artefato antigo de full rescan '%s': %s",
                        partial,
                        exc,
                    )
                    break
            else:
                discard_full_rescan_artifact_marker(db_path, str(stale))
                logger.info(
                    "Artefato antigo de full rescan removido: %s", stale.name
                )


def promote_full_rescan_candidate(
    candidate_db_path: str, primary_db_path: str
) -> Optional[str]:
    """Promote a validated full-rescan candidate DB into the primary path."""
    with database_writer_lock(primary_db_path):
        return _promote_full_rescan_candidate_locked(candidate_db_path, primary_db_path)


def _promote_full_rescan_candidate_locked(
    candidate_db_path: str, primary_db_path: str
) -> Optional[str]:
    if not os.path.exists(candidate_db_path):
        raise DatabaseError(
            f"DB candidato ausente para promocao final: {candidate_db_path}"
        )

    logger.info(
        "Promovendo DB candidato de full rescan para principal: %s",
        os.path.basename(candidate_db_path),
    )
    ensure_wal_checkpointed(
        candidate_db_path,
        log_label="DB candidato de full rescan",
        busy_warning=(
            "Checkpoint WAL do DB candidato permaneceu ocupado; "
            "promocao vai preservar sidecars se existirem: %s"
        ),
        failure_message=(
            "WAL do DB candidato ainda ativo apos checkpoint; "
            "promocao bloqueada para evitar banco inconsistente."
        ),
        cleanup_sidecars=True,
    )

    backup_path: str | None = None
    original_mode: str | None = None
    if os.path.exists(primary_db_path):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        backup_path = f"{primary_db_path}.full_rescan_backup_{timestamp}"
        try:
            original_mode = snapshot_database_for_replace(primary_db_path, backup_path)
        except (OSError, sqlite3.Error) as exc:
            raise DatabaseError(
                f"Falha ao preparar backup antes da promocao: {exc}"
            ) from exc
        register_full_rescan_artifact(primary_db_path, backup_path)
    try:
        replace_sqlite_file_with_retry(candidate_db_path, primary_db_path)
    except OSError as exc:
        cleanup_errors: list[str] = []
        if original_mode is not None:
            try:
                restore_journal_mode(primary_db_path, original_mode)
            except (OSError, sqlite3.Error) as restore_exc:
                cleanup_errors.append(f"journal: {restore_exc}")
        if backup_path and not cleanup_errors:
            try:
                os.unlink(backup_path)
                discard_full_rescan_artifact_marker(primary_db_path, backup_path)
            except OSError as cleanup_exc:
                cleanup_errors.append(f"backup {backup_path}: {cleanup_exc}")
        if cleanup_errors:
            raise DatabaseError(
                "Falha ao promover DB candidato; principal preservado com "
                f"limpeza incompleta; backup em {backup_path}: "
                f"promocao={exc}; {'; '.join(cleanup_errors)}"
            ) from exc
        raise DatabaseError(
            "Falha ao promover DB candidato para o caminho principal: "
            f"{exc}"
        ) from exc
    discard_full_rescan_artifact_marker(primary_db_path, candidate_db_path)
    logger.info(
        "DB candidato promovido com sucesso para o caminho principal: %s",
        os.path.basename(primary_db_path),
    )
    return backup_path


def rotate_database_for_full_rescan(db_path: str) -> Optional[str]:
    """Rotate the current DB file to a timestamped backup and return the backup path."""
    with database_writer_lock(db_path):
        return _rotate_database_for_full_rescan_locked(db_path)


def _rotate_database_for_full_rescan_locked(db_path: str) -> Optional[str]:
    if not os.path.exists(db_path):
        return None
    logger.info("Preparando full rescan: checkpoint WAL e rotacao de banco.")
    # Inclui -journal: um rollback journal quente deixado por crash do banco
    # antigo nao pode ficar no caminho principal — apos a promocao o SQLite
    # o aplicaria sobre o banco NOVO, corrompendo-o.
    preexisting_sidecars = {
        suffix: os.path.exists(f"{db_path}{suffix}")
        for suffix in ("-wal", "-shm", "-journal")
    }
    ensure_wal_checkpointed(
        db_path,
        log_label="Banco de full rescan",
        busy_warning=(
            "Checkpoint WAL do full rescan permaneceu ocupado; "
            "rotacao sera bloqueada se o WAL ainda tiver dados: %s"
        ),
        failure_message=(
            "WAL ainda ativo apos checkpoint antes do full rescan; "
            "rotacao bloqueada para evitar backup inconsistente."
        ),
        validation_error_prefix="Falha ao validar estado do WAL antes do full rescan",
    )
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    backup_path = f"{db_path}.full_rescan_backup_{timestamp}"
    primary_moved = False
    moved_sidecars: list[tuple[str, str]] = []
    placeholder_sidecars: list[str] = []
    try:
        replace_sqlite_file_with_retry(db_path, backup_path)
        primary_moved = True
        logger.info(
            "Banco anterior movido para backup de full rescan: %s",
            os.path.basename(backup_path),
        )
        for suffix in ("-wal", "-shm", "-journal"):
            sidecar = f"{db_path}{suffix}"
            sidecar_backup = f"{backup_path}{suffix}"
            # Move pelo estado atual: um sidecar criado apos o snapshot
            # (ex.: journal de crash tardio) tambem precisa sair do caminho
            # principal antes da promocao do candidato.
            if os.path.exists(sidecar):
                replace_sqlite_file_with_retry(sidecar, sidecar_backup)
                moved_sidecars.append((sidecar, sidecar_backup))
                logger.info(
                    "Arquivo auxiliar do banco movido para backup: %s",
                    os.path.basename(sidecar_backup),
                )
                continue
            if preexisting_sidecars.get(suffix):
                Path(sidecar_backup).touch(exist_ok=True)
                placeholder_sidecars.append(sidecar_backup)
                logger.info(
                    "Arquivo auxiliar preexistente foi registrado vazio no backup "
                    "apos checkpoint consumir o sidecar: %s",
                    os.path.basename(sidecar_backup),
                )
    except OSError as exc:
        rollback_errors: list[str] = []
        if primary_moved and os.path.exists(backup_path):
            try:
                replace_sqlite_file_with_retry(backup_path, db_path)
            except OSError as rollback_exc:
                raise DatabaseError(
                    "Falha ao preparar banco limpo e ao restaurar o principal; "
                    f"arquivos de recuperacao preservados em {backup_path}: "
                    f"rotacao={exc}; restauracao={rollback_exc}"
                ) from exc
        for sidecar, sidecar_backup in reversed(moved_sidecars):
            if not os.path.exists(sidecar_backup):
                continue
            try:
                replace_sqlite_file_with_retry(sidecar_backup, sidecar)
            except OSError as rollback_exc:
                rollback_errors.append(
                    f"sidecar {os.path.basename(sidecar)}: {rollback_exc}"
                )
        for placeholder_sidecar in placeholder_sidecars:
            try:
                Path(placeholder_sidecar).unlink(missing_ok=True)
            except OSError as rollback_exc:
                rollback_errors.append(
                    f"placeholder {os.path.basename(placeholder_sidecar)}: {rollback_exc}"
                )
        rollback_detail = (
            f" Rollback incompleto: {'; '.join(rollback_errors)}"
            if rollback_errors
            else " Banco e sidecars restaurados."
        )
        raise DatabaseError(
            f"Falha ao preparar banco limpo para full rescan: {exc}.{rollback_detail}"
        ) from exc
    register_full_rescan_artifact(db_path, backup_path)
    return backup_path


def cleanup_sqlite_sidecars(db_path: str) -> None:
    """Remove sqlite sidecars for a detached database file when they exist."""
    for suffix in ("-wal", "-shm", "-journal"):
        sidecar = f"{db_path}{suffix}"
        if not os.path.exists(sidecar):
            continue
        os.remove(sidecar)
        logger.info(
            "Arquivo auxiliar temporario removido: %s", os.path.basename(sidecar)
        )


def ensure_wal_checkpointed(
    db_path: str,
    *,
    log_label: str,
    busy_warning: str,
    failure_message: str,
    validation_error_prefix: str = "Falha ao validar estado do WAL",
    cleanup_sidecars: bool = False,
) -> None:
    last_error = force_wal_checkpoint(db_path, log_label=log_label)
    if last_error is not None:
        logger.warning(busy_warning, last_error)
    if last_error is not None and os.path.exists(f"{db_path}-journal"):
        raise DatabaseError(failure_message) from last_error
    wal_path = f"{db_path}-wal"
    if not os.path.exists(wal_path):
        if cleanup_sidecars:
            cleanup_sqlite_sidecars(db_path)
        return
    try:
        wal_size = int(os.path.getsize(wal_path))
    except OSError as exc:
        raise DatabaseError(f"{validation_error_prefix}: {exc}") from exc
    if wal_size > 0:
        raise DatabaseError(failure_message)
    if cleanup_sidecars:
        cleanup_sqlite_sidecars(db_path)


def force_wal_checkpoint(db_path: str, *, log_label: str) -> Optional[Exception]:
    last_error: Optional[Exception] = None
    for attempt in range(1, 4):
        conn: Optional[sqlite3.Connection] = None
        try:
            conn = sqlite3.connect(db_path, timeout=2)
            conn.execute("PRAGMA busy_timeout = 2000")
            checkpoint = conn.execute("PRAGMA wal_checkpoint(TRUNCATE)").fetchone()
            if not checkpoint_is_fully_truncated(checkpoint):
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
                break
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


def checkpoint_is_fully_truncated(checkpoint: Any) -> bool:
    if not checkpoint or len(checkpoint) < 3:
        return False
    busy = int(checkpoint[SQLITE_CHECKPOINT_BUSY_INDEX] or 0)
    log_frames = int(checkpoint[SQLITE_CHECKPOINT_LOG_INDEX] or 0)
    checkpointed_frames = int(checkpoint[SQLITE_CHECKPOINT_CHECKPOINTED_INDEX] or 0)
    return busy == 0 and log_frames == checkpointed_frames


def replace_sqlite_file_with_retry(source: str, target: str) -> None:
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
