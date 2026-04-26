# Derivadas Sync Runbook

## Scope

This runbook covers safe operation of derivadas synchronization in backend-only flows.
It does not change GUI behavior.

## Commands Summary

- Dev guard runners:
  - Active (Bun/TS): `bun scripts/dev_ai_guard.ts --mode pre-pr --db data/ssas.db`
  - Fallback (Python): `python scripts/dev_ai_guard.py --mode pre-pr --db data/ssas.db`
  - Note: keep TS version as primary and Python as compatibility fallback.
  - In `pre-pr`, the guard auto-skips `sync --verify-only` only when base table
    `ssa_table` is confirmed missing.
  - If table presence check is unknown (for example temporary DB lock), guard keeps
    `sync --verify-only` enabled.
- Validate schema readiness without writes:
  - `python scripts/derivadas_cli.py --db data/ssas.db --output json schema-scan`
- Validate consistency without writes:
  - `python scripts/derivadas_cli.py --db data/ssas.db --output json scan`
- Validate source merge without writes:
  - `python scripts/derivadas_cli.py --db data/ssas.db --output json sync --verify-only`
- Standard sync:
  - `python scripts/derivadas_cli.py --db data/ssas.db --output json sync`
- Full rebuild sync (stale matrix rows removed):
  - `python scripts/derivadas_cli.py --db data/ssas.db --output json sync --full-rebuild`
- Stats snapshot:
  - `python scripts/derivadas_cli.py --db data/ssas.db --output json stats`
- Low-cost maintenance:
  - `python scripts/derivadas_cli.py --db data/ssas.db --output json maintenance --min-interval-seconds 3600`

## Safety Procedure For Full Rebuild

1. Freeze writes to the database from external jobs when possible.
2. Create a DB backup before running full rebuild:
   - `cp data/ssas.db data/ssas.db.bak.$(date +%Y%m%d_%H%M%S)`
3. Run pre-checks:
   - `schema-scan`
   - `scan`
   - `sync --verify-only`
4. Run `sync --full-rebuild`.
5. Run post-checks:
   - `stats`
   - `scan`
6. Archive output JSON reports for traceability.

## Rollback Procedure

1. Stop writers and background jobs that touch the same DB.
2. Replace current DB with backup copy.
3. Run:
   - `schema-scan`
   - `scan`
4. Re-enable writers only after scan is consistent.

## Operational Notes

- `sync` fails fast when all sources are disabled. At least one source is required:
  - DB source enabled, or
  - `--sheet-file` provided.
- Guard runners keep the failure signal strict, but auto-skip only the `sync --verify-only`
  health step when `ssa_table` is confirmed absent in the target DB.
- Sheet import accepts resilient column aliases for parent, child, and relation label.
- `scan` is independent from import flow and does not perform writes.
- `maintenance` is interval-guarded and can run as a lightweight background check.

<!-- DOC_SYNC_MAC: 2026-03-29 host-agnostic paths, continue from repo root on macOS -->

