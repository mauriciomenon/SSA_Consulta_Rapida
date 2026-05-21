"""Build removal plans for active filter summary actions."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from gui.ssa.filter_summary_entries import SummaryAction
from utils.robust_logging import get_robust_logger

logger = get_robust_logger().get_logger(__name__, "gui")


@dataclass
class SummaryRemovalPlan:
    clear_general_search_state: bool = False
    refresh_needed: bool = False
    sync_advanced_ui: bool = False
    sync_quick_combo: bool = False
    clear_dedicated_or_text: bool = False
    clear_exclude_terminal_statuses: bool = False
    columns_to_reset: list[str] = field(default_factory=list)
    removal_advanced_keys: list[str] = field(default_factory=list)


def build_summary_removal_plan(actions: list[SummaryAction]) -> SummaryRemovalPlan:
    plan = SummaryRemovalPlan()
    for action in actions:
        _collect_summary_removal_action(action, plan)
    return plan


def _collect_summary_removal_action(
    action: SummaryAction, plan: SummaryRemovalPlan
) -> None:
    if not isinstance(action, dict):
        return
    kind = str(action.get("kind") or "").strip()
    if kind == "search":
        plan.clear_general_search_state = True
        plan.refresh_needed = True
        return
    if kind == "dedicated_or":
        plan.clear_dedicated_or_text = True
        plan.refresh_needed = True
        return
    if kind == "exclude_ste_sca":
        plan.clear_exclude_terminal_statuses = True
        plan.sync_advanced_ui = True
        plan.refresh_needed = True
        return
    if kind in {"column", "column_or_group"}:
        _collect_column_reset(action, plan)
        return
    if kind == "advanced_keys":
        _collect_advanced_keys(action, plan)
        return
    raise ValueError(f"Acao de resumo de filtros nao suportada: {action!r}")


def _collect_column_reset(action: dict[str, Any], plan: SummaryRemovalPlan) -> None:
    column_name = str(action.get("column") or "").strip()
    if not column_name:
        logger.warning("Resumo de filtros recebeu acao sem coluna valida: %r", action)
        return
    if column_name not in plan.columns_to_reset:
        plan.columns_to_reset.append(column_name)


def _collect_advanced_keys(action: dict[str, Any], plan: SummaryRemovalPlan) -> None:
    raw_keys = action.get("keys")
    if isinstance(raw_keys, str):
        raw_key_values = [raw_keys]
    elif isinstance(raw_keys, (list, tuple, set)):
        raw_key_values = list(raw_keys)
    else:
        raw_key_values = []
    keys = [str(key).strip() for key in raw_key_values if str(key).strip()]
    if not keys:
        logger.warning("Resumo de filtros recebeu advanced_keys sem chaves: %r", action)
        return
    for key in keys:
        if key not in plan.removal_advanced_keys:
            plan.removal_advanced_keys.append(key)
