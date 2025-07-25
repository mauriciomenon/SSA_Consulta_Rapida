# utils/caching.py 20250725 110000 (v2.1 - Leitura em Blocos, Logging)
"""
Utilitários para gerenciamento de cache de arquivos, baseado em hashes.

Usado para determinar se arquivos Excel foram modificados desde a última importação.
"""

import os
import json
import hashlib
import logging
from typing import List, Dict, Set

logger = logging.getLogger(__name__)

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

def load_cache(cache_file: str) -> Dict[str, str]:
    """Carrega o cache de um arquivo JSON."""
    if not os.path.exists(cache_file):
        logger.debug(f"Arquivo de cache '{cache_file}' não encontrado.")
        return {}
    try:
        with open(cache_file, 'r') as f:
            cache = json.load(f)
        logger.debug(f"Cache carregado com {len(cache)} entradas.")
        return cache
    except (json.JSONDecodeError, IOError) as e:
        logger.warning(f"Erro ao carregar cache de '{cache_file}': {e}. Iniciando novo cache.")
        return {}

def save_cache(cache: Dict[str, str], cache_file: str):
    """Salva o cache em um arquivo JSON."""
    try:
        os.makedirs(os.path.dirname(cache_file), exist_ok=True)
        with open(cache_file, 'w') as f:
            json.dump(cache, f, indent=4)
        logger.debug(f"Cache salvo em '{cache_file}'.")
    except IOError as e:
        logger.error(f"Erro ao salvar cache em '{cache_file}': {e}")

def get_files_to_process(docs_dir: str, cache_file: str) -> List[str]:
    """
    Compara hashes atuais com o cache para determinar arquivos modificados/novos.
    
    Returns:
        List[str]: Lista de caminhos completos para arquivos que precisam ser processados.
    """
    logger.debug("Iniciando comparação de arquivos com cache...")
    current_cache = load_cache(cache_file)
    all_xlsx_files = get_all_xlsx_files(docs_dir)
    
    files_to_process = []
    for file_path in all_xlsx_files:
        filename = os.path.basename(file_path)
        current_hash = _calculate_hash(file_path)
        
        if not current_hash:
            logger.warning(f"Hash não pôde ser calculado para {file_path}. Arquivo será pulado.")
            continue

        # Se o arquivo não está no cache ou o hash mudou, precisa ser processado
        if filename not in current_cache or current_cache[filename] != current_hash:
            files_to_process.append(file_path)
            
    logger.info(f"{len(files_to_process)} arquivo(s) identificado(s) para processamento (novos ou modificados).")
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
        file_hash = _calculate_hash(file_path)
        if file_hash: # Só atualiza se o hash foi calculado com sucesso
            current_cache[filename] = file_hash
            updated = True
        else:
            logger.warning(f"Não foi possível atualizar o cache para {file_path} (hash falhou).")
    
    if updated:
        save_cache(current_cache, cache_file)
