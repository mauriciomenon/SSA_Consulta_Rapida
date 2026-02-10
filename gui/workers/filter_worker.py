# gui/workers/filter_worker.py
# Worker thread for filtering data asynchronously with cache

import hashlib
import logging
import pandas as pd
from PyQt6.QtCore import QThread, pyqtSignal

from gui.cache import FilterCache
from core.app_logic import filter_dataframe, parse_search_terms

logger = logging.getLogger(__name__)


class FilterWorker(QThread):
    """Thread para filtrar dados com cache inteligente."""
    filter_finished = pyqtSignal(pd.DataFrame)  # Emite o DataFrame filtrado
    error_occurred = pyqtSignal(str)

    # Cache de classe compartilhado entre instancias
    _cache = FilterCache(max_size=50)

    def __init__(self, df_completo, search_chunks, default_mode: str = 'contains'):
        super().__init__()
        self.df_completo = df_completo
        self.search_chunks = search_chunks or []
        self.default_mode = default_mode
        self._cancel_requested = False

        # Gera fingerprint estrutural+amostral para reduzir colisões de cache
        self.df_hash = self._build_df_hash(df_completo)

    def cancel(self) -> None:
        self._cancel_requested = True
        try:
            self.requestInterruption()
        except Exception as exc:
            logger.debug("Falha ao solicitar interrupcao do FilterWorker: %s", exc)

    def _is_cancelled(self) -> bool:
        if bool(getattr(self, "_cancel_requested", False)):
            return True
        try:
            return bool(self.isInterruptionRequested())
        except Exception:
            return False

    @staticmethod
    def _build_df_hash(df_completo: pd.DataFrame) -> str:
        """Cria hash estável do DataFrame para chave de cache de filtros."""
        try:
            if df_completo is None:
                return hashlib.md5(b"none").hexdigest()[:16]

            row_count = len(df_completo)
            if row_count <= 24:
                sample_df = df_completo
            else:
                sample_df = pd.concat(
                    [df_completo.head(12), df_completo.tail(12)],
                    axis=0,
                    ignore_index=True,
                )

            sample_records = tuple(
                tuple(str(value) for value in row_values)
                for row_values in sample_df.itertuples(index=False, name=None)
            )
            payload = (
                tuple(df_completo.shape),
                tuple(str(column) for column in df_completo.columns),
                tuple(str(dtype) for dtype in df_completo.dtypes),
                sample_records,
            )
            return hashlib.md5(repr(payload).encode("utf-8")).hexdigest()[:16]
        except Exception as exc:
            logger.debug(
                "Fallback to shape-only DataFrame hash due to fingerprint error: %s",
                exc,
            )
            fallback = str(getattr(df_completo, "shape", "unknown"))
            return hashlib.md5(fallback.encode("utf-8")).hexdigest()[:16]

    def run(self):
        try:
            if self._is_cancelled():
                return
            # Verifica cache primeiro
            cached_result = self._cache.get(self.df_hash, self.search_chunks, self.default_mode)
            if cached_result is not None:
                if self._is_cancelled():
                    return
                self.filter_finished.emit(cached_result)
                return

            # Cache miss - executa filtro
            if self.search_chunks:
                frames = []
                for terms in self.search_chunks:
                    if self._is_cancelled():
                        return
                    if terms:
                        parsed = parse_search_terms(terms, default_mode=self.default_mode)
                        if self._is_cancelled():
                            return
                        frames.append(filter_dataframe(self.df_completo, parsed))
                    else:
                        frames.append(self.df_completo.copy())
                    if self._is_cancelled():
                        return
                if frames:
                    df_filtrado = pd.concat(frames, axis=0, ignore_index=False).drop_duplicates().reset_index(drop=True)
                else:
                    df_filtrado = self.df_completo.copy()
            else:
                df_filtrado = self.df_completo.copy()

            if self._is_cancelled():
                return
            # Armazena no cache
            self._cache.put(self.df_hash, self.search_chunks, self.default_mode, df_filtrado)

            if self._is_cancelled():
                return
            self.filter_finished.emit(df_filtrado)
        except Exception as e:
            self.error_occurred.emit(f"Erro ao filtrar dados: {e}")
