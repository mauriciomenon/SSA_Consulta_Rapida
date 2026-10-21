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


@pytest.mark.parametrize("complementary", ["0", "1"])
def test_parse_block_metric_matches_canonical_and_optimized(
    tmp_path, monkeypatch, complementary
):
    monkeypatch.setenv("SSA_ENABLE_COMPLEMENTARY", complementary)
    incoming = pd.DataFrame(
        [
            {
                "numero_ssa": "202600001",
                "situacao": "ADM",
                "data_cadastro": "2026-03-02",
                "data_planilha": None,
                "arquivo_origem": "arquivo_sem_data.xlsx",
                "descricao_ssa": "bloqueada",
            },
            {
                "numero_ssa": "202600002",
                "situacao": "ADM",
                "data_cadastro": "2026-03-02",
                "data_planilha": "2026-03-02",
                "arquivo_origem": "",
                "descricao_ssa": "atualizada",
            },
        ]
    )
    for name, insert in (
        ("canonical", insert_dataframe_with_smart_upsert_impl),
        ("optimized", insert_dataframe_optimized),
    ):
        path = str(tmp_path / f"metric_{name}.db")
        with sqlite3.connect(path) as conn:
            conn.execute(
                "CREATE TABLE ssa_table (numero_ssa TEXT PRIMARY KEY, situacao TEXT, "
                "data_cadastro TEXT, data_planilha TEXT, arquivo_origem TEXT, "
                "descricao_ssa TEXT)"
            )
            conn.executemany(
                "INSERT INTO ssa_table VALUES (?, 'ADM', '2026-03-01', "
                "'2026-03-01', '', 'original')",
                [("202600001",), ("202600002",)],
            )
        metrics: dict[str, int] = {}
        assert insert(incoming.copy(), path, "ssa_table", metrics_out=metrics)
        if complementary == "1":
            expected_metrics = {"ssa_inserted": 0, "ssa_updated": 2, "ssa_verified": 0}
            expected_rows = [("original",), ("original",)]
        else:
            expected_metrics = {
                "ssa_inserted": 0,
                "ssa_updated": 1,
                "ssa_verified": 0,
                "ssa_blocked_parse": 1,
            }
            expected_rows = [("original",), ("atualizada",)]
        if name == "canonical":
            expected_metrics["ssa_event_records_processed"] = 0
        assert metrics == expected_metrics
        with sqlite3.connect(path) as conn:
            assert (
                conn.execute(
                    "SELECT descricao_ssa FROM ssa_table ORDER BY numero_ssa"
                ).fetchall()
                == expected_rows
            )


_SNAPSHOT_TABLE_DDL = (
    "CREATE TABLE ssa_table (numero_ssa TEXT PRIMARY KEY, situacao TEXT, "
    "data_cadastro TEXT, descricao_ssa TEXT, semana_programada INTEGER, "
    "arquivo_origem TEXT, data_arquivo_origem TEXT, data_planilha TEXT)"
)
_SNAPSHOT_BUSINESS_ROWS = [
    ("202600001", "ADM", "2026-01-01 00:00:00", "bomba", 202601),
    ("202600002", "AAD", "2026-01-02 00:00:00", "valvula", 202602),
    ("202600003", "ADM", "2026-01-03 08:00:00", "motor", 202603),
]
_FIRST_SOURCE = ("SSAs_01-02-2026.xlsx", "2026-02-01T00:00:00")
_SECOND_SOURCE = ("SSAs_02-02-2026.xlsx", "2026-02-02T00:00:00")


def _snapshot_frame(source: tuple[str, str], **overrides) -> pd.DataFrame:
    arquivo, data_planilha = source
    frame = pd.DataFrame(
        _SNAPSHOT_BUSINESS_ROWS,
        columns=[
            "numero_ssa", "situacao", "data_cadastro", "descricao_ssa",
            "semana_programada",
        ],
    )
    frame["arquivo_origem"] = arquivo
    frame["data_arquivo_origem"] = data_planilha
    frame["data_planilha"] = data_planilha
    for column, values in overrides.items():
        frame[column] = values
    return frame


