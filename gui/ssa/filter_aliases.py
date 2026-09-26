"""Column filter alias loading."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from utils.robust_logging import get_robust_logger

logger = get_robust_logger().get_logger(__name__, "gui")

_FILTER_ALIASES_PATH = Path(__file__).resolve().parents[2] / "config" / "filter_aliases.json"


def load_filter_alias_map_once() -> dict[str, Any]:
    return dict(_load_filter_alias_map_cached(_filter_alias_signature()))


@lru_cache(maxsize=1)
def _load_filter_alias_map_cached(_signature: tuple[int, int] | None) -> dict[str, Any]:
    try:
        if _FILTER_ALIASES_PATH.exists():
            with _FILTER_ALIASES_PATH.open("r", encoding="utf-8") as file_obj:
                data = json.load(file_obj)
            if isinstance(data, dict):
                return data
    except Exception as exc:
        logger.debug("Falha ao carregar aliases de filtro em arquivo local: %s", exc)
    return {}


def _filter_alias_signature() -> tuple[int, int] | None:
    try:
        stat = _FILTER_ALIASES_PATH.stat()
        return int(stat.st_mtime_ns), int(stat.st_size)
    except FileNotFoundError:
        return None
    except Exception as exc:
        logger.debug("Falha ao assinar arquivo de aliases de filtro: %s", exc)
        return None


setattr(load_filter_alias_map_once, "cache_clear", _load_filter_alias_map_cached.cache_clear)
