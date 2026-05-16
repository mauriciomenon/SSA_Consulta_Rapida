# gui/ssa/gui_filters_responsavel_refresh.py
# Relation: owns responsible-filter option refresh and ranking for advanced filters.

from __future__ import annotations

from collections import OrderedDict
from dataclasses import dataclass
from typing import Any
from uuid import uuid4

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
RESPONSAVEL_WIDGET_BINDINGS = {
    "adv_responsavel_solicitante": (
        "adv_responsavel_solicitante_box",
        "adv_responsavel_solicitante_button",
        "adv_responsavel_solicitante_menu",
        "adv_responsavel_solicitante_exclude",
        "adv_responsavel_solicitante_checks",
        "adv_responsavel_solicitante_exclude_checks",
    ),
    "adv_responsavel_programacao": (
        "adv_responsavel_programacao_box",
        "adv_responsavel_programacao_button",
        "adv_responsavel_programacao_menu",
        "adv_responsavel_programacao_exclude",
        "adv_responsavel_programacao_checks",
        "adv_responsavel_programacao_exclude_checks",
    ),
    "adv_responsavel_execucao": (
        "adv_responsavel_execucao_box",
        "adv_responsavel_execucao_button",
        "adv_responsavel_execucao_menu",
        "adv_responsavel_execucao_exclude",
        "adv_responsavel_execucao_checks",
        "adv_responsavel_execucao_exclude_checks",
    ),
}


@dataclass(frozen=True)
class ResponsavelPrefixPayload:
    key_name: str
    prefix: str
    source_col: str | None
    values: list[tuple[str, str]]
    selected: set[Any]
    excluded: set[Any]


@dataclass(frozen=True)
class ResponsavelSectorSelection:
    executor_include: list[str]
    executor_exclude: list[str]
    emissor_include: list[str]
    emissor_exclude: list[str]


@dataclass(frozen=True)
class ResponsavelWidgetBinding:
    box: Any
    button: Any
    menu: Any
    exclude: Any
    checks_attr: str
    exclude_checks_attr: str


class ResponsavelRefreshView:
    def __init__(self, window) -> None:
        self.window = window

    @property
    def data_load_token(self):
        return getattr(self.window, "_data_load_token", None)

    @property
    def df_completo(self):
        return getattr(self.window, "df_completo", None)

    @property
    def advanced_filters(self) -> dict:
        return getattr(self.window, "_advanced_filters", None) or {}

    @property
    def updates_widget(self):
        return getattr(self.window, "adv_filters_group", self.window)

    def checked_values(self, attr_name: str) -> list[str]:
        return self.window._get_checked_values(getattr(self.window, attr_name, None))

    def sector_selection(self) -> ResponsavelSectorSelection:
        return ResponsavelSectorSelection(
            executor_include=self.checked_values("adv_executor_checks"),
            executor_exclude=self.checked_values("adv_executor_exclude_checks"),
            emissor_include=self.checked_values("adv_emissor_checks"),
            emissor_exclude=self.checked_values("adv_emissor_exclude_checks"),
        )

    def binding(self, prefix: str) -> ResponsavelWidgetBinding:
        binding = RESPONSAVEL_WIDGET_BINDINGS[prefix]
        box_attr, button_attr, menu_attr, exclude_attr, checks_attr, exclude_attr_checks = (
            binding
        )
        return ResponsavelWidgetBinding(
            box=getattr(self.window, box_attr, None),
            button=getattr(self.window, button_attr, None),
            menu=getattr(self.window, menu_attr, None),
            exclude=getattr(self.window, exclude_attr, None),
            checks_attr=checks_attr,
            exclude_checks_attr=exclude_attr_checks,
        )

    def set_check_lists(
        self,
        binding: ResponsavelWidgetBinding,
        include_checks,
        exclude_checks,
    ) -> None:
        setattr(self.window, binding.checks_attr, include_checks)
        setattr(self.window, binding.exclude_checks_attr, exclude_checks)

    def rebuild_menu(self, payload: ResponsavelPrefixPayload, binding):
        callback = _summary_callback(
            self.window,
            binding.button,
            binding.checks_attr,
            binding.exclude_checks_attr,
        )
        return self.window._rebuild_multiselect_menu(
            binding.button,
            binding.menu,
            payload.values,
            payload.selected,
            callback,
            True,
            payload.excluded,
            callback,
        )

    def set_updates_enabled(self, enabled: bool) -> bool | None:
        return _set_updates_enabled(self.updates_widget, enabled)

    def set_binding_visible(self, binding: ResponsavelWidgetBinding, visible: bool):
        _set_visible(binding.box, visible)

    def set_binding_enabled(self, binding: ResponsavelWidgetBinding, enabled: bool):
        _set_enabled(binding.button, enabled)
        _set_enabled(binding.exclude, enabled)

    def normalize_ssa_series(self, series: pd.Series) -> pd.Series:
        return self.window._normalize_ssa_series(series)


