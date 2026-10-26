"""Espelho do estado da tela (BL-51, opcao A): filtros, ordenacao, colunas, pagina e SSA em foco.

Guarda so o estado e a identidade dos dados (nome do banco, mtime e contagem de linhas),
nunca as linhas. Ao reabrir aplica o estado sobre os dados ja carregados na janela: nao
recarrega nem grava o banco (numa copia de janela vale sobre os dados congelados dela).
"""

from __future__ import annotations

import json
import os
from datetime import datetime
from typing import Any

from gui.qt_stubs import Qt
from gui.ssa.filter_search_undo_controller import (
    restore_last_filter_state,
    snapshot_filter_state,
)
from gui.ssa.filter_state_utils import copy_filter_mapping
from gui.ssa.persistent_filters import (
    PersistentFilterJSONEncoder,
    _write_private_json_file,
)
from utils.robust_logging import get_robust_logger

logger = get_robust_logger().get_logger(__name__, "gui")

FORMAT_VERSION = 1
FILE_SUFFIX = ".ssa-estado.json"
DB_CHANGED_WARNING = (
    "Status: o banco mudou desde que o estado foi salvo;"
    " os resultados podem diferir do original."
)


def data_identity(window: Any, db_path: str) -> dict[str, Any]:
    try:
        mtime: float | None = os.path.getmtime(db_path)
    except OSError as exc:
        logger.warning("Falha ao ler mtime do banco %s: %s", db_path, exc)
        mtime = None
    return {
        "banco": os.path.basename(str(db_path or "")),
        "banco_mtime": mtime,
        "linhas": int(len(window.df_completo)),
    }


def _focused_ssa(window: Any) -> str | None:
    rows = window.table_widget.selectionModel().selectedRows()
    if rows:
        series = window._get_series_from_row(rows[0].row())
        if series is not None and str(series.get("numero_ssa") or "").strip():
            return str(series.get("numero_ssa")).strip()
    focused = str(getattr(window, "_details_current_ssa", None) or "").strip()
    return focused or None


def build_state_payload(window: Any, db_path: str) -> dict[str, Any]:
    # Mesmo encoder do "Salvar filtro": set/tuple/OrderedDict viram list/dict.
    filtros = json.loads(
        json.dumps(snapshot_filter_state(window), cls=PersistentFilterJSONEncoder)
    )
    return {
        "versao_formato": FORMAT_VERSION,
        "salvo_em": datetime.now().isoformat(timespec="seconds"),
        "versao_app": str(getattr(window, "_app_version", "")),
        "filtros": filtros,
        "ordenacao": {
            "coluna": getattr(window, "sort_column", None),
            "crescente": bool(getattr(window, "sort_ascending", True)),
        },
        "colunas": {
            "visiveis": [str(c) for c in window.visible_columns],
            "larguras": window._capture_current_column_widths(),
        },
        "pagina": int(getattr(window.paginator, "current_page", 1)),
        "ssa_em_foco": _focused_ssa(window),
        "dados": data_identity(window, db_path),
    }


def save_state_file(window: Any, path: str, db_path: str) -> str:
    if not path.endswith(FILE_SUFFIX):
        path = path.removesuffix(".json") + FILE_SUFFIX
    _write_private_json_file(path, build_state_payload(window, db_path))
    return path


