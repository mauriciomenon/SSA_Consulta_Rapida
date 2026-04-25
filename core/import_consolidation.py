from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Callable

from utils.path_safety import ensure_path_is_allowed, reserve_unique_path

ProgressCallback = Callable[[int, str], None]
LineCallback = Callable[[str], None]
CancelCallback = Callable[[], bool]

_MUTATION_FIELDS = (
    "rows_inserted",
    "rows_updated",
    "rows_changed",
    "rows_ready_for_insert",
)
_SUCCESS_STATUSES = {"", "success", "no_rows"}


def resolve_latest_project_import_report(
    *,
    project_root: str | os.PathLike[str],
    docs_path: str | os.PathLike[str],
) -> dict[str, Any] | None:
    project_root_path = Path(project_root).resolve()
    safe_docs_path = ensure_path_is_allowed(
        docs_path,
        purpose="consolidation_docs_dir",
        base=project_root_path,
        must_exist=True,
        expect_directory=True,
    )
    logs_dir = ensure_path_is_allowed(
        project_root_path / "logs",
        purpose="consolidation_logs_dir",
        base=project_root_path,
        must_exist=False,
        expect_directory=True,
    )
    if not logs_dir.is_dir():
        return None
    report_paths: list[Path] = [
        logs_dir / name
        for name in os.listdir(logs_dir)
        if name.startswith("import_run_") and name.endswith(".json")
    ]
    report_paths.sort(key=lambda report_path: report_path.stat().st_mtime, reverse=True)
    docs_abs = os.path.normcase(
        os.path.abspath(os.path.normpath(str(safe_docs_path.resolve())))
    )
    for report_path in report_paths:
        payload = None
        try:
            with report_path.open("r", encoding="utf-8") as handle:
                payload = json.load(handle)
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            continue
        if not isinstance(payload, dict):
            continue
        payload_docs = str((payload.get("paths") or {}).get("docs_dir") or "")
        payload_docs_path = Path(payload_docs).expanduser()
        if not payload_docs_path.is_absolute():
            payload_docs_path = project_root_path / payload_docs_path
        try:
            paths_match = (
                payload_docs_path.exists()
                and safe_docs_path.exists()
                and payload_docs_path.samefile(safe_docs_path)
            )
        except OSError:
            paths_match = False
        if not paths_match:
            payload_docs_abs = os.path.normcase(
                os.path.abspath(os.path.normpath(str(payload_docs_path.resolve())))
            )
            if payload_docs_abs != docs_abs:
                continue
        file_reports = payload.get("file_reports") or []
        if isinstance(file_reports, list) and file_reports:
            payload["_report_path"] = str(report_path)
            return payload
    return None


def consolidate_input_files(
    *,
    project_root: str | os.PathLike[str],
    docs_subdir: str = "docs_entrada",
    should_cancel: CancelCallback | None = None,
    progress_callback: ProgressCallback | None = None,
    output_callback: LineCallback | None = None,
    error_callback: LineCallback | None = None,
) -> dict[str, Any]:
    project_root_path = Path(project_root).resolve()
    docs_path = ensure_path_is_allowed(
        project_root_path / docs_subdir,
        purpose="consolidation_docs_dir",
        base=project_root_path,
        must_exist=True,
        expect_directory=True,
    )
    report = resolve_latest_project_import_report(
        project_root=project_root_path,
        docs_path=docs_path,
    )
    if report is None:
        raise RuntimeError(
            "Nenhum import_run com file_reports para docs_entrada foi encontrado."
        )

    processadas_dir = docs_path / "processadas"
    nosurvivor_dir = processadas_dir / "nosurvivor"
    try:
        processadas_dir.mkdir(parents=True, exist_ok=True)
        nosurvivor_dir.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        message = f"Falha ao preparar diretorios de consolidacao: {exc}"
        if callable(error_callback):
            error_callback(message)
        raise RuntimeError(message) from exc

    file_rows: dict[str, dict[str, int | str]] = {}
    for entry in report.get("file_reports", []):
        if not isinstance(entry, dict):
            continue
        file_name = str(entry.get("file") or "").strip()
        if not file_name:
            continue
        status = str(entry.get("status") or "").strip().casefold()
        counts = entry.get("counts") or {}
        file_rows[file_name] = {
            "status": status,
            "rows_inserted": int((counts.get("rows_inserted", 0) or 0)),
            "rows_updated": int((counts.get("rows_updated", 0) or 0)),
            "rows_changed": int((counts.get("rows_changed", 0) or 0)),
            "rows_ready_for_insert": int(
                counts.get("rows_ready_for_insert", counts.get("rows_inserted", 0)) or 0
            ),
        }

    candidate_files = [
        name
        for name in os.listdir(docs_path)
        if (docs_path / name).is_file() and name.casefold().endswith((".xlsx", ".xls"))
    ]
    moved = 0
    moved_nosurvivor = 0
    pending = 0
    failed = 0
    total_files = len(candidate_files)

    for index, base_name in enumerate(candidate_files, start=1):
        if callable(should_cancel) and should_cancel():
            raise RuntimeError("Processo cancelado pelo usuario")
        if callable(progress_callback):
            progress_callback(
                int(10 + ((index / max(total_files, 1)) * 80)),
                f"Consolidando arquivo {index}/{max(total_files, 1)}",
            )
        source_path = docs_path / base_name
        if base_name not in file_rows:
            pending += 1
            continue
        file_meta = file_rows.get(base_name, {})
        status = str(file_meta.get("status") or "").casefold()
        has_mutation = any(
            int(file_meta.get(name, 0) or 0) > 0 for name in _MUTATION_FIELDS
        )
        is_success_status = status in _SUCCESS_STATUSES
        is_zero_survivor = is_success_status and not has_mutation
        if not is_success_status:
            pending += 1
            continue
        target_dir = nosurvivor_dir if is_zero_survivor else processadas_dir
        destination = ""
        try:
            destination = reserve_unique_path(target_dir / base_name, touch=True)
            os.replace(source_path, destination)
            moved += 1
            if target_dir == nosurvivor_dir:
                moved_nosurvivor += 1
            if callable(output_callback):
                output_callback(f"[OK] Consolidado: {base_name}")
        except OSError as exc:
            move_error: BaseException = exc
            if destination and os.path.exists(destination):
                try:
                    os.remove(destination)
                except OSError as cleanup_exc:
                    move_error = RuntimeError(
                        "Falha ao mover arquivo e limpar reserva "
                        f"'{destination}': {exc}; cleanup={cleanup_exc}"
                    )
            failed += 1
            if callable(error_callback):
                error_callback(
                    "[ERRO] Falha ao mover arquivo na consolidacao "
                    f"'{source_path}': {move_error}"
                )

    if callable(output_callback):
        output_callback(
            "Consolidacao concluida: "
            f"movidos={moved}, nosurvivor={moved_nosurvivor}, pendentes={pending}, falhas={failed}"
        )

    return {
        "moved": moved,
        "nosurvivor": moved_nosurvivor,
        "pending": pending,
        "failed": failed,
        "report_path": str(report.get("_report_path", "")),
    }
