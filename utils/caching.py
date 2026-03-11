# utils/caching.py 20250725 110000 (v2.1 - Leitura em Blocos, Logging)
"""
Utilitários para gerenciamento de cache de arquivos, baseado em hashes.

Usado para determinar se arquivos Excel foram modificados desde a última importação.
"""

import os
import json
import hashlib
import logging
import tempfile
from pathlib import Path
from typing import List, Dict, Union, Any, Optional, Tuple

logger = logging.getLogger(__name__)

def _atomic_write_json(cache: Dict[str, Any], cache_file: str) -> None:
    """Write JSON atomically to avoid corrupted/truncated cache files.

    This protects against crashes mid-write and reduces risk when multiple runs
    touch the same cache file.
    """
    target_dir = os.path.dirname(cache_file) or "."
    base_name = os.path.basename(cache_file) or "cache.json"
    os.makedirs(target_dir, exist_ok=True)

    fd = None
    tmp_path = None
    try:
        fd, tmp_path = tempfile.mkstemp(prefix=f".{base_name}.tmp.", dir=target_dir)
        # Close raw descriptor before reopen to avoid leaks on fdopen/open errors.
        os.close(fd)
        fd = None
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(cache, f, indent=4)
            f.flush()
            try:
                os.fsync(f.fileno())
            except OSError as exc:
                logger.debug("fsync failed for cache temp file (%s): %s", tmp_path, exc)
        os.replace(tmp_path, cache_file)
        tmp_path = None
    finally:
        if fd is not None:
            try:
                os.close(fd)
            except OSError as exc:
                logger.warning("Failed to close cache temp file descriptor for '%s': %s", cache_file, exc)
        if tmp_path:
            try:
                os.remove(tmp_path)
            except OSError as exc:
                logger.warning("Failed to remove cache temp file '%s': %s", tmp_path, exc)


def _safe_file_stat(file_path: str) -> Optional[Tuple[int, int]]:
    """Return (size, mtime_ns) for a file, or None if stat fails."""
    try:
        st = os.stat(file_path)
    except OSError as exc:
        logger.warning("Falha ao acessar metadados de '%s': %s", file_path, exc)
        return None

    mtime_ns = getattr(st, "st_mtime_ns", int(st.st_mtime * 1_000_000_000))
    return int(st.st_size), int(mtime_ns)

def _cache_key_for_file(file_path: str, docs_dir: str) -> str:
    """Return a stable cache key using the relative path inside docs_dir."""
    try:
        rel_path = Path(file_path).resolve().relative_to(Path(docs_dir).resolve())
        return rel_path.as_posix()
    except (ValueError, OSError, RuntimeError) as exc:
        logger.debug(
            "Fallback cache key by basename for '%s' (docs_dir='%s'): %s",
            file_path,
            docs_dir,
            exc,
        )
        return os.path.basename(file_path)


def get_all_xlsx_files(
    directory: str,
    *,
    include_processadas: bool = False,
    processadas_subdir: str = "processadas",
    ignore_subdirs: Optional[List[str]] = None,
) -> List[str]:
    """Obtem arquivos .xlsx no diretorio raiz e, opcionalmente, em processadas."""
    xlsx_files: list[str] = []
    if not os.path.exists(directory):
        logger.debug("Diretorio '%s' nao existe para descoberta de .xlsx.", directory)
        return xlsx_files

    for filename in os.listdir(directory):
        file_path = os.path.join(directory, filename)
        lowered = filename.casefold()
        if os.path.isfile(file_path) and lowered.endswith(".xlsx"):
            xlsx_files.append(file_path)

    if include_processadas:
        processadas_dir = os.path.join(directory, processadas_subdir)
        ignored = {
            name.strip().casefold()
            for name in (ignore_subdirs or [])
            if name and name.strip()
        }
        if os.path.isdir(processadas_dir):
            for root, dirnames, filenames in os.walk(processadas_dir):
                if dirnames:
                    dirnames[:] = [
                        dirname for dirname in dirnames
                        if dirname.strip().casefold() not in ignored
                    ]
                for filename in filenames:
                    if filename.casefold().endswith(".xlsx"):
                        xlsx_files.append(os.path.join(root, filename))

    # Deterministic ordering for stable runs and tests.
    xlsx_files = sorted({os.path.abspath(path) for path in xlsx_files})
    logger.debug(
        "Encontrados %s arquivo(s) .xlsx em '%s' (include_processadas=%s).",
        len(xlsx_files),
        directory,
        include_processadas,
    )
    return xlsx_files


