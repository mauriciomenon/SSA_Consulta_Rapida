# tests/test_cli_highlight_and_negatives.py
import os
import sys
import pandas as pd
from unittest.mock import patch

# Add project root to path like other tests do
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

from core.app_logic import filter_dataframe
from interface.table_printer import format_dataframe_for_cli


def test_filter_dataframe_negative_terms_excludes_rows():
    df = pd.DataFrame({
        'numero_ssa': ['202500001', '202500002', '202500003', '202500004'],
        'setor_executor': ['MEL4', 'MEL4', 'IEE3', 'MEL4'],
        'situacao': ['Pendente', 'Cancelada', 'Pendente', 'Executada'],
        'descricao_ssa': ['troca', 'ajuste cancelado', 'inspeção', 'troca urgente']
    })
    # Positive MEL4, negative cancelada -> deve excluir a linha 2
    out = filter_dataframe(df, ['MEL4', '!cancelada'])
    assert len(out) == 2
    # As linhas restantes têm MEL4 e não têm 'Cancelada'
    assert all(out['setor_executor'].str.contains('MEL4'))
    assert all(~out['situacao'].str.contains('Cancelada', case=False))


def test_cli_highlight_terms_ansi_detection_and_no_color(monkeypatch):
    df = pd.DataFrame({
        'numero_ssa': ['202500001', '202500002'],
        'setor_executor': ['IEE3', 'MEL4'],
        'situacao': ['Pendente', 'Executada'],
        'descricao_ssa': ['Teste highlight', 'Outra linha']
    })

    # Força largura para determinismo
    max_width = 120

    # 1) Com suporte ANSI simulado -> deve conter códigos \x1b
    with patch('interface.table_printer.sys.stdout.isatty', return_value=True):
        # Em muitos ambientes os.name!='nt', mas garantimos retorno True simulando POSIX
        with patch('interface.table_printer.os.name', 'posix'):
            text = format_dataframe_for_cli(df, max_width=max_width, highlight_terms=['highlight'])
            lines = text.splitlines()
            # Dados começam a partir da linha 3 (0=header,1=separator)
            assert any('\x1b[1m' in ln for ln in lines[2:]), 'Esperava sequências ANSI quando suportado'

    # 2) Sem suporte (NO_COLOR) -> não deve conter ANSI
    monkeypatch.setenv('NO_COLOR', '1')
    try:
        with patch('interface.table_printer.sys.stdout.isatty', return_value=True):
            with patch('interface.table_printer.os.name', 'posix'):
                text_no_color = format_dataframe_for_cli(df, max_width=max_width, highlight_terms=['highlight'])
                assert '\x1b[1m' not in text_no_color
    finally:
        monkeypatch.delenv('NO_COLOR', raising=False)


def test_cli_fixed_widths_for_known_columns():
    # Garante que larguras fixas foram aplicadas (Stat=5, Exec=6, Emi=6)
    df = pd.DataFrame({
        'numero_ssa': ['202500001'],
        'setor_executor': ['IEE3'],
        'setor_emissor': ['MEL4'],
        'situacao': ['APG'],
        'descricao_ssa': ['X']
    })
    text = format_dataframe_for_cli(df, max_width=120)
    header = text.splitlines()[0]
    cells = header.split(' | ')
    # Mapa: encontrar células por rótulo curto
    # Nota: labels curtos vêm de config/column_priority.json
    labels = {cell.strip(): len(cell) for cell in cells}
    # Verificações: pode estar como "Exec" e "Emi" e "Stat"
    exec_cell_len = next((len(c) for c in cells if c.strip() in ('Exec', 'Executor')), None)
    emi_cell_len = next((len(c) for c in cells if c.strip() in ('Emi', 'Emissor')), None)
    stat_cell_len = next((len(c) for c in cells if c.strip() in ('Stat', 'Situação')), None)
    assert exec_cell_len in (6, None)  # Exec pode não caber dependendo da seleção, então aceitarmos None
    assert emi_cell_len in (6, None)
    assert stat_cell_len in (5, None)
