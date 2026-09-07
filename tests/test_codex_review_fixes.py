"""Contract tests for the codex-review fixes on the import pipeline.

Fix #1: promotion gate whitelist is closed by error_code (not error_type).
Fix #3: launcher exit code governed by outcome status, not event errors.
Fix #4: primary_database_changed reflects actual writes (diff can commit
files and then fail derivadas sync with the database already changed).
Fix #6: snapshot restore skips the heavy re-verify (snapshot was
pre-validated by quick_check).
"""

import os
import sys

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from core import import_outcome  # noqa: E402
from core.import_outcome import ImportStatus  # noqa: E402


def outcome_for(
    status: ImportStatus, *, changed: bool | None = None, run_id: str = "r"
):
    return import_outcome.build_import_outcome(
        raw_status=status.value,
        legacy_result=True,
        run_id=run_id,
        reason="",
        primary_db_path="p",
        working_db_path="w",
        primary_database_actually_changed=changed,
    )


class TestPromotionGateWhitelist:
    """Fix #1: only files in deterministic_failed_files are non-blocking."""

    def test_extraction_with_deterministic_code_passes(self):
        from core.app_logic import _has_blocking_candidate_errors

        files = ["/docs/a.xlsx", "/docs/b.xlsx"]
        errors = [("extraction", "/docs/b.xlsx", "bad columns")]
        det_files = ["/docs/b.xlsx"]  # full path in deterministic list
        assert (
            _has_blocking_candidate_errors(
                files_to_process=files,
                critical_errors=errors,
                deterministic_failed_files=det_files,
            )
            is False
        )

    def test_extraction_with_missing_file_blocks(self):
        from core.app_logic import _has_blocking_candidate_errors

        files = ["/docs/a.xlsx", "/docs/b.xlsx"]
        errors = [("extraction", "/docs/b.xlsx", "file not found")]
        det_files = []  # MISSING_FILE is not deterministic
        assert (
            _has_blocking_candidate_errors(
                files_to_process=files,
                critical_errors=errors,
                deterministic_failed_files=det_files,
            )
            is True
        )

    def test_unexpected_type_blocks_regardless_of_det_list(self):
        from core.app_logic import _has_blocking_candidate_errors

        files = ["/docs/a.xlsx", "/docs/b.xlsx"]
        errors = [("unexpected", "/docs/b.xlsx", "simulated")]
        assert (
            _has_blocking_candidate_errors(
                files_to_process=files,
                critical_errors=errors,
                deterministic_failed_files=[],
            )
            is True
        )

    def test_full_path_no_basename_collision(self):
        """Two files with same basename in different dirs don't cross-match."""
        from core.app_logic import _has_blocking_candidate_errors

        files = ["/docs/a.xlsx", "/docs/processadas/a.xlsx"]
        errors = [
            ("extraction", "/docs/a.xlsx", "missing file"),
        ]
        # Only the processadas copy is deterministic; the root copy is MISSING_FILE
        det_files = ["/docs/processadas/a.xlsx"]
        assert (
            _has_blocking_candidate_errors(
                files_to_process=files,
                critical_errors=errors,
                deterministic_failed_files=det_files,
            )
            is True
        )


class TestLauncherExitCode:
    """Fix #3: non-blocking outcome overrides event errors."""

    def test_rejections_only_with_errors_exits_0(self):
        from launchers import cli_entry

        class FakeLogger:
            def info(self, *a, **k):
                pass

            def error(self, *a, **k):
                pass

        outcome = outcome_for(ImportStatus.DETERMINISTIC_REJECTIONS_ONLY)
        sentinel_old = outcome_for(ImportStatus.NO_CHANGES)
        calls = {"count": 0}

        def fake_get():
            calls["count"] += 1
            return sentinel_old if calls["count"] <= 1 else outcome

        original_get = import_outcome.get_last_import_outcome
        import_outcome.get_last_import_outcome = fake_get
        try:

            class FakeSummary:
                total_candidates = 1
                processed_files = 0
                errors = ["rejection event"]

                def capture(self, *a, **k):
                    pass

            stats = cli_entry._execute_import_and_report(
                lambda **kwargs: True,
                docs_dir="docs",
                data_dir="data",
                runtime_base="base",
                logger=FakeLogger(),
            )
        finally:
            import_outcome.get_last_import_outcome = original_get

        assert stats["exit_code"] == 0, (
            "DETERMINISTIC_REJECTIONS_ONLY with event errors must exit 0"
        )


class TestPrimaryDatabaseChangedOverride:
    """Fix #4: actually_changed flag reflects real writes."""

    def test_diff_committed_then_derivadas_failed_is_changed(self):
        outcome = outcome_for(
            ImportStatus.DERIVADAS_SYNC_ERROR,
            changed=True,  # files were committed before the sync failure
        )
        assert outcome.primary_database_changed is True
        assert outcome.reload_required is True

    def test_status_fallback_when_override_absent(self):
        outcome = import_outcome.build_import_outcome(
            raw_status="derivadas_sync_error",
            legacy_result=False,
            run_id="r",
            reason="",
            primary_db_path="p",
            working_db_path="w",
            # no override: falls back to status-based
        )
        assert outcome.primary_database_changed is False


class TestSnapshotRestoreSkipsHeavyVerify:
    """Fix #6: restore path returns a pre-validated report."""

    def test_ensure_returns_report_with_restored_flag(self):
        from armazenamento.database_integrity import (
            ensure_database_integrity,
        )
        from armazenamento import database_integrity

        original_restore = database_integrity._restore_latest_valid_snapshot
        original_verify = database_integrity.verify_database_integrity
        verify_calls = {"count": 0}

        def fake_restore(db_path, table_name):
            return True  # snapshot restored successfully

        def counting_verify(db_path, table_name):
            verify_calls["count"] += 1
            return original_verify(db_path, table_name)

        database_integrity._restore_latest_valid_snapshot = fake_restore
        database_integrity.verify_database_integrity = counting_verify
        try:
            ok, report = ensure_database_integrity(
                "/nonexistent/path.db",
                "schema.sql",
                "ssa_table",
            )
        finally:
            database_integrity._restore_latest_valid_snapshot = original_restore
            database_integrity.verify_database_integrity = original_verify

        # verify was called once (initial), not twice (initial + post-restore)
        assert verify_calls["count"] == 1, (
            "restore path must not re-run the heavy verify"
        )


class TestRecordOutcomeRunIdGuard:
    """Fix #2: record_import_outcome rejects cross-run outcomes."""

    def test_record_rejects_mismatched_run_id(self):
        outcome_a = outcome_for(ImportStatus.UPDATED, run_id="run_A")
        assert (
            import_outcome.record_import_outcome(
                outcome_a, expected_run_id="run_B"
            )
            is False
        )

    def test_record_accepts_matching_run_id(self):
        outcome_a = outcome_for(ImportStatus.UPDATED, run_id="run_A")
        assert (
            import_outcome.record_import_outcome(
                outcome_a, expected_run_id="run_A"
            )
            is True
        )
