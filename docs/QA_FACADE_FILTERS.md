# QA Guide: Advanced Filters Facade

## Goal

Prevent runtime breakages caused by facade-to-module contract drift during refactor of `gui/gui_ssa.py` and `gui/ssa/gui_filters_*`.

## Design rule (mandatory)

1. `gui/gui_ssa.py` must call `ssa_gui_filters.<symbol>` only when:
   - symbol is reexported by `gui/ssa/gui_filters_advanced.py`, or
   - call is guarded via `getattr(ssa_gui_filters, "<symbol>", None)` with explicit fallback.
2. No direct unsafe call to optional facade symbol.

## Runtime safety rule (mandatory)

For optional/transition symbols:

- Primary path: call aggregated module symbol when present.
- Fallback path: call concrete submodule symbol (for example `gui_filters_advanced_ui`) when primary is absent.
- Last resort: log warning and return safe default.

## Test gate (mandatory)

Whenever a slice changes:

- `gui/gui_ssa.py`, or
- any file under `gui/ssa/gui_filters_*`

run these tests before push:

```bash
uv run pytest -q tests/test_gui_filters_facade_contract.py
uv run pytest -q tests/test_gui_filter_logic.py -k advanced_filters
uv run pytest -q tests/test_gui_filters_advanced_logic.py
```

## Coverage checklist

`tests/test_gui_filters_facade_contract.py` must cover:

1. primary facade symbol exists and is used;
2. primary missing and fallback works;
3. both missing and safe degradation path works (warning + safe return);
4. every `ssa_gui_filters.<symbol>` reference is either exported or explicitly guarded.

`tests/test_gui_filters_advanced_logic.py` must cover:

1. `solicitante` filtering behavior;
2. legacy alias compatibility (`responsavel_solicitante`);
3. active-state detection for `num_reprogramacoes`;
4. week-range filter behavior.
5. priority filters with dataset columns `grau_prioridade_emissao` and `grau_prioridade_planejamento`;
6. static check: keys produced by UI must be covered by logic or active detector.
7. reverse static check: keys consumed by logic/active detector must be either UI-produced or listed as legacy allowlist.
8. `responsavel_emissor` is intentionally out of advanced filter contract (disabled path); do not reintroduce key production/consumption without explicit scope approval and DB support.

Note:
- Derivadas special spreadsheets (`SSAs Derivadas e Relacionadas_*.xlsx`) are not part of this advanced-filter facade contract.
- They are handled by derivadas sync flow in importer, not by the main SSA extractor required-column gate.

## Current verified legacy allowlist

The reverse static check allows only these non-UI keys:

- `ano_emissao`
- `ano_emissao_exclude`
- `ano_execucao`
- `ano_execucao_exclude`
- `responsavel_solicitante`
- `responsavel_solicitante_exclude_values`

Any new non-UI key in logic or detector must be explicit and justified.

## Update 2026-02-17

- `responsavel_emissor` is now fully out of advanced filter UI assembly path.
- The panel no longer creates `adv_responsavel_emissor_*` controls, matching the existing logic contract that excludes this key.
- Contract remains: `solicitante`, `responsavel_programacao`, and `responsavel_execucao` are the supported responsavel filters.
- Derivadas utility button (`Especificas...`) now supports DB materialized view:
  - popup shows summary from `ssa_derivada_summary` for visible SSAs;
  - button can be enabled from DB-derived relations even if visible `derivada_de` series is empty/invalid.
- `ano_execucao` filter logic now relies on `semana_executada` only; `data_execucao` path was removed as dead code for current schema contract.
- Legacy migration behavior is now explicitly validated:
  - `ano_emissao` still works when `_values` keys are absent.
  - `ano_execucao_exclude=True` with `ano_execucao=<year>` excludes that year without accidental include/exclude collision.

## External IA report intake (mandatory)

When another IA sends findings:

1. Do not patch immediately.
2. Validate each finding with local evidence:
   - `rg -n "<pattern>" <file>`
   - `nl -ba <file> | sed -n "<start>,<end>p"`
3. Convert report to actionable list:
   - `id`, `severity`, `file:line`, `impact`, `minimal fix`, `minimal test`.
4. Apply only minimal-risk patches per slice.
5. Run gate after each slice:

```bash
uv run python -m py_compile <files>
uv run ruff check <files>
uv run ty check <files>
uv run pytest -q tests/test_gui_filters_facade_contract.py
uv run pytest -q tests/test_gui_filter_logic.py -k advanced_filters
uv run pytest -q tests/test_gui_filters_advanced_logic.py
```

6. Update `docs/RECOVERY_BACKLOG.md` for deferred non-blockers.

## PR checklist text (copy/paste)

```text
[ ] Facade contract preserved: every ssa_gui_filters.<symbol> is exported or guarded
[ ] Advanced-filters primary/fallback/no-handler tests green
[ ] Advanced-filters logic tests green (solicitante alias, reprogramacoes active-state, week range)
[ ] No unsafe optional symbol call added in gui/gui_ssa.py
```
