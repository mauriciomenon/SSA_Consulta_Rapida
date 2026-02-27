# SSA Consulta Rapida AGENTS Guide

Project handoff baseline from the previous cycle was reviewed by Claude, Codex, and Kimi Code.
Use that baseline as input, then improve with clear scope control and risk-first delivery.

## Current Context

- Recovery/hardening is historical baseline context, not an active branch instruction.
- Active work is being executed on the current dev branch (`codex/dev-filtros-stability`).
- Follow-up backlog is tracked at `/Users/menon/git/SSA_Consulta_Rapida/docs/RECOVERY_BACKLOG.md`.
- Stable baseline from previous cycle must be preserved.

## Main Goal For New Dev Branch

Deliver the new feature end to end with correct behavior and safe rollback, without regression in stabilized flows (async, filters, workers).

## Secondary Goals

1. Keep GUI layout and element positions unchanged unless explicitly requested.
2. Keep atomic commits with simple rollback per feature slice.
3. Validate every batch before push with `py_compile`, `ruff`, and focused `pytest`.
4. Prioritize real risk fixes and avoid broad out-of-scope refactors.
5. Handle only blocking PR bots/checks now; defer non-blocking items to backlog.
6. Keep decisions and deferred work documented in `docs/RECOVERY_BACKLOG.md`.

## Execution Rules

1. Use ASCII only in code and technical messages.
2. No emoji and no emdash in technical communication.
3. Work in short cycles: diagnose -> minimal patch -> validate -> atomic commit -> push.
4. Re-check PR comments, bots, and checks after each push.
5. Preserve recovery hardening behavior unless a change is required by the new feature.

## Explicit Confirmation Protocol (Mandatory)

1. Never infer permission for GUI layout changes from generic replies such as `continue`, `sim`, `segue`, `ok`, or `pode continuar`.
2. Any layout or positioning change requires an explicit command with clear action intent, for example: `alterar layout`, `ajustar alinhamento`, `reverter layout`, or a direct list of UI items.
3. Never execute layout rollback without the user explicitly writing `reverter` plus target scope.
4. If scope is ambiguous, stop and ask a binary confirmation (`sim` or `nao`) tied to a concrete checklist of files/items before editing.
5. In ambiguous cases, default action is: run diagnosis/tests only; do not edit GUI layout.
6. Before any GUI edit, post an impact summary listing exactly what will change and what will remain unchanged.

## Tooling Rules (Mandatory)

1. Qwen is a mandatory support tool for repetitive operational tasks in each slice.
2. Use Qwen for repetitive check execution and repetitive triage formatting when applicable:
   - `ruff check`
   - `ty check`
   - focused `pytest` runs
   - repetitive checklist generation by issue IDs
3. Keep final technical decisions, patch review, and final validation under the main agent.
4. Kluster remains mandatory for security/quality/compliance verification after each file change.
5. Qwen usage does not replace quality gates; quality gates remain mandatory before push.
6. Any broad search command must use timeout 60s. This includes `rg --hidden --no-ignore`, scans outside the repo root, and recursive scans across large trees. If timeout hits, stop and refine scope before rerun.

## Reasoning Profile Rule (Mandatory)

1. Use `xhigh` reasoning for:
   - complex decision points,
   - architecture tradeoff analysis,
   - broad impact/risk mapping,
   - conflict resolution between rules/findings.
2. Keep medium reasoning only for repetitive/mechanical operations.
3. If the assistant cannot switch reasoning level autonomously, it must explicitly remind the user to switch to `xhigh` before continuing complex analysis.

## Detailed Plan For New Feature Branch

1. Branch setup and scope lock
   - Create `codex/dev-<feature-name>`.
   - Write explicit in-scope and out-of-scope boundaries before coding.
2. Impact map
   - Identify touched modules, sensitive integrations, and concurrency/state risks.
   - Mark required tests for each risk area.
3. Minimal design
   - Define the smallest safe architecture delta for the feature.
   - Avoid transversal refactor unless it blocks delivery.
4. Vertical implementation slices
   - Implement by thin end-to-end slices, each independently testable.
   - Add defensive handling only where required for functional correctness.
5. Validation gate per slice
   - Run `py_compile` for touched files.
   - Run `ruff` for touched files.
   - Run focused `pytest` for touched flow plus sensitive regressions when needed.
6. Commit and push discipline
   - One atomic commit per validated slice.
   - Push only after local gate is green.
7. PR and bot handling
   - Fix blockers immediately.
   - Record non-blocking follow-up in backlog with clear action text.
8. Pre-merge consolidation
   - Run focused regression on sensitive flows impacted by the branch.
   - Confirm no GUI layout/position changes were introduced.
9. Final handoff
   - Update backlog and short final note with: delivered scope, known risks, deferred items.

## Definition Of Done

1. Main goal and acceptance criteria are fully met.
2. No confirmed regression in touched sensitive flows.
3. Validation gates passed for all pushed slices.
4. PR has no unresolved technical blockers.
5. Backlog updated for deferred non-blocking work.

## Landing the Plane (Session Completion)

**When ending a work session**, you MUST complete ALL steps below. Work is NOT complete until `git push` succeeds.

**MANDATORY WORKFLOW:**

1. **File issues for remaining work** - Create issues for anything that needs follow-up
2. **Run quality gates** (if code changed) - Tests, linters, builds
3. **Update issue status** - Close finished work, update in-progress items
4. **PUSH TO REMOTE** - This is MANDATORY:
   ```bash
   git pull --rebase
   bd sync
   git push
   git status  # MUST show "up to date with origin"
   ```
5. **Clean up** - Clear stashes, prune remote branches
6. **Verify** - All changes committed AND pushed
7. **Hand off** - Provide context for next session

**CRITICAL RULES:**
- Work is NOT complete until `git push` succeeds
- NEVER stop before pushing - that leaves work stranded locally
- NEVER say "ready to push when you are" - YOU must push
- If push fails, resolve and retry until it succeeds
