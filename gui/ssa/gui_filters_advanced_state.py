# gui/ssa/gui_filters_advanced_state.py
# Relation: holds shared constants and state helpers for advanced filters.

from __future__ import annotations

from collections import OrderedDict

DIVISAO_SETORES = {}
SECTOR_TO_DIV = {}
MONO_FONT_FAMILY = "monospace"
ADV_FILTER_CACHE_ATTRS = (
    "_adv_str_cache",
    "_adv_norm_cache",
    "_adv_clean_cache",
    "_adv_values_cache",
)


def prune_adv_cache(cache: dict, max_entries: int) -> None:
    if len(cache) <= max_entries:
        return
    if isinstance(cache, OrderedDict):
        while len(cache) > max_entries:
            cache.popitem(last=False)
        return
    while len(cache) > max_entries:
        try:
            oldest_key = next(iter(cache))
        except StopIteration:
            break
        cache.pop(oldest_key, None)


def configure_adv_filters_constants(divisao_setores, sector_to_div, mono_font_family):
    global DIVISAO_SETORES, SECTOR_TO_DIV, MONO_FONT_FAMILY
    DIVISAO_SETORES = divisao_setores or {}
    SECTOR_TO_DIV = sector_to_div or {}
    if mono_font_family:
        MONO_FONT_FAMILY = mono_font_family


class AdvancedFilterState:
    def __init__(self, window):
        self._window = window
        if window is None:
            return
        if not hasattr(window, "_adv_cache_token"):
            window._adv_cache_token = -1
        for attr_name in ADV_FILTER_CACHE_ATTRS:
            cache = getattr(window, attr_name, None)
            if not isinstance(cache, dict):
                setattr(window, attr_name, OrderedDict())

    @property
    def filters(self) -> dict:
        data = getattr(self._window, "_advanced_filters", None)
        return data if isinstance(data, dict) else {}

    @filters.setter
    def filters(self, value: dict) -> None:
        setattr(self._window, "_advanced_filters", value)

    def get_cache(self, attr_name: str) -> dict:
        cache = getattr(self._window, attr_name, None)
        if not isinstance(cache, OrderedDict):
            cache = OrderedDict(cache) if isinstance(cache, dict) else OrderedDict()
            setattr(self._window, attr_name, cache)
        return cache

    def clear_caches(self) -> None:
        for attr_name in ADV_FILTER_CACHE_ATTRS:
            cache = getattr(self._window, attr_name, None)
            if isinstance(cache, dict):
                cache.clear()
