import os
import sys
import pandas as pd
from unittest.mock import patch

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, PROJECT_ROOT)

from interface.table_printer import format_dataframe_for_cli


def test_cli_selection_prefers_essentials_on_small_width():
    df = pd.DataFrame({
        'numero_ssa': ['12345', '67890'],
        'setor_executor': ['IEE3', 'MEL3'],
        'localizacao': ['Sala 100', 'Sala 200'],
        'descricao_ssa': ['Texto muito longo que deve ser cortado', 'Outro texto longo']
    })

    # Simula terminal muito estreito
    class Size:
        def __init__(self, columns):
            self.columns = columns

    with patch('os.get_terminal_size', return_value=Size(40)):
        out = format_dataframe_for_cli(df, display_map=None)

    # Primeira linha é o cabeçalho; separador é " | "
    header = out.splitlines()[0]
    headers = [h.strip() for h in header.split('|')]

    # Deve conter '#' sempre e priorizar 'No' e 'Exec' (labels curtos)
    assert any(h.startswith('#') for h in headers)
    assert any(h.strip().startswith('No') for h in headers)
    assert any(h.strip().startswith('Exec') for h in headers)
    # Em largura pequena, 'Desc SSA' pode ficar de fora; não assertiva rígida
