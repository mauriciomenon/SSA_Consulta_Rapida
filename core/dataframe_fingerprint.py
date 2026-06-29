"""DataFrame fingerprint helpers shared by GUI workers and core code."""

from __future__ import annotations

import hashlib
import logging

import pandas as pd

logger = logging.getLogger(__name__)


def _fallback_dataframe_hash_payload(dataframe: pd.DataFrame | None) -> bytes:
    if dataframe is None:
        return b"none"
    try:
        return dataframe.to_csv(index=False).encode("utf-8", errors="replace")
    except (AttributeError, KeyError, OverflowError, TypeError, ValueError) as exc:
        logger.debug("Fallback DataFrame serialization failed: %s", exc)
        fallback = repr((getattr(dataframe, "shape", "unknown"), id(dataframe)))
        return fallback.encode("utf-8", errors="replace")


def sample_dataframe_for_fingerprint(dataframe: pd.DataFrame) -> pd.DataFrame:
    row_count = len(dataframe)
    if row_count <= 24:
        return dataframe

    head_count = 8
    tail_count = 8
    mid_count = 8
    head_df = dataframe.head(head_count)
    tail_df = dataframe.tail(tail_count)
    mid_start = head_count
    tail_start = max(mid_start, row_count - tail_count)
    mid_end = tail_start - 1
    mid_indices: list[int] = []
    span = max(0, (mid_end - mid_start) + 1)
    if span > 0:
        if span <= mid_count:
            mid_indices = list(range(mid_start, mid_start + span))
        else:
            step = float(span - 1) / float(max(mid_count - 1, 1))
            mid_candidates = {
                min(
                    mid_end,
                    max(mid_start, mid_start + int(round(idx * step))),
                )
                for idx in range(mid_count)
            }
            mid_indices = sorted(mid_candidates)
    mid_df = dataframe.iloc[mid_indices] if mid_indices else dataframe.iloc[0:0]
    return pd.concat(
        [head_df, mid_df, tail_df],
        axis=0,
        ignore_index=True,
    )


def build_dataframe_filter_hash(dataframe: pd.DataFrame | None) -> str:
    try:
        if dataframe is None:
            return hashlib.blake2b(b"none", digest_size=8).hexdigest()

        data_hashes = pd.util.hash_pandas_object(
            dataframe,
            index=False,
        ).to_numpy(dtype="uint64", copy=False)
        hasher = hashlib.blake2b(digest_size=8)
        hasher.update(repr(tuple(dataframe.shape)).encode("utf-8"))
        hasher.update(b"\x00cols:")
        for column in dataframe.columns:
            encoded_column = str(column).encode("utf-8", errors="replace")
            hasher.update(len(encoded_column).to_bytes(4, "big"))
            hasher.update(encoded_column)
        hasher.update(b"\x00dtypes:")
        for dtype in dataframe.dtypes:
            encoded_dtype = str(dtype).encode("utf-8", errors="replace")
            hasher.update(len(encoded_dtype).to_bytes(4, "big"))
            hasher.update(encoded_dtype)
        revision = getattr(dataframe, "attrs", {}).get("ssa_data_revision")
        if revision is not None:
            hasher.update(b"\x00revision:")
            hasher.update(str(revision).encode("utf-8", errors="replace"))
        hasher.update(data_hashes.tobytes())
        return hasher.hexdigest()
    except (AttributeError, KeyError, OverflowError, TypeError, ValueError) as exc:
        logger.debug(
            "Fallback to shape-only DataFrame hash due to fingerprint error: %s",
            exc,
        )
        return hashlib.blake2b(
            _fallback_dataframe_hash_payload(dataframe),
            digest_size=8,
        ).hexdigest()
