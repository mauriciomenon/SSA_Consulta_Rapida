# Next Chat Migration Guide

Use this file to migrate context to a new chat without losing execution quality.

## Scope

- Branch: `codex/import-review`
- PR: `#31` (base `dev`)
- Goal now: close PR with minimal-risk fixes and no GUI layout changes.

## What to provide in the next chat

1. Current blocking errors/logs (if any).
2. External IA report in structured form:
   - `id`
   - `severity`
   - `file:line`
   - `evidence`
   - `impact`
   - `suggested fix`
3. Any new user decisions (scope approvals, deferrals).

## Latest intake status (2026-02-17)

- Completed:
  - Restored facade export contract for `_has_active_advanced_filters` in aggregated module.
  - Fixed broken regex in key-coverage test and added reverse contract check (`logic/detector -> UI or legacy`).
- Decision applied:
  - `responsavel_emissor` path B done: advanced filter flow removed/disabled in UI + logic detector.
- New validated input from modular rescan:
  - 75 files total, 64 processed, 11 errors.
  - all 11 errors are `SSAs Derivadas e Relacionadas_*.xlsx` rejected by main extractor required-column gate (`data_cadastro`, `descricao_ssa`).
  - these files are special derivadas source and should be handled by derivadas sync path, not main SSA extractor.
- Delivery status:
  - auto-trigger implemented in importer: special derivadas sheets are skipped from main extraction and synchronized by derivadas sync after import loop.
  - sync currently selects the latest special sheet by mtime and records special files in cache on successful sync.
- Additional delivery status:
  - user decision B applied for advanced filters: `responsavel_emissor` controls removed from UI panel assembly/context.
  - regression test added to keep `adv_responsavel_emissor_*` controls absent.
  - `Especificas...` derivadas button upgraded:
    - popup now shows DB materialized summary/top maes for visible SSAs (`ssa_derivada_summary`);
    - enable state now checks DB relations fallback when dataframe `derivada_de` has no valid values.
  - responsive grid regression fixed after removal of `responsavel_emissor` controls (`emis_resp_box` references removed).
  - advanced year execution filter cleanup:
    - dead `data_execucao` branch removed from logic;
    - behavior validated with test over `semana_executada` and `ano_execucao_values`.
  - legacy year keys migration hardened:
    - fixed precedence for `ano_execucao` + `ano_execucao_exclude=True`;
    - added tests for legacy `ano_emissao` and `ano_execucao` exclude path.
  - derivadas special ingest hardened:
    - importer now sends all detected special sheets to sync (not only latest by mtime);
    - `sync_derivadas` supports `sheet_files` and reports aggregated sheet stats.
- Keep backlog tracking in `docs/RECOVERY_BACKLOG.md` for non-blocking findings from the external report.

## Latest update (2026-02-18)

- Reliability hardening delivered after previous migration snapshot:
  - importer now blocks success when derivadas sync or consistency is not clean (`f9e69d86`);
  - sync pipeline now has internal post-materialization integrity gate (`474e980a`);
  - GUI manual derivadas update requires clean consistency scan (`5a50ea17`);
  - visual special parser now classifies root-only rows as informational (`6f4fcc7a`);
  - filter cache key now accepts advanced-filter context token (`ff266350`).
- Local data integrity check on `data/ssas.db` remains clean:
  - `scan`: `is_consistent=true`, all issue counts `0`.

## Mandatory execution protocol

1. Re-validate every external finding locally before patching.
2. Apply only minimal slices.
3. Run gate for each slice:

```bash
uv run python -m py_compile <files>
uv run ruff check <files>
uv run ty check <files>
uv run pytest -q <focused-tests>
```

4. Commit atomically, push, check PR checks.
5. Update handoff docs after each meaningful slice:
   - `docs/AGENTS_HANDOFF_NEXT_CYCLE.md`
   - `docs/RECOVERY_BACKLOG.md`

## Mandatory gates for advanced filters

```bash
uv run pytest -q tests/test_gui_filters_facade_contract.py
uv run pytest -q tests/test_gui_filter_logic.py -k advanced_filters
uv run pytest -q tests/test_gui_filters_advanced_logic.py
```

## Latest update (2026-02-18, mega sprint block 6)

- New slices delivered:
  - `1f213578`: derivadas sync now emits `sheet_file_reports` with per-file parse evidence and deduplicates relative/absolute file paths.
  - `ffd5d8ef`: importer derivadas phase now fails closed when any special sheet has no individual parse evidence.
  - `3daddd9f`: GUI `Atualizar Derivadas` now fails closed when any special sheet has no individual parse evidence.
  - `f7f7ead7`: derivadas CLI sync now supports `--special-docs-dir` to ingest all `SSAs Derivadas e Relacionadas_*.xlsx`.
  - `60adbd5a`: committed refreshed `data/ssas.db` after full derivadas sync with 11 special sheets.
- Operational run executed on 2026-02-18:
  - `sync_run_id=4`, actor `mega-sprint-special-sync`
  - `sheet_files_count=11`, `db_edges=3216`, `sheet_edges=1497`, `merged_edges=3547`
  - post-sync consistency: `is_consistent=true`

## Copy/paste starter for next chat

```text
Context:
- Continue on branch codex/import-review, PR #31.
- Keep minimal-risk patches only, no GUI layout changes.
- Ingest external IA report with local re-validation per finding.

Must follow:
1) Validate each finding with file:line evidence before editing.
2) Patch in atomic slices.
3) Run py_compile + ruff + ty + focused pytest on touched scope.
4) Push and check PR checks.
5) Update AGENTS_HANDOFF_NEXT_CYCLE.md and RECOVERY_BACKLOG.md.

Input report:
<paste structured report here>
```
