"""Leitura unica de flags booleanas de ambiente (CF-13)."""

from __future__ import annotations

import os

TRUTHY_ENV_VALUES = frozenset({"1", "true", "yes", "on"})


def env_truthy(name: str) -> bool:
    """True so para 1/true/yes/on (sem diferenciar maiusculas); vazio, 0, false etc. = False."""
    return str(os.environ.get(name, "")).strip().casefold() in TRUTHY_ENV_VALUES


def non_interactive_env() -> bool:
    """SSA_NON_INTERACTIVE ligada: sem prompts (CLI, paginacao, confirmacoes da GUI)."""
    return env_truthy("SSA_NON_INTERACTIVE")


FALSY_ENV_VALUES = frozenset({"0", "false", "no", "off"})


def env_flag(name: str, *, default: bool) -> bool:
    """Flag com default: vazio/ausente = default; 1/true/yes/on = True; 0/false/no/off = False."""
    value = str(os.environ.get(name, "")).strip().casefold()
    if value in TRUTHY_ENV_VALUES:
        return True
    if value in FALSY_ENV_VALUES:
        return False
    return default
