import logging
import sqlite3

import pandas as pd
import pytest

from armazenamento import database_upsert_logic as upsert_logic


def _create_test_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE ssa_table (
            numero_ssa TEXT PRIMARY KEY,
            descricao_ssa TEXT,
            data_cadastro TEXT,
            semana_programada INTEGER
        )
        """
    )


def test_perform_upsert_uses_fast_path_for_unique_ssa_on_empty_target(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    conn = sqlite3.connect(":memory:")
    _create_test_table(conn)
    incoming = pd.DataFrame(
        [
            {"numero_ssa": "1001", "descricao_ssa": "SSA A", "data_cadastro": "2026-01-01 00:00:00", "semana_programada": 202601},
            {"numero_ssa": "1002", "descricao_ssa": "SSA B", "data_cadastro": "2026-01-02 00:00:00", "semana_programada": 202602},
        ]
    )

    def _unexpected_persist(*args, **kwargs) -> None:
        raise AssertionError("_persist_upsert_chunk nao deveria ser chamado no fast path")

    monkeypatch.setattr(upsert_logic, "_persist_upsert_chunk", _unexpected_persist)

    with caplog.at_level(logging.INFO):
        processed = upsert_logic._perform_upsert(incoming, "ssa_table", conn, chunk_size=100)

    rows = conn.execute(
        "SELECT numero_ssa, descricao_ssa, data_cadastro, semana_programada, typeof(semana_programada) FROM ssa_table ORDER BY numero_ssa"
    ).fetchall()
    assert processed == 2
    assert rows == [
        ("1001", "SSA A", "2026-01-01 00:00:00", 202601, "integer"),
        ("1002", "SSA B", "2026-01-02 00:00:00", 202602, "integer"),
    ]
    assert "Fast-path append de 2 registros com numero_ssa unicos e ausentes no banco" in caplog.text


def test_perform_upsert_falls_back_when_chunk_has_duplicate_numero_ssa(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    conn = sqlite3.connect(":memory:")
    _create_test_table(conn)
    incoming = pd.DataFrame(
        [
            {"numero_ssa": "1001", "descricao_ssa": "SSA A", "data_cadastro": "2026-01-01 00:00:00", "semana_programada": 202601},
            {"numero_ssa": "1001", "descricao_ssa": "SSA A v2", "data_cadastro": "2026-01-02 00:00:00", "semana_programada": 202602},
        ]
    )

    called = False
    original = upsert_logic._persist_upsert_chunk

    def _wrapped_persist(*args, **kwargs) -> None:
        nonlocal called
        called = True
        return original(*args, **kwargs)

    monkeypatch.setattr(upsert_logic, "_persist_upsert_chunk", _wrapped_persist)

    with caplog.at_level(logging.INFO):
        processed = upsert_logic._perform_upsert(incoming, "ssa_table", conn, chunk_size=100)

    row = conn.execute(
        "SELECT numero_ssa, descricao_ssa, data_cadastro, semana_programada, typeof(semana_programada) FROM ssa_table"
    ).fetchone()
    assert called is True
    assert processed == 2
    assert row == ("1001", "SSA A v2", "2026-01-02 00:00:00", 202602, "integer")
    assert "Fast-path append" not in caplog.text


def test_perform_upsert_falls_back_when_target_has_existing_ssa(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    conn = sqlite3.connect(":memory:")
    _create_test_table(conn)
    conn.execute(
        "INSERT INTO ssa_table (numero_ssa, descricao_ssa, data_cadastro, semana_programada) VALUES (?, ?, ?, ?)",
        ("1001", "SSA antiga", "2026-01-01 00:00:00", 202601),
    )
    conn.commit()
    incoming = pd.DataFrame(
        [
            {"numero_ssa": "1001", "descricao_ssa": "SSA nova", "data_cadastro": "2026-01-02 00:00:00", "semana_programada": 202602},
        ]
    )

    called = False
    original = upsert_logic._persist_upsert_chunk

    def _wrapped_persist(*args, **kwargs) -> None:
        nonlocal called
        called = True
        return original(*args, **kwargs)

    monkeypatch.setattr(upsert_logic, "_persist_upsert_chunk", _wrapped_persist)

    with caplog.at_level(logging.INFO):
        processed = upsert_logic._perform_upsert(incoming, "ssa_table", conn, chunk_size=100)

    row = conn.execute(
        "SELECT numero_ssa, descricao_ssa, data_cadastro, semana_programada, typeof(semana_programada) FROM ssa_table"
    ).fetchone()
    assert called is True
    assert processed == 1
    assert row == ("1001", "SSA nova", "2026-01-02 00:00:00", 202602, "integer")
    assert "Fast-path append" not in caplog.text


def test_insert_dataframe_with_smart_upsert_impl_keeps_mixed_transaction_flow() -> None:
    conn = sqlite3.connect(":memory:")
    conn.execute(
        """
        CREATE TABLE ssa_table (
            numero_ssa TEXT,
            descricao_ssa TEXT,
            data_cadastro TEXT,
            semana_programada INTEGER
        )
        """
    )
    incoming = pd.DataFrame(
        [
            {"numero_ssa": None, "descricao_ssa": "sem identidade", "data_cadastro": "2026-01-01 00:00:00", "semana_programada": 202601},
            {"numero_ssa": "202600001", "descricao_ssa": "com identidade", "data_cadastro": "2026-01-02 00:00:00", "semana_programada": 202602},
        ]
    )

    assert upsert_logic.insert_dataframe_with_smart_upsert_impl(incoming, conn, "ssa_table") is True

    rows = conn.execute(
        "SELECT numero_ssa, descricao_ssa, data_cadastro, semana_programada, typeof(semana_programada) "
        "FROM ssa_table ORDER BY descricao_ssa"
    ).fetchall()
    assert rows == [
        ("202600001", "com identidade", "2026-01-02 00:00:00", 202602, "integer"),
        (None, "sem identidade", "2026-01-01 00:00:00", 202601, "integer"),
    ]


def test_perform_upsert_fast_path_handles_multiple_chunks_in_same_transaction() -> None:
    conn = sqlite3.connect(":memory:")
    _create_test_table(conn)
    conn.execute("BEGIN")
    incoming = pd.DataFrame(
        [
            {
                "numero_ssa": str(1000 + idx),
                "descricao_ssa": f"SSA {idx}",
                "data_cadastro": "2026-01-01 00:00:00",
                "semana_programada": 202601 + idx,
            }
            for idx in range(105)
        ]
    )

    processed = upsert_logic._perform_upsert(incoming, "ssa_table", conn, chunk_size=50)
    conn.commit()

    count = conn.execute("SELECT COUNT(*) FROM ssa_table").fetchone()[0]
    blob_count = conn.execute(
        "SELECT COUNT(*) FROM ssa_table WHERE typeof(semana_programada)='blob'"
    ).fetchone()[0]
    assert processed == 105
    assert count == 105
    assert blob_count == 0


def test_insert_dataframe_with_smart_upsert_impl_skips_upsert_when_only_null_rows_exist(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    conn = sqlite3.connect(":memory:")
    _create_test_table(conn)
    incoming = pd.DataFrame(
        [
            {
                "numero_ssa": None,
                "descricao_ssa": "sem identidade",
                "data_cadastro": "2026-01-01 00:00:00",
                "semana_programada": 202601,
            },
            {
                "numero_ssa": "202600010",
                "descricao_ssa": "SSA 10",
                "data_cadastro": "2026-01-02 00:00:00",
                "semana_programada": 202602,
            },
            {
                "numero_ssa": "202600011",
                "descricao_ssa": "SSA 11",
                "data_cadastro": "2026-01-03 00:00:00",
                "semana_programada": 202603,
            },
        ]
    )

    def _unexpected_upsert(*args, **kwargs) -> int:
        raise AssertionError("_perform_upsert nao deveria ser chamado quando a tabela so tem numero_ssa nulo")

    monkeypatch.setattr(upsert_logic, "_perform_upsert", _unexpected_upsert)

    assert upsert_logic.insert_dataframe_with_smart_upsert_impl(incoming, conn, "ssa_table") is True

    rows = conn.execute(
        "SELECT numero_ssa, descricao_ssa FROM ssa_table ORDER BY descricao_ssa"
    ).fetchall()
    assert rows == [
        ("202600010", "SSA 10"),
        ("202600011", "SSA 11"),
        (None, "sem identidade"),
    ]


def test_quote_identifier_rejects_invalid_name() -> None:
    with pytest.raises(ValueError):
        upsert_logic._quote_identifier("ssa-table")


@pytest.mark.parametrize(
    ("row_count", "expected_chunk_size"),
    [
        (1000, 100),
        (1001, 250),
        (5000, 250),
        (5001, 250),
    ],
)
def test_resolve_upsert_chunk_size_uses_safe_buckets(row_count: int, expected_chunk_size: int) -> None:
    assert upsert_logic._resolve_upsert_chunk_size(row_count) == expected_chunk_size


def test_prepare_upsert_target_row_skips_identical_existing_row() -> None:
    existing = pd.Series(
        {
            "numero_ssa": "202500001",
            "descricao_ssa": "SSA identica",
            "data_cadastro": "2025-01-01 10:00:00",
            "semana_programada": 202501,
        }
    )
    incoming = existing.copy()
    status_rank, description_columns, date_columns = upsert_logic._resolve_upsert_config()

    target, should_persist = upsert_logic._prepare_upsert_target_row(
        incoming,
        existing,
        False,
        status_rank,
        description_columns,
        date_columns,
    )

    assert should_persist is False
    assert target.equals(existing)


def test_prepare_upsert_target_row_skips_older_incoming_row() -> None:
    existing = pd.Series(
        {
            "numero_ssa": "202500001",
            "descricao_ssa": "SSA nova",
            "data_cadastro": "2025-01-02 10:00:00",
            "semana_programada": 202502,
        }
    )
    incoming = pd.Series(
        {
            "numero_ssa": "202500001",
            "descricao_ssa": "SSA antiga",
            "data_cadastro": "2025-01-01 10:00:00",
            "semana_programada": 202501,
        }
    )
    status_rank, description_columns, date_columns = upsert_logic._resolve_upsert_config()

    target, should_persist = upsert_logic._prepare_upsert_target_row(
        incoming,
        existing,
        False,
        status_rank,
        description_columns,
        date_columns,
    )

    assert should_persist is False
    assert target.equals(existing)
