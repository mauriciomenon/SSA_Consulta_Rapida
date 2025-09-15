import pandas as pd
from interface.table_printer import _sanitize_and_truncate, MIN_TRUNCATE_WIDTH


def test_truncation_respects_min_width():
    # DataFrame with long description columns
    df = pd.DataFrame({
        'descricao_ssa': ['X' * (MIN_TRUNCATE_WIDTH + 50)],
        'descricao_execucao': ['Y' * (MIN_TRUNCATE_WIDTH + 80)],
        'outra_coluna': ['Z' * 10],
    })
    # display_cols chooses the two description columns only to exercise logic
    truncated = _sanitize_and_truncate(df.copy(), ['descricao_ssa', 'descricao_execucao'], term_width=40)
    for col in ['descricao_ssa', 'descricao_execucao']:
        val = truncated.iloc[0][col]
        assert isinstance(val, str)
        # Should end with ellipsis due to truncation
        assert val.endswith('...')
        # Effective visible length (without ellipsis) must be at least MIN_TRUNCATE_WIDTH - 3
        core = val[:-3]
        assert len(core) >= MIN_TRUNCATE_WIDTH - 3
        # And total including ellipsis should not exceed large original
        assert len(val) >= MIN_TRUNCATE_WIDTH  # safety lower bound
