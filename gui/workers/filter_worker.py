# gui/workers/filter_worker.py
# Worker thread for filtering data asynchronously with cache

import logging

import pandas as pd
from PyQt6.QtCore import QThread, pyqtSignal

from core.dataframe_fingerprint import build_dataframe_filter_hash
from core.search_filter import (
    GeneralSearchCancelled,
    apply_general_search_terms,
    filter_dataframe,
    parse_search_terms,
)
from gui.cache import FilterCache

logger = logging.getLogger(__name__)

def _normalize_search_chunks(search_chunks: list | tuple | None) -> list[list[str]]:
    unique_search_chunks: list[list[str]] = []
    seen_search_chunks = set()
    for chunk in search_chunks or []:
        if isinstance(chunk, str):
            terms = [chunk.strip()] if chunk.strip() else []
        elif isinstance(chunk, (list, tuple)):
            terms = [str(term).strip() for term in chunk if str(term).strip()]
        else:
            terms = [str(chunk).strip()] if str(chunk).strip() else []
        if not terms:
            continue
        chunk_key = tuple(terms)
        if chunk_key in seen_search_chunks:
            continue
        seen_search_chunks.add(chunk_key)
        unique_search_chunks.append(terms)
    return unique_search_chunks


class FilterWorker(QThread):
    """Thread para filtrar dados com cache inteligente."""

    filter_finished = pyqtSignal(pd.DataFrame)  # Emite o DataFrame filtrado
    error_occurred = pyqtSignal(str)

    # Cache de classe compartilhado entre instancias
    _cache = FilterCache(max_size=50)

    @classmethod
    def reset_shared_cache(cls, max_size: int = 50) -> None:
        cls._cache = FilterCache(max_size=max_size)

    @classmethod
    def clear_shared_cache(cls) -> None:
        cls._cache.clear()

    def __init__(
        self,
        df_completo,
        search_chunks: list | tuple,
        search_columns: list[str] | None = None,
        default_mode: str = "contains",
        cache_context: str | None = None,
        df_hash: str | None = None,
        cache: FilterCache | None = None,
    ):
        super().__init__()
        self.df_completo = (
            df_completo.copy(deep=False)
            if isinstance(df_completo, pd.DataFrame)
            else df_completo
        )
        self.search_chunks = list(search_chunks or [])
        self.search_columns = (
            list(search_columns) if search_columns is not None else None
        )
        self.default_mode = default_mode
        self.cache_context = cache_context or ""
        self._cancel_requested = False

        self.df_hash = df_hash
        self._worker_cache = cache if cache is not None else type(self)._cache

    def cancel(self) -> None:
        self._cancel_requested = True
        try:
            if self.isRunning():
                self.requestInterruption()
        except Exception as exc:
            logger.debug("Falha ao solicitar interrupcao do FilterWorker: %s", exc)

    def _is_cancelled(self) -> bool:
        if self._cancel_requested:
            return True
        try:
            return bool(self.isInterruptionRequested())
        except Exception as exc:
            logger.debug(
                "Falha ao consultar estado de interrupcao do FilterWorker: %s", exc
            )
            return False

    @staticmethod
    def _build_df_hash(df_completo: pd.DataFrame) -> str:
        """Cria hash estável do DataFrame para chave de cache de filtros."""
        return build_dataframe_filter_hash(df_completo)

    def run(self):
        try:
            if self._is_cancelled():
                return
            if self.df_completo is None:
                logger.warning(
                    "FilterWorker recebeu df_completo=None; emitindo resultado vazio"
                )
                self.filter_finished.emit(pd.DataFrame())
                return
            if self.df_hash is None:
                self.df_hash = self._build_df_hash(self.df_completo)
            search_chunks = _normalize_search_chunks(self.search_chunks)
            # Verifica cache primeiro
            cached_result = self._worker_cache.get(
                self.df_hash,
                search_chunks,
                self.default_mode,
                cache_context=self.cache_context,
            )
            if cached_result is not None:
                if self._is_cancelled():
                    return
                self.filter_finished.emit(cached_result)
                return

            # Cache miss - executa filtro
            if search_chunks:
                df_filtrado = apply_general_search_terms(
                    self.df_completo,
                    search_chunks,
                    default_mode=self.default_mode,
                    general_search_columns=self.search_columns,
                    parse_terms_func=parse_search_terms,
                    filter_dataframe_func=filter_dataframe,
                    should_cancel=self._is_cancelled,
                )
            else:
                df_filtrado = self.df_completo

            if self._is_cancelled():
                return
            # Armazena no cache
            self._worker_cache.put(
                self.df_hash,
                search_chunks,
                self.default_mode,
                df_filtrado,
                cache_context=self.cache_context,
            )

            if self._is_cancelled():
                return
            if search_chunks:
                self.filter_finished.emit(df_filtrado)
                return
            cached_empty = self._worker_cache.get(
                self.df_hash,
                search_chunks,
                self.default_mode,
                cache_context=self.cache_context,
            )
            if cached_empty is not None:
                self.filter_finished.emit(cached_empty)
            elif isinstance(self.df_completo, pd.DataFrame):
                self.filter_finished.emit(self.df_completo.copy(deep=True))
        except GeneralSearchCancelled:
            return
        except Exception as e:
            self.error_occurred.emit(f"Erro ao filtrar dados: {e}")
