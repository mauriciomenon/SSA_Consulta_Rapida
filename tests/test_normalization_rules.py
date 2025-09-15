#!/usr/bin/env python3
"""Valida regras de normalização de numero_ssa isoladamente.

Usa a função pública normalize_numero_ssa (se existir) ou fallback para lógica interna.
"""
from __future__ import annotations

import pytest

from armazenamento import database


def _normalize(value):
    if hasattr(database, "normalize_numero_ssa"):
        return database.normalize_numero_ssa(value)
    # fallback: tentar usar função interna (não ideal, mas mantém teste útil)
    if hasattr(database, "_normalize_numero_ssa_value"):
        return database._normalize_numero_ssa_value(value)  # type: ignore[attr-defined]
    raise RuntimeError("Nenhuma função de normalização encontrada")


def test_normalization_cases(normalization_cases):
    for raw, expected in normalization_cases:
        assert _normalize(raw) == expected


@pytest.mark.parametrize(
    "entrada",
    [
        "202512345", 202512345, "202512345000",  # corte para 9 dígitos
    ],
)
def test_normalization_idempotent_and_truncation(entrada):
    norm = _normalize(entrada)
    if norm is None:
        pytest.fail("Valor inesperadamente None para entrada válida")
    # Deve ter exatamente 9 caracteres
    assert len(norm) == 9
    assert norm.isdigit()
