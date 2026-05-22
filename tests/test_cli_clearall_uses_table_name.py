from __future__ import annotations

import pandas as pd

from interface import cli


def test_handle_clear_all_filters_uses_provided_table_name(monkeypatch):
    captured = {"query": None}
    base_df = pd.DataFrame({"numero_ssa": ["202500001"]})
    stack = [(pd.DataFrame({"numero_ssa": ["202500002"]}), ["term"])]

    def _fake_query_db(_db_path, _where, query):
        captured["query"] = query
        return base_df

    monkeypatch.setattr(cli, "query_db", _fake_query_db)
    monkeypatch.setattr(cli, "_render_single_page", lambda *args, **kwargs: None)
    monkeypatch.setattr(cli, "_reset_pagination_state", lambda *_args, **_kwargs: None)

    cli._handle_clear_all_filters("dummy.db", "ssas", stack, {}, {}, {})

    assert captured["query"] is not None
    assert 'FROM "ssa_table"' in captured["query"]
    assert stack[-1][0] is base_df
    assert stack[-1][1] == []
