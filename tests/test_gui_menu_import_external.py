from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast

from gui import gui_ssa


class _DummyLabel:
    def __init__(self) -> None:
        self.text = ""

    def setText(self, value: str) -> None:
        self.text = value


class _DummyMenu:
    def __init__(self) -> None:
        self.actions: list[Any] = []

    def addAction(self, action: Any) -> Any:
        self.actions.append(action)
        return action

    def addSeparator(self) -> None:
        return None


class _DummyMenuBar:
    def __init__(self) -> None:
        self.menus: dict[str, _DummyMenu] = {}

    def addMenu(self, name: str) -> _DummyMenu:
        menu = _DummyMenu()
        self.menus[name] = menu
        return menu


def test_setup_app_menus_registers_arquivo_and_db_actions(monkeypatch) -> None:
    class _FakeSignal:
        def connect(self, *_args, **_kwargs) -> None:
            return None

    class _FakeAction:
        def __init__(self, text: str, *_args, **_kwargs) -> None:
            self._text = text
            self.triggered = _FakeSignal()

    class _Window:
        def __init__(self) -> None:
            self._menu_bar = _DummyMenuBar()

        def menuBar(self) -> _DummyMenuBar:
            return self._menu_bar

        def import_external_excel_files(self) -> None:
            return None

        def open_docs_folder(self) -> None:
            return None

        def _export_current_list_txt(self) -> None:
            return None

        def close(self) -> None:
            return None

        def load_data(self) -> None:
            return None

        def load_other_database(self) -> None:
            return None

        def rescan_data(self) -> None:
            return None

        def rescan_diff_data(self) -> None:
            return None

        def rescan_full_data(self) -> None:
            return None

        def update_derivadas_from_sources(self) -> None:
            return None

        def consolidate_input_files(self) -> None:
            return None

        def open_settings_file_with_backup(self) -> None:
            return None

        def toggle_theme_menu(self) -> None:
            return None

    window = _Window()
    monkeypatch.setattr(gui_ssa, "QAction", cast(Any, _FakeAction))
    gui_ssa.SSAMainWindow._setup_app_menus(cast(Any, window))
    assert "Arquivo" in window._menu_bar.menus
    assert "DB" in window._menu_bar.menus
    assert len(window._menu_bar.menus["Arquivo"].actions) == 4
    assert len(window._menu_bar.menus["DB"].actions) == 8


def test_import_external_excel_files_copies_and_suffixes_collisions(
    monkeypatch,
    tmp_path: Path,
) -> None:
    docs_dir = tmp_path / "docs_entrada"
    docs_dir.mkdir()
    existing = docs_dir / "entrada.xlsx"
    existing.write_text("old", encoding="utf-8")

    source_root = tmp_path / "fontes"
    source_root.mkdir()
    source = source_root / "entrada.xlsx"
    source.write_text("new", encoding="utf-8")
    source2 = source_root / "outra.xls"
    source2.write_text("legacy", encoding="utf-8")

    monkeypatch.setattr(gui_ssa, "project_root", str(tmp_path))
    monkeypatch.setattr(
        gui_ssa.QFileDialog,
        "getOpenFileNames",
        lambda *args, **kwargs: ([str(source), str(source2)], "Arquivos Excel"),
    )
    monkeypatch.setattr(gui_ssa.QMessageBox, "information", lambda *args, **kwargs: None)

    class _Window:
        def __init__(self) -> None:
            self.status_label = _DummyLabel()

    window = _Window()
    result = gui_ssa.SSAMainWindow.import_external_excel_files(cast(Any, window))

    assert result["copied"] == 2
    assert result["skipped"] == 0
    assert result["failed"] == 0
    assert (docs_dir / "entrada__1.xlsx").exists()
    assert (docs_dir / "outra.xls").exists()
    assert "Importacao externa concluida" in window.status_label.text


def test_open_settings_file_with_backup_creates_backup(monkeypatch, tmp_path: Path) -> None:
    settings_dir = tmp_path / "config"
    settings_dir.mkdir()
    settings_path = settings_dir / "settings.json"
    settings_path.write_text('{"x":1}', encoding="utf-8")

    monkeypatch.setattr(gui_ssa, "QT_AVAILABLE", True)
    monkeypatch.setattr(
        gui_ssa,
        "QDesktopServices",
        type("DummyDesktopServices", (), {"openUrl": staticmethod(lambda *args, **kwargs: True)}),
    )

    class _Window:
        def __init__(self) -> None:
            self.status_label = _DummyLabel()

        def _resolve_settings_file_path(self) -> str:
            return str(settings_path)

    window = _Window()
    result = gui_ssa.SSAMainWindow.open_settings_file_with_backup(cast(Any, window))

    backups = list(settings_dir.glob("settings.json.bak_*"))
    assert result["opened"] is True
    assert result["backup_created"] is True
    assert len(backups) == 1
    assert "backup failsafe" in window.status_label.text


def test_consolidate_input_files_moves_by_last_report(monkeypatch, tmp_path: Path) -> None:
    docs_dir = tmp_path / "docs_entrada"
    logs_dir = tmp_path / "logs"
    docs_dir.mkdir()
    logs_dir.mkdir()

    (docs_dir / "ok.xlsx").write_text("ok", encoding="utf-8")
    (docs_dir / "zero.xlsx").write_text("zero", encoding="utf-8")
    (docs_dir / "pending.xlsx").write_text("pending", encoding="utf-8")

    payload = {
        "paths": {"docs_dir": str(docs_dir)},
        "file_reports": [
            {"file": "ok.xlsx", "counts": {"rows_inserted": 5}},
            {"file": "zero.xlsx", "counts": {"rows_inserted": 0}},
        ],
    }
    (logs_dir / "import_run_20260308_000001_000001.json").write_text(
        json.dumps(payload),
        encoding="utf-8",
    )

    monkeypatch.setattr(gui_ssa, "project_root", str(tmp_path))
    monkeypatch.setattr(gui_ssa.QMessageBox, "information", lambda *args, **kwargs: None)

    class _Window:
        def __init__(self) -> None:
            self.status_label = _DummyLabel()

        def _resolve_latest_project_import_report(self, docs_path: str):
            return gui_ssa.SSAMainWindow._resolve_latest_project_import_report(
                cast(Any, self), docs_path
            )

        def _build_unique_destination_path(self, destination_path: str) -> str:
            return gui_ssa.SSAMainWindow._build_unique_destination_path(
                cast(Any, self), destination_path
            )

    window = _Window()
    result = gui_ssa.SSAMainWindow.consolidate_input_files(cast(Any, window))

    assert result["moved"] == 2
    assert result["nosurvivor"] == 1
    assert result["pending"] == 1
    assert (docs_dir / "processadas" / "ok.xlsx").exists()
    assert (docs_dir / "processadas" / "nosurvivor" / "zero.xlsx").exists()
    assert (docs_dir / "pending.xlsx").exists()
