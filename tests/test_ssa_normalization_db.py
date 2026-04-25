# ruff: noqa: E402
import logging

import pandas as pd

from armazenamento.database import (
    _normalize_numero_ssa_value,
    normalize_numero_ssa_dataframe,
    normalize_numero_ssa_dataframe_storage,
)


def test_normalize_numero_ssa_value_various():
    assert _normalize_numero_ssa_value(None) is None
    assert _normalize_numero_ssa_value(" ") is None
    # Apenas SSAs válidos (YYYY + 5) entre 1980-2050 retornam int
    assert _normalize_numero_ssa_value("ABC123") is None
    # 8 dígitos é inválido
    assert _normalize_numero_ssa_value("12345678") is None
    # 10+ digitos: helper numerico legado nao aceita mais sobrecomprimento
    assert _normalize_numero_ssa_value("2025123456") is None


def test_normalize_numero_ssa_value_logs_overlong_rejection(caplog) -> None:
    caplog.set_level(logging.WARNING)

    assert _normalize_numero_ssa_value("2025123456") is None

    assert "exceder 9 digitos" in caplog.text


def test_normalize_numero_ssa_dataframe_apply():
    df = pd.DataFrame(
        {
            "numero_ssa": [
                None,
                "abc123",
                "12345678",
                "202501234",
                "202600654",
            ]
        }
    )
    out = normalize_numero_ssa_dataframe(df)
    assert list(out["numero_ssa"]) == [
        None,
        None,
        None,
        "202501234",
        "202600654",
    ]


def test_normalize_numero_ssa_dataframe_storage_matches_compat_alias() -> None:
    df = pd.DataFrame({"numero_ssa": ["202500777.0", "abc123", None]})

    canonical = normalize_numero_ssa_dataframe_storage(df)
    compat = normalize_numero_ssa_dataframe(df)

    assert canonical.to_dict("list") == compat.to_dict("list")


def test_normalize_numero_ssa_dataframe_storage_preserves_null_cells() -> None:
    df = pd.DataFrame(
        {
            "numero_ssa": [
                None,
                float("nan"),
                "abc123",
                "202501234",
            ]
        }
    )

    out = normalize_numero_ssa_dataframe_storage(df)

    assert out.loc[0, "numero_ssa"] is None
    assert out.loc[1, "numero_ssa"] is None
    assert out.loc[2, "numero_ssa"] is None
    assert out.loc[3, "numero_ssa"] == "202501234"
    assert "nan" not in {
        str(value).lower() for value in out["numero_ssa"] if value is not None
    }


def test_normalize_numero_ssa_dataframe_rejects_short_display_only_values() -> None:
    df = pd.DataFrame(
        {
            "numero_ssa": [
                "123",
                "202500777.0",
            ]
        }
    )

    out = normalize_numero_ssa_dataframe(df)

    assert list(out["numero_ssa"]) == [
        None,
        "202500777",
    ]


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
    # entradas curtas nao viram mais numero_ssa valido por exibicao
    assert normalize_numero_ssa("123") is None
    assert normalize_numero_ssa("0009876") is None
    assert normalize_numero_ssa("2601234") is None
    # ja com 9 digitos mantem
    assert normalize_numero_ssa("202500045") == "202500045"
    # caso atual de export com 9 digitos permanece canonico
    assert normalize_numero_ssa("202600654") == "202600654"
    # 10 digitos nao sao referencia do contrato operacional atual
    assert normalize_numero_ssa("2026000654") is None
    # >9 nao trunca mais no helper legacy
    assert normalize_numero_ssa("202512345678") is None
    # vazios/nulos retornam None
    assert normalize_numero_ssa("") is None
    assert normalize_numero_ssa(None) is None


def test_normalize_numero_ssa_display_logs_overlong_rejection(caplog) -> None:
    caplog.set_level(logging.WARNING)

    assert normalize_numero_ssa("202512345678") is None

    assert "exceder 9 digitos" in caplog.text
