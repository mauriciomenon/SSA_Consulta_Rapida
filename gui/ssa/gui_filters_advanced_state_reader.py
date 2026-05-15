# gui/ssa/gui_filters_advanced_state_reader.py
# Relation: reads advanced-filter widget state without building UI.

from __future__ import annotations

from typing import Any

from utils.robust_logging import get_robust_logger

logger = get_robust_logger().get_logger(__name__, "gui")


def _combo_item_data(combo: Any):
    try:
        if combo is None:
            return None
        mode_idx = combo.currentIndex()
        return combo.itemData(mode_idx)
    except Exception:
        return None


class AdvancedFilterStateReader:
    def __init__(self, window) -> None:
        self.window = window
        self.current_filters = getattr(window, "_advanced_filters", None) or {}
        self.built_prefixes = set(
            getattr(window, "_responsavel_materialized_prefixes", set())
        )

    def checked_values(self, checks_attr: str) -> list[str]:
        try:
            return self.window._get_checked_values(
                getattr(self.window, checks_attr, None)
            )
        except Exception as exc:
            logger.debug("Failed to collect advanced values (%s): %s", checks_attr, exc)
            return []

    def week_range(self, start_attr: str, end_attr: str) -> tuple[int | None, int | None]:
        try:
            start_widget = getattr(self.window, start_attr, None)
            end_widget = getattr(self.window, end_attr, None)
            start_text = start_widget.text() if start_widget is not None else ""
            end_text = end_widget.text() if end_widget is not None else ""
            return self.window._parse_week(start_text), self.window._parse_week(
                end_text
            )
        except Exception as exc:
            logger.debug(
                "Failed to collect advanced week range (%s/%s): %s",
                start_attr,
                end_attr,
                exc,
            )
            return None, None

    def responsavel_values(
        self,
        checks_attr: str,
        key_name: str,
        prefix: str,
    ) -> list[str]:
        if prefix not in self.built_prefixes:
            return list(self.current_filters.get(key_name) or [])
        try:
            return self.window._get_checked_values(
                getattr(self.window, checks_attr, None)
            )
        except Exception as exc:
            logger.debug(
                "Failed to collect advanced responsible values (%s/%s): %s",
                key_name,
                checks_attr,
                exc,
            )
            return []

    def derivada_flags(self) -> dict[str, bool]:
        selected = {str(v).casefold() for v in self.checked_values("adv_derivada_checks")}
        return {
            "derivada_has": "has" in selected,
            "derivada_all_ste": "all_ste" in selected,
            "derivada_is": "is" in selected,
        }

    def macro_filter(self):
        try:
            return self.window.adv_macro_combo.currentData()
        except Exception as exc:
            logger.debug("Failed to collect advanced macro_filter: %s", exc)
            return None

    def collect(self) -> dict:
        data = {
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
            "ano_emissao_values": self.checked_values("adv_year_emissao_checks"),
            "ano_emissao_exclude_values": self.checked_values(
                "adv_year_emissao_exclude_checks"
            ),
            "ano_execucao_values": self.checked_values("adv_year_execucao_checks"),
            "ano_execucao_exclude_values": self.checked_values(
                "adv_year_execucao_exclude_checks"
            ),
            "semana_emissao_exclude": False,
            "semana_execucao_exclude": False,
            "solicitante": self.responsavel_values(
                "adv_responsavel_solicitante_checks",
                "solicitante",
                "adv_responsavel_solicitante",
            ),
            "solicitante_exclude_values": self.responsavel_values(
                "adv_responsavel_solicitante_exclude_checks",
                "solicitante_exclude_values",
                "adv_responsavel_solicitante",
            ),
            "responsavel_programacao": self.responsavel_values(
                "adv_responsavel_programacao_checks",
                "responsavel_programacao",
                "adv_responsavel_programacao",
            ),
            "responsavel_programacao_exclude_values": self.responsavel_values(
                "adv_responsavel_programacao_exclude_checks",
                "responsavel_programacao_exclude_values",
                "adv_responsavel_programacao",
            ),
            "responsavel_execucao": self.responsavel_values(
                "adv_responsavel_execucao_checks",
                "responsavel_execucao",
                "adv_responsavel_execucao",
            ),
            "responsavel_execucao_exclude_values": self.responsavel_values(
                "adv_responsavel_execucao_exclude_checks",
                "responsavel_execucao_exclude_values",
                "adv_responsavel_execucao",
            ),
            "num_reprogramacoes_values": self.checked_values("adv_reprog_checks"),
            "num_reprogramacoes_mode": _combo_item_data(
                getattr(self.window, "adv_reprog_mode", None)
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
            "macro_filter": self.macro_filter(),
        }
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
