from __future__ import annotations

import json
import logging
import sqlite3
from contextlib import closing
from pathlib import Path
from typing import Any

import pytest

pytest.importorskip(
    "PyQt6", reason="Dependencia PyQt6 indisponivel no ambiente de teste"
)
from PyQt6.QtCore import QEvent, QPoint, QPointF, Qt
from PyQt6.QtGui import QMouseEvent
from PyQt6.QtWidgets import QApplication

from gui.gui_config import (
    COLUMN_HEADER_LABEL_VARIANTS,
    DEFAULT_COLUMN_WIDTHS_BY_PLATFORM,
    DEFAULT_GUI_MAIN_PREFERENCES,
)
from gui.ssa.table_context_menu import (
    TableContextMenuCallbacks,
    show_table_context_menu,
)
from gui.workers.data_loader_worker import DataLoaderWorker


@pytest.fixture(scope="module", autouse=True)
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


def _run_loader(db_path: Path):
    payloads: list[Any] = []
    worker = DataLoaderWorker(str(db_path), "ssa_table")
    worker.data_prepared.connect(payloads.append)
    worker.run()
    assert len(payloads) == 1
    return payloads[0].complete


def test_loader_adds_descendants_count_for_each_ssa(tmp_path):
    db_path = tmp_path / "derivadas_count.db"
    with closing(sqlite3.connect(db_path)) as conn:
        conn.execute("CREATE TABLE ssa_table (numero_ssa TEXT, situacao TEXT)")
        conn.executemany(
            "INSERT INTO ssa_table VALUES (?, ?)",
            [("100", "APV"), ("101", "APV"), ("102", "APV")],
        )
        conn.execute(
            """
            CREATE TABLE ssa_derivada_summary (
                ssa TEXT PRIMARY KEY,
                descendants_count INTEGER NOT NULL
            )
            """
        )
        conn.executemany(
            "INSERT INTO ssa_derivada_summary VALUES (?, ?)",
            [("100", 2), ("101", 1), ("102", 0)],
        )
        conn.commit()

    loaded = _run_loader(db_path)

    assert dict(
        zip(loaded["numero_ssa"].astype(str), loaded["qtd_derivadas"], strict=True)
    ) == {"100": 2, "101": 1, "102": 0}


def test_loader_uses_zero_when_derivadas_summary_is_missing(tmp_path, caplog):
    db_path = tmp_path / "legacy_without_derivadas_summary.db"
    with closing(sqlite3.connect(db_path)) as conn:
        conn.execute("CREATE TABLE ssa_table (numero_ssa TEXT, situacao TEXT)")
        conn.execute("INSERT INTO ssa_table VALUES ('100', 'APV')")
        conn.commit()

    with caplog.at_level(logging.WARNING):
        loaded = _run_loader(db_path)

    assert loaded["qtd_derivadas"].tolist() == [0]
    assert "ssa_derivada_summary" in caplog.text


def test_derivadas_column_defaults_and_planning_visibility_are_canonical():
    display = DEFAULT_GUI_MAIN_PREFERENCES["display_columns"]
    hidden = DEFAULT_GUI_MAIN_PREFERENCES["hidden_columns"]

    assert display.index("qtd_derivadas") == display.index("solicitante") + 1
    assert "grau_prioridade_planejamento" not in display
    assert "grau_prioridade_planejamento" in hidden
    assert DEFAULT_GUI_MAIN_PREFERENCES["column_display_names"]["qtd_derivadas"] == (
        "Qtd. Der."
    )
    assert COLUMN_HEADER_LABEL_VARIANTS["qtd_derivadas"] == {
        "short": "Der.",
        "medium": "Qtd. Der.",
        "long": "Qtd. Derivadas",
    }
    assert all(
        widths["qtd_derivadas"] == 48
        for widths in DEFAULT_COLUMN_WIDTHS_BY_PLATFORM.values()
    )


def test_versioned_preferences_match_requested_column_defaults():
    project_root = Path(__file__).resolve().parents[1]
    versioned_preferences = project_root / "config" / "gui_main_preferences.json.example"
    payload = json.loads(versioned_preferences.read_text("utf-8"))
    display = payload["display_columns"]
    hidden = payload["hidden_columns"]
    assert display.index("qtd_derivadas") == display.index("solicitante") + 1
    assert "grau_prioridade_planejamento" not in display
    assert "grau_prioridade_planejamento" in hidden
    assert payload["column_display_names"]["qtd_derivadas"] == "Qtd. Der."
    assert payload["column_widths"]["qtd_derivadas"] == 48
    assert all(
        widths["qtd_derivadas"] == 48
        for widths in payload["column_widths_by_platform"].values()
    )


