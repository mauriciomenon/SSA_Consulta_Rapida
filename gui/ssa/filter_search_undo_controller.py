"""General search and undo state controller helpers."""

from __future__ import annotations

from collections import OrderedDict
from typing import Any, cast

import pandas as pd

from gui.ssa.filter_state_utils import copy_filter_mapping, freeze_filter_state_value
from gui.ssa.search_refinement import can_reuse_refined_search
from utils.robust_logging import get_robust_logger

logger = get_robust_logger().get_logger(__name__, "gui")


def _can_use_last_search_result(
    window: Any,
    *,
    last_search_filtered: Any,
    has_column_filters: bool,
) -> bool:
    if not isinstance(last_search_filtered, pd.DataFrame):
        return False
    if not list(last_search_filtered.columns):
        return False
    if getattr(window, "_advanced_filters_active", False):
        return False
    if has_column_filters:
        return False
    if getattr(window, "_exclude_ste_sca", False):
        return False
    if getattr(window, "filter_thread", None) is not None:
        return False
    return True


def _can_reuse_normalized_terms(
    previous_terms: list[str],
    current_terms: list[str],
) -> bool:
    if not (previous_terms and current_terms):
        return False
    return can_reuse_refined_search(previous_terms, current_terms)


def _read_search_text(window: Any, *, is_widget_valid=None) -> str:
    search_widget = getattr(window, "search_input", None)
    if search_widget is None:
        return ""
    if is_widget_valid is not None and not is_widget_valid(search_widget):
        return ""
    try:
        return str(cast(Any, search_widget).text() or "").strip()
    except RuntimeError:
        return ""


def current_general_search_text(window: Any, *, is_widget_valid) -> str:
    return _read_search_text(window, is_widget_valid=is_widget_valid)


def _snapshot_search_text(window: Any) -> str:
    try:
        active_display = getattr(window, "_active_filter_search_display", "")
        if active_display is None:
            return ""
        return str(active_display).strip()
    except RuntimeError as exc:
        logger.debug("Falha ao capturar texto de busca para snapshot: %s", exc)
        return ""


def select_general_filter_source_candidate(
    window: Any,
    search_text: str,
) -> pd.DataFrame:
    filter_source_candidate = window.df_completo
    try:
        last_search_filtered = getattr(window, "_df_last_search_filtered", None)
        column_filters = getattr(window, "_active_column_filters", {}) or {}
        has_column_filters = any(
            str(filter_value).strip() for filter_value in column_filters.values()
        )
        previous_search_display = str(
            getattr(window, "_active_filter_search_display", "") or ""
        ).strip()
        if not _can_use_last_search_result(
            window,
            last_search_filtered=last_search_filtered,
            has_column_filters=has_column_filters,
        ):
            return filter_source_candidate
        previous_terms = (
            window._normalize_chunk_for_parse(previous_search_display)
            if previous_search_display
            else []
        )
        current_terms = (
            window._normalize_chunk_for_parse(search_text) if search_text else []
        )
        if _can_reuse_normalized_terms(previous_terms, current_terms):
            filter_source_candidate = cast(pd.DataFrame, last_search_filtered)
    except Exception as exc:
        logger.debug(
            "Falha ao avaliar refinamento seguro da busca; usando df_completo: %s",
            exc,
        )
    return filter_source_candidate


def safe_store_last_filter_state(
    window: Any,
    reason: str = "",
    *,
    search_text_override: str | None = None,
    pending_search_display_override: str | None = None,
) -> None:
    window._filter_cache_context_dirty = True
    try:
        store_last_filter_state(
            window,
            search_text_override=search_text_override,
            pending_search_display_override=pending_search_display_override,
        )
    except AttributeError as exc:
        if reason:
            logger.debug("Historico de filtros indisponivel (%s): %s", reason, exc)
        else:
            logger.debug("Historico de filtros indisponivel: %s", exc)
    except Exception as exc:
        if reason:
            logger.warning("Falha ao salvar historico de filtros (%s): %s", reason, exc)
        else:
            logger.warning("Falha ao salvar historico de filtros: %s", exc)