def get_ignored_legacy_excel_files(directory: str) -> List[str]:
    """Lista arquivos .xls presentes, mas explicitamente ignorados pelo pipeline principal."""
    legacy_xls_files: List[str] = []
    if os.path.exists(directory):
        for filename in os.listdir(directory):
            if filename.casefold().endswith(".xls"):
                legacy_xls_files.append(os.path.join(directory, filename))
    logger.debug(
        "Encontrados %s arquivo(s) .xls ignorado(s) em '%s'.",
        len(legacy_xls_files),
        directory,
    )
    return sorted(legacy_xls_files)

def _calculate_hash(file_path: str, block_size: int = 65536) -> str:
    """
    Calcula o hash SHA-256 de um arquivo lendo-o em blocos.

    Args:
        file_path (str): Caminho para o arquivo.
        block_size (int): Tamanho do bloco de leitura em bytes.

    Returns:
        str: O hash hexadecimal do arquivo.
    """
    logger.debug(f"Calculando hash para '{file_path}'...")
    hash_sha256 = hashlib.sha256()
    try:
        with open(file_path, 'rb') as f:
            # Lê o arquivo em blocos para eficiência de memória
            for chunk in iter(lambda: f.read(block_size), b""):
                hash_sha256.update(chunk)
        file_hash = hash_sha256.hexdigest()
        logger.debug(f"Hash calculado para '{file_path}': {file_hash}")
        return file_hash
    except IOError as e:
        logger.error(f"Erro ao ler o arquivo {file_path} para hashing: {e}")
        return ""

def load_cache(cache_file: str) -> Dict[str, Any]:
    """Carrega o cache de um arquivo JSON."""
    if not os.path.exists(cache_file):
        logger.debug(f"Arquivo de cache '{cache_file}' não encontrado.")
        return {}
    try:
        with open(cache_file, 'r', encoding='utf-8') as f:
            cache = json.load(f)
        logger.debug(f"Cache carregado com {len(cache)} entradas.")
        return cache
    except (json.JSONDecodeError, UnicodeDecodeError, IOError) as e:
        logger.warning(f"Erro ao carregar cache de '{cache_file}': {e}. Iniciando novo cache.")
        return {}

def save_cache(cache: Dict[str, Any], cache_file: str):
    """Salva o cache em um arquivo JSON."""
    try:
        _atomic_write_json(cache, cache_file)
        logger.debug(f"Cache salvo em '{cache_file}'.")
    except Exception as e:  # noqa: BLE001
        # Cache nao eh critico para a importacao; nao deve derrubar o processo.
        # Ainda assim, logamos o erro para diagnostico.
        logger.exception("Erro ao salvar cache em '%s': %s", cache_file, e)