class _Signal:
    def __init__(self):
        self.callback = None

    def connect(self, callback):
        self.callback = callback

    def emit(self):
        assert self.callback is not None
        self.callback()


class _Action:
    def __init__(self, label, _parent=None):
        self.label = str(label)
        self.triggered = _Signal()


class _Menu:
    trigger_prefix = ""
    last_actions: list[_Action] = []

    def __init__(self, _parent=None):
        self.actions: list[_Action] = []
        type(self).last_actions = self.actions

    def addAction(self, action):
        self.actions.append(action)
        return action

    def addSeparator(self):
        return None

    def exec(self, _global_position):
        for action in self.actions:
            if action.label.startswith(type(self).trigger_prefix):
                action.triggered.emit()
                return action
        return None


class _Point:
    def __init__(self, x: int, y: int):
        self._x = x
        self._y = y

    def x(self):
        return self._x

    def y(self):
        return self._y


class _Item:
    def __init__(self, row: int, column: int, text: str):
        self._row = row
        self._column = column
        self._text = text

    def row(self):
        return self._row

    def column(self):
        return self._column

    def text(self):
        return self._text


class _HeaderItem:
    def __init__(self, text: str):
        self._text = text

    def text(self):
        return self._text


class _Viewport:
    def __init__(self):
        self.mapped = []

    def mapToGlobal(self, position):
        self.mapped.append(position)
        return position


class _Table:
    def __init__(self, *, row: int, column: int, item: _Item | None):
        self._row = row
        self._column = column
        self._item = item
        self._viewport = _Viewport()

    def rowAt(self, _y):
        return self._row

    def columnAt(self, _x):
        return self._column

    def item(self, row, column):
        if self._item is None:
            return None
        if row == self._item.row() and column == self._item.column():
            return self._item
        return None

    def horizontalHeaderItem(self, column):
        return _HeaderItem(f"Coluna {column}")

    def viewport(self):
        return self._viewport

    def mapToGlobal(self, _position):
        raise AssertionError("O menu deve mapear a posicao pelo viewport")


def _callbacks(events, *, get_series=None):
    return TableContextMenuCallbacks(
        copy_cell_value=lambda value: events.append(("cell", value)),
        copy_row_data=lambda row: events.append(("row", row)),
        export_current_list_txt=lambda: events.append(("export", None)),
        get_series_from_row=get_series or (lambda row: {"numero_ssa": str(row)}),
        open_details_dialog=lambda *_args: None,
        jump_to_ssa=lambda *_args: None,
        filter_by_derivadas=lambda *_args: None,
        clear_derivadas_filter=lambda: None,
        remove_column_by_index=lambda column: events.append(("hide", column)),
        auto_fit_column=lambda column: events.append(("fit", column)),
        last_derivada_origem=lambda: None,
    )


@pytest.mark.parametrize(
    ("action_prefix", "expected"),
    [
        ("Copiar Valor", ("cell", "clicada")),
        ("Copiar Linha", ("row", 3)),
    ],
)
def test_context_menu_uses_clicked_cell_instead_of_current_selection(
    action_prefix, expected
):
    events = []
    table = _Table(row=3, column=2, item=_Item(3, 2, "clicada"))
    _Menu.trigger_prefix = action_prefix

    show_table_context_menu(
        object(),
        table,
        _Point(20, 30),
        _callbacks(events),
        action_cls=_Action,
        menu_cls=_Menu,
    )

    assert expected in events
    assert table.viewport().mapped


def test_context_menu_hides_column_from_blank_area_below_rows():
    events = []
    table = _Table(row=-1, column=4, item=None)
    _Menu.trigger_prefix = "Ocultar Coluna"

    show_table_context_menu(
        object(),
        table,
        _Point(40, 999),
        _callbacks(events),
        action_cls=_Action,
        menu_cls=_Menu,
    )

    assert events == [("hide", 4)]
    labels = [action.label for action in _Menu.last_actions]
    assert not any(label.startswith("Copiar") for label in labels)


