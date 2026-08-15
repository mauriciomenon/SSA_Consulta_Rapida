"""General search column selection rules for the SSA GUI."""

from __future__ import annotations

import pandas as pd

from utils.robust_logging import get_robust_logger

logger = get_robust_logger().get_logger(__name__, "gui")

GENERAL_SEARCH_PRIORITY_COLUMNS = (
    "numero_ssa",
    "situacao",
    "derivada_de",
    "localizacao_codigo",
    "descricao_localizacao",
    "equipamento",
    "descricao_ssa",
    "descricao_execucao",
    "setor_emissor",
    "setor_executor",
    "solicitante",
    "responsavel_solicitante",
    "responsavel_programacao",
    "responsavel_execucao",
    "responsavel_emissor",
    "servico_origem",
    "sistema_origem",
    "arquivo_origem",
    "justificativa",
    "anomalia",
    "situacao_espera",
    "situacao_reprogramacao",
    "situacao_de_desvio",
    "atividade_especial",
    "destino",
    "origem",
    "numero_ssa_relacionada_1",
    "numero_ssa_relacionada_2",
    "numero_ssa_relacionada_3",
    "setor_emissor_relacionado_1",
    "setor_emissor_relacionado_2",
    "setor_executor_relacionado_1",
    "setor_executor_relacionado_2",
    "situacao_relacionada_1",
    "situacao_relacionada_2",
    "relacao",
    "grau_prioridade",
    "grau_prioridade_emissao",
    "grau_prioridade_planejamento",
    "prioridade_emissao",
    "prioridade_planejamento",
    "semana_cadastro",
    "semana_programada",
    "semana_executada",
)
GENERAL_SEARCH_EXCLUDED_COLUMNS = frozenset(
    {
        "id",
        "data_cadastro",
        "data_planilha",
        "execucao_simples",
        "prazo_limite",
        "prazo_limite_str",
        "status_execucao_prazo",
        "tempo_disponivel",
        "data_limite",
        "tempo_excedido",
        "desde",
        "tempo_total",
        "desde_1",
        "total_tempo_tpe_planejado",
        "total_tempo_tex_planejado",
        "total_tempo_tpo_planejado",
        "total_horas_programadas",
        "total_tempo_tpe_executada",
        "num_reprogramacoes",
        "execucao_parcial",
        "registros_espera",
        "num_reprobaciones",
        "numero_desvios",
        "ate",
        "total_tempo_tex_executada",
        "parciais",
        "situacao_da_parcial",
        "ate_1",
        "ate_2",
        "desde_2",
        "total_tempo_tpo_executada",
        "equipamento_retirado",
        "sn_retirado",
        "equipamento_instalado",
        "sn_instalado",
        "sn_extra",
        "desativacao_da_localizacao",
        "instalacao_estimada",
        "executado",
        "concluido",
        "data_inicio_programada",
        "data_programacao",
        "data_inicio_reprogramada",
        "data_reprogramacao",
        "total_de_reprogramacoes",
        "data_arquivo_origem",
        "data_cadastro_str",
    }
)
GENERAL_SEARCH_AUTO_EXCLUDE_PREFIXES = (
    "_",
    "data_",
    "tempo_",
    "total_",
    "sn_",
)
GENERAL_SEARCH_AUTO_EXCLUDE_SUFFIXES = (
    "_ts",
    "_timestamp",
    "_str",
)


def _is_general_search_auto_excluded(column_name: str) -> bool:
    normalized_name = str(column_name or "").strip()
    if not normalized_name:
        return True
    if normalized_name in GENERAL_SEARCH_EXCLUDED_COLUMNS:
        return True
    if normalized_name.startswith("prioridade_"):
        return False
    for prefix in GENERAL_SEARCH_AUTO_EXCLUDE_PREFIXES:
        if normalized_name.startswith(prefix):
            return True
    for suffix in GENERAL_SEARCH_AUTO_EXCLUDE_SUFFIXES:
        if normalized_name.endswith(suffix):
            return True
    return False


def _is_general_search_auto_includable(series: pd.Series) -> bool:
    dtype = series.dtype
    return bool(
        pd.api.types.is_string_dtype(dtype)
        or pd.api.types.is_object_dtype(dtype)
        or isinstance(dtype, pd.CategoricalDtype)
    )


def build_gui_general_search_columns(df: pd.DataFrame | None) -> list[str]:
    """
    Build the GUI-owned general search contract from the current DataFrame.

    The explicit ordered base list keeps core business columns first. Additional
    textual columns are appended when eligible; date/time, totals, timers,
    serials, cache fields, and other technical columns stay out by default.
    """
    if not isinstance(df, pd.DataFrame) or df.empty and len(df.columns) == 0:
        return []

    non_null_columns: set[str] | None = None
    try:
        non_null_attr = df.attrs.get("ssa_non_null_cols")
        if isinstance(non_null_attr, (list, tuple, set, frozenset)):
            non_null_columns = {str(col) for col in non_null_attr if str(col)}
    except Exception as exc:
        logger.debug(
            "Falha ao ler attrs de colunas nao nulas para busca geral: %s", exc
        )

    selected_columns: list[str] = []
    seen_columns: set[str] = set()

    for column_name in GENERAL_SEARCH_PRIORITY_COLUMNS:
        if non_null_columns is not None and column_name not in non_null_columns:
            continue
        if column_name in df.columns and column_name not in seen_columns:
            selected_columns.append(column_name)
            seen_columns.add(column_name)

    for column_name in df.columns:
        if column_name in seen_columns:
            continue
        if non_null_columns is not None and column_name not in non_null_columns:
            continue
        if _is_general_search_auto_excluded(column_name):
            continue
        series = df[column_name]
        if _is_general_search_auto_includable(series):
            selected_columns.append(column_name)
            seen_columns.add(column_name)

    return selected_columns
