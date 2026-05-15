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


def normalize_nonempty_string_series(series: pd.Series) -> pd.Series:
    return series.astype("string").fillna("").str.strip()


def exclude_terminal_status_rows(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty or "situacao" not in df.columns:
        return df
    return df[
        ~df["situacao"].astype(str).str.upper().isin(EXCLUDED_TERMINAL_STATUSES)
    ]


def collect_nonempty_column_values(df: pd.DataFrame, column: str) -> list[str]:
    if not isinstance(df, pd.DataFrame) or df.empty or column not in df.columns:
        return []
    series = normalize_nonempty_string_series(df[column].dropna())
    return series[series != ""].astype(str).tolist()


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


def known_division_rank(div: str) -> int:
    if div == "SMIN":
        return 0
    if div == "SMME":
        return 1
    if div:
        return 2
    return 3


def sector_sort_key(
    sector: str,
    sector_to_div: Mapping[str, str] | None = None,
) -> tuple[int, str, str]:
    value = str(sector or "").strip()
    sector_to_div = sector_to_div or {}
    div = sector_to_div.get(value) or sector_to_div.get(value.upper(), "")
    return (known_division_rank(str(div)), str(div).casefold(), value.casefold())


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
            ordered.append(by_upper[item])
            used_upper.add(item)
    remaining = [item for item in cleaned if item.upper() not in used_upper]
    remaining.sort(key=lambda item: sector_sort_key(item, sector_to_div))
    return ordered + remaining


def _best_sector_from_counts(counts: Mapping[str, int] | None) -> str:
    if not counts:
        return ""
    best_sector = ""
    best_key = (-1, 0, "")
    for raw_sector, raw_count in counts.items():
        sector = str(raw_sector)
        key = (int(raw_count), -len(sector), sector.casefold())
        if key > best_key:
            best_sector = sector
            best_key = key
    return best_sector


def _responsavel_sector_long_frame(
    df: pd.DataFrame,
    resp_col: str,
    sector_cols: list[str],
) -> pd.DataFrame:
    resp_series = normalize_nonempty_string_series(df[resp_col])
    wide = pd.DataFrame({resp_col: resp_series}, index=df.index)
    for sector_col in sector_cols:
        wide[sector_col] = normalize_nonempty_string_series(df[sector_col])
    long = wide.melt(id_vars=resp_col, value_vars=sector_cols, value_name="sector")
    return long[(long[resp_col] != "") & (long["sector"] != "")]


def _sector_counts_from_long_frame(
    long: pd.DataFrame,
    resp_col: str,
) -> dict[str, dict[str, int]]:
    pivot = (
        long.groupby([resp_col, "sector"], dropna=False)
        .size()
        .unstack(fill_value=0)
    )
    stacked = pivot.stack()
    stacked = stacked[stacked > 0]
    sector_counts: dict[str, dict[str, int]] = {}
    for (person, sector), count in stacked.items():
        sector_counts.setdefault(str(person), {})[str(sector)] = int(count)
    return sector_counts


def build_responsavel_sector_counts(
    df: pd.DataFrame,
    resp_col: str,
    *,
    sector_columns: Iterable[str] = ("setor_executor", "setor_emissor"),
) -> dict[str, dict[str, int]]:
    if not isinstance(df, pd.DataFrame) or df.empty or resp_col not in df.columns:
        return {}
    sector_cols = [column for column in sector_columns if column in df.columns]
    if not sector_cols:
        return {}
    long = _responsavel_sector_long_frame(df, resp_col, sector_cols)
    if long.empty:
        return {}
    return _sector_counts_from_long_frame(long, resp_col)


def order_responsavel_values(
    values: Iterable[Any] | None,
    sector_counts: Mapping[str, Mapping[str, int]] | None = None,
    *,
    sector_to_div: Mapping[str, str] | None = None,
) -> list[tuple[str, str]]:
    cleaned = dedupe_nonempty_strings(values)
    sector_counts = sector_counts or {}
    sector_to_div = sector_to_div or {}

    person_meta = {}
    for person in cleaned:
        sector = _best_sector_from_counts(sector_counts.get(person))
        div = sector_to_div.get(sector, "")
        if div and sector:
            prefix = f"{div} / {sector} - "
        elif sector:
            prefix = f"{sector} - "
        else:
            prefix = ""
        person_meta[person] = (
            (
                known_division_rank(str(div)),
                div.casefold(),
                sector.casefold(),
                person.casefold(),
            ),
            prefix,
        )

    decorated: list[tuple[str, str]] = []
    for person in sorted(cleaned, key=lambda value: person_meta[value][0]):
        prefix = person_meta[person][1]
        decorated.append((person, f"{prefix}{person}"))
    return decorated


def subset_by_sector_filters(
    df: pd.DataFrame,
    *,
    executor_include: Iterable[Any] | None = None,
    executor_exclude: Iterable[Any] | None = None,
    emissor_include: Iterable[Any] | None = None,
    emissor_exclude: Iterable[Any] | None = None,
) -> pd.DataFrame:
    if not isinstance(df, pd.DataFrame) or df.empty:
        return df
    mask = pd.Series(True, index=df.index)
    normalized: dict[str, pd.Series] = {}
    for column in ("setor_executor", "setor_emissor"):
        if column in df.columns:
            normalized[column] = normalize_nonempty_string_series(df[column])
    filters = (
        ("setor_executor", executor_include, True),
        ("setor_executor", executor_exclude, False),
        ("setor_emissor", emissor_include, True),
        ("setor_emissor", emissor_exclude, False),
    )
    for column, raw_values, include in filters:
        values = {
            str(value).strip() for value in (raw_values or []) if str(value).strip()
        }
        if not values or column not in df.columns:
            continue
        series = normalized.get(column)
        if series is None:
            series = normalize_nonempty_string_series(df[column])
            normalized[column] = series
        current_mask = series.isin(values)
        mask &= current_mask if include else ~current_mask
    return df[mask]

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
