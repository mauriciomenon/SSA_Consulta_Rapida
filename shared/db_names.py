"""Shared canonical table names for SSA runtime."""

CANONICAL_SSA_TABLE = "ssa_table"
LEGACY_SSA_TABLE_ALIASES = frozenset({"ssas", "ssa_chamados"})
ALL_SSA_TABLE_NAMES = (
    CANONICAL_SSA_TABLE,
    "ssas",
    "ssa_chamados",
)
