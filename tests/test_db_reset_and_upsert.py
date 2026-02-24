import os
import pandas as pd

from armazenamento.database import (
    get_db_connection,
    initialize_database,
    reset_database,
    ensure_indexes,
    insert_dataframe_to_db,
    insert_dataframe_with_smart_upsert,
)


def _make_schema(tmpdir):
    schema = os.path.join(tmpdir, 'schema.sql')
    with open(schema, 'w', encoding='utf-8') as f:
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
    db_path = os.path.join(tmp_path, 'x.sqlite')
    with get_db_connection(db_path) as conn:
        conn.execute('CREATE TABLE T(x INTEGER);')
        conn.commit()
    assert os.path.exists(db_path)
    assert reset_database(db_path, mode='file') is True
    assert not os.path.exists(db_path)


def test_reset_database_table_mode(tmp_path):
    db_path = os.path.join(tmp_path, 'x.sqlite')
    schema = _make_schema(tmp_path)
    # Create and then reset
    initialize_database(db_path, schema)
    assert reset_database(db_path, mode='table', schema_path=schema) is True
    # Table should exist
    with get_db_connection(db_path) as conn:
        cur = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='ssas'")
        assert cur.fetchone() is not None


def test_ensure_indexes(tmp_path):
    db_path = os.path.join(tmp_path, 'x.sqlite')
    schema = _make_schema(tmp_path)
    initialize_database(db_path, schema)
    assert ensure_indexes(db_path) is True


def test_insert_dataframe_with_smart_upsert(tmp_path):
    db_path = os.path.join(tmp_path, 'x.sqlite')
    schema = _make_schema(tmp_path)
    initialize_database(db_path, schema)

    # Seed old row for a valid numero_ssa (YYYY + 5 dígitos) with earlier date
    old = pd.DataFrame([
        {
            'numero_ssa': '202401234',
            'situacao': 'OLD',
            'data_cadastro': '01/01/2025',
            'descricao_ssa': 'older',
            'setor_executor': 'MEL1',
        }
    ])
    insert_dataframe_to_db(old, db_path, 'ssas')

    # New with same key and newer date
    new = pd.DataFrame([
        {
            'numero_ssa': '202401234',
            'situacao': 'NEW',
            'data_cadastro': '02/01/2025',
            'descricao_ssa': 'newer',
            'setor_executor': 'MEL2',
        }
    ])
    assert insert_dataframe_with_smart_upsert(new, db_path, 'ssas') is True

    # Verify that updated row has NEW data
    with get_db_connection(db_path) as conn:
        df = pd.read_sql_query('SELECT * FROM ssas', conn)
    assert len(df) == 1
    assert df.iloc[0]['situacao'] == 'NEW'
    assert df.iloc[0]['setor_executor'] == 'MEL2'


def test_insert_dataframe_with_smart_upsert_handles_duplicate_numero_ssa_in_chunk(tmp_path):
    db_path = os.path.join(tmp_path, 'x_dup.sqlite')
    schema = _make_schema(tmp_path)
    initialize_database(db_path, schema)

    seed = pd.DataFrame(
        [
            {
                'numero_ssa': '202401999',
                'situacao': 'BASE',
                'data_cadastro': '01/01/2025',
                'descricao_ssa': 'base',
                'setor_executor': 'A1',
            }
        ]
    )
    insert_dataframe_to_db(seed, db_path, 'ssas')

    incoming = pd.DataFrame(
        [
            {
                'numero_ssa': '202401999',
                'situacao': 'UP1',
                'data_cadastro': '02/01/2025',
                'descricao_ssa': 'up1',
                'setor_executor': 'B1',
            },
            {
                'numero_ssa': '202401999',
                'situacao': 'UP2',
                'data_cadastro': '03/01/2025',
                'descricao_ssa': 'up2',
                'setor_executor': 'C1',
            },
        ]
    )

    assert insert_dataframe_with_smart_upsert(incoming, db_path, 'ssas') is True

    with get_db_connection(db_path) as conn:
        rows = pd.read_sql_query(
            "SELECT numero_ssa, situacao, data_cadastro, descricao_ssa, setor_executor FROM ssas",
            conn,
        )

    assert len(rows) == 1
    row = rows.iloc[0]
    assert str(row['numero_ssa']) == '202401999'
    assert row['situacao'] == 'UP2'
    assert row['setor_executor'] == 'C1'
