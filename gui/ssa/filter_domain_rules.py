"""Domain rules used by SSA filters."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

import pandas as pd

EXCLUDED_TERMINAL_STATUSES = frozenset({"SCA", "SES", "STE"})
EXCLUDED_TERMINAL_SUMMARY = "situacao!=SCA/SES/STE"
MACRO_BAIXAR_FILTER_KEY = "ssas_para_baixar"
# SAD is macro-specific here; global terminal filtering stays SCA/SES/STE.
MACRO_BAIXAR_STATUS_EXCLUSIONS = ("SAD", "SCA", "SES", "STE")
MACRO_BAIXAR_DERIVADA_SELECTION = ("all_ste",)
SECTOR_EXECUTOR_PRIORITY = (
    "IEE3",
    "IEE1",
    "IEE2",
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
    normalized = str(div or "").upper()
    if normalized == "SMIN":
        return 0
    if normalized == "SMME":
        return 1
    if normalized:
        return 2
    return 3


def sector_sort_key(
    sector: str,
    sector_to_div: Mapping[str, str] | None = None,
) -> tuple[int, str, str]:
    value = str(sector or "").strip()
    sector_to_div = sector_to_div or {}
    div = (
        sector_to_div.get(value)
        or sector_to_div.get(value.upper())
        or sector_to_div.get(value.lower())
        or ""
    )
    div_text = str(div)
    return (
        known_division_rank(div_text.upper()),
        div_text.casefold(),
        value.casefold(),
    )


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
    best_count = -1
    best_name_key: str | None = None
    for raw_sector, raw_count in counts.items():
        sector = str(raw_sector)
        count = int(raw_count)
        name_key = sector.casefold()
        if count > best_count or (
            count == best_count
            and (best_name_key is None or name_key < best_name_key)
        ):
            best_sector = sector
            best_count = count
            best_name_key = name_key
    return best_sector


def _count_responsavel_sector_pairs(
    row_index,
    responsavel_series: Mapping[str, pd.Series],
    sector_series: Mapping[str, pd.Series],
) -> dict[str, dict[str, dict[str, int]]]:
    if not responsavel_series or not sector_series:
        return {}
    result: dict[str, dict[str, dict[str, int]]] = {}
    for resp_col, person_series in responsavel_series.items():
        column_result = _count_single_responsavel_sector_pairs(
            row_index,
            person_series,
            sector_series,
        )
        if column_result:
            result[str(resp_col)] = column_result
    return result


def _count_single_responsavel_sector_pairs(
    row_index,
    person_series: pd.Series,
    sector_series: Mapping[str, pd.Series],
) -> dict[str, dict[str, int]]:
    indexes = _person_sector_indexes(row_index, person_series, sector_series)
    if not indexes:
        return {}
    combined_index = indexes[0].append(indexes[1:])
    return _count_person_sector_index(combined_index.drop_duplicates())


def _person_sector_indexes(
    row_index,
    person_series: pd.Series,
    sector_series: Mapping[str, pd.Series],
) -> list[pd.MultiIndex]:
    # The current domain contract uses two sector columns: executor and emissor.
    row_values = pd.Index(row_index).to_numpy()
    person_values = person_series.to_numpy()
    indexes: list[pd.MultiIndex] = []
    for sector_values in sector_series.values():
        sector_array = sector_values.to_numpy()
        valid = (person_values != "") & (sector_array != "")
        if valid.any():
            indexes.append(
                pd.MultiIndex.from_arrays(
                    (
                        row_values[valid],
                        person_values[valid],
                        sector_array[valid],
                    ),
                    names=("row_id", "person", "sector"),
                )
            )
    return indexes


def _count_person_sector_index(
    unique_pairs: pd.MultiIndex,
) -> dict[str, dict[str, int]]:
    counts = unique_pairs.droplevel("row_id").value_counts()
    result: dict[str, dict[str, int]] = {}
    for (person, sector), count in counts.items():
        result.setdefault(str(person), {})[str(sector)] = int(count)
    return result


def build_responsavel_sector_counts(
    df: pd.DataFrame,
    resp_col: str,
    *,
    sector_columns: Iterable[str] = ("setor_executor", "setor_emissor"),
) -> dict[str, dict[str, int]]:
    return build_responsavel_sector_counts_by_column(
        df,
        (resp_col,),
        sector_columns=sector_columns,
    ).get(resp_col, {})


def build_responsavel_sector_counts_by_column(
    df: pd.DataFrame,
    resp_columns: Iterable[str],
    *,
    sector_columns: Iterable[str] = ("setor_executor", "setor_emissor"),
) -> dict[str, dict[str, dict[str, int]]]:
    if not isinstance(df, pd.DataFrame) or df.empty:
        return {}
    sector_cols = [column for column in sector_columns if column in df.columns]
    if not sector_cols:
        return {}
    normalized_sectors = {
        sector_col: normalize_nonempty_string_series(df[sector_col])
        for sector_col in sector_cols
    }
    resp_cols = [resp_col for resp_col in resp_columns if resp_col in df.columns]
    if not resp_cols:
        return {}
    normalized_responsaveis = {
        resp_col: normalize_nonempty_string_series(df[resp_col])
        for resp_col in resp_cols
    }
    return _count_responsavel_sector_pairs(
        df.index,
        normalized_responsaveis,
        normalized_sectors,
    )


def order_responsavel_values(
    values: Iterable[Any] | None,
    sector_counts: Mapping[str, Mapping[str, int]] | None = None,
    *,
    sector_to_div: Mapping[str, str] | None = None,
) -> list[tuple[str, str]]:
    cleaned = dedupe_nonempty_strings(values)
    sector_counts = sector_counts or {}
    sector_to_div = sector_to_div or {}

    decorated_meta = []
    for person in cleaned:
        sector = _best_sector_from_counts(sector_counts.get(person))
        div = sector_to_div.get(sector, "")
        if div and sector:
            prefix = f"{div} / {sector} - "
        elif sector:
            prefix = f"{sector} - "
        else:
            prefix = ""
        decorated_meta.append(
            (
                (
                    known_division_rank(str(div)),
                    div.casefold(),
                    sector.casefold(),
                    person.casefold(),
                ),
                person,
                prefix,
            ),
        )

    return [
        (person, f"{prefix}{person}")
        for _, person, prefix in sorted(decorated_meta, key=lambda item: item[0])
    ]


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
        series = normalized.get(column)
        if not values or series is None:
            continue
        current_mask = series.isin(values)
        mask &= current_mask if include else ~current_mask
    return df[mask]


def generate_responsavel_sector_filter_cache_signature(
    df: pd.DataFrame,
    *,
    data_load_token: Any,
    executor_include: Iterable[Any] | None = None,
    executor_exclude: Iterable[Any] | None = None,
    emissor_include: Iterable[Any] | None = None,
    emissor_exclude: Iterable[Any] | None = None,
) -> tuple[Any, ...]:
    frame_token = (
        data_load_token
        if data_load_token is not None
        else _responsavel_sector_frame_fingerprint(df)
    )
    return (
        frame_token,
        len(df),
        tuple(str(column) for column in df.columns),
        tuple(executor_include or ()),
        tuple(executor_exclude or ()),
        tuple(emissor_include or ()),
        tuple(emissor_exclude or ()),
    )


def _responsavel_sector_frame_fingerprint(df: pd.DataFrame) -> int:
    # Fallback for callers without a data version token; structure-level only.
    try:
        first_index = df.index[0] if len(df.index) else None
        last_index = df.index[-1] if len(df.index) else None
        return hash(
            (
                len(df),
                first_index,
                last_index,
                tuple(str(column) for column in df.columns),
            )
        )
    except Exception:
        return hash(len(df))


def filter_responsavel_frame_by_sector_selection(
    df: pd.DataFrame,
    *,
    executor_include: Iterable[Any] | None = None,
    executor_exclude: Iterable[Any] | None = None,
    emissor_include: Iterable[Any] | None = None,
    emissor_exclude: Iterable[Any] | None = None,
) -> pd.DataFrame:
    return subset_by_sector_filters(
        df,
        executor_include=executor_include,
        executor_exclude=executor_exclude,
        emissor_include=emissor_include,
        emissor_exclude=emissor_exclude,
    )


def macro_baixar_filter_preset() -> dict[str, tuple[str, ...]]:
    return {
        "derivada_include_values": MACRO_BAIXAR_DERIVADA_SELECTION,
        "situacao_exclude_values": MACRO_BAIXAR_STATUS_EXCLUSIONS,
    }


def advanced_macro_filter_preset(choice: Any) -> dict[str, tuple[str, ...]] | None:
    if choice == MACRO_BAIXAR_FILTER_KEY:
        return macro_baixar_filter_preset()
    return None

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
    "derivada_include_values": ("derivada_de",),
    "derivada_has": ("derivada_de",),
    "derivada_all_ste": ("derivada_de",),
    "derivada_is": ("derivada_de",),
}
