import os
from contextlib import contextmanager

import pandas as pd
import pytest

from armazenamento import database as database_module
from armazenamento.database import (
    ensure_indexes,
    get_db_connection,
    initialize_database,
    insert_dataframe_to_db,
    insert_dataframe_with_smart_upsert,
    reset_database,
)
from armazenamento.database_optimized import (
    disable_optimized_import,
    enable_optimized_import,
)
from shared.db_names import SSA_READ_REQUIRED_COLUMNS


def _make_schema(tmpdir):
    schema = os.path.join(tmpdir, "schema.sql")
    with open(schema, "w", encoding="utf-8") as f:
        f.write(
            """
            CREATE TABLE IF NOT EXISTS ssas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                numero_ssa INTEGER,
                situacao TEXT,
                data_cadastro TEXT,
                descricao_ssa TEXT,
                setor_executor TEXT
            );
            """
        )
    return schema


def _seed_canonical_parent_and_event(db_path):
    with get_db_connection(db_path, write=True) as conn:
        conn.execute(
            "INSERT INTO ssa_table (numero_ssa, situacao) VALUES (?, ?)",
            ("202401234", "OLD"),
        )
        conn.execute(
            "INSERT INTO ssa_event_records "
            "(numero_ssa, record_type, record_order, record_label, payload_json, "
            "arquivo_origem, source_sheet, source_row) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (
                "202401234",
                "deviation_records",
                2,
                "Deviation #2",
                '{"deviation_records":"Deviation #2"}',
                "snapshot.xlsx",
                "Sheet1",
                3,
            ),
        )
        conn.commit()


def test_reset_database_file_mode(tmp_path):
    db_path = os.path.join(tmp_path, "x.sqlite")
    with get_db_connection(db_path) as conn:
        conn.execute("CREATE TABLE T(x INTEGER);")
        conn.commit()
    assert os.path.exists(db_path)
    assert reset_database(db_path, mode="file") is True
    assert not os.path.exists(db_path)


def test_reset_database_table_mode(tmp_path):
    db_path = os.path.join(tmp_path, "x.sqlite")
    missing_schema = os.path.join(tmp_path, "missing.sql")
    assert not os.path.exists(db_path)
    assert reset_database(db_path, mode="table", schema_path=missing_schema) is False
    assert not os.path.exists(db_path)
    assert reset_database(db_path, mode="table") is True
    with get_db_connection(db_path) as conn:
        tables = {
            str(row[0])
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            ).fetchall()
        }
    assert {"ssa_table", "ssa_event_records"} <= tables


def test_reset_database_table_mode_clears_hierarchical_events(tmp_path):
    db_path = os.path.join(tmp_path, "x.sqlite")
    initialize_database(db_path)
    _seed_canonical_parent_and_event(db_path)

    assert reset_database(db_path, mode="table") is True

    with get_db_connection(db_path) as conn:
        parent_count = conn.execute("SELECT COUNT(*) FROM ssa_table").fetchone()[0]
        event_count = conn.execute(
            "SELECT COUNT(*) FROM ssa_event_records"
        ).fetchone()[0]
    assert (parent_count, event_count) == (0, 0)


