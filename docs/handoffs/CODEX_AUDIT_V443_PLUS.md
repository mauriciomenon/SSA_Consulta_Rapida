# Codex Audit V443 Plus

Handoff DOC_SYNC para Codex. Baseline funcional `9e36576` (tag `v4.43`).

## Metadata

| Campo | Valor |
|-------|-------|
| Repositorio | `/Users/menon/git/SSA_Consulta_Rapida` |
| Branch | `dev` |
| HEAD | `b3e0b740fd4c5103908a5eb9707c1e83ce1c34aa` |
| Baseline | `9e36576b11ae2ba64d8a988f7fbe7cf885f64722` |
| Commits pos-baseline | 28 |
| Status | `## dev...origin/dev [ahead 33]` |
| Push | **nao executado** |
| Reword H6 | `9b2005d5` -> `faeb8f19` (HOTFIX_BLOCKER, `--no-gpg-sign` no rebase; GPG TTY indisponivel no agente) |
| Pos-fix closure | `37ad59d0`, `1a8b2c5d`, `e5ab1585`, `b3e0b740` (2026-06-27) |

## git log 9e36576..HEAD --format=fuller (pos-fix tail)

```
commit b3e0b740fd4c5103908a5eb9707c1e83ce1c34aa
    STABILITY_PATCH: cover dirty gate executor menu rebuild

commit e5ab1585
    STABILITY_PATCH: treat SSA_CACHE_MAX_MB=0 as unlimited cache

commit 1a8b2c5d
    STABILITY_PATCH: narrow advanced apply except to mask errors only

commit 37ad59d0
    HOTFIX_BLOCKER: preserve H6 status when mask fails after search
```

## git log 9e36576..HEAD --format=fuller

