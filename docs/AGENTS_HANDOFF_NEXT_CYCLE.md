# AGENTS Handoff For Next Cycle

## CURRENT TRUTH 2026-05-19 21h30

- Branch alvo operacional: `dev`.
- HEAD operacional atual validado localmente antes deste DOC_SYNC:
  - `b96c5d8b438673b2ae152d2c1cf6a7e5d4030c4d 2026-05-19T21:29:07-03:00 STABILITY_PATCH: simplify PAI summary aggregation`.
- `dev` esta sincronizado com `origin/dev` antes deste DOC_SYNC.
- `main` nao deve ser assumido sincronizado com `dev` sem nova checagem.
- Workspace local tem apenas residuos fora de escopo:
  - `.agents/`
  - `agents.lock`
  - `config/gui_saved_filters.json`
- `.gitignore` ja ignora `.clawpatch/`, `agents.toml` e `tmp/`.
- Checks GitHub verdes no head publicado `29c359ad3ab4e53eedafe5de6a25e685f506924c`:
  - `minimal-ci`
  - `CodeQL`
  - `Secret Scan`
  - `Automatic Dependency Submission`
- API PAI:
  - fluxo real habilitado: `consulta`.
  - smoke real fetch-only validado para `IEE3`, `MEL4`, `MEL3` com CA exportada via `scrap_report`.
  - GUI confirma antes de gravar dados da API no DB.
  - Auto-refresh nao grava no DB automaticamente.
  - `summary-json` registra fonte, filtros pedidos, setores, arquivos origem, contagens e exemplos de SSAs.
- Dependencia:
  - `idna` atualizado em `dev`; alerta Dependabot deve fechar quando o fix chegar ao default branch.
- Tipos PAI:
  - `executadas` e `aprovacao` seguem planejados ate existir provider real.
  - `planejamento` e `programacao` seguem nao suportados.
- God modules ainda abertos:
  - `gui/gui_ssa.py`: 3846 linhas.
  - `gui/mixins/filter_gui_ssa_mixin.py`: 3014 linhas.
  - `tests/test_gui_filter_logic.py`: 10372 linhas.
  - `core/app_logic.py`: 2179 linhas.
- Bloqueios antes de merge operacional:
  1. Smoke GUI final: boot, API, XLS externo, filtros, undo, detalhes e derivadas.
  2. Se PR for autorizado, rodar CodeRabbit no PR.
  3. Continuar corte de `filter_gui_ssa_mixin.py` e `SSAMainWindow` se a meta clean-code for criterio bloqueante.
- Build macOS/release ainda nao executado neste ciclo.

Este handoff esta pronto para reutilizacao no proximo ciclo.

## HISTORICAL SNAPSHOT 2026-04-22 13h14

- Leitura rapida:
  1. branch alvo confirmada: `dev`
  2. `HEAD` local e `origin/dev` estao alinhados em `b5e3335b7565f104c23054777499ff350cce2b94`
  3. ultimo commit atual:
     - `2026-04-22 13:14:32 -0300`
     - `docs(handoff): Sync post-lab current truth`
  4. worktree local atual:
     - repo limpo no runtime/docs desta frente
     - residuos locais fora de escopo no momento:
       - `AGENTS.md.backup_20260416_223903`
     - laboratorio `B` em worktree destacado foi testado, descartado e removido sem portar patch para `dev`
  5. PR ativo:
     - `#47` `dev -> main`
     - titulo: `Merge dev into main for stabilization and gui follow-up`
     - estado: `OPEN`
     - `mergeStateStatus=UNSTABLE`
  6. a frente principal recente seguiu sendo estabilizacao e performance da GUI, com foco em:
     - carga inicial
     - busca geral
     - filtros
     - undo
     - detalhes laterais
     - dialogo completo de detalhes
     - troca de aba sem destruir estado
  7. o ciclo de `2026-04-16/17` corrigiu gargalos reais de RAM e de custo de carga:
     - cortes de alocacao desnecessaria em busca, reset e undo
     - eliminacao de rebuilds pesados de indices globais no fluxo de detalhes
     - reducao de cache frio e de lookups redundantes
     - preservacao do estado vivo de detalhes ao trocar de aba
  8. commits-chave desta frente:
     - `3f49caef` `perf(gui): Elide stale details lookup on tab bind`
     - `51a0a69a` `perf(gui): Preserve search cache across requests`
     - `12fbc46c` `fix(gui): Stop global SSA index builds in details flows`
     - `b93b367d` `perf(gui): Reduce search cache memory and details lookup`
     - `edaa90e7` `perf(gui): Reuse full dataset on reset and lazy reprog cache`
     - `73881633` `perf(gui): Remove heavy undo snapshot dataframe retention`
     - `a160a589` `perf(gui): Skip null-only columns in general search`
     - `e3b5561d` `perf(search): Cut cold row cache build cost`
     - `ffecabff` `fix(gui): Preserve live details across tab bind`
  9. item fechado nesta frente:
     - o bug de trocar de aba e perder a SSA selecionada foi fechado
  10. estado atual da frente:
     - busca e filtros melhoraram de forma material, mas ainda nao estao encerrados
     - o risco maior agora esta em ownership duplicado de dataframe, residuos de verificacao e hotspots algoritmicos restantes, nao em layout
  11. pendencias reais abertas nesta retomada:
     - o backlog antigo ainda citava:
       - `tests/test_quality_gates_smoke.py:34`
       - `tests/test_workers_advanced.py:648`
     - revalidacao posterior mostrou esses 2 itens como fechados
     - o laboratorio `B` para cache grande no full dataframe foi descartado por custo de RAM em ambiente alvo de `4 GB`
     - o proximo residual tecnico real deve ser reidentificado por novo diagnostico puro
  11.1. levantamento de footprint alto executado nesta rodada, sem editar runtime:
     - `query_db()` em `armazenamento/database.py` materializa `80448 x 84` e sobe o RSS de `90.50 MB` para `402.30 MB` em `717.60 ms`
     - `_prepare_dataframe_for_ui()` em `gui/workers/data_loader_worker.py` adiciona `67.79 MB` e retorna novo objeto (`same_object=False`) em `303.14 ms`
     - `filter_dataframe()` no full dataframe continua caro porque recompõe a busca ampla no full df:
       - frio `419.17 ms`
       - quente `416.42 ms`
       - cache cheio fica so com `token`
     - o refinamento em subset segue bom:
       - `39.75 ms`
       - cache do subset contem `row_search_text` e `token`
     - o fallback raro de `on_data_loaded()` sem preprocessamento ainda explode ownership:
       - `255.61 ms`
       - `+108 MB` de RSS no harness
       - `df_completo is df_exibido == False`
  11.2. ranking tecnico atual de hotspots de memoria:
     1. leitura/materializacao cheia em `query_db()`
     2. preprocessamento inicial em `_prepare_dataframe_for_ui()`
     3. rebuild da busca ampla no full dataframe em `filter_dataframe()`
     4. fallback raro de `on_data_loaded()` sem attrs de preprocessamento
  11.3. proxima frente recomendada:
     - diagnostico/slice minimo focado em reduzir ownership e materializacao no load path principal, antes de voltar a mexer em busca ampla
  12. slices funcionais desta retomada ja aterrados em `dev`:
     - `d8451041` `test(gui): Lock load ordering behavior`
     - `e594d5bc` `perf(gui): Reuse sorted search result in refresh`
     - `dcb6a830` `perf(gui): Trim cache and load copies`
     - `e1fc2106` `perf(gui): Keep preprocessed load order`
     - `5ca3020c` `perf(gui): Skip redundant refresh steps`
     - `17c9a806` `perf(search): Cap large row cache retention`
     - `581b88bf` `perf(gui): Reuse subset on safe search refinement`
     - `991fa874` `perf(gui): Narrow column filter working set`
     - `908e8561` `perf(gui): Reuse quick executor combo options`
     - `a094fcce08be8fc71b69212705a4ca2df58efb52`
       - `2026-04-22 07:27:37 -0300`
       - `perf(gui): Cache normalized column filter series`
     - `541a8f0a9d651a03108d281b1df5f822897e6854`
       - `2026-04-22 07:45:33 -0300`
       - `perf(gui): Invalidate date display cache by revision`
     - `a96b8c703249b53832bb335e9b212f81f27d847f`
       - `2026-04-22 08:57:32 -0300`
       - `fix(import): Keep file runtime faults inside batch`
     - `3652dc90e5198238e78af3d50fc189b6a8b83db5`
       - `2026-04-22 09:00:27 -0300`
       - `docs(policy): Sync AGENTS operating rules`
     - `083078de05c25e942c995fcb8290cc47d3c5267d`
       - `2026-04-22 09:27:09 -0300`
       - `docs(handoff): Sync import continuity`
     - `0c57e699a3867cd88a8faf926ad9d3f1a11f7023`
       - `2026-04-22 09:33:13 -0300`
       - `perf(gui): Reuse single-frame filter results`
     - `94c40bb8391e88a6ffd1c0bf41abf841fee84e1e`
       - `2026-04-22 09:35:36 -0300`
       - `docs(handoff): Sync single-frame filter continuity`
     - `fe608884496868c08f61557e9b844076ee80acb5`
       - `2026-04-22 09:39:02 -0300`
       - `ref(gui): Trim load fallback duplication`
     - `c707c8f99eb9d4a30ccdbe6ff3d13ca0087538aa`
       - `2026-04-22 09:54:13 -0300`
       - `perf(gui): Deduplicate repeated search chunks`
     - `7f7baf65cd520b390c9a37a0eef05f270e17fe11`
       - `2026-04-22 10:02:06 -0300`
       - `perf(gui): Deduplicate merged chunks by source index`
  13. ganhos funcionais acumulados do bloco `D` e follow-ups imediatos:
     - a carga inicial sem filtros agora preserva o dataframe preprocessado do worker como estado visual canonico
     - o refresh simples deixa de reaplicar filtros avancados e filtros por coluna quando nao existe filtro extra ativo
     - o load path passou a ter um unico dono para sanitizacao e ordenacao inicial
     - a busca geral simples reaproveita o resultado ordenado em vez de rematerializar o dataframe exibido
     - o cache grande de `row_search_text` deixou de ficar residente no dataframe cheio quando o payload passa do limite definido
     - a GUI voltou a reaproveitar o subset anterior em refinamento seguro (`MEL -> MEL3`) sem reter o cache gigante no `df_completo`
     - o refresh por coluna passou a estreitar o `working_df` incrementalmente, sem recalcular todas as mascaras sempre sobre o dataset cheio
     - o combo rapido de setor executor deixou de ser repopulado em todo refresh quando as opcoes ja cobrem o valor atual
     - o caso real `MEL3` segue com `df_exibido is _df_last_search_filtered == True`
     - o caso de carga sem filtros segue com `df_exibido is df_completo == True`
  14. validacao local aterrada nesta frente:
     - `uv run --python 3.13 python -m py_compile gui/cache/filter_cache.py gui/workers/filter_worker.py gui/workers/data_loader_worker.py gui/mixins/filter_gui_ssa_mixin.py gui/ssa/gui_workers.py tests/test_filter_cache_locking.py tests/test_filter_worker.py tests/test_data_loader_worker.py tests/test_gui_filter_logic.py`
     - `uv run --python 3.13 ruff check ...` no mesmo escopo tocado
     - `uv run --python 3.13 ty check ...` no mesmo escopo tocado
     - `uv run --python 3.13 pytest -q tests/test_filter_cache_locking.py tests/test_filter_worker.py`
     - `uv run --python 3.13 pytest -q tests/test_workers_advanced.py -k 'filter_worker_cache_performance or worker_uses_cache_for_same_query or worker_different_cache_context_misses_cache'`
     - `uv run --python 3.13 pytest -q tests/test_data_loader_worker.py`
     - `uv run --python 3.13 pytest -q tests/test_gui_filter_logic.py -k 'refresh_after_filter_change or on_filter_finished or on_data_loaded or clear_all_filters_global_reuses_df_completo_reference or hard_reset_filters_state_reuses_df_completo_reference'`
     - review `kluster` local limpo no escopo tocado
  15. prova real curta mais recente com GUI e `data/ssas.db`:
     - carga: `80448` linhas, `84` colunas, `3.8360s`
     - busca fria `MEL`: `1.5125s` com `22606` linhas
     - refinamento `MEL -> MEL3`: `0.8553s` com `4680` linhas
     - repeticao quente `MEL3`: `0.6602s`
     - pagina `2`: `0.3444s`
     - `df_exibido is _df_last_search_filtered == True` no resultado final
     - refresh cheio com `80448` linhas e 3 filtros por coluna:
       - baseline diagnosticada: `138.72ms`
       - apos `991fa874`: `113.78ms`
       - apos `908e8561`: `74.19ms`
       - apos `a094fcce`, primeira passagem: `62.61ms`
       - repeticao na mesma revisao/dataframe: `10.13ms`
       - `_apply_column_filters`: `94.57ms -> 66.74ms -> 70.61ms -> 9.32ms` no caso repetido
       - `_sync_quick_setor_executor_combo_from_filters`: `40.92ms -> 41.51ms -> 0.03ms`
       - cache local de series normalizadas ativo com `3` entradas no caso repetido
     - prints atualizados em:
       - `artifacts/gui_load_after_real_db.png`
       - `artifacts/gui_filter_MEL3.png`
       - `artifacts/gui_filter_MEL3_page2.png`
     - nota: esta ultima prova foi executada em `offscreen`; o RSS lido via `ru_maxrss` e high-water mark de processo, nao baseline canonica de memoria residente
  16. validacao local aterrada no `P3C`:
     - `uv run --python 3.13 python -m py_compile gui/mixins/filter_gui_ssa_mixin.py tests/test_gui_filter_logic.py`
     - `uv run --python 3.13 ruff check gui/mixins/filter_gui_ssa_mixin.py tests/test_gui_filter_logic.py`
     - `uv run --python 3.13 ty check gui/mixins/filter_gui_ssa_mixin.py tests/test_gui_filter_logic.py`
     - `uv run --python 3.13 pytest -q tests/test_gui_filter_logic.py -k '_apply_column_filters or column_filter or data_programacao or general_search or initiate_filtering or on_filter_finished or clear_filter'`
     - review `kluster` sem blocker novo do slice; restaram apenas debts estruturais antigos e amplos do mixin
  17. validacao local aterrada no `P4A`:
     - `uv run --python 3.13 python -m py_compile gui/mixins/filter_gui_ssa_mixin.py tests/test_gui_filter_logic.py`
     - `uv run --python 3.13 ruff check gui/mixins/filter_gui_ssa_mixin.py tests/test_gui_filter_logic.py`
     - `uv run --python 3.13 ty check gui/mixins/filter_gui_ssa_mixin.py tests/test_gui_filter_logic.py`
     - `uv run --python 3.13 pytest -q tests/test_gui_filter_logic.py -k 'data_cadastro or data_programacao or _apply_column_filters or column_filter_date_display_guard'`
     - review `kluster` sem blocker novo do slice; restaram debts estruturais antigos do mixin e um apontamento amplo fora do escopo do caminho de data
  18. prova real curta do `P4A`:
     - `_get_column_filter_date_display_series()` em `12000` linhas:
       - primeira chamada: `4.44ms`
       - hit quente na mesma revisao/dataframe: `0.01ms`
       - recalc apos bump de revisao no mesmo dataframe: `2.79ms`
     - confirmacao funcional:
       - `SAME_FIRST_SECOND=True`
       - `SAME_SECOND_THIRD=False`
       - valor recalculado apos revisao: `05/03/2025`
     - leitura: o stale risk do cache por `id(df)` puro foi fechado sem reabrir parser
  19. checks remotos relevantes apos os pushes desta frente:
     - `pass`: `CodeFactor`, `CodeQL`, `CodeRabbit`, `DeepScan`, `GitGuardian`, `Socket Security: Project Report`, `analyze (python)`, `secret-scan`, `submit-pypi`, `precheck-default-setup`
     - `pending`: `semgrep-cloud-platform/scan`
     - `fail` externo/vendor: `DeepSource: Error`
     - `fail` externo por limite: `code/snyk (mauriciomenon)`, `security/snyk (mauriciomenon)`
  20. update multi-chunk mais recente:
     - chunks identicos agora sao deduplicados dentro da mesma requisicao
     - o ajuste vale para:
       - `FilterWorker`
       - modo sincrono
       - fallback sem worker
     - a semantica final foi preservada:
       - chunk unico reaproveita o proprio frame
       - chunk vazio reaproveita a base
       - multi-chunk continua com uniao e `drop_duplicates()` no final
     - validacao aterrada:
       - `uv run --python 3.13 python -m py_compile gui/workers/filter_worker.py gui/mixins/filter_gui_ssa_mixin.py tests/test_filter_worker.py tests/test_gui_filter_logic.py`
       - `uv run --python 3.13 ruff check ...`
       - `uv run --python 3.13 ty check ...`
       - `uv run --python 3.13 pytest -q tests/test_filter_worker.py tests/test_workers_advanced.py`
       - `uv run --python 3.13 pytest -q tests/test_gui_filter_logic.py -k 'general_search or initiate_filtering or on_filter_finished or clear_filter'`
     - resultados:
       - `49 passed`
       - `44 passed, 1 skipped`
     - prova real curta:
       - busca `MEL3, MEL3, MEL`
       - `FILTER_MS=1019.53`
       - `FILTER_ROWS=4680`
       - `df_exibido is _df_last_search_filtered == True`
  21. update de merge multi-chunk por indice:
     - a deduplicacao final deixou de comparar linha inteira
     - o merge agora preserva a primeira ocorrencia de cada indice original do `df_completo`
     - isso vale para:
       - `FilterWorker`
       - modo sincrono
       - fallback sem worker
     - contrato preservado:
       - chunk unico reaproveita o proprio frame
       - chunk vazio reaproveita a base
       - sobreposicao entre chunks diferentes continua sem repeticao
       - linhas iguais com indices diferentes continuam existindo
     - validacao aterrada:
       - `uv run --python 3.13 python -m py_compile gui/workers/filter_worker.py gui/mixins/filter_gui_ssa_mixin.py tests/test_filter_worker.py tests/test_gui_filter_logic.py`
       - `uv run --python 3.13 ruff check ...`
       - `uv run --python 3.13 ty check ...`
       - `uv run --python 3.13 pytest -q tests/test_filter_worker.py tests/test_workers_advanced.py`
       - `uv run --python 3.13 pytest -q tests/test_gui_filter_logic.py -k 'general_search or initiate_filtering or on_filter_finished or clear_filter'`
     - resultados:
       - `51 passed`
       - `46 passed, 1 skipped`
     - prova real curta:
       - chunks artificiais `MEL3 + MEL`
       - `FILTER_MS=1674.28`
       - `FILTER_ROWS=22606`
       - `df_exibido is _df_last_search_filtered == True`
     - leitura:
       - o custo isolado do dedup de merge caiu de `~105.89ms` para um caminho equivalente de `~9.60ms` no diagnostico real
  22. docs vivos estavam atrasados antes deste sync:
     - `docs/AGENTS_HANDOFF_NEXT_CYCLE.md`
     - `docs/NEXT_CHAT_MIGRATION.md`
     - `docs/RECOVERY_BACKLOG.md`
     - eles agora devem contar a historia da branch a partir deste topo, nao do snapshot de `2026-04-15`
  23. update de import/politica ja aterrada:
     - `core/app_logic.py:1615` deixou de ser pendencia aberta nesta frente
     - `_process_file_with_resilience(...)` agora contem `KeyError` e `AttributeError` por arquivo sem derrubar o lote inteiro
     - `_import_single_file(...)` passou a tolerar ausencia de `validation_report["is_valid"]` via `get("is_valid", False)`
     - validacao focada aterrada:
       - `uv run --python 3.13 python -m py_compile core/app_logic.py tests/test_import_single_error_classification.py`
       - `uv run --python 3.13 ruff check core/app_logic.py tests/test_import_single_error_classification.py`
       - `uv run --python 3.13 ty check core/app_logic.py tests/test_import_single_error_classification.py`
       - `uv run --python 3.13 pytest -q tests/test_import_single_error_classification.py`
       - resultado: `15 passed`
  24. regra de retomada obrigatoria daqui em diante:
     - a frente quente da GUI deve permanecer fechada salvo novo repro material
     - `core/app_logic.py:1615` agora esta fechado
     - o residual de `gui/workers/filter_worker.py:182` no caminho de frame unico foi fechado em `0c57e699a3867cd88a8faf926ad9d3f1a11f7023`
     - a duplicacao de fallback em `gui/ssa/gui_workers.py:910` foi reduzida em `fe608884496868c08f61557e9b844076ee80acb5`
     - a proxima frente principal deve voltar para diagnostico puro de multi-chunk em:
       - `gui/workers/filter_worker.py:182`
       - o custo de `drop_duplicates()` no merge por sobreposicao forte ja foi reduzido
       - a proxima rodada deve medir apenas o residual realmente aberto, sem reabrir o merge ja fechado
     - se reaparecer residual de teste, tratar em frente separada e pequena

