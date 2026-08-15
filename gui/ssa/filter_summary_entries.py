"""Summary entry builders for active SSA filters."""

from __future__ import annotations

from collections import OrderedDict
from dataclasses import dataclass
import re
from typing import Any, TypedDict

SummaryAction = dict[str, Any]
SummaryEntry = dict[str, Any]


class ColumnOrGroupSummary(TypedDict, total=False):
    columns: list[str]
    values: list[str]

FILTER_SUMMARY_COMPACT_NAMES = {
    "setor_executor": "Exec",
    "setor_emissor": "Emis",
    "descricao_ssa": "Desc",
    "descricao_execucao": "Desc Exec",
    "localizacao_codigo": "Loc",
    "semana_cadastro": "Sem Cad",
    "semana_programada": "Sem Prog",
    "semana_executada": "Sem Exec",
    "situacao": "Sit",
    "grau_prioridade_emissao": "Prio Emis",
    "grau_prioridade_planejamento": "Prio Plan",
}

COLUMN_FILTER_COMPACT_ALIASES = {
    "Descricao da SSA": "Desc. SSA",
    "Descricao Execucao": "Desc. Exec.",
    "Setor executor": "Set. Exec.",
    "Setor emissor": "Set. Emis.",
    "Semana cadastro": "Sem. Cad.",
    "Semana programada": "Sem. Prog.",
    "Semana executada": "Sem. Exec.",
}