```
commit b309ebbe9f021392153eb3ffb67997d583593d4a
Author:     Mauricio Menon <mauriciomenon@users.noreply.github.com>
AuthorDate: Sat Jun 27 23:36:58 2026 -0300
Commit:     Mauricio Menon <mauriciomenon@users.noreply.github.com>
CommitDate: Sat Jun 27 23:44:56 2026 -0300

    STABILITY_PATCH: fail-closed sort defer when filter flags fail
    
    Default has_post_search_filters to True and log warning when
    _filter_refresh_flags raises so pre-search sort cannot run silently
    with wrong defer semantics.

commit 0c4e6684432d98e6dd6e8f0e1da1722999b9971c
Author:     Mauricio Menon <mauriciomenon@users.noreply.github.com>
AuthorDate: Sat Jun 27 23:36:45 2026 -0300
Commit:     Mauricio Menon <mauriciomenon@users.noreply.github.com>
CommitDate: Sat Jun 27 23:44:51 2026 -0300

    STABILITY_PATCH: unify has_post_search_filters via shared helper
    
    Extract _compute_has_post_search_filters with documented for_sort_defer
    contract so on_filter_finished and _refresh_after_filter_change share one
    gate implementation without changing intentional terminal semantics.

commit a38a2ac3889369570e528e70870e2ceb0d87d1c8
Author:     Mauricio Menon <mauriciomenon@users.noreply.github.com>
AuthorDate: Sat Jun 27 23:31:50 2026 -0300
Commit:     Mauricio Menon <mauriciomenon@users.noreply.github.com>
CommitDate: Sat Jun 27 23:44:45 2026 -0300

    STABILITY_PATCH: harden advanced filter mask errors with domain exception
    
    Replace fragile RuntimeError message prefix checks with AdvancedFilterMaskError
    so mixin and UI handlers classify mask.any() failures via isinstance.

commit faeb8f198862d6097e538505f3652f2ba7efeb66
Author:     Mauricio Menon <mauriciomenon@users.noreply.github.com>
AuthorDate: Sat Jun 27 22:25:14 2026 -0300
Commit:     Mauricio Menon <mauriciomenon@users.noreply.github.com>
CommitDate: Sat Jun 27 23:44:40 2026 -0300

    HOTFIX_BLOCKER: sync status when advanced filter mask fails on refresh
    
    After mask.any() failure during post-search refresh, keep displayed rows
    and update filter status with explicit failure suffix instead of silent
    "0 de 0 SSAs" mismatch (H6).

commit 213a416dce95b0bd70ef15f462ab7c792f8973a0
Author:     Mauricio Menon <mauriciomenon@users.noreply.github.com>
AuthorDate: Sat Jun 27 22:18:55 2026 -0300
Commit:     Mauricio Menon <mauriciomenon@users.noreply.github.com>
CommitDate: Sat Jun 27 22:18:55 2026 -0300

    STABILITY_PATCH: close deferred GUI gaps and refine with five passes
    
    Add column-filter clicks, grid SSA display, paginator prev/page3, derivada
    positive path, cancel optimistic display contract, and LIMIT+OFFSET SQL
    policy; refine helpers and asserts across five review personas.

commit 0abc7d4a1940995739c230bd8b06f948aab3276c
Author:     Mauricio Menon <mauriciomenon@users.noreply.github.com>
AuthorDate: Sat Jun 27 22:06:11 2026 -0300
Commit:     Mauricio Menon <mauriciomenon@users.noreply.github.com>
CommitDate: Sat Jun 27 22:06:11 2026 -0300

    STABILITY_PATCH: add GUI click, grid, cancel, and SQL policy tests
    
    Cover real widget clicks, paginator table order, async cancel mid-search,
    derivada checkbox wiring, basic label visibility, and DataLoader OFFSET
    policy after four-pass test refinement.

commit 5ca3b19369afc44ada3b704e58772611e60a9c3c
Author:     Mauricio Menon <mauriciomenon@users.noreply.github.com>
AuthorDate: Sat Jun 27 21:19:24 2026 -0300
Commit:     Mauricio Menon <mauriciomenon@users.noreply.github.com>
CommitDate: Sat Jun 27 21:19:24 2026 -0300

    STABILITY_PATCH: reduce option value materialization

commit aa11f35bc171a37be49c250259473d1721e21d9b
Author:     Mauricio Menon <mauriciomenon@users.noreply.github.com>
AuthorDate: Sat Jun 27 21:13:56 2026 -0300
Commit:     Mauricio Menon <mauriciomenon@users.noreply.github.com>
CommitDate: Sat Jun 27 21:13:56 2026 -0300

    DOC_SYNC: record local filter hardening after v4.43

commit 0d8fdb4b2184b1e5b93ab27d7fe10e0a5a635cae
Author:     Mauricio Menon <mauriciomenon@users.noreply.github.com>
AuthorDate: Sat Jun 27 21:09:00 2026 -0300
Commit:     Mauricio Menon <mauriciomenon@users.noreply.github.com>
CommitDate: Sat Jun 27 21:09:00 2026 -0300

    STABILITY_PATCH: skip advanced options cache read on clean hit

commit 33b07012e58c6dedfc5e694c7731967a471f9104
Author:     Mauricio Menon <mauriciomenon@users.noreply.github.com>
AuthorDate: Sat Jun 27 20:55:56 2026 -0300
Commit:     Mauricio Menon <mauriciomenon@users.noreply.github.com>
CommitDate: Sat Jun 27 20:55:56 2026 -0300

    STABILITY_PATCH: cover mid-search filter worker cancel

commit b2a51b81b8ee48dfa82364bd7410c80a0074610b
Author:     Mauricio Menon <mauriciomenon@users.noreply.github.com>
AuthorDate: Sat Jun 27 20:53:23 2026 -0300
Commit:     Mauricio Menon <mauriciomenon@users.noreply.github.com>
CommitDate: Sat Jun 27 20:53:23 2026 -0300

    HOTFIX_BLOCKER: keep advanced failure count status in sync

commit 14fb4e2ba5a8b0ea51610488ea18976ee50c3467
Author:     Mauricio Menon <mauriciomenon@users.noreply.github.com>
AuthorDate: Sat Jun 27 20:44:18 2026 -0300
Commit:     Mauricio Menon <mauriciomenon@users.noreply.github.com>
CommitDate: Sat Jun 27 20:44:18 2026 -0300

    DOC_SYNC: add local command hooks rules for agents
    
    Document mandatory restrictions on package installs, git mutation, and
    system changes for assistants operating in this repository.

commit 9550a79684a4642a7b9abea040b053d783cfd5b3
Author:     Mauricio Menon <mauriciomenon@users.noreply.github.com>
AuthorDate: Sat Jun 27 20:35:28 2026 -0300
Commit:     Mauricio Menon <mauriciomenon@users.noreply.github.com>
CommitDate: Sat Jun 27 20:35:28 2026 -0300

    STABILITY_PATCH: five-pass refinement of filter regression tests
    
    Strengthen coverage, race/cancel determinism, false-positive guards, and
    budget contracts across contract and Qt scenario tests; centralize shared
    helpers and document known H6 count-label mismatch as test contract.

commit 936fb22bb5978547260bcd780f504d999b6115dc
Author:     Mauricio Menon <mauriciomenon@users.noreply.github.com>
AuthorDate: Sat Jun 27 20:10:10 2026 -0300
Commit:     Mauricio Menon <mauriciomenon@users.noreply.github.com>
CommitDate: Sat Jun 27 20:10:10 2026 -0300

    STABILITY_PATCH: add race/waste tests and refine filter regression suite
    
    Add contract and Qt scenario tests for stale loads, pipeline cache hits,
    worker cancel races, and wasted advanced-option scans; strengthen asserts
    and spies across three review passes and centralize shared test helpers.

commit db27ebb22e76903ca3fd0e6c57409eba6a07d847
Author:     Mauricio Menon <mauriciomenon@users.noreply.github.com>
AuthorDate: Sat Jun 27 19:48:00 2026 -0300
Commit:     Mauricio Menon <mauriciomenon@users.noreply.github.com>
CommitDate: Sat Jun 27 19:48:00 2026 -0300

    STABILITY_PATCH: add refined filter regression tests round 4
    
    Extend contract and headless Qt coverage for search undo source selection,
    cache context digests, reprogramacoes filters, undo restore, stale request
    ignore, and undo snapshot dirty marking from the filter audit.

commit 54357fda86a8ccdecf717be9a6996969dc5359b0
Author:     Mauricio Menon <mauriciomenon@users.noreply.github.com>
AuthorDate: Sat Jun 27 19:43:25 2026 -0300
Commit:     Mauricio Menon <mauriciomenon@users.noreply.github.com>
CommitDate: Sat Jun 27 19:43:25 2026 -0300

    STABILITY_PATCH: add refined filter regression tests round 3

commit 211b2524526590e4e1bdcde3ef3524e9972df7fd
Author:     Mauricio Menon <mauriciomenon@users.noreply.github.com>
AuthorDate: Sat Jun 27 19:38:26 2026 -0300
Commit:     Mauricio Menon <mauriciomenon@users.noreply.github.com>
CommitDate: Sat Jun 27 19:38:26 2026 -0300

    STABILITY_PATCH: extend filter regression tests for P1 P2 audit gaps
    
    Adds large-df GUI smoke RSS budget, derivada notice UI scenarios, dirty-gate
    ordering, worker cache E2E, responsavel ranking fingerprint, SQL loader contract,
    H4 df_completo scope, and complementary J1 sort semantics coverage.

commit 874f48c7c98fa0a7a65586e5b5198159b3084a45
Author:     Mauricio Menon <mauriciomenon@users.noreply.github.com>
AuthorDate: Sat Jun 27 19:32:44 2026 -0300
Commit:     Mauricio Menon <mauriciomenon@users.noreply.github.com>
CommitDate: Sat Jun 27 19:32:44 2026 -0300

    STABILITY_PATCH: add contract and scenario regression tests for filter pipeline
    
    Adds two-pass test suite (pure contracts + headless Qt scenarios) covering
    P0 filter cache, refresh semantics, visual mapping, and worker token cases
    from the filter/GUI audit without modifying legacy tests.

commit f8239fdfe2e8e97b56bd73c705acbc22281f82ee
Author:     Mauricio Menon <mauriciomenon@users.noreply.github.com>
AuthorDate: Sat Jun 27 17:28:30 2026 -0300
Commit:     Mauricio Menon <mauriciomenon@users.noreply.github.com>
CommitDate: Sat Jun 27 17:28:30 2026 -0300

    STABILITY_PATCH: defer general search sort before post filters

commit 84178418260202a00b39d7e3e811c1c77b7182b7
Author:     Mauricio Menon <mauriciomenon@users.noreply.github.com>
AuthorDate: Sat Jun 27 17:23:14 2026 -0300
Commit:     Mauricio Menon <mauriciomenon@users.noreply.github.com>
CommitDate: Sat Jun 27 17:23:14 2026 -0300

    HOTFIX_BLOCKER: hash GUI filter worker cache token

commit 079908f48974932a53a224b32426d9e9a89bc479
Author:     Mauricio Menon <mauriciomenon@users.noreply.github.com>
AuthorDate: Sat Jun 27 17:18:53 2026 -0300
Commit:     Mauricio Menon <mauriciomenon@users.noreply.github.com>
CommitDate: Sat Jun 27 17:18:53 2026 -0300

    STABILITY_PATCH: vectorize derivada relation normalization

commit 6e230bcf534f90ab9895595d5fe3f6b7034e020d
Author:     Mauricio Menon <mauriciomenon@users.noreply.github.com>
AuthorDate: Sat Jun 27 17:05:24 2026 -0300
Commit:     Mauricio Menon <mauriciomenon@users.noreply.github.com>
CommitDate: Sat Jun 27 17:05:24 2026 -0300

    STABILITY_PATCH: align advanced filter refresh contracts

commit ad4a2cffb30b2d9cf60ade3d82a38ff8b2f80736
Author:     Mauricio Menon <mauriciomenon@users.noreply.github.com>
AuthorDate: Sat Jun 27 16:58:49 2026 -0300
Commit:     Mauricio Menon <mauriciomenon@users.noreply.github.com>
CommitDate: Sat Jun 27 16:58:49 2026 -0300

    HOTFIX_BLOCKER: surface advanced mask evaluation errors

commit 7eef5d314ff5c1685ffdda388eec6278149b8787
Author:     Mauricio Menon <mauriciomenon@users.noreply.github.com>
AuthorDate: Sat Jun 27 16:40:46 2026 -0300
Commit:     Mauricio Menon <mauriciomenon@users.noreply.github.com>
CommitDate: Sat Jun 27 16:40:46 2026 -0300

    HOTFIX_BLOCKER: honor advanced options dirty state
```

