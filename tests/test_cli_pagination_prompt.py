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


def test_enhanced_printer_respects_narrow_terminal_width(monkeypatch):
    printer = EnhancedTablePrinter()
    monkeypatch.setattr(printer, 'get_terminal_size', lambda: (12, 70))

    def _fake_tabulate(data, headers=(), tablefmt='plain', showindex=False, **_kwargs):
        header_list = [str(item) for item in headers]
        rows = []
        for row in data.values.tolist() if hasattr(data, 'values') else data:
            rows.append([str(cell) for cell in row])
        widths = [len(header) for header in header_list]
        for row in rows:
            for idx, cell in enumerate(row):
                widths[idx] = max(widths[idx], len(cell))
        header_line = ' | '.join(header.ljust(widths[idx]) for idx, header in enumerate(header_list))
        separator = '-+-'.join('-' * widths[idx] for idx in range(len(widths)))
        body = [
            ' | '.join(cell.ljust(widths[idx]) for idx, cell in enumerate(row))
            for row in rows
        ]
        return '\n'.join([header_line, separator, *body])

    monkeypatch.setattr('interface.enhanced_table_printer.tabulate', _fake_tabulate)

    df = pd.DataFrame(
        {
            'numero_ssa': ['202500001', '202500002'],
            'situacao': ['ADM', 'APG'],
            'descricao_ssa': [
                'Descricao muito longa com varios segmentos e palavras para estourar largura de terminal estreito.',
                'Outra descricao longa para validar truncamento e wrap sem quebrar a tabela.',
            ],
            'solicitante': [
                'SOLICITANTE MUITO LONGO COM VARIAS PALAVRAS',
                'OUTRO SOLICITANTE EXTENSO',
            ],
            'setor_executor': ['MEL4', 'IEE3'],
        }
    )
    settings = {'user_preferences': {}, 'display_settings': {}}

    buffer = io.StringIO()
    monkeypatch.setattr('builtins.input', lambda _prompt='': 'q')

    with redirect_stdout(buffer):
        printer.print_dataframe_enhanced(df, {}, settings)

    lines = [line for line in buffer.getvalue().splitlines() if line]

    assert lines
    assert max(len(line) for line in lines) <= 70
