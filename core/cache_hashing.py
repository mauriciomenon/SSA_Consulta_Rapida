"""Deterministic hashing helpers for DataFrame cache keys."""

import hashlib
import json
from datetime import datetime
from typing import Any, Dict, Optional

import pandas as pd


def _stable_json_sort_key(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)


def _stable_json_mapping(value: dict, seen: set[int]) -> Dict[str, Any]:
    items = [
        [_stable_json_value(key, seen), _stable_json_value(item, seen)]
        for key, item in value.items()
    ]
    return {"__dict__": sorted(items, key=lambda item: _stable_json_sort_key(item[0]))}


def _stable_json_sequence(value: list | tuple, seen: set[int]) -> Any:
    converted = [_stable_json_value(item, seen) for item in value]
    if isinstance(value, tuple):
        return {"__tuple__": converted}
    return converted


def _stable_json_set(value: set, seen: set[int]) -> Dict[str, Any]:
    converted = [_stable_json_value(item, seen) for item in value]
    return {"__set__": sorted(converted, key=_stable_json_sort_key)}


def _stable_json_object(value: Any, seen: set[int]) -> Dict[str, Any]:
    type_name = f"{type(value).__module__}.{type(value).__qualname__}"
    state = None
    try:
        state = vars(value)
    except (TypeError, AttributeError, RuntimeError, ValueError):
        state = None
    if state:
        return {
            "__object__": type_name,
            "state": _stable_json_value(state, seen),
        }
    return {"__object__": type_name}


def _stable_json_value(value: Any, seen: Optional[set[int]] = None) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, datetime):
        return {"__datetime__": value.isoformat()}
    if isinstance(value, bytes):
        return {"__bytes__": value.hex()}

    if seen is None:
        seen = set()
    value_id = id(value)
    if value_id in seen:
        return {"__cycle__": type(value).__name__}
    seen.add(value_id)
    try:
        if isinstance(value, dict):
            return _stable_json_mapping(value, seen)
        if isinstance(value, (list, tuple)):
            return _stable_json_sequence(value, seen)
        if isinstance(value, set):
            return _stable_json_set(value, seen)
        return _stable_json_object(value, seen)
    finally:
        seen.remove(value_id)


def _stable_json_bytes(value: Any) -> bytes:
    return json.dumps(
        _stable_json_value(value),
        sort_keys=True,
        separators=(",", ":"),
    ).encode()


def _dataframe_index_metadata(index: pd.Index) -> Dict[str, Any]:
    if isinstance(index, pd.RangeIndex):
        return {
            "__range_index__": {
                "start": index.start,
                "stop": index.stop,
                "step": index.step,
                "name": index.name,
            }
        }
    if isinstance(index, pd.MultiIndex):
        return {
            "__index__": type(index).__name__,
            "length": len(index),
            "names": tuple(index.names),
        }
    return {
        "__index__": type(index).__name__,
        "length": len(index),
        "name": index.name,
    }


def hash_dataframe_object_content(df: pd.DataFrame) -> str:
    chunk_size = 512
    digest = hashlib.md5(usedforsecurity=False)
    for metadata_value in (_dataframe_index_metadata(df.index), tuple(df.columns)):
        digest.update(_stable_json_bytes(metadata_value))
        digest.update(b"\0")

    include_index_values = not isinstance(df.index, pd.RangeIndex)
    rows = df.itertuples(index=False, name=None)
    indexed_rows = zip(df.index, rows) if include_index_values else rows
    chunk = []
    for row in indexed_rows:
        chunk.append(row)
        if len(chunk) >= chunk_size:
            digest.update(_stable_json_bytes(chunk))
            digest.update(b"\0")
            chunk.clear()
    if chunk:
        digest.update(_stable_json_bytes(chunk))
        digest.update(b"\0")
    return digest.hexdigest()
