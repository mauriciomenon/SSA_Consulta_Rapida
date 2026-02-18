from __future__ import annotations

import io
from contextlib import redirect_stdout
import types
import sys

import pandas as pd

if 'tabulate' not in sys.modules:
    fake_tabulate = types.ModuleType('tabulate')

    def _tabulate(*args, **kwargs):
        data = args[0]
        if isinstance(data, pd.DataFrame):
            return data.to_string(index=False)
        return str(data)

    setattr(fake_tabulate, "tabulate", _tabulate)
    sys.modules['tabulate'] = fake_tabulate

from interface.enhanced_table_printer import EnhancedTablePrinter


def test_paginated_prompt_shows_updated_shortcuts(monkeypatch):
    printer = EnhancedTablePrinter()
    monkeypatch.setattr(printer, 'get_terminal_size', lambda: (6, 120))

    df = pd.DataFrame({
        '#': [1, 2, 3],
        'numero_ssa': ['202500001', '202500002', '202500003'],
    })
    widths = {'#': 3, 'numero_ssa': 12}
    settings = {'user_preferences': {}, 'display_settings': {}}

    inputs = iter(['l', 'q'])
    prompts: list[str] = []

    def fake_input(prompt: str) -> str:
        prompts.append(prompt)
        return next(inputs)

    monkeypatch.setattr('builtins.input', fake_input)

    buffer = io.StringIO()
    with redirect_stdout(buffer):
        printer._render_paginated(
            df,
            widths,
            settings,
            highlight_terms=None,
            filter_terms=['svp'],
        )

    output = buffer.getvalue()

    assert prompts, "Nenhum prompt foi exibido durante a paginação"
    first_prompt = prompts[0]
    assert "'z': até o final" in first_prompt
    assert "'l': listar filtros" in first_prompt
    assert '+filtro' not in first_prompt
    assert 'Filtros ativos: svp' in output
    assert 'Comando inválido' not in output
