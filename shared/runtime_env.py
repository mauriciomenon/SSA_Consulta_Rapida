"""Aplicacao das variaveis SSA_* do runtime empacotado (CF-06).

Usado por launchers/main_runtime.py (PyOxidizer) e launchers/runtime_entry_helpers.py
(Nuitka/PyInstaller). Fica em shared/ porque o PyOxidizer so empacota
launchers.main_runtime da pasta launchers/.
"""

from __future__ import annotations

import os
import sys
from collections.abc import Mapping


def _same_path(left: str, right: str) -> bool:
    """Mesmo destino apos resolver symlinks (BL-28: /var x /private/var no macOS)."""
    return os.path.normcase(os.path.realpath(left)) == os.path.normcase(
        os.path.realpath(right)
    )


def apply_runtime_env(values: Mapping[str, str], *, logger_name: str) -> list[str]:
    """Define `values` no ambiente e avisa no log cada valor do usuario descartado.

    Retorna as mensagens de aviso (vazia quando nada foi sobrescrito).
    """
    discarded = [
        f"{name} definido pelo usuario ({previous}) ignorado no app empacotado; usando {value}"
        for name, value in values.items()
        if (previous := os.environ.get(name, "").strip())
        and not _same_path(previous, value)
    ]
    for name, value in values.items():
        os.environ[name] = value
    for message in discarded:
        try:
            from utils.robust_logging import get_robust_logger

            get_robust_logger().get_logger("ssa.launcher", logger_name).warning(message)
        except Exception as exc:
            sys.stderr.write(f"AVISO: {message} (logger indisponivel: {exc})\n")
    return discarded
