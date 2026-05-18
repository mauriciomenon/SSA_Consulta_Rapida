# gui/ssa/gui_filters_advanced_state_reader.py
# Relation: reads advanced-filter widget state without building UI.

from __future__ import annotations

from typing import Any, Callable

from utils.robust_logging import get_robust_logger

from .gui_filters_advanced_specs import (
    AdvancedFilterWidgetContext,
    ADVANCED_RESPONSAVEL_MULTISELECT_SPECS,
    ADVANCED_STANDARD_MULTISELECT_SPECS,
    ADVANCED_YEAR_MULTISELECT_SPECS,
)
from .gui_filters_multiselect_menu import _checked_values_from_checkboxes

logger = get_robust_logger().get_logger(__name__, "gui")


def _combo_item_data(combo: Any):
    if combo is None:
        return None
    try:
        current_data = getattr(combo, "currentData", None)
        if callable(current_data):
            return current_data()
        current_index = getattr(combo, "currentIndex", None)
        item_data = getattr(combo, "itemData", None)
        if not callable(current_index) or not callable(item_data):
            return None
        mode_idx = current_index()
        if mode_idx < 0:
            return None
        return item_data(mode_idx)
    except RuntimeError as exc:
        if _is_deleted_qt_wrapper_error(exc):
            return None
        raise


def _is_deleted_qt_wrapper_error(exc: RuntimeError) -> bool:
    text = str(exc)
    return "wrapped C/C++ object" in text and "has been deleted" in text


def _call_widget_bool(widget: Any, method_name: str, default: bool = False) -> bool:
    method = getattr(widget, method_name, None)
    if not callable(method):
        return default
    try:
        return bool(method())
    except RuntimeError as exc:
        if _is_deleted_qt_wrapper_error(exc):
            return default
        raise


def _widget_text(widget: Any) -> str:
    if widget is None:
        return ""
    text_getter = getattr(widget, "text", None)
    if not callable(text_getter):
        return ""
    try:
        return str(text_getter() or "")
    except RuntimeError as exc:
        if _is_deleted_qt_wrapper_error(exc):
            return ""
        raise


def resolve_year_selection_sets(
    filters,
    *,
    values_key: str,
    exclude_values_key: str,
    legacy_value_key: str,
    legacy_exclude_key: str,
) -> tuple[set[str], set[str]]:
    include_values = filters.get(values_key)
    exclude_values = filters.get(exclude_values_key)
    legacy_value = filters.get(legacy_value_key)
    legacy_exclude = bool(filters.get(legacy_exclude_key))
    if not include_values and not exclude_values and legacy_value is not None:
        if legacy_exclude:
            exclude_values = [legacy_value]
        else:
            include_values = [legacy_value]
    return {str(v) for v in (include_values or [])}, {
        str(v) for v in (exclude_values or [])
    }


