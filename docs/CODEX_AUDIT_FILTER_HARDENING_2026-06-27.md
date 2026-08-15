# Auditoria Codex — Filter/GUI Hardening pos-v4.43

Documento de handoff para Codex. Referencia permanente de diagnostico: relatorio Cursor A-K (bugs H1-H7, slices J1-J6, plano Codex Slices 0-8).

---

## 1. Metadata

| Campo | Valor |
|-------|-------|
| Repositorio | `/Users/menon/git/SSA_Consulta_Rapida` |
| Branch | `dev` |
| HEAD de entrada do DOC_SYNC residual | `75c30f2f681a2303309cce9d51d9bd2da788fdc2` |
| HEAD de entrada data | 2026-07-06 00:48:03 -0300 |
| HEAD de entrada titulo | DOC_SYNC: close filter hardening audit statuses |
| Baseline local atual | `4ae43f05b0d81d15b7b224a09dcac7dfb316c915` — DOC_SYNC: promote local baseline to 4.44 |
| Baseline local data | 2026-07-06 00:46:00 -0300 |
| Tags locais | `v4.43` -> `9e36576`; `v4.44` -> `4ae43f05` |
| Ahead vs `origin/dev` | **66 commits** na entrada do DOC_SYNC residual; **67** apos `7eab54b5`; **68** apos `54bcbc002af3db8877a3b718c105d808a0d5381b`; **74** apos `4ac834b23fe243f801aac4995b0c11efa6fe62fe` |
| Merge-base `origin/dev` | `ae36e281fa92432b292cf754368e9249a1b9f35b` |
| Workspace | tracked limpo; untracked `docs/handoffs/SKILLS_*` e `quality_gates_output.jsonl` fora do app |
| Report anterior (referencia) | HEAD `f8239fdfe2e8e97b56bd73c705acbc22281f82ee` (2026-06-27 17:28:30 -0300) |
| Commits pos-baseline v4.43 | **66** na entrada (`9e36576..75c30f2f`); **74** apos P2 runtime cleanup |
| Push/fetch | **bloqueado**: GitHub retorna HTTP 403 por conta suspensa |

---

### 1.1 Atualizacao P2 local — 2026-07-06

- `bd76ace31d77d98455e7e6125e698164bde99e9a` (2026-07-06 10:28:11 -0300, `STABILITY_PATCH: replace runtime select star queries`) fechou P2 `SELECT *` no runtime (`armazenamento`, `gui`, `core`, `scripts`).
- Busca runtime: `rg -n "SELECT \* FROM" armazenamento gui core scripts` retornou sem matches; residuos ficam em testes/fixtures e SQL customizado historico.
- H7/J2 medidos sem patch runtime: smoke performance `4 passed, 2 deselected in 3.87s`; contratos filter/cache `54 passed in 26.91s`; RSS pequeno delta 6.3 MB; 50k rows/3 ciclos delta 4.5 MB; maior stage `column=8.31ms`.
- J5 medido sem patch runtime: `tests/test_derivadas_cli.py`, `tests/test_derivadas_sync_controller.py`, `tests/test_import_derivadas_trigger.py`, `tests/test_scenario_derivada_checkbox_click_qt.py` passaram (`40 passed in 4.97s`).
- Decisao P2: nao aplicar patch H7/J2/J5 sem hotspot; manter como medicao documentada e reabrir somente com falha real, dados maiores ou novo budget.

---

## 2. Tabela cronologica — snapshot inicial pos-9e36576

> Snapshot historico de auditoria. O estado corrente pos-2026-06-29 esta consolidado nas secoes 5, 7 e 10; a tabela nao foi expandida para todos os 57 commits para evitar duplicar o `git log`.

Legenda autor sessao:
- **Codex** — commits runtime/plano Codex Slices 0-3 e rodadas pos-testes (`b2a51b81`, `0d8fdb4b`, `5ca3b193`, `aa11f35b`)
- **Cursor** — suite contract/scenario Qt, DOC_SYNC auxiliar, fechamento H6 refresh path (`faeb8f19`, `37ad59d0`)

