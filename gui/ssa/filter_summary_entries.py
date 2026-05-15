"""Summary entry builders for active SSA filters."""

from __future__ import annotations

from collections import OrderedDict
from typing import Any

SummaryAction = dict[str, Any]
SummaryEntry = dict[str, Any]

SUMMARY_LABEL_SHORTENINGS = (
    ("Executor", "Exec"),
    ("Emissor", "Emis"),
    ("Situacao", "Sit"),
    ("Prio Emissao", "Prio"),
    ("Prio Planejamento", "Plan"),
    ("Ano Emissao", "Ano Emis"),
    ("Ano Execucao", "Ano Exec"),
    ("Reprogramacoes", "No. Reprog"),
    ("Derivada de", "Deriv"),
    ("Solicitante", "Solic"),
    ("Resp Programacao", "Resp Prog"),
    ("Resp Execucao", "Resp Exec"),
    ("Semana Emissao", "Sem Emis"),
    ("Semana Execucao", "Sem Exec"),
)

ADVANCED_SECTOR_SPECS = (
    ("Executor", "setor_executor", None, ["setor_executor"]),
    ("Executor", "setor_executor_exclude_values", "!=", ["setor_executor_exclude_values"]),
    ("Emissor", "setor_emissor", None, ["setor_emissor"]),
    ("Emissor", "setor_emissor_exclude_values", "!=", ["setor_emissor_exclude_values"]),
    ("Divisao", "divisao", None, ["divisao"]),
    ("Divisao", "divisao_exclude_values", "!=", ["divisao_exclude_values"]),
)
ADVANCED_STATUS_SPECS = (
    ("Situacao", "situacao", None, ["situacao"]),
    ("Situacao", "situacao_exclude_values", "!=", ["situacao_exclude_values"]),
    ("Prio Emissao", "prioridade_emissao_values", None, ["prioridade_emissao_values"]),
    (
        "Prio Emissao",
        "prioridade_emissao_exclude_values",
        "!=",
        ["prioridade_emissao_exclude_values"],
    ),
    (
        "Prio Planejamento",
        "prioridade_planejamento_values",
        None,
        ["prioridade_planejamento_values"],
    ),
    (
        "Prio Planejamento",
        "prioridade_planejamento_exclude_values",
        "!=",
        ["prioridade_planejamento_exclude_values"],
    ),
)
ADVANCED_RESPONSIBLE_SPECS = (
    ("Solicitante", "solicitante", None, ["solicitante"]),
    ("Solicitante", "solicitante_exclude_values", "!=", ["solicitante_exclude_values"]),
    ("Resp Programacao", "responsavel_programacao", None, ["responsavel_programacao"]),
    (
        "Resp Programacao",
        "responsavel_programacao_exclude_values",
        "!=",
        ["responsavel_programacao_exclude_values"],
    ),
    ("Resp Execucao", "responsavel_execucao", None, ["responsavel_execucao"]),
    (
        "Resp Execucao",
        "responsavel_execucao_exclude_values",
        "!=",
        ["responsavel_execucao_exclude_values"],
    ),
)


def summary_week_range(start: Any, end: Any) -> str | None:
    if start is None and end is None:
        return None
    if start is None:
        return f"<= {end}"
    if end is None:
        return f">= {start}"
    return f"{start}-{end}"


def shorten_summary_label(text: str) -> str:
    display_text = str(text or "")
    for full_label, short_label in SUMMARY_LABEL_SHORTENINGS:
        prefix = f"{full_label}:"
        if display_text.startswith(prefix):
            return f"{short_label}:{display_text[len(prefix):]}"
    return display_text


def merge_summary_actions(
    target: dict[str, SummaryEntry],
    *,
    text: str,
    actions: list[SummaryAction],
) -> None:
    normalized_text = str(text or "").strip()
    if not normalized_text:
        return
    entry = target.get(normalized_text)
    if entry is None:
        target[normalized_text] = {"text": normalized_text, "actions": list(actions)}
        return
    existing_actions = entry.setdefault("actions", [])
    seen_signatures = {
        _freeze_summary_action(action)
        for action in existing_actions
        if isinstance(action, dict)
    }
    for action in actions:
        if not isinstance(action, dict):
            continue
        signature = _freeze_summary_action(action)
        if signature in seen_signatures:
            continue
        existing_actions.append(action)
        seen_signatures.add(signature)


