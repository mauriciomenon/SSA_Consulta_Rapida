# gui/ssa/gui_filters_responsavel_refresh.py
# Relation: owns responsible-filter option refresh and ranking for advanced filters.

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pandas as pd

from utils.robust_logging import get_robust_logger

from .filter_domain_rules import (
    build_responsavel_sector_counts_by_column,
    collect_nonempty_column_values,
    filter_responsavel_frame_by_sector_selection,
    generate_responsavel_sector_filter_cache_signature,
    order_responsavel_values,
)
from .gui_filters_advanced_logic import RESPONSAVEL_FILTER_COLUMN_CANDIDATES
from .gui_filters_advanced_state import SECTOR_TO_DIV
from .gui_filters_responsavel_state import responsavel_materialization_state

logger = get_robust_logger().get_logger(__name__, "gui")
RESPONSAVEL_CACHE_MAX_ENTRIES = 8


@dataclass(frozen=True)
class ResponsavelPrefixPayload:
    key_name: str
    prefix: str
    source_col: str | None
    values: list[tuple[str, str]]
    selected: set[Any]
    excluded: set[Any]


class ResponsavelOptionsRefresher:
    def __init__(self, window) -> None:
        self.window = window
        self.responsavel_state = responsavel_materialization_state(window)
        self._filtered_cache: dict[str, Any] = {}
        self._rank_cache: dict[Any, Any] = {}
        self._value_cache: dict[Any, list[tuple[str, str]]] = {}
        self._cache_generation = self._current_generation()

    @property
    def all_prefixes(self) -> set[str]:
        return self.responsavel_state.all_prefixes

    @property
    def dirty_prefixes(self) -> set[str]:
        return self.responsavel_state.dirty_prefixes

    @property
    def built_prefixes(self) -> set[str]:
        return self.responsavel_state.built_prefixes

    def mark_dirty(self, prefixes=None) -> None:
        self.responsavel_state.mark_dirty(prefixes)

    def ensure_materialized(
        self,
        target_prefix: str | None = None,
        force: bool = False,
    ) -> None:
        if target_prefix:
            if target_prefix not in self.all_prefixes:
                return
            target_prefixes = {target_prefix}
        else:
            target_prefixes = set(self.all_prefixes)
        if not force and target_prefixes.issubset(self.built_prefixes) and not (
            target_prefixes & self.dirty_prefixes
        ):
            return
        if getattr(self.window, "_responsavel_refreshing", False):
            return
        self.window._responsavel_refreshing = True
        try:
            self.window._refresh_responsavel_options(target_prefixes=target_prefixes)
        finally:
            self.window._responsavel_refreshing = False

    def filtered_frame(self, frame: pd.DataFrame) -> pd.DataFrame:
        selection = self._sector_selection()
        cache_key = generate_responsavel_sector_filter_cache_signature(
            frame,
            data_load_token=getattr(self.window, "_data_load_token", None),
            executor_include=selection["executor_include"],
            executor_exclude=selection["executor_exclude"],
            emissor_include=selection["emissor_include"],
            emissor_exclude=selection["emissor_exclude"],
        )
        cached_frame = self._cached_filtered_frame(cache_key)
        if cached_frame is not None:
            return cached_frame
        filtered = filter_responsavel_frame_by_sector_selection(
            frame,
            executor_include=selection["executor_include"],
            executor_exclude=selection["executor_exclude"],
            emissor_include=selection["emissor_include"],
            emissor_exclude=selection["emissor_exclude"],
        )
        self._filtered_cache = {"key": cache_key, "frame": filtered}
        return filtered

    def _sector_selection(self) -> dict[str, list[str]]:
        window = self.window
        return {
            "executor_include": window._get_checked_values(
                getattr(window, "adv_executor_checks", None)
            ),
            "executor_exclude": window._get_checked_values(
                getattr(window, "adv_executor_exclude_checks", None)
            ),
            "emissor_include": window._get_checked_values(
                getattr(window, "adv_emissor_checks", None)
            ),
            "emissor_exclude": window._get_checked_values(
                getattr(window, "adv_emissor_exclude_checks", None)
            ),
        }

    def _cached_filtered_frame(self, cache_key: tuple[Any, ...]) -> pd.DataFrame | None:
        if self._filtered_cache.get("key") != cache_key:
            return None
        cached_frame = self._filtered_cache.get("frame")
        if isinstance(cached_frame, pd.DataFrame):
            return cached_frame
        return None

    def sorted_values(
        self, df_subset, values, resp_col: str, df_source=None
    ) -> list[tuple[str, str]]:
        if not values:
            return []
        source_df = df_source if isinstance(df_source, pd.DataFrame) else df_subset
        cache_key = self._rank_cache_key(source_df)
        counts_by_column = self._rank_cache.get(cache_key)
        if not isinstance(counts_by_column, dict):
            counts_by_column = build_responsavel_sector_counts_by_column(
                source_df, RESPONSAVEL_FILTER_COLUMN_CANDIDATES
            )
            self._rank_cache[cache_key] = counts_by_column
            _trim_cache(self._rank_cache)
        sector_counts = counts_by_column.get(resp_col, {})
        return order_responsavel_values(
            values, sector_counts, sector_to_div=SECTOR_TO_DIV
        )

    def _rank_cache_key(self, source_df: pd.DataFrame) -> tuple[Any, ...]:
        data_token = getattr(self.window, "_data_load_token", None)
        if data_token is not None:
            source_key = ("data_load_token", data_token)
        else:
            source_key = (
                "df_completo",
                id(getattr(self.window, "df_completo", source_df)),
            )
        return (source_key, len(source_df), id(source_df.columns))

    def option_values(
        self, frame: pd.DataFrame, source_col: str
    ) -> list[tuple[str, str]]:
        cache_key = self._option_values_cache_key(frame, source_col)
        cached_values = self._value_cache.get(cache_key)
        if cached_values is not None:
            return cached_values
        try:
            vals = collect_nonempty_column_values(frame, source_col)
        except Exception:
            vals = []
        values = self.sorted_values(
            frame,
            vals,
            source_col,
            df_source=getattr(self.window, "df_completo", frame),
        )
        self._value_cache[cache_key] = values
        _trim_cache(self._value_cache)
        return values

    def _option_values_cache_key(
        self, frame: pd.DataFrame, source_col: str
    ) -> tuple[Any, ...]:
        return (
            getattr(self.window, "_data_load_token", None),
            id(frame),
            len(frame),
            id(frame.columns),
            source_col,
        )

    def refresh(self, target_prefixes=None) -> None:
        self._clear_caches_if_generation_changed()
        all_prefixes = self.all_prefixes
        if target_prefixes is None:
            requested_prefixes = set(all_prefixes)
        else:
            requested_prefixes = {p for p in target_prefixes if p in all_prefixes}
        if not requested_prefixes:
            return
        if self.window.df_completo is None or self.window.df_completo.empty:
            self.mark_dirty(prefixes=requested_prefixes)
            return

        df = self.filtered_frame(self.window.df_completo)
        processed_prefixes = set()
        updates_widget = getattr(self.window, "adv_filters_group", self.window)
        previous_updates_state = _set_updates_enabled(updates_widget, False)
        try:
            for payload in self._prepare_prefix_payloads(requested_prefixes, df):
                self._apply_prefix_payload(payload)
                processed_prefixes.add(payload.prefix)
        finally:
            if previous_updates_state is not None:
                _set_updates_enabled(updates_widget, previous_updates_state)
        self._refresh_derivadas_cache(df)
        self.responsavel_state.mark_materialized(processed_prefixes)

    def _prepare_prefix_payloads(
        self, requested_prefixes: set[str], df: pd.DataFrame
    ) -> list[ResponsavelPrefixPayload]:
        window = self.window
        filters = getattr(window, "_advanced_filters", None) or {}
        payloads: list[ResponsavelPrefixPayload] = []
        for key_name, prefix, candidate_cols in _responsavel_refresh_specs():
            if prefix not in requested_prefixes:
                continue
            source_col = next(
                (name for name in candidate_cols if name in window.df_completo.columns),
                None,
            )
            values = [] if source_col is None else self.option_values(df, source_col)
            payloads.append(
                ResponsavelPrefixPayload(
                    key_name=key_name,
                    prefix=prefix,
                    source_col=source_col,
                    values=values,
                    selected=set(filters.get(key_name) or []),
                    excluded=set(filters.get(f"{key_name}_exclude_values") or []),
                )
            )
        return payloads

    def _apply_prefix_payload(self, payload: ResponsavelPrefixPayload) -> None:
        window = self.window
        prefix = payload.prefix
        box = getattr(window, f"{prefix}_box", None)
        button = getattr(window, f"{prefix}_button", None)
        menu = getattr(window, f"{prefix}_menu", None)
        checks_attr = f"{prefix}_checks"
        exclude_checks_attr = f"{prefix}_exclude_checks"
        exclude = getattr(window, f"{prefix}_exclude", None)
        col_exists = payload.source_col is not None
        _set_visible(box, col_exists)
        if not col_exists:
            _set_enabled(button, False)
            _set_enabled(exclude, False)
            setattr(window, checks_attr, [])
            setattr(window, exclude_checks_attr, [])
            return

        _set_enabled(button, True)
        _set_enabled(exclude, True)
        include_checks, exclude_checks = window._rebuild_multiselect_menu(
            button,
            menu,
            payload.values,
            payload.selected,
            _summary_callback(window, button, checks_attr, exclude_checks_attr),
            True,
            payload.excluded,
            _summary_callback(window, button, checks_attr, exclude_checks_attr),
        )
        setattr(window, checks_attr, include_checks)
        setattr(window, exclude_checks_attr, exclude_checks)

    def _refresh_derivadas_cache(self, df: pd.DataFrame) -> None:
        adv_cache = getattr(self.window, "_adv_values_cache", {}) or {}
        cache_key = self._frame_cache_key(df)
        if adv_cache.get("derivadas_vals_key") != cache_key:
            adv_cache.pop("derivadas_vals", None)
        derivadas_numbers = adv_cache.get("derivadas_vals", [])
        if derivadas_numbers:
            return
        try:
            if "derivada_de" not in df.columns:
                return
            derivadas_series = self.window._normalize_ssa_series(df["derivada_de"])
            derivadas_numbers = sorted(
                {v for v in derivadas_series.unique() if v and str(v).strip()},
                key=lambda value: str(value).casefold(),
            )
            adv_cache["derivadas_vals"] = derivadas_numbers
            adv_cache["derivadas_vals_key"] = cache_key
            self.window._adv_values_cache = adv_cache
        except Exception as exc:
            logger.debug(
                "Falha ao atualizar cache de derivadas em filtros avancados: %s", exc
            )

    def _current_generation(self) -> tuple[Any, int]:
        return (
            getattr(self.window, "_data_load_token", None),
            id(getattr(self.window, "df_completo", None)),
        )

    def _clear_caches_if_generation_changed(self) -> None:
        generation = self._current_generation()
        if self._cache_generation == generation:
            return
        self._cache_generation = generation
        self._filtered_cache.clear()
        self._rank_cache.clear()
        self._value_cache.clear()

    def _frame_cache_key(self, frame: pd.DataFrame) -> tuple[Any, ...]:
        return (
            self._current_generation(),
            id(frame),
            len(frame),
            id(frame.columns),
        )


