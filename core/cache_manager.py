"""
Cache Manager - Sistema Unificado de Cache
Elimina os 4 sistemas de cache independentes.
"""

from typing import Any, Dict, Optional, List, Callable
import hashlib
import json
import pandas as pd
from datetime import datetime


class CacheManager:
    """
    Gerenciador unificado de cache para GUI e CLI.
    Substitui múltiplos sistemas de cache por uma implementação centralizada.
    """
    
    def __init__(self, max_entries: int = 50):
        """
        Inicializa o gerenciador de cache.
        
        Args:
            max_entries: Número máximo de entradas no cache
        """
        self.max_entries = max_entries
        self._caches: Dict[str, Dict[str, Any]] = {
            'widths': {},           # Cache de larguras computadas
            'dataframes': {},       # Cache de DataFrames formatados
            'configurations': {},   # Cache de configurações
            'column_sets': {},      # Cache de sets de colunas
            'outputs': {},          # Cache de saídas formatadas (CLI)
        }
        self._access_times: Dict[str, Dict[str, datetime]] = {
            cache_name: {} for cache_name in self._caches.keys()
        }
        self._stats = {
            'hits': 0,
            'misses': 0,
            'evictions': 0
        }
    
    def get_dataframe_hash(self, df: pd.DataFrame, extra_info: str = '') -> str:
        """
        Gera hash único para um DataFrame.
        
        Args:
            df: DataFrame para gerar hash
            extra_info: Informação adicional para incluir no hash
            
        Returns:
            Hash string único
        """
        # Cria identificador baseado na estrutura e tamanho do DataFrame
        df_info = {
            'shape': df.shape,
            'columns': list(df.columns),
            'dtypes': str(df.dtypes.to_dict()),
            'extra': extra_info
        }
        
        # Inclui sample dos dados para detectar mudanças de conteúdo
        if not df.empty:
            # Usa primeiras e últimas linhas para detecção eficiente
            sample_data = pd.concat([df.head(2), df.tail(2)]) if len(df) > 4 else df
            df_info['sample'] = sample_data.to_string()
        
        # Gera hash MD5
        info_str = json.dumps(df_info, sort_keys=True, default=str)
        return hashlib.md5(info_str.encode()).hexdigest()
    
    def get_cached_widths(
        self, 
        df_hash: str, 
        table_width: int = None
    ) -> Optional[Dict[str, int]]:
        """
        Recupera larguras do cache.
        
        Args:
            df_hash: Hash do DataFrame
            table_width: Largura da tabela (opcional para validação)
            
        Returns:
            Dict com larguras ou None se não encontrado
        """
        cache_key = f"{df_hash}_{table_width}" if table_width else df_hash
        return self._get_from_cache('widths', cache_key)
    
    def cache_widths(
        self, 
        df_hash: str, 
        widths: Dict[str, int], 
        table_width: int = None
    ) -> None:
        """
        Armazena larguras no cache.
        
        Args:
            df_hash: Hash do DataFrame
            widths: Dict com larguras por coluna
            table_width: Largura da tabela (opcional)
        """
        cache_key = f"{df_hash}_{table_width}" if table_width else df_hash
        self._put_in_cache('widths', cache_key, widths.copy())
    
    def get_cached_formatted_df(self, df_hash: str) -> Optional[pd.DataFrame]:
        """
        Recupera DataFrame formatado do cache.
        
        Args:
            df_hash: Hash do DataFrame original
            
        Returns:
            DataFrame formatado ou None se não encontrado
        """
        return self._get_from_cache('dataframes', df_hash)
    
    def cache_formatted_df(self, df_hash: str, formatted_df: pd.DataFrame) -> None:
        """
        Armazena DataFrame formatado no cache.
        
        Args:
            df_hash: Hash do DataFrame original
            formatted_df: DataFrame formatado
        """
        # Cria cópia para evitar modificações externas
        df_copy = formatted_df.copy()
        self._put_in_cache('dataframes', df_hash, df_copy)
    
    def get_cached_config(self, config_name: str) -> Optional[Dict[str, Any]]:
        """
        Recupera configuração do cache.
        
        Args:
            config_name: Nome da configuração
            
        Returns:
            Dict com configuração ou None se não encontrado
        """
        return self._get_from_cache('configurations', config_name)
    
    def cache_config(self, config_name: str, config_data: Dict[str, Any]) -> None:
        """
        Armazena configuração no cache.
        
        Args:
            config_name: Nome da configuração
            config_data: Dados da configuração
        """
        self._put_in_cache('configurations', config_name, config_data.copy())
    
    def get_cached_column_set(self, set_name: str) -> Optional[List[str]]:
        """
        Recupera set de colunas do cache.
        
        Args:
            set_name: Nome do set
            
        Returns:
            Lista de colunas ou None se não encontrado
        """
        return self._get_from_cache('column_sets', set_name)
    
    def cache_column_set(self, set_name: str, columns: List[str]) -> None:
        """
        Armazena set de colunas no cache.
        
        Args:
            set_name: Nome do set
            columns: Lista de colunas
        """
        self._put_in_cache('column_sets', set_name, columns.copy())
    
    def get_cached_output(self, output_hash: str) -> Optional[str]:
        """
        Recupera saída formatada do cache (para CLI).
        
        Args:
            output_hash: Hash da saída
            
        Returns:
            String formatada ou None se não encontrado
        """
        return self._get_from_cache('outputs', output_hash)
    
    def cache_output(self, output_hash: str, output_text: str) -> None:
        """
        Armazena saída formatada no cache (para CLI).
        
        Args:
            output_hash: Hash da saída
            output_text: Texto formatado
        """
        self._put_in_cache('outputs', output_hash, output_text)
    
    def _get_from_cache(self, cache_name: str, key: str) -> Optional[Any]:
        """Recupera item do cache específico."""
        if cache_name not in self._caches:
            return None
        
        cache = self._caches[cache_name]
        if key in cache:
            # Atualiza tempo de acesso
            self._access_times[cache_name][key] = datetime.now()
            self._stats['hits'] += 1
            return cache[key]
        
        self._stats['misses'] += 1
        return None
    
    def _put_in_cache(self, cache_name: str, key: str, value: Any) -> None:
        """Armazena item no cache específico."""
        if cache_name not in self._caches:
            return
        
        cache = self._caches[cache_name]
        access_times = self._access_times[cache_name]
        
        # Verifica se precisa fazer eviction
        if len(cache) >= self.max_entries and key not in cache:
            self._evict_oldest(cache_name)
        
        # Armazena o item
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
        
        self._stats['evictions'] += 1
    
    def invalidate_cache(self, cache_name: Optional[str] = None) -> None:
        """
        Invalida cache específico ou todos os caches.
        
        Args:
            cache_name: Nome do cache a invalidar (None para todos)
        """
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
        """Retorna estatísticas detalhadas do cache."""
        stats = self._stats.copy()
        
        # Adiciona estatísticas por cache
        cache_details = {}
        for cache_name, cache in self._caches.items():
            cache_details[cache_name] = {
                'entries': len(cache),
                'keys': list(cache.keys())[:5],  # Primeiras 5 chaves
                'memory_estimate': len(str(cache))
            }
        
        stats['cache_details'] = cache_details
        stats['total_entries'] = sum(len(cache) for cache in self._caches.values())
        
        # Calcula hit rate
        total_requests = stats['hits'] + stats['misses']
        stats['hit_rate'] = stats['hits'] / total_requests if total_requests > 0 else 0
        
        return stats
    
    def cleanup_old_entries(self, max_age_minutes: int = 60) -> int:
        """
        Remove entradas antigas do cache.
        
        Args:
            max_age_minutes: Idade máxima em minutos
            
        Returns:
            Número de entradas removidas
        """
        cutoff_time = datetime.now()
        cutoff_time = cutoff_time.replace(minute=cutoff_time.minute - max_age_minutes)
        
        removed_count = 0
        
        for cache_name in self._caches.keys():
            cache = self._caches[cache_name]
            access_times = self._access_times[cache_name]
            
            old_keys = [
                key for key, access_time in access_times.items()
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
        export_data = {
            'timestamp': datetime.now().isoformat(),
            'stats': self.get_cache_stats(),
            'caches': {}
        }
        
        # Exporta apenas metadados dos caches (não os dados completos)
        for cache_name, cache in self._caches.items():
            export_data['caches'][cache_name] = {
                'keys': list(cache.keys()),
                'entry_count': len(cache),
                'sample_key': list(cache.keys())[0] if cache else None
            }
        
        return export_data