| # | Hash completo | Data/hora -0300 | Titulo | Categoria | Autor sessao | --stat resumido |
|---|---------------|-----------------|--------|-----------|--------------|-----------------|
| 1 | `7eef5d314ff5c1685ffdda388eec6278149b8787` | 2026-06-27 16:40:46 | HOTFIX_BLOCKER: honor advanced options dirty state | HOTFIX_BLOCKER | Codex | `gui_filters_advanced_refresh.py` (+1 param), `gui_filters_advanced_ui.py`, tests refresh (+42/-3) |
| 2 | `ad4a2cffb30b2d9cf60ade3d82a38ff8b2f80736` | 2026-06-27 16:58:49 | HOTFIX_BLOCKER: surface advanced mask evaluation errors | HOTFIX_BLOCKER | Codex | `gui_filters_advanced_logic.py` `_mask_any` raise, tests logic (+16/-4) |
| 3 | `6e230bcf534f90ab9895595d5fe3f6b7034e020d` | 2026-06-27 17:05:24 | STABILITY_PATCH: align advanced filter refresh contracts | STABILITY_PATCH | Codex | `filter_gui_ssa_mixin.py`, `filter_domain_rules.py` mapa visual/exec, tests (+28/-9) |
| 4 | `079908f48974932a53a224b32426d9e9a89bc479` | 2026-06-27 17:18:53 | STABILITY_PATCH: vectorize derivada relation normalization | STABILITY_PATCH | Codex | `gui_filters_advanced_logic.py` normalizacao derivada vetorizada (+20/-5) |
| 5 | `84178418260202a00b39d7e3e811c1c77b7182b7` | 2026-06-27 17:23:14 | HOTFIX_BLOCKER: hash GUI filter worker cache token | HOTFIX_BLOCKER | Codex | `filter_gui_ssa_mixin.py` `build_dataframe_filter_hash` no token (+35/-4) |
| 6 | `f8239fdfe2e8e97b56bd73c705acbc22281f82ee` | 2026-06-27 17:28:30 | STABILITY_PATCH: defer general search sort before post filters | STABILITY_PATCH | Codex | `filter_gui_ssa_mixin.py` `on_filter_finished` sort gate (+52/-1) |
| 7 | `874f48c7c98fa0a7a65586e5b5198159b3084a45` | 2026-06-27 19:32:44 | STABILITY_PATCH: add contract and scenario regression tests for filter pipeline | tests | Cursor | 14 arquivos novos contract/scenario + helpers (+1431) |
| 8 | `211b2524526590e4e1bdcde3ef3524e9972df7fd` | 2026-06-27 19:38:26 | STABILITY_PATCH: extend filter regression tests for P1 P2 audit gaps | tests | Cursor | 8 arquivos contract/scenario (+320/-1) |
| 9 | `54357fda86a8ccdecf717be9a6996969dc5359b0` | 2026-06-27 19:43:25 | STABILITY_PATCH: add refined filter regression tests round 3 | tests | Cursor | 4 arquivos contract/scenario (+177) |
| 10 | `db27ebb22e76903ca3fd0e6c57409eba6a07d847` | 2026-06-27 19:48:00 | STABILITY_PATCH: add refined filter regression tests round 4 | tests | Cursor | 7 arquivos undo/cache/reprogramacoes (+232) |
| 11 | `936fb22bb5978547260bcd780f504d999b6115dc` | 2026-06-27 20:10:10 | STABILITY_PATCH: add race/waste tests and refine filter regression suite | tests | Cursor | 27 arquivos race/cancel/waste (+892/-149) |
| 12 | `9550a79684a4642a7b9abea040b053d783cfd5b3` | 2026-06-27 20:35:28 | STABILITY_PATCH: five-pass refinement of filter regression tests | tests | Cursor | 24 arquivos refinamento asserts (+684/-145) |
| 13 | `14fb4e2ba5a8b0ea51610488ea18976ee50c3467` | 2026-06-27 20:44:18 | DOC_SYNC: add local command hooks rules for agents | DOC_SYNC | Cursor | `COMMAND_HOOKS.md` (+69) |
| 14 | `b2a51b81b8ee48dfa82364bd7410c80a0074610b` | 2026-06-27 20:53:23 | HOTFIX_BLOCKER: keep advanced failure count status in sync | HOTFIX_BLOCKER | Codex | `gui_filters_advanced_ui.py` status pos-falha apply (+15/-7) |
| 15 | `33b07012e58c6dedfc5e694c7731967a471f9104` | 2026-06-27 20:55:56 | STABILITY_PATCH: cover mid-search filter worker cancel | tests | Cursor | `test_contract_filter_worker_cancel_race.py` QThread mid-search (+49) |
| 16 | `0d8fdb4b2184b1e5b93ab27d7fe10e0a5a635cae` | 2026-06-27 21:09:00 | STABILITY_PATCH: skip advanced options cache read on clean hit | STABILITY_PATCH | Codex | `gui_filters_advanced_ui.py` fast-path antes de `_read` (+13/-8) |
| 17 | `aa11f35bc171a37be49c250259473d1721e21d9b` | 2026-06-27 21:13:56 | DOC_SYNC: record local filter hardening after v4.43 | DOC_SYNC | Codex | `CHANGELOG.md` [Unreleased] (+14) |
| 18 | `5ca3b19369afc44ada3b704e58772611e60a9c3c` | 2026-06-27 21:19:24 | STABILITY_PATCH: reduce option value materialization | STABILITY_PATCH | Codex | `filter_domain_rules.py` `collect_nonempty_column_values` (+2/-2) |
| 19 | `0abc7d4a1940995739c230bd8b06f948aab3276c` | 2026-06-27 22:06:11 | STABILITY_PATCH: add GUI click, grid, cancel, and SQL policy tests | tests | Cursor | 7 arquivos clicks/grid/cancel/SQL (+462/-2) |
| 20 | `213a416dce95b0bd70ef15f462ab7c792f8973a0` | 2026-06-27 22:18:55 | STABILITY_PATCH: close deferred GUI gaps and refine with five passes | tests | Cursor | 9 arquivos grid/paginator/column clicks (+398/-51) |
| 21 | `faeb8f198862d6097e538505f3652f2ba7efeb66` | 2026-06-27 22:25:14 | HOTFIX_BLOCKER: sync status when advanced filter mask fails on refresh | HOTFIX_BLOCKER | Cursor | `filter_gui_ssa_mixin.py`, `gui_filters_advanced_ui.py` H6 refresh (+46/-15) |
| 22 | `37ad59d0` | 2026-06-27 | HOTFIX_BLOCKER: preserve H6 status when mask fails after search | HOTFIX_BLOCKER | Cursor | bool return + on_filter_finished early return + finish UI skip_status |
| 23 | `1a8b2c5d` | 2026-06-27 | STABILITY_PATCH: narrow advanced apply except to mask errors only | STABILITY_PATCH | Cursor | `_refresh_after_advanced_filters_apply` except scope |
| 24 | `e5ab1585` | 2026-06-27 | STABILITY_PATCH: treat SSA_CACHE_MAX_MB=0 as unlimited cache | STABILITY_PATCH | Cursor | `filter_cache.py` zero env = unlimited |
| 25 | `b3e0b740` | 2026-06-27 | STABILITY_PATCH: cover dirty gate executor menu rebuild | STABILITY_PATCH | Cursor | `test_dirty_refresh_rebuilds_executor_menu_checks` |

