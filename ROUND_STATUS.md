# ROUND_STATUS

## 2026-06-05 STABILITY_PATCH selecao Windows

- Kluster MCP auto review initial run: clean for first patch set, chat_id `yf495ma2nq8`.
- Kluster MCP auto review after final geometry/status adjustment: timed out repeatedly at 120s.
- Fallback check: `where.exe kluster-verify; kluster-verify --help` failed because `kluster-verify` was not found in PATH.
- Fallback check: `C:\Users\mauri\.pnpm\bin\pnpm.CMD dlx kluster-verify --help` failed with npm registry 404 for `kluster-verify`.
- Status: user accepted this version as reasonable; latest Kluster retries after the Macro/Reprogramacoes micro adjustment timed out at 120s; local gates passed after the final adjustment.

## 2026-06-05 STABILITY_PATCH main bottom splitter

- Status: splitter implemented after user accepted the Windows selection filter version and requested commit/push.
- Previous accepted selection commit pushed: `da7882dd`.
- Final visual adjustment: removed local splitter QSS, kept native Qt handle with width 8, and locked compact selection-control height against Macro while keeping Reprogramacoes at 26 px to avoid cutting `= Igual`.
- Local gates passed after final adjustment: py_compile, ruff, ty, and focused pytest (`6 passed, 456 deselected`).
- Visual smoke: Computer Use captured the real window; splitter was native/discreet, Selecao had no vertical scroll, Macro was centered, controls matched Macro height (21 px), Reprogramacoes remained legible (26 px), and Detalhes/Filtros heights matched.
- Drag smoke: Qt handle drag moved splitter sizes from `[382, 319]` to `[502, 199]`, increasing table height and keeping bottom panels synced.
- Kluster MCP auto review: clean before final test-only drag coverage; later retries after test/status edits timed out at 120s.
- Fallback check: `where.exe kluster-verify; kluster-verify --help` failed because `kluster-verify` was not found in PATH.
- Fallback check: `C:\Users\mauri\.pnpm\bin\pnpm.CMD dlx kluster-verify --help` failed with npm registry 404 for `kluster-verify`.
