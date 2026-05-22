"""Search refinement rules for GUI filtering."""

from __future__ import annotations

from collections.abc import Iterable

_UNSAFE_REFINEMENT_PREFIXES = ("!", "=", "~", "^")


def _normalized_term_keys(terms: Iterable[object]) -> tuple[str, ...]:
    return tuple(
        str(term).strip().casefold() for term in terms if str(term).strip()
    )


def can_reuse_refined_search(
    previous_terms: Iterable[object],
    current_terms: Iterable[object],
) -> bool:
    """Return true only for conservative subset reuse.

    This intentionally rejects semantic replacement. The previous filtered
    dataframe can be reused only when every previous simple term is still
    present or has become a stricter prefix extension in the current search.
    """
    previous_keys = _normalized_term_keys(previous_terms)
    current_keys = _normalized_term_keys(current_terms)
    if not current_keys:
        return False
    current_key_set = frozenset(current_keys)
    simple_current_keys = tuple(
        key for key in current_keys if not key.startswith(_UNSAFE_REFINEMENT_PREFIXES)
    )
    for previous_key in previous_keys:
        if previous_key in current_key_set:
            continue
        if previous_key.startswith(_UNSAFE_REFINEMENT_PREFIXES):
            return False
        if not any(
            current_key.startswith(previous_key) for current_key in simple_current_keys
        ):
            return False
    return True
