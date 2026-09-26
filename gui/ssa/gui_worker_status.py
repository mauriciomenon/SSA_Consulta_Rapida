# gui/ssa/gui_worker_status.py
# Relation: status text helpers used by gui/ssa/gui_workers.py.

from __future__ import annotations

from gui.workers.rescan_worker import RescanOutcome


def success_status_text(is_explicit_import: bool, outcome: RescanOutcome) -> str:
    if not is_explicit_import:
        return "Status: Reescaneamento concluido."
    if outcome == RescanOutcome.UPDATED:
        return "Status: Importacao concluida."
    if outcome == RescanOutcome.REJECTIONS_ONLY:
        return "Status: Importacao concluida com rejeicoes de regra."
    if outcome == RescanOutcome.NO_CHANGES:
        return "Status: Importacao concluida sem alteracoes."
    if outcome == RescanOutcome.CANCELLED:
        return "Status: Importacao cancelada."
    if outcome == RescanOutcome.ERROR:
        return "Status: Importacao falhou. Consulte os detalhes."
    return "Status: Importacao concluida com resultado desconhecido."


def consolidation_status_text(outcome: RescanOutcome) -> str:
    if outcome == RescanOutcome.UPDATED:
        return "Status: Consolidacao de arquivos concluida."
    return "Status: Consolidacao de arquivos concluida sem alteracoes."


def cancel_request_status_text(
    is_explicit_import: bool, operation_kind: str
) -> tuple[str, str]:
    if operation_kind == "consolidate":
        return (
            "Status: Cancelamento solicitado na consolidacao de arquivos.",
            "consolidate.cancel.requested",
        )
    if is_explicit_import:
        return (
            "Status: Cancelamento solicitado na importacao.",
            "explicit_import.cancel.requested",
        )
    return (
        "Status: Cancelamento solicitado no reescaneamento.",
        "rescan.cancel.requested",
    )


def already_running_status_text(
    *, is_explicit_import: bool, operation_kind: str
) -> tuple[str, str]:
    if operation_kind == "consolidate":
        return (
            "Status: Consolidacao de arquivos ja em andamento.",
            "consolidate.already_running",
        )
    if is_explicit_import:
        return (
            "Status: Importacao ja em andamento.",
            "explicit_import.already_running",
        )
    return (
        "Status: Reescaneamento ja em andamento.",
        "rescan.already_running",
    )
