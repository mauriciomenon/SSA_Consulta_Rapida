"""Facade contract tests for gui details forwarding."""

import os
import sys
from typing import Any, cast

import pytest

pytest.importorskip(
    "PyQt6", reason="Dependencia PyQt6 indisponivel no ambiente de teste"
)

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from gui.gui_ssa import SSAMainWindow  # noqa: E402
from gui.ssa import gui_details as ssa_gui_details  # noqa: E402


def test_format_details_html_facade_forwards_label_font_size_pt(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: dict[str, object] = {}

    def _fake_format_details_html(
        window,
        series,
        highlight_search_terms=False,
        font_size_pt=None,
        linkify=False,
        label_font_size_pt=None,
    ):
        calls["window"] = window
        calls["series"] = series
        calls["highlight_search_terms"] = highlight_search_terms
        calls["font_size_pt"] = font_size_pt
        calls["linkify"] = linkify
        calls["label_font_size_pt"] = label_font_size_pt
        return "ok"

    monkeypatch.setattr(
        ssa_gui_details, "_format_details_html", _fake_format_details_html
    )

    dummy_window = cast(Any, object())
    payload = {"numero_ssa": "202500001"}
    result = SSAMainWindow._format_details_html(
        dummy_window,
        payload,
        highlight_search_terms=True,
        font_size_pt=12.0,
        linkify=True,
        label_font_size_pt=11.0,
    )

    assert result == "ok"
    assert calls["window"] is dummy_window
    assert calls["series"] == payload
    assert calls["highlight_search_terms"] is True
    assert calls["font_size_pt"] == 12.0
    assert calls["linkify"] is True
    assert calls["label_font_size_pt"] == 11.0