## Commits (detalhe)

### 1. `7eef5d314ff5`

- **Data:** 2026-06-27 16:40:46 -0300
- **Titulo:** HOTFIX_BLOCKER: honor advanced options dirty state
- **Classificacao:** HOTFIX_BLOCKER
- **Sessao:** Codex

**--stat:**
```
gui/ssa/gui_filters_advanced_refresh.py    |  3 ++-
 gui/ssa/gui_filters_advanced_ui.py         |  1 +
 tests/test_gui_filters_advanced_refresh.py | 42 ++++++++++++++++++++++++++++--
 3 files changed, 43 insertions(+), 3 deletions(-)
```

**Diff resumido (3-5 linhas):**
```diff
+    force_refresh: bool = False,
-    if cache.get("df_key") == df_key and isinstance(
+    if not force_refresh and cache.get("df_key") == df_key and isinstance(
+        force_refresh=bool(getattr(self, "_adv_options_dirty", False)),
+    same_revision = object()
```

### 2. `ad4a2cffb30b`

- **Data:** 2026-06-27 16:58:49 -0300
- **Titulo:** HOTFIX_BLOCKER: surface advanced mask evaluation errors
- **Classificacao:** HOTFIX_BLOCKER
- **Sessao:** Codex

**--stat:**
```
gui/ssa/gui_filters_advanced_logic.py    |  7 +++----
 tests/test_gui_filters_advanced_logic.py | 13 +++++++++++++
 2 files changed, 16 insertions(+), 4 deletions(-)
```

**Diff resumido (3-5 linhas):**
```diff
-        logger.debug(
-            "Failed to evaluate advanced filter mask.any() %s: %s", context, exc
-        )
-        return False
+        raise RuntimeError(
```

### 3. `6e230bcf534f`

- **Data:** 2026-06-27 17:05:24 -0300
- **Titulo:** STABILITY_PATCH: align advanced filter refresh contracts
- **Classificacao:** STABILITY_PATCH (tests)
- **Sessao:** Codex

**--stat:**
```
gui/mixins/filter_gui_ssa_mixin.py       |  3 +--
 gui/ssa/filter_domain_rules.py           | 10 +++++-----
 tests/test_filter_refresh_pipeline.py    |  7 +++++--
 tests/test_gui_filters_advanced_logic.py | 17 +++++++++++++++++
 4 files changed, 28 insertions(+), 9 deletions(-)
```

**Diff resumido (3-5 linhas):**
```diff
-        if has_post_search_filters:
+        if has_post_search_filters or has_excluded_terminal_status:
-            or has_excluded_terminal_status
-    "ano_execucao": ("data_programada",),
-    "ano_execucao_values": ("data_programada",),
```

### 4. `079908f48974`

- **Data:** 2026-06-27 17:18:53 -0300
- **Titulo:** STABILITY_PATCH: vectorize derivada relation normalization
- **Classificacao:** STABILITY_PATCH
- **Sessao:** Codex

**--stat:**
```
gui/ssa/gui_filters_advanced_logic.py    | 12 +++++++-----
 tests/test_gui_filters_advanced_logic.py | 13 +++++++++++++
 2 files changed, 20 insertions(+), 5 deletions(-)
```

**Diff resumido (3-5 linhas):**
```diff
-        resolved = [""] * len(series_obj)
-        for index, code in enumerate(codes):
-            if code >= 0:
-                resolved[index] = normalized_uniques[code]
-        return pd.Series(resolved, index=series_obj.index, dtype="object")
```

### 5. `841784182602`

- **Data:** 2026-06-27 17:23:14 -0300
- **Titulo:** HOTFIX_BLOCKER: hash GUI filter worker cache token
- **Classificacao:** HOTFIX_BLOCKER
- **Sessao:** Codex

**--stat:**
```
gui/mixins/filter_gui_ssa_mixin.py | 23 +++++++++++++++++++----
 tests/test_filter_worker.py        | 16 ++++++++++++++++
 2 files changed, 35 insertions(+), 4 deletions(-)
```

**Diff resumido (3-5 linhas):**
```diff
+        content_hash = build_dataframe_filter_hash(source)
-        if isinstance(cached, tuple) and len(cached) == 4:
-            cached_source_id, cached_shape, cached_revision, cached_token = cached
+        if isinstance(cached, tuple) and len(cached) == 5:
+            (
```

### 6. `f8239fdfe2e8`

- **Data:** 2026-06-27 17:28:30 -0300
- **Titulo:** STABILITY_PATCH: defer general search sort before post filters
- **Classificacao:** STABILITY_PATCH
- **Sessao:** Codex

**--stat:**
```
gui/mixins/filter_gui_ssa_mixin.py | 23 ++++++++++++++++++++++-
 tests/test_gui_filter_logic.py     | 30 ++++++++++++++++++++++++++++++
 2 files changed, 52 insertions(+), 1 deletion(-)
```