**Nota categoria commit #21:** rotulo `STABILITY_PATCH` no titulo git, mas conteudo funcional e **HOTFIX H6** (recovery pos-`mask.any()` no refresh pos-busca). Recomendacao: amend/relabel para `HOTFIX_BLOCKER` antes de push, se politica de categoria for rigida.

---

## 3. Diff resumido — commits runtime (nao-tests)

### 3.1 `7eef5d31` — Slice 1 / P0 dirty cache

**Arquivos:** `gui/ssa/gui_filters_advanced_refresh.py`, `gui/ssa/gui_filters_advanced_ui.py`

**Mudanca-chave:**
- `get_cached_advanced_filter_option_values(..., force_refresh: bool = False)`
- Gate cache: `if not force_refresh and cache.get("df_key") == df_key ...`
- `_read_advanced_filter_ui_state` passa `force_refresh=bool(_adv_options_dirty)`

**Funcoes:** `get_cached_advanced_filter_option_values`, `_read_advanced_filter_ui_state`

---

### 3.2 `ad4a2cff` — Slice 2 / H6 raise

**Arquivo:** `gui/ssa/gui_filters_advanced_logic.py`

**Mudanca-chave:**
- `_mask_any`: de `logger.debug` + `return False` para `raise RuntimeError(...)` com contexto

**Linhas-chave:** ~101-108

---

### 3.3 `6e230bcf` — Slice 3 / H1 + H2 + J6

**Arquivos:** `gui/mixins/filter_gui_ssa_mixin.py`, `gui/ssa/filter_domain_rules.py`

**Mudanca-chave:**
- Cache refresh: `if has_post_search_filters or has_excluded_terminal_status` (terminal entra no cache key path)
- `_refresh_after_filter_change`: `has_post_search_filters` **nao** inclui `has_excluded_terminal_status`
- `ADVANCED_FILTER_VISUAL_COLUMN_MAP`: `ano_execucao*` e `semana_execucao_*` -> colunas `semana_executada` / `semana_cadastro`

**Funcoes:** `_apply_filter_refresh_filters_and_update_cache`, `_refresh_after_filter_change`, mapa visual

---

### 3.4 `079908f4` — J5 parcial (normalizacao serie)

**Arquivo:** `gui/ssa/gui_filters_advanced_logic.py`

**Mudanca-chave:**
- `_normalize_derivada_relation_series`: lookup vetorizado via `Series.map` + `fillna` em vez de loop Python por indice

**Nota:** arvore derivada `itertuples` permanece intacta (Slice 6 deferido).

---

### 3.5 `84178418` — H3 parcial (worker token)

**Arquivo:** `gui/mixins/filter_gui_ssa_mixin.py`

**Mudanca-chave:**
- Import `build_dataframe_filter_hash`
- `_filter_worker_df_token_cache` tupla 4 -> 5 elementos incluindo `content_hash`
- Token repr usa hash de conteudo, nao so `id(source)`

**Funcao:** metodo de token do worker GUI (~601-631)

---

### 3.6 `f8239fdf` — H5/J1 parcial (sort defer)

**Arquivo:** `gui/mixins/filter_gui_ssa_mixin.py`

**Mudanca-chave:**
- `on_filter_finished`: calcula `has_post_search_filters` via `_filter_refresh_flags()` **incluindo** terminal
- Sort por `numero_ssa` so roda se `not has_post_search_filters`
- `except` em flags: log debug, `has_post_search_filters=False` (sort pode rodar indevidamente)

**Funcao:** `on_filter_finished` (~902-931)

---

### 3.7 `b2a51b81` — H6 producao (apply path)

**Arquivo:** `gui/ssa/gui_filters_advanced_ui.py`

**Mudanca-chave:**
- `_refresh_after_advanced_filters_apply` `except`: chama `update_filter_status_display` com `len(df_exibido)` / `len(df_completo)`

**Gap fechado:** label "0 de 0 SSAs" vs linhas visiveis apos falha no apply avancado.

