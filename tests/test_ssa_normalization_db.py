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