**Diff resumido (3-5 linhas):**
```diff
+        has_post_search_filters = False
-            if not df_filtrado.empty and "numero_ssa" in df_filtrado.columns:
+            (
+                has_column_filters,
+                has_advanced_filters,
```

### 7. `874f48c7c98f`

- **Data:** 2026-06-27 19:32:44 -0300
- **Titulo:** STABILITY_PATCH: add contract and scenario regression tests for filter pipeline
- **Classificacao:** STABILITY_PATCH (tests)
- **Sessao:** Cursor
- **Corpo:** Adds two-pass test suite (pure contracts + headless Qt scenarios) covering P0 filter cache, refresh semantics, visual mapping, and worker token cases from the filter/GUI audit without modifying legacy tests.

**--stat:**
```
tests/_helpers/contract_data_builders.py          |  79 ++++++++
 tests/_helpers/gui_scenario_harness.py            | 177 ++++++++++++++++++
 tests/test_contract_advanced_filter_domain.py     | 133 ++++++++++++++
 tests/test_contract_cache_content_invalidation.py |  90 +++++++++
 tests/test_contract_collect_nonempty_budget.py    |  74 ++++++++
 tests/test_contract_derivadas_tree_budget.py      |  99 ++++++++++
 tests/test_contract_filter_cache_deep_copy.py     |  29 +++
 tests/test_contract_filter_refresh_deep_copy.py   |  65 +++++++
 tests/test_contract_filter_refresh_semantics.py   | 214 ++++++++++++++++++++++
 tests/test_scenario_adv_options_dirty_gate_qt.py  |  85 +++++++++
 tests/test_scenario_filter_refresh_mixin_qt.py    | 160 ++++++++++++++++
 tests/test_scenario_filter_worker_cache_qt.py     |  56 ++++++
 tests/test_scenario_gui_filter_smoke_budget_qt.py |  70 +++++++
 tests/test_scenario_visual_filter_state_qt.py     | 100 ++++++++++
 14 files changed, 1431 insertions(+)
```

**Diff resumido (3-5 linhas):**
```diff
+    situacoes = ["APV", "STE", "SCA", "AMP", "APV"]
+    executores = ["IEE3", "OURO", "MEL4", "XYZ", "IEE2"]
+    emissores = ["ABC", "IEE3", "MEL4", "MEL3", "XYZ"]
+    descricoes = ["Teste A", "Teste B", "Teste C", "Teste D", "Teste E"]
+    return pd.DataFrame(
```

### 8. `211b25245265`

- **Data:** 2026-06-27 19:38:26 -0300
- **Titulo:** STABILITY_PATCH: extend filter regression tests for P1 P2 audit gaps
- **Classificacao:** STABILITY_PATCH (tests)
- **Sessao:** Cursor
- **Corpo:** Adds large-df GUI smoke RSS budget, derivada notice UI scenarios, dirty-gate ordering, worker cache E2E, responsavel ranking fingerprint, SQL loader contract, H4 df_completo scope, and complementary J1 sort semantics coverage.

**--stat:**
```
tests/test_contract_advanced_filter_domain.py     | 23 ++++++++++
 tests/test_contract_data_loader_query.py          | 35 ++++++++++++++
 tests/test_contract_filter_refresh_semantics.py   | 34 ++++++++++++++
 tests/test_contract_responsavel_options_budget.py | 56 +++++++++++++++++++++++
 tests/test_scenario_adv_options_dirty_gate_qt.py  | 40 +++++++++++++++-
 tests/test_scenario_derivada_notice_qt.py         | 48 +++++++++++++++++++
 tests/test_scenario_filter_worker_cache_qt.py     | 32 +++++++++++++
 tests/test_scenario_gui_filter_smoke_budget_qt.py | 53 +++++++++++++++++++++
 8 files changed, 320 insertions(+), 1 deletion(-)
```

**Diff resumido (3-5 linhas):**
```diff
+    """H4: option collection reflects df_completo scope, not active search subset."""
+    from gui.ssa.gui_filters_advanced_refresh import collect_advanced_filter_option_values
+    df_full = build_advanced_filter_contract_df()
+    df_full = df_full.copy()
+    df_full.loc[3, "setor_executor"] = "ONLY_IN_COMPLETO"
```

### 9. `54357fda86a8`

- **Data:** 2026-06-27 19:43:25 -0300
- **Titulo:** STABILITY_PATCH: add refined filter regression tests round 3
- **Classificacao:** STABILITY_PATCH (tests)
- **Sessao:** Cursor

**--stat:**
```
tests/test_contract_data_loader_query.py          | 53 +++++++++++++++++++++++
 tests/test_contract_derivadas_tree_budget.py      | 22 ++++++++++
 tests/test_scenario_gui_filter_smoke_budget_qt.py | 52 ++++++++++++++++++++++
 tests/test_scenario_responsavel_options_qt.py     | 50 +++++++++++++++++++++
 4 files changed, 177 insertions(+)
```

**Diff resumido (3-5 linhas):**
```diff
+    "PyQt6", reason="Dependencia PyQt6 indisponivel no ambiente de teste"
+    app = QApplication.instance() or QApplication([])
+    yield app
+    db_path = tmp_path / "loader_contract.db"
+    row_count = 42
```

### 10. `db27ebb22e76`

- **Data:** 2026-06-27 19:48:00 -0300
- **Titulo:** STABILITY_PATCH: add refined filter regression tests round 4
- **Classificacao:** STABILITY_PATCH (tests)
- **Sessao:** Cursor
- **Corpo:** Extend contract and headless Qt coverage for search undo source selection, cache context digests, reprogramacoes filters, undo restore, stale request ignore, and undo snapshot dirty marking from the filter audit.

**--stat:**
```
tests/test_contract_advanced_filter_domain.py      | 34 ++++++++++++++++
 tests/test_contract_filter_cache_context_digest.py | 47 ++++++++++++++++++++++
 tests/test_contract_filter_search_undo_state.py    | 34 ++++++++++++++++
 tests/test_contract_search_undo_source.py          | 46 +++++++++++++++++++++
 tests/test_scenario_advanced_reprogramacoes_qt.py  | 24 +++++++++++
 tests/test_scenario_filter_refresh_mixin_qt.py     | 10 +++++
 tests/test_scenario_filter_undo_restore_qt.py      | 37 +++++++++++++++++
 7 files changed, 232 insertions(+)
```

**Diff resumido (3-5 linhas):**
```diff
+    from gui.ssa.gui_filters_advanced_logic import _apply_reprogramacoes_filter
+    df = build_advanced_filter_contract_df()
+    mask = pd.Series(True, index=df.index)
+    filters = {
+        "num_reprogramacoes_mode": "eq",
```

