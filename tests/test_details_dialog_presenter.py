from __future__ import annotations

from types import SimpleNamespace

import pandas as pd

from gui.ssa.details_dialog_presenter import (
    DetailsDialogCallbacks,
    DetailsDialogPresenter,
    DetailsDialogRenderPayload,
)


class _Logger:
    def __init__(self) -> None:
        self.debug_messages: list[str] = []

    def debug(self, message: str, *args) -> None:
        self.debug_messages.append(message % args if args else message)


def _callbacks(logger: _Logger) -> DetailsDialogCallbacks:
    return DetailsDialogCallbacks(
        apply_geometry=lambda *_args, **_kwargs: None,
        build_graph_html=lambda *_args, **_kwargs: "",
        build_mermaid_text=lambda *_args, **_kwargs: "",
        build_tree_html=lambda *_args, **_kwargs: "",
        collect_tree_data=lambda *_args, **_kwargs: {},
        copy_ssa_to_clipboard=lambda *_args, **_kwargs: None,
        extract_svg_markup=lambda *_args, **_kwargs: "",
        format_details_html=lambda *_args, **_kwargs: "",
        get_series_for_ssa=lambda *_args, **_kwargs: None,
        logger=logger,
        normalize_ssa_value=lambda _window, value: str(value or ""),
        resolve_style=lambda *_args, **_kwargs: ("#000", 10.0, 10.0, 10.0, "monospace"),
    )


def test_forget_dialog_clears_presenter_references() -> None:
    logger = _Logger()
    window = SimpleNamespace(_open_details_dialogs=[])
    dialog = SimpleNamespace()
    widgets = SimpleNamespace(dialog=dialog)
    presenter = DetailsDialogPresenter(
        window=window,
        target="1",
        series=pd.Series({"numero_ssa": "1"}),
        callbacks=_callbacks(logger),
    )
    presenter._widgets = widgets
    presenter._render_cache["1"] = DetailsDialogRenderPayload(
        details_html="details",
        graph_html="graph",
        graph_svg="<svg></svg>",
        mermaid_text="graph TD",
        tree_html="tree",
    )
    presenter._last_graph_render_key = ("<svg></svg>", 1, 1)
    dialog._ssa_details_dialog_presenter = presenter
    window._open_details_dialogs.append(dialog)

    presenter._forget_dialog(dialog)

    assert window._open_details_dialogs == []
    assert not hasattr(dialog, "_ssa_details_dialog_presenter")
    assert presenter._widgets is None
    assert presenter._render_cache == {}
    assert presenter._last_graph_render_key is None
