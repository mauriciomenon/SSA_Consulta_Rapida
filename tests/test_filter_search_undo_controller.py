from __future__ import annotations

from types import SimpleNamespace

import pandas as pd

from gui.ssa.filter_search_undo_controller import restore_filter_search_state


def test_restore_empty_search_uses_isolated_dataframe_copy():
    df = pd.DataFrame({"numero_ssa": ["202600001", "202600002"]})
    df.attrs["source"] = "complete"
    window = SimpleNamespace(
        df_completo=df,
        _pending_search_display="old",
        _set_search_text_across_tabs=lambda _text: None,
    )

    restored = restore_filter_search_state(
        window,
        {"search_text": "", "pending_search_display": None},
    )

    assert restored == ""
    assert window._df_last_search_filtered is not df
    assert window._df_last_search_filtered.equals(df)
    assert window._df_last_search_filtered.attrs == {"source": "complete"}
    df.loc[0, "numero_ssa"] = "MUTATED"
    assert window._df_last_search_filtered["numero_ssa"].tolist() == [
        "202600001",
        "202600002",
    ]
