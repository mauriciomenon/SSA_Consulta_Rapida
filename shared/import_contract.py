"""Shared import/validation contract for SSA ingestion."""

MANDATORY_SCHEMA_COLUMNS = frozenset({"numero_ssa", "descricao_ssa", "data_cadastro"})

VALIDATION_REQUIRED_COLUMNS = (
    ("numero_ssa", "warning"),
    ("data_cadastro", "error"),
    ("situacao", "warning"),
)

ALLOWED_MISSING_DATA_CADASTRO_STATUSES = frozenset({"SCC", "ADI", "ASE"})