def test_reset_database_table_mode_preserves_original_on_invalid_schema(tmp_path):
    db_path = os.path.join(tmp_path, "x.sqlite")
    invalid_schema = os.path.join(tmp_path, "invalid.sql")
    missing_schema = os.path.join(tmp_path, "missing.sql")
    missing_events_schema = os.path.join(tmp_path, "missing_events.sql")
    missing_target_schema = os.path.join(tmp_path, "missing_target.sql")
    truncated_target_schema = os.path.join(tmp_path, "truncated_target.sql")
    truncated_events_schema = os.path.join(tmp_path, "truncated_events.sql")
    missing_event_unique_schema = os.path.join(tmp_path, "missing_event_unique.sql")
    target_columns_sql = ", ".join(
        f'"{column}" TEXT' for column in SSA_READ_REQUIRED_COLUMNS
    )
    event_columns_sql = """
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        numero_ssa TEXT NOT NULL,
        record_type TEXT NOT NULL,
        record_order INTEGER NOT NULL,
        record_label TEXT NOT NULL,
        payload_json TEXT NOT NULL,
        arquivo_origem TEXT NOT NULL,
        data_planilha TEXT,
        data_arquivo_origem TEXT,
        source_sheet TEXT NOT NULL,
        source_row INTEGER NOT NULL
    """
    with open(invalid_schema, "w", encoding="utf-8") as f:
        f.write("THIS IS NOT VALID SQL;")
    with open(missing_events_schema, "w", encoding="utf-8") as f:
        f.write(f"CREATE TABLE ssa_table ({target_columns_sql});")
    with open(missing_target_schema, "w", encoding="utf-8") as f:
        f.write("CREATE TABLE unrelated (value TEXT);")
    with open(truncated_target_schema, "w", encoding="utf-8") as f:
        f.write(
            "CREATE TABLE ssa_table (numero_ssa TEXT);"
            f"CREATE TABLE ssa_event_records ({event_columns_sql}, "
            "UNIQUE (numero_ssa, record_type, record_order, payload_json));"
        )
    with open(truncated_events_schema, "w", encoding="utf-8") as f:
        f.write(
            f"CREATE TABLE ssa_table ({target_columns_sql});"
            "CREATE TABLE ssa_event_records (numero_ssa TEXT);"
        )
    with open(missing_event_unique_schema, "w", encoding="utf-8") as f:
        f.write(
            f"CREATE TABLE ssa_table ({target_columns_sql});"
            f"CREATE TABLE ssa_event_records ({event_columns_sql});"
        )
    initialize_database(db_path)
    _seed_canonical_parent_and_event(db_path)
    with open(db_path, "rb") as f:
        original_bytes = f.read()

    for schema_path in (
        invalid_schema,
        missing_schema,
        missing_events_schema,
        missing_target_schema,
        truncated_target_schema,
        truncated_events_schema,
        missing_event_unique_schema,
    ):
        assert reset_database(db_path, mode="table", schema_path=schema_path) is False
        with open(db_path, "rb") as f:
            assert f.read() == original_bytes
        with get_db_connection(db_path) as conn:
            parent_count = conn.execute("SELECT COUNT(*) FROM ssa_table").fetchone()[0]
            event_count = conn.execute(
                "SELECT COUNT(*) FROM ssa_event_records"
            ).fetchone()[0]
            quick_check = conn.execute("PRAGMA quick_check").fetchone()
        assert (parent_count, event_count, quick_check) == (1, 1, ("ok",))


@pytest.mark.parametrize("database_exists", [True, False])
def test_reset_database_table_mode_handles_promotion_failure(
    tmp_path,
    monkeypatch,
    database_exists,
):
    db_path = os.path.join(tmp_path, "x.sqlite")
    if database_exists:
        initialize_database(db_path)
        _seed_canonical_parent_and_event(db_path)
        with open(db_path, "rb") as f:
            original_bytes = f.read()
    original_get_db_connection = database_module.get_db_connection

    @contextmanager
    def fail_destination(path, *args, **kwargs):
        with original_get_db_connection(path, *args, **kwargs) as conn:
            if os.path.abspath(os.fspath(path)) == os.path.abspath(db_path) and kwargs.get(
                "write"
            ):
                conn.close()
            yield conn

    monkeypatch.setattr(
        database_module,
        "get_db_connection",
        fail_destination,
    )

    assert reset_database(db_path, mode="table") is False

    if database_exists:
        with open(db_path, "rb") as f:
            assert f.read() == original_bytes
        with original_get_db_connection(db_path) as conn:
            counts = (
                conn.execute("SELECT COUNT(*) FROM ssa_table").fetchone()[0],
                conn.execute("SELECT COUNT(*) FROM ssa_event_records").fetchone()[0],
                conn.execute("PRAGMA quick_check").fetchone(),
            )
        assert counts == (1, 1, ("ok",))
    else:
        assert not any(
            os.path.exists(path)
            for path in (db_path, f"{db_path}-wal", f"{db_path}-shm")
        )


