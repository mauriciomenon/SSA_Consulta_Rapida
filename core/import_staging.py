from __future__ import annotations

import os
import shutil
from pathlib import Path
from typing import Callable, Iterable, Sequence

from core.import_formats import SUPPORTED_IMPORT_SUFFIXES
from core.import_formats import supported_import_suffixes_text
from utils.path_safety import ensure_path_is_allowed, reserve_unique_path

CancelCallback = Callable[[], bool]
LineCallback = Callable[[str], None]


def _normalize_explicit_allowed_files(
    extra_allowed_files: Iterable[str | os.PathLike[str]] | None,
) -> set[Path]:
    if not extra_allowed_files:
        return set()
    allowed_files: set[Path] = set()
    for raw in extra_allowed_files:
        if not raw:
            continue
        candidate = Path(raw).expanduser()
        resolved = candidate.resolve(strict=False)
        if resolved.is_file():
            allowed_files.add(resolved)
    return allowed_files


def validate_external_source_path(
    raw_source: str | os.PathLike[str],
    *,
    extra_allowed_files: Iterable[str | os.PathLike[str]] | None = None,
    normalized_allowed_files: set[Path] | None = None,
) -> str:
    source = str(raw_source or "").strip()
    if not source:
        raise ValueError("Caminho vazio para staging externo.")
    if any(ch in source for ch in ("\x00", "\n", "\r")):
        raise ValueError("Caminho externo contem caracteres invalidos.")
    normalized = os.path.abspath(os.path.normpath(source))
    if os.path.basename(normalized).startswith("-"):
        raise ValueError("Caminho externo inicia com '-' e nao e permitido.")
    source_path = Path(normalized)
    try:
        safe_source_path = ensure_path_is_allowed(
            source_path,
            purpose="external_import_file",
            must_exist=True,
            expect_directory=False,
        )
    except ValueError as exc:
        if not source_path.exists():
            raise FileNotFoundError(f"Arquivo inexistente: {normalized}") from exc
        if not source_path.is_file():
            raise
        explicit_allowed_files = (
            normalized_allowed_files
            if normalized_allowed_files is not None
            else _normalize_explicit_allowed_files(extra_allowed_files)
        )
        resolved_source = source_path.resolve(strict=False)
        if resolved_source not in explicit_allowed_files:
            raise
        safe_source_path = resolved_source
    source_path = safe_source_path
    if source_path.suffix.casefold() not in SUPPORTED_IMPORT_SUFFIXES:
        raise ValueError(
            "Arquivo nao suportado pelo pipeline "
            f"({supported_import_suffixes_text()}): {source_path.name}"
        )
    return str(source_path)


