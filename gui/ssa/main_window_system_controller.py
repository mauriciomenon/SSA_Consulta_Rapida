"""System/config operations for the main SSA window."""

from __future__ import annotations

import os
import re
import shutil
from datetime import datetime
from typing import Any, Callable

from core.config_defaults import default_settings_payload
from core.config_manager import atomic_write_json_file
from core.config_manager import ensure_default_settings
from core.config_manager import load_default_settings_payload
from core.config_manager import resolve_user_settings_path
from core.import_staging import _normalize_explicit_allowed_files
from core.import_staging import validate_external_source_path
from gui.ssa import database_operations
from gui.ssa import gui_preferences_persistence
from gui.ssa import system_integration

SEARCH_DEBOUNCE_DEFAULT_MS = 250
SEARCH_DEBOUNCE_MIN_MS = 100
SEARCH_DEBOUNCE_MAX_MS = 5000


def resolve_search_debounce_ms(settings: dict[str, Any], *, logger: Any) -> int:
    raw_delay = settings.get("debounce_delay", SEARCH_DEBOUNCE_DEFAULT_MS)
    try:
        delay = int(raw_delay)
    except (TypeError, ValueError) as exc:
        logger.warning(
            "Valor invalido para debounce_delay nas preferencias (%s); usando fallback %s ms.",
            exc,
            SEARCH_DEBOUNCE_DEFAULT_MS,
        )
        delay = SEARCH_DEBOUNCE_DEFAULT_MS
    return min(max(delay, SEARCH_DEBOUNCE_MIN_MS), SEARCH_DEBOUNCE_MAX_MS)


def queue_gui_preferences_write(gui_prefs: dict[str, Any]) -> bool:
    return gui_preferences_persistence.persist_gui_preferences_async(gui_prefs)


def build_sam_ssa_url(numero_ssa: str) -> str:
    return system_integration.build_sam_ssa_url(numero_ssa)


def open_allowed_url(
    url: str,
    *,
    qdesktopservices: Any,
    qurl_cls: Any,
    logger: Any,
) -> bool:
    return system_integration.open_allowed_url(
        url,
        qdesktopservices=qdesktopservices,
        qurl_cls=qurl_cls,
        logger=logger,
    )


def open_sam_home(
    *,
    qdesktopservices: Any,
    qurl_cls: Any,
    logger: Any,
) -> bool:
    return open_allowed_url(
        system_integration.SAM_HOME_URL,
        qdesktopservices=qdesktopservices,
        qurl_cls=qurl_cls,
        logger=logger,
    )


def open_sam_ssa(
    numero_ssa: str,
    *,
    qdesktopservices: Any,
    qurl_cls: Any,
    logger: Any,
) -> tuple[bool, str]:
    safe_numero = str(numero_ssa or "").strip()
    if not re.fullmatch(r"[A-Za-z0-9]+", safe_numero):
        logger.warning("Numero SSA invalido para URL SAM: %s", safe_numero)
        return False, safe_numero
    sam_url = build_sam_ssa_url(safe_numero)
    opened = open_allowed_url(
        sam_url,
        qdesktopservices=qdesktopservices,
        qurl_cls=qurl_cls,
        logger=logger,
    )
    return opened, safe_numero


def resolve_settings_file_path(project_root: str) -> str:
    _ = project_root
    return resolve_user_settings_path()


def validate_project_open_target(
    project_root: str,
    target_path: str,
    *,
    must_exist: bool,
    expect_dir: bool | None,
    allowed_base: str | list[str] | tuple[str, ...] | None = None,
) -> str:
    safe_bases = _normalize_allowed_bases(project_root, allowed_base)
    if not safe_bases:
        raise ValueError("Base permitida obrigatoria para caminho local.")
    return system_integration.validate_local_open_target(
        target_path,
        must_exist=must_exist,
        expect_dir=expect_dir,
        allowed_base=safe_bases,
    )


def _normalize_allowed_bases(
    project_root: str,
    allowed_base: str | list[str] | tuple[str, ...] | None,
) -> tuple[str, ...]:
    if allowed_base is None:
        return (os.path.realpath(os.path.normpath(project_root)),)
    raw_bases = [allowed_base] if isinstance(allowed_base, str) else list(allowed_base)
    safe_bases = []
    for raw_base in raw_bases:
        if raw_base is None:
            continue
        candidate = str(raw_base).strip()
        if not candidate:
            continue
        safe_bases.append(os.path.realpath(os.path.normpath(candidate)))
    if not safe_bases:
        return ()
    return tuple(dict.fromkeys(safe_bases))