def test_reset_database_custom_table_preserves_hierarchical_events(tmp_path):
    db_path = os.path.join(tmp_path, "x.sqlite")
    schema = os.path.join(tmp_path, "schema.sql")
    with open(schema, "w", encoding="utf-8") as f:
        f.write(
            """
            CREATE TABLE IF NOT EXISTS custom_records (numero_ssa TEXT);
            CREATE TABLE IF NOT EXISTS ssa_event_records (numero_ssa TEXT);
            """
        )
    initialize_database(db_path, schema)
    with get_db_connection(db_path, write=True) as conn:
        conn.execute("INSERT INTO custom_records VALUES ('202401234')")
        conn.execute("INSERT INTO ssa_event_records VALUES ('202401234')")
        conn.commit()

    assert (
        reset_database(
            db_path,
            mode="table",
            _table_name="custom_records",
            schema_path=schema,
        )
        is True
    )

    with get_db_connection(db_path) as conn:
        custom_count = conn.execute(
            "SELECT COUNT(*) FROM custom_records"
        ).fetchone()[0]
        event_count = conn.execute(
            "SELECT COUNT(*) FROM ssa_event_records"
        ).fetchone()[0]
    assert (custom_count, event_count) == (0, 1)


def test_reset_database_table_mode_uses_explicit_table_name(tmp_path):
    db_path = os.path.join(tmp_path, "x.sqlite")
    initialize_database(db_path)
    with get_db_connection(db_path) as conn:
        conn.execute(
            "INSERT INTO ssa_table (numero_ssa, situacao) VALUES (?, ?)",
            (202401234, "OLD"),
        )
        conn.commit()

    assert (
        reset_database(db_path, mode="table", _table_name="ssas") is True
    )

    with get_db_connection(db_path) as conn:
        row_count = conn.execute("SELECT COUNT(*) FROM ssa_table").fetchone()[0]
    assert row_count == 0


def test_ensure_indexes(tmp_path):
    db_path = os.path.join(tmp_path, "x.sqlite")
    schema = _make_schema(tmp_path)
    initialize_database(db_path, schema)
    assert ensure_indexes(db_path) is True


def test_insert_dataframe_with_smart_upsert(tmp_path):
    db_path = os.path.join(tmp_path, "x.sqlite")
    schema = _make_schema(tmp_path)
    initialize_database(db_path, schema)

    # Seed old row for a valid numero_ssa (YYYY + 5 dígitos) with earlier date
    old = pd.DataFrame(
        [
            {
                "numero_ssa": "202401234",
                "situacao": "OLD",
                "data_cadastro": "01/01/2025",
                "descricao_ssa": "older",
                "setor_executor": "MEL1",
            }
        ]
    )
    insert_dataframe_to_db(old, db_path, "ssas")

    # New with same key and newer date
    new = pd.DataFrame(
        [
            {
                "numero_ssa": "202401234",
                "situacao": "NEW",
                "data_cadastro": "02/01/2025",
                "descricao_ssa": "newer",
                "setor_executor": "MEL2",
            }
        ]
    )
    assert insert_dataframe_with_smart_upsert(new, db_path, "ssas") is True

    # Verify that updated row has NEW data
    with get_db_connection(db_path) as conn:
        df = pd.read_sql_query("SELECT * FROM ssas", conn)
    assert len(df) == 1
    assert df.iloc[0]["situacao"] == "NEW"
    assert df.iloc[0]["setor_executor"] == "MEL2"