def get_files_to_process(
    docs_dir: str,
    cache_or_path: Union[str, Dict[str, Any]],
    *,
    include_processadas: bool = False,
    processadas_subdir: str = "processadas",
    ignore_subdirs: Optional[List[str]] = None,
) -> List[str]:
    """
    Compara hashes atuais com o cache para determinar arquivos modificados/novos.

    Returns:
        List[str]: Lista de caminhos completos para arquivos que precisam ser processados.
    """
    logger.debug("Iniciando comparação de arquivos com cache...")
    # Aceita tanto um caminho para cache (str) quanto um dicionario ja carregado
    cache_file_path = None
    if isinstance(cache_or_path, dict):
        current_cache: Dict[str, Any] = cache_or_path
    else:
        cache_file_path = cache_or_path
        current_cache = load_cache(cache_or_path)

    # Avoid mutating the caller-provided cache dict.
    updated_cache: Dict[str, Any] = dict(current_cache)
    cache_updated = False

    all_xlsx_files = get_all_xlsx_files(
        docs_dir,
        include_processadas=include_processadas,
        processadas_subdir=processadas_subdir,
        ignore_subdirs=ignore_subdirs,
    )

    files_to_process = []
    for file_path in all_xlsx_files:
        filename = os.path.basename(file_path)
        file_cache_key = _cache_key_for_file(file_path, docs_dir)
        stat_sig = _safe_file_stat(file_path)
        if stat_sig is None:
            logger.warning(
                "Metadados indisponiveis para '%s'; reenfileirando para processamento.",
                file_path,
            )
            files_to_process.append(file_path)
            continue
        size, mtime_ns = stat_sig

        cached_entry = current_cache.get(file_cache_key)
        if cached_entry is None and file_cache_key != filename:
            cached_entry = current_cache.get(filename)
        if cached_entry is None:
            files_to_process.append(file_path)
            continue

        cached_sha = None
        cached_size = None
        cached_mtime_ns = None
        if isinstance(cached_entry, str):
            cached_sha = cached_entry
        elif isinstance(cached_entry, dict):
            sha_val = cached_entry.get("sha256")
            size_val = cached_entry.get("size")
            mtime_val = cached_entry.get("mtime_ns")
            if isinstance(sha_val, str):
                cached_sha = sha_val
            if isinstance(size_val, int):
                cached_size = size_val
            if isinstance(mtime_val, int):
                cached_mtime_ns = mtime_val

        # Fast path: metadata matches and we have a sha.
        if (
            isinstance(cached_sha, str)
            and cached_sha
            and cached_size is not None
            and cached_mtime_ns is not None
            and cached_size == size
            and cached_mtime_ns == mtime_ns
        ):
            continue

        current_hash = _calculate_hash(file_path)
        if not current_hash:
            logger.warning(
                "Hash nao pode ser calculado para %s; reenfileirando para processamento para evitar perda silenciosa.",
                file_path,
            )
            files_to_process.append(file_path)
            continue

        if not cached_sha:
            files_to_process.append(file_path)
            continue

        if current_hash != cached_sha:
            files_to_process.append(file_path)
            continue

        # Hash matches: refresh cache entry with metadata for future fast paths.
        new_entry = {"sha256": current_hash, "size": size, "mtime_ns": mtime_ns}
        if updated_cache.get(file_cache_key) != new_entry:
            updated_cache[file_cache_key] = new_entry
            cache_updated = True

    logger.info(f"{len(files_to_process)} arquivo(s) identificado(s) para processamento (novos ou modificados).")

    # Persist cache upgrades even when nothing is imported, so subsequent runs can
    # avoid hashing every file.
    if cache_file_path and cache_updated:
        save_cache(updated_cache, cache_file_path)
    return files_to_process

def update_cache_for_files(file_paths: List[str], cache_file: str, docs_dir: Optional[str] = None):
    """
    Atualiza o cache com os hashes dos arquivos processados com sucesso.

    Args:
        file_paths (List[str]): Lista de caminhos completos dos arquivos processados.
        cache_file (str): Caminho para o arquivo de cache.
    """
    logger.debug("Atualizando cache para arquivos processados...")
    current_cache = load_cache(cache_file)

    updated = False
    for file_path in file_paths:
        filename = os.path.basename(file_path)
        file_cache_key = _cache_key_for_file(file_path, docs_dir) if docs_dir else filename
        stat_sig = _safe_file_stat(file_path)
        if stat_sig is None:
            continue
        size, mtime_ns = stat_sig
        file_hash = _calculate_hash(file_path)
        if file_hash: # Só atualiza se o hash foi calculado com sucesso
            current_cache[file_cache_key] = {"sha256": file_hash, "size": size, "mtime_ns": mtime_ns}
            updated = True
        else:
            logger.warning(f"Nao foi possivel atualizar o cache para {file_path} (hash falhou).")

    if updated:
        save_cache(current_cache, cache_file)
