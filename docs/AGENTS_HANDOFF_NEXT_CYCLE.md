# AGENTS Handoff For Next Cycle

This handoff is meant to be pasted into a new conversation with any agent that follows AGENTS style instructions.

## Current Project State

- Recovery and hardening cycle was merged.
- Backlog for deferred work is tracked at:
  - `/Users/menon/git/SSA_Consulta_Rapida/docs/RECOVERY_BACKLOG.md`
- Quality baseline from last cycle:
  - Atomic commits only
  - Focused fixes before refactors
  - No GUI layout movement without explicit request
  - Validate each change batch before push

## Required Working Style

1. Use ASCII only in code and technical notes.
2. No emojis and no emdash.
3. Keep commits atomic and easy to rollback.
4. Prefer minimal, low-risk fixes over broad rewrites.
5. Do not move GUI buttons or alter layout unless explicitly requested.
6. After each batch: run targeted validation before commit and push.
7. Re-check PR bot comments and status checks after each push.
8. Treat external provider failures separately from local code quality.

## Validation Contract Per Batch

- Syntax check for touched files (`py_compile`).
- Lint for touched files (`ruff`).
- Targeted tests first, then broader tests only when needed.
- If a critical flow is touched, run a focused smoke/regression test for that flow.

## Merge Gate Policy

- Gate 1: CI green and branch mergeable.
- Gate 2: zero unmitigated high or critical findings.
- Gate 3: local smoke/regression for sensitive flow passes.
- Gate 4: minor bot nits can go to backlog with clear PR note.

## Bot And Review Policy

- Resolve real blockers now.
- Defer non-blocking cleanup to backlog.
- Keep one short PR note with:
  - known risks,
  - accepted waivers,
  - follow-up links.

## Copy Block For New Conversation

```text
Use the same execution discipline from the last recovery cycle:
- ASCII only, no emojis, no emdash.
- Atomic commits only.
- Validate each batch with py_compile + ruff + targeted pytest before push.
- No GUI layout/button position changes unless explicitly requested.
- Fix high-risk issues first, defer broad refactors.
- Re-check PR bot comments and checks after each push.
- Track deferred items in /Users/menon/git/SSA_Consulta_Rapida/docs/RECOVERY_BACKLOG.md.
Current focus changed: preserve quality process, apply it to the new scope.
```

