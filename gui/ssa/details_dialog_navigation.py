"""Navigation protocol parsing for SSA details dialog links."""

from __future__ import annotations

COPY_SSA_PREFIX = "copy-ssa:"
DERIVADAS_TREE_PREFIXES = ("derivadas:tree", "derivadas://tree")
SSA_NAVIGATION_PREFIXES = (
    "ssa-context:",
    "ssa-panel:",
    "ssa-details:",
    "ssa_details://",
    "ssa:",
)


def resolve_details_anchor(href: str) -> tuple[str, str]:
    if not href:
        return "", ""
    if href.startswith(COPY_SSA_PREFIX):
        return "copy", href[len(COPY_SSA_PREFIX) :].strip().lstrip("/")
    for prefix in DERIVADAS_TREE_PREFIXES:
        if href.startswith(prefix):
            return "root", href[len(prefix) :].strip().lstrip("/")
    for prefix in SSA_NAVIGATION_PREFIXES:
        if href.startswith(prefix):
            return "ssa", href[len(prefix) :].strip().lstrip("/")
    return "", ""
