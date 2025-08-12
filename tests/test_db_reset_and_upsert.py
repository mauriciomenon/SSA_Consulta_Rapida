import os
import sys
import pandas as pd

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
one_up = os.path.dirname(PROJECT_ROOT)
if one_up not in sys.path:
    sys.path.insert(0, one_up)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from armazenamento.database import (
    initialize_database,
    create_indexes,
    reset_database,
    insert_dataframe_with_smart_upsert,
    query_db,
)


def _setup_db(tmp_path):
    db_path = os.path.join(tmp_path, 'test.db')
    schema = os.path.join(PROJECT_ROOT, 'config', 'schema.sql')
    initialize_database(db_path, schema)
    create_indexes(db_path)
    return db_path


def test_reset_database_file(tmp_path):
    db_path = _setup_db(tmp_path)
    # Write something
    df = pd.DataFrame({'numero_ssa': ['123']})
    # Use a real file path so metadata extraction works
    dummy_file = os.path.join(PROJECT_ROOT, 'docs_entrada', 'SSAs Executadas_15-07-2025_0239PM.xlsx')
    insert_dataframe_with_smart_upsert(df, db_path, 'ssas', dummy_file)
    assert not query_db(db_path, 'ssas').empty
    # Reset file
    assert reset_database(db_path, mode='file', schema_file=os.path.join(PROJECT_ROOT, 'config', 'schema.sql')) is True
    # Should be empty again
    out = query_db(db_path, 'ssas')
    assert out.empty


def test_reset_database_table(tmp_path):
    db_path = _setup_db(tmp_path)

    df = pd.DataFrame({'numero_ssa': ['123', '456']})
    file1 = os.path.join(PROJECT_ROOT, 'docs_entrada', 'SSAs Executadas_15-07-2025_0239PM.xlsx')
    insert_dataframe_with_smart_upsert(df, db_path, 'ssas', file1)

    # Sanity
    out = query_db(db_path, 'ssas')
    assert len(out) >= 2

    # Reset only table
    assert reset_database(db_path, mode='table') is True
    out2 = query_db(db_path, 'ssas')
    assert out2.empty


def test_upsert_uses_newer_file_date(tmp_path):
    db_path = _setup_db(tmp_path)
    # Insert initial row from older file
    df1 = pd.DataFrame({'numero_ssa': ['123'], 'situacao': ['APL']})
    file_old = os.path.join(PROJECT_ROOT, 'docs_entrada', 'SSAs Executadas_15-07-2025_0227PM.xlsx')
    insert_dataframe_with_smart_upsert(df1, db_path, 'ssas', file_old)

    # Update with newer file and different situacao
    df2 = pd.DataFrame({'numero_ssa': ['123'], 'situacao': ['APG']})
    file_new = os.path.join(PROJECT_ROOT, 'docs_entrada', 'SSAs Executadas_22-07-2025_0252PM.xlsx')
    insert_dataframe_with_smart_upsert(df2, db_path, 'ssas', file_new)

    out = query_db(db_path, 'ssas')
    assert len(out) >= 1
    # Latest should reflect newer file and incremented version
    latest = out[out['numero_ssa'] == 202500123].sort_values('versao_dados').iloc[-1]
    assert latest['situacao'] == 'APG'
    assert int(latest['versao_dados']) >= 2


def test_upsert_tie_breaks_by_state_when_same_date(tmp_path):
    db_path = _setup_db(tmp_path)
    # Same date in filename -> tie; expect state advancement to win
    df1 = pd.DataFrame({'numero_ssa': ['123'], 'situacao': ['APL']})
    df2 = pd.DataFrame({'numero_ssa': ['123'], 'situacao': ['APG']})
    file_same = os.path.join(PROJECT_ROOT, 'docs_entrada', 'SSAs Executadas_22-07-2025_0252PM.xlsx')
    insert_dataframe_with_smart_upsert(df1, db_path, 'ssas', file_same)
    insert_dataframe_with_smart_upsert(df2, db_path, 'ssas', file_same)

    out = query_db(db_path, 'ssas')
    assert len(out) >= 1
    latest = out[out['numero_ssa'] == 202500123].sort_values('versao_dados').iloc[-1]
    assert latest['situacao'] == 'APG'
