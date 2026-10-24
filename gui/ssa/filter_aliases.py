"""Column filter alias loading."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from core.config_manager import resolve_config_path
from utils.robust_logging import get_robust_logger

logger = get_robust_logger().get_logger(__name__, "gui")


def _filter_aliases_path() -> Path:
    """filter_aliases.json na pasta de config ativa (CF-08)."""
    return Path(resolve_config_path("filter_aliases.json"))


def load_filter_alias_map_once() -> dict[str, Any]:
    path = _filter_aliases_path()
    return dict(_load_filter_alias_map_cached(path, _filter_alias_signature(path)))


@lru_cache(maxsize=1)
def _load_filter_alias_map_cached(
    path: Path, _signature: tuple[int, int] | None
) -> dict[str, Any]:
    try:
        if path.exists():
            with path.open("r", encoding="utf-8") as file_obj:
                data = json.load(file_obj)
            if isinstance(data, dict):
                return data
    except Exception as exc:
        logger.debug("Falha ao carregar aliases de filtro em arquivo local: %s", exc)
    return {}


def _filter_alias_signature(path: Path) -> tuple[int, int] | None:
    try:
        stat = path.stat()
        return int(stat.st_mtime_ns), int(stat.st_size)
    except FileNotFoundError:
        return None
    except Exception as exc:
        logger.debug("Falha ao assinar arquivo de aliases de filtro: %s", exc)
        return None


setattr(load_filter_alias_map_once, "cache_clear", _load_filter_alias_map_cached.cache_clear)
