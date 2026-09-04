"""Consumer contract tests for the typed import outcome (S4d).

Consumers classify runs by ImportOutcome instead of the legacy bool:
exit codes in the launcher, the busy state everywhere, and the
reload/imported flags driven by primary_database_changed. Fake importers
(exactly what existing launcher tests inject) never record an outcome,
so the identity-snapshot pattern keeps the legacy fallback intact.
"""

import os
import sys
from unittest.mock import MagicMock, patch

import pytest

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from core import import_outcome  # noqa: E402
from core.import_outcome import ImportStatus  # noqa: E402


def outcome_for(status: ImportStatus, *, changed: bool | None = None):
    return import_outcome.build_import_outcome(
        raw_status=status.value,
        legacy_result=(changed if changed is not None else status.value == "updated"),
        run_id="test",
        reason="",
        primary_db_path="primary.db",
        working_db_path="working.db",
    )


def test_blocking_classification_matches_exit_code_policy():
    non_blocking = {
        ImportStatus.UPDATED,
        ImportStatus.DERIVADAS_MATERIALIZED,
        ImportStatus.NO_CHANGES,
        ImportStatus.DETERMINISTIC_REJECTIONS_ONLY,
    }
    for status in ImportStatus:
        expected = status not in non_blocking
        assert import_outcome.is_blocking_status(status) is expected, status


def _fake_import_with_return(value: bool):
    def fake(**kwargs):
        return value

    return fake


class TestCliEntryExitCodes:
    @pytest.fixture()
    def execute(self, monkeypatch):
        from launchers import cli_entry

        class FakeLogger:
            def info(self, *args, **kwargs):
                pass

            def error(self, *args, **kwargs):
                pass

        def run(fake_importer, fake_outcome):
            # Simulate: before-run returns old outcome, after-run returns
            # the new one (different object = identity snapshot detects it).
            sentinel_old = (
                outcome_for(ImportStatus.NO_CHANGES) if fake_outcome else None
            )
            calls = {"count": 0}

            def fake_get():
                calls["count"] += 1
                if calls["count"] <= 1:
                    return sentinel_old
                return fake_outcome

            monkeypatch.setattr(
                import_outcome, "get_last_import_outcome", fake_get
            )
            stats = cli_entry._execute_import_and_report(
                fake_importer,
                docs_dir="docs",
                data_dir="data",
                runtime_base="base",
                logger=FakeLogger(),
            )
            return stats

        return run

    def test_busy_blocks_with_exit_1(self, execute):
        stats = execute(
            _fake_import_with_return(False),
            outcome_for(ImportStatus.BUSY),
        )
        assert stats["exit_code"] == 1
        assert stats["status"] == "blocked"

    def test_candidate_incomplete_blocks_with_exit_1(self, execute):
        stats = execute(
            _fake_import_with_return(False),
            outcome_for(ImportStatus.CANDIDATE_INCOMPLETE),
        )
        assert stats["exit_code"] == 1
        assert stats["status"] == "blocked"

    def test_rejections_only_exits_0(self, execute):
        stats = execute(
            _fake_import_with_return(True),
            outcome_for(ImportStatus.DETERMINISTIC_REJECTIONS_ONLY),
        )
        assert stats["exit_code"] == 0
        assert stats["status"] == "success"

    def test_no_outcome_falls_back_to_legacy_bool(self, execute):
        stats = execute(
            _fake_import_with_return(False),
            None,
        )
        assert stats["exit_code"] == 0
        assert stats["status"] == "no_work"


class TestPaiImportServiceFlag:
    def _make_preview(self):
        from core.pai_import_service import PaiFetchedXlsxPreview

        return PaiFetchedXlsxPreview(
            export="",
            import_xlsx_path="import.xlsx",
            normalized_rows=0,
            xlsx_summary={},
        )

    def test_imported_uses_primary_database_changed(self, tmp_path):
        from core import pai_import_service as service

        outcome = outcome_for(
            ImportStatus.DETERMINISTIC_REJECTIONS_ONLY, changed=True
        )
        returns = iter([None, outcome])
        with patch.object(
            import_outcome,
            "get_last_import_outcome",
            side_effect=lambda: next(returns, outcome),
        ):
            result = service.import_prepared_pai_xlsx(
                request=MagicMock(project_root=str(tmp_path)),
                preview=self._make_preview(),
                docs_dir=tmp_path,
                db_path=tmp_path / "ssas.db",
                stage_files=lambda **kwargs: (["staged.xlsx"], {}),
                import_files=lambda *a, **k: True,
                count_rows=lambda db_path: 5,
                should_cancel=None,
            )
        assert result.imported is False

    def test_imported_legacy_when_no_outcome(self, tmp_path):
        from core import pai_import_service as service

        result = service.import_prepared_pai_xlsx(
            request=MagicMock(project_root=str(tmp_path)),
            preview=self._make_preview(),
            docs_dir=tmp_path,
            db_path=tmp_path / "ssas.db",
            stage_files=lambda **kwargs: (["staged.xlsx"], {}),
            import_files=lambda *a, **k: True,
            count_rows=lambda db_path: 5,
            should_cancel=None,
        )
        assert result.imported is True


class TestRescanWorkerClassification:
    @pytest.fixture()
    def worker(self):
        pytest.importorskip("PyQt6")
        from PyQt6.QtWidgets import QApplication
        from gui.workers.rescan_worker import RescanWorker

        QApplication.instance() or QApplication([])
        w = RescanWorker(
            main_py_path="/fake/path/main.py", project_root="/fake/project"
        )
        yield w
        if w._logger_attached:
            w._detach_logger()

    def _run_with(self, worker, monkeypatch, *, success, outcome, processed=0):
        monkeypatch.setattr(
            worker, "_prepare_import_inputs", lambda: (True, None)
        )

        def fake_op():
            worker._last_import_outcome = outcome
            worker._last_processed_files = processed
            return success

        monkeypatch.setattr(worker, "_run_import_operation", fake_op)
        monkeypatch.setattr(worker, "_attach_logger", lambda: None)
        monkeypatch.setattr(worker, "_detach_logger", lambda: None)
        worker.run()

    def test_busy_outcome_maps_to_error(self, worker, monkeypatch):
        from gui.workers.rescan_worker import RescanOutcome

        self._run_with(
            worker,
            monkeypatch,
            success=False,
            outcome=outcome_for(ImportStatus.BUSY),
        )
        assert worker.last_outcome is RescanOutcome.ERROR

    def test_updated_by_outcome_not_by_processed_count(self, worker, monkeypatch):
        from gui.workers.rescan_worker import RescanOutcome

        # outcome says NO_CHANGES even though files were processed
        self._run_with(
            worker,
            monkeypatch,
            success=True,
            outcome=outcome_for(ImportStatus.NO_CHANGES, changed=False),
            processed=5,
        )
        assert worker.last_outcome is RescanOutcome.NO_CHANGES

    def test_no_outcome_keeps_legacy_heuristic(self, worker, monkeypatch):
        from gui.workers.rescan_worker import RescanOutcome

        self._run_with(
            worker, monkeypatch, success=True, outcome=None, processed=5
        )
        assert worker.last_outcome is RescanOutcome.UPDATED