def test_insert_dataframe_with_smart_upsert_handles_duplicate_numero_ssa_in_chunk(
    tmp_path,
):
    db_path = os.path.join(tmp_path, "x_dup.sqlite")
    schema = _make_schema(tmp_path)
    initialize_database(db_path, schema)

    seed = pd.DataFrame(
        [
            {
                "numero_ssa": "202401999",
                "situacao": "BASE",
                "data_cadastro": "01/01/2025",
                "descricao_ssa": "base",
                "setor_executor": "A1",
            }
        ]
    )
    insert_dataframe_to_db(seed, db_path, "ssas")

    incoming = pd.DataFrame(
        [
            {
                "numero_ssa": "202401999",
                "situacao": "UP1",
                "data_cadastro": "02/01/2025",
                "descricao_ssa": "up1",
                "setor_executor": "B1",
            },
            {
                "numero_ssa": "202401999",
                "situacao": "UP2",
                "data_cadastro": "03/01/2025",
                "descricao_ssa": "up2",
                "setor_executor": "C1",
            },
        ]
    )

    assert insert_dataframe_with_smart_upsert(incoming, db_path, "ssas") is True

    with get_db_connection(db_path) as conn:
        rows = pd.read_sql_query(
            "SELECT numero_ssa, situacao, data_cadastro, descricao_ssa, setor_executor FROM ssas",
            conn,
        )

    assert len(rows) == 1
    row = rows.iloc[0]
    assert str(row["numero_ssa"]) == "202401999"
    assert row["situacao"] == "UP2"
    assert row["setor_executor"] == "C1"


def test_smart_upsert_bootstraps_schema_with_id_on_fresh_db(tmp_path, monkeypatch):
    db_path = os.path.join(tmp_path, "fresh.sqlite")
    assert not os.path.exists(db_path)
    monkeypatch.setenv(
        "SSA_ALLOWED_COLUMNS",
        "numero_ssa,situacao,data_cadastro,descricao_ssa,setor_executor",
    )

    incoming = pd.DataFrame(
        [
            {
                "numero_ssa": "202599999",
                "situacao": "NEW",
                "data_cadastro": "03/01/2025",
                "descricao_ssa": "fresh insert",
                "setor_executor": "ZZ1",
                "campo_nao_permitido": "DROP_ME",
            }
        ]
    )

    assert insert_dataframe_with_smart_upsert(incoming, db_path, "ssa_table") is True
    assert os.path.exists(db_path)

    with get_db_connection(db_path) as conn:
        cols = [
            row[1] for row in conn.execute("PRAGMA table_info(ssa_table)").fetchall()
        ]
        assert "id" in cols
        assert "campo_nao_permitido" not in cols
        row = conn.execute(
            "SELECT numero_ssa, situacao FROM ssa_table WHERE numero_ssa = ?",
            ("202599999",),
        ).fetchone()

    assert row is not None
    assert str(row[0]) == "202599999"
    assert row[1] == "NEW"


def test_smart_upsert_reimport_keeps_single_sanitized_column(tmp_path, monkeypatch):
    db_path = os.path.join(tmp_path, "fresh_reimport.sqlite")
    monkeypatch.delenv("SSA_ALLOWED_COLUMNS", raising=False)

    incoming = pd.DataFrame(
        [
            {
                "numero_ssa": "202500001",
                "situacao": "A",
                "descricao_ssa": "d1",
                "nome paciente": "X",
            },
            {
                "numero_ssa": "202500002",
                "situacao": "B",
                "descricao_ssa": "d2",
                "nome paciente": "Y",
            },
        ]
    )

    assert insert_dataframe_with_smart_upsert(incoming, db_path, "ssas") is True
    assert insert_dataframe_with_smart_upsert(incoming, db_path, "ssas") is True

    with get_db_connection(db_path) as conn:
        cols = [
            row[1] for row in conn.execute("PRAGMA table_info(ssa_table)").fetchall()
        ]
        row_count = conn.execute("SELECT COUNT(*) FROM ssa_table").fetchone()[0]
        filled_count = conn.execute(
            "SELECT COUNT(*) FROM ssa_table WHERE nome_paciente IS NOT NULL"
        ).fetchone()[0]

    assert "nome_paciente" in cols
    assert "nome_paciente_1" not in cols
    assert row_count == 2
    assert int(filled_count) == row_count


