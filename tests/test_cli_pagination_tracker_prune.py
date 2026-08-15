from __future__ import annotations

import pandas as pd

from interface import cli


def test_prune_pagination_tracker_keeps_only_active_stack_entries():
    cli.CLI_PAGINATION_TRACKER.clear()
    base_df = pd.DataFrame({"numero_ssa": ["202500001"]})
    top_df = pd.DataFrame({"numero_ssa": ["202500002"]})
    orphan_df = pd.DataFrame({"numero_ssa": ["202500003"]})

    cli._reset_pagination_state(base_df)
    cli._reset_pagination_state(top_df)
    cli._reset_pagination_state(orphan_df)

    cli._prune_pagination_tracker_for_stack(
        [(base_df, []), (top_df, ["a"])], force=True
    )

    base_key = cli._pagination_state_key_for_df(base_df)
    top_key = cli._pagination_state_key_for_df(top_df)
    orphan_key = cli._pagination_state_key_for_df(orphan_df)
    assert base_key in cli.CLI_PAGINATION_TRACKER
    assert top_key in cli.CLI_PAGINATION_TRACKER
    assert orphan_key not in cli.CLI_PAGINATION_TRACKER


def test_remove_filter_prunes_replaced_top_state(monkeypatch):
    cli.CLI_PAGINATION_TRACKER.clear()
    base_df = pd.DataFrame({"numero_ssa": ["202500001"]})
    current_df = pd.DataFrame({"numero_ssa": ["202500002"]})
    new_df = pd.DataFrame({"numero_ssa": ["202500003"]})

    results_stack = [
        (base_df, ["a"]),
        (current_df, ["a", "b"]),
    ]

    cli._reset_pagination_state(base_df)
    cli._reset_pagination_state(current_df)

    monkeypatch.setattr(cli, "filter_dataframe", lambda _df, _terms: new_df)
    monkeypatch.setattr(cli, "_render_single_page", lambda *args, **kwargs: None)

    cli._handle_remove_filter(["-x", "b"], results_stack, {}, {}, {})

    base_key = cli._pagination_state_key_for_df(base_df)
    current_key = cli._pagination_state_key_for_df(current_df)
    new_key = cli._pagination_state_key_for_df(new_df)
    assert base_key in cli.CLI_PAGINATION_TRACKER
    assert new_key in cli.CLI_PAGINATION_TRACKER
    assert current_key not in cli.CLI_PAGINATION_TRACKER


def test_pagination_state_survives_dataframe_copy_via_attrs_key():
    cli.CLI_PAGINATION_TRACKER.clear()
    df = pd.DataFrame({"numero_ssa": ["202500001"]})
    cli._update_pagination_state(df, {"next_page": 3, "total_pages": 10})

    df_copy = df.copy()
    assert cli._next_page_for(df_copy) == 3


def test_next_page_for_missing_next_page_restarts_from_first_page():
    cli.CLI_PAGINATION_TRACKER.clear()
    df = pd.DataFrame({"numero_ssa": ["202500001"]})
    cli._update_pagination_state(
        df,
        {
            "total_pages": 5,
            "rendered_pages": 2,
            "page_size": 20,
        },
    )

    assert cli._next_page_for(df) == 0


def test_last_rendered_page_for_missing_rendered_pages_restarts_from_first_page():
    cli.CLI_PAGINATION_TRACKER.clear()
    df = pd.DataFrame({"numero_ssa": ["202500001"]})
    cli._update_pagination_state(
        df,
        {
            "next_page": None,
            "total_pages": 5,
            "page_size": 20,
        },
    )

    assert cli._last_rendered_page_for(df) == 0


def test_last_rendered_page_for_finished_state_uses_rendered_page_count():
    cli.CLI_PAGINATION_TRACKER.clear()
    df = pd.DataFrame({"numero_ssa": ["202500001"]})
    cli._update_pagination_state(
        df,
        {
            "next_page": None,
            "total_pages": 5,
            "rendered_pages": 2,
            "page_size": 20,
        },
    )

    assert cli._last_rendered_page_for(df) == 3
