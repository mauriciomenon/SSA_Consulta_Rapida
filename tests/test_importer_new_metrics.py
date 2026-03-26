import os
import pathlib

import pandas as pd

from utils.robust_importer import import_excel_robust

BASE = pathlib.Path(__file__).resolve().parent.parent


def test_importer_metrics_exposed(tmp_path):
    # cria planilha simples com cabecalho pobre para acionar reheader scan
    df = pd.DataFrame(
        {
            "Titulo Geral": ["ColA", "ColB", "ColC", "ColD", "ColE"],
            "X": [1, 2, 3, 4, 5],
            "Y": [10, 20, 30, 40, 50],
            "Z": [100, 200, 300, 400, 500],
            "W": [5, 4, 3, 2, 1],
            "K": [9, 8, 7, 6, 5],
        }
    )
    file_path = tmp_path / "teste_header.xlsx"
    df.to_excel(file_path, index=False)
    os.environ["SSA_MAX_HEADER_SCAN"] = "5"
    _df, stats = import_excel_robust(str(file_path))
    assert "header_candidate_lines_considered" in stats
    assert stats["header_candidate_lines_considered"] <= 5
    assert "alias_hits" in stats
    # limpeza
    os.environ.pop("SSA_MAX_HEADER_SCAN")
