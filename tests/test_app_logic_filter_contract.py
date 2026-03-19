from __future__ import annotations

import sqlite3
from pathlib import Path

import pandas as pd

from core.app_logic import filter_dataframe, get_filtered_data


def test_filter_dataframe_preserves_group_or_for_preparsed_terms() -> None:
    df = pd.DataFrame(
        {
            "descricao_ssa": [
                "motor mel4",
                "bomba iee3",
                "valvula geral",
            ]
        }
    )

    terms = [
        {"mode": "contains", "value": "mel4", "negative": False, "group": 0},
        {"mode": "contains", "value": "iee3", "negative": False, "group": 1},
    ]

    out = filter_dataframe(df, terms, ["descricao_ssa"])

    assert len(out) == 2
    assert set(out["descricao_ssa"]) == {"motor mel4", "bomba iee3"}


def test_filter_dataframe_raw_term_modes_match_any_searchable_field() -> None:
    df = pd.DataFrame(
        {
            "numero_ssa": ["202500001", "202500002", "202500003"],
            "descricao_ssa": ["admin area", "motor mel4", "fechado 2025"],
        }
    )

    out_prefix = filter_dataframe(df, ["^admin"], ["numero_ssa", "descricao_ssa"])
    out_exact = filter_dataframe(df, ["=motor mel4"], ["numero_ssa", "descricao_ssa"])
    out_suffix = filter_dataframe(df, ["2025$"], ["numero_ssa", "descricao_ssa"])

    assert set(out_prefix["numero_ssa"]) == {"202500001"}
    assert set(out_exact["numero_ssa"]) == {"202500002"}
    assert set(out_suffix["numero_ssa"]) == {"202500003"}


def test_get_filtered_data_reads_canonical_table_without_legacy_view(tmp_path: Path) -> None:
    db_path = tmp_path / "ssa_canonica.sqlite"
    conn = sqlite3.connect(db_path)
    conn.execute(
        """
        CREATE TABLE ssa_table (
            numero_ssa TEXT,
            situacao TEXT,
            descricao_ssa TEXT
        )
        """
    )
    conn.execute(
        "INSERT INTO ssa_table (numero_ssa, situacao, descricao_ssa) VALUES (?, ?, ?)",
        ("202500001", "STE", "SSA canonica"),
    )
    conn.commit()
    conn.close()

    out = get_filtered_data(str(db_path))

    assert len(out) == 1
    assert out.iloc[0]["numero_ssa"] == "202500001"
    assert out.iloc[0]["descricao_ssa"] == "SSA canonica"


def test_filter_dataframe_default_search_columns_match_solicitante_and_setor_executor() -> None:
    df = pd.DataFrame(
        {
            "numero_ssa": ["202500001", "202500002"],
            "solicitante": ["danilo", "maria"],
            "setor_executor": ["MEL4", "MEL3"],
        }
    )

    out = filter_dataframe(df, ["danilo", "mel4"])

    assert list(out["numero_ssa"]) == ["202500001"]


def test_filter_dataframe_default_search_columns_match_responsavel_execucao_and_setor_executor() -> None:
    df = pd.DataFrame(
        {
            "numero_ssa": ["202500001", "202500002"],
            "responsavel_execucao": ["danilo", "maria"],
            "setor_executor": ["MEL4", "MEL3"],
        }
    )

    out = filter_dataframe(df, ["danilo", "mel4"])

    assert list(out["numero_ssa"]) == ["202500001"]


def test_filter_dataframe_default_search_columns_require_terms_in_same_row() -> None:
    df = pd.DataFrame(
        {
            "numero_ssa": ["202500001", "202500002"],
            "solicitante": ["danilo", "maria"],
            "setor_executor": ["MEL3", "MEL4"],
        }
    )

    out = filter_dataframe(df, ["danilo", "mel4"])

    assert out.empty


def test_filter_dataframe_default_search_columns_allow_terms_in_different_columns_same_row() -> None:
    df = pd.DataFrame(
        {
            "numero_ssa": ["202500001", "202500002"],
            "solicitante": ["danilo", "maria"],
            "responsavel_execucao": ["carlos", "joao"],
            "setor_executor": ["MEL4", "MEL3"],
        }
    )

    out = filter_dataframe(df, ["danilo", "mel4"])

    assert list(out["numero_ssa"]) == ["202500001"]
