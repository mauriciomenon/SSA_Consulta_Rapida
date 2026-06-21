from __future__ import annotations

from types import SimpleNamespace

import pandas as pd
import pytest

import gui.ssa.details_dialog_presenter as presenter_module
from gui.ssa.details_dialog_presenter import (
    DetailsDialogCallbacks,
    DetailsDialogPresenter,
    DetailsDialogRenderPayload,
)


class _Logger:
    def __init__(self) -> None:
        self.debug_messages: list[str] = []
        self.warning_messages: list[str] = []

    def debug(self, message: str, *args) -> None:
        self.debug_messages.append(message % args if args else message)

    def warning(self, message: str, *args) -> None:
        self.warning_messages.append(message % args if args else message)


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


class _GraphLabel:
    def __init__(self) -> None:
        self.cleared = False
        self.svg_markup = "<svg>old</svg>"
        self.hitboxes = [("1", 0.0, 0.0, 1.0, 1.0)]

    def clear(self) -> None:
        self.cleared = True

    def clear_graph_svg_markup(self) -> None:
        self.svg_markup = ""

    def set_ssa_hitboxes(self, hitboxes) -> None:
        self.hitboxes = list(hitboxes)

    def pixmap(self):
        return None


class _Panel:
    def width(self) -> int:
        return 400

    def height(self) -> int:
        return 300


def test_render_graph_pixmap_failure_clears_stale_label_state(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    logger = _Logger()
    presenter = DetailsDialogPresenter(
        window=SimpleNamespace(),
        target="1",
        series=pd.Series({"numero_ssa": "1"}),
        callbacks=_callbacks(logger),
    )
    presenter.export_state["svg"] = "<svg>new</svg>"
    presenter._last_graph_render_key = ("<svg>old</svg>", 400, 300)
    graph_label = _GraphLabel()
    widgets = SimpleNamespace(
        tree_graph_label=graph_label,
        tree_graph_panel=_Panel(),
    )
    monkeypatch.setattr(
        presenter_module,
        "render_graph_svg_pixmap",
        lambda **_kwargs: False,
    )

    assert presenter._render_graph_pixmap(widgets, svg_render_deps=object()) is False

    assert presenter._last_graph_render_key is None
    assert graph_label.cleared is True
    assert graph_label.svg_markup == ""
    assert graph_label.hitboxes == []


class _BrokenUrl:
    def toString(self):
        raise RuntimeError("bad url")


def test_handle_anchor_logs_invalid_url() -> None:
    logger = _Logger()
    presenter = DetailsDialogPresenter(
        window=SimpleNamespace(),
        target="1",
        series=pd.Series({"numero_ssa": "1"}),
        callbacks=_callbacks(logger),
    )

    presenter._handle_anchor(SimpleNamespace(), _BrokenUrl())

    assert logger.warning_messages == [
        "Failed to parse details dialog anchor: bad url"
    ]


class _Url:
    def __init__(self, href: str) -> None:
        self.href = href

    def toString(self) -> str:
        return self.href


def test_handle_anchor_logs_unknown_action(monkeypatch: pytest.MonkeyPatch) -> None:
    logger = _Logger()
    presenter = DetailsDialogPresenter(
        window=SimpleNamespace(),
        target="1",
        series=pd.Series({"numero_ssa": "1"}),
        callbacks=_callbacks(logger),
    )
    monkeypatch.setattr(
        presenter_module,
        "resolve_details_anchor",
        lambda _href: ("unexpected", "2"),
    )

    presenter._handle_anchor(SimpleNamespace(), _Url("ssa:2"))

    assert logger.warning_messages == [
        "Unknown details dialog anchor action: unexpected"
    ]
