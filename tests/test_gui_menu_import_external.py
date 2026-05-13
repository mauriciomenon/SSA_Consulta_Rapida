from __future__ import annotations

import json
import sqlite3
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
        self.submenus: dict[str, _DummyMenu] = {}

    def addAction(self, action: Any) -> Any:
        self.actions.append(action)
        return action

    def addSeparator(self) -> None:
        return None

    def addMenu(self, name: str) -> "_DummyMenu":
        menu = _DummyMenu()
        self.submenus[name] = menu
        return menu


class _DummyMenuBar:
    def __init__(self) -> None:
        self.menus: dict[str, _DummyMenu] = {}

    def addMenu(self, name: str) -> _DummyMenu:
        menu = _DummyMenu()
        self.menus[name] = menu
        return menu


def test_setup_app_menus_registers_grouped_menus(monkeypatch) -> None:
    class _FakeSignal:
        def connect(self, *_args, **_kwargs) -> None:
            return None

    class _FakeAction:
        def __init__(self, text: str, *_args, **_kwargs) -> None:
            self._text = text
            self.triggered = _FakeSignal()
            self._checkable = False
            self._checked = False

        def setCheckable(self, value: bool) -> None:
            self._checkable = bool(value)

        def setChecked(self, value: bool) -> None:
            self._checked = bool(value)

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

        def open_processadas_folder(self) -> None:
            return None

        def open_nosurvivor_folder(self) -> None:
            return None

        def open_settings_file_with_backup(self) -> None:
            return None

        def reset_settings_to_defaults(self) -> None:
            return None

        def _hard_reset_filters_state(self) -> None:
            return None

        def toggle_theme_menu(self) -> None:
            return None

        def show_filter_help(self) -> None:
            return None

        def open_installation_guide(self) -> None:
            return None

        def run_vacuum_analyze(self) -> None:
            return None

        def _apply_table_cell_alignment_preference(self, _name: str) -> None:
            return None

    window = _Window()
    monkeypatch.setattr(gui_ssa, "QAction", cast(Any, _FakeAction))
    gui_ssa.SSAMainWindow._setup_app_menus(cast(Any, window))
    assert "Arquivo" in window._menu_bar.menus
    assert "Importacao" in window._menu_bar.menus
    assert "Database" in window._menu_bar.menus
    assert "Opcoes" in window._menu_bar.menus
    assert "Ajuda" in window._menu_bar.menus
    assert len(window._menu_bar.menus["Arquivo"].actions) == 2
    assert len(window._menu_bar.menus["Importacao"].actions) == 7
    assert len(window._menu_bar.menus["Database"].actions) == 4
    assert len(window._menu_bar.menus["Opcoes"].actions) == 4
    assert len(window._menu_bar.menus["Ajuda"].actions) == 2

    arquivo_labels = [
        getattr(action, "_text", "")
        for action in window._menu_bar.menus["Arquivo"].actions
    ]
    importacao_labels = [
        getattr(action, "_text", "")
        for action in window._menu_bar.menus["Importacao"].actions
    ]
    database_labels = [
        getattr(action, "_text", "")
        for action in window._menu_bar.menus["Database"].actions
    ]
    opcoes_labels = [
        getattr(action, "_text", "")
        for action in window._menu_bar.menus["Opcoes"].actions
    ]
    ajuda_labels = [
        getattr(action, "_text", "")
        for action in window._menu_bar.menus["Ajuda"].actions
    ]

    assert arquivo_labels == [
        "Exportar lista",
        "Sair",
    ]
    assert importacao_labels == [
        "Importar XLS/XLSX externo",
        "Atualizar Dados",
        "Reescaneamento Completo",
        "Abrir Pasta de Arquivos",
        "Abrir Pasta Arquivos Processados",
        "Abrir Pasta Arquivos Redundantes",
        "Consolidar arquivos de entrada",
    ]
    assert database_labels == [
        "Reescanear",
        "Atualizar derivadas",
        "Carregar outro DB",
        "Compactar DB",
    ]
    assert opcoes_labels == [
        "Abrir arquivo de opcoes",
        "Restaurar opcoes padrao",
        "Limpar Filtros",
        "Selecionar Tema",
    ]
    assert ajuda_labels == ["Instalacao", "Ajuda"]


