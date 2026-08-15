"""SHIM: Re-exports from shared.date_utils for backward compatibility.

Canonical source: shared.date_utils
This shim exists because tests import from core.date_utils.
Production code uses shared.date_utils directly.
Candidate for removal once test imports are consolidated.
Tracked in docs/RECOVERY_BACKLOG.md.
"""

from shared.date_utils import parse_any_date, bulk_parse_dates

__all__ = ["parse_any_date", "bulk_parse_dates"]
