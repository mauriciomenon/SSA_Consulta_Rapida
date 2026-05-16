# gui/workers/filter_worker.py
# Worker thread for filtering data asynchronously with cache

import hashlib
import logging

import pandas as pd
from PyQt6.QtCore import QThread, pyqtSignal

from core.app_logic import filter_dataframe, parse_search_terms
from gui.cache import FilterCache

logger = logging.getLogger(__name__)


class FilterWorker(QThread):
    """Thread para filtrar dados com cache inteligente."""

    filter_finished = pyqtSignal(pd.DataFrame)  # Emite o DataFrame filtrado
    error_occurred = pyqtSignal(str)

    # Cache de classe compartilhado entre instancias
    _cache = FilterCache(max_size=50)

    def __init__(
        self,
        df_completo,
        search_chunks: list[list[str]],
        search_columns: list[str] | None = None,
        default_mode: str = "contains",
        cache_context: str | None = None,
        df_hash: str | None = None,
    ):
        super().__init__()
        self.df_completo = df_completo
        unique_search_chunks = []
        seen_search_chunks = set()
        for chunk in search_chunks or []:
            chunk_key = tuple(str(term) for term in chunk)
            if chunk_key in seen_search_chunks:
                continue
            seen_search_chunks.add(chunk_key)
            unique_search_chunks.append(list(chunk))
        self.search_chunks = unique_search_chunks
        self.search_columns = (
            list(search_columns) if search_columns is not None else None
        )
        self.default_mode = default_mode
        self.cache_context = cache_context or ""
        self._cancel_requested = False

        self.df_hash = df_hash

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
        except Exception as exc:
            logger.debug(
                "Falha ao consultar estado de interrupcao do FilterWorker: %s", exc
            )
            return False

    @staticmethod
    def _build_df_hash(df_completo: pd.DataFrame) -> str:
        """Cria hash estável do DataFrame para chave de cache de filtros."""
        try:
            if df_completo is None:
                return hashlib.blake2b(b"none", digest_size=8).hexdigest()

            row_count = len(df_completo)
            if row_count <= 24:
                sample_df = df_completo
            else:
                head_count = 8
                tail_count = 8
                mid_count = 8
                head_df = df_completo.head(head_count)
                tail_df = df_completo.tail(tail_count)
                mid_start = head_count
                tail_start = max(mid_start, row_count - tail_count)
                mid_end = tail_start - 1
                mid_indices = []
                span = max(0, (mid_end - mid_start) + 1)
                if span > 0:
                    if span <= mid_count:
                        mid_indices = list(range(mid_start, mid_start + span))
                    else:
                        step = float(span - 1) / float(max(mid_count - 1, 1))
                        for idx in range(mid_count):
                            candidate = mid_start + int(round(idx * step))
                            if not mid_indices or candidate != mid_indices[-1]:
                                mid_indices.append(candidate)
                mid_df = (
                    df_completo.iloc[mid_indices]
                    if mid_indices
                    else df_completo.iloc[0:0]
                )
                sample_df = pd.concat(
                    [head_df, mid_df, tail_df],
                    axis=0,
                    ignore_index=True,
                )

            sample_hashes = pd.util.hash_pandas_object(
                sample_df,
                index=False,
            ).to_numpy(dtype="uint64", copy=False)
            hasher = hashlib.blake2b(digest_size=8)
            hasher.update(repr(tuple(df_completo.shape)).encode("utf-8"))
            for column in df_completo.columns:
                hasher.update(b"\x00col:")
                hasher.update(str(column).encode("utf-8", errors="replace"))
            for dtype in df_completo.dtypes:
                hasher.update(b"\x00dtype:")
                hasher.update(str(dtype).encode("utf-8", errors="replace"))
            hasher.update(sample_hashes.tobytes())
            return hasher.hexdigest()
        except Exception as exc:
            logger.debug(
                "Fallback to shape-only DataFrame hash due to fingerprint error: %s",
                exc,
            )
            fallback = str(getattr(df_completo, "shape", "unknown"))
            return hashlib.blake2b(
                fallback.encode("utf-8"),
                digest_size=8,
            ).hexdigest()

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
            # Verifica cache primeiro
            cached_result = self._cache.get(
                self.df_hash,
                self.search_chunks,
                self.default_mode,
                cache_context=self.cache_context,
            )
            if cached_result is not None:
                if self._is_cancelled():
                    return
                self.filter_finished.emit(cached_result)
                return

            # Cache miss - executa filtro
            if self.search_chunks:
                if len(self.search_chunks) == 1:
                    terms = self.search_chunks[0]
                    if self._is_cancelled():
                        return
                    if terms:
                        parsed = parse_search_terms(
                            terms, default_mode=self.default_mode
                        )
                        if self._is_cancelled():
                            return
                        if self.search_columns is None:
                            df_filtrado = filter_dataframe(self.df_completo, parsed)
                        else:
                            df_filtrado = filter_dataframe(
                                self.df_completo,
                                parsed,
                                search_columns=self.search_columns,
                            )
                    else:
                        df_filtrado = self.df_completo
                    if self._is_cancelled():
                        return
                else:
                    matched_indices: list[pd.Index] = []
                    include_all_rows = False
                    for terms in self.search_chunks:
                        if self._is_cancelled():
                            return
                        if terms:
                            parsed = parse_search_terms(
                                terms, default_mode=self.default_mode
                            )
                            if self._is_cancelled():
                                return
                            if self.search_columns is None:
                                filtered = filter_dataframe(self.df_completo, parsed)
                            else:
                                filtered = filter_dataframe(
                                    self.df_completo,
                                    parsed,
                                    search_columns=self.search_columns,
                                )
                            if not filtered.empty:
                                matched_indices.append(filtered.index)
                        else:
                            include_all_rows = True
                            break
                        if self._is_cancelled():
                            return
                    if include_all_rows:
                        df_filtrado = self.df_completo
                    elif matched_indices:
                        matched_index = matched_indices[0]
                        for index in matched_indices[1:]:
                            matched_index = matched_index.union(index)
                        df_filtrado = self.df_completo.loc[
                            self.df_completo.index.isin(matched_index)
                        ]
                    else:
                        df_filtrado = self.df_completo.iloc[0:0]
            else:
                df_filtrado = self.df_completo.copy(deep=False)

            if self._is_cancelled():
                return
            # Armazena no cache
            self._cache.put(
                self.df_hash,
                self.search_chunks,
                self.default_mode,
                df_filtrado,
                cache_context=self.cache_context,
            )

            if self._is_cancelled():
                return
            self.filter_finished.emit(df_filtrado)
        except Exception as e:
            self.error_occurred.emit(f"Erro ao filtrar dados: {e}")