## HISTORICAL SNAPSHOT 2026-04-14 10h15

- Leitura rapida:
  1. branch alvo confirmada: `dev`
  2. este slice consolida dois temas sem mistura funcional:
    - separacao de caixas de status na GUI (`filtered_status_label` para contagem, `status_label` para aviso/busca)
    - sincronizacao das larguras Windows entre codigo e preferencia versionada
  3. o contrato de status agora e:
    - contagem sempre em `Status: X de Y SSAs`
    - aviso de busca sem resultado em `status_label`
  4. fixture realista de 50 linhas foi adicionada para cobertura de busca geral com dados sanitizados
  5. alteracoes colaterais de fallback/plataforma permanecem fora deste slice
  6. PR ativo lido: `#47` `dev -> main` (`Merge dev into main for stabilization and gui follow-up`)

## HISTORICAL SNAPSHOT 2026-04-11 23h00

- Leitura rapida:
  1. branch alvo confirmada: `dev`
  2. este slice fechou o vazamento dos globais de workers aposentados no harness de `tests/test_gui_filter_logic.py`
  3. `setup_method` agora tira snapshot e reseta, e `teardown_method` restaura os globais usados nos testes
  4. follow-up minimo validou `gui/gui_ssa.py` para reaproveitar o cache de sort de `num_reprogramacoes` e mostrar o path real no dialogo de reset
  5. follow-up minimo validou `.gitignore` para preservar `/temp/.gitkeep` sem reabrir limpeza ampla de regras
  6. backlog e handoff foram atualizados para registrar o item fechado e o residual documental ainda pendente

## HISTORICAL SNAPSHOT 2026-04-09 22h26

- Leitura rapida:
  1. branch alvo confirmada: `dev`
  2. stash preservado fora de `dev`:
     - `stash@{0}` `On main: pre-dev-switch-display-mappings-20260406`
  3. esta frente consolidou o contrato do bloco GUI/tabela/detalhes sem refatoracao ampla:
     - busca geral da GUI agora e dona explicita das colunas de busca
     - reorder preserva detalhes
     - sort preserva detalhes
     - resize persiste largura na coluna correta
     - reorder em schema parcial preserva colunas visiveis ausentes
     - derivadas ficaram travadas em contrato de navegacao e retorno a origem
     - selecao stale nao sobrevive ao rebuild de pagina
     - filtro assincrono preserva ou migra detalhes conforme permanencia da SSA atual
  4. docs de referencia desta frente:
     - `docs/GUI_GENERAL_SEARCH_COLUMN_CONTRACT.md`
     - `docs/GUI_STATE_CONTRACT_POSTMORTEM_20260409.md`
  5. commits chave desta frente:
     - `bf57520d` `STABILITY_PATCH: make GUI own general search columns`
     - `38cb9cc5` `STABILITY_PATCH: harden header column resolution and reorder sync`
     - `048700c4` `STABILITY_PATCH: preserve hidden-visible column state on partial reorder`
     - `5e581d6e` `STABILITY_PATCH: align header resize persistence with visual mapping`
     - `c45d9e42` `STABILITY_PATCH: keep details panel stable during column reorder`
     - `3bc0d36f` `STABILITY_PATCH: preserve details during header sorting`
     - `21135ccf` `STABILITY_PATCH: lock derivadas detail navigation contract`
     - `43c1443b` `STABILITY_PATCH: clear stale selection on page rebuild`
     - `ce7501d2` `STABILITY_PATCH: lock async filter selection detail contract`
  6. validacao relevante desta frente:
     - `py_compile`, `ruff`, `ty` verdes nos slices tocados
     - `pytest` focados relevantes verdes
     - `bandit` indisponivel neste host (`No module named bandit`)
  7. `kluster` esta disponivel neste host:
     - `/Users/menon/.kluster/cli/bin/kluster`
     - timeout eventual de review deve ser tratado como bloqueio de ferramenta, nao como gate verde
  8. PR ativo:
     - `#46` `dev -> main`
     - `mergeStateStatus=UNSTABLE`
  9. checks remotos relevantes:
     - `DeepSource: Python` -> fail
     - `code/snyk (mauriciomenon)` -> fail por limite
- Regra operacional importante desta retomada:
  1. nao confundir o stash criado no `main` com trabalho pendente do `dev`
  2. nao reaplicar `display_mappings.json` sem decidir primeiro se ele deve sair do versionamento
  3. `config/gui_main_preferences.json` continua sendo o arquivo efetivo de runtime, e o repo tambem tem `config/gui_main_preferences.json.example` como referencia canonica de auditoria
  4. o comportamento agora precisa ser lido assim, sem ambiguidade:
     - se faltar `config/gui_main_preferences.json` ou o runtime mudar `SSA_CONFIG_DIR`, o runtime usa os defaults em memoria do codigo
     - se existir largura persistida valida, ela ganha da largura calculada em runtime
     - o fallback local da tabela e o baseline automatico partem do contrato canonico em `gui/gui_config.py`
     - o baseline canonico de widths agora nasce de `DEFAULT_COLUMN_WIDTHS_BY_PLATFORM`
     - `DEFAULT_COLUMN_WIDTHS` no runtime ja e o mapa resolvido para a plataforma atual
     - `config/gui_main_preferences.json` e o arquivo efetivo tracked com ultima palavra em runtime; o `.example` documenta o padrao; codigo define a base
     - a fase antiga de local-only/skip-worktree para esse arquivo e apenas historica
     - o header da GUI agora escolhe `long -> medium -> short` pela largura real da coluna, com reserva para `[f] `
     - as celulas da tabela agora aceitam `left|center|right`, com default `right`
     - reorder e sort de coluna nao podem atualizar o painel de detalhes
     - resize usa o mesmo contrato de resolucao de coluna do header
     - reorder em schema parcial nao pode expulsar colunas visiveis ausentes do estado persistido
     - o contrato de derivadas deve ser lido pelo post-mortem e pelos testes de regressao, nao por inferencia
     - `selectionChanged` so pode governar detalhes a partir da selecao atual valida; selecao stale precisa morrer no rebuild
     - filtro assincrono com selecao manual previa preserva detalhes se a SSA continua visivel e migra detalhes quando ela sai do resultado
     - a CLI continua fora do contrato de preferencias da GUI, mas segue usando `display_map`, `short_labels`, `fixed_widths` e alternancia `short/full`
     - `core/handler_base.py:197` continua documentado apenas como renderer paralelo fora do caminho principal `main.py -> interface/cli.py -> interface/table_printer.py`
     - referencia detalhada do algoritmo: `docs/COLUMN_WIDTHS_BY_PLATFORM.md`
- Proximo foco recomendado:
  1. manter este sync documental como `DOC_SYNC` isolado, sem tocar runtime
  2. nao reabrir `tests/test_quality_gates_smoke.py` nem `tests/test_workers_advanced.py` sem novo repro
  3. nao reabrir `core/app_logic.py:1615`; essa frente ja foi fechada
  4. fazer novo diagnostico puro para identificar o residual tecnico real ainda aberto
  5. manter qualquer refatoracao de `display_current_page(...)` em slice separado
  7. nao reabrir layout, ordem visual ou defaults de produto sem pedido explicito

## HISTORICAL SNAPSHOT 2026-03-31 09h49

- Leitura rapida:
  1. branch alvo: `dev`
  2. metadata local ativa: `4.37`
  3. ultima tag publicada em `dev`: `v4.36`
  4. ultimos slices relevantes ja aterrados:
     - `7913c712` `DOC_SYNC: align live continuity docs`
     - `02ec4a30` `DOC_SYNC: add ultra technical audit report`
     - `b7af8aef` `STABILITY_PATCH: support non-text search columns`
     - `d6fbb4fe` `STABILITY_PATCH: unify advanced filter state`
  5. recuperacao forense desta retomada confirmou:
     - worktree limpo
     - `HEAD...origin/dev = 00`
     - nenhum shell/agent ativo
     - nenhum patch de runtime interrompido detectado
  6. existe residuo antigo `.git\REBASE_HEAD` datado de `2025-11-26`, sem `rebase-apply`/`rebase-merge`; tratar como hygiene de Git fora do slice atual
- PASSO 0 OBRIGATORIO ANTES DE QUALQUER NOVA FRENTE:
  1. revisar checks e comentarios mais recentes do PR `dev -> main`
  2. confirmar worktree limpo
  3. confirmar que o gate do Kluster esta disponivel antes do primeiro patch; se o review remoto oscilar, registrar o bloqueio exato
  4. atacar primeiro `svp03-targeted-repro`, salvo ordem contraria explicita do usuario
  5. so depois responder threads cujo status mudou de verdade
- Prioridade operacional:
  1. `P0`: manter fechado o contrato de `numero_ssa` sem reabrir heuristica ou truncagem
  2. `P0`: manter fechado o contrato anti-downgrade de `situacao` em empate de `data_cadastro`
  3. `P1`: reproduzir tecnicamente o caso `svp-03` / SSA `202604849`
  4. `P1`: definir historico de filtros para `undo` e `redo`
  5. `P1`: agrupar ajustes pontuais de ordem/labels sem reabrir layout geral
  6. `P1`: validar habilitacao minima de drag de cabecalho de colunas
  7. `P2`: revisar hotspots restantes da thread principal apos o sprint GUI
  8. `P2`: decidir paridade CLI vs GUI para diff/full import e discovery
  9. `P2`: endurecer rollback/error boundary residual em `database*`
  10. `P2`: auditar testes viciados no fluxo critico de dados/CLI
  11. `P2`: convergir helper local de data em `database_upsert_logic.py`
- Sprint GUI entregue nesta frente:
  0. implementacao runtime consolidada nos commits `b343c621` e `07ebfe1d`
  1. `[f]` no cabecalho sincronizado com filtros avancados equivalentes
  2. dedupe do resumo `Filtros ativos`
  3. macro `Baixar` com `SAD`
  4. dialogo de filtro por coluna com hint e largura minima padronizada
  5. sync manual de derivadas movido para background em runtime normal
  6. caixa `Filtros ativos` com borda destacada e texto em negrito quando ativa
  7. botao `Abrir SAM`
  8. nova caixa `Status: X de Y SSAs`
  9. `Semana Atual` centralizado entre os controles
  10. `#` da lista abrindo a SSA no SAM
  11. detalhe da SSA com `situacao` expandida
  12. copia por duplo clique do numero da SSA no detalhe
  13. visualizacao de derivadas em arvore textual mais clara
  14. `load_other_database()` em background no runtime normal
  15. aba dedicada `Arvore` no dialogo de detalhes, com arvore navegavel e painel inferior de detalhes
  16. aba `Arvore` ganhou subabas `Grafo`, `Arvore` e `Mermaid`
  17. `_normalize_ssa_series` de detalhes foi reotimizado por valores unicos
  18. historico: subaba `Grafo` foi promovida de refinamento para entrega por comando explicito neste ciclo
- Follow-up entregue apos o sprint GUI:
  1. `filter_dataframe()` passou a aceitar `search_columns` nao textuais sem falso vazio
  2. `setor_executor` deixou de manter estado persistente divergente entre combo rapido e painel avancado
  3. `Solicitante` no painel avancado passou a reconhecer `responsavel_solicitante`
  4. prefixo de area/setor de responsaveis ficou estavel contra subset filtrado
- Follow-up do sprint GUI:
  1. `svp-03` / SSA `202604849` ainda precisa reproducao dirigida
  2. `undo`/`redo` de filtros ainda nao existe
  3. ordem/labels pedidas pelo usuario ainda precisam agrupamento por arquivo
  4. drag de colunas por cabecalho ainda precisa prova tecnica/local
  5. render/table refresh apos filtros ainda e hotspot provavel de custo
  6. staging/copy de importacao externa ainda merece revisao de thread principal
  7. `bandit` segue indisponivel neste ambiente atual (`No module named bandit`); nao fingir gate verde
- Estado tecnico fechado:
  1. o `.0` vazava por regras duplicadas no write path
  2. a normalizacao de storage foi centralizada
  3. o artefato decimal canonico `NNNNNNNNN.0` agora morre no inicio do fluxo
  4. salvaguardas posteriores de id canonico devem ser mantidas
  5. `numero_ssa` real validado nas planilhas medidas segue em `9 digitos`; a narrativa de `10 digitos` foi erro de inferencia/teste synthetic
- Integridade do handoff:
  1. nada foi perdido na reorganizacao dos docs
  2. snapshots antigos permanecem abaixo como historico
  3. o estado atual precisa ser continuado pelo topo, nao por colagem no historico
- Validacao atual:
  1. baseline amplo registrado nos docs vivos:
     - `pytest -q tests` -> `993 passed, 4 skipped, 11 subtests passed`
  2. hotfix de busca nao textual:
     - `py_compile`, `ruff`, `ty` verdes
     - `pytest -q tests/test_app_logic_filter_contract.py` -> `20 passed`
  3. patch de sincronizacao de filtros:
     - `py_compile`, `ruff`, `ty` verdes
     - `pytest -q tests/test_gui_filter_logic.py -k "...executor...responsavel..."` -> `8 passed`
- Regras e proibicoes que o proximo ciclo deve respeitar sem excecao:
  1. nao criar branch, PR, worktree, pasta ou tag sem autorizacao explicita
  2. nao editar nada antes de aprovar plano curto com escopo e proibicoes
  3. nao reabrir parser de operadores textuais legados
  4. nao criar helper/wrapper extra sem necessidade real
  5. nao usar reset destrutivo
  6. commits atomicos e rollback facil por slice
- Regras para o proximo ciclo:
  1. nao criar tag nova antes da rodada final de backlog e review externo
  2. nao reabrir operadores textuais legados de busca
  3. nao reintroduzir regra paralela de `numero_ssa`; partir sempre da fonte central
- Arquivos autoritativos do proximo ciclo:
  1. `AGENTS.md`
  2. `README.md`
  3. `docs/README.md`
  4. `docs/NEXT_CHAT_MIGRATION.md`
  5. `docs/AGENTS_HANDOFF_NEXT_CYCLE.md`
  6. `docs/RECOVERY_BACKLOG.md`
  7. `docs/NUNCA_CONFIE_IA.md`
  8. `docs/GUIA_DISTRIBUICAO.md`
  9. `.github/instructions/kluster-code-verify.instructions.md`
  10. `docs/archive/LEGACY_DOCS_REORG_STUDY_20260327.md`
- Commits recentes desta frente:
  1. `02ec4a30` `DOC_SYNC: add ultra technical audit report`
  2. `b7af8aef` `STABILITY_PATCH: support non-text search columns`
  3. `d6fbb4fe` `STABILITY_PATCH: unify advanced filter state`
  4. `194fc4e7` `STABILITY_PATCH: sync visual filter indicators`
  5. `cd06941f` `STABILITY_PATCH: improve column filter prompt`
  6. `31dc9c99` `STABILITY_PATCH: move derivadas sync off ui thread`
  7. `9983a757` `STABILITY_PATCH: tighten async import gui contract`
  8. `b343c621` `STABILITY_PATCH: finish gui sam status and details sprint`
  9. `a34a54b3` `HOTFIX_BLOCKER: prevent same-date situacao downgrade`
  10. `051d3b6e` `STABILITY_PATCH: add dedicated derivadas tree tab`
  11. `07ebfe1d` `STABILITY_PATCH: add visual derivadas graph tab`
- Estado do Kluster local:
  1. configuracao MCP local foi corrigida para `pnpm.CMD dlx ... --server=https://api.kluster.ai`
  2. timeout eventual de `manualCheck` deve ser tratado como bloqueio do review remoto, nao como bug do repo
  3. Kluster continua obrigatorio como gate apos alteracoes
- Pendencia documental nova:
  1. usar `docs/NUNCA_CONFIE_IA.md` como checklist de contencao antes de tocar em fluxos criticos de dados

## HISTORICAL SNAPSHOTS

O historico detalhado desta frente permanece centralizado em `docs/RECOVERY_BACKLOG.md`.
Este handoff deve carregar apenas o topo vivo, para evitar divergencia e duplicacao entre documentos de continuidade.
- Politica de render proposta para o proximo ciclo:
  1. medir e reduzir primeiro o custo de render da tabela, sem mexer no parser.
  2. considerar early-exit quando o resultado filtrado nao muda a pagina efetiva.
  3. separar render de tabela, resumo e sync para permitir atualizacao parcial barata.
  4. manter mudanca minima e sem alterar layout.

## HISTORICAL SNAPSHOT 2026-03-20 17h25

- Objetivo consolidado deste ciclo:
  1. revisar a pilha real do CLI em subprocesso.
  2. corrigir hangs de fluxo basico sem refatoracao ampla.
  3. promover o baseline para `v4.33`.
  4. fechar o micro-slice minimo do Streamlit e revisar o repo por furos ululantes sem voltar a editar runtime maior.
- Estado confirmado:
  1. branch alvo: `dev`.
  2. commits principais deste ciclo:
     - `ec98013f` `STABILITY_PATCH: harden real CLI review flows`
     - `83660463` `STABILITY_PATCH: bump baseline to v4.33`
     - `c7992b39` `STABILITY_PATCH: align Streamlit title with v4.33`
     - `220e1847` `HOTFIX_BLOCKER: restore main streamlit launcher`
  3. residuos locais fora de escopo continuam presentes:
     - `M .python-version`
     - `M config/cli_enhancements.json`
     - `M config/gui_main_preferences.json`
     - `M data/ssas.db`
     - `M pyproject.toml`
     - `M requirements_build.txt`
     - `?? .backups/*`
     - `?? config/cli_enhancements.json.lock`
     - `?? docs_entrada/*.xlsx`
     - `?? *.bak.*`
