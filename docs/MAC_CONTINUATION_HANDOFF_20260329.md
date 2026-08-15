# MAC Continuation Handoff (2026-03-29)

## Scope

- This handoff consolidates current operational status for continuing work on macOS.
- Use repository-relative paths only.
- Run commands from repository root.

## Current branch and commits

1. `dev` e a branch operacional.
2. Para capturar o estado exato no macOS:

```bash
git log --oneline -n 8
```

3. Commits minimos que devem existir no historico recente:
   - `147424ef` (`data_planilha` + imutabilidade `STE/SCA`)
   - `f115d715` (full rescan com `processadas` por default)
   - `81f05676` (doc sync host-agnostic inicial)

## Runtime behavior currently active

1. `data_planilha` column exists in schema and import path.
2. `STE` and `SCA` rows are immutable in update flow.
3. If incoming file has file-context but no trustworthy timestamp, update is blocked (insert new only).
4. Full rescan includes `docs_entrada/processadas` by default.
5. Explicit import is sorted by file datetime (older first, newer last).

## Matrix draft status (needs user validation)

Source docs:

- `docs/FORENSIC_UPDATE_CRITERIA_SSA_20260329.md`
- `docs/SSA_STATE_MATRIX_DRAFT_20260329.md`

Open validation items:

1. Exact placement/meaning of `SES`.
2. Exact role of `APL` in planning flow.
3. Whether `SCS/SCD` are mandatory or optional before `SCA`.
4. Policy for forward jumps when intermediate states are missing in newer sheets.

## Contract summary for update

1. Existing `STE`/`SCA`: no update.
2. New row with file-context but no reliable timestamp: no update (insert-only behavior).
3. Older snapshot does not overwrite newer snapshot.
4. `data_cadastro` is auxiliar/tie-break, not primary ordering source.

## macOS command baseline

```bash
uv run --python 3.13 python -m pytest -q
uv run --python 3.13 ruff check .
uv run --python 3.13 ty check .
```

Focused regression suite used in latest hotfix cycles:

```bash
uv run --python 3.13 python -m pytest -q \
  tests/test_upsert_behaviors.py \
  tests/test_import_run_report.py::test_run_importer_logic_full_rescan_enforces_subdir_policy_and_upsert_policy \
  tests/test_app_logic_filter_contract.py::test_get_filtered_data_reflects_updated_state_after_explicit_import \
  tests/test_app_logic_filter_contract.py::test_explicit_import_persists_data_planilha_iso_from_filename
```

## Notes

1. Do not infer legacy absolute Windows paths from historical docs; prefer repo-relative paths.
2. Two frozen baseline docs were intentionally not modified:
   - `docs/POLICY_BASELINE_V1_FROZEN.md`
   - `docs/POLICY_BASELINE_V1_1_FROZEN.md`

<!-- DOC_SYNC_MAC: 2026-03-30 contract-aligned -->
