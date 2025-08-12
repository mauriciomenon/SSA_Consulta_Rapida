# tests/test_formatting_rules.py
import os
import sys
import pandas as pd
from datetime import datetime

# Add project root to sys.path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

from interface.table_printer import format_cell_data, format_dataframe_for_cli
from core.app_logic import advanced_filter_dataframe

def test_week_formatting_removes_decimal_zero():
    df = pd.DataFrame({
        'semana_programada': [10.0, 11.5, '12.0', '13', None]
    })
    out = [format_cell_data(v, 'semana_programada') for v in df['semana_programada']]
    assert out[0] == '10'
    assert out[1] == '11.5'
    assert out[2] == '12'
    assert out[3] == '13'
    assert out[4] == ''

def test_date_formatting_strips_time():
    values = ['2025-07-22 10:33:00', '2025-07-22', None]
    out = [format_cell_data(v, 'data_cadastro') for v in values]
    assert out[0] == '2025-07-22'
    assert out[1] == '2025-07-22'
    assert out[2] == ''

def test_cli_no_nan_and_headers_short_labels(tmp_path):
    df = pd.DataFrame({
        'numero_ssa': ['123', None],
        'descricao_ssa': ['Teste', float('nan')],
        'semana_programada': [5.0, 6.0],
        'emitida_em': ['2025-07-22 10:00:00', '2025-07-23 12:00:00']
    })
    text = format_dataframe_for_cli(df, display_map=None, max_rows=5)
    assert 'nan' not in text.lower()
    assert 'No' in text.splitlines()[0]
    assert '2025-07-22' in text
    assert '5' in text and '5.0' not in text

def test_advanced_filter_date_range():
    df = pd.DataFrame({
        'data_cadastro': [
            '2025-07-20 08:00:00',
            '2025-07-25 09:00:00',
            '2025-08-01 10:00:00'
        ],
        'setor_executor': ['A', 'B', 'C']
    })
    filters = {
        'data_inicio': datetime(2025, 7, 22).date(),
        'data_fim': datetime(2025, 7, 31).date()
    }
    out = advanced_filter_dataframe(df, filters)
    assert len(out) == 1
    assert out.iloc[0]['setor_executor'] == 'B'

def test_ssa_formatting_variants():
    vals = ['123', '0009876', '202512345', None, '']
    out = [format_cell_data(v, 'numero_ssa') for v in vals]
    # <=5 dígitos: prefixa ano atual (2025)
    assert out[0] == '202500123'
    # 7 dígitos com zeros à esquerda vira 4 dígitos após strip -> prefixa ano (2025)
    assert out[1] == '202509876'
    # Já 9 dígitos: mantém
    assert out[2] == '202512345'
    # Nulos -> vazio
    assert out[3] == '' and out[4] == ''