- Diagnostico tecnico consolidado:
  1. a causa real dos hangs em fluxos como `clear`, `status-cli -> v` e `m -> qq` era custo de renderizacao:
     - o printer preparava o DataFrame inteiro antes da paginacao
     - em sessao real isso custava tempo demais e deixava a CLI parecer travada
  2. a correcao foi paginacao lazy com preparo por pagina:
     - preparar so a pagina corrente
     - cachear a pagina corrente
     - manter o contrato de `m`
  3. o startup do CLI segue sem rescan automatico.
  4. o CLI segue sem comando de diff-only rescan; a GUI ja tem esse split.
  5. `q` continua com semantica por escopo:
     - prompt principal: sai da aplicacao
     - prompt da paginacao: fecha exibicao
     - `qq`: sai da aplicacao a partir da paginacao
  6. o achado ululante do launcher Streamlit foi fechado no mesmo ciclo:
     - `launch_streamlit()` agora aponta para `dev_env/streamlit_app.py`
     - o entrypoint `main.py --streamlit` voltou a funcionar
- Micro-slice Streamlit entregue:
  1. o titulo/cabecalho do Streamlit agora refletem a versao ativa `v4.33`
  2. regressao focada adicionada em `tests/test_streamlit_filter_cache.py`
  3. regressao focada do launcher adicionada em `tests/test_main_streamlit_launcher.py`
- Validacao consolidada:
  1. `py_compile`, `ruff` e `ty` verdes no escopo do CLI endurecido.
  2. suite CLI ampliada:
     - `tests/test_cli_loop_filter_rounds.py`
     - `tests/test_cli_pagination_prompt.py`
     - `tests/test_table_printer.py`
     - `tests/test_search_v_character.py`
     - `tests/test_cli_get_ssa_query_identifier_guard.py`
     - resultado: `44 passed`
  3. teste de build/versionamento:
     - `tests/test_build_multiplatform_manifest.py` -> `5 passed`
  4. teste Streamlit:
     - `tests/test_streamlit_filter_cache.py` -> `46 passed`
     - `tests/test_main_streamlit_launcher.py` -> `2 passed`
  4. subprocessos reais confirmados como limpos:
     - `h -> q`
     - `mel4 -> q`
     - `mel4 -> clear -> q`
     - `mel4 -> status-cli -> v -> q`
     - `mel4 -> m -> qq`
     - `force-rescan -> q`
- Pendencias ainda abertas:
  1. `_handle_rescan` continua grande demais.
  2. `ord` / `ordi` ainda merecem revisao de contrato vs ordem realmente exibida.
  3. diff-only rescan ainda inexiste no CLI.
  4. schema local sem `responsavel_solicitante`.

## HISTORICAL SNAPSHOT 2026-03-20 14:00 - previous current truth

- Objetivo desta rodada:
  1. impedir que subprocessos de teste do CLI escrevam no arquivo real `config/cli_enhancements.json`.
  2. isolar settings de automacao em arquivo temporario.
  3. manter o caminho padrao do runtime inalterado para uso normal.
- Estado confirmado:
  1. branch alvo: `dev`.
  2. residuos locais fora de escopo continuam presentes:
     - `M .python-version`
     - `M config/cli_enhancements.json`
     - `M config/gui_main_preferences.json`
     - `M data/ssas.db`
     - `M pyproject.toml`
     - `M requirements_build.txt`
     - `?? .backups/*`
     - `?? config/cli_enhancements.json.lock`
     - `?? docs_entrada/*.xlsx`
     - `?? *.bak.*`
  3. o `M config/cli_enhancements.json` ja existia; o slice atual so evita novas sujeiras.
- Commit funcional novo:
  1. `049b0b2e`
     - `CLIEnhancementManager` aceita override de caminho por `SSA_CLI_ENHANCEMENTS_PATH`
     - o override e validado por `ensure_path_is_allowed(...)`
     - subprocessos de teste passam a usar arquivo temporario proprio
- Diagnostico tecnico consolidado:
  1. o problema real desta rodada era acoplamento dos testes CLI ao arquivo real de settings.
  2. a sujidade vinha dos subprocessos que chamavam `toggle-debug` e `enhanced-on/off`.
  3. a correcao minima foi um override seguro de caminho, sem mexer no fluxo funcional da CLI.
- Validacao consolidada:
  1. `py_compile`, `ruff` e `ty` verdes no escopo do slice.
  2. `tests/test_cli_loop_filter_rounds.py` no foco de subprocesso/status/paginacao -> `13 passed, 9 deselected`.
  3. Kluster encontrou 1 issue media na primeira passada e ficou clean apos a validacao de path.
- Pendencias ainda abertas:
  1. `_handle_rescan` continua grande demais.
  2. `m`, `m z`, status e paginacao ainda merecem cobertura combinada de sessao longa.
  3. o resido ja existente em `config/cli_enhancements.json` continua fora de escopo ate comando explicito.
  4. schema local sem `responsavel_solicitante`.

## HISTORICAL SNAPSHOT 2026-03-20 13:47 - previous current truth

- Objetivo desta rodada:
  1. impedir que `m z` trave automacao do CLI.
  2. cobrir o caso real por subprocesso.
  3. preservar o `m` normal e o comportamento interativo.
- Estado confirmado:
  1. branch alvo: `dev`.
  2. residuos locais fora de escopo continuam presentes:
     - `M .python-version`
     - `M config/gui_main_preferences.json`
     - `M data/ssas.db`
     - `M pyproject.toml`
     - `M requirements_build.txt`
     - `?? .backups/*`
     - `?? config/cli_enhancements.json.lock`
     - `?? docs_entrada/*.xlsx`
     - `?? *.bak.*`
  3. esses residuos nao devem ser revertidos nem incluidos por inferencia.
- Commit funcional novo:
  1. `b796b6e5`
     - `m z` passa a retornar rapido com mensagem clara em sessao non-interactive.
     - novos testes cobrem o handler e o subprocesso `mel4 -> m z -> q`.
- Diagnostico tecnico consolidado:
  1. o bug real desta rodada era timeout de automacao por volume de saida em `m z`.
  2. nao era falha de parser, nem do loop principal, nem do renderer.
  3. a correcao adotada foi uma guarda minima so para `show_all` em non-interactive.
- Validacao consolidada:
  1. `py_compile`, `ruff` e `ty` verdes no escopo do slice.
  2. `tests/test_cli_loop_filter_rounds.py` no foco de paginacao/status/help/subprocess -> `13 passed, 9 deselected`.
  3. Kluster limpo no lote pequeno deste slice.
- Pendencias ainda abertas:
  1. `_handle_rescan` continua grande demais.
  2. `m`, `m z`, status e paginacao ainda merecem cobertura combinada de sessao longa.
  3. manager de CLI continua acumulando texto de status + persistencia local.
  4. schema local sem `responsavel_solicitante`.

## HISTORICAL SNAPSHOT 2026-03-20 13:33 - previous current truth

- Objetivo desta rodada:
  1. limpar a UX textual de `status-cli`, `toggle-debug` e `enhanced-on/off`.
  2. reduzir o ruido do prompt principal do CLI.
  3. fechar cobertura focada disso em unitario e subprocesso.
- Estado confirmado:
  1. branch alvo: `dev`.
  2. residuos locais fora de escopo continuam presentes:
     - `M .python-version`
     - `M config/gui_main_preferences.json`
     - `M data/ssas.db`
     - `M pyproject.toml`
     - `M requirements_build.txt`
     - `?? .backups/*`
     - `?? config/cli_enhancements.json.lock`
     - `?? docs_entrada/*.xlsx`
     - `?? *.bak.*`
  3. esses residuos nao devem ser revertidos nem incluidos por inferencia.
- Commit funcional novo:
  1. `82d0465b`
     - wrappers pequenos deixam `status-cli` em ASCII e removem ruido de `toggle-debug` / `enhanced-on/off`.
     - o prompt principal fica mais curto e direto.
     - testes novos cobrem status ASCII, feedback compacto e subprocesso real.
- Diagnostico tecnico consolidado:
  1. nao havia bug de fluxo aqui; o problema era UX textual ruim em sessao real.
  2. o `status-cli` herdava bullets unicode e acentos do manager.
  3. `toggle-debug` ainda respondia com prefixo ruidoso e tom inconsistente.
- Validacao consolidada:
  1. `py_compile`, `ruff` e `ty` verdes no escopo do slice.
  2. `tests/test_cli_loop_filter_rounds.py` no foco `status_cli/toggle/enhanced/help/force_rescan/subprocess` -> `11 passed, 9 deselected`.
  3. Kluster encontrou 1 issue media na primeira passada e ficou clean apos o ajuste.
- Pendencias ainda abertas:
  1. `_handle_rescan` continua grande demais.
  2. `status-cli` ainda depende do texto do manager e pode merecer refino proprio em slice futuro.
  3. `m`, `m z`, paginacao e `status-cli` ainda pedem mais cobertura de sessao real.
  4. schema local sem `responsavel_solicitante`.

## HISTORICAL SNAPSHOT 2026-03-20 13:18 - previous current truth

- Objetivo desta rodada:
  1. impedir `rescan/force-rescan` pesado em sessao automatizada.
  2. alinhar o tom do help detalhado ao contrato ja exibido no help inicial.
  3. manter o patch pequeno e testavel.
- Estado confirmado:
  1. branch alvo: `dev`.
  2. residuos locais fora de escopo continuam presentes:
     - `M .python-version`
     - `M config/gui_main_preferences.json`
     - `M data/ssas.db`
     - `M pyproject.toml`
     - `M requirements_build.txt`
     - `?? .backups/*`
     - `?? config/cli_enhancements.json.lock`
     - `?? docs_entrada/*.xlsx`
     - `?? *.bak.*`
  3. esses residuos nao devem ser revertidos nem incluidos por inferencia.
- Commit funcional novo:
  1. `0f2f9a93`
     - `rescan/force-rescan` passam a falhar rapido com mensagem clara em sessao non-interactive.
     - o help detalhado passa a espelhar explicitamente o contrato da busca inicial.
     - novos testes cobrem consistencia textual e subprocesso `force-rescan -> q`.
- Diagnostico tecnico consolidado:
  1. o bug real desta rodada era travamento de `force-rescan` no harness por falta de guarda de contexto.
  2. o help detalhado ainda repetia a regra da busca com densidade diferente do help inicial.
  3. a solucao adotada foi guarda minima + teste real por subprocesso, sem abrir refatoracao ampla.
- Validacao consolidada:
  1. `py_compile`, `ruff` e `ty` verdes no escopo do slice.
  2. `tests/test_cli_loop_filter_rounds.py` no foco `help/force_rescan/subprocess` -> `9 passed, 8 deselected`.
  3. Kluster limpo no lote pequeno deste slice.
- Pendencias ainda abertas:
  1. `_handle_rescan` continua grande demais.
  2. `status-cli`, `toggle-debug` e afins ainda pedem refinamento de UX/texto.
  3. consolidacao final de help inicial vs help detalhado ainda pode melhorar.
  4. schema local sem `responsavel_solicitante`.

## HISTORICAL SNAPSHOT 2026-03-20 12:55 - previous current truth

- Objetivo desta rodada:
  1. mover `get_ssa_query()` para a camada de banco.
  2. impedir que o help detalhado do CLI quebre a sessao em modo pipe/non-interactive.
  3. fechar a cobertura focada desse caminho antes do proximo refinamento.
- Estado confirmado:
  1. branch alvo: `dev`.
  2. residuos locais fora de escopo continuam presentes:
     - `M .python-version`
     - `M config/gui_main_preferences.json`
     - `M data/ssas.db`
     - `M gui/gui_ssa.py`
     - `M pyproject.toml`
     - `M requirements_build.txt`
     - `?? .backups/*`
     - `?? config/cli_enhancements.json.lock`
     - `?? docs_entrada/*.xlsx`
     - `?? *.bak.*`
  3. esses residuos nao devem ser revertidos nem incluidos por inferencia.
- Commit funcional novo:
  1. `65351ef0`
     - `get_ssa_query()` foi extraido para `armazenamento/database.py`.
     - `_handle_help()` nao pausa mais em `SSA_NON_INTERACTIVE=1` nem em stdin sem TTY.
     - novos testes travam:
       - help sem pausa em modo non-interactive
       - subprocesso `h -> q` com saida limpa
- Diagnostico tecnico consolidado:
  1. o bug reproduzivel do CLI nesta rodada era `h -> q` com `EOFError`.
  2. a causa era um `input()` extra dentro do help, nao o loop principal em si.
  3. `get_ssa_query()` ainda estava acoplado a UI/CLI sem necessidade funcional.
- Validacao consolidada:
  1. `py_compile`, `ruff` e `ty` verdes no escopo do slice.
  2. `tests/test_cli_get_ssa_query_identifier_guard.py + tests/test_cli_loop_filter_rounds.py` no foco `get_ssa_query/help/subprocess` -> `11 passed, 8 deselected`.
  3. Kluster limpo no lote pequeno deste slice.
- Pendencias ainda abertas:
  1. `_handle_rescan` continua grande demais.
  2. consolidacao final de tom/densidade entre help inicial e help detalhado segue em aberto.
  3. `force-rescan` em sessao automatizada ainda pede guarda de UX/teste dedicado.
  4. schema local sem `responsavel_solicitante`.

## HISTORICAL SNAPSHOT 2026-03-20 12:05 - previous current truth

- Objetivo desta rodada:
  1. revisar a camada de help/menu do CLI e o renderer em terminal estreito.
  2. alinhar o help completo ao contrato textual atual do runtime.
  3. fechar cobertura de terminal estreito no `EnhancedTablePrinter`.
- Estado confirmado:
  1. branch alvo: `dev`.
  2. residuos locais fora de escopo continuam presentes:
     - `M .python-version`
     - `M config/gui_main_preferences.json`
     - `M data/ssas.db`
     - `M gui/gui_ssa.py`
     - `M pyproject.toml`
     - `M requirements_build.txt`
     - `?? .backups/*`
     - `?? docs_entrada/*.xlsx`
     - `?? *.bak.*`
  3. esses residuos nao devem ser revertidos nem incluidos por inferencia.
- Commits funcionais novos:
  1. `43770be4`
     - help completo sai da caixa hardcoded e passa a usar builder com wrap deterministico em 79 colunas.
     - `force-rescan` vira alias real de `rescan`.
  2. `3dd90c49`
     - `EnhancedTablePrinter` deixa de impor largura minima 80.
     - `CLIWidthManager` reduz colunas de texto ate um piso minimo quando o terminal e estreito.
- Diagnostico tecnico consolidado:
  1. o startup do CLI continua sem chamar `rescan` na abertura.
  2. o problema real do help era drift de contrato e layout:
     - `force-rescan` aparecia no help mas nao existia no loop
     - o help em caixa tinha linhas acima da moldura
  3. o problema real do renderer era largura minima artificial:
     - com terminal `70`, o printer ainda podia sair mais largo por causa de `max(..., 80)`
  4. a suite anterior nao pegava isso porque:
     - validava loop e fallback do help
     - nao validava caminho normal do help completo
     - nao validava `EnhancedTablePrinter` em terminal estreito real
  5. erro operacional desta rodada:
     - houve uma tentativa incorreta de commits paralelos
     - isso bateu em `index.lock`
     - correcao: seguir commits estritamente sequenciais
- Validacao consolidada:
  1. `py_compile`, `ruff` e `ty` verdes no escopo do CLI alterado.
  2. `tests/test_cli_loop_filter_rounds.py + tests/test_cli_pagination_prompt.py + tests/test_table_printer.py + tests/test_search_v_character.py` -> `24 passed`.
  3. testes novos:
     - `test_build_cli_plain_help_text_detailed_includes_force_rescan_alias`
     - `test_handle_help_normal_path_uses_plain_layout_without_box_art`
     - `test_start_cli_loop_accepts_force_rescan_alias`
     - `test_enhanced_printer_respects_narrow_terminal_width`
- Pendencias ainda abertas:
  1. `_handle_rescan` continua grande demais.
  2. `get_ssa_query()` continua na camada de UI/CLI.
  3. schema local sem `responsavel_solicitante`.
  4. termos curtos na busca superior seguem como decisao de produto.
  5. Kluster continua oscilando por timeout no lote do CLI.

## HISTORICAL SNAPSHOT 2026-03-20 11:32 - previous current truth

- Objetivo desta rodada:
  1. consolidar o contrato textual do CLI para nao voltar a divergir do runtime.
  2. confirmar por subprocesso que os fluxos antes suspeitos agora encerram normalmente.
  3. manter os debts estruturais restantes do CLI em slices separados.
- Estado confirmado:
  1. branch alvo: `dev`.
  2. residuos locais fora de escopo continuam presentes:
     - `M .python-version`
     - `M config/gui_main_preferences.json`
     - `M data/ssas.db`
     - `M gui/gui_ssa.py`
     - `M pyproject.toml`
     - `M requirements_build.txt`
     - `?? .backups/*`
     - `?? docs_entrada/*.xlsx`
     - `?? *.bak.*`
  3. esses residuos nao devem ser revertidos nem incluidos por inferencia.
- Commit funcional novo:
  1. `067a05d3`
     - help inicial e fallback do help completo passam a usar o mesmo texto compartilhado.
     - testes novos travam o contrato textual compartilhado.
  2. `6d29addf`
     - CLI passa a respeitar o contrato atual da busca superior.
     - lookup direto de detalhe fica restrito a SSA numerica exata.
     - `v` volta a reexibir o estado anterior.
     - exportacao rejeita nome inseguro e valida o diretorio de saida.
     - cache de render foi endurecido e `ord 0` passa a ser rejeitado.
- Diagnostico tecnico consolidado:
  1. apos estabilizar o loop, ainda restava duplicacao perigosa no help do CLI.
  2. essa duplicacao mantinha risco de drift entre help inicial e fallback do help completo.
  3. os cenarios de subprocesso que antes eram suspeitos agora encerram com `rc=0`:
     - `mel4 -> clear -> q`
     - `mel4 -> x mel4 -> q`
     - `mel4 -> danilo -> svp -> !STE -> q`
     - `mel4 -> v -> q`
- Validacao consolidada:
  1. `py_compile`, `ruff` e `ty` verdes em `interface/cli.py` e `tests/test_cli_loop_filter_rounds.py`.
  2. foco de CLI -> `18 passed`.
  3. testes novos:
     - `test_start_cli_loop_keeps_session_after_clear`
     - `test_start_cli_loop_back_rerenders_previous_state`
     - `test_start_cli_loop_treats_short_year_as_literal_search`
     - `test_start_cli_loop_opens_detail_for_exact_ssa_number`
     - `test_handle_export_rejects_unsafe_filename`
     - `test_handle_sort_rejects_zero_index`
     - `test_cached_pretty_print_df_cache_key_includes_rendered_rows`
     - `test_build_cli_plain_help_text_reflects_current_search_contract`
     - `test_handle_help_fallback_uses_shared_plain_help_text`
- Pendencias ainda abertas:
  1. schema local sem `responsavel_solicitante`.
  2. termos curtos na busca superior ainda dependem de decisao de produto.
  3. comentarios/docstrings/configs mortos fora do runtime ainda pedem limpeza em slice proprio.
  4. debt estrutural de CLI para proximo ciclo:
     - `_handle_rescan` grande demais
     - help completo em caixa continua separado do texto plano compartilhado
     - `get_ssa_query()` ainda na camada de UI
  5. Kluster estourou timeout repetidamente no lote do CLI apos o patch e nao devolveu findings adicionais; considerar isso bloqueio da ferramenta.

## HISTORICAL SNAPSHOT 2026-03-20 11:14 - previous current truth