**Substituido/refatorado em `faeb8f19`:** logica extraida para `_sync_status_after_advanced_filter_failure`.

---

### 3.8 `0d8fdb4b` — Slice 1 follow-up (ordem gate)

**Arquivo:** `gui/ssa/gui_filters_advanced_ui.py`

**Mudanca-chave:**
- `_refresh_advanced_filter_options`: fast-path **antes** de `_read_advanced_filter_ui_state`
- Clean hit: monta `AdvancedFilterUIState` do cache sem chamar `get_cached_advanced_filter_option_values`
- Valida `isinstance(cached_values, AdvancedFilterOptionValues)`

**Funcao:** `_refresh_advanced_filter_options` (~1931-1948)

---

### 3.9 `5ca3b193` — H7 parcial

**Arquivo:** `gui/ssa/filter_domain_rules.py`

**Mudanca-chave:**
- `collect_nonempty_column_values`: remove `dropna()` redundante e `astype(str)` final
- Mantem `tolist()` O(n) — ganho micro (~12% ms em benchmark 50k local Codex)

**Linhas:** ~51-55

---

### 3.10 `faeb8f19` — H6 refresh pos-busca (HOTFIX funcional)

**Arquivos:** `gui/mixins/filter_gui_ssa_mixin.py`, `gui/ssa/gui_filters_advanced_ui.py`

**Mudanca-chave:**
- Novos helpers: `_ADVANCED_FILTER_FAILURE_SUFFIX`, `_is_advanced_filter_mask_runtime_error`, `_sync_status_after_advanced_filter_failure`
- `_refresh_after_filter_change`: `try/except RuntimeError` em `_apply_filter_refresh_filters_and_update_cache`; se erro de mascara, log warning, sync status, **return** (mantem `df_exibido`)
- `_refresh_after_advanced_filters_apply`: reusa `_sync_status_after_advanced_filter_failure` com suffix explicito

**Funcoes:** `_refresh_after_filter_change` (~2674-2699), helpers UI (~1548-1575)

---

## 4. Trabalho Cursor (commits Cursor-only)

| Commit | O que fez |
|--------|-----------|
| `874f48c7` | Infra base: `tests/_helpers/contract_data_builders.py`, `gui_scenario_harness.py`; 12 contract + 4 scenario cobrindo cache, refresh semantics, dirty gate, worker token, visual state, smoke budget |
| `211b2524` | Gaps P1/P2: data loader query, responsavel budget, derivada notice Qt, H4 df_completo scope, sort semantics J1 |
| `54357fda` | Round 3: derivadas tree budget, responsavel options scenario, smoke budget ampliado |
| `db27ebb2` | Round 4: search undo source, cache context digest, reprogramacoes, undo restore, stale request |
| `936fb22b` | Race/waste: stale load guard, pipeline waste, worker cancel race, helpers centralizados |
| `9550a796` | Five-pass refinement: asserts mais fortes, guards false-positive, contrato H6 count-label documentado |
| `14fb4e2b` | DOC_SYNC: `COMMAND_HOOKS.md` restricoes agentes locais |
| `33b07012` | Cancel cooperativo mid-search: QThread real cancel dentro de `apply_general_search_terms` |
| `0abc7d4a` | GUI clicks reais, grid paginator order, cancel mid-search scenario, derivada checkbox, labels basicos, SQL policy contract |
| `213a416d` | Fechamento gaps GUI: column filter clicks, SSA display grid, paginator prev/page3, derivada positive path, cancel optimistic display, LIMIT+OFFSET SQL |
| `faeb8f19` | HOTFIX H6 refresh path: status sync + suffix apos falha `mask.any()` em `_refresh_after_filter_change` |
| `37ad59d0` | HOTFIX H6 on_filter_finished: early return preserva suffix quando refresh retorna False |

**Commits Codex (nao listados acima):** `7eef5d31`, `ad4a2cff`, `6e230bcf`, `079908f4`, `84178418`, `f8239fdf`, `b2a51b81`, `0d8fdb4b`, `aa11f35b`, `5ca3b193`

**Baseline Slice 0 (pre-tabela, Codex):** `9e36576` DOC_SYNC 4.43 + tag `v4.43`

---

## 5. Matriz plano A-K vs report antigo (HEAD f8239fdf)

Referencia report #1: HEAD `f8239fdf`, ahead 11, ~40% plano Codex entregue.
Referencia operacional atual: entrada do DOC_SYNC residual em `75c30f2f681a2303309cce9d51d9bd2da788fdc2` (66 ahead); apos P2 runtime cleanup, o branch local esta 74 commits ahead. A coluna `Runtime cf85ec83` abaixo e snapshot historico da rodada 2026-06-29.

