"""Canonical UI column selection rules."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

EXCLUDED_CANONICAL_UI_COLUMNS = {
    "id",
    "desde",
    "desde_1",
    "desde_2",
    "ate",
    "ate_1",
    "ate_2",
    "tempo_excedido",
    "tempo_total",
    "tempo_disponivel",
    "total_tempo_tpe_planejado",
    "total_tempo_tex_planejado",
    "total_tempo_tpo_planejado",
    "total_tempo_tpe_executada",
    "total_tempo_tex_executada",
    "total_tempo_tpo_executada",
    "total_horas_programadas",
    "prazo_limite",
    "data_limite",
    "status_execucao_prazo",
    "sistema_origem",
    "data_planilha",
    "deviation_records",
    "situation_of_deviation",
    "partial_records",
    "situation_of_partial",
    "registros_espera",
    "num_reprobaciones",
    "situacao_espera",
    "numero_desvios",
    "justificativa",
    "parciais",
    "situacao_da_parcial",
    "atividade_especial",
    "equipamento_retirado",
    "sn_retirado",
    "destino",
    "equipamento_instalado",
    "sn_instalado",
    "sn_extra",
    "origem",
    "desativacao_da_localizacao",
    "instalacao_estimada",
    "executado",
    "concluido",
    "situacao_de_desvio",
    "relacao",
}

LEGACY_INVALID_UI_COLUMNS = {
    "Numero da SSA",
    "Número da SSA",
    "No SSA",
    "Data Cadastro",
}


@dataclass(frozen=True)
class CanonicalColumnInputs:
    visible_columns: tuple[str, ...]
    default_columns: tuple[str, ...]
    profile_columns: tuple[str, ...]
    current_display_columns: tuple[str, ...]
    active_filter_columns: tuple[str, ...]
    widget_columns: tuple[str, ...]
    non_null_columns: tuple[str, ...]
    allowed_columns_text: str
    default_display_mappings: dict[str, Any]
    internal_to_display: dict[str, Any] | None
    display_map: dict[str, Any] | None
    compatibility_null_ui_columns: set[str]

    def cache_key(self, data_revision: int) -> tuple[Any, ...]:
        return (
            data_revision,
            self.visible_columns,
            self.default_columns,
            self.profile_columns,
            self.current_display_columns,
            self.active_filter_columns,
            self.widget_columns,
            tuple(sorted(self.non_null_columns)),
            self.allowed_columns_text,
        )


def build_canonical_available_columns(inputs: CanonicalColumnInputs) -> list[str]:
    candidates: list[str] = []
    seen_candidates: set[str] = set()
    always_allow: set[str] = set()
    mapped_columns: set[str] = set()

    def append_candidate(value: Any, *, allow: bool = False) -> None:
        if not isinstance(value, str):
            return
        col_name = value.strip()
        if not col_name or col_name == "#":
            return
        if col_name in seen_candidates:
            if allow:
                always_allow.add(col_name)
            return
        seen_candidates.add(col_name)
        candidates.append(col_name)
        if allow:
            always_allow.add(col_name)

    def collect_mapped_keys(mapping_obj: Any) -> None:
        if not isinstance(mapping_obj, dict):
            return
        for key in mapping_obj.keys():
            if not isinstance(key, str):
                continue
            key_name = key.strip()
            if key_name:
                mapped_columns.add(key_name)

    for values in (
        inputs.visible_columns,
        inputs.default_columns,
        inputs.profile_columns,
        inputs.current_display_columns,
        inputs.active_filter_columns,
        inputs.widget_columns,
    ):
        for value in values:
            append_candidate(value, allow=True)

    collect_mapped_keys(inputs.default_display_mappings)
    collect_mapped_keys(inputs.internal_to_display)
    collect_mapped_keys(inputs.display_map)

    allowed_columns = _parse_allowed_columns(inputs.allowed_columns_text)
    for col_name in mapped_columns:
        append_candidate(col_name, allow=(col_name in always_allow))
    for col_name in inputs.non_null_columns:
        append_candidate(col_name, allow=(col_name in always_allow))
    for col_name in always_allow:
        append_candidate(col_name, allow=True)

    result: list[str] = []
    seen: set[str] = set()
    for col in candidates:
        col_name = col.strip()
        if col_name in seen:
            continue
        if not _is_canonical_column(
            col_name,
            always_allow=always_allow,
            allowed_columns=allowed_columns,
            compatibility_null_ui_columns=inputs.compatibility_null_ui_columns,
        ):
            continue
        seen.add(col_name)
        result.append(col_name)
    return result


def _parse_allowed_columns(raw_text: str) -> set[str] | None:
    allowed_raw = str(raw_text or "").strip()
    if not allowed_raw:
        return None
    return {token.strip() for token in allowed_raw.split(",") if token.strip()}


def _is_canonical_column(
    col_name: str,
    *,
    always_allow: set[str],
    allowed_columns: set[str] | None,
    compatibility_null_ui_columns: set[str],
) -> bool:
    if not col_name or col_name == "#":
        return False
    if col_name in always_allow:
        return True
    if col_name in compatibility_null_ui_columns:
        return False
    if col_name in LEGACY_INVALID_UI_COLUMNS:
        return False
    if col_name in EXCLUDED_CANONICAL_UI_COLUMNS:
        return False
    if "_relacionada_" in col_name or "_relacionado_" in col_name:
        return False
    if not re.fullmatch(r"[a-z][a-z0-9_]*", col_name):
        return False
    return not (isinstance(allowed_columns, set) and col_name not in allowed_columns)