### 11. `936fb22bb597`

- **Data:** 2026-06-27 20:10:10 -0300
- **Titulo:** STABILITY_PATCH: add race/waste tests and refine filter regression suite
- **Classificacao:** STABILITY_PATCH (tests)
- **Sessao:** Cursor
- **Corpo:** Add contract and Qt scenario tests for stale loads, pipeline cache hits, worker cancel races, and wasted advanced-option scans; strengthen asserts and spies across three review passes and centralize shared test helpers.

**--stat:**
```
tests/_helpers/contract_data_builders.py           |  46 ++++++++-
 tests/_helpers/gui_scenario_harness.py             |  37 +++++++
 tests/test_contract_advanced_filter_domain.py      |  21 +++-
 tests/test_contract_cache_content_invalidation.py  |  24 +++++
 tests/test_contract_collect_nonempty_budget.py     |  53 +++++-----
 tests/test_contract_data_load_stale_guard.py       | 109 +++++++++++++++++++
 tests/test_contract_data_loader_query.py           |   2 +
 tests/test_contract_derivadas_tree_budget.py       |   1 +
 tests/test_contract_filter_cache_context_digest.py |  37 +++++++
 tests/test_contract_filter_cache_deep_copy.py      |   5 +
 tests/test_contract_filter_refresh_deep_copy.py    |  12 +--
 .../test_contract_filter_refresh_pipeline_waste.py | 115 +++++++++++++++++++++
 tests/test_contract_filter_refresh_semantics.py    |  59 ++++-------
 tests/test_contract_filter_search_undo_state.py    |  51 +++++++++
 tests/test_contract_filter_worker_cancel_race.py   | 115 +++++++++++++++++++++
 tests/test_contract_responsavel_options_budget.py  |  15 +++
 tests/test_contract_search_undo_source.py          |  13 +++
 tests/test_scenario_adv_options_dirty_gate_qt.py   |   2 +
 tests/test_scenario_adv_options_load_waste_qt.py   |  98 ++++++++++++++++++
 tests/test_scenario_advanced_reprogramacoes_qt.py  |   4 +
 tests/test_scenario_derivada_notice_qt.py          |   1 +
 tests/test_scenario_filter_race_conditions_qt.py   | 113 ++++++++++++++++++++
 tests/test_scenario_filter_refresh_mixin_qt.py     |  61 +++--------
 tests/test_scenario_filter_undo_restore_qt.py      |   5 +
 tests/test_scenario_filter_worker_cache_qt.py      |  17 +--
 tests/test_scenario_gui_filter_smoke_budget_qt.py  |  18 +---
 tests/test_scenario_visual_filter_state_qt.py      |   7 ++
 27 files changed, 892 insertions(+), 149 deletions(-)
```

**Diff resumido (3-5 linhas):**
```diff
+    """Identity timing hook for apply_filter_refresh_pipeline contract tests."""
+    return callback()
+    """Return sort call counter and patched DataFrame.sort_values wrapper."""
+    sort_calls = {"numero_ssa": 0}
+    original_sort_values = pd.DataFrame.sort_values
```

### 12. `9550a79684a4`

- **Data:** 2026-06-27 20:35:28 -0300
- **Titulo:** STABILITY_PATCH: five-pass refinement of filter regression tests
- **Classificacao:** STABILITY_PATCH (tests)
- **Sessao:** Cursor
- **Corpo:** Strengthen coverage, race/cancel determinism, false-positive guards, and budget contracts across contract and Qt scenario tests; centralize shared helpers and document known H6 count-label mismatch as test contract.

**--stat:**
```
tests/_helpers/contract_data_builders.py           | 55 +++++++++++-
 tests/_helpers/gui_scenario_harness.py             | 36 ++++++--
 tests/test_contract_advanced_filter_domain.py      | 17 +++-
 tests/test_contract_cache_content_invalidation.py  | 19 +++--
 tests/test_contract_collect_nonempty_budget.py     |  5 +-
 tests/test_contract_data_load_stale_guard.py       | 50 +++++++++++
 tests/test_contract_derivadas_tree_budget.py       | 36 ++++++++
 .../test_contract_filter_refresh_pipeline_waste.py |  1 +
 tests/test_contract_filter_refresh_semantics.py    | 12 +--
 tests/test_contract_filter_search_undo_state.py    | 43 +++++++++-
 tests/test_contract_filter_worker_cancel_race.py   | 98 +++++++++++++++++-----
 tests/test_contract_responsavel_options_budget.py  | 42 +++++++++-
 tests/test_contract_search_undo_source.py          | 51 ++++++-----
 tests/test_scenario_adv_options_dirty_gate_qt.py   |  9 +-
 tests/test_scenario_adv_options_load_waste_qt.py   | 23 ++---
 tests/test_scenario_advanced_reprogramacoes_qt.py  | 12 +--
 tests/test_scenario_derivada_notice_qt.py          |  5 +-
 tests/test_scenario_filter_race_conditions_qt.py   | 92 ++++++++++++++++----
 tests/test_scenario_filter_refresh_mixin_qt.py     | 82 +++++++++++++++---
 tests/test_scenario_filter_undo_restore_qt.py      |  9 +-
 tests/test_scenario_filter_worker_cache_qt.py      | 63 +++++++++++++-
 tests/test_scenario_gui_filter_smoke_budget_qt.py  | 22 ++++-
 tests/test_scenario_responsavel_options_qt.py      | 36 ++++----
 tests/test_scenario_visual_filter_state_qt.py      | 11 +--
 24 files changed, 684 insertions(+), 145 deletions(-)
```

**Diff resumido (3-5 linhas):**
```diff
+    """Dual spy template for advanced-options cache budget tests.
+    Yields (get_cached_spy, collect_spy). Cache hit: collect call_count == 0.
+    Cache miss / force_refresh: collect call_count == 1.
+    """
+    from gui.ssa.gui_filters_advanced_refresh import (
```

### 13. `14fb4e2ba5a8`

- **Data:** 2026-06-27 20:44:18 -0300
- **Titulo:** DOC_SYNC: add local command hooks rules for agents
- **Classificacao:** DOC_SYNC
- **Sessao:** Codex
- **Corpo:** Document mandatory restrictions on package installs, git mutation, and system changes for assistants operating in this repository.

**--stat:**
```
COMMAND_HOOKS.md | 69 ++++++++++++++++++++++++++++++++++++++++++++++++++++++++
 1 file changed, 69 insertions(+)
```

