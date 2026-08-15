"""Synchronize advanced filter state back into widgets."""

from __future__ import annotations

from utils.robust_logging import get_robust_logger

from .gui_filters_advanced_specs import (
    AdvancedFilterWidgetContext,
    ADVANCED_RESPONSAVEL_MULTISELECT_SPECS,
    ADVANCED_STANDARD_MULTISELECT_SPECS,
    ADVANCED_WEEK_TEXT_SPECS,
    ADVANCED_YEAR_MULTISELECT_SPECS,
)
from .gui_filters_responsavel_state import responsavel_materialization_state

logger = get_robust_logger().get_logger(__name__, "gui")


def sync_advanced_filter_ui(window) -> None:
    data = getattr(window, "_advanced_filters", None) or {}
    context = _advanced_widget_context(window)
    _sync_standard_multiselects(window, context, data)
    _sync_responsavel_multiselects(window, context, data)
    _sync_reprogramacoes(window, context, data)
    _sync_year_multiselects(window, context, data)
    _sync_week_fields(context, data)
    _sync_derivada_flags(window, context, data)
    _sync_macro_combo(context, data)


def _advanced_widget_context(window) -> AdvancedFilterWidgetContext:
    context = getattr(window, "_filter_panel_context", None)
    if not isinstance(context, dict):
        context = getattr(window, "_adv_ctx", None)
    return AdvancedFilterWidgetContext(context if isinstance(context, dict) else {})


def _sync_standard_multiselects(window, context: AdvancedFilterWidgetContext, data: dict) -> None:
    for spec in ADVANCED_STANDARD_MULTISELECT_SPECS:
        _sync_multiselect(
            window,
            context,
            spec.prefix,
            data.get(spec.include_key),
            data.get(spec.exclude_key),
        )


def _sync_responsavel_multiselects(window, context: AdvancedFilterWidgetContext, data: dict) -> None:
    built_prefixes = responsavel_materialization_state(window).built_prefixes
    unbuilt_prefixes = set()
    for spec in ADVANCED_RESPONSAVEL_MULTISELECT_SPECS:
        if spec.prefix in built_prefixes:
            _sync_multiselect(
                window,
                context,
                spec.prefix,
                data.get(spec.include_key),
                data.get(spec.exclude_key),
            )
        else:
            unbuilt_prefixes.add(spec.prefix)
    if unbuilt_prefixes:
        window._sync_responsavel_button_summaries(only_prefixes=unbuilt_prefixes)


def _sync_multiselect(
    window,
    context: AdvancedFilterWidgetContext,
    prefix: str,
    include_values,
    exclude_values=None,
) -> None:
    button, checks, exclude_checks = context.multiselect_widgets(prefix)
    window._sync_multiselect_checks(
        button,
        checks,
        include_values,
        exclude_checks,
        exclude_values,
    )


def _sync_reprogramacoes(window, context: AdvancedFilterWidgetContext, data: dict) -> None:
    _sync_multiselect(
        window,
        context,
        "adv_reprog",
        data.get("num_reprogramacoes_values"),
    )
    try:
        reprog_mode = context.widget("adv_reprog_mode")
        if reprog_mode is None:
            return
        mode_value = data.get("num_reprogramacoes_mode") or "eq"
        idx = reprog_mode.findData(mode_value)
        if idx < 0:
            idx = reprog_mode.findData("eq")
        if idx >= 0:
            reprog_mode.setCurrentIndex(idx)
    except Exception as exc:
        logger.warning(
            "Falha ao sincronizar modo de reprogramacoes nos filtros avancados: %s",
            exc,
        )


def _sync_year_multiselects(window, context: AdvancedFilterWidgetContext, data: dict) -> None:
    for spec in ADVANCED_YEAR_MULTISELECT_SPECS:
        try:
            values, excluded = _resolve_year_values(data, spec.base_key)
            _sync_multiselect(window, context, spec.prefix, values, excluded)
        except Exception as exc:
            logger.warning(
                "Falha ao sincronizar filtro avancado de ano %s: %s",
                spec.base_key,
                exc,
            )


def _resolve_year_values(data: dict, base_key: str) -> tuple[object, object]:
    values_key = f"{base_key}_values"
    exclude_key = f"{base_key}_exclude"
    exclude_values_key = f"{base_key}_exclude_values"
    values = data.get(values_key)
    excluded = data.get(exclude_values_key)
    legacy_value = data.get(base_key)
    if values is None and not data.get(exclude_key) and legacy_value is not None:
        values = [legacy_value]
    if excluded is None and data.get(exclude_key) and legacy_value is not None:
        excluded = [legacy_value]
    return values, excluded


def _sync_week_fields(context: AdvancedFilterWidgetContext, data: dict) -> None:
    try:
        for attr, key in ADVANCED_WEEK_TEXT_SPECS:
            widget = context.widget(attr)
            if widget is None:
                continue
            value = data.get(key)
            widget.setText("" if value is None else str(value))
    except Exception as exc:
        logger.warning(
            "Falha ao sincronizar intervalo de semanas dos filtros avancados: %s",
            exc,
        )


def _sync_derivada_flags(window, context: AdvancedFilterWidgetContext, data: dict) -> None:
    try:
        selected = []
        if bool(data.get("derivada_has")):
            selected.append("has")
        if bool(data.get("derivada_all_ste")):
            selected.append("all_ste")
        if bool(data.get("derivada_is")):
            selected.append("is")
        _sync_multiselect(window, context, "adv_derivada", selected)
    except Exception as exc:
        logger.warning(
            "Falha ao sincronizar toggles de derivadas nos filtros avancados: %s",
            exc,
        )


def _sync_macro_combo(context: AdvancedFilterWidgetContext, data: dict) -> None:
    macro_combo = context.widget("adv_macro_combo")
    if macro_combo is None:
        return
    try:
        macro_combo.blockSignals(True)
        idx = macro_combo.findData(data.get("macro_filter"))
        macro_combo.setCurrentIndex(max(0, idx))
    except Exception as exc:
        logger.warning(
            "Falha ao sincronizar seletor macro dos filtros avancados: %s",
            exc,
        )
    finally:
        try:
            macro_combo.blockSignals(False)
        except Exception as exc:
            logger.debug("Falha ao reativar sinais do seletor macro apos sync: %s", exc)
