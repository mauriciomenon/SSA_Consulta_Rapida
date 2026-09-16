"""Data access helpers for SSA details and derivadas views."""

from __future__ import annotations

import os
from typing import Any

from shared.numero_ssa import normalize_strict as normalize_numero_ssa_strict
from utils.robust_logging import get_robust_logger

logger = get_robust_logger().get_logger(__name__, "gui")


def resolve_current_db_path(window: Any = None) -> str | None:
    candidate = getattr(window, "db_path", None) if window is not None else None
    if isinstance(candidate, str) and candidate.strip():
        return candidate
    try:
        from gui import gui_ssa as gui_ssa_module
    except Exception as exc:
        logger.debug("Falha ao importar gui_ssa para resolver DB atual: %s", exc)
        return None
    db_path = getattr(gui_ssa_module, "DB_PATH", None)
    if isinstance(db_path, str) and db_path.strip():
        return db_path
    return None


def get_db_mtime(db_path: str | None) -> float | None:
    if not db_path:
        return None
    try:
        return os.path.getmtime(db_path)
    except Exception as exc:
        logger.debug("Falha ao ler mtime do banco de detalhes %s: %s", db_path, exc)
        return None


def get_derivadas_graph_cache_token(db_path: str | None) -> tuple[str, object]:
    """Token de invalidacao para dados derivados do grafo de derivadas.

    Usa o graph_fingerprint do ultimo sync_run com status 'ok'; cai para o
    mtime do arquivo quando a tabela nao existe, o ultimo run falhou ou o
    fingerprint esta ausente.
    """
    fingerprint = _latest_derivadas_graph_fingerprint(db_path)
    if fingerprint:
        return ("graph", fingerprint)
    return ("mtime", get_db_mtime(db_path))


def _latest_derivadas_graph_fingerprint(db_path: str | None) -> str | None:
    if not db_path or not os.path.exists(db_path):
        return None
    try:
        from armazenamento.database import get_db_connection
    except Exception as exc:
        logger.debug("Falha ao importar conexao para fingerprint: %s", exc)
        return None
    try:
        with get_db_connection(db_path, read_only=True) as conn:
            row = conn.execute(
                """
                SELECT graph_fingerprint, status
                FROM ssa_derivada_sync_run
                ORDER BY sync_run_id DESC
                LIMIT 1
                """
            ).fetchone()
    except Exception as exc:
        logger.debug("Falha ao ler fingerprint do grafo de derivadas: %s", exc)
        return None
    if not row or row[1] != "ok":
        return None
    fingerprint = row[0]
    if not fingerprint:
        return None
    return str(fingerprint)


def load_derivadas_snapshot(
    db_path: str | None,
    target: str,
    *,
    max_nodes: int,
) -> dict[str, Any] | None:
    if not db_path or not os.path.exists(db_path):
        return None
    try:
        from armazenamento import derivadas_queries

        return derivadas_queries.get_ssa_hierarchy_snapshot(
            db_path,
            target,
            max_distance=None,
            max_nodes=max_nodes,
        )
    except Exception as exc:
        logger.debug(
            "Falha ao coletar arvore de derivadas no DB para %s: %s", target, exc
        )
        return None


def build_local_family_payload(
    target: str,
    edges: list[tuple[str, str]],
    *,
    max_nodes: int,
) -> dict[str, Any] | None:
    try:
        from armazenamento.derivadas_queries import build_family_payload_from_edges

        return build_family_payload_from_edges(
            target,
            edges,
            max_nodes=max_nodes,
            allow_relation_ids=normalize_numero_ssa_strict(target) is None,
        )
    except Exception as exc:
        logger.debug(
            "Falha ao montar payload local de familia de derivadas para %s: %s",
            target,
            exc,
        )
        return None