def build_advanced_summary_entries(advanced_filters: dict) -> OrderedDict[str, SummaryEntry]:
    entries: OrderedDict[str, SummaryEntry] = OrderedDict()

    def add_adv(
        label,
        values,
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
        if not keys:
            return
        merge_summary_actions(
            entries,
            text=text,
            actions=[{"kind": "advanced_keys", "keys": keys}],
        )

    for builder in ADVANCED_ENTRY_BUILDERS:
        builder(advanced_filters, entries, add_adv)
    return entries


def _add_basic_advanced_entries(adv: dict, _entries, add_adv) -> None:
    for specs in (
        ADVANCED_SECTOR_SPECS,
        ADVANCED_STATUS_SPECS,
        ADVANCED_RESPONSIBLE_SPECS,
    ):
        for label, key, op, action_keys in specs:
            add_adv(label, adv.get(key), op, action_keys=action_keys)


def _add_year_advanced_entries(adv: dict, _entries, add_adv) -> None:
    for label, base_key in (
        ("Ano Emissao", "ano_emissao"),
        ("Ano Execucao", "ano_execucao"),
    ):
        values_key, exclude_key, exclude_values_key, values, excluded = (
            _resolve_year_filter_values(adv, base_key)
        )
        add_adv(label, values, action_keys=[base_key, values_key])
        add_adv(label, excluded, "!=", action_keys=[exclude_key, exclude_values_key])


def _add_week_advanced_entries(adv: dict, _entries, add_adv) -> None:
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
    values = adv.get(values_key)
    excluded = adv.get(exclude_values_key)
    exclude_legacy = bool(adv.get(exclude_key))
    if values is None and not exclude_legacy and adv.get(base_key) is not None:
        values = [adv.get(base_key)]
    if excluded is None and exclude_legacy and adv.get(base_key) is not None:
        excluded = [adv.get(base_key)]
    return values_key, exclude_key, exclude_values_key, values, excluded


def _add_temporal_range_entry(
    adv: dict,
    add_adv,
    label: str,
    start_key: str,
    end_key: str,
    exclude_key: str,
) -> None:
    week_range = summary_week_range(adv.get(start_key), adv.get(end_key))
    if not week_range:
        return
    action_keys = [start_key, end_key]
    if adv.get(exclude_key):
        action_keys.append(exclude_key)
    add_adv(
        label,
        [week_range],
        "!=" if adv.get(exclude_key) else None,
        action_keys=action_keys,
    )


def _add_derivada_advanced_entries(adv: dict, entries, _add_adv) -> None:
    if adv.get("derivada_has"):
        merge_summary_actions(
            entries,
            text="Possui derivada",
            actions=[{"kind": "advanced_keys", "keys": ["derivada_has"]}],
        )
    if adv.get("derivada_terminal_statuses") or adv.get("derivada_all_ste"):
        merge_summary_actions(
            entries,
            text="Derivadas em status terminal",
            actions=[
                {
                    "kind": "advanced_keys",
                    "keys": ["derivada_terminal_statuses", "derivada_all_ste"],
                }
            ],
        )
    if adv.get("derivada_is"):
        merge_summary_actions(
            entries,
            text="SSA derivada",
            actions=[{"kind": "advanced_keys", "keys": ["derivada_is"]}],
        )


def _add_macro_advanced_entries(adv: dict, entries, _add_adv) -> None:
    if not adv.get("macro_filter"):
        return
    macro_value = adv.get("macro_filter")
    macro_label = "SSAs para baixar" if macro_value == "ssas_para_baixar" else str(macro_value)
    merge_summary_actions(
        entries,
        text=f"Macro: {macro_label}",
        actions=[{"kind": "advanced_keys", "keys": ["macro_filter"]}],
    )


ADVANCED_ENTRY_BUILDERS = (
    _add_basic_advanced_entries,
    _add_year_advanced_entries,
    _add_week_advanced_entries,
    _add_derivada_advanced_entries,
    _add_macro_advanced_entries,
)


def _freeze_summary_action(value: Any) -> Any:
    if isinstance(value, dict):
        return tuple(
            (str(key), _freeze_summary_action(item))
            for key, item in sorted(value.items(), key=lambda entry: str(entry[0]))
        )
    if isinstance(value, (list, tuple)):
        return tuple(_freeze_summary_action(item) for item in value)
    if isinstance(value, set):
        return tuple(sorted(_freeze_summary_action(item) for item in value))
    try:
        hash(value)
    except TypeError:
        return f"<unhashable:{type(value).__name__}>"
    return value