def stage_external_import_files(
    *,
    project_root: str | os.PathLike[str],
    source_files: Sequence[str | os.PathLike[str]],
    should_cancel: CancelCallback | None = None,
    output_callback: LineCallback | None = None,
    error_callback: LineCallback | None = None,
) -> tuple[list[str], dict[str, int]]:
    project_root_path = Path(project_root).resolve()
    docs_path = ensure_path_is_allowed(
        project_root_path / "docs_entrada",
        purpose="explicit_import_docs_dir",
        base=project_root_path,
        must_exist=False,
        expect_directory=True,
    )
    docs_path.mkdir(parents=True, exist_ok=True)

    reserved_paths = {
        os.path.abspath(str(path)) for path in docs_path.iterdir() if path.is_file()
    }
    next_suffix_by_base: dict[str, int] = {}
    copied = 0
    skipped = 0
    failed = 0
    unsupported = 0
    staged_files: list[str] = []
    total_sources = len(source_files)
    explicit_allowed_files = _normalize_explicit_allowed_files(source_files)

    for index, raw_source in enumerate(tuple(source_files), start=1):
        if callable(should_cancel) and should_cancel():
            break
        source = str(raw_source or "").strip()
        if not source:
            skipped += 1
            continue
        if callable(output_callback):
            output_callback(
                f"[STAGE {index}/{total_sources}] Preparando: {os.path.basename(source) or source}"
            )
        try:
            validated_source = validate_external_source_path(
                source,
                normalized_allowed_files=explicit_allowed_files,
            )
        except FileNotFoundError:
            failed += 1
            if callable(error_callback):
                error_callback(f"[ERRO] Arquivo inexistente: {source}")
            continue
        except ValueError as exc:
            unsupported += 1
            if callable(output_callback):
                output_callback(f"[IGNORADO] {exc}")
            continue
        except (OSError, shutil.Error) as exc:
            failed += 1
            if callable(error_callback):
                error_callback(
                    f"[ERRO] Falha ao validar arquivo externo '{source}': {exc}"
                )
            continue

        base_name = os.path.basename(validated_source)
        base_destination = docs_path / base_name
        source_abs = os.path.abspath(validated_source)
        destination_abs = os.path.abspath(str(base_destination))
        if source_abs == destination_abs:
            staged_files.append(destination_abs)
            reserved_paths.add(destination_abs)
            continue

        destination = reserve_unique_path(
            base_destination,
            reserved_paths=reserved_paths,
            starting_index=next_suffix_by_base.get(destination_abs, 1),
        )
        destination_abs = os.path.abspath(destination)
        destination_name = Path(destination).stem
        base_name_stem = base_destination.stem
        prefix = f"{base_name_stem}__"
        if destination_name.startswith(prefix):
            raw_index = destination_name[len(prefix) :]
            if raw_index.isdigit():
                next_suffix_by_base[os.path.abspath(str(base_destination))] = (
                    int(raw_index) + 1
                )
        destination_created = False
        try:
            if callable(should_cancel) and should_cancel():
                break
            reserved_paths.add(destination_abs)
            source_fd = None
            source_stat = None
            try:
                source_fd = os.open(validated_source, os.O_RDONLY)
                source_stat = os.fstat(source_fd)
                with os.fdopen(source_fd, "rb") as source_handle:
                    source_fd = None
                    with open(destination, "xb") as destination_handle:
                        destination_created = True
                        shutil.copyfileobj(source_handle, destination_handle)
                os.chmod(destination, source_stat.st_mode & 0o600)
                os.utime(
                    destination,
                    ns=(source_stat.st_atime_ns, source_stat.st_mtime_ns),
                )
            finally:
                if source_fd is not None:
                    os.close(source_fd)
            if callable(should_cancel) and should_cancel():
                if destination_created:
                    try:
                        os.remove(destination)
                    except OSError as exc:
                        failed += 1
                        if callable(error_callback):
                            error_callback(
                                "[ERRO] Falha ao remover arquivo staged apos "
                                f"cancelamento '{destination}': {exc}"
                            )
                reserved_paths.discard(destination_abs)
                break
            copied += 1
            staged_files.append(destination)
        except (OSError, shutil.Error) as exc:
            failed += 1
            if destination_created:
                try:
                    os.remove(destination)
                except FileNotFoundError:
                    pass
                except OSError as cleanup_exc:
                    if callable(error_callback):
                        error_callback(
                            "[ERRO] Falha ao remover arquivo staged parcial "
                            f"'{destination}': {cleanup_exc}"
                        )
            reserved_paths.discard(destination_abs)
            if callable(error_callback):
                error_callback(
                    f"[ERRO] Falha ao copiar arquivo externo '{validated_source}': {exc}"
                )

    summary = {
        "copied": copied,
        "skipped": skipped,
        "failed": failed,
        "unsupported": unsupported,
        "staged": len(staged_files),
    }
    if callable(output_callback):
        output_callback(
            "Staging concluido: "
            f"copiados={copied}, ignorados={skipped}, "
            f"nao_suportados={unsupported}, falhas={failed}, staged={len(staged_files)}"
        )
    return staged_files, summary