| Item | Report f8239fdf | Runtime cf85ec83 (snapshot historico) | Delta |
|------|-----------------|----------------------|-------|
| **Slice 0** DOC_SYNC 4.43 | Entregue | Entregue | — |
| **Slice 1** cache/dirty | Parcial | **Entregue** | `0d8fdb4b` fecha ordem gate + testes Qt |
| **Slice 2** H6 `_mask_any` | Parcial (raise sem GUI) | **Entregue** | `b2a51b81` + `9b2005d5` cobrem apply e refresh |
| **Slice 3** H1/H2/J6 | Entregue | Entregue | testes visuais Qt reforcados (Cursor) |
| **Slice 4** smoke RSS/ms | Pendente | **Parcial** | `@pytest.mark.performance` + medicao 50k; CI job dedicado pendente |
| **Slice 5** J2 deep copies | Pendente | **Medido/deferido** | contracts deep_copy existem; 2026-07-06 RSS delta 4.5 MB em 50k/3 ciclos, sem hotspot |
| **Slice 6** J5 arvore derivadas | Parcial (~15%) | **Medido/deferido** | contratos derivadas passaram (`40 passed in 4.97s`); sem patch runtime |
| **Slice 7** H4 universo opcoes | Pendente | **Entregue** | contrato atual documentado: opcoes avancadas usam `df_completo` |
| **Slice 8** SQL/load SELECT * | Pendente | **Entregue** | `bd76ace31d77d98455e7e6125e698164bde99e9a`; runtime sem `SELECT *` em `armazenamento`, `gui`, `core`, `scripts` |
| **H1** mapa visual execucao | Resolvido | Resolvido | — |
| **H2** terminal vs post-search | Resolvido | Resolvido | — |
| **H3** worker cache token | Parcial | Entregue funcionalmente | hash conteudo entregue; baseline de custo do hash fica como perf follow-up |
| **H4** opcoes de universo global | Pendente | Entregue | contrato atual: opcoes avancadas usam `df_completo` |
| **H5** sort antes pos-filtros | Parcial | Entregue funcionalmente | contrato `for_sort_defer` e sort reuse existem; manter sem refactor amplo |
| **H6** contador vs df_exibido | Parcial | **Entregue** | fix producao + refresh mixin + on_filter_finished (`faeb8f19`, `37ad59d0`) |
| **H7** materializacao menus | Pendente | **Medido/deferido** | 2026-07-06 maior stage observado `column=8.31ms` em 50k; sem patch runtime |
| **J1** sort unico por ciclo | Parcial | Parcial | `ssa_sorted_for_display` reduz re-sort; sem prova formal de max 1 sort/ciclo |
| **J2** deep copies | Pendente | Medido/deferido | baseline RSS registrado; contratos de isolacao continuam verdes |
| **J3** contratos cache | Resolvido | Resolvido | testes ampliados |
| **J4** opcoes pos-busca | Pendente | Entregue | entregue junto com H4 conforme contrato `df_completo` |
| **J5** derivadas performance | Parcial | Medido/deferido | contratos CLI/sync/import/Qt passaram; sem hotspot |
| **J6** terminal-only refresh | Resolvido | Resolvido | — |
| **has_post_search_filters** | Parcial (semantica dupla) | **Parcial estabilizado** | `_compute_has_post_search_filters(..., for_sort_defer)` documenta divergencia; trocar por novo helper seria refactor sem ganho claro |
| **paginate** hotspot | Pendente | **Entregue** | `977e67cdc2129e1296bdf39a40a8705db6fda66c` reduz duplicate render; 50k: paginate avg ~0.035ms, render avg ~4.144ms |
| **Push/checks remotos** | Pendente | Pendente | 62 commits locais |
| **Regressao contract/scenario** | Ausente | **Entregue** | 34 arquivos test_contract_* + test_scenario_* |

---

## 6. Delta vs report antigo (pos-f8239fdf)

Commits novos desde `f8239fdf` (15 commits):

### 6.1 Runtime Codex

| Commit | Impacto |
|--------|---------|
| `b2a51b81` | H6: contador sincronizado no `except` de apply avancado |
| `0d8fdb4b` | Slice 1: fast-path cache clean hit; evita recomputacao O(n) desnecessaria |
| `5ca3b193` | H7 parcial: menos passes em `collect_nonempty_column_values` |

### 6.2 DOC_SYNC

| Commit | Impacto |
|--------|---------|
| `aa11f35b` | CHANGELOG [Unreleased] registra hotfixes, deferidos, validacao |
| `14fb4e2b` | COMMAND_HOOKS.md (fora escopo filtro, mas no diff local) |

### 6.3 Suite tests Cursor (874f48c7 .. 213a416d)

- **15+ contract** + **19+ scenario** arquivos (total 34 paths `test_contract_*` / `test_scenario_*`)
- Cobertura nova: cancel mid-search QThread, stale load, pipeline waste, undo, cache digest, SQL LIMIT/OFFSET policy, clicks reais, paginator, grid SSA display, derivada checkbox, visual labels
- Five-pass refinement em asserts e helpers compartilhados

### 6.4 Runtime Cursor — fechamento H6 cadeia

| Commit | Impacto |
|--------|---------|
| `faeb8f19` | H6 refresh pos-busca: captura `AdvancedFilterMaskError`; mantem linhas; status com suffix |
| `37ad59d0` | H6 on_filter_finished: bool return + early return sem sobrescrever status |

### 6.5 O que o report f8239fdf ainda acertava e permanece