def _responsavel_refresh_specs():
    return (
        (
            "solicitante",
            "adv_responsavel_solicitante",
            RESPONSAVEL_FILTER_COLUMN_CANDIDATES["solicitante"],
        ),
        (
            "responsavel_programacao",
            "adv_responsavel_programacao",
            RESPONSAVEL_FILTER_COLUMN_CANDIDATES["responsavel_programacao"],
        ),
        (
            "responsavel_execucao",
            "adv_responsavel_execucao",
            RESPONSAVEL_FILTER_COLUMN_CANDIDATES["responsavel_execucao"],
        ),
    )


def _summary_callback(window, button, checks_attr: str, exclude_checks_attr: str):
    return lambda *_: window._update_multiselect_button(
        button,
        getattr(window, checks_attr, []),
        exclude_checks=getattr(window, exclude_checks_attr, None),
    )


def _set_enabled(widget, enabled: bool) -> None:
    if widget is None:
        return
    try:
        widget.setEnabled(bool(enabled))
    except Exception as exc:
        logger.debug("Falha ao ajustar estado enabled de widget %r: %s", widget, exc)


def _set_visible(widget, visible: bool) -> None:
    if widget is None:
        return
    try:
        widget.setVisible(bool(visible))
    except Exception as exc:
        logger.debug("Falha ao ajustar visibilidade de widget %r: %s", widget, exc)


def _set_updates_enabled(widget, enabled: bool) -> bool | None:
    if widget is None or not hasattr(widget, "setUpdatesEnabled"):
        return None
    try:
        previous = bool(widget.updatesEnabled()) if hasattr(
            widget, "updatesEnabled"
        ) else True
        widget.setUpdatesEnabled(bool(enabled))
        return previous
    except Exception as exc:
        logger.debug("Falha ao ajustar updatesEnabled em widget %r: %s", widget, exc)
        return None


def _trim_cache(cache: dict[Any, Any]) -> None:
    while len(cache) > RESPONSAVEL_CACHE_MAX_ENTRIES:
        try:
            cache.pop(next(iter(cache)))
        except StopIteration:
            return


def responsavel_options_refresher(window) -> ResponsavelOptionsRefresher:
    refresher = getattr(window, "_responsavel_options_refresher", None)
    if not isinstance(refresher, ResponsavelOptionsRefresher):
        refresher = ResponsavelOptionsRefresher(window)
        window._responsavel_options_refresher = refresher
    return refresher