def test_import_external_excel_files_copies_and_suffixes_collisions(
    monkeypatch,
    tmp_path: Path,
) -> None:
    source_root = tmp_path / "fontes"
    source_root.mkdir()
    source = source_root / "entrada.xlsx"
    source.write_text("new", encoding="utf-8")
    source_ok_2 = source_root / "segunda.xlsx"
    source_ok_2.write_text("new-2", encoding="utf-8")
    source2 = source_root / "outra.xls"
    source2.write_text("legacy", encoding="utf-8")

    monkeypatch.setattr(gui_ssa, "project_root", str(tmp_path))
    monkeypatch.setattr(
        gui_ssa.QFileDialog,
        "getOpenFileNames",
        lambda *args, **kwargs: (
            [str(source), str(source_ok_2), str(source2)],
            "Arquivos Excel",
        ),
    )
    monkeypatch.setattr(
        gui_ssa.QMessageBox, "information", lambda *args, **kwargs: None
    )
    captured: dict[str, Any] = {}
    monkeypatch.setattr(
        gui_ssa.ssa_gui_workers,
        "rescan_data",
        lambda _window, **kwargs: captured.setdefault("kwargs", dict(kwargs)),
    )

    class _Window:
        def __init__(self) -> None:
            self.status_label = _DummyLabel()

    window = _Window()
    result = gui_ssa.SSAMainWindow.import_external_excel_files(cast(Any, window))

    assert result["selected"] == 3
    assert result["copied"] == 0
    assert result["skipped"] == 0
    assert result["failed"] == 0
    assert result["unsupported"] == 0
    assert result["staged"] == 3
    assert result["result_scope"] == "queue"
    assert result["db_updated"] is False
    assert result["db_update_requested"] is True
    assert result["queued"] is True
    assert list(captured["kwargs"]["source_files"]) == [
        str(source),
        str(source_ok_2),
        str(source2),
    ]
    assert captured["kwargs"]["rescan_mode"] == "explicit"
    assert captured["kwargs"]["reload_on_success"] is True
    assert captured["kwargs"]["operation_kind"] == "import"
    assert window.status_label.text == ""


def test_import_external_excel_files_empty_selection_returns_consistent_schema(
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        gui_ssa.QFileDialog,
        "getOpenFileNames",
        lambda *args, **kwargs: ([], "Arquivos Excel"),
    )

    result = gui_ssa.SSAMainWindow.import_external_excel_files(cast(Any, object()))
    assert result == {
        "selected": 0,
        "copied": 0,
        "skipped": 0,
        "failed": 0,
        "unsupported": 0,
        "staged": 0,
        "result_scope": "queue",
        "db_updated": False,
        "db_update_requested": False,
        "queued": False,
    }


def test_import_external_excel_files_applies_staged_file_without_recopiar(
    monkeypatch,
    tmp_path: Path,
) -> None:
    docs_dir = tmp_path / "docs_entrada"
    docs_dir.mkdir()
    staged = docs_dir / "entrada.xlsx"
    staged.write_text("dados", encoding="utf-8")

    monkeypatch.setattr(gui_ssa, "project_root", str(tmp_path))
    monkeypatch.setattr(
        gui_ssa.QFileDialog,
        "getOpenFileNames",
        lambda *args, **kwargs: ([str(staged)], "Arquivos Excel"),
    )
    monkeypatch.setattr(
        gui_ssa.QMessageBox, "information", lambda *args, **kwargs: None
    )
    captured: dict[str, Any] = {}
    monkeypatch.setattr(
        gui_ssa.ssa_gui_workers,
        "rescan_data",
        lambda _window, **kwargs: captured.setdefault("kwargs", dict(kwargs)),
    )

    class _Window:
        def __init__(self) -> None:
            self.status_label = _DummyLabel()

    result = gui_ssa.SSAMainWindow.import_external_excel_files(cast(Any, _Window()))
    assert result["selected"] == 1
    assert result["copied"] == 0
    assert result["failed"] == 0
    assert result["staged"] == 1
    assert result["result_scope"] == "queue"
    assert result["db_updated"] is False
    assert result["db_update_requested"] is True
    assert result["queued"] is True
    assert list(captured["kwargs"]["source_files"]) == [str(staged)]