- Deep copies J2 deferidos (CHANGELOG explicito)
- Arvore derivadas J5 deferida por benchmark 50k
- Semantica dupla `has_post_search_filters` mantida de proposito e documentada por parametro `for_sort_defer`
- Hotspot paginate original fechado por `977e67cdc2129e1296bdf39a40a8705db6fda66c`; nova medicao 50k: paginate avg ~0.035ms, render avg ~4.144ms
- Reviews externos (clawpatch/coderabbit/semgrep) nao fechados
- Push atomico por slice nao executado

### 6.6 Regressoes de classificacao / processo

- `9b2005d5` rotulado STABILITY_PATCH mas e HOTFIX H6 funcional
- Commits Codex pos-Slice 0 executados sem aprovacao literal slice-a-slice (contexto conversa; nao bloqueio tecnico atual)

---

## 7. Pendencias abertas (ordenadas P0 -> P2)

### P0 — bloqueantes operacionais

| ID | Pendencia | Evidencia | Acao sugerida |
|----|-----------|-----------|---------------|
| P0-1 | **Push/checks remotos bloqueados** | branch local fica 74 commits ahead apos P2 runtime cleanup; GitHub retorna HTTP 403 por conta suspensa | Nao fazer fetch/push/PR ate desbloquear GitHub; depois comparar divergencia antes de propor push |
| P0-2 | **Checks remotos indisponiveis** | sem PR/checks confiaveis enquanto GitHub retorna HTTP 403 | Reavaliar apos desbloqueio remoto; gates locais seguem como fonte temporaria |
| P0-3 | **Relabel `faeb8f19`** | Concluido no rebase (HOTFIX_BLOCKER) | — |
| P0-4 | **Smoke visual GUI real H6** | Fechado em 2026-07-06 com janela Qt real, falha simulada de mascara avancada, 4/4 linhas preservadas e status de falha explicito | Evidencia local reportada na conversa; screenshot nao commitado |

### P1 — funcional / contrato

| ID | Pendencia | Evidencia | Acao sugerida |
|----|-----------|-----------|---------------|
| P1-1 | **has_post_search_filters unificar** | Parametro `for_sort_defer` ja explicita contrato; refactor amplo nao justificado | Manter; reabrir so com regressao ou simplificacao menor comprovada |
| P1-2 | **H5/J1 sort unico** | H5 entregue funcionalmente; J1 segue sem spy formal de max 1 sort/ciclo | Adicionar teste se nova regressao aparecer |
| P1-3 | **Paginate hotspot runtime** | Fechado em `977e67cdc2129e1296bdf39a40a8705db6fda66c`; 50k paginate avg ~0.035ms | Manter smoke performance como guarda |
| P1-4 | **Notice H6 explicita** | Fechado em `671554e7bc54b47ef2b5f5e262a524a32a61864c` | Manter testes H6 apply/refresh |
| P1-5 | **Header visual `[f]` semana_executada** | Coberto por `test_scenario_visual_filter_state_qt.py` (`ano_execucao` marca `semana_executada`) | Manter cobertura Qt |

### P2 — performance / decisao produto

| ID | Pendencia | Evidencia | Acao sugerida |
|----|-----------|-----------|---------------|
| P2-1 | **Slice 5 J2 deep copies** | Medido 2026-07-06; contracts existem | Sem patch runtime ate haver hotspot/RSS acima do budget |
| P2-2 | **Slice 6 J5 arvore derivadas** | Medido 2026-07-06; contratos derivadas verdes | Reabrir so com dados reais maiores ou budget novo |
| P2-3 | **Slice 7 H4/J4 universo opcoes** | Entregue conforme contrato atual `df_completo` global | Reabrir somente com decisao produto para universo filtrado |
| P2-4 | **Slice 8 SELECT *** | Entregue em `bd76ace31d77d98455e7e6125e698164bde99e9a` | Manter tests de policy; residuos em testes sao historicos/custom SQL |
| P2-5 | **H7 estrutural** | Medido 2026-07-06; sem hotspot | Reabrir com benchmark falhando ou dataset maior |
| P2-6 | **CI job performance** | `-m "not performance"` no pytest normal | Workflow dedicado com marker performance |
| P2-7 | **except flags L917-921** | Falha flags -> sort indevido silencioso | Tratar como erro visivel ou fail-closed sem sort |
| P2-8 | **Fonte Qt headless** | Fechado em `cf85ec83ca6157265d57bef267748b108e9ecf41`; smoke direto usa `Helvetica Neue` no macOS e remove aviso `Sans Serif` | Manter lista por plataforma; nao alterar layout sem screenshot/smoke |

---

## 8. Comandos de verificacao por commit / slice

### 8.1 Gates globais (HEAD atual)