def validate_payload(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise ValueError("Arquivo de estado invalido: conteudo nao e um objeto JSON.")
    version = payload.get("versao_formato")
    if type(version) is not int or version != FORMAT_VERSION:
        raise ValueError(
            f"Versao do arquivo de estado nao suportada ({version!r});"
            f" esperado {FORMAT_VERSION}. Nada foi aplicado."
        )
    for key in ("filtros", "ordenacao", "colunas", "dados"):
        if not isinstance(payload.get(key), dict):
            raise ValueError(f"Arquivo de estado invalido: secao '{key}' ausente.")
    # Arquivo vem do usuario: tipos errados recusam o arquivo inteiro antes de aplicar
    # qualquer parte (nada fica pela metade na tela).
    colunas, ordenacao = payload["colunas"], payload["ordenacao"]
    checks = (
        ("colunas.visiveis", colunas.get("visiveis"), (list, type(None))),
        ("colunas.larguras", colunas.get("larguras"), (dict, type(None))),
        ("ordenacao.crescente", ordenacao.get("crescente"), (bool, type(None))),
        ("pagina", payload.get("pagina"), (int, type(None))),
    )
    for name, value, types in checks:
        if not isinstance(value, types) or (name == "pagina" and isinstance(value, bool)):
            raise ValueError(f"Arquivo de estado invalido: '{name}' com tipo inesperado.")
    return payload


def load_state_file(path: str) -> dict[str, Any]:
    with open(path, encoding="utf-8") as handle:
        return validate_payload(json.load(handle))


def _apply_columns(window: Any, colunas: dict[str, Any], warnings: list[str]) -> None:
    known = set(window.df_completo.columns)
    known.update(getattr(getattr(window, "column_selector", None), "available_columns", []) or [])
    saved = [str(c) for c in colunas.get("visiveis") or []]
    visible = [c for c in saved if c in known]
    if len(visible) != len(saved):
        missing = ", ".join(c for c in saved if c not in known)
        warnings.append(f"Colunas ausentes ignoradas: {missing}.")
    if visible and visible != list(window.visible_columns):
        window.on_columns_changed(visible)


def _apply_sort_indicator(window: Any) -> None:
    header = window.table_widget.horizontalHeader()
    columns = list(getattr(window, "_current_display_columns", []) or [])
    if window.sort_column not in columns:
        header.setSortIndicatorShown(False)
        return
    order = Qt.SortOrder.AscendingOrder if window.sort_ascending else Qt.SortOrder.DescendingOrder
    header.setSortIndicatorShown(True)
    header.setSortIndicator(columns.index(window.sort_column), order)


def _filter_in_flight(window: Any) -> bool:
    thread = getattr(window, "filter_thread", None)
    return bool(thread is not None and hasattr(thread, "isRunning") and thread.isRunning())


def apply_state_payload(window: Any, payload: Any, db_path: str) -> list[str]:
    """Aplica o espelho validado; devolve avisos para a barra de status."""
    payload = validate_payload(payload)
    if window.df_completo.empty:
        raise ValueError("Nenhum dado carregado; aguarde a carga antes de abrir o estado.")
    warnings: list[str] = []
    _apply_columns(window, payload["colunas"], warnings)

    # Ordenacao antes dos filtros: o refresh dos filtros reaplica sort_column.
    sort_column = payload["ordenacao"].get("coluna")
    if sort_column is not None and sort_column not in window.df_completo.columns:
        warnings.append(f"Coluna de ordenacao ausente ignorada: {sort_column}.")
        sort_column = None
    window.sort_column = sort_column
    window.sort_ascending = bool(payload["ordenacao"].get("crescente", True))

    undo_state = snapshot_filter_state(window)
    restore_last_filter_state(
        window, copy_filter_mapping(payload["filtros"]), consume_undo=False
    )
    # Como no "Salvar filtro": Desfazer volta ao estado anterior a abertura.
    window._last_filter_state = undo_state
    window._update_undo_button_state()
    _apply_sort_indicator(window)

    focused = str(payload.get("ssa_em_foco") or "").strip()
    if _filter_in_flight(window):
        # ponytail: com busca assincrona so a SSA em foco e reposta (mecanismo do salto);
        # pagina e larguras sem SSA em foco ficam como o filtro renderizar.
        if focused:
            window._pending_jump_to_ssa = {
                "numero_ssa": focused,
                "request_id": getattr(window, "_active_filter_request_id", None),
            }
    else:
        paginator = window.paginator
        page = max(1, min(int(payload.get("pagina") or 1), int(paginator.total_pages)))
        paginator.current_page = page
        window.display_current_page(page, update_details=False)
        window._restore_column_widths(payload["colunas"].get("larguras") or {})
        if focused:
            window._jump_to_ssa(focused, _allow_refilter=False)

    if payload["dados"] != data_identity(window, db_path):
        warnings.append(DB_CHANGED_WARNING)
    return warnings
