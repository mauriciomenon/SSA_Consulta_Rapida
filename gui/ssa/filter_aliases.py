"""Column filter alias loading."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from utils.robust_logging import get_robust_logger

logger = get_robust_logger().get_logger(__name__, "gui")

_FILTER_ALIASES_PATH = Path(__file__).resolve().parents[2] / "config" / "filter_aliases.json"


@lru_cache(maxsize=1)
def load_filter_alias_map_once() -> dict[str, Any]:
    try:
        if _FILTER_ALIASES_PATH.exists():
            with _FILTER_ALIASES_PATH.open("r", encoding="utf-8") as file_obj:
                data = json.load(file_obj)
            if isinstance(data, dict):
                return data
    except Exception as exc:
        logger.debug("Falha ao carregar aliases de filtro em arquivo local: %s", exc)
    return {}