```bash
cd /Users/menon/git/SSA_Consulta_Rapida

# Sintaxe runtime tocado pos-v4.43
uv run --python 3.13 python -m py_compile \
  gui/mixins/filter_gui_ssa_mixin.py \
  gui/ssa/gui_filters_advanced_ui.py \
  gui/ssa/gui_filters_advanced_logic.py \
  gui/ssa/gui_filters_advanced_refresh.py \
  gui/ssa/filter_domain_rules.py \
  gui/ssa/filter_refresh_pipeline.py

uv run --python 3.13 ruff check \
  gui/mixins/filter_gui_ssa_mixin.py \
  gui/ssa/gui_filters_advanced_ui.py \
  gui/ssa/gui_filters_advanced_logic.py \
  gui/ssa/gui_filters_advanced_refresh.py \
  gui/ssa/filter_domain_rules.py \
  gui/ssa/filter_refresh_pipeline.py

uv run --python 3.13 ty check \
  gui/mixins/filter_gui_ssa_mixin.py \
  gui/ssa/gui_filters_advanced_ui.py \
  gui/ssa/gui_filters_advanced_logic.py \
  gui/ssa/filter_domain_rules.py
```

### 8.2 Por commit runtime

| Commit | Comando pytest focado |
|--------|----------------------|
| `7eef5d31` Slice 1 | `uv run --python 3.13 pytest -q tests/test_gui_filters_advanced_refresh.py -k force_refresh` |
| `ad4a2cff` Slice 2 | `uv run --python 3.13 pytest -q tests/test_gui_filters_advanced_logic.py -k mask_any_raises` |
| `6e230bcf` Slice 3 | `uv run --python 3.13 pytest -q tests/test_filter_refresh_pipeline.py tests/test_gui_filters_advanced_logic.py -k "terminal or semana_executada"` |
| `079908f4` J5 parcial | `uv run --python 3.13 pytest -q tests/test_gui_filters_advanced_logic.py -k derivada` |
| `84178418` H3 | `uv run --python 3.13 pytest -q tests/test_filter_worker.py -k token` |
| `f8239fdf` H5/J1 | `uv run --python 3.13 pytest -q tests/test_gui_filter_logic.py -k defer_general_sort` |
| `b2a51b81` H6 apply | `uv run --python 3.13 pytest -q tests/test_scenario_filter_refresh_mixin_qt.py -k mask_any_failure_surfaces` |
| `0d8fdb4b` Slice 1 gate | `uv run --python 3.13 pytest -q tests/test_scenario_adv_options_dirty_gate_qt.py tests/test_scenario_adv_options_load_waste_qt.py` |
| `5ca3b193` H7 | `uv run --python 3.13 pytest -q tests/test_contract_collect_nonempty_budget.py` |
| `faeb8f19` H6 refresh | `uv run --python 3.13 pytest -q tests/test_scenario_filter_refresh_mixin_qt.py -k "mask_any_failure"` |
| `37ad59d0` H6 on_filter_finished | `uv run --python 3.13 pytest -q tests/test_scenario_filter_refresh_mixin_qt.py::TestScenarioFilterRefreshMixin::test_mask_any_failure_via_on_filter_finished_keeps_status` |

### 8.3 Por slice / tema (suite)

```bash
# Slice 0 baseline
grep -E '4\.43' VERSION config/version.json
git show v4.43 --no-patch

# Contract + scenario (nao performance) — gate pos-rodadas Cursor
uv run --python 3.13 pytest -q \
  tests/test_contract*.py tests/test_scenario*.py \
  -m "not performance" --tb=no

# Performance smoke (CI dedicado)
QT_QPA_PLATFORM=offscreen SSA_SYNC_FILTER=1 uv run --python 3.13 pytest -q \
  tests/test_scenario_gui_filter_smoke_budget_qt.py -m performance

# Cancel mid-search (33b07012)
uv run --python 3.13 pytest -q tests/test_contract_filter_worker_cancel_race.py

# GUI clicks / grid / paginator (0abc7d4a + 213a416d)
uv run --python 3.13 pytest -q \
  tests/test_scenario_filter_button_clicks_qt.py \
  tests/test_scenario_column_filter_button_clicks_qt.py \
  tests/test_scenario_grid_paginator_order_qt.py \
  tests/test_scenario_grid_table_ssa_display_qt.py

# SQL policy (runtime SELECT * fechado em 2026-07-06)
uv run --python 3.13 pytest -q tests/test_contract_data_loader_sql_policy.py

# Suite historica filtro ampliada (~6-7 min)
uv run --python 3.13 pytest -q \
  tests/test_filter*.py tests/test_gui_filter*.py tests/test_filter_cache*.py \
  -m "not performance"
```

### 8.4 Git forense

```bash
# Lista commits pos-baseline
git log 9e36576..HEAD --format=fuller --reverse

# Diff runtime pos-baseline (exclui tests)
git diff 9e36576..HEAD -- gui/ cache/ mixins/ workers/ -- ':!tests'

# Delta pos-report f8239fdf
git log f8239fdf..HEAD --oneline --reverse
git diff f8239fdf..HEAD --stat
```

---

## 9. Notas de categorizacao e conformidade AGENTS.md

### 9.1 Commit `faeb8f19` — rotulo vs conteudo

| Aspecto | Valor |
|---------|-------|
| Rotulo git | `HOTFIX_BLOCKER` (reworded from STABILITY_PATCH `9b2005d5` during rebase) |
| Conteudo real | **HOTFIX H6**: recovery pos-falha `mask.any()` no refresh pos-busca; sync `filtered_status_label`; suffix explicito; early return preservando `df_exibido` |
| Categoria recomendada | `HOTFIX_BLOCKER` |
| Testes associados | `test_scenario_filter_refresh_mixin_qt.py::test_mask_any_failure_via_refresh_after_filter_change_keeps_status` |
| Acao | Considerar amend antes de push; nao altera comportamento, so metadata commit |

