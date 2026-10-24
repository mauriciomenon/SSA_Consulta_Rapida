"""Regras de numero_ssa nos nomes usados pela camada de armazenamento (A-30).

normalize_numero_ssa_storage e o caminho de gravacao (upsert, validacao, modo
otimizado); normalize_numero_ssa e o de exibicao (utils.formatting). Os
wrappers de DataFrame e o helper numerico legado sairam por nao ter chamador.
"""

import logging

import pytest

from armazenamento.numero_ssa_utils import (
    normalize_numero_ssa,
    normalize_numero_ssa_storage,
)


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        (None, None),
        (" ", None),
        ("ABC123", None),
        ("abc123", None),
        ("12345678", None),
        ("2025123456", None),
        (float("nan"), None),
        ("123", None),
        ("202501234", "202501234"),
        ("202600654", "202600654"),
        ("202500777.0", "202500777"),
    ],
)
def test_storage_normalization_cases(raw, expected):
    assert normalize_numero_ssa_storage(raw) == expected


def test_storage_normalization_logs_overlong_rejection(caplog) -> None:
    caplog.set_level(logging.WARNING)

    assert normalize_numero_ssa_storage("2025123456") is None

    assert "exceder 9 digitos" in caplog.text


def test_normalize_numero_ssa_basic():
    # entradas curtas nao viram numero_ssa valido por exibicao
    assert normalize_numero_ssa("123") is None
    assert normalize_numero_ssa("0009876") is None
    assert normalize_numero_ssa("2601234") is None
    # ja com 9 digitos mantem
    assert normalize_numero_ssa("202500045") == "202500045"
    # caso atual de export com 9 digitos permanece canonico
    assert normalize_numero_ssa("202600654") == "202600654"
    # 10 digitos nao sao referencia do contrato operacional atual
    assert normalize_numero_ssa("2026000654") is None
    # >9 nao trunca
    assert normalize_numero_ssa("202512345678") is None
    # vazios/nulos retornam None
    assert normalize_numero_ssa("") is None
    assert normalize_numero_ssa(None) is None


def test_normalize_numero_ssa_display_logs_overlong_rejection(caplog) -> None:
    caplog.set_level(logging.WARNING)

    assert normalize_numero_ssa("202512345678") is None

    assert "exceder 9 digitos" in caplog.text


def test_dead_numero_ssa_aliases_removed():
    """A-30: sem wrappers de DataFrame nem helper numerico legado."""
    from armazenamento import database, numero_ssa_utils

    for name in (
        "_normalize_numero_ssa_value",
        "normalize_numero_ssa",
        "normalize_numero_ssa_dataframe",
        "normalize_numero_ssa_dataframe_storage",
    ):
        assert not hasattr(database, name), name
    for name in (
        "normalize_numero_ssa_int_legacy_bridge",
        "batch_normalize_series",
        "extract_candidate_digits",
        "bulk_int_or_none",
        "normalize_numero_ssa_dataframe",
        "normalize_numero_ssa_dataframe_storage",
    ):
        assert not hasattr(numero_ssa_utils, name), name
