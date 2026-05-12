from pathlib import Path
import gc
import sqlite3
import time
import pandas as pd
import pytest

from utils.robust_importer import import_excel_robust
from armazenamento.database import insert_dataframe_with_smart_upsert

# Contract (assumptions):
# - import_excel_robust(path) -> DataFrame with cleaned 'numero_ssa' column (string) and date columns parsed.
# - insert_dataframe_with_smart_upsert(df, db_path) performs upsert on primary key 'numero_ssa'.
# - Re-importing same file must not duplicate rows.
# - Re-creating database (deleting file) then re-importing should repopulate from scratch without hang.

@pytest.fixture()
def sample_excel_file(tmp_path: Path):
    """Create a realistic Excel file with variations, duplicates and invalid numero_ssa.

    Uses mixed header styles to exercise header normalization & coalescence. Uses
    'Data Cadastro' / 'data_cadastro' variants to feed deduplication logic.
    """
    # numero_ssa must be exactly 9 digits; first 4 digits year 1980-2050.
    rows = [
        {"N\u00ba SSA": "202512345", "NOME Paciente": "Alice", "Data Cadastro": "2025-09-10", "Valor": 10},
        # Duplicate with newer date (should supersede first for numero_ssa)
        {"Numero SSA": "202512345", "nome paciente": "Alice A.", "data_cadastro": "2025-09-12", "Valor": 11},
        # Another distinct record
        {"N\u00ba SSA Original": "202545678", "Nome Paciente": "Bob", "Data Cadastro": "2025-09-11", "Valor": 5},
        # Invalid numero_ssa (blank) should be dropped
        {"N\u00ba SSA": "", "Nome Paciente": "Vazio", "Data Cadastro": "2025-09-09", "Valor": 1},
    ]
    df = pd.DataFrame(rows)
    file_path = tmp_path / "planilha_real.xlsx"
    df.to_excel(file_path, index=False)
    return file_path

@pytest.fixture()
def temp_db_path(tmp_path: Path):
    return tmp_path / "ssas_test.db"


def _count_rows(db_path: Path) -> int:
    if not db_path.exists():
        return 0
    with sqlite3.connect(db_path) as conn:
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM ssa_table")
        return int(cur.fetchone()[0])


def test_fresh_import(sample_excel_file: Path, temp_db_path: Path):
    df, stats = import_excel_robust(str(sample_excel_file))
    assert not df.empty, "Importer returned empty DataFrame for synthetic workbook"
    # Expect 2 valid normalized numero_ssa values after dedup and cleaning
    numeros = sorted(df['numero_ssa'].unique().tolist())
    assert numeros == ['202512345', '202545678']
    # numero_ssa 202512345 should retain newer row (Valor 11)
    # Coluna 'Valor' e normalizada para 'valor' pelo importador (minusculas canonicas)
    valor_latest = df.loc[df['numero_ssa'] == '202512345', 'valor'].iloc[0]
    assert int(valor_latest) == 11
    # stats validations
    assert stats.get('total_rows_in', 0) >= 3
    assert stats.get('invalid_numero_ssa_rows', -1) >= 1
    # Upsert into fresh DB
    ok = insert_dataframe_with_smart_upsert(df, str(temp_db_path))
    assert ok is True
    assert temp_db_path.exists(), "DB should be created"
    assert _count_rows(temp_db_path) == 2, "DB should have 2 rows after first import"


def test_reimport_idempotent(sample_excel_file: Path, temp_db_path: Path):
    df_first, _ = import_excel_robust(str(sample_excel_file))
    assert not df_first.empty, "Importer returned empty DataFrame on first import"
    insert_dataframe_with_smart_upsert(df_first, str(temp_db_path))
    count_after_first = _count_rows(temp_db_path)
    df_second, _ = import_excel_robust(str(sample_excel_file))
    insert_dataframe_with_smart_upsert(df_second, str(temp_db_path))
    count_after_second = _count_rows(temp_db_path)
    assert count_after_first == 2
    assert count_after_second == 2, "Reimporting same file should not create duplicates"


def test_recreate_db_then_import(sample_excel_file: Path, temp_db_path: Path):
    # First import
    df1, _ = import_excel_robust(str(sample_excel_file))
    assert not df1.empty, "Importer returned empty DataFrame before DB recreation"
    insert_dataframe_with_smart_upsert(df1, str(temp_db_path))
    assert _count_rows(temp_db_path) == 2
    # Simulate recreation: delete DB file
    if temp_db_path.exists():
        last_exc: Exception | None = None
        for _ in range(50):
            try:
                temp_db_path.unlink()
                last_exc = None
                break
            except PermissionError as exc:
                last_exc = exc
                try:
                    with sqlite3.connect(temp_db_path) as conn:
                        conn.close()
                except Exception:
                    pass
                gc.collect()
                time.sleep(0.2)
        if last_exc:
            raise last_exc
    assert not temp_db_path.exists()
    # Import again (should recreate schema internally)
    df2, _ = import_excel_robust(str(sample_excel_file))
    insert_dataframe_with_smart_upsert(df2, str(temp_db_path))
    assert temp_db_path.exists(), "DB file should be recreated"
    assert _count_rows(temp_db_path) == 2, "Freshly recreated DB should have 2 rows after import"
