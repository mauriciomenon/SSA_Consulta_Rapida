"""Domain rules used by SSA filters."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

import pandas as pd

EXCLUDED_TERMINAL_STATUSES = frozenset({"SCA", "SES", "STE"})
EXCLUDED_TERMINAL_SUMMARY = "situacao!=SCA/SES/STE"
SECTOR_EXECUTOR_PRIORITY = (
    "IEE1",
    "IEE2",
    "IEE3",
    "IEE4",
    "MEL1",
    "MEL2",
    "MEL3",
    "MEL4",
)


def exclude_terminal_status_rows(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty or "situacao" not in df.columns:
        return df
    return df[
        ~df["situacao"].astype(str).str.upper().isin(EXCLUDED_TERMINAL_STATUSES)
    ]


def collect_nonempty_column_values(df: pd.DataFrame, column: str) -> list[str]:
    if not isinstance(df, pd.DataFrame) or df.empty or column not in df.columns:
        return []
    values: list[str] = []
    for raw in df[column].dropna().astype(str):
        value = str(raw).strip()
        if value:
            values.append(value)
    return values


def dedupe_nonempty_strings(values: Iterable[Any] | None) -> list[str]:
    cleaned: list[str] = []
    seen: set[str] = set()
    iterable = () if values is None else values
    for raw in iterable:
        value = str(raw).strip()
        if not value:
            continue
        key = value.casefold()
        if key in seen:
            continue
        seen.add(key)
        cleaned.append(value)
    return cleaned


def sector_sort_key(
    sector: str,
    sector_to_div: Mapping[str, str] | None = None,
) -> tuple[int, str, str]:
    value = str(sector or "").strip()
    sector_to_div = sector_to_div or {}
    div = sector_to_div.get(value) or sector_to_div.get(value.upper(), "")
    if div == "SMIN":
        div_rank = 0
    elif div == "SMME":
        div_rank = 1
    elif div:
        div_rank = 2
    else:
        div_rank = 3
    return (div_rank, str(div).casefold(), value.casefold())


def order_sector_values(
    values: Iterable[Any] | None,
    *,
    sector_to_div: Mapping[str, str] | None = None,
    priority: Iterable[str] = SECTOR_EXECUTOR_PRIORITY,
) -> list[str]:
    cleaned = dedupe_nonempty_strings(values)
    by_upper = {item.upper(): item for item in cleaned}
    ordered: list[str] = []
    used_upper: set[str] = set()
    for raw_priority in priority:
        item = str(raw_priority).strip().upper()
        if item in by_upper:
            ordered.append(item)
            used_upper.add(item)
    remaining = [item for item in cleaned if item.upper() not in used_upper]
    remaining.sort(key=lambda item: sector_sort_key(item, sector_to_div))
    return ordered + remaining

ADVANCED_FILTER_VISUAL_COLUMN_MAP = {
    "setor_executor": ("setor_executor",),
    "setor_executor_exclude_values": ("setor_executor",),
    "setor_emissor": ("setor_emissor",),
    "setor_emissor_exclude_values": ("setor_emissor",),
    "divisao": ("divisao",),
    "divisao_exclude_values": ("divisao",),
    "situacao": ("situacao",),
    "situacao_exclude_values": ("situacao",),
    "solicitante": ("solicitante", "responsavel_solicitante"),
    "solicitante_exclude_values": ("solicitante", "responsavel_solicitante"),
    "responsavel_programacao": ("responsavel_programacao",),
    "responsavel_programacao_exclude_values": ("responsavel_programacao",),
    "responsavel_execucao": ("responsavel_execucao",),
    "responsavel_execucao_exclude_values": ("responsavel_execucao",),
    "prioridade_emissao_values": ("prioridade_emissao", "grau_prioridade_emissao"),
    "prioridade_emissao_exclude_values": (
        "prioridade_emissao",
        "grau_prioridade_emissao",
    ),
    "prioridade_planejamento_values": (
        "prioridade_planejamento",
        "grau_prioridade_planejamento",
    ),
    "prioridade_planejamento_exclude_values": (
        "prioridade_planejamento",
        "grau_prioridade_planejamento",
    ),
    "ano_emissao": ("data_cadastro",),
    "ano_emissao_values": ("data_cadastro",),
    "ano_emissao_exclude_values": ("data_cadastro",),
    "ano_execucao": ("data_programada",),
    "ano_execucao_values": ("data_programada",),
    "ano_execucao_exclude_values": ("data_programada",),
    "semana_emissao_inicio": ("semana_cadastro",),
    "semana_emissao_fim": ("semana_cadastro",),
    "semana_execucao_inicio": ("semana_programada",),
    "semana_execucao_fim": ("semana_programada",),
    "derivada_has": ("derivada_de",),
    "derivada_all_ste": ("derivada_de",),
    "derivada_is": ("derivada_de",),
}
