# ROUND_STATUS

## 2026-07-06 DOC_SYNC v4.44 local baseline

- Local baseline promoted to `v4.44` at `4ae43f05b0d81d15b7b224a09dcac7dfb316c915` (`DOC_SYNC: promote local baseline to 4.44`).
- Current local runtime includes `54bcbc002af3db8877a3b718c105d808a0d5381b` (`STABILITY_PATCH: show commit ISO date in about dialog`), which makes About/Data ISO fall back to the running commit date when `build_info.json` is absent.
- This DOC_SYNC input HEAD was `54bcbc002af3db8877a3b718c105d808a0d5381b` on `dev`, 68 commits ahead of local `origin/dev`; this DOC_SYNC adds 1 local commit, making the branch 69 commits ahead after commit.
- Local gates recorded for v4.44: `ruff check .` OK, `ty check` OK, `pip-audit` OK, full pytest `2455 passed, 6 skipped, 2 warnings, 11 subtests`.
- Follow-up docs closed H3/H4/H5/J4 as delivered or delivered functionally; H7 remains partial and J2 remains deferred pending measured baseline.
- GitHub operations are blocked: `git ls-remote --heads origin dev` returns HTTP 403 because the account is suspended. Do not fetch, push, open PRs, or rely on remote checks until this is resolved.
- Local untracked files intentionally remain outside commits: `docs/handoffs/SKILLS_*`, skill audit backups/logs, and `quality_gates_output.jsonl`.
- H6 visual smoke was executed locally with screenshot evidence in the conversation; next functional cycle is P2 H7/J2/J5/SELECT * after remote unblock and divergence review.

## 2026-06-07 STABILITY_PATCH advanced filter popup/theme learning

- Pushed commit: `d1d1dfa80da08900ffc786e6e98801b690310106` (`STABILITY_PATCH: repair advanced filter popup and theme`) on `dev`.
- Learning: visual GUI claims require evidence from a real popup/window screenshot, not only unit assertions or verbal inspection.
- Learning: Kluster on a single file can miss cross-file intent; rerun with the full modified-file context before treating an intent finding as real or false.
- Learning: `QComboBox` with editable/read-only line edit on Windows needs a real `QTest.mouseClick()` smoke for the displayed field, because a fake event filter test can pass while the user click still fails.
- Learning: theme refresh must reapply QSS to existing widgets without rebuilding advanced filter options; stale queued refresh callbacks must no-op after a direct refresh clears the scheduled flag.
- Learning: multiselect popup header must stay outside the scroll area; alignment must be verified against checkbox columns while the body scrolls independently.
- Learning: local or unrelated files (`pyproject.toml`, `uv.lock`, `.vs/`, `docs_entrada/pai_api/`, `package-lock.json`) must remain out of the slice stage unless explicitly requested.
- Evidence captured: `ssa_responsavel_execucao_popup_evidence_final2.png`, `ssa_por_texto_theme_evidence_final2.png`, and `ssa_macro_popup_evidence_final2.png` under `%TEMP%`.
- Final gates before push: py_compile, ruff, ty, focused pytest (`44 passed`), Kluster full-context clean, CodeRabbit rerun only reported `.vs/` files outside scope.

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
