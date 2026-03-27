# Legacy Docs Reorg Study 2026-03-27

## Purpose

This study consolidates the current plan to reduce ambiguity between active docs,
historical snapshots, and long-form legacy guides without rewriting historical facts.

## Current Rules

1. Active truth lives in:
   - `README.md`
   - `docs/README.md`
   - `docs/INDEX.md`
   - `docs/RECOVERY_BACKLOG.md`
   - `docs/NEXT_CHAT_MIGRATION.md`
   - `docs/AGENTS_HANDOFF_NEXT_CYCLE.md`
2. Frozen policy files remain untouched:
   - `docs/POLICY_BASELINE_V1_FROZEN.md`
   - `docs/POLICY_BASELINE_V1_1_FROZEN.md`
3. Archive files preserve historical context and must not be silently "updated into truth".

## Problem Statement

The repository now mixes three documentation classes:

1. active operational docs,
2. historical snapshots that are still useful,
3. long guides that are mostly historical but still stored alongside active docs.

This increases the chance of:

1. reading a historical note as if it were current truth,
2. reopening already-closed decisions,
3. duplicating current-truth sections across too many files.

## Recommended Target Structure

### Keep active in `docs/`

These should remain active and short:

- `README.md`
- `docs/README.md`
- `docs/INDEX.md`
- `docs/RECOVERY_BACKLOG.md`
- `docs/NEXT_CHAT_MIGRATION.md`
- `docs/AGENTS_HANDOFF_NEXT_CYCLE.md`
- `docs/NUNCA_CONFIE_IA.md`
- focused runbooks still used operationally

### Keep frozen in place

- `docs/POLICY_BASELINE_V1_FROZEN.md`
- `docs/POLICY_BASELINE_V1_1_FROZEN.md`

### Archive or relabel as historical-first

These files already behave mostly as historical references and should be treated that way:

- `docs/BUILD_EXECUTAVEL_ANALISE_COMPLETA.md`
- `docs/BUILD_EXECUTION_AUDIT_20260311.md`
- `docs/BUILD_SYSTEM.md`
- `docs/BUILD_PYINSTALLER_GUIA_COMPLETO.md`
- `docs/BUILD_NUITKA_GUIA_COMPLETO.md`
- `docs/BUILD_PYOXIDIZER_GUIA_COMPLETO.md`
- `docs/BUILD_SCRIPTS_COMPARISON.md`
- `docs/HISTORICO_VERSOES.md`
- `docs/archive/*`

## Migration Strategy

### Phase 1: label clearly

1. Ensure every historical-first doc starts with one of:
   - `HISTORICAL SNAPSHOT`
   - `Historical-first guide`
   - `Archive reference`
2. Add a short pointer back to active truth at the top.

### Phase 2: reduce duplicate "current truth"

1. `README.md` keeps the product-level top truth.
2. `docs/README.md` and `docs/INDEX.md` act as navigators, not mini-backlogs.
3. `docs/NEXT_CHAT_MIGRATION.md` and `docs/AGENTS_HANDOFF_NEXT_CYCLE.md` keep only the live operational top plus compact history references.

### Phase 3: optional physical archive move

Only after an explicit user-approved cycle:

1. move historical-first build guides into `docs/archive/`,
2. leave thin active stubs in `docs/` when needed for compatibility,
3. update all inbound links in one atomic `DOC_SYNC`.

## Immediate Candidates For Future Cleanup

1. `docs/AGENTS_HANDOFF_NEXT_CYCLE.md`
   - still stores too much inline history;
   - can shrink further if the team accepts a separate historical ledger.
2. `docs/NEXT_CHAT_MIGRATION.md`
   - should remain shorter than handoff;
   - avoid repeating large validation matrices.
3. build guides
   - several are now historical-first and can be grouped more aggressively.

## Non-Goals

This study does not:

1. rewrite historical facts,
2. change runtime behavior,
3. move files automatically,
4. replace frozen policy files.

## Exit Criteria For A Future Reorg Slice

1. no active doc points to a stale historical block as truth,
2. archive docs all self-identify as historical,
3. active docs stay short and non-duplicative,
4. link integrity is rechecked in one pass after moves.
