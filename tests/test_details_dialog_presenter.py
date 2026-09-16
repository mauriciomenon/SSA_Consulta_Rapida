from __future__ import annotations

from dataclasses import replace
from types import SimpleNamespace

import pandas as pd
import pytest

import gui.ssa.details_dialog_presenter as presenter_module
from gui.ssa.details_dialog_navigation import resolve_details_anchor
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

    @staticmethod
    def pixmap():
        return None


class _Panel:
    @staticmethod
    def width() -> int:
        return 400

    @staticmethod
    def height() -> int:
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
    @staticmethod
    def toString():
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


def test_resolve_details_anchor_accepts_ssa_context() -> None:
    assert resolve_details_anchor("ssa-context:202500777") == ("ssa", "202500777")


def test_handle_anchor_navigates_ssa_context_without_warning(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    logger = _Logger()
    presenter = DetailsDialogPresenter(
        window=SimpleNamespace(),
        target="202500001",
        series=pd.Series({"numero_ssa": "202500001"}),
        callbacks=_callbacks(logger),
    )
    presenter._style = ("#000", 10.0, 10.0, 10.0, "monospace")
    rendered = []
    monkeypatch.setattr(
        presenter,
        "_render_target",
        lambda **kwargs: rendered.append(kwargs),
    )
    widgets = SimpleNamespace()

    presenter._handle_anchor(widgets, _Url("ssa-context:202500777"))

    assert len(rendered) == 1
    assert rendered[0]["widgets"] is widgets
    assert rendered[0]["ssa_target"] == "202500777"
    assert logger.warning_messages == []


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


def _counting_callbacks(logger: _Logger, builds: dict) -> DetailsDialogCallbacks:
    def _format(*_args, **_kwargs) -> str:
        builds["count"] += 1
        return "details"

    return DetailsDialogCallbacks(
        apply_geometry=lambda *_args, **_kwargs: None,
        build_graph_html=lambda *_args, **_kwargs: "graph",
        build_mermaid_text=lambda *_args, **_kwargs: "mermaid",
        build_tree_html=lambda *_args, **_kwargs: "tree",
        collect_tree_data=lambda *_args, **_kwargs: {"children": []},
        copy_ssa_to_clipboard=lambda *_args, **_kwargs: None,
        extract_svg_markup=lambda *_args, **_kwargs: "svg",
        format_details_html=_format,
        get_series_for_ssa=lambda *_args, **_kwargs: None,
        logger=logger,
        normalize_ssa_value=lambda _window, value: str(value or ""),
        resolve_style=lambda *_args, **_kwargs: ("#000", 10.0, 10.0, 10.0, "monospace"),
        render_payload_context=lambda window, normalized, style: (
            getattr(window, "_data_uuid", None),
            getattr(window, "_data_revision", None),
            tuple(style),
            tuple(getattr(window, "_test_terms", ())),
        ),
    )


def _render_kwargs(series: pd.Series, normalized: str = "202600100") -> dict:
    return {
        "normalized": normalized,
        "series_target": series,
        "link_color": "#000",
        "font_pt": 10.0,
        "label_font_pt": 10.0,
        "tree_font_pt": 10.0,
        "font_family": "monospace",
    }


def test_window_payload_cache_shared_across_presenter_instances() -> None:
    builds = {"count": 0}
    window = SimpleNamespace(_data_uuid="d1", _data_revision=1)
    series = pd.Series({"numero_ssa": "202600100"})
    callbacks = _counting_callbacks(_Logger(), builds)
    first = DetailsDialogPresenter(
        window=window, target="202600100", series=series, callbacks=callbacks
    )
    second = DetailsDialogPresenter(
        window=window, target="202600100", series=series, callbacks=callbacks
    )

    payload_one = first._get_render_payload(**_render_kwargs(series))
    payload_two = second._get_render_payload(**_render_kwargs(series))

    assert builds["count"] == 1
    assert payload_one is payload_two


def test_window_payload_cache_invalidates_on_context_change() -> None:
    builds = {"count": 0}
    window = SimpleNamespace(_data_uuid="d1", _data_revision=1)
    series = pd.Series({"numero_ssa": "202600100", "descricao_ssa": "antes"})
    callbacks = replace(
        _counting_callbacks(_Logger(), builds),
        format_details_html=lambda _window, current, **_kwargs: current["descricao_ssa"],
    )
    presenter = DetailsDialogPresenter(
        window=window, target="202600100", series=series, callbacks=callbacks
    )

    before = presenter._get_render_payload(**_render_kwargs(series))
    window._data_revision = 2
    series = pd.Series({"numero_ssa": "202600100", "descricao_ssa": "depois"})
    after = presenter._get_render_payload(**_render_kwargs(series))

    assert before.details_html == "antes"
    assert after.details_html == "depois"


def test_window_payload_cache_is_bounded() -> None:
    builds = {"count": 0}
    window = SimpleNamespace(_data_uuid="d1", _data_revision=1)
    series = pd.Series({"numero_ssa": "1"})
    callbacks = _counting_callbacks(_Logger(), builds)
    presenter = DetailsDialogPresenter(
        window=window, target="1", series=series, callbacks=callbacks
    )

    for index in range(20):
        presenter._get_render_payload(
            **_render_kwargs(series, normalized=f"2026001{index:02d}")
        )

    cache = window._details_render_payload_cache
    assert len(cache) == presenter_module._DETAILS_PAYLOAD_CACHE_MAX_ENTRIES
    assert builds["count"] == 20


def test_render_payload_falls_back_to_instance_cache_without_context() -> None:
    window = SimpleNamespace()
    series = pd.Series({"numero_ssa": "1"})
    presenter = DetailsDialogPresenter(
        window=window, target="1", series=series, callbacks=_callbacks(_Logger())
    )

    first = presenter._get_render_payload(**_render_kwargs(series, normalized="1"))
    second = presenter._get_render_payload(**_render_kwargs(series, normalized="1"))

    assert first is second
    assert getattr(window, "_details_render_payload_cache", {}) == {}
