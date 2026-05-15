"""Domain rules used by SSA filters."""

from __future__ import annotations

import pandas as pd

EXCLUDED_TERMINAL_STATUSES = frozenset({"SCA", "SES", "STE"})
EXCLUDED_TERMINAL_SUMMARY = "situacao!=SCA/SES/STE"


def exclude_terminal_status_rows(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty or "situacao" not in df.columns:
        return df
    return df[
        ~df["situacao"].astype(str).str.upper().isin(EXCLUDED_TERMINAL_STATUSES)
    ]

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
