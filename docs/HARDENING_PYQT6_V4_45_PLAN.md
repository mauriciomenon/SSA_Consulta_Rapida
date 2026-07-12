# Hardening Python/PyQt6 v4.45 - Plano Detalhado

## CURRENT TRUTH 2026-07-12 18h32

- O patch local interrompido do Ciclo 4 foi arquivado fora do repositorio e removido do workspace antes das correcoes para frente.
- ThemeGUISSAMixin, EventGUISSAMixin e DisplayGUISSAMixin permanecem suspensos. A God Class e `NAO_BLOQUEANTE_DEFERIDO`; nenhum mixin estrutural entrou na estabilizacao.
- Os status antigos de Ciclos 1 a 3 nao eram aceite final: shutdown, PaiApi, SQLite, DataLoader, AdvancedOptions, Derivadas e XLSX exigiram correcoes adicionais.
- Shutdown recusa fechamento enquanto qualquer worker owned ou retired estiver ativo, sem `terminate()` e sem liberar ownership antes do termino nativo.
- Cancelamento PaiApi e terminal antes de staging/import/SQLite/sinal; SQLite usa `SQLITE_INTERRUPT=9`; DataLoader so trata `InterruptedError` como cancelamento quando o flag esta ativo.
- AdvancedOptions usa cache independente, rejeita geracao stale e preserva selecao enquanto o timer de aplicacao esta ativo. Derivadas entrega exatamente um resultado terminal.
- O validador XLSX canonico cobre extractor, staging, PAI, robust importer, Derivadas, CLI, backfill e full rescan confiavel. Ele valida e consome o mesmo stream, revalida snapshots e aplica 64 arquivos externos, 128 MiB por arquivo, 1 GiB por lote e 1 GiB expandido por arquivo.
- A proposta posterior do z.ai para validar quatro entrypoints por `getsize` foi absorvida pelo fechamento mais forte acima; nao deve ser reaplicada.
- Dead-code review removeu somente o lock Derivadas sem caller. Callbacks Qt, slots, `eventFilter`, resize e binding dinamico de tema foram mantidos.
- Smoke GUI real validou 96028 linhas, 1921 paginas, filtros, limpeza, detalhes, links, grafo Derivadas, tema, resize e fechamento nativo. Screenshots com dados permanecem somente em `/private/tmp`.
- Medianas em cinco rodadas: startup/carga 2.247 s, render 0.278 s, filtro simples 0.238 s, filtro avancado 0.238 s, detalhes 0.011 s. RSS final ficou cerca de 29 MiB menor que o baseline medido.
- Gates locais focados estao verdes. CodeRabbit e Clawpatch permanecem bloqueados quando nao emitem verdict; timeout nunca foi classificado como limpo. GitHub continua bloqueado por HTTP 403, portanto nao houve push, PR, tag ou release.

## HISTORICAL SNAPSHOT 2026-07-11

Mapeei o modelo de concorrencia completo: 5 workers QThread (Filter, DataLoader, Rescan, PaiApi, ListExport), 3 threads daemon (vacuum, other_db, derivadas_sync), 1 singleton thread (PreferencesWriter), 1 cache de classe compartilhado (FilterCache), 3 registries globais de retirees, 7 locks. Encontrei **11 races distintas** (4 criticas), 3 riscos use-after-free via sip, 2 bloqueios de GUI thread, e God Class SSAMainWindow (238 metodos).

## Modelo de concorrencia (referencia)

| Worker | Arquivo | Cancel efetivo? | Conexao slot |
|---|---|---|---|
| FilterWorker | `gui/workers/filter_worker.py:40` | Sim (entre fases pandas) | Queued |
| DataLoaderWorker | `gui/workers/data_loader_worker.py:26` | NAO (query SQL bloqueante) | Queued |
| RescanWorker | `gui/workers/rescan_worker.py:152` | Parcial (`_should_stop` bool) | Queued |
| PaiApiRefreshWorker | `gui/workers/pai_api_worker.py:86` | NENHUM | Direta/Auto |
| ListExportWorker | `gui/workers/list_export_worker.py:15` | NENHUM | Queued |

