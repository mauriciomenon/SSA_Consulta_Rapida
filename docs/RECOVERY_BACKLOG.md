# Recovery Backlog

This file tracks post-merge hardening and cleanup for the recovery branch.
Scope is split by priority to keep delivery safe and incremental.

## P0 blockers

- Clear legacy `CHANGES_REQUESTED` state from old bot reviews on PR #25.
- Define repo policy for external check waivers when provider plan limits are hit.

## P1 hardening targets

- Extract shared process termination helper for:
  - `scripts/run_pytest_stream_and_log.py`
  - `scripts/run_pytest_stream_and_log_v2.py`
  - `scripts/run_pytest_with_timeout.py`
  - `scripts/run_pytest_with_timeout_v2.py`
- Reduce broad `except Exception` in pytest wrapper scripts where specific exceptions are known.
- Start timeout clock at process start (`Popen`) for wrapper consistency.
- Improve fallback hash in `gui/workers/filter_worker.py` to include columns in fallback path.
- Revisit `concat + drop_duplicates` in `gui/workers/filter_worker.py` for large DataFrame performance.
- Standardize log levels and use `logger.exception` where traceback is required in `gui/gui_ssa.py`.
- Plan transversal `except ... pass` cleanup in GUI code, no layout changes.
- Add stronger user-facing diagnostics for config fallback cases in `gui/gui_config.py`.
- Validate worker retention strategy in long runs and add simple retention telemetry.

## P2 cleanup and consistency

- Align dependency declarations between `pyproject.toml` and `requirements*.txt`.
- Revisit `requires-python >=3.13` and confirm minimum supported version.
- Remove redundant imports and unused logger references in import verification scripts.
- Normalize success/failure contract in `tests/run_import_detailed.py`.
- Improve `.gitignore` pattern tests in `tests/test_release_artifact_guard.py`.
- Add integration tests for stream wrapper edge cases:
  - full queue,
  - closed pipe while reader is active,
  - forced timeout with kill escalation.
- Mark performance-sensitive tests explicitly to reduce CI flakiness.
- Revisit smoke GUI fixture isolation to prevent accidental real `load_data` execution.
- Define bot review cadence to reduce duplicate noise in large PRs.
- Reassess active review apps and disable redundant ones.
- Add merge checklist in PR template:
  - known risks,
  - accepted waivers,
  - mandatory follow-up links.

## Execution model

- Use atomic commits per topic.
- Keep rollback easy by changing one concern at a time.
- Prefer low-risk defensive changes first, then structural cleanup.

