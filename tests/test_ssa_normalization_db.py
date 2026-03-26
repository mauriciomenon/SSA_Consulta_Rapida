# ruff: noqa: E402
from datetime import datetime

import pandas as pd

from armazenamento.database import (
    _normalize_numero_ssa_value,
    normalize_numero_ssa_dataframe,
)


def test_normalize_numero_ssa_value_various():
    assert _normalize_numero_ssa_value(None) is None
    assert _normalize_numero_ssa_value(" ") is None
    # Apenas SSAs válidos (YYYY + 5) entre 1980-2050 retornam int
    assert _normalize_numero_ssa_value("ABC123") is None
    # 8 dígitos é inválido
    assert _normalize_numero_ssa_value("12345678") is None
    # 10+ dígitos: usa primeiros 9; se ano válido, aceita
    assert _normalize_numero_ssa_value("2025123456") == 202512345


def test_normalize_numero_ssa_dataframe_apply():
    df = pd.DataFrame({"numero_ssa": [None, "abc123", "12345678", "202501234"]})
    out = normalize_numero_ssa_dataframe(df)
    assert list(out["numero_ssa"]) == [None, None, None, "202501234"]


def test_normalize_numero_ssa_dataframe_preserves_index_alignment():
    df = pd.DataFrame(
        {"numero_ssa": ["202501234", "202512345"]},
        index=[10, 20],
    )
    out = normalize_numero_ssa_dataframe(df)
    assert list(out.index) == [10, 20]
    assert out.loc[10, "numero_ssa"] == "202501234"
    assert out.loc[20, "numero_ssa"] == "202512345"


# tests/test_ssa_normalization_db.py
import os
import sys

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, project_root)

from armazenamento.database import normalize_numero_ssa


def test_normalize_numero_ssa_basic():
    current_year = datetime.now().year
    # <=5 digitos: prefixa ano corrente e preenche para 5
    assert normalize_numero_ssa("123") == f"{current_year}00123"
    # 7 digitos com zeros a esquerda: apos remover zeros fica com 4 -> prefixa ano corrente
    assert normalize_numero_ssa("0009876") == f"{current_year}09876"
    # 7 digitos com ano em 2 digitos aceitam 26+
    assert normalize_numero_ssa("2601234") == "202601234"
    # ja com 9 digitos mantem
    assert normalize_numero_ssa("202500045") == "202500045"
    # >9 nao trunca mais no helper legacy
    assert normalize_numero_ssa("202512345678") is None
    # vazios/nulos retornam None
    assert normalize_numero_ssa("") is None
    assert normalize_numero_ssa(None) is None