Locks: FilterCache._lock, _GLOBAL_WORKERS_LOCK, _derivadas_sync_lock, PreferencesWriter._lock, _GUI_PREFERENCES_WRITER_LOCK, TABLE_RESOLUTION_LOCK, _NORMALIZED_SEARCH_CACHE_LOCK.

## Fase 0 - Estabilizar v4.44 e tag v4.45

- **0.1** Confirmar `git status --short`. Commit `STABILITY_PATCH` se sujo.
- **0.2** Bump 4.44->4.45 nos 3 canonicos: `config/version.json:2-3`, `VERSION:1`, `pyproject.toml:31`. Rodar `uv lock`. Commit `DOC_SYNC: bump version to 4.45.0`.
- **0.3** `git tag v4.45`.
- **0.4** Atualizar `CHANGELOG.md`, `docs/HISTORICO_RELEASES.md`, `docs/INDEX.md` (9x), `docs/README.md`, `docs/AGENTS_HANDOFF_NEXT_CYCLE.md`. Nao tocar `docs/POLICY_BASELINE_*` (frozen). Commit `DOC_SYNC: mark v4.45 baseline`.
- **0.5** Criar este arquivo, link no README. Commit `DOC_SYNC: attach plan`.

## Ciclo 1 (P0) - Races criticas de crash/shutdown/bloqueio

### 1.1 shutdown() explicito
**RACE:** closeEvent (`gui/gui_ssa.py:6037-6071`) faz `event.accept()` incondicional. Workers retidos em `GLOBAL_RETIRED_*` com `wait_ms=0` nao sao aguardados -> `QThread: Destroyed while thread is still running` (confirmado docstring :6040). **UAF:** PaiApiRefreshWorker nao tratado em cleanup; sinais caem em slots `partial(..., window)` de window destruida via sip -> RuntimeError.
**Threads:** GUI (closeEvent) vs N QThreads retidas + PaiApi ativo.
**Janela:** entre cleanup retornar e exit do processo.
**Saida:** `SSAMainWindow.shutdown()`: seta `_is_shutting_down`, para 5 timers, `cancel()` no PaiApi ativo, chama cleanup, aguarda retirees com timeout (3s filter, 0s data_loader best-effort), so entao `event.accept()`. Guards `_is_shutting_down` em load_data/start_filter/start_pai.
**Muda:** `gui/gui_ssa.py`, `gui/ssa/gui_workers.py`.
**Teste:** offscreen iniciar 3 workers com sleep 2s em run(), close(), verificar: shutdown bloqueia ate parar/timeout, 0 signals apos close, 0 warning stderr.
**Commit:** `HOTFIX_BLOCKER: add explicit shutdown() to prevent QThread destroyed and PaiApi UAF`.

### 1.2 Cancelamento SQLite via progress_handler
**RACE:** `query_db` (`database.py:228-274`) usa `pd.read_sql_query` bloqueante. `_is_cancelled()` checado so :62/:75/:78, nunca durante. Busca confirmou ZERO `set_progress_handler`. **RACE 1.2b:** troca de pagina rapida -> query antiga continua consumindo CPU/IO; stale descartado por `_is_stale_data_load_result` (`gui_workers.py:1065`) mas trabalho desperdicado e contencao SQLite.
**Saida:** `query_db` aceita `cancel_callback=None`; chama `conn.set_progress_handler(handler, 1000)` que aborta quando callback True -> `OperationalError` SQLITE_INTERRUPT(999) -> retorna DataFrame vazio + log. DataLoaderWorker passa `self._is_cancelled`.
**Muda:** `database.py:228-274`, `data_loader_worker.py:77`.
**Teste:** DB 50k linhas + CROSS JOIN recursivo, cancel apos 100ms, aborta < 2s, nova pagina inicia imediato.
**Commit:** `HOTFIX_BLOCKER: add SQLite progress_handler cancellation`.