class ResponsavelRefreshCache:
    def __init__(self, view: ResponsavelRefreshView) -> None:
        self.view = view
        self.filtered: OrderedDict[tuple[Any, ...], pd.DataFrame] = OrderedDict()
        self.rank: OrderedDict[Any, Any] = OrderedDict()
        self.values: OrderedDict[Any, list[tuple[str, str]]] = OrderedDict()
        self.frame_tokens: OrderedDict[int, str] = OrderedDict()
        self.generation = self.current_generation()

    def current_generation(self) -> tuple[Any, int]:
        df = self.view.df_completo
        fallback_token = (
            self.frame_token(df)
            if isinstance(df, pd.DataFrame)
            else id(df)
        )
        return (
            self.view.data_load_token or fallback_token,
            len(df) if isinstance(df, pd.DataFrame) else 0,
        )

    def clear_if_generation_changed(self) -> None:
        generation = self.current_generation()
        if self.generation == generation:
            return
        self.generation = generation
        self.filtered.clear()
        self.rank.clear()
        self.values.clear()
        self.frame_tokens.clear()

    def filtered_frame(
        self,
        frame: pd.DataFrame,
        selection: ResponsavelSectorSelection,
    ) -> pd.DataFrame | None:
        cache_key = self.filtered_frame_key(frame, selection)
        cached_frame = self.filtered.get(cache_key)
        if isinstance(cached_frame, pd.DataFrame):
            self.filtered.move_to_end(cache_key)
            return cached_frame
        return None

    def filtered_frame_key(
        self,
        frame: pd.DataFrame,
        selection: ResponsavelSectorSelection,
    ) -> tuple[Any, ...]:
        return generate_responsavel_sector_filter_cache_signature(
            frame,
            data_load_token=self.view.data_load_token,
            executor_include=selection.executor_include,
            executor_exclude=selection.executor_exclude,
            emissor_include=selection.emissor_include,
            emissor_exclude=selection.emissor_exclude,
        )

    def store_filtered_frame(self, cache_key: tuple[Any, ...], frame: pd.DataFrame):
        self.filtered[cache_key] = frame
        self.filtered.move_to_end(cache_key)
        _trim_ordered_cache(self.filtered)

    def counts_by_column(self, source_df: pd.DataFrame) -> dict:
        cache_key = self.rank_key(source_df)
        counts_by_column = self.rank.get(cache_key)
        if isinstance(counts_by_column, dict):
            self.rank.move_to_end(cache_key)
            return counts_by_column
        counts_by_column = build_responsavel_sector_counts_by_column(
            source_df, RESPONSAVEL_FILTER_COLUMN_CANDIDATES
        )
        self.rank[cache_key] = counts_by_column
        _trim_ordered_cache(self.rank)
        return counts_by_column

    def rank_key(self, source_df: pd.DataFrame) -> tuple[Any, ...]:
        data_token = self.view.data_load_token
        if data_token is not None:
            return ("data_load_token", data_token, len(source_df))
        return ("frame_token", self.frame_token(source_df), len(source_df))

    def frame_token(self, source_df: pd.DataFrame) -> str:
        frame_id = id(source_df)
        token = self.frame_tokens.get(frame_id)
        if token is None:
            token = uuid4().hex
            self.frame_tokens[frame_id] = token
            self.frame_tokens.move_to_end(frame_id)
            _trim_ordered_cache(self.frame_tokens)
        return token

    def option_values(
        self,
        frame: pd.DataFrame,
        source_col: str,
        frame_key: tuple[Any, ...],
        builder,
    ) -> list[tuple[str, str]]:
        cache_key = (
            frame_key,
            source_col,
        )
        cached_values = self.values.get(cache_key)
        if cached_values is not None:
            self.values.move_to_end(cache_key)
            return cached_values
        values = builder()
        self.values[cache_key] = values
        _trim_ordered_cache(self.values)
        return values


