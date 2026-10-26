"""Espelho do estado da tela (BL-51): salvar/abrir filtros, ordenacao, colunas e foco."""

import json
import os
from collections import OrderedDict
from unittest.mock import patch

import pandas as pd
import pytest

pytest.importorskip("PyQt6", reason="PyQt6 dependency unavailable in test environment")

from PyQt6.QtWidgets import QApplication  # noqa: E402

from gui import gui_ssa  # noqa: E402
from gui.gui_ssa import SSAMainWindow  # noqa: E402
from gui.mixins import filter_gui_ssa_mixin as filter_mixin  # noqa: E402
from gui.ssa import screen_state_mirror as mirror  # noqa: E402


class TestScreenStateMirror:
    @classmethod
    def setup_class(cls):
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        cls.app = QApplication.instance() or QApplication([])

    def setup_method(self):
        self._load_patch = patch.object(SSAMainWindow, "load_data", lambda win: None)
        self._load_patch.start()
        self.win = SSAMainWindow()
        self.win._filter_worker_registry = filter_mixin.DeferredFilterWorkerRegistry()
        self.win._sync_filtering = True
        self.base_df = pd.DataFrame(
            {
                "numero_ssa": ["202500001", "202500002", "202500003", "202500004", "202500005"],
                "situacao": ["AAD", "STE", "AMP", "AAD", "AMP"],
                "derivada_de": ["", "202500001", "", "", ""],
                "descricao_ssa": ["Bomba A", "Bomba B", "Motor C", "Bomba D", "Bomba E"],
                "setor_executor": ["IEE3", "MEL4", "IEE3", "IEE3", "IEE3"],
            }
        )
        self.win.on_data_loaded(self.base_df.copy())

    def teardown_method(self):
        self.win.close()
        self._load_patch.stop()

    def _db(self, tmp_path):
        db = tmp_path / "ssas.db"
        db.write_bytes(b"x")
        return str(db)

    def _set_screen(self):
        win = self.win
        win.search_input.setText("bomba")
        win.initiate_filtering()
        win._active_column_filters = OrderedDict({"setor_executor": "IEE3"})
        win.sort_column = "descricao_ssa"
        win.sort_ascending = False
        win._refresh_after_filter_change()
        win._jump_to_ssa("202500004", _allow_refilter=False)
        self.app.processEvents()

    def _shown(self):
        return list(self.win.df_exibido["numero_ssa"])

    def test_round_trip_restores_search_filters_sort_and_focus(self, tmp_path):
        db = self._db(tmp_path)
        self._set_screen()
        expected_rows = self._shown()
        assert expected_rows == ["202500005", "202500004", "202500001"]
        saved = mirror.save_state_file(self.win, str(tmp_path / "tela"), db)
        assert saved.endswith(".ssa-estado.json")

        self.win._clear_all_filters_global()
        self.win.sort_column = None
        self.win.sort_ascending = True
        self.win._refresh_after_filter_change()
        self.win._jump_to_ssa("202500003", _allow_refilter=False)
        assert self.win.search_input.text() == ""

        warnings = mirror.apply_state_payload(self.win, mirror.load_state_file(saved), db)
        self.app.processEvents()

        assert warnings == []
        assert self.win.search_input.text() == "bomba"
        assert dict(self.win._active_column_filters) == {"setor_executor": "IEE3"}
        assert (self.win.sort_column, self.win.sort_ascending) == ("descricao_ssa", False)
        assert self._shown() == expected_rows
        assert self.win._details_current_ssa == "202500004"

    def test_unknown_version_is_refused_and_nothing_changes(self, tmp_path):
        db = self._db(tmp_path)
        self._set_screen()
        payload = mirror.build_state_payload(self.win, db)
        payload["filtros"]["search_text"] = "motor"
        before = (self.win.search_input.text(), self.win.sort_column, self._shown())
        for bad in (99, None, "1"):
            payload["versao_formato"] = bad
            with pytest.raises(ValueError, match="Versao do arquivo de estado"):
                mirror.apply_state_payload(self.win, payload, db)
        assert (self.win.search_input.text(), self.win.sort_column, self._shown()) == before

    def test_changed_database_identity_warns_in_status_bar(self, tmp_path, monkeypatch):
        db = self._db(tmp_path)
        self._set_screen()
        saved = mirror.save_state_file(self.win, str(tmp_path / "tela"), db)

        payload = mirror.load_state_file(saved)
        payload["dados"]["linhas"] += 1
        assert mirror.DB_CHANGED_WARNING in mirror.apply_state_payload(self.win, payload, db)

        os.utime(db, (1_000_000, 1_000_000))
        monkeypatch.setattr(gui_ssa, "DB_PATH", db)
        monkeypatch.setattr(
            gui_ssa.QFileDialog, "getOpenFileName", lambda *a, **k: (saved, "")
        )
        self.win.open_screen_state()
        assert "o banco mudou" in self.win.status_label.text()

    def test_payload_is_json_without_data_rows(self, tmp_path):
        db = self._db(tmp_path)
        self._set_screen()
        saved = mirror.save_state_file(self.win, str(tmp_path / "tela.ssa-estado.json"), db)
        with open(saved, encoding="utf-8") as handle:
            text = handle.read()
        payload = json.loads(text)

        assert set(payload) == {
            "versao_formato", "salvo_em", "versao_app", "filtros", "ordenacao",
            "colunas", "pagina", "ssa_em_foco", "dados",
        }
        assert payload["versao_formato"] == mirror.FORMAT_VERSION
        assert payload["dados"] == {
            "banco": "ssas.db", "banco_mtime": os.path.getmtime(db), "linhas": 5,
        }
        for row_value in ("Bomba A", "Motor C", "202500001", "MEL4"):
            assert row_value not in text