class AdvancedFilterStateReader:
    def __init__(
        self,
        *,
        widget_context: dict[str, Any],
        current_filters: dict,
        responsavel_state,
        parse_week: Callable[[str], int | None],
    ) -> None:
        self.current_filters = current_filters or {}
        self.responsavel_state = responsavel_state
        self.context = AdvancedFilterWidgetContext(widget_context)
        self.parse_week = parse_week
        self._checked_values_cache: dict[str, list[str]] = {}

    def widget(self, name: str):
        return self.context.widget(name)

    def checked_values(self, checks_attr: str) -> list[str]:
        cached = self._checked_values_cache.get(checks_attr)
        if cached is not None:
            return list(cached)
        values = _checked_values_from_checkboxes(self.widget(checks_attr) or [])
        self._checked_values_cache[checks_attr] = list(values)
        return values

    def week_range(self, start_attr: str, end_attr: str) -> tuple[int | None, int | None]:
        start_widget = self.widget(start_attr)
        end_widget = self.widget(end_attr)
        if start_widget is None and end_widget is None:
            return None, None
        return self.parse_week(_widget_text(start_widget)), self.parse_week(
            _widget_text(end_widget)
        )

    def responsavel_values(
        self,
        checks_attr: str,
        key_name: str,
        prefix: str,
    ) -> list[str]:
        if not self.responsavel_state.is_materialized(prefix):
            return list(self.current_filters.get(key_name) or [])
        return self.checked_values(checks_attr)

    def derivada_flags(self) -> dict[str, bool]:
        selected = {str(v).casefold() for v in self.checked_values("adv_derivada_checks")}
        return {
            "derivada_has": "has" in selected,
            "derivada_all_ste": "all_ste" in selected,
            "derivada_is": "is" in selected,
        }

    def macro_filter(self):
        return _combo_item_data(self.widget("adv_macro_combo"))

    def checked_flag(self, widget_attr: str) -> bool:
        widget = self.widget(widget_attr)
        if widget is None:
            return False
        return _call_widget_bool(widget, "isChecked")

    def _collect_sector_status_filters(self) -> dict:
        bindings = []
        for spec in ADVANCED_STANDARD_MULTISELECT_SPECS[:3]:
            bindings.append((spec.include_key, f"{spec.prefix}_checks"))
            if spec.exclude_key is not None:
                bindings.append((spec.exclude_key, f"{spec.prefix}_exclude_checks"))
        return {key: self.checked_values(attr) for key, attr in bindings}

    def _collect_year_priority_filters(self) -> dict:
        multiselect_bindings = [
            ("num_reprogramacoes_values", "adv_reprog_checks"),
        ]
        for spec in ADVANCED_YEAR_MULTISELECT_SPECS:
            multiselect_bindings.append(
                (f"{spec.base_key}_values", f"{spec.prefix}_checks")
            )
            multiselect_bindings.append(
                (f"{spec.base_key}_exclude_values", f"{spec.prefix}_exclude_checks")
            )
        for spec in ADVANCED_STANDARD_MULTISELECT_SPECS[3:]:
            multiselect_bindings.append((spec.include_key, f"{spec.prefix}_checks"))
            if spec.exclude_key is not None:
                multiselect_bindings.append(
                    (spec.exclude_key, f"{spec.prefix}_exclude_checks")
                )
        data: dict[str, object] = {
            key: self.checked_values(attr) for key, attr in multiselect_bindings
        }
        data.update(
            {
                "num_reprogramacoes_mode": _combo_item_data(
                    self.widget("adv_reprog_mode")
                ),
            }
        )
        return data

    def _collect_misc_filters(self) -> dict:
        return {
            "macro_filter": self.macro_filter(),
        }

    def _collect_responsavel_filters(self) -> dict:
        data = {}
        for spec in ADVANCED_RESPONSAVEL_MULTISELECT_SPECS:
            data[spec.include_key] = self.responsavel_values(
                f"{spec.prefix}_checks",
                spec.include_key,
                spec.prefix,
            )
            if spec.exclude_key is None:
                continue
            data[spec.exclude_key] = self.responsavel_values(
                f"{spec.prefix}_exclude_checks",
                spec.exclude_key,
                spec.prefix,
            )
        return data

    def collect(self) -> dict:
        data = self._collect_sector_status_filters()
        data.update(self._collect_year_priority_filters())
        data.update(self._collect_responsavel_filters())
        data.update(self._collect_misc_filters())
        semana_emissao_inicio, semana_emissao_fim = self.week_range(
            "adv_week_emissao_start",
            "adv_week_emissao_end",
        )
        data["semana_emissao_inicio"] = semana_emissao_inicio
        data["semana_emissao_fim"] = semana_emissao_fim
        semana_execucao_inicio, semana_execucao_fim = self.week_range(
            "adv_week_execucao_start",
            "adv_week_execucao_end",
        )
        data["semana_execucao_inicio"] = semana_execucao_inicio
        data["semana_execucao_fim"] = semana_execucao_fim
        data.update(self.derivada_flags())
        return data
