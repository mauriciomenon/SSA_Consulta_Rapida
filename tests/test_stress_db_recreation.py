from pathlib import Path

import pytest

from armazenamento.database import insert_dataframe_with_smart_upsert
from utils.robust_importer import import_excel_robust


@pytest.mark.stress
def test_stress_recreate_db_loop(tmp_path: Path):
    """Stress: recria DB 5 vezes garantindo que não há falha ou acumulo de lixo.

    Não mede performance rigorosa, apenas robustez.
    """
    # Pequena planilha sintética
    import pandas as pd

    rows = [
        {"Nº SSA": "202512345", "Data Cadastro": "2025-09-10", "Valor": 1},
        {"Numero SSA": "202512345", "data_cadastro": "2025-09-12", "Valor": 2},
        {"Nº SSA Original": "202545678", "Data Cadastro": "2025-09-11", "Valor": 3},
    ]
    f = tmp_path / "stress.xlsx"
    pd.DataFrame(rows).to_excel(f, index=False)
    db_path = tmp_path / "loop.db"
    for i in range(5):
        df, stats = import_excel_robust(str(f))
        assert not df.empty, "Import unexpectedly empty in stress loop"
        ok = insert_dataframe_with_smart_upsert(df, str(db_path))
        assert ok is True
        # remove DB to force full recreation next cycle
        if db_path.exists():
            db_path.unlink()
    # sucesso se chegou aqui sem exceção
    assert True
