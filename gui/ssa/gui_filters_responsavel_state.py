# gui/ssa/gui_filters_responsavel_state.py
# Relation: owns advanced responsible-filter materialization state.

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, NamedTuple


RESPONSAVEL_FILTER_PREFIXES = (
    "adv_responsavel_solicitante",
    "adv_responsavel_programacao",
    "adv_responsavel_execucao",
)


class ResponsavelStatus(NamedTuple):
    materialized: bool
    is_dirty: bool


@dataclass(slots=True)
class ResponsavelMaterializationState:
    all_prefixes: set[str] = field(default_factory=set)
    dirty_prefixes: set[str] = field(default_factory=set)
    built_prefixes: set[str] = field(default_factory=set)

    def status_flags(
        self, prefixes: Iterable[str] | None = None
    ) -> ResponsavelStatus:
        required = (
            set(self.all_prefixes)
            if prefixes is None
            else {prefix for prefix in prefixes if prefix in self.all_prefixes}
        )
        dirty = self.dirty_prefixes
        built = self.built_prefixes
        materialized = bool(
            not required
        ) or (required.issubset(built) and not bool(required & dirty))
        return ResponsavelStatus(materialized, bool(required & dirty))

    def sync_prefixes(self, prefixes: Iterable[str]) -> None:
        updated = set(prefixes)
        new_prefixes = updated - self.all_prefixes
        self.all_prefixes = updated
        self.dirty_prefixes = (self.dirty_prefixes & updated) | new_prefixes
        self.built_prefixes &= updated

    def mark_dirty(self, prefixes: Iterable[str] | None = None) -> None:
        all_prefixes = self.all_prefixes
        if prefixes is None:
            self.dirty_prefixes |= all_prefixes
        else:
            self.dirty_prefixes |= {
                prefix for prefix in prefixes if prefix in all_prefixes
            }

    def mark_materialized(self, prefixes: Iterable[str]) -> None:
        processed = {prefix for prefix in prefixes if prefix in self.all_prefixes}
        self.built_prefixes |= processed
        self.dirty_prefixes -= processed

    def reset(self) -> None:
        self.built_prefixes.clear()
        self.dirty_prefixes = set(self.all_prefixes)

    def stale_built_prefixes(self) -> set[str]:
        """Prefixes built once and marked dirty by a later sector/filter change."""
        return self.built_prefixes & self.dirty_prefixes

    def is_materialized(self, prefix: str) -> bool:
        return prefix in self.built_prefixes and prefix not in self.dirty_prefixes


def responsavel_materialization_state(window) -> ResponsavelMaterializationState:
    state = getattr(window, "responsavel_materialization_state", None)
    if not isinstance(state, ResponsavelMaterializationState):
        raise AttributeError(
            "responsavel_materialization_state must be initialized by the window"
        )
    state.sync_prefixes(RESPONSAVEL_FILTER_PREFIXES)
    return state