### 1.3 PaiApiRefreshWorker: cancel() + cleanup
**RACE:** Worker cria `ThreadPoolExecutor(max_workers=3)` (`pai_api_worker.py:309`) + subprocessos SAM. NENHUM `cancel()`. No close: executor/subprocessos continuam (threads non-daemon), sinais -> slots de window destruida -> UAF.
**Janela:** entre `worker.start()` (:225) e finished_*. Sem cancel = duracao total de fetch.
**Saida:** `cancel()` seta `_cancel_requested`, sinaliza `_import_decision_event`, `executor.shutdown(wait=False, cancel_futures=True)`. Guard `_is_cancelled()` entre setores e antes de `future.result()`. Integrar em `cleanup_window_workers_on_close`.
**Muda:** `pai_api_worker.py:86-155`, `gui_workers.py:526-608`, `pai_api_controller.py`.
**Teste:** mock 10 setores sleep 0.5s, cancel apos 0.7s, run retorna < 1s, executor shutdown, 0 sinais apos cancel. UAF: destruir window, verificar cancel chamado, 0 RuntimeError.
**Commit:** `HOTFIX_BLOCKER: add cancel() and cleanup to PaiApiRefreshWorker`.

### 1.4 Mover _refresh_advanced_filter_options para thread
**BLOQUEIO:** `_refresh_advanced_filter_options` (`gui_filters_advanced_ui.py:1930`) roda 6+ `pd.unique`/`pd.to_datetime`/`pd.to_numeric` sobre df_completo na GUI thread via `QTimer.singleShot(0,...)` (`gui_ssa.py:1826`). Centenas de ms bloqueados em bases grandes.
**Saida:** `collect_advanced_filter_option_values` (ja pura em `gui_filters_advanced_refresh.py:87`) num QThread com signal `options_ready(dict)` QueuedConnection. UI mostra imediato, opcoes preenchem quando prontas. Cache `_adv_values_cache` checado antes de despachar.
**Muda:** `gui_filters_advanced_ui.py:1930-1981`, novo `gui/workers/advanced_options_worker.py`.
**Nao muda:** layout, ordem opcoes, cache key, lazy responsavel.
**Teste:** df 10k linhas, medir antes (bloqueia >Xms) vs depois (< 10ms retorno), opcoes corretas.
**Commit:** `HOTFIX_BLOCKER: move advanced filter options off GUI thread`.

## Ciclo 2 (P1) - Performance/cancelamento/dedup

### 2.1 ListExportWorker cancelavel
`list_export_worker.py:15` sem cancel. Signal cai em `deleteLater` de worker destruido.
**Muda:** `list_export_worker.py`, `list_exporter.py`.
**Commit:** `STABILITY_PATCH: make ListExportWorker cancellable`.

### 2.2 FilterWorker: snapshot df_completo
**RACE:** `__init__` (`filter_worker.py:68`) recebe df_completo sem copia. GUI muta in-place (drop/sort) enquanto worker roda -> estado inconsistente pandas.
**Saida:** `df_completo.copy(deep=False)` (shallow, O(1)).
**Teste:** iniciar worker, imediatamente `df.drop(inplace=True)` na GUI, sem copia ve 500 linhas (race), com copia ve 1k (correto).
**Muda:** `filter_worker.py:68`, `filter_gui_ssa_mixin.py:760-808`.
**Commit:** `STABILITY_PATCH: snapshot df_completo in FilterWorker`.

### 2.3 busy_timeout na leitura
**RACE:** `get_db_connection` (`database.py:131`) sem busy_timeout. ALTER TABLE concorrente com SELECT -> `database is locked` imediato.
**Saida:** `PRAGMA busy_timeout = 5000`.
**Teste:** Thread A BEGIN IMMEDIATE segurar, Thread B SELECT, sem timeout falha, com timeout espera 5s e sucesso.
**Muda:** `database.py:131-147`.
**Commit:** `STABILITY_PATCH: add busy_timeout to read connection`.

