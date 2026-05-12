import os

import pandas as pd

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
    schema = _make_schema(tmp_path)
    # Create and then reset
    initialize_database(db_path, schema)
    assert reset_database(db_path, mode="table", schema_path=schema) is True
    # Table should exist
    with get_db_connection(db_path) as conn:
        cur = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='ssas'"
        )
        assert cur.fetchone() is not None


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
