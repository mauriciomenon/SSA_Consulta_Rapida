"""Shared advanced filter widget/data specifications."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class AdvancedMultiselectSpec:
    prefix: str
    field_key: str
    include_key: str
    exclude_key: str | None = None


@dataclass(frozen=True)
class AdvancedYearSpec:
    prefix: str
    field_key: str
    base_key: str


class AdvancedFilterWidgetContext:
    def __init__(self, widgets: dict):
        self.widgets = widgets if isinstance(widgets, dict) else {}

    def widget(self, name: str):
        return self.widgets.get(name)

    def multiselect_widgets(self, prefix: str):
        return (
            self.widget(f"{prefix}_button"),
            self.widget(f"{prefix}_checks"),
            self.widget(f"{prefix}_exclude_checks"),
        )


ADVANCED_STANDARD_MULTISELECT_SPECS = (
    AdvancedMultiselectSpec(
        "adv_executor",
        "exec",
        "setor_executor",
        "setor_executor_exclude_values",
    ),
    AdvancedMultiselectSpec(
        "adv_emissor",
        "emis",
        "setor_emissor",
        "setor_emissor_exclude_values",
    ),
    AdvancedMultiselectSpec(
        "adv_status",
        "status",
        "situacao",
        "situacao_exclude_values",
    ),
    AdvancedMultiselectSpec(
        "adv_prioridade_emissao",
        "prio_emis",
        "prioridade_emissao_values",
        "prioridade_emissao_exclude_values",
    ),
    AdvancedMultiselectSpec(
        "adv_prioridade_planejamento",
        "prio_plan",
        "prioridade_planejamento_values",
        "prioridade_planejamento_exclude_values",
    ),
)

ADVANCED_RESPONSAVEL_MULTISELECT_SPECS = (
    AdvancedMultiselectSpec(
        "adv_responsavel_solicitante",
        "sol",
        "solicitante",
        "solicitante_exclude_values",
    ),
    AdvancedMultiselectSpec(
        "adv_responsavel_programacao",
        "prog",
        "responsavel_programacao",
        "responsavel_programacao_exclude_values",
    ),
    AdvancedMultiselectSpec(
        "adv_responsavel_execucao",
        "exec_resp",
        "responsavel_execucao",
        "responsavel_execucao_exclude_values",
    ),
)

ADVANCED_YEAR_MULTISELECT_SPECS = (
    AdvancedYearSpec("adv_year_emissao", "year_emissao", "ano_emissao"),
    AdvancedYearSpec("adv_year_execucao", "year_execucao", "ano_execucao"),
)

ADVANCED_WEEK_TEXT_SPECS = (
    ("adv_week_emissao_start", "semana_emissao_inicio"),
    ("adv_week_emissao_end", "semana_emissao_fim"),
    ("adv_week_execucao_start", "semana_execucao_inicio"),
    ("adv_week_execucao_end", "semana_execucao_fim"),
)