@pytest.mark.parametrize(
    ("second_source", "overrides", "business_rows", "expected_counts"),
    [
        # X-01: so a metadata de origem muda (tipos variam sem mudar o valor).
        (
            _SECOND_SOURCE,
            {
                "semana_programada": ["202601", 202602.0, "202603"],
                "data_cadastro": ["01/01/2026", "2026-01-02", "2026-01-03 08:00:00"],
            },
            _SNAPSHOT_BUSINESS_ROWS,
            (0, 0, 3),
        ),
        # Mudanca real de situacao/descricao conta como atualizada.
        (
            _SECOND_SOURCE,
            {
                "situacao": ["AAD", "AAD", "ADM"],
                "descricao_ssa": ["bomba", "valvula trocada", "motor"],
            },
            [
                ("202600001", "AAD", "2026-01-01 00:00:00", "bomba", 202601),
                ("202600002", "AAD", "2026-01-02 00:00:00", "valvula trocada", 202602),
                _SNAPSHOT_BUSINESS_ROWS[2],
            ],
            (0, 2, 1),
        ),
        # Reimportacao identica: nem atualizada nem verificada.
        (_FIRST_SOURCE, {}, _SNAPSHOT_BUSINESS_ROWS, (0, 0, 0)),
    ],
    ids=["metadata_only", "business_change", "identical"],
)
def test_reimport_separates_verified_from_updated_in_both_paths(
    tmp_path, monkeypatch, second_source, overrides, business_rows, expected_counts
):
    monkeypatch.setenv("SSA_ENABLE_COMPLEMENTARY", "0")
    expected_rows = [
        (*row, second_source[0], second_source[1], second_source[1])
        for row in business_rows
    ]
    results = {}
    for name, insert in (
        ("canonical", insert_dataframe_with_smart_upsert_impl),
        ("optimized", insert_dataframe_optimized),
    ):
        path = str(tmp_path / f"{name}.db")
        with sqlite3.connect(path) as conn:
            conn.execute(_SNAPSHOT_TABLE_DDL)
        assert insert(_snapshot_frame(_FIRST_SOURCE), path, "ssa_table")
        metrics: dict[str, int] = {}
        assert insert(
            _snapshot_frame(second_source, **overrides),
            path,
            "ssa_table",
            metrics_out=metrics,
        )
        with sqlite3.connect(path) as conn:
            rows = conn.execute(
                "SELECT * FROM ssa_table ORDER BY numero_ssa"
            ).fetchall()
        # Banco grava o mesmo de antes (metadata de origem atualizada).
        assert rows == expected_rows, name
        results[name] = tuple(
            metrics.get(key) for key in ("ssa_inserted", "ssa_updated", "ssa_verified")
        )
    assert results["canonical"] == expected_counts
    assert results["optimized"] == results["canonical"]


def test_classify_existing_row_change_is_type_tolerant():
    from armazenamento.database_upsert_logic import _classify_existing_row_change

    existing = {
        "id": 1,
        "numero_ssa": "202600001",
        "situacao": "ADM",
        "descricao_ssa": "bomba",
        "semana_programada": 202601,
        "data_cadastro": "2026-01-01 00:00:00",
        "executado": None,
        "observacoes": "",
        "arquivo_origem": "a.xlsx",
        "data_criacao_arquivo": "2026-01-01",
    }
    same_values = {
        **existing,
        "id": 9,
        "situacao": " ADM ",
        "descricao_ssa": "bomba",
        "semana_programada": "202601.0",
        "data_cadastro": pd.Timestamp("2026-01-01"),
        "executado": float("nan"),
        "observacoes": pd.NaT,
    }
    assert _classify_existing_row_change(existing, same_values) is None
    assert _classify_existing_row_change(existing, pd.Series(same_values)) is None
    assert (
        _classify_existing_row_change(
            existing, {**same_values, "data_criacao_arquivo": "2026-01-02"}
        )
        == "verified"
    )
    assert (
        _classify_existing_row_change(
            existing, {**same_values, "arquivo_origem": "b.xlsx", "situacao": "AAD"}
        )
        == "updated"
    )
    assert (
        _classify_existing_row_change(existing, {**same_values, "nova_coluna": "x"})
        == "updated"
    )


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


def test_optimized_import_keeps_default_journal_mode(tmp_path):
    path = str(tmp_path / "journal.db")
    with sqlite3.connect(path) as conn:
        conn.execute("CREATE TABLE ssa_table (numero_ssa TEXT PRIMARY KEY, "
                     "situacao TEXT, data_cadastro TEXT)")
    frame = pd.DataFrame({"numero_ssa": ["202600001"], "situacao": ["ADM"],
                          "data_cadastro": ["2026-01-01"]})

    assert insert_dataframe_optimized(frame, path, "ssa_table")

    with sqlite3.connect(path) as conn:
        assert conn.execute("PRAGMA journal_mode").fetchone()[0] == "delete"


def test_optimized_sanitizes_dynamic_column_like_canonical(tmp_path):
    frame = pd.DataFrame({
        "numero_ssa": ["202600001"],
        "situacao": ["ADM"],
        "data_cadastro": ["2026-01-01"],
        "Categoría": ["valor"],
    })
    results = []
    for name, insert in (
        ("canonical", insert_dataframe_with_smart_upsert_impl),
        ("optimized", insert_dataframe_optimized),
    ):
        path = str(tmp_path / f"{name}.db")
        with sqlite3.connect(path) as conn:
            conn.execute("CREATE TABLE ssa_table (numero_ssa TEXT PRIMARY KEY, "
                         "situacao TEXT, data_cadastro TEXT)")
        assert insert(frame.copy(), path, "ssa_table")
        with sqlite3.connect(path) as conn:
            columns = [row[1] for row in conn.execute("PRAGMA table_info(ssa_table)")]
            results.append((columns, conn.execute("SELECT * FROM ssa_table").fetchall()))
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