def snapshot_filter_state(
    window: Any,
    *,
    search_text_override: str | None = None,
    pending_search_display_override: str | None = None,
) -> dict:
    search_text = (
        str(search_text_override)
        if search_text_override is not None
        else _snapshot_search_text(window)
    )
    try:
        active_filters = OrderedDict(window._active_column_filters or {})
    except Exception:
        active_filters = OrderedDict()
    groups_snapshot = []
    for group in getattr(window, "_column_or_groups", []) or []:
        if not isinstance(group, dict):
            continue
        groups_snapshot.append(
            {
                "columns": tuple(group.get("columns", ())),
                "values": list(group.get("values", ())),
            }
        )
    return {
        "search_text": search_text,
        "pending_search_display": (
            pending_search_display_override
            if pending_search_display_override is not None
            else getattr(window, "_pending_search_display", None)
        ),
        "active_column_filters": active_filters,
        "column_or_groups": groups_snapshot,
        "exclude_ste_sca": bool(getattr(window, "_exclude_ste_sca", False)),
        "advanced_filters": copy_filter_mapping(
            getattr(window, "_advanced_filters", None)
        ),
        "advanced_filters_active": bool(
            getattr(window, "_advanced_filters_active", False)
        ),
        "current_filter_profile": getattr(window, "current_filter_profile", None),
        "profile_base_filters": copy_filter_mapping(
            getattr(window, "_profile_base_filters", None)
        ),
        "hidden_column_filter_lines": set(
            getattr(window, "_hidden_column_filter_lines", None) or set()
        ),
        "dedicated_or_text": str(getattr(window, "_dedicated_or_text", "")),
    }


def filter_state_signature(
    window: Any,
    *,
    search_text_override: str | None = None,
    pending_search_display_override: str | None = None,
    state: dict | None = None,
) -> tuple:
    state = state or snapshot_filter_state(
        window,
        search_text_override=search_text_override,
        pending_search_display_override=pending_search_display_override,
    )
    active_filters = state.get("active_column_filters") or {}
    or_groups = state.get("column_or_groups") or []
    hidden_lines = state.get("hidden_column_filter_lines") or set()
    return (
        str(state.get("search_text") or ""),
        tuple((str(k), str(v)) for k, v in active_filters.items()),
        tuple(
            (
                tuple(str(column) for column in (group.get("columns", ()) or ())),
                tuple(str(value) for value in (group.get("values", ()) or ())),
            )
            for group in or_groups
            if isinstance(group, dict)
        ),
        bool(state.get("exclude_ste_sca")),
        freeze_filter_state_value(state.get("advanced_filters") or {}),
        bool(state.get("advanced_filters_active")),
        str(state.get("current_filter_profile")),
        freeze_filter_state_value(state.get("profile_base_filters") or {}),
        tuple(sorted(str(value) for value in hidden_lines)),
        str(state.get("dedicated_or_text", "")),
        str(state.get("pending_search_display")),
    )


def store_last_filter_state(
    window: Any,
    *,
    search_text_override: str | None = None,
    pending_search_display_override: str | None = None,
) -> None:
    if getattr(window, "_restoring_filter_state", False):
        return
    try:
        state = snapshot_filter_state(
            window,
            search_text_override=search_text_override,
            pending_search_display_override=pending_search_display_override,
        )
        signature = filter_state_signature(window, state=state)
        if (
            getattr(window, "_last_filter_state_signature", None) == signature
            and getattr(window, "_last_filter_state", None) is not None
        ):
            window._update_undo_button_state()
            return
        window._last_filter_state = state
        window._last_filter_state_signature = signature
    except Exception as exc:
        logger.warning("Falha ao gerar snapshot de estado de filtros: %s", exc)
        window._last_filter_state = None
        window._last_filter_state_signature = None
    window._update_undo_button_state()


