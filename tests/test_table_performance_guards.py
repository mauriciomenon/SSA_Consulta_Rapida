from __future__ import annotations

from types import SimpleNamespace
from typing import Any, cast

import pandas as pd

from gui.ssa import gui_table, table_sorting


class _DummySortWindow:
    def __init__(self, df: pd.DataFrame):
        self.df_exibido = df
        self._mixed_text_sort_cache: dict[str, Any]
        self._num_reprog_sort_cache: dict[str, Any]
        self._reset_mixed_text_sort_cache()
        self._reset_num_reprogramacoes_sort_cache()

    @staticmethod
    def _empty_cache(*, column_name: str | None = None) -> dict[str, Any]:
        cache: dict[str, Any] = {
            "source_marker": None,
            "source_len": 0,
            "keys_df": None,
        }
        if column_name is not None:
            cache["column_name"] = column_name
        return cache

    def _reset_mixed_text_sort_cache(self) -> None:
        self._mixed_text_sort_cache = self._empty_cache(column_name=None)
        self._mixed_text_sort_cache.update(
            {
                "column_name": None,
            }
        )

    def _reset_num_reprogramacoes_sort_cache(self) -> None:
        self._num_reprog_sort_cache = self._empty_cache()


class _RecordingWidthManager:
    def __init__(self):
        self.row_count = None
        self.column_order = None

    def compute_optimal_widths(self, *, df, available_width, column_order):
        self.row_count = len(df.index)
        self.column_order = list(column_order)
        return {column: 100 for column in column_order}


def test_compute_widths_passes_sample_for_large_dataframe_to_width_manager():
    rows = 2500
    df = pd.DataFrame(
        {
            "numero_ssa": range(rows),
            "descricao_ssa": [f"Descricao {i}" for i in range(rows)],
        }
    )
    width_manager = _RecordingWidthManager()

    widths = gui_table._compute_widths_for_df(
        df,
        ["numero_ssa", "descricao_ssa"],
        width_manager,
        {},
        {},
        widget_width=1200,
        window_width=1300,
    )

    assert set(widths) == {"#", "numero_ssa", "descricao_ssa"}
    assert widths["#"] == 100
    assert widths["numero_ssa"] >= 100
    assert widths["descricao_ssa"] >= 100
    assert width_manager.row_count == 1000
    assert width_manager.column_order == ["#", "numero_ssa", "descricao_ssa"]


def test_render_marker_sample_is_reused_for_same_page(monkeypatch):
    df = pd.DataFrame({"numero_ssa": [1, 2, 3], "situacao": ["A", "B", "C"]})
    paginator = SimpleNamespace(current_page=1, page_size=50)
    window = SimpleNamespace(
        _data_uuid="dataset-1",
        _data_revision=7,
        paginator=paginator,
    )
    calls = {"count": 0}
    original_builder = gui_table._build_render_marker_sample

    def _counted_builder(frame: pd.DataFrame):
        calls["count"] += 1
        return original_builder(frame)

    monkeypatch.setattr(gui_table, "_build_render_marker_sample", _counted_builder)

    first = gui_table._get_cached_render_marker_sample(window, df)
    second = gui_table._get_cached_render_marker_sample(window, df)

    assert first == second
    assert calls["count"] == 1


def test_mixed_text_sort_does_not_retain_cache_above_row_limit():
    rows = table_sorting.MAX_SORT_CACHE_ROWS + 1
    df = pd.DataFrame({"situacao": ["B", "A"] * ((rows // 2) + 1)}).iloc[:rows]
    window = _DummySortWindow(df)
    window._mixed_text_sort_cache = {
        "column_name": "situacao",
        "source_marker": ("old-token",),
        "source_len": 5,
        "keys_df": pd.DataFrame({"stale": [1]}),
    }

    table_sorting.sort_mixed_text_column_robust(window, "situacao", ascending=True)

    assert window._mixed_text_sort_cache["keys_df"] is None
    assert window._mixed_text_sort_cache["source_len"] == 0


def test_mixed_text_sort_cache_token_changes_after_sampled_value_mutation():
    df = pd.DataFrame({"situacao": ["A", "B", "C"]})
    first = table_sorting._get_sort_cache_source_marker(df, ("situacao",))
    df.loc[1, "situacao"] = "Z"
    second = table_sorting._get_sort_cache_source_marker(df, ("situacao",))

    assert first != second


def test_mixed_text_sort_treats_scientific_notation_as_numeric():
    keys = table_sorting.build_mixed_text_sort_keys(
        pd.Series(["1e3", "2.5E-2", "A"], dtype="object")
    )

    assert keys["__mixed_bucket_order"].tolist() == [1, 1, 2]


def test_num_reprogramacoes_sort_does_not_retain_cache_above_row_limit():
    rows = table_sorting.MAX_SORT_CACHE_ROWS + 1
    df = pd.DataFrame({"num_reprogramacoes": list(range(rows))})
    window = _DummySortWindow(df)
    window._num_reprog_sort_cache = {
        "source_marker": ("old-token",),
        "source_len": 5,
        "keys_df": pd.DataFrame({"stale": [1]}),
    }

    table_sorting.sort_num_reprogramacoes_robust(window, ascending=True)

    assert window._num_reprog_sort_cache["keys_df"] is None
    assert window._num_reprog_sort_cache["source_len"] == 0


def test_best_fit_visible_columns_skips_hash_column_only():
    calls: list[int] = []

    class _TableWidget:
        def columnCount(self):
            return 3

    window = SimpleNamespace(
        table_widget=_TableWidget(),
        _current_display_columns=["numero_ssa", "situacao", "#"],
    )

    def _best_fit(column_index: int) -> bool:
        calls.append(column_index)
        return True

    window._best_fit_column_width = _best_fit

    from gui.gui_ssa import SSAMainWindow

    SSAMainWindow.best_fit_visible_columns(cast(Any, window))

    assert calls == [0, 1]
