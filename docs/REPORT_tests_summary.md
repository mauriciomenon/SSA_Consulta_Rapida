# Test Run Summary (local)

- Focused tests for robust importer: PASS
- Full suite run: interrupted by KeyboardInterrupt after long execution; first launcher test passed. Recommend running in CI or with markers to avoid long-running tests locally.

Suggested quick runs:
- `pytest -q tests/test_robust_importer.py`
- `pytest -q -k importer` (subset)