def test_import_external_excel_files_filters_invalid_and_unsupported_before_queue(
    monkeypatch,
    tmp_path: Path,
) -> None:
    source_root = tmp_path / "fontes"
    source_root.mkdir()
    ok_file = source_root / "ok.xlsx"
    ok_file.write_text("ok", encoding="utf-8")
    unsupported = source_root / "nota.txt"
    unsupported.write_text("txt", encoding="utf-8")
    missing = source_root / "sumiu.xlsx"

    monkeypatch.setattr(gui_ssa, "project_root", str(tmp_path))
    monkeypatch.setattr(
        gui_ssa.QFileDialog,
        "getOpenFileNames",
        lambda *args, **kwargs: (
            [str(ok_file), str(unsupported), str(missing)],
            "Arquivos Excel",
        ),
    )
    captured: dict[str, Any] = {}
    monkeypatch.setattr(
        gui_ssa.ssa_gui_workers,
        "rescan_data",
        lambda _window, **kwargs: captured.setdefault("kwargs", dict(kwargs)),
    )

    class _Window:
        def __init__(self) -> None:
            self.status_label = _DummyLabel()

    result = gui_ssa.SSAMainWindow.import_external_excel_files(cast(Any, _Window()))

    assert result["selected"] == 3
    assert result["failed"] == 1
    assert result["unsupported"] == 1
    assert result["staged"] == 1
    assert list(captured["kwargs"]["source_files"]) == [str(ok_file)]


