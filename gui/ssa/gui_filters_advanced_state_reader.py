# gui/ssa/gui_filters_advanced_state_reader.py
# Relation: reads advanced-filter widget state without building UI.

from __future__ import annotations

from typing import Any, Callable

from utils.robust_logging import get_robust_logger

logger = get_robust_logger().get_logger(__name__, "gui")


def _combo_item_data(combo: Any):
    if combo is None:
        return None
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


def _widget_value(widget: Any):
    property_getter = getattr(widget, "property", None)
    if callable(property_getter):
        value = property_getter("value")
        if value is not None:
            return value
    text_getter = getattr(widget, "text", None)
    if callable(text_getter):
        return text_getter()
    return None


class AdvancedFilterStateReader:
    RESPONSAVEL_OUTPUT_KEYS = {
        "solicitante": "solicitante_exclude_values",
        "responsavel_programacao": "responsavel_programacao_exclude_values",
        "responsavel_execucao": "responsavel_execucao_exclude_values",
    }
    RESPONSAVEL_EXCLUDE_OUTPUT_KEYS = {
        "solicitante_exclude_values": "solicitante",
        "responsavel_programacao_exclude_values": "responsavel_programacao",
        "responsavel_execucao_exclude_values": "responsavel_execucao",
    }
    RESPONSAVEL_PREFIXES = {
        "solicitante": "adv_responsavel_solicitante",
        "responsavel_programacao": "adv_responsavel_programacao",
        "responsavel_execucao": "adv_responsavel_execucao",
    }
    RESPONSAVEL_WIDGET_BINDINGS = {
        "solicitante": (
            "adv_responsavel_solicitante",
            "adv_responsavel_solicitante_checks",
            "solicitante_exclude_values",
            "adv_responsavel_solicitante_exclude_checks",
        ),
        "responsavel_programacao": (
            "adv_responsavel_programacao",
            "adv_responsavel_programacao_checks",
            "responsavel_programacao_exclude_values",
            "adv_responsavel_programacao_exclude_checks",
        ),
        "responsavel_execucao": (
            "adv_responsavel_execucao",
            "adv_responsavel_execucao_checks",
            "responsavel_execucao_exclude_values",
            "adv_responsavel_execucao_exclude_checks",
        ),
    }

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
        self.widgets = widget_context if isinstance(widget_context, dict) else {}
        self.parse_week = parse_week

    def widget(self, name: str):
        return self.widgets.get(name)

    def checked_values(self, checks_attr: str) -> list[str]:
        values = []
        for item in self.widget(checks_attr) or []:
            is_checked = getattr(item, "isChecked", None)
            if callable(is_checked) and not is_checked():
                continue
            raw_value = _widget_value(item)
            if raw_value is None:
                continue
            text = str(raw_value).strip()
            if text:
                values.append(text)
        return values

    def week_range(self, start_attr: str, end_attr: str) -> tuple[int | None, int | None]:
        start_widget = self.widget(start_attr)
        end_widget = self.widget(end_attr)
        if start_widget is None and end_widget is None:
            return None, None
        start_text_getter = getattr(start_widget, "text", None)
        end_text_getter = getattr(end_widget, "text", None)
        start_text = start_text_getter() if callable(start_text_getter) else ""
        end_text = end_text_getter() if callable(end_text_getter) else ""
        return self.parse_week(start_text), self.parse_week(end_text)

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
        is_checked = getattr(widget, "isChecked", None)
        return bool(is_checked()) if callable(is_checked) else False

    def _collect_sector_status_filters(self) -> dict:
        return {
            "setor_executor": self.checked_values("adv_executor_checks"),
            "setor_executor_exclude_values": self.checked_values(
                "adv_executor_exclude_checks"
            ),
            "setor_emissor": self.checked_values("adv_emissor_checks"),
            "setor_emissor_exclude_values": self.checked_values(
                "adv_emissor_exclude_checks"
            ),
            "situacao": self.checked_values("adv_status_checks"),
            "situacao_exclude_values": self.checked_values("adv_status_exclude_checks"),
        }

    def _collect_year_priority_filters(self) -> dict:
        return {
            "ano_emissao_values": self.checked_values("adv_year_emissao_checks"),
            "ano_emissao_exclude_values": self.checked_values(
                "adv_year_emissao_exclude_checks"
            ),
            "ano_execucao_values": self.checked_values("adv_year_execucao_checks"),
            "ano_execucao_exclude_values": self.checked_values(
                "adv_year_execucao_exclude_checks"
            ),
            "semana_emissao_exclude": self.checked_flag("adv_week_emissao_exclude"),
            "semana_execucao_exclude": self.checked_flag("adv_week_execucao_exclude"),
            "num_reprogramacoes_values": self.checked_values("adv_reprog_checks"),
            "num_reprogramacoes_mode": _combo_item_data(
                self.widget("adv_reprog_mode")
            ),
            "prioridade_emissao_values": self.checked_values(
                "adv_prioridade_emissao_checks"
            ),
            "prioridade_emissao_exclude_values": self.checked_values(
                "adv_prioridade_emissao_exclude_checks"
            ),
            "prioridade_planejamento_values": self.checked_values(
                "adv_prioridade_planejamento_checks"
            ),
            "prioridade_planejamento_exclude_values": self.checked_values(
                "adv_prioridade_planejamento_exclude_checks"
            ),
        }

    def _collect_misc_filters(self) -> dict:
        return {
            "macro_filter": self.macro_filter(),
        }

    def _collect_responsavel_filters(self) -> dict:
        data = {}
        for include_key, binding in self.RESPONSAVEL_WIDGET_BINDINGS.items():
            prefix, include_checks_attr, exclude_key, exclude_checks_attr = binding
            data[include_key] = self.responsavel_values(
                include_checks_attr,
                include_key,
                prefix,
            )
            data[exclude_key] = self.responsavel_values(
                exclude_checks_attr,
                exclude_key,
                prefix,
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