def test_smart_upsert_preserves_literal_na_text(tmp_path):
    db_path = os.path.join(tmp_path, "text_na.sqlite")
    schema = _make_schema(tmp_path)
    initialize_database(db_path, schema)

    incoming = pd.DataFrame(
        [
            {
                "numero_ssa": "202500201",
                "situacao": "NEW",
                "data_cadastro": "03/01/2025",
                "descricao_ssa": "na",
                "setor_executor": "MEL4",
            }
        ]
    )

    assert insert_dataframe_with_smart_upsert(incoming, db_path, "ssas") is True

    with get_db_connection(db_path) as conn:
        row = conn.execute(
            "SELECT descricao_ssa FROM ssas WHERE numero_ssa = ?",
            ("202500201",),
        ).fetchone()

    assert row is not None
    assert row[0] == "na"


def test_smart_upsert_updates_to_literal_na_text(tmp_path):
    db_path = os.path.join(tmp_path, "text_na_update.sqlite")
    schema = _make_schema(tmp_path)
    initialize_database(db_path, schema)

    seed = pd.DataFrame(
        [
            {
                "numero_ssa": "202500202",
                "situacao": "OLD",
                "data_cadastro": "01/01/2025",
                "descricao_ssa": "antigo",
                "setor_executor": "MEL1",
            }
        ]
    )
    incoming = pd.DataFrame(
        [
            {
                "numero_ssa": "202500202",
                "situacao": "NEW",
                "data_cadastro": "02/01/2025",
                "descricao_ssa": "na",
                "setor_executor": "MEL4",
            }
        ]
    )

    assert insert_dataframe_to_db(seed, db_path, "ssas") is True
    assert insert_dataframe_with_smart_upsert(incoming, db_path, "ssas") is True

    with get_db_connection(db_path) as conn:
        row = conn.execute(
            "SELECT situacao, descricao_ssa FROM ssas WHERE numero_ssa = ?",
            ("202500202",),
        ).fetchone()

    assert row is not None
    assert row[0] == "NEW"
    assert row[1] == "na"


def test_optimized_insert_applies_whitelist_before_schema_sync(tmp_path, monkeypatch):
    db_path = os.path.join(tmp_path, "optimized_whitelist.sqlite")
    schema = _make_schema(tmp_path)
    initialize_database(db_path, schema)
    monkeypatch.setenv(
        "SSA_ALLOWED_COLUMNS",
        "numero_ssa,situacao,data_cadastro,descricao_ssa,setor_executor",
    )

    incoming = pd.DataFrame(
        [
            {
                "numero_ssa": "202500301",
                "situacao": "NEW",
                "data_cadastro": "03/01/2025",
                "descricao_ssa": "ok",
                "setor_executor": "MEL4",
                "campo_extra": "DROP_ME",
            }
        ]
    )

    enable_optimized_import()
    try:
        assert insert_dataframe_with_smart_upsert(incoming, db_path, "ssas") is True

        with get_db_connection(db_path) as conn:
            cols = [
                row[1] for row in conn.execute("PRAGMA table_info(ssas)").fetchall()
            ]
            row = conn.execute(
                "SELECT numero_ssa, descricao_ssa FROM ssas WHERE numero_ssa = ?",
                ("202500301",),
            ).fetchone()
    finally:
        disable_optimized_import()

    assert "campo_extra" not in cols
    assert row is not None
    assert str(row[0]) == "202500301"
    assert row[1] == "ok"


def test_smart_upsert_discards_placeholder_dynamic_headers(tmp_path, monkeypatch):
    db_path = os.path.join(tmp_path, "fresh_placeholder.sqlite")
    monkeypatch.delenv("SSA_ALLOWED_COLUMNS", raising=False)

    incoming = pd.DataFrame(
        [["202500031", "NEW", "desc", "A", "B", "C"]],
        columns=["numero_ssa", "situacao", "descricao_ssa", float("nan"), "nan", "   "],
    )

    assert insert_dataframe_with_smart_upsert(incoming, db_path, "ssas") is True

    with get_db_connection(db_path) as conn:
        cols = [
            row[1] for row in conn.execute("PRAGMA table_info(ssa_table)").fetchall()
        ]
        row_count = conn.execute("SELECT COUNT(*) FROM ssa_table").fetchone()[0]

    lowered = {str(col).strip().lower() for col in cols}
    assert "nan" not in lowered
    assert "nan_1" not in lowered
    assert "nan_2" not in lowered
    assert row_count == 1


