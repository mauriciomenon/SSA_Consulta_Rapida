# gui/workers/filter_worker.py
# Worker thread for filtering data asynchronously with cache

import hashlib
import pandas as pd
from PyQt6.QtCore import QThread, pyqtSignal

from gui.cache import FilterCache
from core.app_logic import filter_dataframe, parse_search_terms


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

        # Gera hash do DataFrame para cache
        self.df_hash = hashlib.md5(str(df_completo.shape).encode()).hexdigest()[:16]

    def run(self):
        try:
            # Verifica cache primeiro
            cached_result = self._cache.get(self.df_hash, self.search_chunks, self.default_mode)
            if cached_result is not None:
                self.filter_finished.emit(cached_result)
                return

            # Cache miss - executa filtro
            if self.search_chunks:
                frames = []
                for terms in self.search_chunks:
                    if terms:
                        parsed = parse_search_terms(terms, default_mode=self.default_mode)
                        frames.append(filter_dataframe(self.df_completo, parsed))
                    else:
                        frames.append(self.df_completo.copy())
                if frames:
                    df_filtrado = pd.concat(frames, axis=0, ignore_index=False).drop_duplicates().reset_index(drop=True)
                else:
                    df_filtrado = self.df_completo.copy()
            else:
                df_filtrado = self.df_completo.copy()

            # Armazena no cache
            self._cache.put(self.df_hash, self.search_chunks, self.default_mode, df_filtrado)

            self.filter_finished.emit(df_filtrado)
        except Exception as e:
            self.error_occurred.emit(f"Erro ao filtrar dados: {e}")
