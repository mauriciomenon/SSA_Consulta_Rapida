# ROUND_STATUS

## 2026-07-15 dependency update cycle checkpoint

- Local incremental checkpoint tag created: `v4.45.1`, targeting `d8c4033c6828f1ecde05f4f3140f137ee43d496f` (`DOC_SYNC: clarify GitLab Bitbucket and GitHub remotes`, 2026-07-14 19:32:28 -0300). This is a local rollback marker, not a published release.
- Read-only dependency audit confirmed 69 distinct outdated packages in the locked all-groups graph; no bulk update is authorized by this cycle.
- `uv.lock` currently has PyPI sources only. The private Safety index remains configured in user/project files and must be isolated with `UV_CONFIG_FILE=/dev/null` during lock regeneration.
- Current security and consistency checks: `pip-audit` 0 vulnerabilities, Safety 0 vulnerabilities across 121 packages, `pip check` OK, and `uv lock --check` OK.
- Click `8.4.2` and Pillow `12.3.0` are the current locked versions after the previous authorized update; both are outside the base runtime dependency list.
- Clawpatch was rerun without dirty-tree inclusion, but fell back to broad repository feature review and was interrupted before completion. No findings were applied. Vulture findings remain intentionally ignored as false positives.
- Next step: controlled no-major dependency slice covering PyQt6, build tooling, and selected development tooling, followed by lock regeneration against PyPI and full validation.

## 2026-07-06 Windows release hardening

- Windows build wrappers hardened at `bdad722c343fcd604a5a35f0d9bb307dd37c8a5b` (2026-07-06 12:39:15 -0300, `STABILITY_PATCH: harden Windows build wrapper cleanup`).
- `release_windows.ps1` pre-zip workspace hardened at `63631e72b1f622c33d0c64fdb43e8e5fb342c4b8` (2026-07-06 12:39:15 -0300, `STABILITY_PATCH: harden release_windows.ps1 pre-zip workspace`).
- Scope: PyInstaller `--clean` fails on non-zero exit; Nuitka Windows renames `SSA_*_windows_amd64.dist` to canonical `gui_entry.dist` / `cli_entry.dist`; release script adds backend allowlist cleanup, user workspace dirs with `.gitkeep`, and runtime source protection before ZIP.
- Local contract gates: `tests/test_release_windows_script.py` and focused `tests/test_dev_env_build_scripts.py` Windows cases passed (15 focused / 91 release-related).
- Commits were created without GPG signature in agent environment (`commit.gpgsign=false` override); re-sign locally if policy requires.
- Next step: Windows smoke on real host with `release_windows.ps1 -Backend pyinstaller,nuitka -Yes -SkipInstaller`.
- Remote map: `origin` is GitLab, `bitbucket` is Bitbucket, and `gh` is GitHub. `dev` is published to GitLab and Bitbucket; the HTTP 403 affects only `gh`.
- Standard `git pull` on `dev` uses `origin/dev` (GitLab). A request to `commitar` also publishes to `bitbucket/dev`.

## 2026-07-06 P2 runtime cleanup and measured defer

- P2 `SELECT *` runtime closed locally at `bd76ace31d77d98455e7e6125e698164bde99e9a` (2026-07-06 10:28:11 -0300, `STABILITY_PATCH: replace runtime select star queries`).
- Runtime search `rg -n "SELECT \* FROM" armazenamento gui core scripts` returned no matches; remaining `SELECT *` occurrences are tests/fixtures or custom SQL contract cases.
- H7/J2 measured before runtime patch: GUI filter smoke `4 passed, 2 deselected in 3.87s`; focused filter/cache contracts `54 passed in 26.91s`.
- RSS/timing evidence: small filter cycles delta 6.3 MB; 50k rows/3 cycles delta 4.5 MB; largest observed stage was `column=8.31ms`, `render=3.99ms`.
- J5 derivadas contracts passed: `40 passed in 4.97s` for CLI snapshot/family, sync controller, import triggers, and derivada checkbox scenario.
- Decision: no H7/J2/J5 runtime patch in this cycle because current evidence shows no hotspot or failing contract. Next step is GitHub non-mutating check; do not fetch/push while 403 persists.

## 2026-07-06 DOC_SYNC v4.44 local baseline

- Local baseline promoted to `v4.44` at `4ae43f05b0d81d15b7b224a09dcac7dfb316c915` (`DOC_SYNC: promote local baseline to 4.44`).
- Current local runtime includes `54bcbc002af3db8877a3b718c105d808a0d5381b` (`STABILITY_PATCH: show commit ISO date in about dialog`), which makes About/Data ISO fall back to the running commit date when `build_info.json` is absent.
- This DOC_SYNC input HEAD was `54bcbc002af3db8877a3b718c105d808a0d5381b` on `dev`, 68 commits ahead of local `origin/dev`; subsequent local cleanup and P2 commits leave the branch 74 commits ahead after `4ac834b23fe243f801aac4995b0c11efa6fe62fe`.
- Local gates recorded for v4.44: `ruff check .` OK, `ty check` OK, `pip-audit` OK, full pytest `2455 passed, 6 skipped, 2 warnings, 11 subtests`.
- Follow-up docs closed H3/H4/H5/J4 as delivered or delivered functionally; H7/J2/J5 were measured in P2 and remain defer-only without runtime patch because no hotspot was observed.
- Historical correction: the HTTP 403 came from remote `gh` (GitHub), not `origin`. GitLab operations through `origin` and Bitbucket operations through `bitbucket` remain available.
- Local untracked files intentionally remain outside commits: `docs/handoffs/SKILLS_*`, skill audit backups/logs, and `quality_gates_output.jsonl`.
- H6 visual smoke was executed locally with screenshot evidence in the conversation; P2 runtime cleanup and measured defer is recorded above.

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
