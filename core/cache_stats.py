"""Cache statistics helpers kept outside the cache storage class."""

import sys
from typing import Any, Dict, List

import pandas as pd


def copy_cache_details(details: Dict[str, Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    return {
        cache_name: {
            "entries": detail["entries"],
            "keys": list(detail["keys"]),
            "memory_estimate": detail["memory_estimate"],
        }
        for cache_name, detail in details.items()
    }


def estimate_cache_items_memory(items: List[tuple[str, Any]]) -> int:
    memory_estimate = 0
    max_stats_depth = 2
    max_stats_items = 2048
    seen: set[int] = set()
    visited_items = 0
    for _cache_key, value in items:
        stack = [(value, 0)]
        while stack:
            if visited_items >= max_stats_items:
                break
            item, depth = stack.pop()
            item_id = id(item)
            if item_id in seen:
                continue
            seen.add(item_id)
            visited_items += 1

            if isinstance(item, pd.DataFrame):
                memory_estimate += int(item.memory_usage(deep=False).sum())
                continue

            memory_estimate += sys.getsizeof(item)
            if depth >= max_stats_depth:
                continue
            if isinstance(item, dict):
                stack.extend((child, depth + 1) for child in item.keys())
                stack.extend((child, depth + 1) for child in item.values())
            elif isinstance(item, (list, tuple, set, frozenset)):
                stack.extend((child, depth + 1) for child in item)

    return memory_estimate


def build_cache_details(
    cache_snapshots: Dict[str, List[tuple[str, Any]]]
) -> Dict[str, Dict[str, Any]]:
    cache_details = {}
    for cache_name, items in cache_snapshots.items():
        cache_details[cache_name] = {
            "entries": len(items),
            "keys": [key for key, _value in items[:5]],
            "memory_estimate": estimate_cache_items_memory(items),
        }
    return cache_details