def test_context_menu_omits_cell_copy_when_item_is_missing():
    events = []
    table = _Table(row=2, column=3, item=None)
    _Menu.trigger_prefix = "Ocultar Coluna"

    show_table_context_menu(
        object(),
        table,
        _Point(30, 20),
        _callbacks(events),
        action_cls=_Action,
        menu_cls=_Menu,
    )

    assert events == [("hide", 3)]
    assert not any(
        action.label == "Copiar Valor da Celula" for action in _Menu.last_actions
    )


def test_context_menu_keeps_column_actions_when_row_lookup_fails(caplog):
    events = []
    table = _Table(row=2, column=3, item=_Item(2, 3, "valor"))
    _Menu.trigger_prefix = "Ocultar Coluna"

    def fail_row_lookup(_row):
        raise RuntimeError("falha controlada")

    with caplog.at_level(logging.WARNING):
        show_table_context_menu(
            object(),
            table,
            _Point(30, 20),
            _callbacks(events, get_series=fail_row_lookup),
            action_cls=_Action,
            menu_cls=_Menu,
        )

    assert events == [("hide", 3)]
    assert "falha controlada" in caplog.text


def test_context_menu_does_not_hide_synthetic_hash_column():
    events = []
    table = _Table(row=-1, column=0, item=None)
    _Menu.trigger_prefix = "Ocultar Coluna"
    _Menu.last_actions = []

    show_table_context_menu(
        object(),
        table,
        _Point(1, 999),
        _callbacks(events),
        action_cls=_Action,
        menu_cls=_Menu,
    )

    assert events == []
    assert not any(
        action.label.startswith("Ocultar Coluna") for action in _Menu.last_actions
    )


def test_main_window_respects_hidden_required_columns(monkeypatch):
    from gui import gui_ssa

    monkeypatch.setattr(gui_ssa.SSAMainWindow, "load_data", lambda _self: None)
    display = ["numero_ssa", "qtd_derivadas"]
    hidden = ["grau_prioridade_planejamento"]
    monkeypatch.setitem(gui_ssa.GUI_MAIN_PREFERENCES, "display_columns", display)
    monkeypatch.setitem(gui_ssa.GUI_MAIN_PREFERENCES, "hidden_columns", hidden)

    window = gui_ssa.SSAMainWindow()
    try:
        assert "qtd_derivadas" in window.visible_columns
        assert "grau_prioridade_planejamento" not in window.visible_columns
    finally:
        window.close()


def test_header_context_menu_hides_clicked_column(monkeypatch):
    from gui import gui_ssa

    monkeypatch.setattr(gui_ssa.SSAMainWindow, "load_data", lambda _self: None)
    window = gui_ssa.SSAMainWindow()
    hidden = []
    try:
        window.visible_columns = ["numero_ssa", "situacao"]
        window._current_display_columns = ["#", "numero_ssa", "situacao"]
        window.table_widget.setColumnCount(3)
        window.table_widget.setHorizontalHeaderLabels(["#", "Numero SSA", "Sit."])
        monkeypatch.setattr(gui_ssa, "QAction", _Action)
        monkeypatch.setattr(gui_ssa, "QMenu", _Menu)
        monkeypatch.setattr(
            window, "remove_column_by_index", lambda column: hidden.append(column)
        )
        _Menu.trigger_prefix = "Ocultar Coluna"
        header = window.table_widget.horizontalHeader()
        position = QPoint(header.sectionPosition(1) + 2, 2)

        window.show_header_context_menu(position)

        assert hidden == [1]
    finally:
        window.close()


def test_header_right_click_is_not_dispatched_by_event_filter(monkeypatch):
    from gui import gui_ssa

    monkeypatch.setattr(gui_ssa.SSAMainWindow, "load_data", lambda _self: None)
    window = gui_ssa.SSAMainWindow()
    calls = []
    try:
        monkeypatch.setattr(
            window, "show_header_context_menu", lambda position: calls.append(position)
        )
        event = QMouseEvent(
            QEvent.Type.MouseButtonPress,
            QPointF(2, 2),
            QPointF(2, 2),
            Qt.MouseButton.RightButton,
            Qt.MouseButton.RightButton,
            Qt.KeyboardModifier.NoModifier,
        )

        handled = window.eventFilter(window.table_widget.horizontalHeader(), event)

        assert handled is False
        assert calls == []
    finally:
        window.close()
