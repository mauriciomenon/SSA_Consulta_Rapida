import pandas as pd

from interface.cli import (
    _handle_sort_by_name,
    _handle_remove_filter,
    _handle_list_columns,
)
from core.app_logic import filter_dataframe


def test_sort_by_name_ascending_descending(capsys):
    df = pd.DataFrame({
        'a': [2, 1, 3],
        'b': ['x', 'y', 'z']
    })
    display_map = {'a': 'Alpha', 'b': 'Beta'}
    settings = {}
    results_stack = [(df, [])]

    # Ascendente por nome de exibição
    _handle_sort_by_name(['-ordn', 'Alpha'], results_stack, display_map, settings, ascending=True)
    sorted_df, terms = results_stack[-1]
    assert sorted_df['a'].tolist() == [1, 2, 3]

    # Descendente por nome interno
    results_stack = [(df, [])]
    _handle_sort_by_name(['-ordni', 'a'], results_stack, display_map, settings, ascending=False)
    sorted_df, terms = results_stack[-1]
    assert sorted_df['a'].tolist() == [3, 2, 1]


def test_remove_filter_term_and_reapply(capsys):
    base_df = pd.DataFrame({
        'col': ['foo', 'bar', 'foobar', 'baz']
    })
    display_map = {'col': 'Col'}
    settings = {}

    initial = (base_df, [])
    filtered = filter_dataframe(base_df, ['foo', 'baz'])
    results_stack = [initial, (filtered, ['foo', 'baz'])]

    # Remove 'foo' (resta 'baz')
    _handle_remove_filter(['-x', 'foo'], results_stack, display_map, settings)
    new_df, new_terms = results_stack[-1]
    assert new_terms == ['baz']
    assert new_df.reset_index(drop=True).equals(
        filter_dataframe(base_df, ['baz']).reset_index(drop=True)
    )

    # Remove último termo -> volta ao estado inicial
    _handle_remove_filter(['-x', 'baz'], results_stack, display_map, settings)
    top_df, top_terms = results_stack[-1]
    assert top_terms == []
    assert top_df.reset_index(drop=True).equals(base_df.reset_index(drop=True))


def test_list_columns_outputs_indices(capsys):
    df = pd.DataFrame({
        'a': [1],
        'b': [2],
        'c': [3],
    })
    display_map = {'a': 'Alpha', 'b': 'Beta', 'c': 'Gamma'}
    _handle_list_columns(df, display_map)
    captured = capsys.readouterr().out
    assert '1:' in captured
    assert '2:' in captured
    assert '3:' in captured
    assert 'Alpha' in captured and 'Beta' in captured and 'Gamma' in captured
