from __future__ import annotations

import csv
import sqlite3
from pathlib import Path
from types import SimpleNamespace

import pandas as pd

from armazenamento.derivadas_sync import sync_derivadas
from gui.ssa import gui_details


def _window(db_path: str, rows: list[tuple[str, str]]) -> SimpleNamespace:
    frame = pd.DataFrame(rows, columns=["numero_ssa", "derivada_de"])
    frame["situacao"] = "APV"
    return SimpleNamespace(
        db_path=db_path,
        df_completo=frame,
        df_exibido=frame,
        _data_uuid="relations-1",
        _data_revision=1,
        internal_to_display={},
    )


def test_details_prefers_matrix_and_separates_direct_relation_types(
    temp_db: str, tmp_path: Path, monkeypatch
) -> None:
    root = "202304697"
    local_child = "202304698"
    sheet_derived = "202304699"
    sheet_other = "202304700"
    with sqlite3.connect(temp_db) as conn:
        conn.executemany(
            "INSERT INTO ssa_table (numero_ssa, derivada_de) VALUES (?, ?)",
            [(root, None), (local_child, root), (sheet_derived, None), (sheet_other, None)],
        )
    sheet = tmp_path / "relations.csv"
    with sheet.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["parent_ssa", "child_ssa", "relation_label"])
        writer.writerow([root, local_child, "Complementa a"])
        writer.writerow([root, sheet_derived, "Derivada da"])
        writer.writerow([root, sheet_other, "Complementa a"])
    sync_derivadas(temp_db, sheet_file=str(sheet))

    window = _window(
        temp_db,
        [(root, ""), (local_child, root), (sheet_derived, ""), (sheet_other, "")],
    )
    monkeypatch.setattr(
        gui_details,
        "_get_cached_derivadas_family_edges",
        lambda *_args: (_ for _ in ()).throw(
            AssertionError("snapshot da matriz nao deve varrer DataFrame local")
        ),
    )
    data = gui_details._collect_derivadas_tree_data(window, root)
    derived, other = gui_details._get_direct_relations_for_ssa(window, root)
    html = gui_details._format_details_html(window, window.df_completo.iloc[0])
    with sqlite3.connect(temp_db) as conn:
        local_flags = conn.execute(
            "SELECT source_flags FROM ssa_derivada_matrix WHERE parent_ssa = ? AND child_ssa = ?",
            (root, local_child),
        ).fetchone()

    assert data["graph_source"] == "matrix"
    assert set(data["children"]) == {local_child, sheet_derived, sheet_other}
    assert data["render_family"] is True
    assert local_flags == (3,)
    assert derived == [local_child, sheet_derived]
    assert other == [{"ssa": sheet_other, "relacao": "Complementa a"}]
    assert "SSAs derivadas diretas (2)" in html
    assert "Outras relacoes diretas (1)" in html
    assert "202304700 (Complementa a)" in html

    stale_window = _window(
        temp_db,
        [(sheet_derived, ""), (sheet_other, sheet_derived)],
    )
    assert gui_details._get_direct_relations_for_ssa(
        stale_window, sheet_derived
    ) == ([], [])


def test_details_uses_sheet_snapshot_when_local_family_has_only_unrelated_edge(
    temp_db: str, tmp_path: Path
) -> None:
    root = "202100284"
    sheet_child = "202100285"
    sheet = tmp_path / "relation.csv"
    sheet.write_text(
        "parent_ssa,child_ssa,relation_label\n"
        f"{root},{sheet_child},Substitui a\n",
        encoding="utf-8",
    )
    sync_derivadas(temp_db, include_db_source=False, sheet_file=str(sheet))
    window = _window(
        temp_db,
        [(root, ""), (sheet_child, ""), ("202500001", ""), ("202500002", "202500001")],
    )

    data = gui_details._collect_derivadas_tree_data(window, root)
    derived, other = gui_details._get_direct_relations_for_ssa(window, root)

    assert data["graph_source"] == "matrix"
    assert data["children"] == [sheet_child]
    assert derived == []
    assert other == [{"ssa": sheet_child, "relacao": "Substitui a"}]


def test_details_uses_local_children_when_target_absent_from_synced_matrix(
    temp_db: str, tmp_path: Path
) -> None:
    sheet = tmp_path / "other.csv"
    sheet.write_text(
        "parent_ssa,child_ssa,relation_label\n202500001,202500002,Derivada da\n",
        encoding="utf-8",
    )
    sync_derivadas(temp_db, include_db_source=False, sheet_file=str(sheet))
    window = _window(temp_db, [("202600100", ""), ("202600101", "202600100")])

    data = gui_details._collect_derivadas_tree_data(window, "202600100")

    assert data["graph_source"] == "local"
    assert data["children"] == ["202600101"]
    assert "direct_relation_rows" not in data


