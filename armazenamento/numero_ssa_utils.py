"""Nomes de normalizacao de numero_ssa usados pela camada de armazenamento.

Todos delegam a ``shared.numero_ssa.normalize_strict`` (regra unica): valor
invalido vira None e e logado, sem prefixo de ano.

API publica:
 - normalize_numero_ssa_strict(value) -> str | None
 - normalize_numero_ssa_storage(value) -> str | None (caminho de gravacao)
 - normalize_numero_ssa(value) -> str | None (exibicao, utils.formatting)
"""

from __future__ import annotations

from shared.numero_ssa import normalize_strict as _strict

NUMERO_SSA_LEN = 9

__all__ = [
    "normalize_numero_ssa_strict",
    "normalize_numero_ssa_storage",
    "normalize_numero_ssa",
]


def normalize_numero_ssa_strict(value) -> str | None:
    """Wrapper explicito para clareza sem expor ``_strict`` direto fora do modulo."""
    return _strict(value)


def normalize_numero_ssa_storage(value) -> str | None:
    """Return canonical storage form for numero_ssa as text."""
    return normalize_numero_ssa_strict(value)


def normalize_numero_ssa(value) -> str | None:
    """Compat wrapper alinhado ao mesmo contrato canonico de storage."""
    return normalize_numero_ssa_strict(value)