- Objetivo desta rodada:
  1. estabilizar o loop interativo do CLI alinhando a busca ao contrato atual do `core`.
  2. fechar a regressao em que certas rodadas do CLI deixavam de reexibir dados.
  3. separar debts estruturais do CLI para um ciclo proprio, sem refatoracao ampla agora.
- Commit funcional entregue:
  1. `6d29addf`
     - CLI passa a respeitar o contrato atual da busca superior.
     - lookup direto de detalhe fica restrito a SSA numerica exata.
     - `v` volta a reexibir o estado anterior.
- Validacao consolidada:
  1. foco de CLI -> `16 passed`.

## HISTORICAL SNAPSHOT 2026-03-20 09:29 - previous current truth

- Objetivo desta rodada:
  1. tratar `SES` como equivalente funcional de `STE` nos filtros que usam esse estado terminal.
  2. corrigir a macro `Baixar` para operar com `SCA/SES/STE` e derivadas em `STE/SES`.
  3. registrar a avaliacao do triplo clique em limpar filtros como melhoria separada de UX.
- Estado confirmado:
  1. branch alvo: `dev`.
  2. residuos locais fora de escopo continuam presentes:
     - `M .python-version`
     - `M config/gui_main_preferences.json`
     - `M data/ssas.db`
     - `M gui/gui_ssa.py`
     - `M pyproject.toml`
     - `M requirements_build.txt`
     - `?? .backups/*`
     - `?? docs_entrada/*.xlsx`
     - `?? *.bak.*`
  3. esses residuos nao devem ser revertidos nem incluidos por inferencia.
- Commit funcional novo:
  1. `9b80344d`
     - macro `Baixar` passa a excluir `SCA/SES/STE`.
     - `derivada_all_ste` passa a aceitar `STE/SES` como estado terminal funcional.
     - resumo funcional e texto do checkbox oculto passam a refletir `SCA/SES/STE`.
     - testes novos travam exclusao funcional com `SES` e macro `Baixar`.
- Diagnostico tecnico consolidado:
  1. `SES` continua distinto para o usuario, mas entrou na mesma classe funcional terminal de `STE` nos filtros pedidos.
  2. os nomes internos legados `_exclude_ste_sca` e `derivada_all_ste` foram mantidos por compatibilidade; a semantica funcional e que foi expandida.
  3. a mudanca foi localizada em:
     - `gui/ssa/gui_filters_advanced_logic.py`
     - `gui/ssa/gui_filters_advanced_ui.py`
     - `gui/mixins/filter_gui_ssa_mixin.py`
     - `gui/gui_ssa.py`
  4. naquele ponto, o triplo clique em limpar filtros foi avaliado como melhoria separada; depois, no mesmo dia, o atalho foi promovido em slice proprio com confirmacao para hard reset.
- Validacao consolidada:
  1. `py_compile`, `ruff` e `ty` verdes no escopo alterado.
  2. `tests/test_gui_filters_advanced_logic.py` -> `15 passed`.
  3. `tests/test_gui_filter_logic.py` no foco do slice -> `13 passed, 146 deselected`.
  4. testes novos:
     - `test_apply_advanced_filters_derivada_all_ste_accepts_ses_as_terminal_state`
     - `test_macro_baixar_excludes_sca_ses_ste_and_keeps_ste_or_ses_derivadas`
- Pendencias ainda abertas:
  1. revisar outros fluxos que talvez ainda tratem `STE` isoladamente, especialmente ordenacao em `gui/workers/data_loader_worker.py`.
  2. schema local sem `responsavel_solicitante`.
  3. termos curtos na busca superior ainda dependem de decisao de produto.
  4. comentarios/docstrings/configs mortos fora do runtime ainda pedem limpeza em slice proprio.

## HISTORICAL SNAPSHOT 2026-03-20 08:49 - previous current truth

- Objetivo desta rodada:
  1. sincronizar handoff com os ultimos slices funcionais ja publicados em `dev`.
  2. registrar a leitura correta do repro real `danilo, svp, mel4, !STE`.
  3. registrar a regra atual de troca de `setor_executor` em dado mais novo.
- Estado confirmado:
  1. branch alvo: `dev`.
  2. residuos locais fora de escopo continuam presentes:
     - `M .python-version`
     - `M config/gui_main_preferences.json`
     - `M data/ssas.db`
     - `M gui/gui_ssa.py`
     - `M pyproject.toml`
     - `M requirements_build.txt`
     - `?? .backups/*`
     - `?? docs_entrada/*.xlsx`
     - `?? *.bak.*`
  3. esses residuos nao devem ser revertidos nem incluidos por inferencia.
- Commits funcionais recentes:
  1. `fd2d9b09`
     - full rescan Windows fecha conexoes SQLite antes de promover o DB candidato.
  2. `3ea0881b`
     - busca superior travada em teste no contrato simplificado atual.
  3. `2a1623bf`
     - upsert registra em log troca de `setor_executor` quando o dado mais novo vence.
- Diagnostico tecnico consolidado:
  1. repro real no banco local:
     - `danilo, svp, mel4, !STE` retorna `1` linha no runtime atual.
     - esse `1` vem de match literal de `svp` em `descricao_ssa`, nao de alias, sinonimo ou semantica especial de `S/P`.
  2. `config/filter_aliases.json` nao contem mais `svp -> S/P`.
  3. o schema local atual nao contem `responsavel_solicitante`.
  4. a logica de upsert ja aceitava troca de setor por linha mais nova; agora isso tambem fica registrado em log de arquivo sem afetar UI.
- Validacao consolidada:
  1. contrato simplificado atual da busca superior travado em `tests/test_app_logic_filter_contract.py`.
  2. full rescan com DB-only derivadas validado apos fechar handles SQLite.
  3. troca de `setor_executor` por linha mais nova validada e logada em `tests/test_upsert_behaviors.py`.
- Proximo passo sugerido:
  1. se o usuario quiser ajustar o comportamento de termos curtos na busca superior, tratar isso como decisao de produto com teste de contrato antes de qualquer patch.
  2. se o schema local precisar refletir o contrato novo completo da busca, abrir slice separado para migracao/compatibilidade de schema.
  3. manter separados os debts de comentario/docstring/config mortos que nao afetam runtime.

## HISTORICAL SNAPSHOT 2026-03-19 15:49 - previous current truth

- Objetivo desta rodada:
  1. remover legado morto de alias do `core` sem mudar a semantica da busca superior.
  2. corrigir o contrato textual entre busca geral e filtro de coluna.
  3. preparar commit limpo com stage separado do diff local preexistente em `pyproject.toml`.
- Estado confirmado:
  1. branch alvo: `dev`.
  2. residuos locais fora de escopo continuam presentes:
     - `M .python-version`
     - `M config/gui_main_preferences.json`
     - `M data/ssas.db`
     - `M requirements_build.txt`
     - `?? docs_entrada/*.xlsx`
     - `?? .backups/*`
     - `?? *.bak.*`
  3. `pyproject.toml` tem diff misto local; nao commitar por inferencia.
- Diagnostico tecnico final desta subrodada:
  1. a busca superior do `core` deve permanecer no contrato simplificado atual, sem reinterpretacao semantica.
  2. ainda existia superficie morta no `core` sugerindo alias de busca:
     - `get_filter_alias_map()`
     - `apply_filter_aliases()`
  3. o texto de ajuda ainda induzia leitura errada ao dizer que filtro de coluna e filtro geral tinham regras identicas.
- Mudancas entregues nesta subrodada:
  1. `core/app_logic.py`
     - removidas as funcoes mortas de alias.
     - docstring ajustada para refletir o contrato real.
  2. `tests/test_app_logic_filter_contract.py`
     - novo teste trava o contrato simplificado atual da busca superior.
  3. `tests/test_filter_alias_map_loading.py`
     - removido por ter virado teste de legado morto.
  4. `gui/widgets/filter_help_dialog.py`
     - ajuda separa busca geral de filtro por coluna.
  5. `gui/gui_ssa.py`
     - ajustes minimos para reduzir ruido de `ty` e alinhar fallback.
  6. `pyproject.toml`
     - alvo desta rodada e apenas remover as 4 chaves antigas de pytest do stage final.
  7. ambiente local
     - `pandas`, `openpyxl` e `PyQt6` confirmados
     - stubs e verificadores extras instalados na `.venv-win`
- Validacao desta subrodada:
  1. `py_compile` no escopo alterado -> pass.
  2. `ruff check` no escopo alterado -> pass.
  3. `ty check` no escopo alterado -> pass.
  4. `tests/test_app_logic_filter_contract.py + tests/test_search_v_character.py` -> `10 passed`.
  5. foco busca/ajuda -> `9 passed, 157 deselected`.
  6. `mypy`, `pylint`, `pylama`, `semgrep`, `qwen` e `kluster` rodados como segunda camada de revisao.
- Leitura de risco para o proximo ciclo:
  1. parser da busca superior esta mais limpo; o proximo hotspot real nao esta no `core`.
  2. debt estrutural antigo ainda aparece em:
     - `gui/gui_ssa.py`
     - `gui/mixins/filter_gui_ssa_mixin.py`
     - `gui/qt_stubs.py`
     - `utils/robust_logging.py`
     - `pyproject.toml` legado de tooling
  3. esses itens exigem slice separado; nao misturar com este commit.
- Proximo passo sugerido:
  1. commitar so o stage limpo desta rodada.
  2. empurrar para `origin/dev`.
  3. abrir proximo slice so depois para o backlog exposto por `mypy/pylama`.

## HISTORICAL SNAPSHOT 2026-03-19 08:18 - previous current truth

- Objetivo desta rodada:
  1. fechar o incidente grave de filtros GUI com patch minimo.
  2. deixar a cobertura forte o bastante para pegar a regressao em minutos.
  3. sincronizar handoff com a causa raiz real ja validada em codigo e testes.
- Estado confirmado:
  1. branch alvo: `dev`.
  2. residuos locais fora de escopo continuam presentes:
     - `M .python-version`
     - `M config/gui_main_preferences.json`
     - `M data/ssas.db`
     - `M pyproject.toml`
     - `M requirements_build.txt`
     - `?? docs_entrada/*.xlsx`
  3. esses residuos nao devem ser revertidos nem incluidos por inferencia.
- Diagnostico tecnico final:
  0. ownership errado do contrato:
     - a GUI dependia do default de `filter_dataframe(..., search_columns=None)`.
     - a lista de colunas da busca geral ficou escondida no core.
  1. busca geral:
     - `core/app_logic.py` tinha `priority_columns` incompleto.
     - faltavam `solicitante`, `responsavel_solicitante`, `responsavel_programacao` e `responsavel_execucao`.
  2. cache de filtro:
     - `gui/mixins/filter_gui_ssa_mixin.py` mandava ao worker apenas `advanced_filters`.
     - nao incluia `active_column_filters` nem `exclude_ste_sca`.
  3. estado invisivel:
     - `Ocultar` escondia a linha mantendo o filtro ativo.
     - isso tornava o estado restritivo invisivel e explicava parte do sintoma de `clear`.
- Historico de introducao:
  1. busca geral incompleta:
     - base em `0c87e431`
     - lista consolidada ainda incompleta em `e7ddea48`
  2. cache parcial:
     - introduzido em `ff266350`
  3. estado invisivel:
     - base de hidden lines em `4df69305`
     - fluxo consolidado em `776c5905`
- Mudancas entregues:
  1. `core/app_logic.py`
     - busca geral agora inclui campos humanos criticos.
  2. `gui/mixins/filter_gui_ssa_mixin.py`
     - `cache_context` deterministico com estado efetivo de filtros.
     - `Ocultar` bloqueado quando existe filtro ativo na linha.
     - `restore_last_filter_state` nao pode mais reidratar filtro ativo invisivel.
  3. testes:
     - `tests/test_app_logic_filter_contract.py`
     - `tests/test_filter_worker.py`
     - `tests/test_gui_filter_logic.py`
  4. observacao de rastreabilidade:
     - este handoff descreve mudancas de runtime ja aplicadas no mesmo working tree.
     - o presente DOC_SYNC nao e o patch funcional; ele apenas consolida o estado entregue.
  5. segunda varredura:
     - a suite ampliada encontrou tambem um desalinhamento do quick combo de `setor_executor`, ligado a mudanca estrutural de `c56d0e8e`.
     - `gui/gui_ssa.py` passou a centralizar a aplicacao segura de alturas no toolbar e no sync inferior.
     - esse ponto entrou no refinamento final antes de commit/push.
  6. estado atual da frente:
     - o contrato de colunas da busca geral da GUI deve ser lido em `docs/GUI_GENERAL_SEARCH_COLUMN_CONTRACT.md`.
     - o core ainda preserva `search_columns=None` como fallback generico.
     - fuzzy search continua deferido para release futuro.
- Validacao final:
  1. `py_compile` no escopo alterado -> pass.
  2. `ruff check` no escopo alterado -> pass.
  3. `ty check` no escopo alterado -> pass.
  4. `tests/test_app_logic_filter_contract.py` -> `7 passed`.
  5. foco GUI/worker -> `15 passed`.
  6. suite ampliada (`tests/test_app_logic_filter_contract.py`, `tests/test_filter_worker.py`, `tests/test_workers_advanced.py`, `tests/test_gui_filter_logic.py`) -> `204 passed, 1 skipped`.
  7. warnings residuais de pytest config continuam fora deste slice.
- Regra nova de cobertura:
  1. qualquer bug de filtros GUI reproduzivel em uso normal exige teste de jornada completa.
  2. cobertura minima obrigatoria:
     - busca superior
     - filtro de coluna
     - `exclude_ste_sca`
     - cache worker
     - `clear`
     - resumo
     - linha oculta
     - alinhamento funcional do quick toolbar quando a linha superior receber novos controles
- Proximo passo sugerido:
  1. revisar e commitar o patch em slices atomicos, se aprovado.
  2. nao abrir refatoracao ampla de GUI.
  3. se houver novo ciclo de docs, manter este bloco como fonte de verdade unica.

## HISTORICAL SNAPSHOT 2026-03-17 00:30 - previous current truth

- Objetivo desta rodada:
  1. fechar o diagnostico real de full vs diff na importacao.
  2. corrigir a semantica de status para rejeicoes deterministicas sem tocar no algoritmo de cache.
- Estado tecnico confirmado:
  1. `data/file_cache.json` existe e esta funcional neste host.
  2. medicao local: `431/431` arquivos atuais em `metadata_match_skip`; diff atual selecionaria `0`.
  3. GUI chama os modos corretos:
     - `rescan_diff_data -> force_import=False`
     - `rescan_full_data -> force_import=True`
- Bug real confirmado:
  1. `MISSING_REQUIRED_COLUMNS` entra em cache deterministico, mas fazia o core retornar `no_success` quando nao havia sucesso de arquivo.
  2. worker GUI convertia isso em:
     - `diff`: `sem alteracoes`
     - `full`: `falhou`
  3. ambos sao falsos para rejeicao esperada de arquivo fora do padrao.
- Estrategia minima deste slice:
  1. manter `utils/caching.py` sem alteracao.
  2. introduzir status dedicado `deterministic_rejections_only` no core.
  3. ajustar o worker GUI para concluir com sucesso informativo nesse caso.
  4. travar o comportamento em testes focados.

## HISTORICAL SNAPSHOT 2026-03-12 00:45 - previous current truth

- Objetivo desta rodada:
  1. fechar rastreabilidade documental completa do ciclo de build multi-plataforma.
  2. consolidar atendimento de pedidos e pendencias em um unico ponto de leitura.
- Registro aplicado:
  1. novo documento canonico de auditoria:
     - `docs/BUILD_EXECUTION_AUDIT_20260311.md`
  2. novo runbook operacional:
     - `docs/BUILD_3X3_RUNBOOK.md`
  3. `INDEX`, `BUILD_MULTIPLATFORM`, `BUILD_TOOLING_LESSONS_LEARNED` sincronizados para referencia cruzada.
  4. `NEXT_CHAT_MIGRATION` e `RECOVERY_BACKLOG` atualizados com a mesma verdade atual.
- Estado operacional para o proximo ciclo:
  1. branch: `dev`
  2. foco tecnico imediato:
     - fechar retorno final nao-zero do script `build_nuitka_debian.sh --silent`
     - executar smoke final cross-platform
- Evidencias novas desta rodada:
  1. `iscc` confirmado no host atual.
  2. instalador pyinstaller compilado com sucesso.
  3. `patchelf` instalado no WSL Debian 13.
  4. `build_nuitka_debian.sh` ajustado (CLI sem plugin PyQt6 + trap de erro com step/log).

## HISTORICAL SNAPSHOT 2026-03-12 00:05 - previous current truth

- Objetivo desta rodada:
  1. registrar handover para continuidade no host Windows com contexto seguro.
  2. preservar escopo: proximo slice focado em scripts/build do Windows.
- Registro aplicado:
  1. estado canonico para o novo host:
     - branch: `dev`
     - ultimo commit em `origin/dev`: `05bbc2e1`
  2. referencia de entrega ja concluida no host atual:
     - startup `.app` macOS estabilizado
     - icone azul no `.app/.dmg`
     - titulo com versao e menu `Sobre`
  3. docs de controle sincronizados para leitura no proximo chat.
- Guardrails para o proximo ciclo:
  1. iniciar com diagnostico objetivo e plano curto antes de editar.
  2. nao tocar runtime GUI/importacao sem aprovacao explicita.
  3. corrigir apenas blockers reais de scripts/build no Windows.
  4. manter commit atomico e rollback facil por slice.
- Estado local no fechamento desta maquina:
  1. residuos fora de escopo:
     - `M data/ssas.db`
     - `M docs/INDEX.md`
     - `?? config/settings.json.bak_20260308_212715`
  2. esses residuos podem nao existir no Windows; considerar apenas estado commitado em git.
- Proximo ciclo (entrada minima no Windows):
  1. `git pull` em `dev`.
  2. checklist de arranque (`status`, `branch`, `stash`, riscos/foco).
  3. seguir SDLC por slice: diagnostico -> plano -> patch minimo -> gates -> commit/push -> doc sync.

## HISTORICAL SNAPSHOT 2026-03-11 00:36 - previous current truth

- Objetivo da rodada anterior:
  1. estabilizar startup do `.app` macOS.
  2. garantir icone azul no `.app/.dmg`.
  3. incluir versao no titulo da janela e menu `Sobre`.
- Registro da rodada anterior:
  1. `launchers/gui_entry.py`:
     - runtime frozen em area gravavel.
     - `cwd` ajustado para runtime local.
  2. `gui/gui_ssa.py`:
     - titulo com versao.
     - `Ajuda -> Sobre` com app/python/uv/pyqt/qt/pandas.
  3. artefatos gerados:
     - `launchers/dist/macos_arm64/SSA_GUI_v4.32_macos_arm64.app`
     - `launchers/dist/macos_arm64/SSA_Consulta_Rapida_v4.32_macos_arm64.dmg`
- Validacao da rodada anterior:
  1. `py_compile`, `ruff`, `ty` no escopo alterado -> pass.
  2. `pytest` focado -> `9 passed`.
  3. launch check com `cwd=/` -> processo ativo.
  4. hash de icone do bundle igual ao `resources/app_icon.icns`.

## HISTORICAL SNAPSHOT 2026-03-10 22:52 - authoritative block

- Objetivo desta rodada:
  1. mitigar stale-lock no cache para evitar timeout recorrente apos crash de processo.
