from __future__ import annotations

import pandas as pd

from interface import cli


def test_prune_pagination_tracker_keeps_only_active_stack_entries():
    cli.CLI_PAGINATION_TRACKER.clear()
    base_df = pd.DataFrame({"numero_ssa": ["202500001"]})
    top_df = pd.DataFrame({"numero_ssa": ["202500002"]})
    orphan_df = pd.DataFrame({"numero_ssa": ["202500003"]})

    cli.CLI_PAGINATION_TRACKER[id(base_df)] = {"next_page": 0}
    cli.CLI_PAGINATION_TRACKER[id(top_df)] = {"next_page": 1}
    cli.CLI_PAGINATION_TRACKER[id(orphan_df)] = {"next_page": 9}

    cli._prune_pagination_tracker_for_stack([(base_df, []), (top_df, ["a"])], force=True)

    assert id(base_df) in cli.CLI_PAGINATION_TRACKER
    assert id(top_df) in cli.CLI_PAGINATION_TRACKER
    assert id(orphan_df) not in cli.CLI_PAGINATION_TRACKER


def test_remove_filter_prunes_replaced_top_state(monkeypatch):
    cli.CLI_PAGINATION_TRACKER.clear()
    base_df = pd.DataFrame({"numero_ssa": ["202500001"]})
    current_df = pd.DataFrame({"numero_ssa": ["202500002"]})
    new_df = pd.DataFrame({"numero_ssa": ["202500003"]})

    results_stack = [
        (base_df, ["a"]),
        (current_df, ["a", "b"]),
    ]

    cli.CLI_PAGINATION_TRACKER[id(base_df)] = {"next_page": 0}
    cli.CLI_PAGINATION_TRACKER[id(current_df)] = {"next_page": 5}

    monkeypatch.setattr(cli, "filter_dataframe", lambda _df, _terms: new_df)
    monkeypatch.setattr(cli, "_render_single_page", lambda *args, **kwargs: None)

    cli._handle_remove_filter(["-x", "b"], results_stack, {}, {}, {})

    assert id(base_df) in cli.CLI_PAGINATION_TRACKER
    assert id(new_df) in cli.CLI_PAGINATION_TRACKER
    assert id(current_df) not in cli.CLI_PAGINATION_TRACKER