class ResponsavelOptionsRefresher:
    def __init__(self, window) -> None:
        self.window = window
        self.view = ResponsavelRefreshView(window)
        self.responsavel_state = responsavel_materialization_state(window)
        self.cache = ResponsavelRefreshCache(self.view)
        self._active_filtered_key: tuple[Any, ...] | None = None
        self._refreshing = False

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
        if self._refreshing:
            return
        self._refreshing = True
        try:
            self.window._refresh_responsavel_options(target_prefixes=target_prefixes)
        finally:
            self._refreshing = False

    def filtered_frame(self, frame: pd.DataFrame) -> pd.DataFrame:
        selection = self.view.sector_selection()
        return self._filtered_frame_for_selection(frame, selection)

    def _filtered_frame_for_selection(
        self,
        frame: pd.DataFrame,
        selection: ResponsavelSectorSelection,
    ) -> pd.DataFrame:
        cache_key = self.cache.filtered_frame_key(frame, selection)
        self._active_filtered_key = cache_key
        cached_frame = self.cache.filtered_frame(frame, selection)
        if cached_frame is not None:
            return cached_frame
        return self._cache_filtered_frame(frame, selection, cache_key)

    def _cache_filtered_frame(
        self,
        frame: pd.DataFrame,
        selection: ResponsavelSectorSelection,
        cache_key: tuple[Any, ...],
    ) -> pd.DataFrame:
        filtered = filter_responsavel_frame_by_sector_selection(
            frame,
            executor_include=selection.executor_include,
            executor_exclude=selection.executor_exclude,
            emissor_include=selection.emissor_include,
            emissor_exclude=selection.emissor_exclude,
        )
        self.cache.store_filtered_frame(cache_key, filtered)
        return filtered

    def sorted_values(
        self, df_subset, values, resp_col: str, df_source=None
    ) -> list[tuple[str, str]]:
        if not values:
            return []
        source_df = df_source if isinstance(df_source, pd.DataFrame) else df_subset
        counts_by_column = self.cache.counts_by_column(source_df)
        sector_counts = counts_by_column.get(resp_col, {})
        return order_responsavel_values(
            values, sector_counts, sector_to_div=SECTOR_TO_DIV
        )

    def option_values(
        self, frame: pd.DataFrame, source_col: str
    ) -> list[tuple[str, str]]:
        return self.cache.option_values(
            frame,
            source_col,
            self._active_filtered_key
            or self.cache.filtered_frame_key(frame, self.view.sector_selection()),
            lambda: self._build_option_values(frame, source_col),
        )

    def _build_option_values(
        self,
        frame: pd.DataFrame,
        source_col: str,
    ) -> list[tuple[str, str]]:
        try:
            vals = collect_nonempty_column_values(frame, source_col)
        except Exception:
            vals = []
        source_df = self.view.df_completo
        if not isinstance(source_df, pd.DataFrame):
            source_df = frame
        return self.sorted_values(
            frame,
            vals,
            source_col,
            df_source=source_df,
        )

    def refresh(self, target_prefixes=None) -> None:
        self.cache.clear_if_generation_changed()
        all_prefixes = self.all_prefixes
        if target_prefixes is None:
            requested_prefixes = set(all_prefixes)
        else:
            requested_prefixes = {p for p in target_prefixes if p in all_prefixes}
        if not requested_prefixes:
            return
        source_df = self.view.df_completo
        if source_df is None or source_df.empty:
            self.mark_dirty(prefixes=requested_prefixes)
            return

        df = self.filtered_frame(source_df)
        processed_prefixes = set()
        previous_updates_state = self.view.set_updates_enabled(False)
        try:
            for payload in self._prepare_prefix_payloads(requested_prefixes, df):
                self._apply_prefix_payload(payload)
                processed_prefixes.add(payload.prefix)
        finally:
            if previous_updates_state is not None:
                self.view.set_updates_enabled(previous_updates_state)
        self.responsavel_state.mark_materialized(processed_prefixes)

    def _prepare_prefix_payloads(
        self, requested_prefixes: set[str], df: pd.DataFrame
    ) -> list[ResponsavelPrefixPayload]:
        filters = self.view.advanced_filters
        payloads: list[ResponsavelPrefixPayload] = []
        values_by_source: dict[str, list[tuple[str, str]]] = {}
        available_columns = set(self.view.df_completo.columns)
        for key_name, prefix, candidate_cols in _responsavel_refresh_specs():
            if prefix not in requested_prefixes:
                continue
            source_col = next(
                (name for name in candidate_cols if name in available_columns),
                None,
            )
            if source_col is None:
                values = []
            else:
                if source_col not in values_by_source:
                    values_by_source[source_col] = self.option_values(df, source_col)
                values = values_by_source[source_col]
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
        binding = self.view.binding(payload.prefix)
        col_exists = payload.source_col is not None
        self.view.set_binding_visible(binding, col_exists)
        if not col_exists:
            self.view.set_binding_enabled(binding, False)
            self.view.set_check_lists(binding, [], [])
            return

        self.view.set_binding_enabled(binding, True)
        include_checks, exclude_checks = self.view.rebuild_menu(payload, binding)
        self.view.set_check_lists(binding, include_checks, exclude_checks)

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
        exclude_checks=getattr(window, exclude_checks_attr, []),
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


def _trim_ordered_cache(cache: OrderedDict[Any, Any]) -> None:
    while len(cache) > RESPONSAVEL_CACHE_MAX_ENTRIES:
        cache.popitem(last=False)


def responsavel_options_refresher(window) -> ResponsavelOptionsRefresher:
    refresher = getattr(window, "_responsavel_options_refresher", None)
    if not isinstance(refresher, ResponsavelOptionsRefresher):
        refresher = ResponsavelOptionsRefresher(window)
        window._responsavel_options_refresher = refresher
    return refresher
