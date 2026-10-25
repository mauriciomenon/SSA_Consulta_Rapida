"""Aplicacao das variaveis SSA_* do runtime empacotado (CF-06).

Usado por launchers/main_runtime.py (PyOxidizer) e launchers/runtime_entry_helpers.py
(Nuitka/PyInstaller). Fica em shared/ porque o PyOxidizer so empacota
launchers.main_runtime da pasta launchers/.
"""

from __future__ import annotations

import os
from collections.abc import Mapping


def _same_path(left: str, right: str) -> bool:
    """Mesmo destino apos resolver symlinks (BL-28: /var x /private/var no macOS)."""
    return os.path.normcase(os.path.realpath(left)) == os.path.normcase(
        os.path.realpath(right)
    )


def apply_runtime_env(values: Mapping[str, str]) -> list[str]:
    """Define `values` no ambiente e devolve um aviso por valor do usuario descartado.

    O log fica com quem chama (utils.robust_logging.log_warnings): shared/ nao importa
    utils (BL-44), e o logger robusto so pode iniciar depois de SSA_RUNTIME_ROOT definido.

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
    return discarded