- Correcoes aplicadas:
  1. `utils/caching.py`
     - stale-lock recovery no acquire path com leitura de PID e check de processo vivo.
     - remocao controlada de lock stale por idade minima (PID morto) ou idade de seguranca (PID ausente).
  2. `tests/test_caching_atomic_save.py`
     - testes focados para lock stale recuperavel e lock ativo nao removivel.
     - ajuste de import `pytest`.
- Validacao:
  1. `uv run --python 3.13 python -m py_compile utils/caching.py tests/test_caching_atomic_save.py` -> pass.
  2. `uv run --python 3.13 ruff check utils/caching.py tests/test_caching_atomic_save.py` -> pass.
  3. `uv run --python 3.13 ty check utils/caching.py tests/test_caching_atomic_save.py` -> pass.
  4. `timeout 180s uv run --python 3.13 pytest -q tests/test_caching.py tests/test_caching_atomic_save.py` -> `17 passed`.
- Classificacao:
  1. `BUG_REAL` corrigido:
     - lock sidecar preso apos crash bloqueando persistencia de cache.
  2. `NAO_BLOQUEANTE_DEFERIDO`:
     - debts de performance ampla em hashing sequencial no `utils/caching.py`.
     - debt semantico antigo no teste de atomicidade.
- Decisao intencional registrada:
  1. nao reintroduzir `--not --remotes` no `scripts/git_hooks/pre-push`.
  2. prioridade: seguranca do gate de blob grande (evitar falso-negativo no destino remoto).

## HISTORICAL SNAPSHOT 2026-03-10 22:41 - authoritative block

- Objetivo desta rodada:
  1. fechar os 2 P2 novos do cubic em scripts de hook.
- Correcoes aplicadas:
  1. `scripts/install_hooks.sh`
     - validacao completa dos hooks obrigatorios no mesmo run.
     - agregacao de falhas por hook e retorno final unico.
     - sem mascaramento de erro real de copia/permissao.
  2. `scripts/git_hooks/pre-push`
     - removido `--not --remotes` para nao perder deteccao de blob grande novo no alvo.
     - tolerancia por range invalido preservada.
- Validacao:
  1. `bash -n scripts/install_hooks.sh scripts/git_hooks/pre-push` -> pass.
  2. kluster `install_hooks.sh` -> clean.
  3. kluster `pre-push` -> 3 MEDIUM (debt), sem blocker novo.
- Classificacao:
  1. `BUG_REAL` corrigido:
     - gate de tamanho que podia esconder blobs novos no destino.
     - instalador que podia interromper cedo sem reportar todos os hooks obrigatorios.
  2. `NAO_BLOQUEANTE_DEFERIDO`:
     - debt semantico/performance amplo no `pre-push`.

## HISTORICAL SNAPSHOT 2026-03-10 22:30 - authoritative block

- Objetivo desta rodada:
  1. mitigar risco real de concorrencia no cache (lost update) com patch minimo.
- Correcoes aplicadas:
  1. `utils/caching.py`
     - lock sidecar de escrita (`.lock`) com timeout e retry.
     - `save_cache` sob lock exclusivo.
     - merge de updates sob lock em `get_files_to_process` e `update_cache_for_files`.
  2. `tests/test_caching_atomic_save.py`
     - cobertura de lock file + merge concorrente.
     - ajuste semantico no teste de overwrite concorrente do `save_cache`.
- Validacao:
  1. `uv run --python 3.13 python -m py_compile utils/caching.py tests/test_caching_atomic_save.py` -> pass.
  2. `uv run --python 3.13 ruff check utils/caching.py tests/test_caching_atomic_save.py` -> pass.
  3. `uv run --python 3.13 ty check utils/caching.py tests/test_caching_atomic_save.py` -> pass.
  4. `timeout 180s uv run --python 3.13 pytest -q tests/test_caching.py tests/test_caching_atomic_save.py` -> `15 passed`.
- Classificacao:
  1. `BUG_REAL` corrigido:
     - risco de perda de update no cache em execucoes concorrentes.
  2. `NAO_BLOQUEANTE_DEFERIDO`:
     - debts MEDIUM remanescentes no kluster de `utils/caching.py` (naming/decomposicao/perf).
- Estado local fora de escopo mantido:
  1. `data/ssas.db` modificado local.
  2. `config/settings.json.bak_20260308_212715` arquivo local novo.

## HISTORICAL SNAPSHOT 2026-03-10 22:23 - authoritative block

- Objetivo desta rodada:
  1. fechar comentarios novos de bot em hooks/cache com patch minimo e verificavel.
- Correcoes aplicadas:
  1. `scripts/install_hooks.sh`
     - removido `|| true` das chamadas obrigatorias de `install_named_hook`.
  2. `scripts/git_hooks/pre-push`
     - ranges processados individualmente com tolerancia a range invalido.
     - `git rev-list` com `--not --remotes`.
     - formato de `git cat-file --batch-check` corrigido para TAB real.
  3. `utils/caching.py`
     - `except Exception` removido de `_cache_key_for_file`; fallback agora com excecoes especificas e `logger.debug`.
- Validacao executada:
  1. `uv run --python 3.13 python -m py_compile utils/caching.py` -> pass.
  2. `uv run --python 3.13 ruff check utils/caching.py` -> pass.
  3. `uv run --python 3.13 ty check utils/caching.py` -> pass.
  4. `timeout 180s uv run --python 3.13 pytest -q tests/test_caching.py tests/test_caching_atomic_save.py` -> `13 passed`.
  5. `bash -n scripts/install_hooks.sh scripts/git_hooks/pre-push` -> pass.
- Classificacao dos comentarios:
  1. `BUG_REAL` corrigido:
     - mascaramento de falha no `install_hooks.sh`.
     - risco de abortar push valido por range ruim no `pre-push`.
     - parse incorreto de saida do `cat-file` no `pre-push` por `%x09` literal.
     - `except Exception` amplo em `_cache_key_for_file`.
  2. `NAO_BLOQUEANTE_DEFERIDO`:
     - debts MEDIUM de naming/decomposicao/perf em `utils/caching.py`.
     - debt MEDIUM de semantica/performance no escopo amplo do `pre-push`.
- Estado local fora de escopo mantido:
  1. `data/ssas.db` (modificado localmente).
  2. `config/settings.json.bak_20260308_212715` (arquivo local novo).

## HISTORICAL SNAPSHOT 2026-03-10 22:03 - authoritative block

- Objetivo desta rodada:
  1. refresh total de contexto para migracao de conversa, sem alteracao de runtime.
- Estado local confirmado:
  1. branch ativa: `codex/sprint-importacao-grave-fixes-20260305`.
  2. ultimo commit: `30500374 STABILITY_PATCH: fechar rodada bot (hooks pre-push ascii worker)`.
  3. residuos fora de escopo:
     - `data/ssas.db` (modificado localmente)
     - `config/settings.json.bak_20260308_212715` (arquivo local novo)
  4. stashes abertos:
     - `stash@{0}` `wip-before-return-import-branch-20260308_011343`
     - `stash@{1}` `incident-freeze-before-reapply-20260305-083301`
     - `stash@{2}` `local-wip-config-db-before-dev-switch-20260303`
- Estado de PR e checks:
  1. PR `#45` aberto, `mergeStateStatus=UNSTABLE`.
  2. threads abertas: `0`.
  3. checks com falha: `CodeFactor`, `code/snyk`, `security/snyk`.
  4. checks pendentes: `cubic`, `semgrep-cloud-platform/scan`.
- Decisao desta rodada:
  1. nenhum arquivo de runtime foi alterado.
  2. somente docs de controle foram atualizados para handoff limpo.
- Proximo passo recomendado:
  1. revalidar checks pendentes.
  2. se limpos e sem novos comentarios bloqueantes, seguir merge.

## HISTORICAL SNAPSHOT 2026-03-10 21:42 - authoritative block

- Priority note (carry-over mandatory):
  1. debt BLE001 no restante do codigo deve ser tratado em breve, por modulo.
  2. contagem atual: `860`.
  3. comando base: `ruff check . --select BLE001`.
  4. hotspots iniciais: `armazenamento/database*.py`, `core/app_logic.py`, `core/config_manager.py`, `dev_env/streamlit_app.py`.
  5. status PR observado neste fechamento:
     - PR `#45` aberto.
     - `0` threads abertas.
     - checks externos bloqueando merge: `CodeFactor`, `code/snyk`, `security/snyk`.

- Slice entregue:
  1. fechamento da rodada adicional de comentarios bot com correcoes de risco real e patch minimo.
- Arquivos alterados:
  1. `scripts/install_hooks.sh`
  2. `scripts/git_hooks/pre-push`
  3. `tests/test_robust_importer.py`
  4. `README.md`
  5. `gui/workers/data_loader_worker.py`
  6. `docs/RECOVERY_BACKLOG.md`
  7. `docs/NEXT_CHAT_MIGRATION.md`
  8. `docs/AGENTS_HANDOFF_NEXT_CYCLE.md`
- Validacao:
  1. `uv run --python 3.13 python -m py_compile gui/workers/data_loader_worker.py tests/test_robust_importer.py` -> pass.
  2. `uv run --python 3.13 ruff check gui/workers/data_loader_worker.py tests/test_robust_importer.py` -> pass.
  3. `uv run --python 3.13 ty check gui/workers/data_loader_worker.py tests/test_robust_importer.py` -> pass.
  4. `uv run --python 3.13 pytest -q tests/test_robust_importer.py tests/test_data_loader_worker.py` -> `23 passed`.
  5. `bash -n scripts/install_hooks.sh scripts/git_hooks/pre-push` -> pass.
- Decisao aplicada:
  1. hook ausente em `install_hooks.sh` agora e erro obrigatorio com falha explicita.
  2. `pre-push` passou a preservar caminho de blob para diagnostico util em bloqueio de tamanho.
  3. `test_robust_importer.py` convertido para fonte ASCII sem perda semantica (escapes unicode).
  4. `DataLoaderWorker` captura `pd.errors.DatabaseError` no topo e mantem emissao de erro para GUI.
- Deferido:
  1. custo de varredura sincrona no pre-push (tradeoff intencional do hook de seguranca).
  2. debts antigos de semantica/performance em `DataLoaderWorker`, incluindo recalculo de `non_null_cols` por carregamento.
  3. contradicao textual historica no `README` fora deste fix pontual.
- Estado de residuos locais fora de escopo:
  1. `data/ssas.db` (mantido local, nao commitar).
  2. `config/settings.json.bak_20260308_212715` (backup local, nao commitar).

## HISTORICAL SNAPSHOT 2026-03-10 16:37 - authoritative block

- Slice entregue:
  1. remocao de `except Exception` amplos em `main.py` e `DataLoaderWorker`.
- Arquivos alterados:
  1. `main.py`
  2. `gui/workers/data_loader_worker.py`
  3. `docs/RECOVERY_BACKLOG.md`
  4. `docs/NEXT_CHAT_MIGRATION.md`
  5. `docs/AGENTS_HANDOFF_NEXT_CYCLE.md`
- Validacao:
  1. `ruff --select BLE001` no escopo alvo -> limpo.
  2. `py_compile`, `ruff`, `ty` no escopo alterado -> pass.
  3. `pytest -q tests/test_data_loader_worker.py tests/test_main_import_fallback.py tests/test_main_skip_import.py tests/test_main_gui_fallback.py` -> `17 passed`.
- Decisao aplicada:
  1. manter tratamento de erro por bloco funcional com tuple explicita de excecoes.
  2. evitar captura generica para reduzir mascaramento de falha real.
- Deferido:
  1. debts antigos em `main.py` e `data_loader_worker.py` de arquitetura/performance/semantica (fora deste slice).
- Estado de residuos locais fora de escopo:
  1. `data/ssas.db` (mantido local, nao commitar).
  2. `config/settings.json.bak_20260308_212715` (backup local, nao commitar).

## HISTORICAL SNAPSHOT 2026-03-10 15:53 - authoritative block

- Slice entregue:
  1. estabilizacao dos testes de `main` para evitar travamento em pytest por entrada interativa.
  2. ajuste final de layout/comportamento do quick filter `Setor Executor`.
- Arquivos alterados:
  1. `tests/test_main_import_fallback.py`
  2. `tests/test_main_skip_import.py`
  3. `gui/gui_ssa.py`
  4. `tests/test_gui_filter_logic.py`
  5. `docs/RECOVERY_BACKLOG.md`
  6. `docs/NEXT_CHAT_MIGRATION.md`
  7. `docs/AGENTS_HANDOFF_NEXT_CYCLE.md`
- Validacao:
  1. `py_compile`, `ruff`, `ty` no escopo alterado -> pass.
  2. `pytest -q tests/test_main_import_fallback.py tests/test_main_skip_import.py tests/test_gui_filter_logic.py` -> `152 passed, 1 skipped`.
- Decisoes aplicadas:
  1. `--force-rescan` e tratado como prioridade sobre `--skip-import` nos testes de `main`.
  2. quick filter `setor_executor` nao sincroniza mais `setor_emissor`.
  3. label `Setor Executor:` fica fora da combo; combo exibe apenas valor do setor.
  4. `Colunas Visiveis` fica imediatamente apos o paginator/`Linhas por Pagina`.
- Deferido:
  1. debts antigos de arquitetura/performance em `gui/gui_ssa.py` fora do escopo.
- Estado de residuos locais fora de escopo:
  1. `data/ssas.db` (mantido local, nao commitar).
  2. `config/settings.json.bak_20260308_212715` (backup local, nao commitar).

## HISTORICAL SNAPSHOT 2026-03-10 15:29 - authoritative block

- Slice entregue:
  1. realocacao de controles na aba Filtros:
     - `Salvar Filtro` na linha de `Pesquisa Geral`;
     - `Colunas Visiveis` + `Setor Executor` na linha de paginacao.
  2. remocao visual do botao superior `Atualizar Derivadas` (acao mantida no menu Database).
- Arquivos alterados:
  1. `gui/gui_ssa.py`
  2. `tests/test_gui_filter_logic.py`
  3. `docs/RECOVERY_BACKLOG.md`
  4. `docs/NEXT_CHAT_MIGRATION.md`
  5. `docs/AGENTS_HANDOFF_NEXT_CYCLE.md`
- Validacao:
  1. `py_compile`, `ruff`, `ty` no escopo alterado -> pass.
  2. `pytest` focado de GUI/filtros -> `5 passed`.
- Deferido:
  1. debts antigos de performance/arquitetura no `gui/gui_ssa.py` apontados por kluster, fora deste slice.
- Estado de residuos locais fora de escopo:
  1. `data/ssas.db` (mantido local, nao commitar).
  2. `config/settings.json.bak_20260308_212715` (backup local, nao commitar).

## HISTORICAL SNAPSHOT 2026-03-10 15:17 - authoritative block

- Slice entregue:
  1. hardening de bootstrap GUI em `main.py` para nao mascarar erro de importacao inesperado.
  2. cobertura de regressao com novo teste focado (`tests/test_main_gui_fallback.py`).
- Arquivos alterados:
  1. `main.py`
  2. `tests/test_main_gui_fallback.py`
  3. `docs/RECOVERY_BACKLOG.md`
  4. `docs/NEXT_CHAT_MIGRATION.md`
  5. `docs/AGENTS_HANDOFF_NEXT_CYCLE.md`
- Validacao:
  1. `py_compile`, `ruff`, `ty` no escopo alterado -> pass.
  2. `pytest -q tests/test_main_gui_fallback.py tests/test_main_skip_import.py::test_main_skip_import_does_not_call_importer` -> `3 passed`.
- Deferido:
  1. debts antigos de arquitetura em `main.py` (funcao extensa e blocos amplos fora do trecho GUI).
  2. testes legados de `main` que nao isolam importacao real.
- Estado de residuos locais fora de escopo:
  1. `data/ssas.db` (mantido local, nao commitar).
  2. `config/settings.json.bak_20260308_212715` (backup local, nao commitar).

## HISTORICAL SNAPSHOT 2026-03-10 14:54 - authoritative block

- Slice entregue:
  1. correcao de bug real em `gui/gui_ssa.py` no fluxo de importacao externa por fallback seguro de helper.
  2. correcao de bug real de seguranca em `scripts/create_distribution.py` para ignorar arquivos sensiveis em `build_dir/config`.
- Arquivos alterados:
  1. `gui/gui_ssa.py`
  2. `scripts/create_distribution.py`
  3. `tests/test_create_distribution.py`
  4. `docs/RECOVERY_BACKLOG.md`
  5. `docs/NEXT_CHAT_MIGRATION.md`
  6. `docs/AGENTS_HANDOFF_NEXT_CYCLE.md`
- Validacao:
  1. `py_compile`, `ruff`, `ty` no escopo alterado -> pass.
  2. `pytest -q tests/test_gui_menu_import_external.py` -> `13 passed`.
  3. `pytest -q tests/test_create_distribution.py` -> `18 passed`.
- Deferido:
  1. debts antigos de arquitetura/performance em `gui/gui_ssa.py` (fora do escopo deste slice de bug real).
- Estado de residuos locais fora de escopo:
  1. `data/ssas.db` (mantido local, nao commitar).
  2. `config/settings.json.bak_20260308_212715` (backup local, nao commitar).

## HISTORICAL SNAPSHOT 2026-03-10 14:44 - authoritative block

- Slice entregue:
  1. fix de bug real no mapeamento semantico de `SN/SN.1` no robust importer.
  2. ajuste de semantica de finalizacao no `RescanWorker` para full-rescan com `success=False`.
- Arquivos alterados:
  1. `utils/robust_importer.py`
  2. `gui/workers/rescan_worker.py`
  3. `tests/test_rescan_worker_advanced.py`
  4. `docs/RECOVERY_BACKLOG.md`
  5. `docs/NEXT_CHAT_MIGRATION.md`
  6. `docs/AGENTS_HANDOFF_NEXT_CYCLE.md`
- Validacao:
  1. `py_compile`, `ruff`, `ty` no escopo alterado -> pass.
  2. `pytest -q tests/test_robust_importer.py tests/test_rescan_worker_advanced.py tests/test_rescan_worker_cleanup.py` -> `41 passed`.
- Regra final aplicada no worker:
  1. `force_import=False` e `success=False` permanece sucesso sem alteracoes (decisao intencional de UX para diff).
  2. `force_import=True` e `success=False`:
     - se houve erro observado ou `total_files>0` -> `finished_error`;
     - se nao houve contexto de arquivos (`total=0`) -> sucesso sem alteracoes.
- Estado de residuos locais fora de escopo:
  1. `data/ssas.db` (mantido local, nao commitar).
  2. `config/settings.json.bak_20260308_212715` (backup local, nao commitar).

## HISTORICAL SNAPSHOT 2026-03-10 14:31 - authoritative block

- Slice entregue:
  1. fechamento seguro do refactor minimo em `core/app_logic.py` (orquestracao de importacao).
  2. fix de runtime por import faltante de `cast`.
  3. fix de regressao em full-rescan para materializacao do DB candidato antes da promocao.
- Arquivos alterados:
  1. `core/app_logic.py`
  2. `docs/RECOVERY_BACKLOG.md`
  3. `docs/NEXT_CHAT_MIGRATION.md`
  4. `docs/AGENTS_HANDOFF_NEXT_CYCLE.md`
