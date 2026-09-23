"""Persisted row parity for sequential duplicate and complementary imports."""

import sqlite3

import pandas as pd
import pytest

from armazenamento.database_optimized import insert_dataframe_optimized
from armazenamento.database_upsert_logic import insert_dataframe_with_smart_upsert_impl


@pytest.mark.parametrize("complementary", [False, True])
@pytest.mark.parametrize("seeded", [False, True])
@pytest.mark.parametrize("reverse", [False, True])
@pytest.mark.parametrize("terminal", [False, True])
@pytest.mark.parametrize("unique", [False, True])
def test_optimized_matches_canonical_persisted_rows(
    tmp_path, monkeypatch, complementary, seeded, reverse, terminal, unique
):
    monkeypatch.setenv("SSA_ENABLE_COMPLEMENTARY", "1" if complementary else "0")
    frame = pd.DataFrame({
        "numero_ssa": ["202600001", "202600001"],
        "situacao": ["STE" if terminal else "ADM", "ADM"],
        "data_cadastro": ["2026-01-01", "2026-01-02"],
        "descricao_ssa": ["preservar", ""],
        "data_planilha": ["2026-02-01", "2026-02-02"],
    })
    if reverse:
        frame = frame.iloc[::-1]
    if unique:
        frame = frame.iloc[:1]
    else:
        frame.index = [7, 7]
    results = []
    for name, insert in (
        ("canonical", insert_dataframe_with_smart_upsert_impl),
        ("optimized", insert_dataframe_optimized),
    ):
        path = str(tmp_path / f"{name}.db")
        with sqlite3.connect(path) as conn:
            conn.execute("CREATE TABLE ssa_table (numero_ssa TEXT PRIMARY KEY, "
                         "situacao TEXT, data_cadastro TEXT, descricao_ssa TEXT, "
                         "data_planilha TEXT)")
            if seeded:
                conn.execute("INSERT INTO ssa_table VALUES "
                             "('202600001', 'STE', '2025-01-01', 'original', '2025-02-01')")
        assert insert(frame.copy(), path, "ssa_table")
        with sqlite3.connect(path) as conn:
            results.append(conn.execute("SELECT * FROM ssa_table").fetchall())
    assert results[1] == results[0]
    assert len(results[0]) == 1
    if not reverse:
        assert results[0][0][3]


@pytest.mark.parametrize("column", ["ate", "desde_2", "data_programacao"])
def test_optimized_normalizes_all_canonical_date_columns(tmp_path, column):
    results = []
    for name, insert in (
        ("canonical", insert_dataframe_with_smart_upsert_impl),
        ("optimized", insert_dataframe_optimized),
    ):
        path = str(tmp_path / f"{name}.db")
        with sqlite3.connect(path) as conn:
            conn.execute(f'CREATE TABLE ssa_table (numero_ssa TEXT PRIMARY KEY, '
                         f'situacao TEXT, data_cadastro TEXT, "{column}" TEXT)')
        frame = pd.DataFrame({"numero_ssa": ["202600001"], "situacao": ["ADM"],
                              "data_cadastro": ["2026-01-01"], column: ["05/01/2026"]})
        assert insert(frame, path, "ssa_table")
        with sqlite3.connect(path) as conn:
            results.append(conn.execute(f'SELECT "{column}" FROM ssa_table').fetchone())
    assert results[0] == ("2026-01-05 00:00:00",)
    assert results[1] == results[0]


def test_optimized_rolls_back_new_column_when_insert_constraint_fails(tmp_path):
    path = str(tmp_path / "rollback_schema.db")
    with sqlite3.connect(path) as conn:
        conn.execute("CREATE TABLE ssa_table (numero_ssa TEXT PRIMARY KEY, "
                     "situacao TEXT CHECK(situacao != 'FAIL'), data_cadastro TEXT)")
    frame = pd.DataFrame({"numero_ssa": ["202600001"], "situacao": ["FAIL"],
                          "data_cadastro": ["2026-01-01"], "new_column": ["value"]})
    assert insert_dataframe_optimized(frame, path, "ssa_table") is False
    with sqlite3.connect(path) as conn:
        assert [row[1] for row in conn.execute("PRAGMA table_info(ssa_table)")] == [
            "numero_ssa", "situacao", "data_cadastro"
        ]
        assert conn.execute("SELECT COUNT(*) FROM ssa_table").fetchone() == (0,)


def test_optimized_mixed_dates_match_canonical_for_all_date_columns(tmp_path):
    from armazenamento.database_upsert_logic import UPSERT_DATE_COLUMNS

    values = [None, pd.NA, float("nan"), "", "invalid", "05/01/2026", "2026-01-06",
              46029, 46029.5, pd.Timestamp("2026-01-08"), -1, 0, True, False, 1, 999999]
    frame = pd.DataFrame({"numero_ssa": [str(202600001 + i) for i in range(len(values))],
                          "situacao": ["ADM"] * len(values)})
    for column in UPSERT_DATE_COLUMNS:
        frame[column] = values
    results = []
    for name, insert in (
        ("canonical", insert_dataframe_with_smart_upsert_impl),
        ("optimized", insert_dataframe_optimized),
    ):
        path = str(tmp_path / f"{name}.db")
        with sqlite3.connect(path) as conn:
            columns = ", ".join(f'"{column}" TEXT' for column in UPSERT_DATE_COLUMNS)
            conn.execute(f"CREATE TABLE ssa_table (numero_ssa TEXT PRIMARY KEY, situacao TEXT, {columns})")
        assert insert(frame.copy(), path, "ssa_table")
        with sqlite3.connect(path) as conn:
            results.append(conn.execute("SELECT * FROM ssa_table ORDER BY numero_ssa").fetchall())
    assert results[1] == results[0]