**Diff resumido (3-5 linhas):**
```diff
+  Forbidden without explicit user authorization in the same turn.
+  List/search commands (`brew list`, `brew search`, `brew info`) are allowed.
+  Forbidden without explicit user authorization in the same turn.
+  Listing commands (`uv tool list`, `pip list`, `pipx list`) are allowed.
+  Same as above. No install/remove without explicit user authorization.
```

### 14. `b2a51b81b8ee`

- **Data:** 2026-06-27 20:53:23 -0300
- **Titulo:** HOTFIX_BLOCKER: keep advanced failure count status in sync
- **Classificacao:** HOTFIX_BLOCKER
- **Sessao:** Codex

**--stat:**
```
gui/ssa/gui_filters_advanced_ui.py             |  9 +++++++++
 tests/test_scenario_filter_refresh_mixin_qt.py | 13 ++++++-------
 2 files changed, 15 insertions(+), 7 deletions(-)
```

**Diff resumido (3-5 linhas):**
```diff
+        update_status = getattr(self, "update_filter_status_display", None)
+        displayed_df = getattr(self, "df_exibido", None)
+        complete_df = getattr(self, "df_completo", None)
+        if callable(update_status):
+            update_status(
```

### 15. `33b07012e58c`

- **Data:** 2026-06-27 20:55:56 -0300
- **Titulo:** STABILITY_PATCH: cover mid-search filter worker cancel
- **Classificacao:** STABILITY_PATCH
- **Sessao:** Cursor

**--stat:**
```
tests/test_contract_filter_worker_cancel_race.py | 51 +++++++++++++++++++++++-
 1 file changed, 49 insertions(+), 2 deletions(-)
```

**Diff resumido (3-5 linhas):**
```diff
+    df_hash = FilterWorker._build_df_hash(df)
-        df_hash=FilterWorker._build_df_hash(df),
+        df_hash=df_hash,
-        worker.df_hash,
+        df_hash,
```

### 16. `0d8fdb4b2184`

- **Data:** 2026-06-27 21:09:00 -0300
- **Titulo:** STABILITY_PATCH: skip advanced options cache read on clean hit
- **Classificacao:** STABILITY_PATCH
- **Sessao:** Codex

**--stat:**
```
gui/ssa/gui_filters_advanced_ui.py               | 13 +++++++++----
 tests/test_scenario_adv_options_dirty_gate_qt.py |  4 ++--
 tests/test_scenario_adv_options_load_waste_qt.py |  4 ++--
 3 files changed, 13 insertions(+), 8 deletions(-)
```

**Diff resumido (3-5 linhas):**
```diff
+    AdvancedFilterOptionValues,
-        ui_state = _read_advanced_filter_ui_state(self, df, filters)
+        dirty = bool(getattr(self, "_adv_options_dirty", False))
+        cached_values = cache.get("values") if isinstance(cache, dict) else None
-            cache.get("df_key") == df_key
```

### 17. `aa11f35bc171`

- **Data:** 2026-06-27 21:13:56 -0300
- **Titulo:** DOC_SYNC: record local filter hardening after v4.43
- **Classificacao:** DOC_SYNC
- **Sessao:** Codex

**--stat:**
```
CHANGELOG.md | 14 ++++++++++++++
 1 file changed, 14 insertions(+)
```

**Diff resumido (3-5 linhas):**
```diff
+  - Advanced filter option refresh now skips the cache helper entirely on clean cache hits, while dirty refresh still r
+  - Filter worker cancel/race coverage now includes a real `QThread` cancel while `apply_general_search_terms()` is run
+  - Advanced filter mask failures now keep the displayed dataframe and `filtered_status_label` count in sync instead of
+  - `tests/test_scenario_filter_refresh_mixin_qt.py`: `8 passed`
+  - `tests/test_contract_filter_worker_cancel_race.py`: `6 passed`
```

### 18. `5ca3b19369af`

- **Data:** 2026-06-27 21:19:24 -0300
- **Titulo:** STABILITY_PATCH: reduce option value materialization
- **Classificacao:** STABILITY_PATCH
- **Sessao:** Codex

**--stat:**
```
gui/ssa/filter_domain_rules.py | 4 ++--
 1 file changed, 2 insertions(+), 2 deletions(-)
```

**Diff resumido (3-5 linhas):**
```diff
-    series = normalize_nonempty_string_series(df[column].dropna())
-    return series[series != ""].astype(str).tolist()
+    series = normalize_nonempty_string_series(df[column])
+    return series[series != ""].tolist()
```

### 19. `0abc7d4a1940`

- **Data:** 2026-06-27 22:06:11 -0300
- **Titulo:** STABILITY_PATCH: add GUI click, grid, cancel, and SQL policy tests
- **Classificacao:** STABILITY_PATCH (tests)
- **Sessao:** Cursor
- **Corpo:** Cover real widget clicks, paginator table order, async cancel mid-search, derivada checkbox wiring, basic label visibility, and DataLoader OFFSET policy after four-pass test refinement.

**--stat:**
```
tests/_helpers/gui_scenario_harness.py             |  36 ++++-
 tests/test_contract_data_loader_sql_policy.py      | 156 +++++++++++++++++++++
 tests/test_scenario_derivada_checkbox_click_qt.py  |  45 ++++++
 tests/test_scenario_filter_button_clicks_qt.py     |  84 +++++++++++
 tests/test_scenario_filter_cancel_mid_search_qt.py |  60 ++++++++
 tests/test_scenario_grid_paginator_order_qt.py     |  44 ++++++
 tests/test_scenario_visual_labels_basic_qt.py      |  39 ++++++
 7 files changed, 462 insertions(+), 2 deletions(-)
```

**Diff resumido (3-5 linhas):**
```diff
+    def filter_panel_context(self) -> dict[str, Any]:
+        """Shared filter panel widget map (see gui_ssa._filter_panel_context)."""
+        return self.window._filter_panel_context
-        ctx = self.window._filter_panel_context
+        ctx = self.filter_panel_context()
```

### 20. `213a416dce95`

- **Data:** 2026-06-27 22:18:55 -0300
- **Titulo:** STABILITY_PATCH: close deferred GUI gaps and refine with five passes
- **Classificacao:** STABILITY_PATCH
- **Sessao:** Cursor
- **Corpo:** Add column-filter clicks, grid SSA display, paginator prev/page3, derivada positive path, cancel optimistic display contract, and LIMIT+OFFSET SQL policy; refine helpers and asserts across five review personas.

