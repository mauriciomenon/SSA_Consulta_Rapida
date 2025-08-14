import pandas as pd
from armazenamento.database import normalize_numero_ssa_dataframe, _normalize_numero_ssa_value


def test_normalize_numero_ssa_value_various():
    assert _normalize_numero_ssa_value(None) is None
    assert _normalize_numero_ssa_value(" ") is None
    assert _normalize_numero_ssa_value("ABC123") == 123
    # 8 digits -> zfill to 9
    assert _normalize_numero_ssa_value("12345678") == 12345678  # zfill then int still same numeric
    # 10+ digits -> use last 9
    assert _normalize_numero_ssa_value("2025123456") == 25123456  # last 9 -> 025123456 -> int 25123456


def test_normalize_numero_ssa_dataframe_apply():
    df = pd.DataFrame({
        'numero_ssa': [None, 'abc123', '12345678', '202501234']
    })
    out = normalize_numero_ssa_dataframe(df)
    assert list(out['numero_ssa']) == [None, 123, 12345678, 2501234]
# tests/test_ssa_normalization_db.py
import os
import sys
import pandas as pd

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

from armazenamento.database import normalize_numero_ssa

def test_normalize_numero_ssa_basic():
    # <=5 dígitos: prefixa ano 2025 e preenche para 5
    assert normalize_numero_ssa('123') == '202500123'
    # 7 dígitos com zeros à esquerda: após remover zeros fica com 4 -> prefixa ano
    assert normalize_numero_ssa('0009876') == '202509876'
    # já com 9 dígitos mantém
    assert normalize_numero_ssa('202500045') == '202500045'
    # vazios/nulos retornam None
    assert normalize_numero_ssa('') is None
    assert normalize_numero_ssa(None) is None
