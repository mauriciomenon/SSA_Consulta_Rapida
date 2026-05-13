import pandas as pd

from interface.table_printer import _select_columns_for_width


def test_select_columns_respects_always_visible_and_fixed_widths(tmp_path, monkeypatch):
    df = pd.DataFrame(
        {
            'numero_ssa': ['2025001', '2025002'],
            'localizacao_codigo': ['A1', 'B2'],
            'setor_executor': ['IEE3', 'MEL3'],
            'situacao': ['ADM', 'APG'],
            'descricao_ssa': ['desc ' * 20, 'desc ' * 20],
            'data_cadastro': ['2025-01-01', '2025-01-02'],
            'outra': ['x', 'y'],
        }
    )
    display_map = {
        'numero_ssa': 'Nº SSA',
        'localizacao_codigo': 'Loc.',
        'setor_executor': 'Executor',
        'situacao': 'Situação',
        'descricao_ssa': 'Descrição da SSA',
        'data_cadastro': 'Emitida Em',
        'outra': 'Outra',
    }

    essential = ['numero_ssa', 'descricao_ssa']
    priority = ['data_cadastro']
    always_visible = ['numero_ssa', 'localizacao_codigo', 'situacao']
    fixed_widths = {'numero_ssa': 9, 'localizacao_codigo': 5, 'situacao': 6}

    selected = _select_columns_for_width(
        df,
        display_map,
        available_width=40,
        essential_columns=essential,
        priority_order=priority,
        always_visible=always_visible,
        fixed_widths=fixed_widths,
    )
    assert selected[0] == '#'
    assert 'numero_ssa' in selected
    assert 'localizacao_codigo' in selected
    assert 'situacao' in selected


def test_select_columns_handles_extremely_small_width(monkeypatch):
    df = pd.DataFrame(
        {
            'numero_ssa': ['2025001', '2025002'],
            'localizacao_codigo': ['A1', 'B2'],
            'situacao': ['ADM', 'APG'],
            'descricao_ssa': ['x' * 100, 'y' * 100],
        }
    )
    display_map = {
        'numero_ssa': 'Nº SSA',
        'localizacao_codigo': 'Loc.',
        'situacao': 'Sit.',
        'descricao_ssa': 'Descrição',
    }

    essential = ['numero_ssa', 'descricao_ssa']
    priority = []
    always_visible = ['numero_ssa', 'localizacao_codigo', 'situacao']
    fixed_widths = {'numero_ssa': 9, 'localizacao_codigo': 4, 'situacao': 4}

    selected = _select_columns_for_width(
        df,
        display_map,
        available_width=10,
        essential_columns=essential,
        priority_order=priority,
        always_visible=always_visible,
        fixed_widths=fixed_widths,
    )
    assert selected[0] == '#'
    for col in always_visible:
        assert col in selected
