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


class _FailingCursor:
    def executemany(self, _sql, _rows):
        raise RuntimeError("forced executemany failure")


class _TrackingConn:
    def __init__(self, *, in_transaction: bool):
        self.in_transaction = in_transaction
        self.rollback_calls = 0
        self._cursor = _FailingCursor()

    def cursor(self):
        return self._cursor

    def rollback(self):
        self.rollback_calls += 1


def test_append_dataframe_rows_does_not_rollback_when_chunk_insert_fails() -> None:
    conn = _TrackingConn(in_transaction=True)
    frame = pd.DataFrame([{"numero_ssa": "202600001", "situacao": "ADM"}])

    with pytest.raises(RuntimeError, match="forced executemany failure"):
        upsert_logic._append_dataframe_rows(conn, "ssa_table", frame)

    assert conn.rollback_calls == 0


def test_append_dataframe_rows_does_not_rollback_without_active_transaction() -> None:
    conn = _TrackingConn(in_transaction=False)
    frame = pd.DataFrame([{"numero_ssa": "202600001", "situacao": "ADM"}])

    with pytest.raises(RuntimeError, match="forced executemany failure"):
        upsert_logic._append_dataframe_rows(conn, "ssa_table", frame)

    assert conn.rollback_calls == 0


def test_perform_upsert_uses_fast_path_for_unique_ssa_on_empty_target(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    conn = sqlite3.connect(":memory:")
    _create_test_table(conn)
    incoming = pd.DataFrame(
        [
            {
                "numero_ssa": "1001",
                "descricao_ssa": "SSA A",
                "data_cadastro": "2026-01-01 00:00:00",
                "semana_programada": 202601,
            },
            {
                "numero_ssa": "1002",
                "descricao_ssa": "SSA B",
                "data_cadastro": "2026-01-02 00:00:00",
                "semana_programada": 202602,
            },
        ]
    )

    def _unexpected_persist(*args, **kwargs) -> None:
        raise AssertionError(
            "_persist_upsert_chunk nao deveria ser chamado no fast path"
        )

    monkeypatch.setattr(upsert_logic, "_persist_upsert_chunk", _unexpected_persist)

    with caplog.at_level(logging.INFO):
        processed = upsert_logic._perform_upsert(
            incoming, "ssa_table", conn, chunk_size=100
        )

    rows = conn.execute(
        "SELECT numero_ssa, descricao_ssa, data_cadastro, semana_programada, typeof(semana_programada) FROM ssa_table ORDER BY numero_ssa"
    ).fetchall()
    assert processed == 2
    assert rows == [
        ("1001", "SSA A", "2026-01-01 00:00:00", 202601, "integer"),
        ("1002", "SSA B", "2026-01-02 00:00:00", 202602, "integer"),
    ]
    assert (
        "Fast-path append de 2 registros com numero_ssa unicos e ausentes no banco"
        in caplog.text
    )


def test_perform_upsert_falls_back_when_chunk_has_duplicate_numero_ssa(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    conn = sqlite3.connect(":memory:")
    _create_test_table(conn)
    incoming = pd.DataFrame(
        [
            {
                "numero_ssa": "1001",
                "descricao_ssa": "SSA A",
                "data_cadastro": "2026-01-01 00:00:00",
                "semana_programada": 202601,
            },
            {
                "numero_ssa": "1001",
                "descricao_ssa": "SSA A v2",
                "data_cadastro": "2026-01-02 00:00:00",
                "semana_programada": 202602,
            },
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
        processed = upsert_logic._perform_upsert(
            incoming, "ssa_table", conn, chunk_size=100
        )

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
            {
                "numero_ssa": "1001",
                "descricao_ssa": "SSA nova",
                "data_cadastro": "2026-01-02 00:00:00",
                "semana_programada": 202602,
            },
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
        processed = upsert_logic._perform_upsert(
            incoming, "ssa_table", conn, chunk_size=100
        )

    row = conn.execute(
        "SELECT numero_ssa, descricao_ssa, data_cadastro, semana_programada, typeof(semana_programada) FROM ssa_table"
    ).fetchone()
    assert called is True
    assert processed == 1
    assert row == ("1001", "SSA nova", "2026-01-02 00:00:00", 202602, "integer")
    assert "Fast-path append" not in caplog.text


def test_perform_upsert_non_short_policy_uses_lazy_existing_cache(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    conn = sqlite3.connect(":memory:")
    _create_test_table(conn)
    conn.execute("ALTER TABLE ssa_table ADD COLUMN arquivo_origem TEXT")
    conn.execute(
        "INSERT INTO ssa_table (numero_ssa, descricao_ssa, data_cadastro, semana_programada, arquivo_origem) VALUES (?, ?, ?, ?, ?)",
        (
            "1001",
            "SSA antiga",
            "2026-01-01 00:00:00",
            202601,
            "Todas as SSAs - 18-08-2022_1144AM.xlsx",
        ),
    )
    conn.commit()
    incoming = pd.DataFrame(
        [
            {
                "numero_ssa": "1001",
                "descricao_ssa": "SSA nova",
                "data_cadastro": "2026-01-02 00:00:00",
                "semana_programada": 202602,
                "arquivo_origem": "Todas as SSAs - 18-08-2022_1144AM.xlsx",
            }
        ]
    )

    def _unexpected_eager_cache(*args, **kwargs) -> dict[str, pd.Series]:
        raise AssertionError(
            "_build_existing_series_cache nao deve ser chamado no ramo lazy"
        )

    monkeypatch.setattr(
        upsert_logic, "_build_existing_series_cache", _unexpected_eager_cache
    )

    processed = upsert_logic._perform_upsert(
        incoming, "ssa_table", conn, chunk_size=100
    )

    row = conn.execute(
        "SELECT numero_ssa, descricao_ssa, data_cadastro, semana_programada, arquivo_origem FROM ssa_table"
    ).fetchone()
    assert processed == 1
    assert row == (
        "1001",
        "SSA nova",
        "2026-01-02 00:00:00",
        202602,
        "Todas as SSAs - 18-08-2022_1144AM.xlsx",
    )


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
            {
                "numero_ssa": None,
                "descricao_ssa": "sem identidade",
                "data_cadastro": "2026-01-01 00:00:00",
                "semana_programada": 202601,
            },
            {
                "numero_ssa": "202600001",
                "descricao_ssa": "com identidade",
                "data_cadastro": "2026-01-02 00:00:00",
                "semana_programada": 202602,
            },
        ]
    )

    assert (
        upsert_logic.insert_dataframe_with_smart_upsert_impl(
            incoming, conn, "ssa_table"
        )
        is True
    )

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
    assert bool(conn.in_transaction) is True
    conn.commit()

    count = conn.execute("SELECT COUNT(*) FROM ssa_table").fetchone()[0]
    blob_count = conn.execute(
        "SELECT COUNT(*) FROM ssa_table WHERE typeof(semana_programada)='blob'"
    ).fetchone()[0]
    assert processed == 105
    assert count == 105
    assert blob_count == 0


def test_insert_dataframe_with_smart_upsert_impl_rolls_back_if_upsert_phase_fails(
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
                "numero_ssa": "202600999",
                "descricao_ssa": "com identidade",
                "data_cadastro": "2026-01-02 00:00:00",
                "semana_programada": 202602,
            },
        ]
    )

    def _raise_upsert(*_args, **_kwargs):
        raise RuntimeError("forced upsert failure")

    monkeypatch.setattr(upsert_logic, "_perform_upsert", _raise_upsert)

    with pytest.raises(RuntimeError, match="forced upsert failure"):
        upsert_logic.insert_dataframe_with_smart_upsert_impl(
            incoming, conn, "ssa_table"
        )

    persisted_count = conn.execute("SELECT COUNT(*) FROM ssa_table").fetchone()[0]
    assert persisted_count == 0


def test_insert_dataframe_with_smart_upsert_impl_preserves_enter_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from armazenamento import database as database_module

    class BrokenConnectionManager:
        exit_calls = 0

        def __enter__(self):
            raise RuntimeError("forced enter failure")

        def __exit__(self, *_args):
            self.exit_calls += 1

    conn_cm = BrokenConnectionManager()
    incoming = pd.DataFrame(
        [
            {
                "numero_ssa": "202600999",
                "descricao_ssa": "com identidade",
                "data_cadastro": "2026-01-02 00:00:00",
                "semana_programada": 202602,
            }
        ]
    )

    monkeypatch.setattr(
        database_module,
        "get_db_connection",
        lambda _db_path: conn_cm,
    )

    with pytest.raises(RuntimeError, match="forced enter failure"):
        upsert_logic.insert_dataframe_with_smart_upsert_impl(
            incoming,
            "/tmp/not-opened.db",
            "ssa_table",
        )

    assert conn_cm.exit_calls == 0


def test_insert_dataframe_with_smart_upsert_impl_persists_no_ssa_and_has_ssa_rows() -> (
    None
):
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

    assert (
        upsert_logic.insert_dataframe_with_smart_upsert_impl(
            incoming, conn, "ssa_table"
        )
        is True
    )

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
def test_resolve_upsert_chunk_size_uses_safe_buckets(
    row_count: int, expected_chunk_size: int
) -> None:
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
    status_rank, description_columns, date_columns = (
        upsert_logic._resolve_upsert_config()
    )

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
    status_rank, description_columns, date_columns = (
        upsert_logic._resolve_upsert_config()
    )

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


def test_perform_upsert_skips_exact_overlap_without_persist(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    conn = sqlite3.connect(":memory:")
    _create_test_table(conn)
    conn.execute("ALTER TABLE ssa_table ADD COLUMN arquivo_origem TEXT")
    conn.execute(
        "INSERT INTO ssa_table (numero_ssa, descricao_ssa, data_cadastro, semana_programada, arquivo_origem) VALUES (?, ?, ?, ?, ?)",
        (
            "1001",
            "SSA identica",
            "2025-01-01 10:00:00",
            202501,
            "Consulta SSA - 02-03-2026_0540PM.xlsx",
        ),
    )
    conn.commit()
    incoming = pd.DataFrame(
        [
            {
                "numero_ssa": "1001",
                "descricao_ssa": "SSA identica",
                "data_cadastro": "2025-01-01 10:00:00",
                "semana_programada": 202501,
                "arquivo_origem": "Consulta SSA - 02-03-2026_0540PM.xlsx",
            }
        ]
    )

    def _unexpected_persist(*args, **kwargs) -> None:
        raise AssertionError(
            "_persist_upsert_chunk nao deveria ser chamado para overlap identico"
        )

    monkeypatch.setattr(upsert_logic, "_persist_upsert_chunk", _unexpected_persist)

    processed = upsert_logic._perform_upsert(
        incoming, "ssa_table", conn, chunk_size=100
    )

    row = conn.execute(
        "SELECT numero_ssa, descricao_ssa, data_cadastro, semana_programada, arquivo_origem FROM ssa_table"
    ).fetchone()
    assert processed == 0
    assert row == (
        "1001",
        "SSA identica",
        "2025-01-01 10:00:00",
        202501,
        "Consulta SSA - 02-03-2026_0540PM.xlsx",
    )


def test_perform_upsert_skips_exact_overlap_with_pd_na_without_persist(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    conn = sqlite3.connect(":memory:")
    _create_test_table(conn)
    conn.execute("ALTER TABLE ssa_table ADD COLUMN arquivo_origem TEXT")
    conn.execute(
        "INSERT INTO ssa_table (numero_ssa, descricao_ssa, data_cadastro, semana_programada, arquivo_origem) VALUES (?, ?, ?, ?, ?)",
        (
            "1002",
            "SSA com nulo",
            "2025-01-01 10:00:00",
            None,
            "Consulta SSA - 02-03-2026_0540PM.xlsx",
        ),
    )
    conn.commit()
    incoming = pd.DataFrame(
        [
            {
                "numero_ssa": "1002",
                "descricao_ssa": "SSA com nulo",
                "data_cadastro": "2025-01-01 10:00:00",
                "semana_programada": pd.NA,
                "arquivo_origem": "Consulta SSA - 02-03-2026_0540PM.xlsx",
            }
        ]
    )

    def _unexpected_persist(*args, **kwargs) -> None:
        raise AssertionError(
            "_persist_upsert_chunk nao deveria ser chamado para overlap identico com nulo"
        )

    monkeypatch.setattr(upsert_logic, "_persist_upsert_chunk", _unexpected_persist)

    processed = upsert_logic._perform_upsert(
        incoming, "ssa_table", conn, chunk_size=100
    )

    row = conn.execute(
        "SELECT numero_ssa, descricao_ssa, data_cadastro, semana_programada, arquivo_origem FROM ssa_table"
    ).fetchone()
    assert processed == 0
    assert row == (
        "1002",
        "SSA com nulo",
        "2025-01-01 10:00:00",
        None,
        "Consulta SSA - 02-03-2026_0540PM.xlsx",
    )


def test_should_enable_exact_overlap_short_circuit_only_for_consulta_ssa() -> None:
    consulta_chunk = pd.DataFrame(
        [{"numero_ssa": "1", "arquivo_origem": "Consulta SSA - 02-03-2026_0540PM.xlsx"}]
    )
    todas_chunk = pd.DataFrame(
        [
            {
                "numero_ssa": "1",
                "arquivo_origem": "Todas as SSAs - 18-08-2022_1144AM.xlsx",
            }
        ]
    )
    mixed_chunk = pd.DataFrame(
        [
            {
                "numero_ssa": "1",
                "arquivo_origem": "Consulta SSA - 02-03-2026_0540PM.xlsx",
            },
            {
                "numero_ssa": "2",
                "arquivo_origem": "Consulta SSA - 03-03-2026_0540PM.xlsx",
            },
        ]
    )

    assert (
        upsert_logic._should_enable_exact_overlap_short_circuit(consulta_chunk) is True
    )
    assert upsert_logic._should_enable_exact_overlap_short_circuit(todas_chunk) is False
    assert upsert_logic._should_enable_exact_overlap_short_circuit(mixed_chunk) is False


def test_resolve_short_circuit_policy_defaults_to_consulta_only() -> None:
    assert upsert_logic._resolve_short_circuit_policy() == "consulta_only"


def test_should_enable_exact_overlap_short_circuit_with_no_short_policy() -> None:
    todas_chunk = pd.DataFrame(
        [
            {
                "numero_ssa": "1",
                "arquivo_origem": "Todas as SSAs - 18-08-2022_1144AM.xlsx",
            }
        ]
    )
    assert (
        upsert_logic._should_enable_exact_overlap_short_circuit(
            todas_chunk,
            policy="no_short",
        )
        is False
    )
    assert upsert_logic._resolve_short_circuit_policy("no_short") == "no_short"


def test_should_enable_exact_overlap_short_circuit_with_all_short_policy() -> None:
    all_short_chunk = pd.DataFrame(
        [
            {
                "numero_ssa": "1",
                "arquivo_origem": "Todas as SSAs - 18-08-2022_1144AM.xlsx",
            }
        ]
    )
    assert (
        upsert_logic._should_enable_exact_overlap_short_circuit(
            all_short_chunk,
            policy="all_short",
        )
        is True
    )
    assert upsert_logic._resolve_short_circuit_policy("all_short") == "all_short"


def test_short_circuit_policy_modes_are_disjoint() -> None:
    consulta_chunk = pd.DataFrame(
        [{"numero_ssa": "1", "arquivo_origem": "Consulta SSA - 02-03-2026_0540PM.xlsx"}]
    )
    todas_chunk = pd.DataFrame(
        [
            {
                "numero_ssa": "1",
                "arquivo_origem": "Todas as SSAs - 18-08-2022_1144AM.xlsx",
            }
        ]
    )
    mixed_chunk = pd.DataFrame(
        [
            {
                "numero_ssa": "1",
                "arquivo_origem": "Todas as SSAs - 18-08-2022_1144AM.xlsx",
            },
            {
                "numero_ssa": "2",
                "arquivo_origem": "Todas as SSAs - 19-08-2022_1032PM.xlsx",
            },
        ]
    )

    assert (
        upsert_logic._should_enable_exact_overlap_short_circuit(
            consulta_chunk,
            policy="consulta_only",
        )
        is True
    )
    assert (
        upsert_logic._should_enable_exact_overlap_short_circuit(
            consulta_chunk,
            policy="no_short",
        )
        is False
    )
    assert (
        upsert_logic._should_enable_exact_overlap_short_circuit(
            consulta_chunk,
            policy="all_short",
        )
        is True
    )

    assert (
        upsert_logic._should_enable_exact_overlap_short_circuit(
            todas_chunk,
            policy="consulta_only",
        )
        is False
    )
    assert (
        upsert_logic._should_enable_exact_overlap_short_circuit(
            todas_chunk,
            policy="no_short",
        )
        is False
    )
    assert (
        upsert_logic._should_enable_exact_overlap_short_circuit(
            todas_chunk,
            policy="all_short",
        )
        is True
    )

    assert (
        upsert_logic._should_enable_exact_overlap_short_circuit(
            mixed_chunk,
            policy="all_short",
        )
        is False
    )


def test_resolve_short_circuit_policy_invalid_falls_back_to_consulta_only() -> None:
    assert upsert_logic._resolve_short_circuit_policy("invalida") == "consulta_only"
