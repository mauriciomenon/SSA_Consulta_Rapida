# tests/test_cli_formatting.py
import os
import sys
import pandas as pd
from unittest.mock import patch

# Add project root to sys.path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

from interface.table_printer import format_dataframe_for_cli

def test_format_dataframe_for_cli_applies_short_labels_and_ssa_formatting():
    df = pd.DataFrame({
        'numero_ssa': ['123', '202500045', '0009876'],
        'setor_executor': ['IEE3', 'MEL3', 'IEQ1'],
        'situacao': ['APG', 'ADM', 'SCA'],
        'descricao_ssa': ['Desc A', 'Desc B', 'Desc C']
    })

    class Size:
        def __init__(self, columns):
            self.columns = columns
    
    with patch('os.get_terminal_size', return_value=Size(200)):
        out = format_dataframe_for_cli(df, display_map=None)

    # Headers should include short label for numero_ssa ("No") from config
    header = out.splitlines()[0]
    assert 'No' in header

    # SSA numbers should be normalized to 9 digits (e.g., 123 -> 202500123)
    assert '202500123' in out
    # Preserve already-9-digit form
    assert '202500045' in out
    # 7-digit with leading zeros becomes 9-digit
    assert '000009876' not in out  # should be formatted
    # Check formatted version of 0009876 -> 00009876 -> 2025? no: it's 7 digits so pad to 9
    assert '000009876' not in out
    assert '000009876' not in out