SUMMARY_LABEL_SHORTENINGS = (
    ("Descricao da SSA", "Desc"),
    ("Descricao Execucao", "Desc Exec"),
    ("Setor Executor", "Exec"),
    ("Setor Emissor", "Emis"),
    ("Executor", "Exec"),
    ("Emissor", "Emis"),
    ("Situacao", "Sit"),
    ("Prio Emissao", "Prio Emis"),
    ("Prio Planejamento", "Prio Plan"),
    ("Semana Cadastro", "Sem Cad"),
    ("Semana Programada", "Sem Prog"),
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

_FILTER_VALUE_WHITESPACE_RE = re.compile(r"\s+")


@dataclass(frozen=True)
class FilterSummaryContext:
    search_text: str
    dedicated_or_text: str
    active_column_filters: dict[str, Any]
    column_or_groups: list[ColumnOrGroupSummary]
    column_to_or_group: dict[str, ColumnOrGroupSummary]
    advanced_filters: dict[str, Any]
    advanced_filters_active: bool
    exclude_terminal_statuses: bool
    theme_name: str

def summary_week_range(start: Any, end: Any) -> str | None:
    if start is None and end is None:
        return None
    if start is None:
        return f"<= {end}"
    if end is None:
        return f">= {start}"
    return f"{start}-{end}"


def excluded_summary_week_range(start: Any, end: Any) -> str | None:
    if start is None and end is None:
        return None
    if start is None:
        return f"exclui ate {end}"
    if end is None:
        return f"exclui desde {start}"
    return f"exclui {start}-{end}"


def shorten_summary_label(text: str) -> str:
    display_text = str(text or "")
    for full_label, short_label in SUMMARY_LABEL_SHORTENINGS:
        prefix = f"{full_label}:"
        if display_text.startswith(prefix):
            return f"{short_label}:{display_text[len(prefix):]}"
    return display_text


def filters_summary_display_name(col: str, resolve_column_display_name) -> str:
    column_name = str(col)
    if column_name in FILTER_SUMMARY_COMPACT_NAMES:
        return FILTER_SUMMARY_COMPACT_NAMES[column_name]
    return str(resolve_column_display_name(column_name))


def compact_column_filter_display_name(resolved_name: str) -> str:
    display_name = str(resolved_name)
    return COLUMN_FILTER_COMPACT_ALIASES.get(display_name, display_name)


def format_column_filter_display_value(
    raw: str,
    *,
    column: str | None = None,
    alias_map: dict | None = None,
) -> str:
    if not raw:
        return ""
    tokens = _split_column_filter_display_tokens(raw)
    if not tokens:
        return ""
    return ", ".join(_map_column_filter_display_tokens(tokens, column, alias_map))


def _split_column_filter_display_tokens(raw: str) -> list[str]:
    text = str(raw).replace(";", ",").strip()
    text = _FILTER_VALUE_WHITESPACE_RE.sub(" ", text).strip()
    return [token.strip() for token in text.split(",") if token.strip()]


def _map_column_filter_display_tokens(
    tokens: list[str],
    column: str | None,
    alias_map: dict | None,
) -> list[str]:
    if not tokens or not isinstance(alias_map, dict):
        return tokens
    col_map = None
    if column:
        col_map = alias_map.get(column) or alias_map.get(column.lower())
    global_map = alias_map.get("_global")
    return [
        _map_column_filter_display_token(token, col_map, global_map)
        for token in tokens
    ]


def _map_column_filter_display_token(
    token: str,
    col_map: Any,
    global_map: Any,
) -> str:
    key = token.casefold()
    new_token = None
    if isinstance(col_map, dict):
        new_token = col_map.get(key)
    if new_token is None and isinstance(global_map, dict):
        new_token = global_map.get(key)
    if isinstance(new_token, str) and new_token.strip():
        return new_token
    return token


def build_filters_summary_base_entries(
    *,
    context: FilterSummaryContext,
    display_name_for_column,
    format_value,
) -> tuple[OrderedDict[str, SummaryEntry], tuple, dict, bool]:
    summary_entries: OrderedDict[str, SummaryEntry] = OrderedDict()
    normalized_search_text = str(context.search_text or "").strip()
    if normalized_search_text:
        merge_summary_actions(
            summary_entries,
            text=f"Busca: '{normalized_search_text}'",
            actions=[{"kind": "search"}],
        )

    normalized_or_text = str(context.dedicated_or_text or "").strip()
    if normalized_or_text:
        merge_summary_actions(
            summary_entries,
            text=f"Filtro OU: {format_value(normalized_or_text)}",
            actions=[{"kind": "dedicated_or"}],
        )

    _add_column_filter_summary_entries(
        summary_entries,
        active_column_filters=context.active_column_filters,
        column_or_groups=context.column_or_groups,
        column_to_or_group=context.column_to_or_group,
        display_name_for_column=display_name_for_column,
        format_value=format_value,
    )

    raw_summary_signature = build_filters_summary_raw_signature(
        context=context,
    )
    return (
        summary_entries,
        raw_summary_signature,
        context.advanced_filters,
        context.advanced_filters_active,
    )


def build_filters_summary_raw_signature(
    *,
    context: FilterSummaryContext,
) -> tuple:
    return (
        str(context.search_text or "").strip(),
        tuple((str(k), str(v)) for k, v in context.active_column_filters.items()),
        _freeze_summary_action(context.column_or_groups or []),
        _freeze_summary_action(context.advanced_filters),
        bool(context.advanced_filters_active),
        bool(context.exclude_terminal_statuses),
        str(context.dedicated_or_text or "").strip(),
        str(context.theme_name or "dark"),
    )


def _add_column_filter_summary_entries(
    summary_entries: OrderedDict[str, SummaryEntry],
    *,
    active_column_filters: dict,
    column_or_groups: list,
    column_to_or_group: dict,
    display_name_for_column,
    format_value,
) -> None:
    if not active_column_filters:
        return
    for group in column_or_groups:
        _add_column_or_group_summary_entry(
            summary_entries,
            group,
            display_name_for_column=display_name_for_column,
            format_value=format_value,
        )
    for col_name, filter_value in active_column_filters.items():
        if col_name in column_to_or_group:
            continue
        normalized_value = format_value(str(filter_value), column=col_name)
        if not normalized_value:
            continue
        merge_summary_actions(
            summary_entries,
            text=f"{display_name_for_column(col_name)}: {normalized_value}",
            actions=[{"kind": "column", "column": str(col_name)}],
        )


def _add_column_or_group_summary_entry(
    summary_entries: OrderedDict[str, SummaryEntry],
    group: dict,
    *,
    display_name_for_column,
    format_value,
) -> None:
    values = list(group.get("values", []) or [])
    if not values:
        return
    columns = list(group.get("columns", []) or [])
    if set(columns) == {"setor_executor", "setor_emissor"}:
        label = "Executor ou Emissor (OU)"
    else:
        column_names = " ou ".join(display_name_for_column(column) for column in columns)
        label = f"{column_names} (OU)"
    values_txt = format_value(", ".join(values))
    if not values_txt:
        return
    action_column = str(columns[0]) if columns else ""
    merge_summary_actions(
        summary_entries,
        text=f"{label}: {values_txt}",
        actions=[
            {
                "kind": "column_or_group",
                "column": action_column,
                "columns": columns,
            }
        ],
    )


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
        target[normalized_text] = _new_summary_entry(normalized_text, actions)
        return
    _append_unique_summary_actions(entry, actions)


def _new_summary_entry(text: str, actions: list[SummaryAction]) -> SummaryEntry:
    valid_actions = [action for action in actions if isinstance(action, dict)]
    return {
        "text": text,
        "actions": valid_actions,
    }


def _append_unique_summary_actions(
    entry: SummaryEntry,
    actions: list[SummaryAction],
) -> None:
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


def _freeze_summary_action(value: Any) -> Any:
    if isinstance(value, dict):
        return (
            "dict",
            tuple((str(key), _freeze_summary_value(item)) for key, item in value.items()),
        )
    return _freeze_summary_value(value)


def _freeze_summary_value(value: Any) -> Any:
    if isinstance(value, dict):
        return (
            "dict",
            tuple((str(key), _freeze_summary_value(item)) for key, item in value.items()),
        )
    if isinstance(value, (list, tuple)):
        return tuple(_freeze_summary_value(item) for item in value)
    if isinstance(value, set):
        return tuple(sorted((_freeze_summary_value(item) for item in value), key=repr))
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    return ("str", str(value))
