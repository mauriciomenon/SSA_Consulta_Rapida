"""Copias da janela principal com o estado da tela congelado (dados ja carregados).

Uma copia recebe os dados em memoria e os filtros da janela de origem: permite ordenar,
reorganizar, filtrar sobre esses dados e abrir detalhes (leitura do banco), mas nao
recarrega do banco nem roda importacao, SAM API ou sincronizacao de derivadas. A janela
principal continua sendo a unica que opera o banco.
"""

from __future__ import annotations

from typing import Any, Callable

MAX_WINDOW_COPIES = 3

_open_copies: list[Any] = []


def open_window_copy(source: Any, window_factory: Callable[..., Any]) -> Any | None:
    """Abre uma copia de `source`; devolve None quando ja ha MAX_WINDOW_COPIES abertas."""
    if len(_open_copies) >= MAX_WINDOW_COPIES:
        return None
    copy_window = window_factory(copy_from=source, copy_number=_next_copy_number())
    _open_copies.append(copy_window)
    return copy_window


def forget_window_copy(copy_window: Any) -> None:
    """Chamado no fechamento de uma copia."""
    if copy_window in _open_copies:
        _open_copies.remove(copy_window)


def close_all_window_copies() -> None:
    """Fecha as copias (a janela principal, dona do banco, esta fechando)."""
    for copy_window in list(_open_copies):
        copy_window.close()
    _open_copies.clear()


def open_copy_count() -> int:
    return len(_open_copies)


def _next_copy_number() -> int:
    used = {getattr(window, "_window_copy_number", 0) for window in _open_copies}
    return next(n for n in range(1, MAX_WINDOW_COPIES + 1) if n not in used)
