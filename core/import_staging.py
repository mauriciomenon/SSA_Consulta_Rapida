from __future__ import annotations

import os
import shutil
from pathlib import Path
from typing import Callable, Sequence

from utils.path_safety import ensure_path_is_allowed

CancelCallback = Callable[[], bool]
LineCallback = Callable[[str], None]


def build_unique_destination_path(
    destination_path: str | os.PathLike[str],
    *,
    reserved_paths: set[str] | None = None,
    starting_index: int = 1,
) -> str:
    destination = str(destination_path)
    normalized_destination = os.path.abspath(destination)
    if reserved_paths is not None:
        if normalized_destination not in reserved_paths and not os.path.exists(
            destination
        ):
            reserved_paths.add(normalized_destination)
            return destination
    elif not os.path.exists(destination):
        return destination

    base, ext = os.path.splitext(destination)
    idx = max(int(starting_index), 1)
    max_attempts = 10000
    while idx <= max_attempts:
        candidate = f"{base}__{idx}{ext}"
        normalized_candidate = os.path.abspath(candidate)
        if reserved_paths is not None:
            if normalized_candidate not in reserved_paths and not os.path.exists(
                candidate
            ):
                reserved_paths.add(normalized_candidate)
                return candidate
        elif not os.path.exists(candidate):
            return candidate
        idx += 1
    raise RuntimeError(
        f"Nao foi possivel gerar nome unico apos {max_attempts} tentativas: {destination}"
    )


def validate_external_source_path(raw_source: str | os.PathLike[str]) -> str:
    source = str(raw_source or "").strip()
    if not source:
        raise ValueError("Caminho vazio para staging externo.")
    if any(ch in source for ch in ("\x00", "\n", "\r")):
        raise ValueError("Caminho externo contem caracteres invalidos.")
    normalized = os.path.abspath(os.path.normpath(source))
    if os.path.basename(normalized).startswith("-"):
        raise ValueError("Caminho externo inicia com '-' e nao e permitido.")
    source_path = Path(normalized)
    if not source_path.is_file():
        raise FileNotFoundError(f"Arquivo inexistente: {normalized}")
    if source_path.suffix.casefold() not in {".xlsx", ".xls"}:
        raise ValueError(f"Arquivo nao suportado pelo pipeline: {source_path.name}")
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
            validated_source = validate_external_source_path(source)
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
        except Exception as exc:
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

        destination = build_unique_destination_path(
            base_destination,
            reserved_paths=reserved_paths,
            starting_index=next_suffix_by_base.get(destination_abs, 1),
        )
        destination_name = Path(destination).stem
        base_name_stem = base_destination.stem
        prefix = f"{base_name_stem}__"
        if destination_name.startswith(prefix):
            raw_index = destination_name[len(prefix) :]
            if raw_index.isdigit():
                next_suffix_by_base[destination_abs] = int(raw_index) + 1
        try:
            if callable(should_cancel) and should_cancel():
                break
            shutil.copy2(validated_source, destination)
            if callable(should_cancel) and should_cancel():
                try:
                    os.remove(destination)
                    reserved_paths.discard(os.path.abspath(destination))
                except OSError:
                    pass
                break
            copied += 1
            staged_files.append(destination)
        except Exception as exc:
            failed += 1
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
