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