### 2.4 Unificar _quote_identifier (5 copias -> 1)
Copias: `database.py:529`, `database_optimized.py:51`, `database_integrity.py:35`, `database_upsert_logic.py:169`, `tests/_helpers/db_utils.py:24`.
Extrair para `armazenamento/sql_utils.py`.
**Teste:** quoting de `order`, `select`, coluna com espaco.
**Commit:** `STABILITY_PATCH: unify _quote_identifier into sql_utils`.

### 2.5 Unificar normalizacao SSA (3 fontes -> 1)
Fontes: `shared/numero_ssa.py` (canonica), `armazenamento/numero_ssa_utils.py` (5 funcs), in-line `gui_ssa.py:4886` + `gui_details.py:272`.
**Teste:** contrato positivo/negativo 100 SSAs, diff = 0.
**Commit:** `STABILITY_PATCH: consolidate SSA normalization into shared.numero_ssa`.

### 2.6 Unificar parse de datas
`parse_any_date` `shared/date_utils.py:40` canonica. `database_upsert_logic.py:591/600` reimplementam.
**Teste:** roundtrip 50 datas, diff = 0.
**Commit:** `STABILITY_PATCH: consolidate date parsing`.

### 2.7 Limites importacao XLSX (conservador)
`extract_data_from_excel` (`extractor.py:325`) sem validacao tamanho -> OOM. Limites: 64 arquivos/lote, 128 MiB/arquivo, 1 GiB/lote.
**Teste:** mock `os.path.getsize` > 128 MiB -> ExtractionError exit nao-zero.
**Commit:** `HOTFIX_BLOCKER: enforce XLSX import limits`.

### 2.8 Resolver polling singleShot fragil
**RACE 2.8:** derivadas_sync `_poll_delivery` (`derivadas_sync_controller.py:262`) le pending None em :274, entra ramo timeout :275-284, chama `mark_finished()` :280. Se `_work` grava pending entre :274 e :280, resultado perdido (race timeout-vs-entrega). Mesmo padrao em `gui_ssa.py:5640-5648` (vacuum), `:5964-5972` (other_db).
**Saida:** converter `_work` para QThread com signal `job_finished(dict)` QueuedConnection. Eliminar `_poll_delivery`. Timeout via `QTimer.singleShot` que cancela worker.
**Teste:** mock `_work` sleep aleatorio ate TIMEOUT, rodar 100x. Antes: alguns perdem resultado. Depois: todos entregam ou cancelam limpo.
**Muda:** `derivadas_sync_controller.py:230-311`, `gui_ssa.py:5611-5660`, `:5938-5985`.
**Commit:** `STABILITY_PATCH: replace singleShot polling with QThread signal`.

## Ciclo 3 (P2) - Limpeza

- **3.1** Remover mortos (grep=0): `utils/robust_importer_old.py`, `gui/gui_ssa_dev.py`, `validate_filter_optimizations.py`, `scripts/find_ssa.py`, 5 vazios em `scripts_manutencao/`.
- **3.2** Widget morto `rescan_button` (`gui_ssa.py:1454-1459`), 5 imports nao usados (`gui_ssa.py:86,88,335,360`, `gui_workers.py:21`).
- **3.3** Consolidar v1/v2 scripts (`run_pytest_*`), `check_columns.py` duplicado.
- **3.4** Unificar Qt stubs (`gui/qt_stubs.py` + `gui/ssa/headless_qt_stubs.py` -> 1).
- **3.5** Documentar shims `core/numero_ssa.py`/`core/date_utils.py` (manter, docstring SHIM, RECOVERY_BACKLOG).
- **3.6** Triar `except Exception` (770) focando closeEvent/cleanup/workers -> excecoes especificas (`sqlite3.Error`, `OSError`, `ValueError`). Resto DEFERRED_NOTE.

## Ciclo 4 (P3) - Decompor God Class - DEFERRED

**Status**: DEFERRED por decisao do usuario (2026-07-11) apos a extracao do
ThemeGUISSAMixin degenerar em costura local.

