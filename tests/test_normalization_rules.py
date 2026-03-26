#!/usr/bin/env python3
"""Valida regras de normalização de numero_ssa isoladamente.

Usa a função pública normalize_numero_ssa (se existir) ou fallback para lógica interna.
"""

from __future__ import annotations

from datetime import datetime

import pytest

from armazenamento import database


def _normalize(value):
    if hasattr(database, "normalize_numero_ssa"):
        return database.normalize_numero_ssa(value)
    # fallback: tentar usar função interna (não ideal, mas mantém teste útil)
    if hasattr(database, "_normalize_numero_ssa_value"):
        return database._normalize_numero_ssa_value(value)
    raise RuntimeError("Nenhuma função de normalização encontrada")


def test_normalization_cases(normalization_cases):
    for raw, expected in normalization_cases:
        assert _normalize(raw) == expected


@pytest.mark.parametrize(
    "entrada",
    [
        "202512345",
        202512345,
    ],
)
def test_normalization_idempotent_for_valid_values(entrada):
    norm = _normalize(entrada)
    if norm is None:
        pytest.fail("Valor inesperadamente None para entrada válida")
    # Deve ter exatamente 9 caracteres
    assert len(norm) == 9
    assert norm.isdigit()


def test_normalization_short_values_use_current_year_prefix():
    current_year = datetime.now().year
    assert _normalize("123") == f"{current_year}00123"


def test_normalization_rejects_overlong_legacy_values():
    assert _normalize("202512345000") is None


def test_normalization_accepts_two_digit_year_beyond_2025():
    assert _normalize("2601234") == "202601234"
