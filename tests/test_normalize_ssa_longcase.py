# tests/test_normalize_ssa_longcase.py
"""Teste dedicado para o caso longo de normalização de numero_ssa.

Motivação: garantir comportamento estável para strings >9 dígitos iniciando com '2025'
conforme expectativa legada (ex.: '2025123456789' -> '512345678').

Se este comportamento mudar no futuro, ajuste tanto o teste paramétrico em
`test_normalize_ssa.py` quanto esta âncora dedicada.
"""
from interface import table_printer as tp


def test_long_prefixed_value_trims_expected():  # noqa: D103
    original = '2025123456789'
    expected = '512345678'
    assert tp._normalize_ssa(original) == expected


def test_long_prefixed_value_idempotent():  # noqa: D103
    v = '2025123456789'
    norm = tp._normalize_ssa(v)
    assert tp._normalize_ssa(norm) == norm  # segunda aplicação não altera
