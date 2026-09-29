"""Shared canonical table names for SSA runtime."""

CANONICAL_SSA_TABLE = "ssa_table"
LEGACY_SSA_TABLE_ALIASES = frozenset({"ssas", "ssa_chamados"})
ALL_SSA_TABLE_NAMES = (
    CANONICAL_SSA_TABLE,
    "ssas",
    "ssa_chamados",
)

# Columns projected by the canonical CLI/runtime read path. Integrity checks use
# the same contract so a manually damaged schema cannot pass verification and
# then fail during the first real query.
SSA_READ_REQUIRED_COLUMNS = (
    "numero_ssa",
    "situacao",
    "derivada_de",
    "localizacao_codigo",
    "descricao_localizacao",
    "equipamento",
    "semana_cadastro",
    "data_cadastro",
    "descricao_ssa",
    "setor_emissor",
    "setor_executor",
    "solicitante",
    "servico_origem",
    "grau_prioridade_emissao",
    "grau_prioridade_planejamento",
    "execucao_simples",
    "responsavel_programacao",
    "semana_programada",
    "responsavel_execucao",
    "descricao_execucao",
    "id",
    "sistema_origem",
    "prazo_limite",
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
    "execucao_parcial",
    "anomalia",
    "semana_executada",
    "num_reprogramacoes",
)
