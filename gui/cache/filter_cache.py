# gui/cache/filter_cache.py
# LRU cache for filter results

import hashlib
import math
import os
import threading
from collections import OrderedDict

import pandas as pd

from utils.robust_logging import get_robust_logger

logger = get_robust_logger().get_logger(__name__, "gui")

DEFAULT_CACHE_MAX_ENTRY_MB = 64.0
DEFAULT_CACHE_MAX_TOTAL_MB = 256.0


def _resolve_cache_limit_bytes(env_name: str, default_mb: float) -> int | None:
    raw = os.environ.get(env_name, "").strip()
    if not raw:
        return int(default_mb * 1024 * 1024)
    try:
        max_mb = float(raw)
    except ValueError:
        logger.warning("Invalid %s value: %r", env_name, raw)
        return int(default_mb * 1024 * 1024)
    if not math.isfinite(max_mb):
        logger.warning("Invalid %s non-finite value: %r", env_name, raw)
        return int(default_mb * 1024 * 1024)
    if max_mb <= 0:
        logger.warning("Invalid %s non-positive value: %r", env_name, raw)
        return int(default_mb * 1024 * 1024)
    return int(max_mb * 1024 * 1024)


def _resolve_cache_max_entry_bytes() -> int | None:
    return _resolve_cache_limit_bytes("SSA_CACHE_MAX_MB", DEFAULT_CACHE_MAX_ENTRY_MB)


def _resolve_cache_max_total_bytes() -> int | None:
    return _resolve_cache_limit_bytes(
        "SSA_CACHE_MAX_TOTAL_MB", DEFAULT_CACHE_MAX_TOTAL_MB
    )


