# ruff: noqa: E402
import os
import sys
from io import StringIO
from unittest.mock import patch

import pandas as pd

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, project_root)

from interface.display import pretty_print_details


def test_details_uses_shared_formatter_for_dates_and_nulls():
    series = pd.Series(
        {
            "numero_ssa": "2025001",
            "data_cadastro": "2025-01-03",
            "semana_cadastro": 12.0,
            "valor": 10.0,
            "campo_nulo": None,
            "campo_nan_str": "nan",
        }
    )
    display_map = {
        "numero_ssa": "Nº SSA",
        "data_cadastro": "Emitida Em",
        "semana_cadastro": "Sem. Cad.",
        "valor": "Valor",
        "campo_nulo": "Nulo",
        "campo_nan_str": "NaNstr",
    }
    with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
        pretty_print_details(series, display_map)
        out = mock_stdout.getvalue()
    # Date formatted dd/mm/YYYY
    assert "03/01/2025" in out
    # Week formatted as int
    assert "Sem. Cad.:" in out
    assert "12" in out
    # Valor without .0
    assert "Valor:" in out and "10" in out and ".0" not in out
    # Nullish as '-'
    assert "Nulo:" in out and " -" in out
    assert "NaNstr:" in out and " -" in out