def restore_filter_search_state(window: Any, state: dict) -> str:
    restored_search_text = str(state.get("search_text", "") or "")
    window._set_search_text_across_tabs(restored_search_text)
    window._pending_search_display = state.get("pending_search_display")
    if not restored_search_text.strip():
        window._df_last_search_filtered = window.df_completo.copy(deep=True)
        window._df_last_search_filtered.attrs = dict(
            getattr(window.df_completo, "attrs", {})
        )
    return restored_search_text


def restore_filter_column_state(window: Any, state: dict) -> None:
    window._active_column_filters = OrderedDict(
        state.get("active_column_filters") or {}
    )
    window._reset_or_groups()
    for group in state.get("column_or_groups") or []:
        if not isinstance(group, dict):
            continue
        window._register_or_group(
            list(group.get("columns") or []), list(group.get("values") or [])
        )
    window._hidden_column_filter_lines = window._sanitize_hidden_column_filter_lines(
        state.get("hidden_column_filter_lines") or set(),
        window._active_column_filters,
    )
    window._dedicated_or_text = str(state.get("dedicated_or_text") or "")


def restore_filter_advanced_state(window: Any, state: dict) -> None:
    window._exclude_ste_sca = bool(state.get("exclude_ste_sca"))
    checkbox = getattr(window, "exclude_ste_checkbox", None)
    if checkbox is not None:
        try:
            window._set_checked_without_signal(
                checkbox,
                window._exclude_ste_sca,
                log_context="restore_exclude_ste_checkbox",
            )
        except Exception as exc:
            logger.debug("Falha ao restaurar checkbox exclude_ste principal: %s", exc)
    window._advanced_filters = state.get("advanced_filters") or {}
    window._advanced_filters_active = bool(state.get("advanced_filters_active"))
    try:
        window._sync_advanced_filter_ui()
        refresh_quick_situacao = getattr(
            window, "_refresh_quick_situacao_buttons", None
        )
        if callable(refresh_quick_situacao):
            refresh_quick_situacao()
    except Exception as exc:
        logger.warning(
            "Falha ao sincronizar UI de filtros avancados no restore: %s", exc
        )


def restore_filter_profile_state(window: Any, state: dict) -> None:
    window.current_filter_profile = state.get("current_filter_profile")
    window._profile_base_filters = state.get("profile_base_filters") or {}
    selector = getattr(window, "profile_selector", None)
    if selector is None:
        return
    idx = (
        selector.findData(window.current_filter_profile)
        if window.current_filter_profile
        else selector.findData(None)
    )
    if idx < 0:
        return
    window._profile_lock = True
    try:
        selector.setCurrentIndex(idx)
    finally:
        window._profile_lock = False


def render_restored_filter_state(window: Any, restored_search_text: str) -> None:
    if restored_search_text.strip():
        window.initiate_filtering()
    else:
        window._refresh_after_filter_change()
    try:
        window._update_filters_summary()
    except Exception as exc:
        logger.debug("Falha ao atualizar resumo de filtros no restore: %s", exc)
    window._sync_clear_filter_button_state()


def restore_last_filter_state(
    window: Any,
    state: dict | None = None,
    *,
    consume_undo: bool = True,
) -> None:
    if state is not None and not isinstance(state, dict):
        state = None
    if state is None:
        state = getattr(window, "_last_filter_state", None)
    if state is None:
        return
    window._invalidate_active_filter_request("restore_last_filter_state")
    window._set_filter_ui_idle()
    window._restoring_filter_state = True
    try:
        restored_search_text = window._restore_filter_search_state(state)
        window._restore_filter_column_state(state)
        window._restore_filter_advanced_state(state)
        window._restore_filter_profile_state(state)
        window._build_column_filters_panel()
        try:
            window.update_filter_tags()
        except Exception as exc:
            logger.debug("Falha ao atualizar tags de filtros no restore: %s", exc)
        window._render_restored_filter_state(restored_search_text)
        if consume_undo:
            window._last_filter_state = None
            window._last_filter_state_signature = None
    finally:
        window._restoring_filter_state = False
        window._update_undo_button_state()


def update_undo_button_state(window: Any) -> None:
    window._set_undo_filter_buttons_enabled(
        getattr(window, "_last_filter_state", None) is not None
    )
