# gui/cache/filter_cache.py
# LRU cache for filter results

import hashlib
import logging
import pandas as pd
from collections import OrderedDict
import threading

logger = logging.getLogger(__name__)


class FilterCache:
    """Cache inteligente LRU para resultados de filtros da GUI."""

    def __init__(self, max_size: int = 50, lock=None):
        self.max_size = max_size
        self._cache = OrderedDict()  # LRU cache
        self._stats = {'hits': 0, 'misses': 0, 'evictions': 0}
        # This cache is shared across FilterWorker instances and accessed from QThreads.
        # Protect internal state to prevent races (e.g., key in cache then pop KeyError).
        self._lock = lock or threading.Lock()

    def _generate_key(self, df_hash: str, search_chunks: list, default_mode: str) -> str:
        """Gera chave unica para cache baseada nos parametros de filtro."""
        # Converte search_chunks em string deterministica
        chunks_str = str(sorted([str(sorted(chunk)) if isinstance(chunk, list) else str(chunk) for chunk in search_chunks]))

        # Cria hash combinado
        combined = f"{df_hash}|{chunks_str}|{default_mode}"
        return hashlib.md5(combined.encode('utf-8')).hexdigest()

    def get(self, df_hash: str, search_chunks: list, default_mode: str) -> pd.DataFrame | None:
        """Recupera resultado do cache se disponivel."""
        key = self._generate_key(df_hash, search_chunks, default_mode)
        result = None

        with self._lock:
            if key in self._cache:
                # Move para o final (marca como recentemente usado)
                result = self._cache.pop(key)
                self._cache[key] = result
                self._stats['hits'] += 1
                logger.debug(f"Cache hit for filter key: {key[:8]}...")
            else:
                self._stats['misses'] += 1
                logger.debug(f"Cache miss for filter key: {key[:8]}...")
                return None

        # Return copy outside the lock to keep critical section small.
        if isinstance(result, pd.DataFrame):
            return result.copy()  # Retorna copia para evitar modificacoes
        logger.debug("Cache hit sem DataFrame valido para key: %s", key[:8])
        return None

    def put(self, df_hash: str, search_chunks: list, default_mode: str, result: pd.DataFrame):
        """Armazena resultado no cache."""
        key = self._generate_key(df_hash, search_chunks, default_mode)
        result_copy = result.copy()

        with self._lock:
            # Remove entrada existente se houver
            if key in self._cache:
                del self._cache[key]

            # Adiciona nova entrada
            self._cache[key] = result_copy

            # Implementa politica LRU
            while len(self._cache) > self.max_size:
                # Remove item mais antigo (primeiro na OrderedDict)
                oldest_key = next(iter(self._cache))
                del self._cache[oldest_key]
                self._stats['evictions'] += 1

            logger.debug(f"Cache put for filter key: {key[:8]}... (size: {len(self._cache)})")

    def clear(self):
        """Limpa todo o cache."""
        with self._lock:
            self._cache.clear()
            self._stats = {'hits': 0, 'misses': 0, 'evictions': 0}
            logger.debug("Filter cache cleared")

    def get_stats(self) -> dict:
        """Retorna estatisticas do cache."""
        with self._lock:
            size = len(self._cache)
            stats = dict(self._stats)

        total = stats['hits'] + stats['misses']
        hit_rate = (stats['hits'] / total * 100) if total > 0 else 0

        return {
            'size': size,
            'max_size': self.max_size,
            'hits': stats['hits'],
            'misses': stats['misses'],
            'evictions': stats['evictions'],
            'hit_rate': hit_rate
        }
