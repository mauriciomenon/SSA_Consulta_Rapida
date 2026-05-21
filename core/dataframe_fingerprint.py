"""DataFrame fingerprint helpers shared by GUI workers and core code."""

from __future__ import annotations

import hashlib
import logging

import pandas as pd

logger = logging.getLogger(__name__)


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

        sample_df = sample_dataframe_for_fingerprint(dataframe)
        sample_hashes = pd.util.hash_pandas_object(
            sample_df,
            index=False,
        ).to_numpy(dtype="uint64", copy=False)
        hasher = hashlib.blake2b(digest_size=8)
        hasher.update(repr(tuple(dataframe.shape)).encode("utf-8"))
        column_blob = "\x1f".join(str(column) for column in dataframe.columns)
        dtype_blob = "\x1f".join(str(dtype) for dtype in dataframe.dtypes)
        hasher.update(b"\x00cols:")
        hasher.update(column_blob.encode("utf-8", errors="replace"))
        hasher.update(b"\x00dtypes:")
        hasher.update(dtype_blob.encode("utf-8", errors="replace"))
        revision = getattr(dataframe, "attrs", {}).get("ssa_data_revision")
        if revision is not None:
            hasher.update(b"\x00revision:")
            hasher.update(str(revision).encode("utf-8", errors="replace"))
        hasher.update(sample_hashes.tobytes())
        return hasher.hexdigest()
    except (AttributeError, KeyError, TypeError, ValueError) as exc:
        logger.debug(
            "Fallback to shape-only DataFrame hash due to fingerprint error: %s",
            exc,
        )
        fallback = str(getattr(dataframe, "shape", "unknown"))
        return hashlib.blake2b(
            fallback.encode("utf-8"),
            digest_size=8,
        ).hexdigest()
