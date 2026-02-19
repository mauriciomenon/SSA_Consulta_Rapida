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

## Writing guardrails (do not do)

1. Do not silence link/runtime warnings without fixing navigation behavior.
2. Do not claim completion if the reported user flow still fails.
3. Do not replace a functional bug with a generic fallback popup.
4. Do not close a slice without before/after evidence for the same user repro.
5. Do not optimize for "clean logs" over correct behavior.

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

## Current execution status (2026-02-18, ready to migrate)

- Branch and PR:
  - `codex/import-review`, PR `#31` open.
- Latest commits on head:
  - `aa454a40` docs handoff package expanded (strict starter + migration payload).
  - `80a73363` details dialog baseline locked at `20/80` with migration guardrails.
  - `24024662` real split enforcement via `QSplitter`.
- Current PR checks snapshot:
  - external blocked by plan limit: `code/snyk`, `security/snyk`.
  - core static/security checks in pass (DeepScan, DeepSource, GitGuardian, Socket, semgrep, submit-pypi, cubic).

## Scope lock from user triage

- Do not execute in this cycle:
  1. remove `if df is None` defensive branch.
  2. add new lock layers in stream scripts.
  3. broad race-condition refactor in `gui/workers`.
- Lint policy for this cycle:
  - ignore `E501` findings.

## Latest update (2026-02-19, critical filters-tab overlap fix)

- Head commit for this fix: `d3d9410f`.
- Root cause:
  - vertical area allocation between main table and bottom panel in `Filtros` tab was not hard constrained for low-row scenarios.
- Minimal fix applied in `gui/gui_ssa.py`:
  - table min height set to `220`;
  - vertical stretch set to `6` (table) and `4` (bottom panel).
- Regression lock:
  - `tests/test_gui_filter_logic.py::test_filters_tab_layout_keeps_bottom_panel_below_table_with_few_rows`.
- Validation evidence:
  - `py_compile`, `ruff`, `ty` green for touched scope;
  - focused pytest gates green, including advanced-filters suites;
  - runtime geometry matrix check reported no overlap in tested combinations.
- Rule for next chat:
  1. preserve `table min height + vertical stretch 6/4` unless user asks explicit layout change;
  2. if changing this area, provide before/after geometry evidence with numeric values.

## Latest update (2026-02-18, behavior and dialog baseline)

- Double-click details dialog (`gui/ssa/gui_details.py`) baseline is now:
  - split: `20/80` (left derivadas / right details),
  - min size: `700x650`,
  - fonts: left `12`, right `12`, labels `11`.
- Implementation detail that must be preserved:
  - split is enforced with `QSplitter` + explicit `setSizes` + stretch factors.
  - do not rely on ratio constants alone.
- Behavior rule for next IA:
  1. explain root cause before patching UI regressions;
  2. never claim visual fix without constraint validation;
  3. provide numeric before/after values in final report.

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
6) For UI ratio fixes, validate layout constraints (`minimumWidth`, splitter/layout manager) and report exact values.

Input report:
<paste structured report here>
```

## Copy/paste full starter (strict mode)

```text
Trabalhe no repo /Users/menon/git/SSA_Consulta_Rapida

Contexto:
- Branch atual: codex/import-review
- PR alvo: #31 (base dev)
- Objetivo: fechar PR com estabilidade e patch minimo

Regras:
1. Nao criar branch nem PR novo.
2. Nao fazer refactor amplo.
3. Nao alterar layout GUI sem pedido explicito.
4. Manter dialogo de detalhes derivadas em baseline fixa:
   - split 20/80
   - min size 700x650
   - fontes: 12/12/11
   - usar QSplitter com sizes reais
5. Sem acentos/cedilha/emojis/emdash em codigo, docs e mensagens tecnicas.
6. Nao ocultar erro real com except vazio/suppress indevido.

Leitura obrigatoria antes de iniciar:
1. docs/AGENTS_HANDOFF_NEXT_CYCLE.md
2. docs/NEXT_CHAT_MIGRATION.md
3. docs/RECOVERY_BACKLOG.md
4. docs/QA_FACADE_FILTERS.md
5. AGENTS.md

Sequencia obrigatoria de ciclo:
1) evidenciar problema com arquivo:linha e repro
2) propor diff minimo antes de editar
3) implementar slice pequeno
4) validar local
5) commit atomico
6) push
7) checar checks e comentarios de PR
8) backlog para nao bloqueante

Fluxo por slice:
1) validar evidencia local (rg -n + nl -ba)
2) patch minimo
3) gate local
4) commit atomico
5) push
6) checar PR checks

Gate tecnico:
- uv run python -m py_compile <files>
- uv run ruff check <files>
- uv run ty check <files>
- uv run pytest -q <tests focados>

Cuidados de seguranca e operacao:
1. Nao comitar segredos e arquivos locais de ambiente.
2. Nao usar comandos git destrutivos.
3. Nao esconder erro real com fallback generico.
4. Nao alterar schema/layout sem aprovacao explicita.
5. Se aparecer mudanca fora de escopo, pausar e confirmar com usuario.

Gate extra se tocar facade de filtros:
- uv run pytest -q tests/test_gui_filters_facade_contract.py
- uv run pytest -q tests/test_gui_filter_logic.py -k advanced_filters
- uv run pytest -q tests/test_gui_filters_advanced_logic.py

Status checks conhecido:
- code/snyk fail por limite de plano
- security/snyk fail por limite de plano
- restante: tratar somente bloqueio real de codigo

Relatorio final por slice:
- commit hash
- testes executados
- checks PR
- pendencias reais
```