### 9.2 Mapa categoria por commit (resumo)

| Categoria | Commits |
|-----------|---------|
| HOTFIX_BLOCKER | `7eef5d31`, `ad4a2cff`, `84178418`, `b2a51b81`, `faeb8f19`, `37ad59d0` |
| STABILITY_PATCH runtime | `6e230bcf`, `079908f4`, `f8239fdf`, `0d8fdb4b`, `5ca3b193` (+ rotulo `9b2005d5`) |
| STABILITY_PATCH tests | `874f48c7`, `211b2524`, `54357fda`, `db27ebb2`, `936fb22b`, `9550a796`, `33b07012`, `0abc7d4a`, `213a416d` |
| DOC_SYNC | `14fb4e2b`, `aa11f35b` |

### 9.3 Referencias cruzadas report A-K

| Bug/Slice | Descricao curta | Status HEAD |
|-----------|-----------------|-------------|
| H1 | Mapa visual ano/semana execucao -> `semana_executada` | Entregue (`6e230bcf`) |
| H2 | Terminal exclusion fora de post-search no refresh | Entregue (`6e230bcf`) |
| H3 | Token worker sensivel a mutacao in-place | Entregue funcionalmente (`84178418`); baseline de custo do hash fica como perf follow-up |
| H4 | Opcoes avancadas de `df_completo` vs recorte busca | Entregue conforme contrato atual `df_completo` |
| H5 | Sort geral antes pos-filtros | Entregue funcionalmente; manter `for_sort_defer` sem refactor |
| H6 | Falha mascara vs contador/grid | Entregue (`b2a51b81`, `faeb8f19`, `37ad59d0`) |
| H7 | Materializacao O(n) menus | Medido/deferido; sem hotspot em 50k rows |
| J1 | Um sort por ciclo | Parcial |
| J2 | Deep copies cache/pipeline | Medido/deferido; baseline RSS registrado e contratos verdes |
| J3 | Contratos invalidacao cache | Entregue + testes |
| J4 | Universo opcoes pos-busca | Entregue junto com H4 conforme contrato `df_completo` |
| J5 | Performance filtros derivada | Medido/deferido; contratos derivadas verdes |
| J6 | Terminal-only sem pos-filtros | Entregue (`6e230bcf`) |

---

## 10. Sintese executiva (3 bullets)

1. **Pos-v4.43:** 66 commits locais na entrada do DOC_SYNC residual promoveram baseline `v4.44`, fecharam P0 funcional principal (dirty cache, H1/H2/H6, H3/H4/H5/J4 por contrato atual) e estabilizaram paginate/fonte; `54bcbc002af3db8877a3b718c105d808a0d5381b` corrige About/Data ISO e P2 cleanup eleva o ahead local para 74.
2. **Estado local validado:** `ruff`, `ty`, `pip-audit` e suite completa passaram; pytest registrou 2455 passed, 6 skipped, 2 warnings e 11 subtests.
3. **Proximo foco operacional:** checagem GitHub nao mutante. Enquanto `git ls-remote` retornar HTTP 403 por conta suspensa, nao fazer fetch/push/PR nem confiar em checks remotos.

---

*Gerado: 2026-06-27. Atualizado pos-fix closure 2026-06-27. Atualizado pos-paginate/fonte 2026-06-29. Atualizado pos-v4.44 local 2026-07-06. Atualizado pos-P2 runtime cleanup 2026-07-06. Sem push.*
# Codex Audit - Filter Hardening (2026-06-27)

## Validation Gates

Captura: 2026-06-28T02:08:40Z (UTC). Branch/worktree limpo salvo indicacao abaixo.

### 1. git status --short

```
```

(saida vazia; exit 0)

### 2. py_compile (runtime pos-fix)

Arquivos: `gui/mixins/filter_gui_ssa_mixin.py`, `gui/ssa/gui_filters_advanced_ui.py`, `gui/cache/filter_cache.py`.

### 5. pytest tests/test_scenario_filter_refresh_mixin_qt.py

```
10 passed (includes test_mask_any_failure_via_on_filter_finished_keeps_status)
```

### 6. pytest contratos (marker not performance)

```
35 passed in focused subset (refresh mixin + dirty gate + cache locking + contracts)
```

### 7. Opcional rapido (test_filter* / test_gui_filter*)

```bash
timeout 180 bash -c 'uv run --python 3.13 pytest tests/test_filter*.py tests/test_gui_filter*.py -q --tb=line 2>&1 | tail -5'
```

Nao concluido em 180s (`optional_exit=124`); tail-5 nao capturado.

### Resumo numerico

| Gate | passed | failed | exit |
|------|--------|--------|------|
| pytest #5 (refresh mixin qt) | 9 | 0 | 0 |
| pytest #6 (contratos) | 21 | 0 | 0 |
| **Total pytest obrigatorio** | **30** | **0** | **0** |

failed=0 confirmado nos gates obrigatorios (#5 e #6): **sim**.
