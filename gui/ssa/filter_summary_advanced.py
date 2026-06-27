"""Advanced filter summary entry builders."""

from __future__ import annotations

from collections import OrderedDict
from typing import Any

from gui.ssa.filter_summary_entries import (
    SummaryEntry,
    excluded_summary_week_range,
    merge_summary_actions,
    shorten_summary_label,
    summary_week_range,
)

AdvancedValueSpec = tuple[str, str, str | None, list[str]]

ADVANCED_VALUE_LABELS = {
    "executor": "Executor",
    "emissor": "Emissor",
    "divisao": "Divisao",
    "situacao": "Situacao",
    "prio_emissao": "Prio Emissao",
    "prio_planejamento": "Prio Planejamento",
    "reprogramacoes": "Reprogramacoes",
    "solicitante": "Solicitante",
    "resp_programacao": "Resp Programacao",
    "resp_execucao": "Resp Execucao",
}

ADVANCED_VALUE_SPECS: tuple[AdvancedValueSpec, ...] = (
    ("executor", "setor_executor", None, ["setor_executor"]),
    ("executor", "setor_executor_exclude_values", "!=", ["setor_executor_exclude_values"]),
    ("emissor", "setor_emissor", None, ["setor_emissor"]),
    ("emissor", "setor_emissor_exclude_values", "!=", ["setor_emissor_exclude_values"]),
    ("divisao", "divisao", None, ["divisao"]),
    ("divisao", "divisao_exclude_values", "!=", ["divisao_exclude_values"]),
    ("situacao", "situacao", None, ["situacao"]),
    ("situacao", "situacao_exclude_values", "!=", ["situacao_exclude_values"]),
    ("prio_emissao", "prioridade_emissao_values", None, ["prioridade_emissao_values"]),
    (
        "prio_emissao",
        "prioridade_emissao_exclude_values",
        "!=",
        ["prioridade_emissao_exclude_values"],
    ),
    (
        "prio_planejamento",
        "prioridade_planejamento_values",
        None,
        ["prioridade_planejamento_values"],
    ),
    (
        "reprogramacoes",
        "num_reprogramacoes_values",
        None,
        ["num_reprogramacoes_values"],
    ),
    (
        "prio_planejamento",
        "prioridade_planejamento_exclude_values",
        "!=",
        ["prioridade_planejamento_exclude_values"],
    ),
    ("solicitante", "solicitante", None, ["solicitante"]),
    ("solicitante", "solicitante_exclude_values", "!=", ["solicitante_exclude_values"]),
    ("resp_programacao", "responsavel_programacao", None, ["responsavel_programacao"]),
    (
        "resp_programacao",
        "responsavel_programacao_exclude_values",
        "!=",
        ["responsavel_programacao_exclude_values"],
    ),
    ("resp_execucao", "responsavel_execucao", None, ["responsavel_execucao"]),
    (
        "resp_execucao",
        "responsavel_execucao_exclude_values",
        "!=",
        ["responsavel_execucao_exclude_values"],
    ),
)


def build_advanced_summary_entries(advanced_filters: dict) -> OrderedDict[str, SummaryEntry]:
    summary_builder = AdvancedSummaryBuilder()
    for builder in ADVANCED_ENTRY_BUILDERS:
        builder(advanced_filters, summary_builder.add_adv, summary_builder.add_entry)
    return summary_builder.entries


class AdvancedSummaryBuilder:
    def __init__(self) -> None:
        self.entries: OrderedDict[str, SummaryEntry] = OrderedDict()

    def add_entry(self, text: str, keys: list[str]) -> None:
        merge_summary_actions(
            self.entries,
            text=text,
            actions=[{"kind": "advanced_keys", "keys": keys}],
        )

    def add_adv(
        self,
        label: str,
        values: Any,
        op: str | None = None,
        *,
        action_keys: list[str] | None = None,
    ) -> None:
        if not values:
            return
        if isinstance(values, list):
            txt = ", ".join(str(value) for value in values if str(value).strip())
        else:
            txt = str(values).strip()
        if not txt:
            return
        text = f"{label}: {txt}"
        if op:
            text = f"{label} {op} {txt}"
        keys = [str(key) for key in (action_keys or []) if str(key).strip()]
        merge_summary_actions(
            self.entries,
            text=shorten_summary_label(text),
            actions=[{"kind": "advanced_keys", "keys": keys}],
        )


