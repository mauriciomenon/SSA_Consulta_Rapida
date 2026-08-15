"""SHIM: Re-exports from shared.numero_ssa for backward compatibility.

Canonical source: shared.numero_ssa
This shim exists because tests and scripts_manutencao/analyze_code_quality.py
import from core.numero_ssa. Production code uses shared.numero_ssa directly.
Candidate for removal once test imports are consolidated.
Tracked in docs/RECOVERY_BACKLOG.md.
"""

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
