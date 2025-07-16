# utils/caching.py (v1.0 - Logica de Cache de Importacao)
import os
import json
import hashlib
from typing import Dict, List

CACHE_FILENAME = '.importer_cache.json'

def _calculate_hash(file_path: str) -> str:
    """Calcula o hash SHA256 de um ficheiro para detetar modificacoes."""
    sha256_hash = hashlib.sha256()
    try:
        with open(file_path, "rb") as f:
            # Le o ficheiro em blocos para ser eficiente com a memoria
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()
    except (IOError, OSError):
        # Retorna um hash invalido se o ficheiro nao puder ser lido
        return ""

def load_cache(data_dir: str) -> Dict[str, str]:
    """Carrega o cache de hashes do ficheiro JSON."""
    cache_path = os.path.join(data_dir, CACHE_FILENAME)
    if not os.path.exists(cache_path):
        return {}
    try:
        with open(cache_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        # Retorna um cache vazio se o ficheiro estiver corrompido ou ilegivel
        return {}

def save_cache(data_dir: str, new_cache_data: Dict[str, str]):
    """Salva os dados do novo cache no ficheiro JSON."""
    cache_path = os.path.join(data_dir, CACHE_FILENAME)
    try:
        with open(cache_path, 'w', encoding='utf-8') as f:
            json.dump(new_cache_data, f, indent=4)
    except IOError as e:
        print(f"AVISO: Nao foi possivel salvar o cache de importacao em '{cache_path}'. Erro: {e}")

def get_files_to_process(docs_dir: str, current_cache: Dict[str, str]) -> List[str]:
    """
    Compara os ficheiros em docs_dir com o cache e retorna uma lista de ficheiros
    que sao novos ou foram modificados.
    """
    files_to_process = []
    
    # Lista todos os ficheiros .xlsx que nao sao temporarios
    all_files = [f for f in os.listdir(docs_dir) if f.endswith('.xlsx') and not f.startswith('~$')]

    for filename in all_files:
        file_path = os.path.join(docs_dir, filename)
        current_hash = _calculate_hash(file_path)

        if not current_hash: # Ignora ficheiros que nao podem ser lidos
            continue

        # Adiciona a lista se o ficheiro for novo ou se o hash for diferente
        if filename not in current_cache or current_cache[filename] != current_hash:
            files_to_process.append(file_path)
            
    return files_to_process