def test_smart_upsert_dynamic_sync_respects_whitelist_after_sanitize(
    tmp_path, monkeypatch
):
    db_path = os.path.join(tmp_path, "fresh_whitelist.sqlite")
    monkeypatch.setenv("SSA_ALLOWED_COLUMNS", "numero_ssa,situacao,descricao_ssa")

    incoming = pd.DataFrame(
        [
            {
                "numero_ssa": "202500099",
                "situacao": "NEW",
                "descricao_ssa": "desc",
                "nome paciente": "X",
            }
        ]
    )

    assert insert_dataframe_with_smart_upsert(incoming, db_path, "ssas") is True

    with get_db_connection(db_path) as conn:
        cols = [
            row[1] for row in conn.execute("PRAGMA table_info(ssa_table)").fetchall()
        ]

    assert "nome_paciente" not in cols


def test_smart_upsert_does_not_persist_textual_null_sentinels(tmp_path):
    db_path = os.path.join(tmp_path, "na_smart.sqlite")
    schema = _make_schema(tmp_path)
    initialize_database(db_path, schema)

    incoming = pd.DataFrame(
        [
            {
                "numero_ssa": "202500111",
                "situacao": "ABERTA",
                "data_cadastro": "01/01/2025",
                "descricao_ssa": "<NA>",
                "setor_executor": " None ",
            }
        ]
    )

    assert insert_dataframe_with_smart_upsert(incoming, db_path, "ssas") is True

    with get_db_connection(db_path) as conn:
        row = conn.execute(
            "SELECT descricao_ssa, setor_executor FROM ssas WHERE numero_ssa = ?",
            ("202500111",),
        ).fetchone()

    assert row is not None
    assert row[0] is None
    assert row[1] is None


def test_smart_upsert_sanitizes_extended_textual_null_sentinels(tmp_path):
    db_path = os.path.join(tmp_path, "na_smart_extended.sqlite")
    schema = _make_schema(tmp_path)
    initialize_database(db_path, schema)

    incoming = pd.DataFrame(
        [
            {
                "numero_ssa": "202500112",
                "situacao": "ABERTA",
                "data_cadastro": "01/01/2025",
                "descricao_ssa": " null ",
                "setor_executor": " n/a ",
            }
        ]
    )

    assert insert_dataframe_with_smart_upsert(incoming, db_path, "ssas") is True

    with get_db_connection(db_path) as conn:
        row = conn.execute(
            "SELECT descricao_ssa, setor_executor FROM ssas WHERE numero_ssa = ?",
            ("202500112",),
        ).fetchone()

    assert row is not None
    assert row[0] is None
    assert row[1] is None


def test_simple_insert_does_not_persist_textual_null_sentinels(tmp_path):
    db_path = os.path.join(tmp_path, "na_simple.sqlite")
    schema = _make_schema(tmp_path)
    initialize_database(db_path, schema)

    incoming = pd.DataFrame(
        [
            {
                "numero_ssa": "202500222",
                "situacao": "ABERTA",
                "data_cadastro": "01/01/2025",
                "descricao_ssa": "<NA>",
                "setor_executor": " nan ",
            }
        ]
    )

    assert insert_dataframe_to_db(incoming, db_path, "ssas") is True

    with get_db_connection(db_path) as conn:
        row = conn.execute(
            "SELECT descricao_ssa, setor_executor FROM ssas WHERE numero_ssa = ?",
            ("202500222",),
        ).fetchone()

    assert row is not None
    assert row[0] is None
    assert row[1] is None