**--stat:**
```
tests/_helpers/contract_data_builders.py           | 22 +++++++
 tests/_helpers/gui_scenario_harness.py             | 48 +++++++++++++-
 tests/test_contract_data_loader_sql_policy.py      | 70 +++++++++++++++-----
 ...test_scenario_column_filter_button_clicks_qt.py | 77 ++++++++++++++++++++++
 tests/test_scenario_derivada_checkbox_click_qt.py  | 57 +++++++++++-----
 tests/test_scenario_filter_cancel_mid_search_qt.py | 39 +++++++++++
 tests/test_scenario_filter_refresh_mixin_qt.py     | 27 ++++++++
 tests/test_scenario_grid_paginator_order_qt.py     | 57 ++++++++++++----
 tests/test_scenario_grid_table_ssa_display_qt.py   | 52 +++++++++++++++
 9 files changed, 398 insertions(+), 51 deletions(-)
```

**Diff resumido (3-5 linhas):**
```diff
+    """Advanced contract df with one derivada link (child -> origin SSA).
+    derivada_has filter keeps rows whose numero_ssa appears in derivada_de origins.
+    See DERIVADA_POSITIVE_* constants for expected SSAs.
+    """
+    df = build_advanced_filter_contract_df()
```

### 21. `faeb8f198862`

- **Data:** 2026-06-27 23:44:40 -0300
- **Titulo:** HOTFIX_BLOCKER: sync status when advanced filter mask fails on refresh
- **Classificacao:** HOTFIX_BLOCKER
- **Sessao:** Cursor
- **Corpo:** After mask.any() failure during post-search refresh, keep displayed rows and update filter status with explicit failure suffix instead of silent "0 de 0 SSAs" mismatch (H6).

**--stat:**
```
gui/mixins/filter_gui_ssa_mixin.py | 27 +++++++++++++++++++++------
 gui/ssa/gui_filters_advanced_ui.py | 34 +++++++++++++++++++++++++---------
 2 files changed, 46 insertions(+), 15 deletions(-)
```

**Diff resumido (3-5 linhas):**
```diff
-        filtered = self._apply_filter_refresh_filters_and_update_cache(
-            filtered,
-            has_post_search_filters=has_post_search_filters,
-            has_excluded_terminal_status=has_excluded_terminal_status,
-            measure_timing=timer.measure,
```

### 22. `a38a2ac38893`

- **Data:** 2026-06-27 23:44:45 -0300
- **Titulo:** STABILITY_PATCH: harden advanced filter mask errors with domain exception
- **Classificacao:** STABILITY_PATCH
- **Sessao:** Cursor
- **Corpo:** Replace fragile RuntimeError message prefix checks with AdvancedFilterMaskError so mixin and UI handlers classify mask.any() failures via isinstance.

**--stat:**
```
gui/mixins/filter_gui_ssa_mixin.py             | 18 ++++++++----------
 gui/ssa/gui_filters_advanced_logic.py          |  6 +++++-
 gui/ssa/gui_filters_advanced_ui.py             |  5 +++--
 tests/test_scenario_filter_refresh_mixin_qt.py |  4 ++--
 4 files changed, 18 insertions(+), 15 deletions(-)
```

**Diff resumido (3-5 linhas):**
```diff
-        except RuntimeError as exc:
+        except AdvancedFilterMaskError as exc:
-                _is_advanced_filter_mask_runtime_error,
-            if _is_advanced_filter_mask_runtime_error(exc):
-                logger.warning(
```

### 23. `0c4e6684432d`

- **Data:** 2026-06-27 23:44:51 -0300
- **Titulo:** STABILITY_PATCH: unify has_post_search_filters via shared helper
- **Classificacao:** STABILITY_PATCH
- **Sessao:** Cursor
- **Corpo:** Extract _compute_has_post_search_filters with documented for_sort_defer contract so on_filter_finished and _refresh_after_filter_change share one gate implementation without changing intentional terminal semantics.

**--stat:**
```
gui/mixins/filter_gui_ssa_mixin.py              | 40 ++++++++++++++++++++-----
 tests/test_contract_filter_refresh_semantics.py | 14 +++++++--
 2 files changed, 44 insertions(+), 10 deletions(-)
```

**Diff resumido (3-5 linhas):**
```diff
-            has_post_search_filters = (
-                has_column_filters
-                or has_advanced_filters
-                or has_excluded_terminal_status
+            has_post_search_filters = self._compute_has_post_search_filters(
```

### 24. `b309ebbe9f02`

- **Data:** 2026-06-27 23:44:56 -0300
- **Titulo:** STABILITY_PATCH: fail-closed sort defer when filter flags fail
- **Classificacao:** STABILITY_PATCH
- **Sessao:** Cursor
- **Corpo:** Default has_post_search_filters to True and log warning when _filter_refresh_flags raises so pre-search sort cannot run silently with wrong defer semantics.

**--stat:**
```
gui/mixins/filter_gui_ssa_mixin.py              |  4 ++--
 tests/test_contract_filter_refresh_semantics.py |  8 ++++----
 tests/test_scenario_filter_refresh_mixin_qt.py  | 16 +++++++---------
 3 files changed, 13 insertions(+), 15 deletions(-)
```

**Diff resumido (3-5 linhas):**
```diff
-        has_post_search_filters = False
+        has_post_search_filters = True
-            logger.debug(
+            logger.warning(
-    """f8239fdf: flags failure keeps has_post_search_filters False and allows sort."""
```

## Matriz plano A-K vs estado (HEAD atual)

