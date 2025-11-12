"""Re-exports from shared.numero_ssa for backward compatibility."""

from shared.numero_ssa import normalize_strict, is_valid_numero_ssa, bulk_normalize

__all__ = ["normalize_strict", "is_valid_numero_ssa", "bulk_normalize"]