def test_open_settings_file_with_backup_creates_backup(
    monkeypatch, tmp_path: Path
) -> None:
    settings_dir = tmp_path / "config"
    settings_dir.mkdir()
    settings_path = settings_dir / "settings.json"
    settings_path.write_text('{"x":1}', encoding="utf-8")

    monkeypatch.setattr(gui_ssa, "QT_AVAILABLE", True)
    monkeypatch.setattr(
        gui_ssa,
        "QUrl",
        type("DummyQUrl", (), {"fromLocalFile": staticmethod(lambda path: path)}),
        raising=False,
    )
    monkeypatch.setattr(
        gui_ssa,
        "QDesktopServices",
        type(
            "DummyDesktopServices",
            (),
            {"openUrl": staticmethod(lambda *args, **kwargs: True)},
        ),
        raising=False,
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
    assert "editor externo" in window.status_label.text

    result_second = gui_ssa.SSAMainWindow.open_settings_file_with_backup(
        cast(Any, window)
    )
    backups_after_second = list(settings_dir.glob("settings.json.bak_*"))
    assert result_second["opened"] is True
    assert len(backups_after_second) == 2


def test_reset_settings_to_defaults_overwrites_user_file(
    monkeypatch, tmp_path: Path
) -> None:
    config_dir = tmp_path / "config_runtime"
    config_dir.mkdir()
    default_settings = {
        "user_preferences": {"theme": "gruvbox", "page_size": 100},
        "default_filters": [],
    }
    (config_dir / "default_settings.json").write_text(
        json.dumps(default_settings),
        encoding="utf-8",
    )
    (config_dir / "settings.json").write_text(
        json.dumps({"user_preferences": {"theme": "old"}}),
        encoding="utf-8",
    )

    monkeypatch.setenv("SSA_CONFIG_DIR", str(config_dir))

    class _Window:
        def __init__(self) -> None:
            self.status_label = _DummyLabel()

        def _resolve_settings_file_path(self) -> str:
            return str(config_dir / "settings.json")

    window = _Window()
    result = gui_ssa.SSAMainWindow.reset_settings_to_defaults(cast(Any, window))

    with open(config_dir / "settings.json", "r", encoding="utf-8") as handle:
        restored = json.load(handle)

    backups = list(config_dir.glob("settings.json.bak_*"))
    assert result["ok"] is True
    assert restored == default_settings
    assert len(backups) == 1
    assert "padrao restauradas" in window.status_label.text


def test_consolidate_input_files_moves_by_last_report(
    monkeypatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(gui_ssa, "project_root", str(tmp_path))
    captured: dict[str, Any] = {}
    monkeypatch.setattr(
        gui_ssa.ssa_gui_workers,
        "rescan_data",
        lambda _window, **kwargs: captured.setdefault("kwargs", dict(kwargs)),
    )

    class _Window:
        def __init__(self) -> None:
            self.status_label = _DummyLabel()

    window = _Window()
    result = gui_ssa.SSAMainWindow.consolidate_input_files(cast(Any, window))

    assert result["moved"] == 0
    assert result["nosurvivor"] == 0
    assert result["pending"] == 0
    assert result["failed"] == 0
    assert result["queued"] is True
    assert result["result_scope"] == "queue"
    assert captured["kwargs"]["operation_kind"] == "consolidate"
    assert captured["kwargs"]["operation_label"] == "Consolidacao de arquivos"


def test_consolidate_input_files_does_not_route_error_status_to_nosurvivor(
    monkeypatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(gui_ssa, "project_root", str(tmp_path))
    captured: dict[str, Any] = {}
    monkeypatch.setattr(
        gui_ssa.ssa_gui_workers,
        "rescan_data",
        lambda _window, **kwargs: captured.setdefault("kwargs", dict(kwargs)),
    )

    class _Window:
        def __init__(self) -> None:
            self.status_label = _DummyLabel()

    window = _Window()
    result = gui_ssa.SSAMainWindow.consolidate_input_files(cast(Any, window))

    assert result["queued"] is True
    assert captured["kwargs"]["operation_kind"] == "consolidate"


def test_consolidate_input_files_keeps_update_only_out_of_nosurvivor(
    monkeypatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(gui_ssa, "project_root", str(tmp_path))
    captured: dict[str, Any] = {}
    monkeypatch.setattr(
        gui_ssa.ssa_gui_workers,
        "rescan_data",
        lambda _window, **kwargs: captured.setdefault("kwargs", dict(kwargs)),
    )

    class _Window:
        def __init__(self) -> None:
            self.status_label = _DummyLabel()

    window = _Window()
    result = gui_ssa.SSAMainWindow.consolidate_input_files(cast(Any, window))

    assert result["queued"] is True
    assert captured["kwargs"]["operation_kind"] == "consolidate"


def test_open_processadas_folder_routes_to_helper(monkeypatch, tmp_path: Path) -> None:
    captured: dict[str, str] = {}
    monkeypatch.setattr(gui_ssa, "project_root", str(tmp_path))

    def _fake_open_folder(self: Any, folder_path: str, folder_label: str) -> None:
        captured["folder_path"] = folder_path
        captured["folder_label"] = folder_label

    monkeypatch.setattr(
        gui_ssa.SSAMainWindow,
        "_open_folder_non_blocking",
        _fake_open_folder,
    )
    gui_ssa.SSAMainWindow.open_processadas_folder(cast(Any, object()))

    assert captured["folder_path"] == str(tmp_path / "docs_entrada" / "processadas")
    assert captured["folder_label"] == "pasta processadas"


def test_open_nosurvivor_folder_routes_to_helper(monkeypatch, tmp_path: Path) -> None:
    captured: dict[str, str] = {}
    monkeypatch.setattr(gui_ssa, "project_root", str(tmp_path))

    def _fake_open_folder(self: Any, folder_path: str, folder_label: str) -> None:
        captured["folder_path"] = folder_path
        captured["folder_label"] = folder_label

    monkeypatch.setattr(
        gui_ssa.SSAMainWindow,
        "_open_folder_non_blocking",
        _fake_open_folder,
    )
    gui_ssa.SSAMainWindow.open_nosurvivor_folder(cast(Any, object()))

    assert captured["folder_path"] == str(
        tmp_path / "docs_entrada" / "processadas" / "nosurvivor"
    )
    assert captured["folder_label"] == "pasta sem sobreviventes"


def test_run_vacuum_analyze_success_updates_status(monkeypatch, tmp_path: Path) -> None:
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    db_path = data_dir / "ssas.db"
    with sqlite3.connect(db_path) as conn:
        conn.execute("CREATE TABLE t(a INTEGER)")
        conn.execute("INSERT INTO t(a) VALUES (1)")

    monkeypatch.setattr(gui_ssa, "DB_PATH", str(db_path))

    class _Window:
        def __init__(self) -> None:
            self.status_label = _DummyLabel()

    window = _Window()
    result = gui_ssa.SSAMainWindow.run_vacuum_analyze(cast(Any, window))

    assert result["ok"] is True
    assert "DB compactado" in window.status_label.text


def test_run_vacuum_analyze_uses_database_layer(monkeypatch, tmp_path: Path) -> None:
    db_path = tmp_path / "ssas.db"
    db_path.write_bytes(b"placeholder")
    monkeypatch.setattr(gui_ssa, "DB_PATH", str(db_path))
    calls: list[str] = []
    monkeypatch.setattr(
        gui_ssa,
        "vacuum_analyze_database",
        lambda path: calls.append(path) or {"ok": True, "db_path": path},
    )

    class _Window:
        def __init__(self) -> None:
            self.status_label = _DummyLabel()

    result = gui_ssa.SSAMainWindow.run_vacuum_analyze(cast(Any, _Window()))

    assert result == {"ok": True, "db_path": str(db_path)}
    assert calls == [str(db_path)]


def test_run_vacuum_analyze_missing_db(monkeypatch, tmp_path: Path) -> None:
    missing_path = tmp_path / "data" / "missing.db"
    monkeypatch.setattr(gui_ssa, "DB_PATH", str(missing_path))

    result = gui_ssa.SSAMainWindow.run_vacuum_analyze(cast(Any, object()))
    assert result["ok"] is False
    assert result["reason"] == "missing_db"


def test_run_vacuum_analyze_async_path_delivers_result_and_resets_flags(
    monkeypatch,
    tmp_path: Path,
) -> None:
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    db_path = data_dir / "ssas.db"
    with sqlite3.connect(db_path) as conn:
        conn.execute("CREATE TABLE t(a INTEGER)")
        conn.execute("INSERT INTO t(a) VALUES (1)")

    monkeypatch.setattr(gui_ssa, "DB_PATH", str(db_path))
    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)

    class _ImmediateTimer:
        @staticmethod
        def singleShot(_msec: int, callback) -> None:
            callback()

    class _FakeMessageBox:
        class StandardButton:
            Yes = 1
            No = 0

        @staticmethod
        def question(*_args, **_kwargs) -> int:
            return _FakeMessageBox.StandardButton.Yes

        @staticmethod
        def information(*_args, **_kwargs) -> int:
            return 0

        @staticmethod
        def warning(*_args, **_kwargs) -> int:
            return 0

    class _InlineThread:
        def __init__(self, target=None, daemon=None, **_kwargs) -> None:
            self._target = target
            self.daemon = daemon

        def start(self) -> None:
            if self._target is not None:
                self._target()

    monkeypatch.setattr(gui_ssa, "QTimer", _ImmediateTimer)
    monkeypatch.setattr(gui_ssa, "QMessageBox", _FakeMessageBox)
    monkeypatch.setattr(gui_ssa.threading, "Thread", _InlineThread)

    class _Window:
        def __init__(self) -> None:
            self.status_label = _DummyLabel()
            self._vacuum_analyze_running = False
            self._vacuum_analyze_thread = None

    window = _Window()
    result = gui_ssa.SSAMainWindow.run_vacuum_analyze(cast(Any, window))

    assert result["ok"] is True
    assert result["started"] is True
    assert window._vacuum_analyze_running is False
    assert window._vacuum_analyze_thread is None
    assert "DB compactado" in window.status_label.text
