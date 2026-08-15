# Terminal integration: pytest wrappers

This repository includes helper scripts to run pytest with a controlled external timeout and an option to stream output to the terminal while saving logs locally. These are intended to help validate terminal integration (PowerShell / pwsh) and obtain live output when debugging CI or local runner issues.

Files added (non-destructive):

- `scripts/run_pytest_with_timeout_v2.py` - Run pytest with an external timeout and write combined stdout/stderr to a log file.
- `scripts/run_pytest_stream_and_log_v2.py` - Stream pytest output live to the terminal while writing the same output to a log file.

Logs and local docs:

- Default logs are written to `local_ai_private/pytest_terminal_integration.log` and `local_ai_private/pytest_terminal_integration_stream.log`.
- Detailed usage notes and troubleshooting can be stored in `local_ai_private/` per machine.

Usage examples:

- Run with a 10s timeout and write log:

```
python scripts/run_pytest_with_timeout_v2.py --test tests/test_terminal_integration.py --timeout 10
```

- Stream live output and save log:

```
python scripts/run_pytest_stream_and_log_v2.py --test tests/test_terminal_integration.py --timeout 10
```

PowerShell Tee fallback (if you prefer native shell streaming):

```
python -m pytest tests/test_terminal_integration.py 2>&1 | Tee-Object -FilePath local_ai_private\pytest_terminal_integration.log
```

Notes:

- The v2 scripts are additive and do not overwrite existing scripts.
- `local_ai_private` is gitignored.

<!-- DOC_SYNC_MAC: 2026-03-29 host-agnostic paths, continue from repo root on macOS -->