- Validacao:
  1. `py_compile`, `ruff`, `ty` em `core/app_logic.py` -> pass.
  2. `pytest -q tests/test_import_derivadas_trigger.py` -> `13 passed`.
  3. `pytest -q tests/test_app_logic_full_rescan_lock.py tests/test_import_derivadas_trigger.py tests/test_import_run_report.py tests/test_app_logic_postprocess_moves.py tests/test_import_cache_integrity.py` -> `27 passed`.
- Deferido:
  1. debts antigos em `filter_dataframe` (performance/semantica) e debt de rotacao/checkpoint sincrono.
- Estado de residuos locais fora de escopo:
  1. `data/ssas.db` (mantido local, nao commitar).
  2. `config/settings.json.bak_20260308_212715` (backup local, nao commitar).

## HISTORICAL SNAPSHOT 2026-03-10 13:58 - authoritative block

- Slice entregue:
  1. ajuste do combo rapido `setor_executor` na barra superior:
     - popup com valores curtos (sem prefixo por item).
     - exibicao fechada com prefixo (`Setor Executor: <valor>`).
     - largura controlada para nao ocupar espaco excessivo.
  2. fix do icone em startup GUI:
     - `main.py --gui` aplica icone no `QApplication`.
     - `SSAMainWindow` tambem aplica no `QApplication` ativo.
- Arquivos alterados:
  1. `gui/gui_ssa.py`
  2. `main.py`
  3. `tests/test_gui_filter_logic.py`
- Validacao:
  1. `py_compile`, `ruff`, `ty` no escopo -> pass.
  2. `pytest` focado do combo rapido -> pass.
  3. smoke offscreen:
     - `window_icon_null=False`
     - `app_icon_null=False`
- Deferido:
  1. debts antigos de arquitetura/performance em `gui/gui_ssa.py` apontados por kluster (fora do escopo).
- Estado de residuos locais fora de escopo:
  1. `data/ssas.db` (mantido local, nao commitar).
  2. `config/settings.json.bak_20260308_212715` (backup local, nao commitar).

## HISTORICAL SNAPSHOT 2026-03-10 13:45 - authoritative block

- Slice entregue:
  1. desbloqueio do check `CodeFactor` no PR #45 sem mudanca de runtime.
- Mudanca aplicada:
  1. adicao dos arquivos `.codefactor` e `.codefactor.yml` no root.
  2. exclusao explicita de arquivos legados com complexidade estrutural historica apontada pelo check.
- Resultado operacional esperado:
  1. `CodeFactor` deixa de bloquear por debt legado fora do escopo funcional desta sprint.
  2. runtime/import/gui/db permanecem sem alteracao neste slice.
- Validacao:
  1. `kluster` no `.codefactor` e nos docs de controle -> clean.
- Deferido:
  1. refatoracao real de complexidade desses modulos segue para sprint dedicado.

## HISTORICAL SNAPSHOT 2026-03-10 13:32 - authoritative block

- Slice entregue:
  1. correcao tecnica das 9 threads `BUG_REAL` remanescentes no PR #45.
  2. foco em atomicidade de upsert, validacao/extracao observavel e consistencia de workers.
- Resultado tecnico principal:
  1. upsert sem `to_sql` no hot-path (evita commit implicito de pandas).
  2. `BEGIN` robusto por estado real de transacao (`in_transaction`) e rollback explicito em falha.
  3. bootstrap com conexao externa passou a usar `initialize_database(conn, ...)`.
  4. carga de cache existente por sublotes (`IN` limitado) para evitar `too many SQL variables`.
  5. erro de validacao com `error_details` estruturado.
  6. erro de extracao `MISSING_REQUIRED_COLUMNS` com `available_columns` e `debug_phases`.
  7. full rescan sem alteracoes agora conclui sucesso (nao erro).
  8. classificador TTL sem side-effect local; sync da lista global no wrapper locked.
- Validacao:
  1. `py_compile`, `ruff`, `ty` no escopo alterado -> pass.
  2. `pytest` focado -> `252 passed, 1 skipped`.

## HISTORICAL SNAPSHOT 2026-03-10 12:56 - authoritative block

- Slice entregue:
  1. triagem final de pendencias do PR #45, com revisao thread a thread.
  2. limpeza de ruido de bot (`Rate Limit Exceeded`) e fechamento de threads ja classificadas.
  3. preservacao somente de bloqueios `BUG_REAL` para proximos slices tecnicos.
- Resultado operacional no PR:
  1. `open_threads` antes: `65`
  2. `open_threads` apos triagem: `9`
  3. `56` threads encerradas nesta rodada.
- Threads abertas remanescentes (`BUG_REAL`):
  1. `armazenamento/database_upsert_logic.py:407`
  2. `armazenamento/database_upsert_logic.py:951`
  3. `armazenamento/database_upsert_logic.py:743`
  4. `armazenamento/database_validation.py:61`
  5. `armazenamento/database_validation.py` (thread sem linha fixa)
  6. `extracao/extractor.py:536`
  7. `gui/ssa/gui_theme.py:458`
  8. `gui/ssa/gui_workers.py:239`
  9. `gui/workers/rescan_worker.py:169`
- Risco ativo:
  1. gargalo de fechamento do PR ficou concentrado em 9 bugs reais; restante foi saneado.
  2. checks externos ainda podem bloquear merge por cota/conta (`snyk`) e jobs pendentes de terceiros.

## HISTORICAL SNAPSHOT 2026-03-10 12:45 - authoritative block

- Slice entregue:
  1. fechamento de pendencias reais do PR #45 no escopo build/hook/docs (sem alterar GUI/layout).
  2. validacao staged-size do hook pre-commit corrigida para blob do index.
  3. fluxo macOS `cli-only` com `package=dmg` agora nao falha por falta de `.app`.
  4. docs de transicao normalizados para manter um unico `CURRENT TRUTH`.
- Mudancas tecnicas principais:
  1. `scripts/git_hooks/pre-commit`:
     - troca de `wc -c` no working tree por `git cat-file -s :<path>` no staged.
  2. `launchers/build_multiplatform.py`:
     - `post_process(..., apps=None)` com regra `apps=["cli"]` -> skip DMG controlado.
     - `build_platform(...)` passa `apps` para `post_process`.
  3. `tests/test_build_multiplatform_manifest.py`:
     - novo teste `test_post_process_macos_dmg_cli_only_skips_when_gui_not_requested`.
  4. docs:
     - `docs/NEXT_CHAT_MIGRATION.md` e `docs/AGENTS_HANDOFF_NEXT_CYCLE.md` com um unico bloco ativo `CURRENT TRUTH`.
- Evidencia de validacao:
  1. `py_compile`, `ruff`, `ty` no escopo -> pass.
  2. `pytest` focado -> `22 passed`.
  3. `bash -n scripts/git_hooks/pre-commit` -> pass.
- Pendencias deferidas:
  1. debts antigos do `build_multiplatform.py` (naming/performance/SRP) seguem para slice dedicado.
  2. alerta kluster de `pip_exe` classificado como falso positivo apos leitura do fluxo.
- Residuos locais fora de escopo (nao commitar):
  1. `data/ssas.db`
  2. `config/settings.json.bak_20260308_212715`

## HISTORICAL SNAPSHOT 2026-03-10 12:13 - authoritative block

- Slice entregue:
  1. icone oficial atualizado para versao azul `SSA` sem raio.
  2. pacote de icones oficiais cross-OS regenerado (`svg/png/ico/icns`).
- Mudancas tecnicas principais:
  1. `resources/app_icon.svg` substituido pela nova base visual.
  2. `resources/app_icon.png` regenerado em alta resolucao (1024x1024).
  3. `resources/app_icon.ico` regenerado com multiplos tamanhos para Windows.
  4. `resources/app_icon.icns` regenerado com `iconutil` para macOS.
- Evidencia de validacao:
  1. `file` confirmou formato valido dos 4 artefatos.
  2. `py_compile`, `ruff`, `ty` em scripts de build/icon -> pass.
  3. `pytest` focado de build manifest -> `4 passed`.
- Pendencias deferidas:
  1. `launchers/convert_icon.py` ainda depende de `cairosvg` com binding nativo `cairo`; fallback automatico no script fica para ciclo de tooling.
  2. `resources/icon_variants/*` mantido como banco de opcoes de design.
- Residuos locais fora de escopo (nao commitar):
  1. `data/ssas.db`
  2. `config/settings.json.bak_20260308_212715`

## HISTORICAL SNAPSHOT 2026-03-10 12:02 - authoritative block

- Slice entregue:
  1. build macOS passou a gerar instalador `.dmg` no fluxo oficial `build_multiplatform`.
  2. executavel direto (`.app` + onedir) mantido no mesmo run.
- Mudancas tecnicas principais:
  1. `launchers/build_multiplatform.py`:
     - `post_process` com `package_mode` e branch dedicado para DMG em `macos_arm64`.
     - helper `_find_macos_gui_app` para localizar `.app`.
     - helper `_create_macos_dmg` usando `hdiutil`.
     - helper `_get_macos_dmg_name` para naming canonico.
     - `build_platform` agora retorna falha se `post_process` falhar.
  2. `launchers/platforms/macos_arm64/build_config.json`:
     - `post_build.package: "dmg"`.
  3. `tests/test_build_multiplatform_manifest.py`:
     - cobertura para geracao DMG e falha controlada sem `.app`.
- Evidencia de validacao:
  1. `py_compile`, `ruff`, `ty` -> pass.
  2. `pytest` focado -> `4 passed`.
  3. build real macOS (`cli+gui`) -> pass com DMG gerado.
- Pendencias deferidas:
  1. trilha pyoxidizer/nuitka segue experimental.
  2. codesign/notarizacao macOS fora do escopo deste slice.
- Residuos locais fora de escopo (nao commitar):
  1. `data/ssas.db`
  2. `config/settings.json.bak_20260308_212715`

## HISTORICAL SNAPSHOT 2026-03-10 11:51 - authoritative block

- Slice entregue:
  1. eliminados os `try/except` proibidos que ainda restavam no escopo pedido.
  2. nenhum ajuste de layout/posicionamento GUI.
- Mudancas tecnicas principais:
  1. `gui/gui_ssa.py`:
     - `except ... pass` removido no restore de signals do combo rapido.
     - leitura de `import_run_*.json` com excecoes especificas e log debug, sem `continue` dentro de `except`.
  2. `gui/workers/data_loader_worker.py`:
     - fallback por coluna para non-null sem `except ... continue`, com log debug.
- Evidencia de validacao:
  1. `py_compile`, `ruff`, `ty` no escopo alterado -> pass.
  2. `pytest` focado (`test_data_loader_worker.py` + `test_gui_filter_logic.py` com filtro) -> `2 passed, 157 deselected`.
  3. `bandit` focado em GUI/worker -> `B110/B112` nao aparecem mais.
- Risco/pendencia:
  1. alertas kluster de arquitetura/performance em `gui_ssa.py` permanecem como debt antigo.
  2. alerta kluster de assinatura `query_db` no worker foi classificado como falso positivo apos checagem da assinatura real.
- Residuos locais fora de escopo (nao commitar):
  1. `data/ssas.db`
  2. `config/settings.json.bak_20260308_212715`

## HISTORICAL SNAPSHOT 2026-03-10 11:26 - authoritative block

- Slice entregue:
  1. build macOS deixou de gerar binario inutil por exclusao agressiva de stdlib.
  2. hooks de tamanho ativados no fluxo real (commit/push) com limite de 95MB.
  3. quick filter de `setor_executor` sincroniza com UI de filtros avancados e mostra rotulo explicito.
  4. commit evidencia: `338614c6`.
- Mudancas tecnicas principais:
  1. `build_config.json` de `macos_arm64`, `windows_amd64`, `debian_amd64`:
     - `exclude_modules` reduzido para `tkinter/test/unittest`.
     - remove exclusoes de stdlib que quebravam runtime (`concurrent`, `email`, `html`, etc).
  2. `launchers/build_multiplatform.py`:
     - `--add-data` com separador correto por plataforma.
     - manifesto com artefatos reais (file/dir), sem hidden de sistema.
     - calculo de tamanho de diretorio com guarda de erro.
     - texto de help `--all` alinhado ao comportamento atual.
  3. hooks:
     - `scripts/git_hooks/pre-commit` com bloqueio de staged >= 95MB.
     - `scripts/git_hooks/pre-push` novo para bloquear blobs >= 95MB.
     - `scripts/install_hooks.sh` instala hooks por nome e corrige `core.hooksPath`.
  4. GUI:
     - `gui/gui_ssa.py` e `gui/ssa/gui_filters_advanced_ui.py`:
       - itens do combo rapido: `Setor Executor: <valor>`.
       - sincronismo do quick filter para UI de `Executor` no painel avancado (sem persistencia em `_advanced_filters`).
       - `import_external_excel_files` simplificado para helper de instancia no destino unico.
  5. testes:
     - novo `tests/test_build_multiplatform_manifest.py`.
     - ajuste em `tests/test_gui_filter_logic.py` para validar prefixo e sync.
  6. robustez adicional:
     - `_compute_directory_size_bytes` ignora symlink para evitar loop em arvore ciclica.
- Evidencia de validacao:
  1. `py_compile`, `ruff`, `ty` no escopo alterado -> pass.
  2. `pytest` focado -> `2 passed`.
  3. build real `macos_arm64` (CLI+GUI) -> success.
  4. smoke runtime apos rebuild:
     - erros `No module named 'concurrent'`, `html`, `email` nao reapareceram.
- Pendencias deferidas:
  1. debts antigos de arquitetura/performance apontados por kluster em `launchers/build_multiplatform.py` e `gui/gui_ssa.py`.
  2. possivel ciclo dedicado para separar manutencao git de `build_multiplatform`.
- Residuos locais fora de escopo (nao commitar):
  1. `data/ssas.db`
  2. `config/settings.json.bak_20260308_212715`

## HISTORICAL SNAPSHOT 2026-03-10 10:38 - authoritative block

- Slice entregue:
  1. pente fino completo de scripts/docs para `pyinstaller`, `nuitka`, `pyoxidizer`, `pytoexe`.
  2. check de ferramentas e tentativa real de pacote por backend concluida.
  3. correcoes no empacotador para detectar executavel primario em bundle macOS e unificar metadados de Inno source.
- Resultado operacional:
  1. `pyinstaller --skip-installer` -> ZIP gerado com sucesso.
  2. `pyinstaller` -> ZIP gerado; installer falhou por falta de origem Windows/Inno neste host.
  3. `nuitka`/`pyoxidizer` -> sem pacote por ausencia de build local.
  4. `pytoexe` -> nao suportado (choice invalida).
- Ferramentas no host:
  1. `pyinstaller 6.19.0`, `nuitka 4.0.1`, `pyoxidizer 0.24.0`.
  2. `iscc`, `pytoexe`, `py2exe` ausentes.
- Evidencia:
  1. `/tmp/ssa_pack_audit_20260310_1030/summary.log`
  2. `dist_packages/SSA_Consulta_Rapida_v4.32_pyinstaller.zip`
- Gates desta rodada:
  1. kluster clean em script/tests/docs tocados.
  2. `py_compile`, `ruff`, `ty` -> pass.
  3. `pytest -q tests/test_create_distribution.py` -> `17 passed`.
- Pendencia deferida:
  1. rodada dedicada em Windows com ISCC + build `windows_amd64` para validar instalador ponta a ponta.
- Residuos locais fora de escopo (nao commitar):
  1. `data/ssas.db`
  2. `config/settings.json.bak_20260308_212715`

## HISTORICAL SNAPSHOT 2026-03-10 10:15 - authoritative block

- Slice entregue:
  1. resolvidos os 3 apontamentos recorrentes do loop:
     - risco semantico de path `Source` no ISS;
     - sincronia de diagnostico `resolve` vs `failure_reason`;
     - concentracao em `create_zip_package`.
  2. `scripts/create_distribution.py`:
     - `_resolve_inno_source` passou a seguir `exe_path` do config para pyoxidizer/nuitka.
     - `create_inno_setup_script` foi quebrado em helpers de path/excludes/template.
     - `Source` no ISS usa macro explicita `SourceDir`.
  3. `tests/test_create_distribution.py`:
     - novo teste de `exe_path` para pyoxidizer.
     - asserts ajustados para novo contrato do ISS.
- Gates desta rodada:
  1. kluster script -> clean.
  2. kluster tests -> clean.
  3. `py_compile`, `ruff`, `ty` -> pass.
  4. `pytest -q tests/test_create_distribution.py` -> `16 passed`.
- Pendencia deferida:
  1. rodada final em Windows/ISCC real para confirmacao de ambiente.
- Residuos locais fora de escopo (nao commitar):
  1. `data/ssas.db`
  2. `config/settings.json.bak_20260308_212715`

## HISTORICAL SNAPSHOT 2026-03-10 10:08 - authoritative block

- Slice entregue:
  1. testes de regressao novos para garantir diagnostico correto de falha em pyinstaller.
  2. cenarios cobertos:
     - `canonical` com conteudo mas sem executavel -> reason canonico.
     - `legacy` com conteudo mas sem executavel -> reason de executavel ausente no legacy.
  3. runtime nao alterado neste micro-slice.
- Gates desta rodada:
  1. kluster em `tests/test_create_distribution.py` -> clean.
  2. `py_compile`, `ruff`, `ty` -> pass.
  3. `pytest -q tests/test_create_distribution.py` -> `15 passed`.
- Pendencia deferida:
  1. validar em Windows/ISCC real o cenario de `Source` no `.iss`.
  2. continuar reducao de concentracao em `create_zip_package` e `create_inno_setup_script`.
- Residuos locais fora de escopo (nao commitar):
  1. `data/ssas.db`
  2. `config/settings.json.bak_20260308_212715`

## HISTORICAL SNAPSHOT 2026-03-10 10:05 - authoritative block

- Slice entregue:
  1. modularizacao minima em `create_zip_package` com helpers dedicados.
  2. fix de tipagem para `build_name` em metadata de versao.
  3. define explicito `SourcePath` no template Inno para evitar macro indefinida.
  4. testes de distribuicao atualizados para validar define `SourcePath`.
- Gates desta rodada:
  1. kluster em `scripts/create_distribution.py` -> 3 apontamentos (1 HIGH sem repro local + 2 MEDIUM antigos/debt).
  2. kluster em `tests/test_create_distribution.py` -> clean.
  3. `py_compile`, `ruff`, `ty` -> pass.
  4. `pytest -q tests/test_create_distribution.py` -> `13 passed`.
- Pendencia deferida:
  1. validar em Windows/ISCC real o cenario de path absoluto/relativo em `Source`.
  2. alinhar mensagem de falha entre `_resolve_build_directory` e helper de reason.
  3. continuar fatiamento de `create_zip_package` em ciclo dedicado.
- Residuos locais fora de escopo (nao commitar):
  1. `data/ssas.db`
  2. `config/settings.json.bak_20260308_212715`

## HISTORICAL SNAPSHOT 2026-03-10 09:59 - authoritative block

- Slice entregue:
  1. extracao minima em `compile_installer` sem mudanca de comportamento.
  2. `scripts/create_distribution.py`:
     - `_get_iscc_path()` isola descoberta/validacao de compilador.
     - `_run_iscc_compile(...)` isola execucao e tratamento de retorno.
     - `compile_installer(...)` ficou como orquestrador simples.
- Gates desta rodada:
  1. kluster em `scripts/create_distribution.py` -> 1 apontamento medio (debt antigo em `create_zip_package`, fora de escopo).
  2. `py_compile`, `ruff`, `ty` -> pass.
  3. `pytest -q tests/test_create_distribution.py` -> `13 passed`.
