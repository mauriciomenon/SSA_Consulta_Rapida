"""
Cache Manager - Sistema Unificado de Cache
Elimina os 4 sistemas de cache independentes.
"""

import hashlib
import json
import pickle
import sys
import threading
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import pandas as pd


class CacheManager:
    """
    Gerenciador unificado de cache para GUI e CLI.
    Substitui multiplos sistemas de cache por uma implementacao centralizada.
    """

    def __init__(self, max_entries: int = 50):
        """
        Inicializa o gerenciador de cache.

        Args:
            max_entries: Numero maximo de entradas por categoria interna de cache
        """
        self.max_entries = max_entries
        self._caches: Dict[str, Dict[str, Any]] = {
            "widths": {},  # Cache de larguras computadas
            "dataframes": {},  # Cache de DataFrames formatados
            "configurations": {},  # Cache de configuracoes
            "column_sets": {},  # Cache de sets de colunas
            "outputs": {},  # Cache de saidas formatadas (CLI)
        }
        self._access_times: Dict[str, Dict[str, datetime]] = {
            cache_name: {} for cache_name in self._caches.keys()
        }
        self._stats: Dict[str, int] = {"hits": 0, "misses": 0, "evictions": 0}
        self._lock = threading.RLock()

    def get_dataframe_hash(self, df: pd.DataFrame, extra_info: str = "") -> str:
        """
        Gera hash unico para um DataFrame.

        Args:
            df: DataFrame para gerar hash
            extra_info: Informacao adicional para incluir no hash

        Returns:
            Hash string unico
        """
        # Cria identificador baseado na estrutura e tamanho do DataFrame
        df_info = {
            "shape": df.shape,
            "columns": list(df.columns),
            "dtypes": str(df.dtypes.to_dict()),
            "extra": extra_info,
        }

        # Hash full content to avoid stale cache hits on middle-row changes.
        if not df.empty:
            try:
                row_hashes = pd.util.hash_pandas_object(df, index=True)
            except TypeError:
                # Pickle is only used to serialize local cache-key input, never load it.
                content_payload = {
                    "index": list(df.index),
                    "columns": list(df.columns),
                    "data": df.to_numpy(dtype=object, copy=False).tolist(),
                }
                df_info["content_hash"] = hashlib.md5(
                    pickle.dumps(content_payload, protocol=pickle.HIGHEST_PROTOCOL),
                    usedforsecurity=False,
                ).hexdigest()
            else:
                df_info["content_hash"] = hashlib.md5(
                    row_hashes.to_numpy(dtype="uint64").tobytes(),
                    usedforsecurity=False,
                ).hexdigest()

        # MD5 is used only for deterministic cache keys, never for security.
        info_str = json.dumps(df_info, sort_keys=True, default=str)
        return hashlib.md5(info_str.encode(), usedforsecurity=False).hexdigest()

    def get_cached_widths(
        self, df_hash: str, table_width: Optional[int] = None
    ) -> Optional[Dict[str, int]]:
        """
        Recupera larguras do cache.

        Args:
            df_hash: Hash do DataFrame
            table_width: Largura da tabela (opcional para validacao)

        Returns:
            Dict com larguras ou None se nao encontrado
        """
        cache_key = f"{df_hash}_{table_width}" if table_width is not None else df_hash
        return self._get_from_cache("widths", cache_key)

    def cache_widths(
        self, df_hash: str, widths: Dict[str, int], table_width: Optional[int] = None
    ) -> None:
        """
        Armazena larguras no cache.

        Args:
            df_hash: Hash do DataFrame
            widths: Dict com larguras por coluna
            table_width: Largura da tabela (opcional)
        """
        cache_key = f"{df_hash}_{table_width}" if table_width is not None else df_hash
        self._put_in_cache("widths", cache_key, widths.copy())

    def get_cached_formatted_df(self, df_hash: str) -> Optional[pd.DataFrame]:
        """
        Recupera DataFrame formatado do cache.

        Args:
            df_hash: Hash do DataFrame original

        Returns:
            DataFrame formatado ou None se nao encontrado
        """
        return self._get_from_cache("dataframes", df_hash)

    def cache_formatted_df(self, df_hash: str, formatted_df: pd.DataFrame) -> None:
        """
        Armazena DataFrame formatado no cache.

        Args:
            df_hash: Hash do DataFrame original
            formatted_df: DataFrame formatado
        """
        # Cria copia para evitar modificacoes externas
        df_copy = formatted_df.copy()
        self._put_in_cache("dataframes", df_hash, df_copy)

    def get_cached_config(self, config_name: str) -> Optional[Dict[str, Any]]:
        """
        Recupera configuracao do cache.

        Args:
            config_name: Nome da configuracao

        Returns:
            Dict com configuracao ou None se nao encontrado
        """
        return self._get_from_cache("configurations", config_name)

    def cache_config(self, config_name: str, config_data: Dict[str, Any]) -> None:
        """
        Armazena configuracao no cache.

        Args:
            config_name: Nome da configuracao
            config_data: Dados da configuracao
        """
        self._put_in_cache("configurations", config_name, config_data.copy())

    def get_cached_column_set(self, set_name: str) -> Optional[List[str]]:
        """
        Recupera set de colunas do cache.

        Args:
            set_name: Nome do set

        Returns:
            Lista de colunas ou None se nao encontrado
        """
        return self._get_from_cache("column_sets", set_name)

    def cache_column_set(self, set_name: str, columns: List[str]) -> None:
        """
        Armazena set de colunas no cache.

        Args:
            set_name: Nome do set
            columns: Lista de colunas
        """
        self._put_in_cache("column_sets", set_name, columns.copy())

    def get_cached_output(self, output_hash: str) -> Optional[str]:
        """
        Recupera saida formatada do cache (para CLI).

        Args:
            output_hash: Hash da saida

        Returns:
            String formatada ou None se nao encontrado
        """
        return self._get_from_cache("outputs", output_hash)

    def cache_output(self, output_hash: str, output_text: str) -> None:
        """
        Armazena saida formatada no cache (para CLI).

        Args:
            output_hash: Hash da saida
            output_text: Texto formatado
        """
        self._put_in_cache("outputs", output_hash, output_text)

    def _get_from_cache(self, cache_name: str, key: str) -> Optional[Any]:
        """Recupera item do cache especifico."""
        with self._lock:
            if cache_name not in self._caches:
                return None

            cache = self._caches[cache_name]
            if key in cache:
                self._access_times[cache_name][key] = datetime.now()
                self._stats["hits"] += 1
                return cache[key]

            self._stats["misses"] += 1
            return None

    def _put_in_cache(self, cache_name: str, key: str, value: Any) -> None:
        """Armazena item no cache especifico."""
        with self._lock:
            if cache_name not in self._caches:
                return

            cache = self._caches[cache_name]
            access_times = self._access_times[cache_name]

            if len(cache) >= self.max_entries and key not in cache:
                self._evict_oldest(cache_name)

            cache[key] = value
            access_times[key] = datetime.now()

    def _evict_oldest(self, cache_name: str) -> None:
        """Remove o item mais antigo do cache."""
        cache = self._caches[cache_name]
        access_times = self._access_times[cache_name]

        if not access_times:
            return

        # Encontra chave com acesso mais antigo
        oldest_key = min(access_times.keys(), key=lambda k: access_times[k])

        # Remove da cache e dos access_times
        if oldest_key in cache:
            del cache[oldest_key]
        if oldest_key in access_times:
            del access_times[oldest_key]

        self._stats["evictions"] += 1

    def invalidate_cache(self, cache_name: Optional[str] = None) -> None:
        """
        Invalida cache especifico ou todos os caches.

        Args:
            cache_name: Nome do cache a invalidar (None para todos)
        """
        with self._lock:
            if cache_name:
                if cache_name in self._caches:
                    self._caches[cache_name].clear()
                    self._access_times[cache_name].clear()
            else:
                for cache in self._caches.values():
                    cache.clear()
                for access_time in self._access_times.values():
                    access_time.clear()

    def get_cache_stats(self) -> Dict[str, Any]:
        """Retorna estatisticas detalhadas do cache."""
        with self._lock:
            stats: Dict[str, Any] = {
                "hits": self._stats["hits"],
                "misses": self._stats["misses"],
                "evictions": self._stats["evictions"],
            }

            cache_details = {}
            for cache_name, cache in self._caches.items():
                memory_estimate = 0
                for value in cache.values():
                    if isinstance(value, pd.DataFrame):
                        memory_estimate += int(value.memory_usage(deep=False).sum())
                    else:
                        memory_estimate += sys.getsizeof(value)
                cache_details[cache_name] = {
                    "entries": len(cache),
                    "keys": list(cache.keys())[:5],
                    "memory_estimate": memory_estimate,
                }

            stats["cache_details"] = cache_details
            stats["total_entries"] = sum(len(cache) for cache in self._caches.values())
            total_requests = stats["hits"] + stats["misses"]
            stats["hit_rate"] = (
                stats["hits"] / total_requests if total_requests > 0 else 0
            )

            return stats

    def cleanup_old_entries(self, max_age_minutes: int = 60) -> int:
        """
        Remove entradas sem acesso recente do cache.

        O nome publico e mantido por compatibilidade; a limpeza usa tempo de
        inatividade desde o ultimo acesso registrado.

        Args:
            max_age_minutes: Limite de inatividade em minutos

        Returns:
            Numero de entradas removidas
        """
        cutoff_time = datetime.now() - timedelta(minutes=max_age_minutes)

        removed_count = 0

        with self._lock:
            for cache_name in self._caches.keys():
                cache = self._caches[cache_name]
                access_times = self._access_times[cache_name]

                old_keys = [
                    key
                    for key, access_time in access_times.items()
                    if access_time < cutoff_time
                ]

                for key in old_keys:
                    if key in cache:
                        del cache[key]
                    if key in access_times:
                        del access_times[key]
                    removed_count += 1

            return removed_count

    def export_cache_for_debugging(self) -> Dict[str, Any]:
        """Exporta estado do cache para debugging."""
        with self._lock:
            export_data = {
                "timestamp": datetime.now().isoformat(),
                "stats": self.get_cache_stats(),
                "caches": {},
            }

            for cache_name, cache in self._caches.items():
                export_data["caches"][cache_name] = {
                    "keys": list(cache.keys()),
                    "entry_count": len(cache),
                    "sample_key": list(cache.keys())[0] if cache else None,
                }

            return export_data
