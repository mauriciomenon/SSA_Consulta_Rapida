"""Re-exports from shared.numero_ssa for backward compatibility."""

from shared.numero_ssa import (
    bulk_normalize,
    bulk_normalize_relation,
    is_valid_numero_ssa,
    normalize_relation_id,
    normalize_strict,
)

__all__ = [
    "normalize_strict",
    "normalize_relation_id",
    "is_valid_numero_ssa",
    "bulk_normalize",
    "bulk_normalize_relation",
]