def test_details_keeps_local_children_for_legacy_database(tmp_path: Path) -> None:
    window = _window(
        str(tmp_path / "missing.db"),
        [("202600100", ""), ("202600101", "202600100")],
    )

    data = gui_details._collect_derivadas_tree_data(window, "202600100")
    derived, other = gui_details._get_direct_relations_for_ssa(window, "202600100")

    assert data["graph_source"] == "local"
    assert data["children"] == ["202600101"]
    assert derived == ["202600101"]
    assert other == []


def test_legacy_family_starts_at_oldest_local_ancestor(tmp_path: Path) -> None:
    window = _window(
        str(tmp_path / "missing.db"),
        [
            ("202600100", ""),
            ("202600101", "202600100"),
            ("202600102", "202600101"),
            ("202600103", "202600100"),
        ],
    )

    data = gui_details._collect_derivadas_tree_data(window, "202600102")

    assert data["graph_source"] == "local"
    assert data["family_roots"] == ["202600100"]
    assert data["render_family"] is True


def test_direct_relation_categories_are_complete_when_graph_is_truncated(
    temp_db: str, tmp_path: Path
) -> None:
    root = "202600100"
    sheet = tmp_path / "many_relations.csv"
    with sheet.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["parent_ssa", "child_ssa", "relation_label"])
        for index in range(130):
            writer.writerow(
                [
                    root,
                    f"{202600101 + index}",
                    "Derivada da" if index % 2 == 0 else "Complementa a",
                ]
            )
    sync_derivadas(temp_db, include_db_source=False, sheet_file=str(sheet))
    window = _window(temp_db, [(root, "")])

    tree = gui_details._collect_derivadas_tree_data(window, root)
    derived, other = gui_details._get_direct_relations_for_ssa(window, root)

    assert tree["descendants_partial"] is True
    assert len(derived) == 65
    assert len(other) == 65


def test_context_tabs_rebind_current_series_and_drop_removed_ssas(monkeypatch) -> None:
    old_frame = pd.DataFrame(
        {
            "numero_ssa": ["202600100", "202600101"],
            "descricao_ssa": ["valor antigo", "removida"],
        }
    )
    new_frame = pd.DataFrame(
        {"numero_ssa": ["202600100"], "descricao_ssa": ["valor novo"]}
    )

    class TabBar:
        def __init__(self) -> None:
            self.current = 0
            self.removed: list[int] = []

        def blockSignals(self, _blocked):
            return False

        def currentIndex(self):
            return self.current

        def setCurrentIndex(self, index):
            self.current = index

        def removeTab(self, index):
            self.removed.append(index)

    class Widget:
        text = ""

        def setText(self, value):
            self.text = value

        def setEnabled(self, _enabled):
            return None

        def clear(self):
            self.text = ""

        def setFixedHeight(self, _height):
            return None

        def setVisible(self, _visible):
            return None

    tab_bar = TabBar()
    text = Widget()
    state = {
        "tab_bar": tab_bar,
        "details_text": text,
        "graph_label": Widget(),
        "back_button": Widget(),
        "close_button": Widget(),
        "current_ssa": "202600100",
        "entries": [
            {"ssa": "202600100", "series": old_frame.iloc[0]},
            {"ssa": "202600101", "series": old_frame.iloc[1]},
        ],
    }
    window = SimpleNamespace(
        df_completo=new_frame,
        df_exibido=new_frame,
        _details_context_state=state,
        _data_uuid="loaded-new",
        _data_revision=2,
    )
    monkeypatch.setattr(
        gui_details, "_format_details_html", lambda _window, series, **_kwargs: series["descricao_ssa"]
    )
    monkeypatch.setattr(gui_details, "_resolve_details_render_fonts", lambda _window: (10, ""))
    monkeypatch.setattr(gui_details, "_collect_derivadas_tree_data", lambda *_args: {})
    monkeypatch.setattr(gui_details, "_has_derivadas_graph_relations", lambda *_args: False)
    monkeypatch.setattr(gui_details, "_clear_graph_browser_markup", lambda *_args: None)
    monkeypatch.setattr(gui_details, "_get_cached_details_ssa_index", lambda *_args: {})
    monkeypatch.setattr(gui_details, "_get_window_ssa_series_index", lambda *_args: {})

    gui_details.refresh_derivadas_context_after_reload(window)

    assert tab_bar.removed == [1]
    assert state["entries"] == [{"ssa": "202600100"}]
    assert state["current_ssa"] == "202600100"
    assert text.text == "valor novo"
