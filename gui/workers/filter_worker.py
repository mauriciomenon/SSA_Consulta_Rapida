# gui/workers/filter_worker.py
# Worker thread for filtering data asynchronously with cache

import hashlib
import logging

import pandas as pd
from PyQt6.QtCore import QThread, pyqtSignal

from core.search_filter import filter_dataframe, parse_search_terms
from gui.cache import FilterCache

logger = logging.getLogger(__name__)

FILTER_WORKER_HASH_ATTR = "_filter_worker_df_hash"


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

    def __init__(
        self,
        df_completo,
        search_chunks: list | tuple,
        search_columns: list[str] | None = None,
        default_mode: str = "contains",
        cache_context: str | None = None,
        df_hash: str | None = None,
    ):
        super().__init__()
        self.df_completo = df_completo
        self.search_chunks = list(search_chunks or [])
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
        try:
            if df_completo is None:
                return hashlib.blake2b(b"none", digest_size=8).hexdigest()

            cache_key = (
                tuple(getattr(df_completo, "shape", (0, 0))),
                tuple(str(column) for column in getattr(df_completo, "columns", ())),
                tuple(str(dtype) for dtype in getattr(df_completo, "dtypes", ())),
                getattr(df_completo, "attrs", {}).get("ssa_data_revision"),
                getattr(df_completo, "attrs", {}).get("ssa_preprocessed_for_gui"),
            )
            cached_hash = getattr(df_completo, "attrs", {}).get(FILTER_WORKER_HASH_ATTR)
            if (
                isinstance(cached_hash, dict)
                and cached_hash.get("key") == cache_key
                and cache_key[3] is not None
                and isinstance(cached_hash.get("hash"), str)
            ):
                return str(cached_hash["hash"])

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
            digest = hasher.hexdigest()
            try:
                df_completo.attrs[FILTER_WORKER_HASH_ATTR] = {
                    "key": cache_key,
                    "hash": digest,
                }
            except Exception as exc:
                logger.debug("Falha ao cachear hash de FilterWorker: %s", exc)
            return digest
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
            search_chunks = _normalize_search_chunks(self.search_chunks)
            # Verifica cache primeiro
            cached_result = self._cache.get(
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
                if len(search_chunks) == 1:
                    terms = search_chunks[0]
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
                    combined_mask = pd.Series(False, index=self.df_completo.index)
                    include_all_rows = False
                    for terms in search_chunks:
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
                                combined_mask = combined_mask | pd.Series(
                                    self.df_completo.index.isin(filtered.index),
                                    index=self.df_completo.index,
                                )
                        else:
                            include_all_rows = True
                            break
                        if self._is_cancelled():
                            return
                    if include_all_rows:
                        df_filtrado = self.df_completo
                    elif bool(combined_mask.any()):
                        df_filtrado = self.df_completo.loc[combined_mask]
                    else:
                        df_filtrado = self.df_completo.iloc[0:0]
            else:
                df_filtrado = self.df_completo

            if self._is_cancelled():
                return
            # Armazena no cache
            self._cache.put(
                self.df_hash,
                search_chunks,
                self.default_mode,
                df_filtrado,
                cache_context=self.cache_context,
            )

            if self._is_cancelled():
                return
            self.filter_finished.emit(df_filtrado)
        except Exception as e:
            self.error_occurred.emit(f"Erro ao filtrar dados: {e}")