| Item | Estado HEAD | Notas |
|------|-------------|-------|
| Slice 0 DOC_SYNC 4.43 | Entregue | `9e36576` |
| Slice 1 cache/dirty | Entregue | `0d8fdb4b`, `7eef5d31`, testes Qt |
| Slice 2 H6 mask | Entregue | `ad4a2cff`, `b2a51b81`, `faeb8f19`, `a38a2ac3` |
| Slice 3 H1/H2/J6 | Entregue | `6e230bcf` + contracts |
| Slice 4 smoke RSS/ms | Parcial | markers performance; CI job pendente |
| Slice 5 J2 deep copies | Pendente | CHANGELOG defer |
| Slice 6 J5 arvore derivadas | Parcial | normalizacao vetorizada only |
| Slice 7 H4 universo opcoes | Pendente | decisao produto |
| Slice 8 SQL SELECT * | Parcial | tests policy; runtime intacto |
| H1 mapa visual | Resolvido |  |
| H2 terminal vs post-search | Resolvido |  |
| H3 worker token | Parcial | `84178418` |
| H4 opcoes universo | Pendente |  |
| H5 sort pos-filtros | Parcial | `f8239fdf`, `b309ebbe` fail-closed flags |
| H6 contador vs grid | Entregue | cadeia apply + refresh + on_filter_finished (`37ad59d0`) |
| H7 materializacao | Parcial | `5ca3b193` |
| J1 sort unico | Parcial | `0c4e6684` helper unificado |
| J2 deep copies | Pendente |  |
| J3 contratos cache | Resolvido |  |
| J4 opcoes pos-busca | Pendente |  |
| J5 derivadas perf | Parcial |  |
| J6 terminal-only refresh | Resolvido |  |
| has_post_search_filters | Parcial->Entregue helper | `0c4e6684` |
| paginate hotspot | Parcial | testes grid; runtime ~313ms/50k |
| Push/checks | Pendente | ahead 29 |
| Regressao contract/scenario | Entregue | 34+ arquivos |

## Cursor vs Codex

| Agente | Papel neste ciclo | Commits tipicos |
|--------|-------------------|-----------------|
| **Codex** | Slices 0-3 runtime, H6 apply path, H7 micro-opt, CHANGELOG | dirty cache, `_mask_any` raise, refresh contracts, worker hash, sort defer, cache clean hit, failure count sync |
| **Cursor** | Suite contract/scenario Qt, fechamento gaps GUI, H6 refresh mixin, semantica flags pos-audit | 874f48c7..213a416d rodadas, cancel race, clicks/grid/SQL tests; pos-9b2005d5: `a38a2ac3` domain exception, `0c4e6684` helper, `b309ebbe` fail-closed sort, `faeb8f19` H6 refresh |

**Divisao pratica:** Codex entregou patches runtime minimos e ordem de gates; Cursor entregou contratos/regressao massiva e commits pos-H6 que fecham classificacao de erro e helper `has_post_search_filters`.

## Pendencias abertas

### P0
- Push preparatorio (33 commits locais) + checks remotos
- Reviews externos (clawpatch/coderabbit/semgrep) nao fechados nesta sessao
- Smoke visual GUI real pos-H6 (status suffix com falha simulada)
- Commits rebaseados usaram `--no-gpg-sign`; re-assinar antes de push se politica exigir GPG

### P1
- Paginate hotspot runtime (~313ms/50k)
- H5/J1: validar max 1 sort/ciclo apos `b309ebbe`
- Unificar suffix H6 em todos callers de falha de mascara

### P2
- Slice 5 J2 deep copies (defer CHANGELOG)
- Slice 6 J5 arvore derivadas (benchmark 50k)
- Slice 7 H4/J4 decisao universo opcoes
- Slice 8 SELECT * runtime
- CI job performance dedicado

## Validacao sessao (pytest focado)

```
uv run --python 3.13 pytest tests/test_scenario_filter_refresh_mixin_qt.py tests/test_contract_filter_refresh_semantics.py tests/test_scenario_adv_options_dirty_gate_qt.py tests/test_filter_cache_locking.py -m "not performance" -q
35 passed; failed=0
```

*Gerado: 2026-06-27/28. Atualizado pos-fix closure. Sem push.*

## Closure operacional (2026-06-28, agente df272a44 follow-up)

| Campo | Valor |
|-------|-------|
| HEAD | `73ca96cbd63fb4ebd4eb5262fdf7d882d43bc2fe` |
| Branch | `dev` |
| Ahead origin/dev | 34 commits |
| Working tree | clean |
| Push | **nao executado** (sem pedido explicito) |

### Quality gates (superficie filter)

| Gate | Resultado | Notas |
|------|-----------|-------|
| py_compile | OK | 8 arquivos (runtime + tests focados) |
| ruff check | OK | All checks passed |
| ty check (runtime) | OK | mixin, advanced_ui, filter_cache |
| ty check (tests) | 3 diagnostics | `test_contract_filter_refresh_semantics.py`: stub `pipeline_measure_timing` retorna `object` vs `DataFrame` esperado; pre-existente, nao bloqueia runtime |
| pytest focado | **36 passed**, 4 deselected (`-m "not performance"`) | bundle: contract/scenario/cache + smoke headless + smoke budget |

Comando pytest bundle:
```
uv run --python 3.13 pytest tests/test_contract_filter_refresh_semantics.py tests/test_scenario_filter_refresh_mixin_qt.py tests/test_scenario_adv_options_dirty_gate_qt.py tests/test_filter_cache_locking.py tests/test_filter_cache_context.py tests/smoke_test_gui.py::test_gui_instantiation tests/smoke_test_gui.py::test_mixin_methods_callable tests/test_scenario_gui_filter_smoke_budget_qt.py -m "not performance" -q
```

### Reviews externos

| Ferramenta | Status | Detalhe |
|------------|--------|---------|
| semgrep `--config=auto` | **0 findings** | 5 arquivos, 1198 rules |
| bandit | **0 findings** | runtime: mixin, advanced_ui, filter_cache |
| clawpatch | **BLOQUEADO** | `review --since origin/dev` e `--since 9e36576` retornam `"no features touched by diff"`; doctor OK (provider grok); diff git confirma +175/-34 nos 3 runtime files vs origin/dev |
| coderabbit | **NAO RODADO** | sem PR aberto nesta sessao |

### Smoke GUI

| Teste | Resultado |
|-------|-----------|
| `smoke_test_gui::test_gui_instantiation` | pass |
| `smoke_test_gui::test_mixin_methods_callable` | pass |
| `test_scenario_gui_filter_smoke_budget_qt` | 5 passed |

**Smoke visual manual ainda pendente (P0):** abrir GUI real, aplicar filtro avancado, simular falha de mascara (`AdvancedFilterMaskError`), confirmar suffix H6 no status bar e contador alinhado ao grid.

### GPG

- 34 commits em `origin/dev..HEAD`: **todos unsigned** (`%G? = N`)
- 0 assinados (`G`), 0 good-but-untrusted (`U`)
- Re-assinar apenas se politica exigir e GPG/TTY disponivel; nao re-assinado nesta sessao

### Proxima acao recomendada

1. **Push** (quando usuario autorizar): `git push origin dev` — 34 commits locais
2. **Smoke visual manual** pos-H6 (status suffix com falha simulada)
3. **Clawpatch:** investigar mapa de features ou abrir PR para review via CI/coderabbit
4. **GPG opcional:** re-assinar cadeia se politica do remoto exigir
