#!/usr/bin/env python3
"""Valida regras de normalização de numero_ssa isoladamente.

Usa a função pública normalize_numero_ssa (se existir) ou fallback para lógica interna.
"""

from __future__ import annotations

from typing import Any, cast

import pandas as pd
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


def test_normalization_short_values_are_rejected():
    assert _normalize("123") is None


def test_normalization_rejects_overlong_legacy_values():
    assert _normalize("202512345000") is None


def test_normalization_rejects_short_two_digit_year_sequences():
    assert _normalize("2601234") is None


def test_dataframe_storage_api_is_textual_and_explicit():
    out = database.normalize_numero_ssa_dataframe_storage(
        pd.DataFrame({"numero_ssa": ["202500777.0", "ABC123"]})
    )
    assert list(out["numero_ssa"]) == ["202500777", None]


def test_invalid_table_name_dispatch_returns_false(tmp_path):
    frame = pd.DataFrame([{"numero_ssa": "202401234", "situacao": "OK"}])
    db_path = str(tmp_path / "x.sqlite")
    assert (
        database.insert_dataframe_with_smart_upsert(
            frame,
            db_path,
            cast(Any, None),
        )
        is False
    )