- Pendencia deferida:
  1. `create_zip_package` continua com debt de funcao longa (ciclo dedicado).
- Residuos locais fora de escopo (nao commitar):
  1. `data/ssas.db`
  2. `config/settings.json.bak_20260308_212715`

## HISTORICAL SNAPSHOT 2026-03-10 09:55 - authoritative block

- Slice entregue:
  1. `SourcePathMode` explicito no template Inno para sinalizar origem relativa vs absoluta.
  2. `scripts/create_distribution.py`:
     - `source_path_mode="relative"` por padrao.
     - fallback de `relpath` muda para `source_path_mode="absolute"`.
     - novo define no `.iss`: `#define SourcePathMode "..."`
  3. `tests/test_create_distribution.py`:
     - cobertura dos dois modos (`relative` e `absolute`) validada em asserts.
- Gates desta rodada:
  1. kluster em `scripts/create_distribution.py` -> 3 apontamentos (1 semantico intencional + 2 debts de qualidade fora do escopo).
  2. kluster em `tests/test_create_distribution.py` -> clean.
  3. `py_compile`, `ruff`, `ty` -> pass.
  4. `pytest -q tests/test_create_distribution.py` -> `13 passed`.
- Pendencia deferida:
  1. manter `OutputDir={#SourcePath}` como decisao intencional deste ciclo.
  2. `create_zip_package` e `compile_installer` continuam como debts de funcao longa para ciclo dedicado.
- Residuos locais fora de escopo (nao commitar):
  1. `data/ssas.db`
  2. `config/settings.json.bak_20260308_212715`

## HISTORICAL SNAPSHOT 2026-03-10 09:33 - authoritative block

- Slice entregue:
  1. hardening de seguranca no override `INNO_SETUP_COMPILER`.
  2. `scripts/create_distribution.py`:
     - validacao estrita de override (absoluto + nome permitido + arquivo existente + parent confiavel).
     - allowlist inclui Program Files Inno Setup e parent do `which iscc`.
     - override invalido nao quebra fluxo; segue fallback de descoberta normal.
  3. `tests/test_create_distribution.py`:
     - teste de rejeicao para override relativo.
     - teste de aceite para override absoluto em parent confiavel.
- Gates desta rodada:
  1. `py_compile`, `ruff`, `ty` -> pass.
  2. `pytest -q tests/test_create_distribution.py` -> `13 passed`.
  3. `kluster review` em codigo/docs tocados -> sem blocker funcional neste slice.
- Pendencia deferida:
  1. `create_zip_package` continua como debt de funcao longa.
  2. semantica geral de resolucao por build system continua para ciclo dedicado.
  3. validacao de Source do Inno em Windows real segue para rodada dedicada.
  4. kluster final apontou HIGH em `Source` relativo; sem repro local, confirmar em runner Windows com ISCC real.
- Residuos locais fora de escopo (nao commitar):
  1. `data/ssas.db`
  2. `config/settings.json.bak_20260308_212715`

## HISTORICAL SNAPSHOT 2026-03-10 09:28

- Slice entregue:
  1. `Source` do Inno Setup agora usa relpath real entre `DIST_OUTPUT` e origem do build.
  2. `scripts/create_distribution.py`:
     - `source_dir_spec` com `os.path.relpath(...)`.
     - fallback absoluto (`source_dir.resolve()`) quando relpath falha.
     - path normalizado para Windows.
  3. `tests/test_create_distribution.py`:
     - teste de `Source` relativo esperado.
     - teste de fallback absoluto quando `relpath` falha.
- Gates desta rodada:
  1. `py_compile`, `ruff`, `ty` -> pass.
  2. `pytest -q tests/test_create_distribution.py` -> `11 passed`.
  3. `kluster review` em codigo/docs tocados -> sem blocker funcional neste slice.
- Pendencia deferida:
  1. `create_zip_package` continua como debt de funcao longa.
  2. semantica geral de resolucao por build system continua para ciclo dedicado.
  3. deduplicacao de setup dos testes fica para manutencao futura.
- Residuos locais fora de escopo (nao commitar):
  1. `data/ssas.db`
  2. `config/settings.json.bak_20260308_212715`

## HISTORICAL SNAPSHOT 2026-03-10 09:23

- Slice entregue:
  1. `OutputDir` do instalador Inno agora e deterministico via `{{#SourcePath}}`.
  2. `scripts/create_distribution.py`:
     - template `.iss` atualizado para reduzir ambiguidade de cwd.
  3. `tests/test_create_distribution.py`:
     - teste novo validando `OutputDir={#SourcePath}`.
- Gates desta rodada:
  1. `py_compile`, `ruff`, `ty` -> pass.
  2. `pytest -q tests/test_create_distribution.py` -> `10 passed`.
  3. `kluster review` em codigo/docs tocados -> sem blocker funcional neste slice.
- Pendencia deferida:
  1. `create_zip_package` continua como debt de funcao longa.
  2. semantica geral de resolucao por build system fica para ciclo dedicado.
  3. deduplicacao de setup dos testes fica para manutencao futura.
- Residuos locais fora de escopo (nao commitar):
  1. `data/ssas.db`
  2. `config/settings.json.bak_20260308_212715`

## HISTORICAL SNAPSHOT 2026-03-10 09:18

- Slice entregue:
  1. fallback pyinstaller canonical->legacy ficou explicito no fluxo de resolucao.
  2. `scripts/create_distribution.py`:
     - `_resolve_build_directory` reorganizado sem mudanca funcional fora do escopo.
  3. `tests/test_create_distribution.py`:
     - teste novo cobrindo fallback para `base_dir` legacy quando canonical e invalido.
- Gates desta rodada:
  1. `py_compile`, `ruff`, `ty` -> pass.
  2. `pytest -q tests/test_create_distribution.py` -> `9 passed`.
  3. `kluster review` em codigo/tests -> sem blocker funcional neste slice.
- Pendencia deferida:
  1. `create_zip_package` segue como debt de funcao longa.
  2. semantica geral de resolucao por build system segue para ciclo dedicado.
- Residuos locais fora de escopo (nao commitar):
  1. `data/ssas.db`
  2. `config/settings.json.bak_20260308_212715`

## HISTORICAL SNAPSHOT 2026-03-10 09:11

- Slice entregue:
  1. erro de empacotamento agora informa causa detalhada na resolucao de build.
  2. `scripts/create_distribution.py`:
     - adicionado `_resolve_build_directory_failure_reason(...)`.
     - `create_zip_package` registra motivo especifico de falha (diretorio ausente, sem conteudo, executavel ausente).
  3. `tests/test_create_distribution.py`:
     - assertions atualizados para mensagens especificas.
     - novo teste para diretorio de build ausente.
- Gates desta rodada:
  1. `py_compile`, `ruff`, `ty` -> pass.
  2. `pytest -q tests/test_create_distribution.py` -> `8 passed`.
  3. `kluster review` em codigo/docs tocados -> sem blocker funcional.
- Pendencia deferida:
  1. `create_zip_package` segue como debt de funcao longa.
  2. separacao semantica mais profunda em `_resolve_build_directory` fica para slice dedicado.
  3. deduplicacao de setup dos testes de distribuicao fica para ciclo de manutencao.
- Residuos locais fora de escopo (nao commitar):
  1. `data/ssas.db`
  2. `config/settings.json.bak_20260308_212715`

## HISTORICAL SNAPSHOT 2026-03-10 08:49

- Slice entregue:
  1. fallback generico `executavel_principal` foi removido do empacotador.
  2. `scripts/create_distribution.py`:
     - `_detect_primary_executable_name` agora retorna `Optional[str]`.
     - `create_zip_package` aborta com erro explicito quando nao encontra executavel no staged package.
     - `_build_bundle_ignore` agora usa tipo real de entrada para aplicar filtro.
  3. `tests/test_create_distribution.py`:
     - teste novo para retorno `None` quando pacote nao possui binario.
- Gates desta rodada:
  1. `py_compile`, `ruff`, `ty` -> pass.
  2. `pytest -q tests/test_create_distribution.py` -> `7 passed`.
  3. `kluster review` no codigo tocado -> sem blocker novo; ficaram 2 debts medios de arquitetura/semantica.
- Pendencia deferida:
  1. `create_zip_package` ainda e funcao longa (qualidade).
  2. separacao semantica em `_resolve_build_directory` (resolver dir vs validar executavel) fica para slice dedicado.
  3. hardening de trust para `INNO_SETUP_COMPILER` (allowlist de diretorios) fica para ciclo de seguranca dedicado.
  4. validacao de path absoluto Inno e heuristica pyinstaller precisam rodada em ambiente Windows dedicado.
- Residuos locais fora de escopo (nao commitar):
  1. `data/ssas.db`
  2. `config/settings.json.bak_20260308_212715`

## HISTORICAL SNAPSHOT 2026-03-10 08:43

- Slice entregue:
  1. escolha de build pyinstaller ficou deterministica pela ordem de `canonical_dirs`.
  2. `scripts/create_distribution.py`:
     - `_resolve_build_directory` para pyinstaller retorna o primeiro candidato valido em ordem.
     - removida dependencia de `mtime` para decidir diretorio canonico.
     - filtro de exclusao consolidado em `_should_skip_bundle_entry` para top-level e nested.
  3. `tests/test_create_distribution.py`:
     - novo teste cobrindo prioridade por ordem vs `mtime`.
- Gates desta rodada:
  1. `py_compile`, `ruff`, `ty` -> pass.
  2. `pytest -q tests/test_create_distribution.py` -> `6 passed`.
  3. `kluster review` dos arquivos tocados -> sem blocker novo.
- Pendencia deferida:
  1. `create_zip_package` ainda e funcao longa (debt de qualidade).
  2. debt conhecido de path Inno cross-drive segue para slice especifico.
  3. alerta semantico amplo de caminhos nao-pyinstaller sem evidencia de regressao neste slice.
  4. fallback generico de `_detect_primary_executable_name` segue para ajuste semantico dedicado.
- Residuos locais fora de escopo (nao commitar):
  1. `data/ssas.db`
  2. `config/settings.json.bak_20260308_212715`

## HISTORICAL SNAPSHOT 2026-03-10 08:40

- Slice entregue:
  1. empacotador endurecido para separar status `missing` vs `failed` no instalador.
  2. `scripts/create_distribution.py`:
     - filtro sanitizado unificado (`_build_bundle_ignore`) aplicado tambem em copias de `_internal/config`.
     - `compile_installer` retorna `success|missing|failed`.
     - caller distingue `script_failed` para falha na geracao do script `.iss`.
     - ZIP usa `arcname` baseado em `package_dir`.
     - validacao de `.app` agora exige executavel real no bundle.
     - readme tecnico alinhado para `ANTIVIRUS_EXCLUSOES.md` e `LEIA-ME.md`.
  3. `tests/test_create_distribution.py`:
     - cobertura nova para caminho `missing` do compilador Inno.
  4. docs:
     - guia de distribuicao com troubleshooting separado para dependencia ausente vs falha de compilacao.
- Gates desta rodada:
  1. `py_compile`, `ruff`, `ty` -> pass.
  2. `pytest -q tests/test_create_distribution.py` -> `5 passed`.
  3. `kluster review` de codigo e docs tocados -> sem blocker novo.
- Pendencia deferida:
  1. `create_zip_package` ainda e funcao longa (debt de qualidade).
  2. regra de selecao por mtime em canonical dirs mantida como comportamento intencional no momento.
  3. alerta de cleanup de temp_dir em early-return ficou classificado como falso positivo apos revisao de codigo.
- Residuos locais fora de escopo (nao commitar):
  1. `data/ssas.db`
  2. `config/settings.json.bak_20260308_212715`

## HISTORICAL SNAPSHOT 2026-03-10 08:28

- Slice entregue:
  1. empacotador agora valida executavel primario antes de aceitar build dir.
  2. `scripts/create_distribution.py`:
     - canonical dirs PyInstaller podem ser configurados via `BUILD_SYSTEMS["pyinstaller"]["canonical_dirs"]`.
     - fallback mantido para canonical dirs padrao.
     - `_resolve_build_directory` endurecido para barrar diretorio parcial sem executavel.
  3. `tests/test_create_distribution.py`:
     - novo teste cobrindo cenario de canonical sem executavel primario.
     - mocks com `canonical_dirs` explicito.
  4. docs:
     - troubleshooting de distribuicao atualizado para nova regra de validacao.
- Gates desta rodada:
  1. `py_compile`, `ruff`, `ty` -> pass.
  2. `pytest -q tests/test_create_distribution.py` -> `4 passed`.
  3. `kluster review` em codigo tocado -> clean.
- Pendencia deferida:
  1. hardening cross-platform mais amplo de deteccao/selecao de artefato no empacotador.
- Residuos locais fora de escopo (nao commitar):
  1. `data/ssas.db`
  2. `config/settings.json.bak_20260308_212715`

## HISTORICAL SNAPSHOT 2026-03-10 08:18

- Slice entregue:
  1. Debian alinhado ao fluxo canonico de pacote ZIP.
  2. `launchers/platforms/debian_amd64/build_config.json`:
     - `post_build.package` ajustado para `zip`.
     - exclusoes de risco removidas de `exclude_modules` (`json`, `argparse` e modulos core de concorrencia/rede).
  3. docs operacionais refinados:
     - `docs/GUIA_DISTRIBUICAO.md`: Debian ZIP no baseline atual.
     - `docs/BUILD_MULTIPLATFORM.md`: UPX como opcional "quando disponivel" e nota de empacotamento Debian.
- Gates desta rodada:
  1. `kluster review` nos arquivos do slice -> clean na rodada final.
- Pendencia deferida:
  1. automacao AppImage/.deb permanece fora do fluxo oficial atual.
  2. revisao de `exclude_modules` em outras plataformas fica para slice dedicado.
- Residuos locais fora de escopo (nao commitar):
  1. `data/ssas.db`
  2. `config/settings.json.bak_20260308_212715`

## HISTORICAL SNAPSHOT 2026-03-10 08:04

- Slice entregue:
  1. hardening de build para nao incluir `data/` por padrao no artefato canonico.
  2. `launchers/build_multiplatform.py`:
     - `data/` so entra se `pyinstaller_args.include_local_data=true`.
     - log explicito de risco quando a flag e ativada.
  3. `tests/test_create_distribution.py`:
     - novo teste cobrindo exclusao de `.db`, `.xlsx`, `.xls` e conteudo sensivel de `data/docs_entrada` no pacote canonico.
  4. docs operacionais alinhados:
     - `docs/GUIA_DISTRIBUICAO.md`
     - `docs/BUILD_MULTIPLATFORM.md`
- Gates desta rodada:
  1. `py_compile`, `ruff`, `ty` -> pass.
  2. `pytest -q tests/test_create_distribution.py` -> `3 passed`.
  3. `kluster review` nos arquivos tocados -> sem blocker novo do slice.
- Pendencia deferida:
  1. debt antigo de naming/cross-compile em `build_multiplatform.py`.
  2. debt antigo de classe concentrada no builder.
  3. debt antigo de performance em scans recursive + subprocess por arquivo.
- Residuos locais fora de escopo (nao commitar):
  1. `data/ssas.db`
  2. `config/settings.json.bak_20260308_212715`

## HISTORICAL SNAPSHOT 2026-03-10 07:44

- Slice entregue:
  1. deduplicacao minima de prune de workers sem mudar semantica de cleanup.
  2. helper comum `_classify_and_update_global_workers_locked(...)` aplicado nos dois fluxos:
     - data loader prune
     - rescan prune
  3. cobertura nova de regressao para cap de workers em prune de rescan.
- Gates desta rodada:
  1. `py_compile`, `ruff`, `ty` -> pass.
  2. `pytest -q tests/test_gui_workers_rescan_data.py` -> `10 passed`.
  3. `kluster review file gui/ssa/gui_workers.py tests/test_gui_workers_rescan_data.py` -> sem novo blocker do slice; restam debts medios antigos fora de escopo.
  4. `kluster review file docs/RECOVERY_BACKLOG.md docs/NEXT_CHAT_MIGRATION.md docs/AGENTS_HANDOFF_NEXT_CYCLE.md` -> clean.
- Pendencia deferida:
  1. decompor `on_data_loaded` (debt de concentracao).
  2. desacoplar prompt de modo do fluxo `rescan_data`.
  3. mover sanitizacao/sort pesado do UI thread para worker.
- Residuos locais fora de escopo (nao commitar):
  1. `data/ssas.db`
  2. `config/settings.json.bak_20260308_212715`

## HISTORICAL SNAPSHOT 2026-03-10 06:14

- Slice entregue:
  1. DOC_SYNC de build/distribuicao para v4.32 sem tocar runtime.
  2. `docs/GUIA_DISTRIBUICAO.md` refeito para caminho canonico:
     - `launchers/build_multiplatform.py`
     - `launchers/dist/*`
     - `scripts/create_distribution.py`
  3. `launchers/README.md` alinhado com plataformas reais ativas.
  4. guias completos de PyInstaller/Nuitka/PyOxidizer com bloco `CURRENT TRUTH`
     e snapshot historico explicito para referencias antigas.
- Gates desta rodada:
  1. `kluster review` dos docs tocados -> clean.
- Pendencia deferida:
  1. secoes historicas extensas com exemplos antigos foram mantidas para contexto tecnico.
- Residuos locais fora de escopo (nao commitar):
  1. `data/ssas.db`
  2. `config/settings.json.bak_20260308_212715`

## HISTORICAL SNAPSHOT 2026-03-10 02:39

- Slice entregue:
  1. `scripts/create_distribution.py`:
     - resolve build canonico pyinstaller em `launchers/dist/*` com fallback legado `builds/*`.
     - exclui dados locais sensiveis no bundle canonico (`data`, `docs_entrada`, `.db`, `.xlsx`, etc.).
     - README do pacote usa executavel detectado dinamicamente.
     - Inno Setup:
       - resolve origem com suporte a build canonico windows;
       - usa `INNO_SETUP_COMPILER`/PATH antes de caminhos hardcoded;
       - corrige `OutputDir=.` e `SetupIconFile=..\\assets\\icon.ico`;
       - aplica exclusoes alinhadas a `EXCLUDED_BUNDLE_ITEMS`.
  2. `scripts/copy_data_to_builds.py`:
     - resolve alvos pyinstaller em `launchers/dist/<plataforma>` com fallback legado.
     - bloqueio de seguranca: copia de dados locais so com `--allow-local-data`.
  3. `tests/test_create_distribution.py`:
     - novo teste para fallback canonico pyinstaller.
     - ajuste de assert de erro no teste legado.
- Gates desta rodada:
  1. `py_compile`, `ruff`, `ty` -> pass.
  2. `pytest -q tests/test_create_distribution.py` -> `2 passed`.
- Pendencia deferida:
  1. `scripts/create_distribution.py`: funcao `create_zip_package` segue grande (debt de qualidade, fora do escopo de patch minimo).
  2. template Inno pode receber refinamento de atalhos GUI/CLI por binario dedicado em ciclo proprio.
  3. constantes de distribuicao ainda duplicadas entre scripts, candidato a modulo compartilhado.
- Residuos locais fora de escopo (nao commitar):
  1. `data/ssas.db`
  2. `config/settings.json.bak_20260308_212715`

## HISTORICAL SNAPSHOT 2026-03-10 01:11

