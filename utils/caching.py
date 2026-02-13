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
from contextlib import suppress
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
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            fd = None  # ownership transferred to file object
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
            with suppress(Exception):
                os.close(fd)
        if tmp_path:
            with suppress(Exception):
                os.remove(tmp_path)


def _safe_file_stat(file_path: str) -> Optional[Tuple[int, int]]:
    """Return (size, mtime_ns) for a file, or None if stat fails."""
    try:
        st = os.stat(file_path)
    except OSError as exc:
        logger.warning("Falha ao acessar metadados de '%s': %s", file_path, exc)
        return None

    mtime_ns = getattr(st, "st_mtime_ns", int(st.st_mtime * 1_000_000_000))
    return int(st.st_size), int(mtime_ns)

def get_all_xlsx_files(directory: str) -> List[str]:
    """Obtem todos os arquivos .xlsx em um diretorio."""
    xlsx_files = []
    if os.path.exists(directory):
        for filename in os.listdir(directory):
            if filename.endswith('.xlsx'):
                xlsx_files.append(os.path.join(directory, filename))
    logger.debug(f"Encontrados {len(xlsx_files)} arquivos .xlsx em '{directory}'.")
    return xlsx_files

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

def get_files_to_process(docs_dir: str, cache_or_path: Union[str, Dict[str, Any]]) -> List[str]:
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

    all_xlsx_files = get_all_xlsx_files(docs_dir)

    files_to_process = []
    for file_path in all_xlsx_files:
        filename = os.path.basename(file_path)
        stat_sig = _safe_file_stat(file_path)
        if stat_sig is None:
            continue
        size, mtime_ns = stat_sig

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
                "Hash não pôde ser calculado para %s; reenfileirando para processamento para evitar perda silenciosa.",
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
        if updated_cache.get(filename) != new_entry:
            updated_cache[filename] = new_entry
            cache_updated = True

    logger.info(f"{len(files_to_process)} arquivo(s) identificado(s) para processamento (novos ou modificados).")

    # Persist cache upgrades even when nothing is imported, so subsequent runs can
    # avoid hashing every file.
    if cache_file_path and cache_updated:
        save_cache(updated_cache, cache_file_path)
    return files_to_process

def update_cache_for_files(file_paths: List[str], cache_file: str):
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
        stat_sig = _safe_file_stat(file_path)
        if stat_sig is None:
            continue
        size, mtime_ns = stat_sig
        file_hash = _calculate_hash(file_path)
        if file_hash: # Só atualiza se o hash foi calculado com sucesso
            current_cache[filename] = {"sha256": file_hash, "size": size, "mtime_ns": mtime_ns}
            updated = True
        else:
            logger.warning(f"Não foi possível atualizar o cache para {file_path} (hash falhou).")

    if updated:
        save_cache(current_cache, cache_file)
