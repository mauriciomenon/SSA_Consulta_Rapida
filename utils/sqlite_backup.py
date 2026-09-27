"""Backup SQLite com prazo total, prazo sem progresso e cancelamento."""

from __future__ import annotations

import math
import sqlite3
import time
from collections.abc import Callable

_SQLITE_DONE = 101


def _progress_checker(
    timeout: float,
    stall_timeout: float,
    cancel_check: Callable[[], bool] | None,
    now: Callable[[], float] = time.monotonic,
) -> Callable[[int, int, int], None]:
    """Callback de backup que aborta por teto total ou falta de progresso.

    Progresso so conta quando `remaining` bate um novo minimo: a API de
    backup do SQLite reinicia a copia do zero se a origem for escrita,
    devolvendo `remaining` ao total. Renovar o prazo por qualquer queda
    permitiria livelock de restarts consecutivos.
    """
    total_deadline = now() + timeout
    stall_deadline = now() + stall_timeout
    minimum = math.inf

    def check_progress(status: int, remaining: int, _total: int) -> None:
        nonlocal stall_deadline, minimum
        if cancel_check is not None and cancel_check():
            raise InterruptedError("Backup SQLite cancelado")
        current = now()
        if current >= total_deadline:
            raise TimeoutError("Prazo total do backup SQLite esgotado")
        if status == _SQLITE_DONE:
            # Copia terminada nao pode estar parada: DONE dispensa stall,
            # mas cancelamento e teto total ja foram fiscalizados acima.
            return
        if current >= stall_deadline:
            raise TimeoutError("Backup SQLite sem progresso")
        if remaining < minimum:
            minimum = remaining
            stall_deadline = current + stall_timeout

    return check_progress


def bounded_sqlite_backup(
    source: sqlite3.Connection,
    target: sqlite3.Connection,
    *,
    timeout: float = 120.0,
    stall_timeout: float = 10.0,
    cancel_check: Callable[[], bool] | None = None,
    pages: int = 128,
) -> None:
    """Copia `source` para `target` com busy_timeout zerado durante a copia.

    `timeout` e o teto total da copia; `stall_timeout` aborta quando o
    backup para de avancar (origem travada por outro escritor). Progresso
    conta apenas por novo minimo de paginas restantes: reinicios da copia
    por escritas na origem nao renovam o prazo de stall. `pages` e o lote
    por passo, limitado a 128; valor nao positivo usa o default. O
    busy_timeout original das duas conexoes e restaurado ao final.
    """
    for name, value in (("timeout", timeout), ("stall_timeout", stall_timeout)):
        if not math.isfinite(value) or value <= 0:
            raise ValueError(f"{name} do backup SQLite invalido: {value!r}")
    if cancel_check is not None and cancel_check():
        raise InterruptedError("Backup SQLite cancelado")
    check_progress = _progress_checker(timeout, stall_timeout, cancel_check)
    busy_timeout = int(source.execute("PRAGMA busy_timeout").fetchone()[0])
    target_timeout = int(target.execute("PRAGMA busy_timeout").fetchone()[0])
    source.execute("PRAGMA busy_timeout=0")
    try:
        target.execute("PRAGMA busy_timeout=0")
        source.backup(
            target,
            pages=min(pages, 128) if pages > 0 else 128,
            progress=check_progress,
            sleep=0.01,
        )
    finally:
        source.execute(f"PRAGMA busy_timeout={busy_timeout}")  # nosec B608  # nosemgrep
        target.execute(f"PRAGMA busy_timeout={target_timeout}")  # nosec B608  # nosemgrep