- Slice entregue:
  1. `armazenamento/database.py`:
     - cache por chave em `_resolve_target_table`.
     - hardening de fallback de schema em `initialize_database`.
  2. `armazenamento/database_validation.py`:
     - report estruturado para coluna obrigatoria ausente.
     - erro de validacao com tipo de excecao + stacktrace.
  3. `extracao/extractor.py` + `utils/robust_importer.py`:
     - debug phases com namespace por planilha.
     - ajuste de duplicadas semanticas (`sn` e fallback de sufixo).
  4. `gui/gui_ssa.py`:
     - fallback de destino unico retrocompativel.
     - validacao de caminho local bloqueando basename iniciado em `-`.
  5. `gui/ssa/gui_workers.py`:
     - `max_global_workers` efetivo no classificador.
     - logs de expiracao com contexto de worker.
     - registro global/meta do data loader logo apos `start()`.
  6. `gui/mixins/tab_context_gui_ssa_mixin.py`:
     - unblock de sinais com guarda explicita.
  7. `gui/ssa/gui_theme.py`:
     - reaplicacao de QSS global baseada no stylesheet atual do app.
  8. testes/docs:
     - `tests/test_gui_workers_rescan_data.py` (cap TTL).
     - `tests/test_gui_filter_logic.py` (qWait dinamico).
     - `tests/test_db_reset_and_upsert.py` (assert reforcado).
     - `docs/TROUBLESHOOTING_IMPORTACAO.md` (`PY_RUNTIME`).
- Gates desta rodada:
  1. `py_compile`, `ruff`, `ty` -> pass.
  2. `pytest` focado workers/gui/upsert/validacao/importacao -> `8 passed`.
  3. `pytest` focado extracao/report/signal -> `35 passed`.
  4. `pytest` focado tema/resize/quick_filter -> `4 passed`.
- Pendencia deferida:
  1. debts estruturais amplos (God class/performance geral) mantidos para slice dedicado.
- Residuos locais fora de escopo (nao commitar):
  1. `data/ssas.db`
  2. `config/settings.json.bak_20260308_212715`

## HISTORICAL SNAPSHOT 2026-03-10 00:55

- Slice entregue:
  1. sync do quick filter com avancados (executor/emissor) + limpeza de excludes.
  2. popup rolavel do combo rapido.
- Gates desta rodada:
  1. `py_compile`, `ruff`, `ty` -> pass.
  2. `pytest` focado em quick setor/sort -> `5 passed`.
- Nota:
  1. comportamento de sync com avancados foi removido no hotfix 00:55.

## HISTORICAL SNAPSHOT 2026-03-10 00:36

- Slice entregue:
  1. `gui/gui_ssa.py`:
     - `_sort_num_reprogramacoes_robust` com alinhamento defensivo de indice para evitar risco de mismatch.
     - `on_header_clicked` re-prima cache de `num_reprogramacoes` apos sort da coluna.
     - tooltip de `Limpar Busca` alinhado ao comportamento real (cancelamento da busca em andamento sem reset de filtros de coluna/avancados).
     - `open_installation_guide` com `QUrl.fromLocalFile` explicito antes de `QDesktopServices.openUrl`.
- Gates desta rodada:
  1. `py_compile`, `ruff`, `ty` -> pass.
  2. `pytest` focado GUI filtro/sort/tooltip -> `6 passed`.
  3. `pytest` focado importacao externa/guia -> `2 passed`.
- Pendencia deferida:
  1. debts antigos de arquitetura/performance em `gui/gui_ssa.py` (fora deste slice).
- Residuos locais fora de escopo (nao commitar):
  1. `data/ssas.db`
  2. `config/settings.json.bak_20260308_212715`

## HISTORICAL SNAPSHOT 2026-03-10 00:22

- Slice entregue:
  1. `gui/gui_ssa.py`:
     - removeu persistencia do atalho rapido `Setor Executor`.
     - removeu checkbox `Configuracao persistente`.
     - combo rapido agora limita popup (`maxVisibleItems=14`) e sincroniza OR group/filtros de coluna via `_sync_or_group_values` + `_build_column_filters_panel`.
     - fix critico no fallback de destino unico em importacao externa (sem descriptor `__get__`).
  2. `tests/test_gui_filter_logic.py`:
     - contrato atualizado para o atalho rapido sem persistencia.
     - assert de sincronismo completo entre atalho e painel de filtros.
     - assert de UX do combo (sem checkbox de persistencia e popup limitado).
- Gates desta rodada:
  1. `py_compile`, `ruff`, `ty` -> pass.
  2. `pytest` focado em filtros/cache -> `7 passed`.
  3. `pytest` focado em importacao externa -> `2 passed`.
- Pendencia deferida:
  1. debts antigos de arquitetura/performance em `gui/gui_ssa.py` (fora deste slice).
- Residuos locais fora de escopo (nao commitar):
  1. `data/ssas.db`
  2. `config/settings.json.bak_20260308_212715`

## HISTORICAL SNAPSHOT 2026-03-10 00:17

- Slice entregue:
  1. `gui/gui_ssa.py`:
     - `_sort_num_reprogramacoes_robust` agora sincroniza `_num_reprog_sort_cache` com o dataframe ja ordenado.
     - evita cache stale imediato apos clique em cabecalho de `num_reprogramacoes`.
  2. `tests/test_gui_filter_logic.py`:
     - testes de cache ajustados para contratos estruturais (index + keys + source_len), sem dependencia de identidade de objeto.
     - teste de persistencia do filtro rapido inicializa checkbox de forma deterministica.
- Gates desta rodada:
  1. `py_compile`, `ruff`, `ty` -> pass.
  2. `pytest` focado (`num_reprogramacoes` + filtro rapido + colunas visiveis) -> `7 passed`.
- Pendencia deferida:
  1. debts antigos de arquitetura/performance em `gui/gui_ssa.py` (fora deste slice).
- Residuos locais fora de escopo (nao commitar):
  1. `data/ssas.db`
  2. `config/settings.json.bak_20260308_212715`

## HISTORICAL SNAPSHOT 2026-03-09 23:53

- Slice entregue:
  1. `gui/widgets/column_selector.py`:
     - removeu resumo lateral.
     - botao agora mostra `Colunas Visiveis: N`.
  2. `gui/gui_ssa.py`:
     - removeu seletor de `Perfil de filtro` da UI.
     - adicionou combo rapido `Setor Executor` ao lado de `Colunas Visiveis`.
     - ordem do combo: `IEE1..IEE4`, depois `MEL1..MEL4`, depois alfabetica.
     - adicionou checkbox `Configuracao persistente` (default false) como primeira opcao da faixa.
     - com persistencia ativa, grava automaticamente:
       - `gui_settings.persist_quick_filter_config`
       - `gui_settings.quick_setor_executor`
       - `display_columns`.
  3. `gui/mixins/tab_context_gui_ssa_mixin.py`:
     - bind de perfil tolera ausencia de `profile_selector`.
  4. `gui/mixins/filter_gui_ssa_mixin.py`:
     - refresh/clear global sincronizam combo rapido de setor executor.
  5. `tests/test_gui_filter_logic.py`:
     - novos testes para:
       - texto do botao `Colunas Visiveis: N`;
       - ordenacao priorizada de setores;
       - aplicacao e persistencia do filtro rapido.
- Gates desta rodada:
  1. `py_compile`, `ruff`, `ty` -> pass.
  2. `pytest` focado novo comportamento -> `3 passed`.
  3. `pytest tests/test_gui_menu_import_external.py` -> `13 passed`.
- Pendencia deferida:
  1. debts antigos de arquitetura/performance em `gui/gui_ssa.py` e mixins (fora deste patch minimo).
- Residuos locais fora de escopo (nao commitar):
  1. `data/ssas.db`
  2. `config/settings.json.bak_20260308_212715`

## HISTORICAL SNAPSHOT 2026-03-09 23:24

- Micro-slice de correcao pontual entregue:
  1. `gui/gui_ssa.py`: ajuste da chamada fallback de `_build_unique_destination_path` para descriptor bound call.
  2. objetivo: remover ambiguidade de assinatura reportada no PR, sem alterar fluxo funcional.
- Gates desta rodada:
  1. `py_compile`, `ruff`, `ty` -> pass.
  2. `pytest` focado em importacao/menu -> `5 passed`.
- Pendencia deferida:
  1. debts antigos de arquitetura/performance em `gui/gui_ssa.py` seguem fora deste micro-slice.
- Residuos locais fora de escopo (nao commitar):
  1. `data/ssas.db`
  2. `config/settings.json.bak_20260308_212715`

## HISTORICAL SNAPSHOT 2026-03-09 23:08

- Slice entregue: pendencia pesada + comentarios simples do PR.
  1. `gui/gui_ssa.py`:
     - `run_vacuum_analyze` em worker de fundo (runtime normal), mantendo modo sincrono em teste.
     - `_build_unique_destination_path` agora limitado (sem loop infinito).
     - backup de opcoes com timestamp de microssegundos.
     - consolidacao de arquivos: update-only fica em `processadas`; `nosurvivor` exige zero mutacao real.
  2. `gui/ssa/gui_workers.py`:
     - fallback seguro de `rescan_mode="prompt"` para incremental quando dialogo nao existe.
     - dedup de `expired_all` no prune de data loaders.
     - limpeza de `_active_rescan_dialog` garantida no `worker.finished`.
  3. testes:
     - `tests/test_gui_menu_import_external.py`: patch headless de `QUrl`/`QDesktopServices`, backup duplo unico, update-only fora de `nosurvivor`.
     - `tests/test_gui_workers_rescan_data.py`: assert de `show_non_modal_called`, dialogo limpo no cancel+finish, `prompt` sem dialogo em incremental.
  4. docs:
     - `docs/CCR_LLM_PROVIDERS_SETUP.md`: nota de snapshot historico para evitar ambiguidade sobre `instructions` legadas.
- Gates desta rodada:
  1. `py_compile`, `ruff`, `ty` -> pass.
  2. `pytest -q tests/test_gui_menu_import_external.py tests/test_gui_workers_rescan_data.py` -> `20 passed`.
- Pendencias deferidas:
  1. debts antigos de arquitetura/performance apontados por kluster em `gui/gui_ssa.py` e `gui/ssa/gui_workers.py` (fora de escopo deste patch minimo).
- Residuos locais fora de escopo (nao commitar):
  1. `data/ssas.db`
  2. `config/settings.json.bak_20260308_212715`

## HISTORICAL SNAPSHOT 2026-03-09 22:49

- Heavy pending slice entregue (foco em performance/stability de carga):
  1. `gui/workers/data_loader_worker.py`:
     - preprocessamento de dados para GUI movido para worker (sanitize + sort + non-null cols).
     - resultado chega com attrs (`ssa_preprocessed_for_gui`, `ssa_sanitized_df`, `ssa_non_null_cols`).
  2. `gui/ssa/gui_workers.py`:
     - `on_data_loaded` usa attrs do worker no caminho padrao e evita preprocessamento pesado no UI thread.
     - fallback legado mantido para compatibilidade.
     - falha ao instanciar worker de carga agora sempre restaura UI (botoes/progress).
     - guards extras para atributos opcionais em status/erro.
  3. testes:
     - `tests/test_data_loader_worker.py` e `tests/test_gui_filter_logic.py` atualizados para novo contrato.
- Gates desta rodada:
  1. `py_compile`, `ruff`, `ty` -> pass.
  2. `pytest` focado (`8 passed`) + `DataLoaderWorker` em `test_workers_advanced` (`14 passed`) -> pass.
- Pendencias deferidas:
  1. kluster `HIGH knowledge` sobre `query_db(..., '', query, ...)` classificado como `FALSO_POSITIVO` pelo contrato atual de `query_db`.
  2. debt historico de concentracao em `on_data_loaded` e duplicacao residual de logica segue para ciclo dedicado.
- Residuos locais fora de escopo (nao commitar):
  1. `data/ssas.db`
  2. `config/settings.json.bak_20260308_212715`

## HISTORICAL SNAPSHOT 2026-03-09 22:30

- Politica ASCII para review/documentacao tecnica reforcada:
  1. sugestoes ortograficas com acentos/cedilha em texto tecnico devem ser classificadas como `FALSO_POSITIVO` quando conflitar com a politica ASCII do repo.
- Debts antigos priorizados para proximo ciclo:
  1. `gui/gui_ssa.py`: `SSAMainWindow` com debt arquitetural (classe concentrada).
  2. `gui/ssa/gui_workers.py`: `on_data_loaded` com custo alto no UI thread.
  3. `gui/ssa/gui_workers.py`: duplicacao de prune/cleanup entre fluxos de workers.
- Escopo desta rodada:
  1. DOC_SYNC de governanca.
  2. sem alteracao de runtime.
  3. kluster em docs tocados -> clean.
- Residuos locais fora de escopo (nao commitar):
  1. `data/ssas.db`
  2. `config/settings.json.bak_20260308_212715`

## HISTORICAL SNAPSHOT 2026-03-09 22:11

- Follow-up de comentarios pendentes do PR #45 concluido com patch minimo:
  1. `gui/ssa/gui_workers.py`: cap nao remove mais worker vivo; init de lista de workers sob lock antes de prune.
  2. `gui/gui_ssa.py`: importacao externa copia somente `.xlsx` e reporta `nao_suportados`; consolidacao de `nosurvivor` depende de sucesso sem sobreviventes.
  3. `utils/caching.py`: descoberta de extensoes Excel case-insensitive.
  4. `armazenamento/database_integrity.py`: resolucao de alias passa a preferir `table` sobre `view`.
  5. testes focados adicionados/ajustados para cobrir os contratos acima.
- Gates desta rodada:
  1. `py_compile`, `ruff`, `ty` -> pass.
  2. `pytest` focado (`47 passed`) -> pass.
- Pendencias deferidas:
  1. debts de arquitetura/performance em `gui/gui_ssa.py` e `gui/ssa/gui_workers.py` (fora deste slice).
  2. revisao de semantica de `database_exists` em arquivo SQLite vazio (ciclo dedicado).
- Residuos locais fora de escopo (nao commitar):
  1. `data/ssas.db`
  2. `config/settings.json.bak_20260308_212715`

## HISTORICAL SNAPSHOT 2026-03-09 21:58

- Follow-up P2 de comentarios do PR #45 concluido:
  1. `gui/ssa/gui_workers.py`: registro global imediato de rescan worker apos `start()`.
  2. `gui/gui_ssa.py`: dedup de destino unificado em importacao externa via helper unico.
  3. `docs/CCR_LLM_PROVIDERS_SETUP.md`: padrao de instructions corrigido para `*.instructions`.
  4. `tests/test_gui_workers_rescan_data.py`: expectativa atualizada para novo contrato do registro global.
- Gates desta rodada:
  1. `py_compile`, `ruff`, `ty` -> pass.
  2. `pytest` focado GUI workers/menu -> `16 passed`.
- Pendencia deferida:
  1. normalizacao nao-ascii em testes (debt transversal, nao blocker funcional imediato).
- Residuos locais fora de escopo (nao commitar):
  1. `data/ssas.db`
  2. `config/settings.json.bak_20260308_212715`

## HISTORICAL SNAPSHOT 2026-03-09 21:43

- PR em andamento: `#45` (`dev` <- `codex/sprint-importacao-grave-fixes-20260305`).
- Slice de hotfix de comentarios/checks concluido:
  1. ajuste de contrato no teste de cancelamento (`tests/test_import_cancellation.py`).
  2. correcao de log de warnings de integridade (`core/app_logic.py`).
  3. limpeza de retorno nao serializavel em validacao (`database_validation.py`).
  4. contrato `raise_on_error` alinhado para `ValueError` em `query_db` (`database.py`).
  5. removido suppress silencioso na whitelist do insert simples (`database.py`).
  6. removido warning falso em reparo opcional (`database_integrity.py`).
- Gates desta rodada:
  1. `py_compile`, `ruff`, `ty` (arquivos tocados) -> pass.
  2. `pytest` focado (`30 passed`) e pacote equivalente ao `quality-gates` (`73 passed`) -> pass.
- Residuos locais fora de escopo (nao commitar):
  1. `data/ssas.db`
  2. `config/settings.json.bak_20260308_212715`

## HISTORICAL SNAPSHOT 2026-03-09 19:26

- Integridade de links/referencias em docs ativos concluida.
- Entregas principais:
  1. referencias quebradas em docs ativos corrigidas.
  2. stubs `docs/ARCH_*` adicionados para compatibilidade com backlog historico.
  3. referencias locais opcionais (`local_ai_private`) deixadas sem dependencia de arquivo especifico.
- Nao alterado:
  1. runtime de importacao/GUI/DB.
  2. testes de runtime.
- Residuos locais fora de escopo (nao commitar):
  1. `data/ssas.db`
  2. `config/settings.json.bak_20260308_212715`

## HISTORICAL SNAPSHOT 2026-03-09 19:01

- Ciclo de refinamento de documentacao concluido no baseline `4.32`.
- Entregas principais:
  1. index e README de docs canonicos.
  2. comandos rapidos alinhados para uv-first.
  3. arquitetura e troubleshooting ativos simplificados.
  4. snapshots legados movidos para `docs/archive/`.
- Nao alterado:
  1. runtime de importacao/GUI/DB.
  2. suite de testes de runtime.
- Residuos locais fora de escopo (nao commitar):
  1. `data/ssas.db`
  2. `config/settings.json.bak_20260308_212715`

## HISTORICAL SNAPSHOT 2026-03-09 17:35

- Baseline ativo de versao/documentacao: `4.32`.
- Escopo consolidado atual:
  1. sync de metadados e docs para `4.32` concluido.
  2. governanca de docs refinada com fonte ativa unica no topo.
  3. historico antigo arquivado para reduzir risco de leitura ambigua.
- Nao alterado nesta rodada:
  1. runtime de importacao/GUI/DB.
  2. testes de runtime.
- Residuos locais fora de escopo (nao commitar):
  1. `data/ssas.db`
  2. `config/settings.json.bak_20260308_212715`

## REGRAS DE USO DESTE HANDOFF

1. Somente este bloco do topo e autoritativo para iniciar o proximo ciclo.
2. Informacoes antigas ficam no arquivo de historico arquivado.
3. Em caso de conflito entre historico e topo, prevalece o topo.

## ARQUIVO HISTORICO

- Historico completo anterior (ate 2026-03-09 17:35):
  - `docs/archive/AGENTS_HANDOFF_NEXT_CYCLE_legacy_until_20260309_1735.md`

## CHECKLIST OPERACIONAL PARA O PROXIMO CICLO

1. confirmar branch/pasta antes de editar.
2. registrar timestamp inicial/final no `docs/RECOVERY_BACKLOG.md`.
3. manter commits atomicos por slice e push imediato no branch alvo.
4. atualizar este handoff e `docs/NEXT_CHAT_MIGRATION.md` no mesmo slice.

## AVISO FINAL - HISTORICO ABAIXO NAO E AREA DE COLAGEM

1. o restante deste arquivo existe para historico e auditoria.
2. nao anexar nova verdade atual, lista de pendencias, logs ou estado de branch abaixo deste aviso.
3. o topo `CURRENT TRUTH` e a unica area viva para status atual.
4. pendencias novas entram no topo ou em `docs/RECOVERY_BACKLOG.md`, sempre por prioridade.
5. colar estado atual no fim deste arquivo degrada leitura automatica e manutencao futura.

<!-- DOC_SYNC_MAC: 2026-03-29 host-agnostic paths, continue from repo root on macOS -->