class FilterCache:
    """Cache inteligente LRU para resultados de filtros da GUI."""

    def __init__(self, max_size: int = 50, lock=None):
        self.max_size = max_size
        self._max_entry_bytes = _resolve_cache_max_entry_bytes()
        self._max_total_bytes = _resolve_cache_max_total_bytes()
        self._entry_bytes_by_key: dict[str, int] = {}
        self._total_bytes = 0
        self._cache = OrderedDict()  # LRU cache
        self._stats = {
            "hits": 0,
            "misses": 0,
            "evictions": 0,
            "skipped_large_entries": 0,
        }
        # This cache is shared across FilterWorker instances and accessed from QThreads.
        # Protect internal state to prevent races (e.g., key in cache then pop KeyError).
        self._lock = lock or threading.Lock()

    def _generate_key(
        self,
        df_hash: str,
        search_chunks: list,
        default_mode: str,
        cache_context: str | None = None,
    ) -> str:
        """Gera chave unica para cache baseada nos parametros de filtro."""
        normalized_chunks = [
            tuple(str(item) for item in chunk)
            if isinstance(chunk, (list, tuple))
            else (str(chunk),)
            for chunk in search_chunks
        ]

        # Cria hash combinado sem serializar JSON no caminho quente do cache.
        context_str = cache_context or ""
        hasher = hashlib.blake2b(digest_size=16)
        for value in (df_hash, default_mode, context_str):
            hasher.update(str(value).encode("utf-8", errors="replace"))
            hasher.update(b"\x00")
        for chunk in sorted(normalized_chunks):
            hasher.update(b"\x1e")
            for item in chunk:
                hasher.update(item.encode("utf-8", errors="replace"))
                hasher.update(b"\x1f")
        return hasher.hexdigest()

    def get(
        self,
        df_hash: str,
        search_chunks: list,
        default_mode: str,
        cache_context: str | None = None,
    ) -> pd.DataFrame | None:
        """Recupera resultado do cache se disponivel."""
        key = self._generate_key(
            df_hash, search_chunks, default_mode, cache_context=cache_context
        )
        result = None

        with self._lock:
            if key in self._cache:
                # Move para o final (marca como recentemente usado)
                result = self._cache.pop(key)
                self._cache[key] = result
                self._stats["hits"] += 1
                logger.debug(f"Cache hit for filter key: {key[:8]}...")
            else:
                self._stats["misses"] += 1
                logger.debug(f"Cache miss for filter key: {key[:8]}...")
                return None

        # Return an isolated copy outside the lock so GUI consumers cannot
        # mutate cached backing arrays and dirty future cache hits.
        if isinstance(result, pd.DataFrame):
            result_copy = result.copy(deep=True)
            result_copy.attrs = dict(getattr(result, "attrs", {}))
            return result_copy
        logger.debug("Cache hit sem DataFrame valido para key: %s", key[:8])
        return None

    def put(
        self,
        df_hash: str,
        search_chunks: list,
        default_mode: str,
        result: pd.DataFrame,
        cache_context: str | None = None,
    ):
        """Armazena resultado DataFrame no cache; ignora entrada invalida."""
        if not isinstance(result, pd.DataFrame):
            logger.debug(
                "FilterCache.put ignorou valor invalido para cache (tipo=%s)",
                type(result).__name__,
            )
            return
        entry_bytes = None
        if self._max_entry_bytes is not None or self._max_total_bytes is not None:
            entry_bytes = self._estimate_result_bytes(result)
            if entry_bytes is None:
                with self._lock:
                    self._stats["skipped_large_entries"] += 1
                logger.info(
                    "FilterCache.put skipped entry with unknown byte size"
                )
                return
        if self._max_entry_bytes is not None:
            if entry_bytes is not None and entry_bytes > self._max_entry_bytes:
                with self._lock:
                    self._stats["skipped_large_entries"] += 1
                logger.info(
                    "FilterCache.put skipped large DataFrame entry (bytes=%s, max_bytes=%s)",
                    entry_bytes,
                    self._max_entry_bytes,
                )
                return
        key = self._generate_key(
            df_hash, search_chunks, default_mode, cache_context=cache_context
        )
        result_copy = result.copy(deep=True)
        result_copy.attrs = dict(getattr(result, "attrs", {}))

        with self._lock:
            # Remove entrada existente se houver
            if key in self._cache:
                del self._cache[key]
                self._total_bytes -= self._entry_bytes_by_key.pop(key, 0)

            # Adiciona nova entrada
            self._cache[key] = result_copy
            if entry_bytes is not None:
                self._entry_bytes_by_key[key] = entry_bytes
                self._total_bytes += entry_bytes

            # Implementa politica LRU
            self._evict_until_within_limits()

            logger.debug(
                f"Cache put for filter key: {key[:8]}... (size: {len(self._cache)})"
            )

    def clear(self):
        """Limpa todo o cache."""
        with self._lock:
            self._cache.clear()
            self._entry_bytes_by_key.clear()
            self._total_bytes = 0
            self._stats = {
                "hits": 0,
                "misses": 0,
                "evictions": 0,
                "skipped_large_entries": 0,
            }
            logger.debug("Filter cache cleared")

    def get_stats(self) -> dict:
        """Retorna estatisticas do cache."""
        with self._lock:
            size = len(self._cache)
            stats = dict(self._stats)

        total = stats["hits"] + stats["misses"]
        hit_percentage = (stats["hits"] / total * 100) if total > 0 else 0

        return {
            "size": size,
            "max_size": self.max_size,
            "total_mb": round(self._total_bytes / (1024 * 1024), 3),
            "max_total_mb": (
                round(self._max_total_bytes / (1024 * 1024), 3)
                if self._max_total_bytes is not None
                else None
            ),
            "hits": stats["hits"],
            "misses": stats["misses"],
            "evictions": stats["evictions"],
            "skipped_large_entries": stats["skipped_large_entries"],
            "max_entry_mb": (
                round(self._max_entry_bytes / (1024 * 1024), 3)
                if self._max_entry_bytes is not None
                else None
            ),
            "hit_percentage": hit_percentage,
        }

    def _estimate_result_bytes(self, result: pd.DataFrame) -> int | None:
        try:
            shallow_bytes = int(result.memory_usage(index=True, deep=False).sum())
            row_count = len(result.index)
            if (
                row_count == 0
                or row_count * max(len(result.columns), 1) <= 10_000
                or shallow_bytes <= 8 * 1024 * 1024
            ):
                return shallow_bytes
            sample_size = min(64, row_count)
            sampled_text_bytes = 0
            for column_name in result.columns:
                series = result[column_name]
                if not (
                    pd.api.types.is_string_dtype(series.dtype)
                    or pd.api.types.is_object_dtype(series.dtype)
                ):
                    continue
                sample = series.iloc[:sample_size]
                sample_bytes = int(sample.memory_usage(index=False, deep=True))
                avg_bytes = sample_bytes / float(sample_size)
                sampled_text_bytes += int(avg_bytes * row_count)
            return shallow_bytes + sampled_text_bytes
        except Exception as exc:
            logger.warning(
                "FilterCache.put falhou ao medir tamanho da entrada; ignorando limite (erro=%s)",
                exc,
            )
            return None

    def _evict_until_within_limits(self) -> None:
        while self._cache and (
            len(self._cache) > self.max_size
            or (
                self._max_total_bytes is not None
                and self._total_bytes > self._max_total_bytes
            )
        ):
            oldest_key = next(iter(self._cache))
            del self._cache[oldest_key]
            self._total_bytes -= self._entry_bytes_by_key.pop(oldest_key, 0)
            self._stats["evictions"] += 1