def _add_basic_advanced_entries(adv: dict, add_adv, _add_entry) -> None:
    for label_key, key, op, action_keys in ADVANCED_VALUE_SPECS:
        label = ADVANCED_VALUE_LABELS[label_key]
        add_adv(label, adv.get(key), op, action_keys=action_keys)


def _add_year_advanced_entries(adv: dict, add_adv, _add_entry) -> None:
    for label, base_key in (
        ("Ano Emissao", "ano_emissao"),
        ("Ano Execucao", "ano_execucao"),
    ):
        values_key, exclude_key, exclude_values_key, values, excluded = (
            _resolve_year_filter_values(adv, base_key)
        )
        add_adv(label, values, action_keys=[base_key, values_key])
        add_adv(label, excluded, "exclui", action_keys=[exclude_key, exclude_values_key])


def _add_week_advanced_entries(adv: dict, add_adv, _add_entry) -> None:
    for label, start_key, end_key, exclude_key in (
        (
            "Semana Emissao",
            "semana_emissao_inicio",
            "semana_emissao_fim",
            "semana_emissao_exclude",
        ),
        (
            "Semana Execucao",
            "semana_execucao_inicio",
            "semana_execucao_fim",
            "semana_execucao_exclude",
        ),
    ):
        _add_temporal_range_entry(adv, add_adv, label, start_key, end_key, exclude_key)


def _resolve_year_filter_values(adv: dict, base_key: str) -> tuple[str, str, str, Any, Any]:
    values_key = f"{base_key}_values"
    exclude_key = f"{base_key}_exclude"
    exclude_values_key = f"{base_key}_exclude_values"
    values_provided = values_key in adv
    excluded_provided = exclude_values_key in adv
    values = adv.get(values_key)
    excluded = adv.get(exclude_values_key)
    exclude_legacy = bool(adv.get(exclude_key))
    legacy_value = adv.get(base_key)
    if values_provided or excluded_provided:
        return values_key, exclude_key, exclude_values_key, values, excluded
    if not values_provided and not exclude_legacy and legacy_value is not None:
        values = [legacy_value]
    if not excluded_provided and exclude_legacy and legacy_value is not None:
        excluded = [legacy_value]
    return values_key, exclude_key, exclude_values_key, values, excluded


def _add_temporal_range_entry(
    adv: dict,
    add_adv,
    label: str,
    start_key: str,
    end_key: str,
    exclude_key: str,
) -> None:
    is_excluded = bool(adv.get(exclude_key))
    if is_excluded:
        week_range = excluded_summary_week_range(adv.get(start_key), adv.get(end_key))
    else:
        week_range = summary_week_range(adv.get(start_key), adv.get(end_key))
    if not week_range:
        return
    action_keys = [start_key, end_key]
    if is_excluded:
        action_keys.append(exclude_key)
    add_adv(
        label,
        week_range,
        action_keys=action_keys,
    )


def _add_derivada_advanced_entries(adv: dict, _add_adv, add_entry) -> None:
    if adv.get("derivada_has"):
        add_entry("Possui derivada", ["derivada_has"])
    if adv.get("derivada_terminal_statuses") or adv.get("derivada_all_ste"):
        add_entry(
            "Derivadas em status terminal",
            ["derivada_terminal_statuses", "derivada_all_ste"],
        )
    if adv.get("derivada_is"):
        add_entry("SSA derivada", ["derivada_is"])


def _add_macro_advanced_entries(adv: dict, _add_adv, add_entry) -> None:
    if not adv.get("macro_filter"):
        return
    macro_value = adv.get("macro_filter")
    macro_label = "SSAs para baixar" if macro_value == "ssas_para_baixar" else str(macro_value)
    add_entry(f"Macro: {macro_label}", ["macro_filter"])


ADVANCED_ENTRY_BUILDERS = (
    _add_basic_advanced_entries,
    _add_year_advanced_entries,
    _add_week_advanced_entries,
    _add_derivada_advanced_entries,
    _add_macro_advanced_entries,
)