**Motivo tecnico**: os metodos de tema dependem de 8+ variaveis de modulo de
`gui_ssa.py` (`GUI_MAIN_PREFERENCES`, `ssa_gui_theme`, `project_root`,
`TSM_DEBUG_ENABLED`, `HIGHLIGHT_BACKGROUND_COLOR`, `HIGHLIGHT_FONT_WEIGHT`,
`QT_AVAILABLE`, `_is_widget_valid`). O mixin plain precisaria re-importar cada
uma com fallback condicional, gerando codigo fragil que quebra o principio do
"patch mais curto e com menor impacto". O AGENTS.md manda parar e declarar
isso explicitamente quando o raciocinio de "patch minimo" degenera.

**Abordagens futuras candidatas** (requerem nova aprovacao):
1. Criar `gui/ssa/runtime_context.py` que centraliza as dependencias de modulo
   e permite que os mixins importem limpo sem fallbacks.
2. Mover as constantes/dependencias para atributos de instancia da MainWindow
   setados no `__init__`, para que os mixins acessem via `self.*`.
3. Aceitar a God Class como esta e focar apenas em extrair metodos que tem
   pouca dependencia de module-globals (EventGUISSAMixin e o melhor candidato).

Padrao mixin originalmente planejado: classe plain, sem `__init__`, sem
metaclass, `self.X` access, `if TYPE_CHECKING: def __getattr__` para type
safety. MRO multipla.

- **4.1 ThemeGUISSAMixin** (7 metodos: `_resolve_startup_theme` :945,
  `theme_filter_context` :990, `set_theme_name_for_filter_context` :994,
  `refresh_filter_widgets_after_theme` :999, `toggle_theme_menu` :2713,
  `apply_theme` :2722). DEFERRED.
- **4.2 EventGUISSAMixin** (7 metodos: `eventFilter`, `resizeEvent`,
  `closeEvent`, helpers de resize). DEFERRED.
- **4.3 DisplayGUISSAMixin** (~13 metodos). DEFERRED.
- **4.4** Ativacao dos mixins. DEFERRED.

## Races DEFERRED (explicitas, nao abordadas)

1. FilterCache._evict_until_within_limits sob lock (max_size=50 limita impacto).
2. _release_worker_ref closure captura window (ref Python, listas).
3. TABLE_RESOLUTION_CACHE TOCTOU (idempotente).
4. _NORMALIZED_SEARCH_CACHE_LOCK (baixa contencao).
5. GLOBAL_WORKERS_LOCK em stress (capped 64/8).
6. PreferencesWriter singleton (protegido por lock).
7. _LogHandler.emit sinais de thread arbitraria (queued + guard sip).

## Aceite

- **Por slice:** `python -m py_compile`, `ruff check`, `ty check`, `pytest` focado.
- **GUI slices:** smoke offscreen (abrir, popular, trocar tema, events, context menu, derivadas popup) + screenshot. Declarar bloqueio se nao feito.
- **Review:** `clawpatch` por slice, `semgrep`+`bandit`+`detect-secrets`/`gitleaks` por ciclo. Timeout nunca autoriza marcar limpo.
- **Report por slice:** categoria commit, arquivos:linha, validacao+resultado, rollback. Patches perf: tempo/RSS antes/depois + justificativa patch mais curto.

## Premissas

- Mudancas atuais intactas. Sem branch/PR/commit/push sem autorizacao por fase.
- Layout nao muda exceto estabilidade. Nenhuma classe removida sem evidencia (grep=0).
- `docs/POLICY_BASELINE_*` frozen. GitHub remoto HTTP 403: sem push.
- Shims `core/*` mantidos. God Class: extrai ~27 metodos (3 mixins), ~211 como DEFERRED_NOTE.

## Ordem

Fase 0 -> Ciclo 1 (P0) -> Ciclo 2 (P1) -> Ciclo 3 (P2) -> Ciclo 4 (P3). Slices em ordem. Cada slice requer confirmacao. Commits atomicos. Push por ciclo com autorizacao. Timestamp inicio/fim por rodada.
