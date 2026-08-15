"""Advanced filter activity rules."""

from __future__ import annotations

ACTIVE_LIST_KEYS = (
    "setor_executor",
    "setor_emissor",
    "situacao",
    "solicitante",
    "responsavel_programacao",
    "responsavel_execucao",
)

ACTIVE_EXCLUDE_LIST_KEYS = (
    "setor_executor_exclude_values",
    "setor_emissor_exclude_values",
    "situacao_exclude_values",
    "solicitante_exclude_values",
    "responsavel_programacao_exclude_values",
    "responsavel_execucao_exclude_values",
    "prioridade_emissao_exclude_values",
    "prioridade_planejamento_exclude_values",
)

ACTIVE_YEAR_KEYS = (
    "ano_emissao",
    "ano_execucao",
    "ano_emissao_values",
    "ano_execucao_values",
    "ano_emissao_exclude_values",
    "ano_execucao_exclude_values",
)

ACTIVE_PRIORITY_KEYS = (
    "prioridade_emissao_values",
    "prioridade_planejamento_values",
)

ACTIVE_WEEK_RANGE_KEYS = (
    "semana_emissao_inicio",
    "semana_emissao_fim",
    "semana_execucao_inicio",
    "semana_execucao_fim",
)

ACTIVE_DERIVADA_KEYS = (
    "derivada_has",
    "derivada_all_ste",
    "derivada_is",
)


def has_active_advanced_filters(data: dict) -> bool:
    if not isinstance(data, dict) or not data:
        return False
    for key in ACTIVE_LIST_KEYS:
        if data.get(key):
            return True
    for key in ACTIVE_EXCLUDE_LIST_KEYS:
        if data.get(key):
            return True
    for key in ACTIVE_YEAR_KEYS:
        if data.get(key):
            return True
    for key in ACTIVE_PRIORITY_KEYS:
        if data.get(key):
            return True
    if data.get("num_reprogramacoes_values"):
        return True
    for key in ACTIVE_WEEK_RANGE_KEYS:
        if data.get(key) is not None:
            return True
    for key in ACTIVE_DERIVADA_KEYS:
        if data.get(key):
            return True
    return bool(data.get("macro_filter"))