def prepare_settings_file_for_edit(
    project_root: str,
    *,
    settings_path: str | None = None,
) -> dict[str, Any]:
    settings_path = os.path.abspath(settings_path or resolve_settings_file_path(project_root))
    os.makedirs(os.path.dirname(settings_path), exist_ok=True)
    created_settings = False
    if not os.path.exists(settings_path):
        atomic_write_json_file(settings_path, _load_default_settings(project_root))
        created_settings = True
    if created_settings:
        return {
            "ok": True,
            "settings_path": settings_path,
            "backup_path": "",
            "backup_created": False,
        }
    backup_path = _copy_timestamped_backup(settings_path)
    backup_created = bool(backup_path) and os.path.exists(backup_path)
    if not backup_created:
        raise FileNotFoundError(f"Backup de opcoes nao criado para: {settings_path}")
    return {
        "ok": True,
        "settings_path": settings_path,
        "backup_path": backup_path,
        "backup_created": backup_created,
    }


def reset_settings_file_to_defaults(
    project_root: str,
    *,
    settings_path: str | None = None,
) -> dict[str, Any]:
    settings_path = os.path.abspath(settings_path or resolve_settings_file_path(project_root))
    os.makedirs(os.path.dirname(settings_path), exist_ok=True)
    default_settings = _load_default_settings(project_root)
    backup_path = ""
    backup_created = False
    if os.path.exists(settings_path):
        backup_path = _copy_timestamped_backup(settings_path)
        backup_created = bool(backup_path)
        if not backup_created:
            raise OSError(f"Backup de opcoes nao criado para: {settings_path}")
    atomic_write_json_file(settings_path, default_settings)
    return {
        "ok": True,
        "settings_path": settings_path,
        "backup_created": backup_created,
        "backup_path": backup_path,
    }


def open_local_path(
    target_path: str,
    *,
    qdesktopservices: Any,
    qurl_cls: Any,
    qt_available: bool,
    logger: Any,
) -> bool:
    return system_integration.open_local_path_non_blocking(
        target_path,
        qdesktopservices=qdesktopservices,
        qurl_cls=qurl_cls,
        qt_available=qt_available,
        logger=logger,
    )


def execute_vacuum_analyze(
    db_path: str,
    vacuum_analyze_database_fn: Callable[[str], dict[str, Any]],
) -> dict[str, Any]:
    return database_operations.execute_vacuum_analyze(db_path, vacuum_analyze_database_fn)


def prepare_external_import_selection(
    selected_files: list[str] | tuple[str, ...],
    *,
    logger: Any,
) -> dict[str, Any]:
    skipped = 0
    failed = 0
    unsupported = 0
    safe_selected_files: list[str] = []
    explicit_allowed_files = _normalize_explicit_allowed_files(selected_files)
    for raw_source in selected_files:
        source = str(raw_source or "").strip()
        if not source:
            skipped += 1
            continue
        try:
            validated_source = validate_external_source_path(
                source,
                normalized_allowed_files=explicit_allowed_files,
            )
        except ValueError as exc:
            logger.info(
                "Importacao externa ignorou arquivo nao suportado ou invalido '%s': %s",
                source,
                exc,
            )
            unsupported += 1
            continue
        except Exception as exc:
            logger.warning(
                "Importacao externa rejeitou caminho invalido '%s': %s",
                source,
                exc,
            )
            failed += 1
            continue
        safe_selected_files.append(validated_source)
    return {
        "safe_selected_files": safe_selected_files,
        "skipped": skipped,
        "failed": failed,
        "unsupported": unsupported,
    }


def _copy_timestamped_backup(path: str) -> str:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    backup_path = f"{path}.bak_{timestamp}"
    try:
        shutil.copy2(path, backup_path)
    except OSError:
        return ""
    return backup_path


def _load_default_settings(project_root: str) -> dict[str, Any]:
    _ = project_root
    ensure_default_settings(fail_fast=False)
    try:
        return load_default_settings_payload()
    except FileNotFoundError:
        return dict(default_settings_payload())
