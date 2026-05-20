# Next Chat Migration Guide

## CURRENT TRUTH 2026-05-20 00h46

- Branch alvo operacional: `dev`.
- HEAD operacional atual validado localmente e publicado em `origin/dev`:
  - `c0888b25a66b59392f4498ba2e4375be76af4504 2026-05-20T00:35:59-03:00 STABILITY_PATCH: stabilize GUI pytest order in CI`.
  - `50f405a6815ec0e33572fa967948f1131a5dcbfa 2026-05-20T00:12:32-03:00 STABILITY_PATCH: harden PAI import summary contract`.
  - `2cf14f52469454cdf2fd08e37d7b4cf817ff24ef 2026-05-19T23:08:55-03:00 STABILITY_PATCH: move PAI XLSX summary to streaming reader`.
- `dev` esta sincronizado com `origin/dev`.
- `main` nao deve ser assumido sincronizado com `dev` sem nova checagem.
- Workspace local tem apenas residuos fora de escopo:
  - `.agents/`
  - `agents.lock`
  - `config/gui_saved_filters.json`
- `.gitignore` ja ignora `.clawpatch/`, `agents.toml` e `tmp/`.
- Checks GitHub verdes no head publicado `c0888b25a66b59392f4498ba2e4375be76af4504`:
  - `minimal-ci`
  - `CodeQL`
  - `Secret Scan`
  - `Automatic Dependency Submission`
- API PAI:
  - fluxo real habilitado: `consulta`.
  - smoke real fetch-only validado neste ciclo para `IEE3` com CA exportada via `scrap_report`; ciclo anterior ja validou `IEE3`, `MEL4`, `MEL3`.
  - GUI confirma antes de gravar dados da API no DB.
  - Auto-refresh nao grava no DB automaticamente.
  - `summary-json` registra fonte, filtros pedidos, setores, arquivos origem, contagens e exemplos de SSAs.
  - resumo XLSX agora e carregado pelo servico de importacao e reaproveitado no report, sem segunda leitura XLSX no caminho normal.
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
  1. Se PR for autorizado, rodar CodeRabbit no PR.
  2. Executar build/smoke macOS se o alvo for release de artefato.
  3. Continuar corte de `filter_gui_ssa_mixin.py` e `SSAMainWindow` se a meta clean-code for criterio bloqueante.
- Build macOS/release ainda nao executado neste ciclo.

Use este arquivo para migrar contexto para um novo chat sem perder qualidade de execucao.

## HISTORICAL SNAPSHOT 2026-04-22 13h14

### Estado de repositorio e runtime

1. branch ativa confirmada: `dev`
2. `HEAD` local e `origin/dev` estao alinhados em `b5e3335b7565f104c23054777499ff350cce2b94`
3. ultimo commit atual:
   - `2026-04-22 13:14:32 -0300`
   - `docs(handoff): Sync post-lab current truth`
4. workspace local atual:
   - repo limpo no escopo desta frente
   - residuos fora de escopo:
     - `AGENTS.md.backup_20260416_223903`
   - laboratorio `B` em worktree destacado foi encerrado e removido sem portar patch para `dev`
5. PR remoto ativo:
   - `#47` `dev -> main`
   - titulo: `Merge dev into main for stabilization and gui follow-up`
   - estado: `OPEN`
   - `mergeStateStatus=UNSTABLE`
6. a frente principal mais recente foi desempenho e estabilidade da GUI:
   - carga inicial
   - busca geral
   - filtros
   - undo
   - detalhes laterais
   - dialogo de detalhes
   - troca de aba preservando estado
7. o ciclo de `2026-04-16/17` fechou gargalos serios de desempenho e RAM:
   - cortes de alocacao desnecessaria no carregamento e nos fluxos de busca/reset/undo
   - eliminacao de carregamentos de recursos excessivos no caminho de detalhes
   - menos rebuild global e menos cache frio caro
   - preservacao do estado vivo de detalhes ao trocar de aba
8. commits de referencia imediata:
   - `3f49caef` `perf(gui): Elide stale details lookup on tab bind`
   - `51a0a69a` `perf(gui): Preserve search cache across requests`
   - `12fbc46c` `fix(gui): Stop global SSA index builds in details flows`
   - `b93b367d` `perf(gui): Reduce search cache memory and details lookup`
   - `edaa90e7` `perf(gui): Reuse full dataset on reset and lazy reprog cache`
   - `73881633` `perf(gui): Remove heavy undo snapshot dataframe retention`
   - `a160a589` `perf(gui): Skip null-only columns in general search`
   - `e3b5561d` `perf(search): Cut cold row cache build cost`
   - `ffecabff` `fix(gui): Preserve live details across tab bind`
9. o bug de perder a SSA selecionada na troca de aba esta fechado
10. busca/filtros melhoraram bem, mas a frente ainda nao esta encerrada
11. residuos reais que continuam abertos nesta retomada:
   - o backlog antigo ainda citava:
     - `tests/test_quality_gates_smoke.py:34`
     - `tests/test_workers_advanced.py:648`
   - revalidacao posterior mostrou esses 2 itens como fechados
   - o laboratorio `B` para cache grande no full dataframe foi descartado por custo de RAM no alvo de `4 GB`
   - o proximo residual tecnico real precisa ser reidentificado por novo diagnostico puro, sem assumir hotspot antigo sem evidencia
12. levantamento de footprint desta rodada, sem editar runtime:
   - `query_db()`:
     - `80448 x 84`
     - `717.60 ms`
     - RSS `90.50 MB -> 402.30 MB`
   - `_prepare_dataframe_for_ui()`:
     - `303.14 ms`
     - RSS `402.30 MB -> 470.09 MB`
     - retorna novo objeto (`same_object=False`)
   - `filter_dataframe()` no full dataframe:
     - frio `419.17 ms`
     - quente `416.42 ms`
     - cache cheio ainda so com `token`
   - refinamento em subset:
     - `39.75 ms`
     - subset com `row_search_text` e `token`
   - fallback raro `on_data_loaded()` sem preprocessamento:
     - `255.61 ms`
     - `+108 MB` de RSS
     - `df_completo is df_exibido == False`
13. ranking tecnico atual:
   - leitura cheia via `query_db()`
   - preprocessamento inicial do `DataLoaderWorker`
   - rebuild da busca ampla no full dataframe
   - fallback raro de `on_data_loaded()` sem attrs
14. proxima frente recomendada:
   - medir e cortar ownership/materializacao no load path principal antes de reabrir qualquer experimento de cache amplo
15. commits aterrados nesta retomada:
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
13. efeito funcional consolidado:
   - a carga sem filtros preserva o dataframe preprocessado do worker como estado visual inicial
   - o refresh simples agora pula filtros avancados/coluna quando nao existe filtro extra ativo
   - o caminho de sanitizacao/ordenacao inicial ficou centralizado no `DataLoaderWorker`
   - a busca geral simples reaproveita o dataframe filtrado ordenado em vez de recriar `df_exibido`
   - o cache grande de `row_search_text` deixou de permanecer no dataframe cheio quando o payload fica caro
   - a GUI agora refina de forma segura sobre `_df_last_search_filtered` quando o novo texto estende monotonicamente a busca anterior
   - os filtros por coluna agora reduzem o `working_df` por etapa no refresh, evitando reprocessamento amplo desnecessario
   - o combo rapido de setor executor passou a reutilizar as opcoes atuais em vez de repopular tudo a cada refresh
14. validacao aterrada nesta frente:
   - `py_compile`, `ruff`, `ty` verdes no escopo tocado
   - `pytest` focados verdes:
     - `tests/test_filter_cache_locking.py`
     - `tests/test_filter_worker.py`
     - `tests/test_workers_advanced.py` no bloco de cache do `FilterWorker`
     - `tests/test_data_loader_worker.py`
     - selecoes relevantes de `tests/test_gui_filter_logic.py`
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
     - cache local de series normalizadas: `3` entradas no caso repetido
   - caminho de data apos `541a8f0a`:
     - primeira chamada: `4.44ms`
     - hit quente: `0.01ms`
     - recalc apos revisao no mesmo dataframe: `2.79ms`
     - invalidacao correta sem stale cache
   - prints atualizados:
     - `artifacts/gui_load_after_real_db.png`
     - `artifacts/gui_filter_MEL3.png`
     - `artifacts/gui_filter_MEL3_page2.png`
   - nota: esta ultima rodada foi em `offscreen`; usar a baseline interativa anterior para comparacao fina de RSS
16. checks remotos do PR `#47` apos esta frente:
   - `pass`: `CodeFactor`, `CodeQL`, `CodeRabbit`, `DeepScan`, `GitGuardian`, `Socket Security: Project Report`, `analyze (python)`, `secret-scan`, `submit-pypi`, `precheck-default-setup`
   - `pending`: `semgrep-cloud-platform/scan`
   - `fail` externo/vendor: `DeepSource: Error`
   - `fail` externo por limite: `code/snyk (mauriciomenon)`, `security/snyk (mauriciomenon)`
17. update multi-chunk mais recente:
   - chunks identicos passaram a ser deduplicados dentro da mesma requisicao
   - o ajuste entrou no worker assincrono e nos caminhos sync/fallback
   - a semantica final foi preservada:
     - chunk unico reaproveita o frame filtrado
     - chunk vazio reaproveita a base
     - multi-chunk continua com `drop_duplicates()` no merge final
   - validacao aterrada:
     - `49 passed`
     - `44 passed, 1 skipped`
   - prova real curta:
     - busca `MEL3, MEL3, MEL`
     - `FILTER_MS=1019.53`
     - `FILTER_ROWS=4680`
     - `df_exibido is _df_last_search_filtered == True`
18. update de merge multi-chunk por indice:
   - a deduplicacao final do merge deixou de comparar linha inteira
   - o merge agora colapsa sobreposicoes pelo indice original do `df_completo`
   - isso preserva linhas iguais com indices diferentes
   - validacao aterrada:
     - `51 passed`
     - `46 passed, 1 skipped`
   - prova real curta:
     - chunks artificiais `MEL3 + MEL`
     - `FILTER_MS=1674.28`
     - `FILTER_ROWS=22606`
     - `df_exibido is _df_last_search_filtered == True`
19. leitura tecnica atual:
   - a frente `D` removeu recarregamentos e donos concorrentes importantes no load/filter path
   - os follow-ups imediatos recuperaram memoria residente do cache de busca e ganho quente no refinamento seguro da GUI
   - os tres slices seguintes derrubaram o refresh quente de `138.72ms` para `62.61ms` na primeira passagem e `10.13ms` na repeticao com a mesma revisao/dataframe
   - o stale risk do cache de data por `id(df)` puro foi fechado em `541a8f0a`
   - o funil funcional de excecoes por arquivo foi fechado em `a96b8c703249b53832bb335e9b212f81f27d847f`
   - `_process_file_with_resilience(...)` agora contem `KeyError` e `AttributeError` por arquivo
   - `_import_single_file(...)` agora tolera `validation_report` sem `is_valid`
   - o residual de frame unico em `gui/workers/filter_worker.py:182` foi reduzido em `0c57e699a3867cd88a8faf926ad9d3f1a11f7023`
   - a duplicacao do fallback de `on_data_loaded(...)` foi reduzida em `fe608884496868c08f61557e9b844076ee80acb5`
   - a frente principal nao precisa mais reabrir o merge multi-chunk ja fechado
   - o proximo diagnostico deve mirar so o residual realmente aberto, sem voltar para `drop_duplicates()` como hotspot principal
   - os residuos de teste devem continuar em frentes separadas e pequenas
   - nao ha motivo para reabrir layout, detalhes de aba ou helper novo nesta retomada

## HISTORICAL SNAPSHOT 2026-04-11 23h00

### Estado de repositorio e runtime

1. branch ativa confirmada: `dev`
2. worktree desta frente deve ser lido como quase limpo:
   - so backups locais fora de escopo permanecem recorrentes
3. a busca geral da GUI agora e dona explicita do proprio contrato de colunas
4. o contrato de busca geral esta documentado em:
   - `docs/GUI_GENERAL_SEARCH_COLUMN_CONTRACT.md`
5. o contrato de estado do bloco GUI/tabela/detalhes agora deve ser lido assim:
   - reorder de coluna nao atualiza detalhes
   - sort de coluna nao atualiza detalhes
   - resize persiste largura pela coluna correta mesmo com reorder
   - reorder em schema parcial nao pode truncar colunas visiveis ausentes
   - filtro por derivadas atualiza lista e detalhes da derivada exibida
   - limpar derivadas retorna para a SSA origem via `_jump_to_ssa(...)`
   - selecao stale nao sobrevive ao rebuild da pagina
   - filtro assincrono preserva detalhes da SSA atual se ela continua visivel
   - filtro assincrono migra detalhes para o novo resultado quando a SSA atual sai do conjunto
6. o post-mortem tecnico desta frente esta em:
   - `docs/GUI_STATE_CONTRACT_POSTMORTEM_20260409.md`
7. o contrato de preferencias GUI continua sendo:
   - `config/gui_main_preferences.json` e o arquivo efetivo tracked de runtime
   - `.example` documenta o padrao
   - largura persistida valida vence largura automatica
   - `column_widths_by_platform` segue como fonte preferencial quando existir
8. a CLI continua fora desta frente; o caminho principal permanece:
   - `main.py -> interface/cli.py -> interface/table_printer.py`
9. `kluster` esta disponivel neste host em:
   - `/Users/menon/.kluster/cli/bin/kluster`
10. `tests/test_gui_filter_logic.py` agora isola e restaura o estado global de lifecycle de workers aposentados por teste
11. o achado medio confirmado sobre dependencia explicita de globais nesse arquivo foi fechado com patch minimo de harness, sem tocar runtime da GUI

### Validacao relevante desta rodada

1. `py_compile`, `ruff`, `ty` -> verdes nos slices funcionais recentes
2. regresses chave aterradas:
   - `tests/test_gui_filter_logic.py`
   - `tests/test_gui_table_render_resilience.py`
   - `tests/test_gui_main_configuration.py`
3. `pytest` focados relevantes desta frente ficaram verdes
4. `kluster` local existe neste host, mas timeout de review continua devendo ser tratado como bloqueio de ferramenta, nao como gate verde
5. o review focado do arquivo de teste apos o patch de lifecycle voltou limpo

### Proximo passo recomendado

1. ao abrir a nova janela, ler nesta ordem:
   - `AGENTS.md`
   - `docs/NEXT_CHAT_MIGRATION.md`
   - `docs/AGENTS_HANDOFF_NEXT_CYCLE.md`
   - `docs/RECOVERY_BACKLOG.md`
2. tratar este topo como a fonte viva do estado atual; os blocos abaixo sao historico
3. manter qualquer refatoracao de `display_current_page(...)` em slice separado
4. nao reabrir CLI junto com GUI sem pedido explicito
5. nao mexer em layout/posicionamento sem pedido explicito
6. ordem obrigatoria de retomada tecnica agora:
   - fechar este `DOC_SYNC`
   - voltar para diagnostico puro do proximo hotspot estrutural
   - aprovar um novo slice minimo antes de tocar runtime
   - manter qualquer novo residual de teste em frente separada, sem misturar tudo
7. considerar fechado o bug da troca de aba; nao reabrir essa area sem novo repro
8. buscar regressao real em RAM e tempo de carga antes de qualquer micro-otimizacao nova
9. antes de qualquer novo patch, declarar:
   - objetivo do slice
   - arquivos permitidos
   - arquivos proibidos

## HISTORICAL SNAPSHOT 2026-04-07 00h30

### Estado de repositorio e runtime

1. branch ativa confirmada: `dev`
2. `HEAD` local inclui o slice de hierarquia de preferencias GUI e a correcao de que o `.example` nao participa do runtime
3. worktree do slice foi validado localmente com `py_compile`, `ruff`, `ty` e `pytest` focado
4. stash preservado fora desta baseline:
   - `stash@{0}` `On main: pre-dev-switch-display-mappings-20260406`
5. este slice consolidou a hierarquia correta de preferencias GUI:
   - arquivo versionado de referencia em `config/gui_main_preferences.json.example`
   - arquivo efetivo de runtime continua `config/gui_main_preferences.json`
   - largura persistida do arquivo agora prevalece sobre largura automatica da tabela
   - o baseline automatico do `SimpleWidthManager` agora parte de `DEFAULT_COLUMN_WIDTHS`, sem numeros paralelos para colunas fixas
   - reorder e hide/show de colunas agora persistem no mesmo arquivo local
6. arquivos tocados no slice funcional mais recente:
   - `gui/gui_config.py`
   - `gui/ssa/gui_table.py`
   - `gui/simple_width_manager.py`
   - `tests/test_gui_main_configuration.py`
   - `tests/test_gui_filter_logic.py`
   - `tests/test_streamlit_filter_cache.py`
   - `config/gui_main_preferences.json.example`
   - `docs/GUI_MAIN_PREFERENCES_STRUCTURE.md`
7. `kluster` esta disponivel neste host em:
   - `/Users/menon/.kluster/cli/bin/kluster`
8. doc tecnico novo desta frente:
   - `docs/GUI_MAIN_PREFERENCES_STRUCTURE.md`
   - o doc agora explicita, em texto direto:
     - runtime cai para defaults em memoria quando faltar arquivo efetivo ou mudar `SSA_CONFIG_DIR`
     - largura persistida vencendo a largura automatica
     - fallback local da tabela preso ao contrato canonico
     - `config/gui_main_preferences.json` como arquivo efetivo tracked, `.example` documentando o padrao e codigo definindo a base
     - header da GUI agora usa matriz explicita `short/medium/long` por coluna e escolhe a maior variante que cabe na largura real
     - o calculo do header reserva espaco para o prefixo `[f] `
     - a CLI continua fora do contrato de preferencias da GUI, mas segue usando `display_map`, `short_labels`, `fixed_widths` e alternancia `short/full`
     - `core/handler_base.py:197` continua documentado apenas como renderer paralelo fora do caminho principal `main.py -> interface/cli.py -> interface/table_printer.py`
9. PR ativo desta baseline:
   - `#46` `dev -> main`
   - `mergeStateStatus=UNSTABLE`
10. checks remotos relevantes agora:
   - `DeepSource: Python` -> fail
   - `code/snyk (mauriciomenon)` -> fail por limite da ferramenta
   - demais checks principais -> pass

### Validacao relevante desta rodada

1. `py_compile`, `ruff`, `ty` -> verdes
2. `pytest` focado -> `11 passed`
3. `kluster` no escopo tocado -> sem blocker do slice; sobrou debt semantico antigo em nome de filtro `exclude_ste_sca`

### Proximo passo recomendado

1. analisar em slice separado, sem executar sem aprovacao:
   - revisao numerica opcional dos mapas em `DEFAULT_COLUMN_WIDTHS_BY_PLATFORM`, se o produto quiser reabrir tamanhos canonicos
2. manter separado qualquer follow-up de `.gitignore`/`dev_env/config/display_mappings.json`
3. backlog semantico aberto:
   - renomear ou reclassificar o agrupamento `exclude_ste_sca` se o produto realmente agrupa `SES/SAD/STE/SCA`

## HISTORICAL SNAPSHOT 2026-03-31 09h49

### Estado de repositorio e runtime

1. branch ativa: `dev`
2. ultimo commit remoto confirmado: `7913c712` (`DOC_SYNC: align live continuity docs`)
3. ultimo slice funcional remoto confirmado: `d6fbb4fe` (`STABILITY_PATCH: unify advanced filter state`)
4. commits recentes de referencia:
   - `7913c712` `DOC_SYNC: align live continuity docs`
   - `02ec4a30` `DOC_SYNC: add ultra technical audit report`
   - `b7af8aef` `STABILITY_PATCH: support non-text search columns`
   - `d6fbb4fe` `STABILITY_PATCH: unify advanced filter state`
5. metadata/tag ativa documentada: `4.37` / `v4.36`
6. worktree esta limpo e alinhado com remoto: `HEAD...origin/dev = 00`
7. recuperacao forense apos falha externa de PowerShell confirmou que nao havia shell ativo nem operacao critica de runtime aberta nesta frente
8. o ultimo pedido explicito recuperado no historico foi sync dos MDs vivos; isso ja foi aterrado em `7913c712`
9. existe residuo antigo `.git\REBASE_HEAD` datado de `2025-11-26`, sem `rebase-apply`/`rebase-merge`; tratar como hygiene de Git separada, nao como rebase vivo desta sessao
10. limite operacional desta retomada: `bandit` nao esta instalado no ambiente atual; se continuar obrigatorio, abrir slice proprio de tooling/dependency antes de cobrar esse gate

### O que foi feito nos ultimos slices

1. foi publicado o artefato de auditoria tecnica grande:
   - `docs_saida/ULTRA_AUDITORIA_TECNICA_REPO_20260330.md`
2. `core/app_logic.py::filter_dataframe()` foi corrigido para nao perder `search_columns` numericas/datetime antes da coercao para string
3. `tests/test_app_logic_filter_contract.py` recebeu regressao para busca em colunas numericas e datetime
4. `setor_executor` passou a sincronizar estado persistente entre combo rapido e painel avancado
5. o painel avancado de `Solicitante` passou a materializar valores quando o dataset expoe apenas `responsavel_solicitante`
6. o prefixo de area/setor em responsaveis deixou de derivar apenas do subconjunto filtrado

### Pendencias reais (nao fechadas)

1. `svp03-targeted-repro`:
   - reproduzir tecnicamente o caso `svp-03` / SSA `202604849`
   - provar se a falha e parser/base search, estado de filtros, dataset exibido ou stale UI
2. `filter-history-core`:
   - desenhar historico de filtros para `undo` e `redo` sem refactor amplo
3. `display-order-labels`:
   - agrupar emissor/executor, `Data do relatorio`, detalhes da SSA e demais ajustes pontuais de rotulo/ordem
4. `table-header-reorder`:
   - validar habilitacao minima de drag de colunas por cabecalho
5. `_sort_responsavel_values` ainda tem follow-up de performance para precomputacao/cache, mas isso ja e slice separado
6. `git-hygiene-rebase-residue`:
   - decidir em slice separado se o `.git\REBASE_HEAD` stale deve ser limpo manualmente
   - nao tratar esse residuo como prova de patch interrompido

### Plano de arranque na proxima conversa (obrigatorio)

1. rodar `git status --short`
2. ler pelo topo:
   - `AGENTS.md`
   - `docs/NEXT_CHAT_MIGRATION.md`
   - `docs/AGENTS_HANDOFF_NEXT_CYCLE.md`
   - `docs/RECOVERY_BACKLOG.md`
3. revisar comentarios/checks mais recentes do PR `dev -> main`
4. comecar por `svp03-targeted-repro` antes de abrir outro patch de filtros
5. executar a suite focada coerente com o slice:
   - busca/search: `uv run --python 3.13 python -m pytest -q tests/test_app_logic_filter_contract.py`
   - GUI/filtros: `uv run --python 3.13 python -m pytest -q tests/test_gui_filter_logic.py -k "executor or responsavel or solicitante"`
6. so depois abrir patch minimo com:
   - objetivo do slice
   - arquivos permitidos
   - arquivos proibidos

### Validacao relevante ja executada

1. hotfix de busca nao textual:
   - `py_compile`, `ruff`, `ty` -> verdes
   - `pytest -q tests/test_app_logic_filter_contract.py` -> `20 passed`
2. patch de sincronizacao de filtros:
   - `py_compile`, `ruff`, `ty` -> verdes
   - `pytest -q tests/test_gui_filter_logic.py -k "...executor...responsavel..."` -> `8 passed`
3. baseline amplo ainda referenciado dos docs vivos:
   - `uv run --python 3.13 python -m pytest -q tests` -> `993 passed, 4 skipped, 11 subtests passed`

## HISTORICAL SNAPSHOT 2026-03-27 20h35

- Leitura rapida:
  1. branch ativa: `dev`
  2. metadata local ativa: `4.37`
  3. ultima tag publicada em `dev`: `v4.36`
  4. os slices recentes de `numero_ssa`, importacao explicita, prova de update/query e bloqueio de downgrade por arquivo antigo ja foram aterrados e pushados
- PASSO 0 OBRIGATORIO NO PROXIMO CHAT:
  1. revisar os checks e comentarios mais recentes do PR `dev -> main`
  2. confirmar worktree limpo antes de abrir frente nova
  3. confirmar que o gate do Kluster esta disponivel antes do primeiro patch; se o review remoto oscilar, registrar o bloqueio exato
  4. continuar apenas pelos itens `P1/P2` com evidencia nova
  5. arquivos de referencia para esse passo:
     - `AGENTS.md`
     - `.github/instructions/kluster-code-verify.instructions.md`
     - `docs/CCR_LLM_PROVIDERS_SETUP.md`
     - `docs/OPENCODE_CONFIG.md`
     - `docs/README.md`
- Prioridade imediata:
  1. `P0`: manter fechado o contrato de `numero_ssa` sem reabrir truncagem ou regra paralela
  2. `P1`: revisar hotspots restantes da thread principal apos o sprint GUI entregue
  3. `P1`: decidir paridade CLI vs GUI para diff/full import e discovery
  4. `P1`: endurecimento residual de rollback/error boundary em `database*`
  5. `P1`: auditoria de testes viciados em dados/CLI
  6. `P2`: helper local de data e hardening residual de tooling/docs
- O que ja esta fechado:
  0. implementacao runtime do sprint GUI consolidada em `b343c621` e `07ebfe1d`
  1. drift de normalizacao no write path foi removido
  2. docs e testes foram alinhados ao contrato simplificado atual
  3. slices locais sujos foram aterrados
  4. `v4.36` ja foi publicada
  5. a prova de update de estado no banco agora existe no caminho de importacao explicita, diff e consulta/filtro
  6. arquivo mais antigo nao pode mais rebaixar estado novo no banco; isso ficou travado por teste
  7. `[f]` no cabecalho agora reflete filtros por coluna e filtros avancados equivalentes
  8. resumo `Filtros ativos` ja deduplica entradas equivalentes
  9. macro `Baixar` ja exclui `SAD`
  10. o prompt de filtro por coluna ganhou hint explicito e largura minima padronizada
  11. `update_derivadas_from_sources()` saiu do thread principal em runtime normal
  12. a caixa `Filtros ativos` ganhou borda destacada e texto em negrito quando ativa
  13. a barra superior ganhou `Abrir SAM`, a caixa `Status: X de Y SSAs` e `Semana Atual` centralizado
  14. a coluna `#` abre a SSA no SAM
  15. o detalhe da SSA expande `situacao`, copia o numero por duplo clique e mostra derivadas em arvore textual
  16. `load_other_database()` saiu da UI thread no runtime normal
  17. upsert nao-complementar passou a bloquear downgrade de `situacao` quando `data_cadastro` empata
  18. teste de regressao para `202600654` em empate de data foi adicionado no fluxo de importacao explicita
  19. dialogo de detalhes ganhou aba dedicada `Arvore` com subabas `Grafo`, `Arvore` e `Mermaid` (base: detalhes)
  19.1. historico: item promovido de refinamento para entrega por comando explicito no ciclo atual
  20. `_normalize_ssa_series` da tela de detalhes foi reotimizado por valores unicos para reduzir custo em massa
- O que ainda falta apos o sprint GUI:
  1. revisar staging/copy da importacao externa na thread principal
  2. revisar hotspots de render/refresh apos filtros
  3. validar no ambiente de operacao se a SSA `202600654` permanece `STE` apos ciclos parciais de atualizacao
  4. decidir se a aba `Grafo` precisa links clicaveis por no no proximo ciclo
- Integridade do contexto:
  1. nada foi perdido nesta reorganizacao documental
  2. historicos antigos continuam preservados abaixo como auditoria
  3. este arquivo deve servir como roteiro unico de migracao, nao como diario corrido
- Validacao atual confiavel:
  1. `py_compile` tracked -> verde
  2. `ruff check .` -> verde
  3. `ty check` -> verde
  4. `pytest -q tests` -> `993 passed, 4 skipped, 11 subtests passed`
- Regras e proibicoes que precisam ser carregadas para a proxima conversa:
  1. nao criar branch, PR, worktree, pasta ou tag sem autorizacao explicita
  2. nao editar nada antes de aprovar plano curto com objetivo, arquivos permitidos e arquivos proibidos
  3. nao misturar idiomas; comunicacao tecnica em PT-BR, codigo/comentarios em ASCII
  4. nao fazer refatoracao ampla, helper extra, mixin extra ou self-healing silencioso
  5. nao alterar layout/posicionamento de GUI sem pedido explicito
  6. usar `uv` para Python e `pnpm` para Node
  7. validar por slice com `py_compile`, `ruff`, `ty`, `pytest` focado
  8. rodar Kluster apos cada alteracao quando a ferramenta estiver funcional
- Regras para o proximo chat:
  1. nao criar tag nova antes de fechar backlog real e reviews externos
  2. nao reabrir operadores textuais legados de busca
  3. qualquer ajuste em `numero_ssa` deve partir da fonte central e vir com matriz de regressao do write path
- Arquivos autoritativos para a proxima conversa:
  1. `AGENTS.md`
  2. `README.md`
  3. `docs/README.md`
  4. `docs/NEXT_CHAT_MIGRATION.md`
  5. `docs/AGENTS_HANDOFF_NEXT_CYCLE.md`
  6. `docs/RECOVERY_BACKLOG.md`
  7. `docs/GUIA_DISTRIBUICAO.md`
  8. `.github/instructions/kluster-code-verify.instructions.md`
  9. `docs/CCR_LLM_PROVIDERS_SETUP.md`
  10. `docs/OPENCODE_CONFIG.md`
- Commits mais recentes desta frente:
  1. `194fc4e7` `STABILITY_PATCH: sync visual filter indicators`
  2. `cd06941f` `STABILITY_PATCH: improve column filter prompt`
  3. `31dc9c99` `STABILITY_PATCH: move derivadas sync off ui thread`
  4. `9983a757` `STABILITY_PATCH: tighten async import gui contract`
  5. `9da3eca0` push de follow-up do contrato assincrono ja publicado
  6. `b343c621` `STABILITY_PATCH: finish gui sam status and details sprint`
  7. `07ebfe1d` `STABILITY_PATCH: add visual derivadas graph tab`
- Estado do Kluster local:
  1. configuracao MCP local foi corrigida para `pnpm.CMD dlx ... --server=https://api.kluster.ai`
  2. se o review remoto voltar a dar timeout em `manualCheck`, tratar como bloqueio de ferramenta, nao como finding do repo
  3. Kluster continua obrigatorio como gate apos alteracoes
 - Estudo novo de organizacao documental:
  1. `docs/archive/LEGACY_DOCS_REORG_STUDY_20260327.md`

## HISTORICAL SNAPSHOT 2026-03-23 19h01

- Objetivo consolidado desta rodada:
  1. corrigir a regressao visivel de `<NA>` em tela introduzida apos a mudanca global de readback para nullable dtypes.
  2. fechar os vazamentos funcionais equivalentes em filtro por coluna, filtros avancados, derivadas e subset dependente de setores.
  3. fechar o diagnostico local do full rescan que no desktop de trabalho apareceu preso em `439` arquivos.
- Estado atual do git:
  1. branch ativa: `dev`.
  2. commits funcionais anteriores que originaram o contexto desta regressao:
     - `06a06e2f` `STABILITY_PATCH: keep nullable ints on DB reads`
     - `ef5c7680` `STABILITY_PATCH: keep numero_ssa storage canonical`
  3. commits funcionais que fecharam a regressao e a auditoria residual:
     - `d5a9e137` `HOTFIX_BLOCKER: fix nullable display and filter contract`
     - `25c64c58` `STABILITY_PATCH: close residual nullable filter paths`
  4. working tree local continua sujo fora de escopo e nao deve ser limpo automaticamente:
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
- Diagnostico consolidado desta rodada:
  1. a regressao do `<NA>` nao era de layout; era de contrato de dados:
     - [armazenamento/database.py](C:/Users/mauri/git/SSA_Consulta_Rapida/armazenamento/database.py) passou a usar `dtype_backend="numpy_nullable"`
     - isso fez `query_db()` devolver `pd.NA` e dtypes nullable em caminhos que antes entregavam `None`/`NaN`
     - [utils/formatting.py](C:/Users/mauri/git/SSA_Consulta_Rapida/utils/formatting.py) nao reconhecia `pd.NA`, entao a exibicao caia em `str(value)` e vazava `"<NA>"`
  2. o primeiro hotfix correto ficou no formatador central:
     - `pd.NA` agora e nullish e vira string vazia na camada de exibicao compartilhada entre GUI/CLI
  3. a matriz seguinte expôs um segundo efeito colateral funcional:
     - filtros e sort ainda tinham coercao textual crua via `astype(str)`
     - isso permitia que `pd.NA` virasse `"<NA>"` em match/sort internos
  4. o patch funcional principal desta rodada:
     - [gui/mixins/filter_gui_ssa_mixin.py](C:/Users/mauri/git/SSA_Consulta_Rapida/gui/mixins/filter_gui_ssa_mixin.py): filtro por coluna passa a usar `astype("string").fillna("")`
     - [gui/ssa/gui_filters_advanced_logic.py](C:/Users/mauri/git/SSA_Consulta_Rapida/gui/ssa/gui_filters_advanced_logic.py): filtros avancados idem
     - [gui/gui_ssa.py](C:/Users/mauri/git/SSA_Consulta_Rapida/gui/gui_ssa.py): sort de `num_reprogramacoes` agora trata `pd.NA` como vazio textual e usa numerico nullable coerente
  5. auditoria residual fechada em seguida:
     - [gui/ssa/gui_filters_advanced_logic.py](C:/Users/mauri/git/SSA_Consulta_Rapida/gui/ssa/gui_filters_advanced_logic.py): agrupamento de `derivada_all_ste` ignora `derivada_de` nullable/vazia
     - [gui/ssa/gui_filters_advanced_ui.py](C:/Users/mauri/git/SSA_Consulta_Rapida/gui/ssa/gui_filters_advanced_ui.py): subset dependente de setor evita `astype(str)` cru
  6. mudancas de contrato que permanecem intencionais:
     - `numero_ssa` segue textual/canonico
     - semanas e reprogramacoes seguem nullable inteiros no readback
     - render frio e salto para SSA continuam no contrato otimizado entregue nas rodadas anteriores
  7. diagnostico local do full rescan fechado, ainda sem alteracao de runtime:
     - o discovery atual usa `.xlsx` na raiz de `docs_entrada` e, opcionalmente, em `processadas/`
     - o pipeline principal ignora `.xls` legado por design
     - nesta maquina, a contagem real ficou:
       - `625` arquivos totais em `docs_entrada`
       - `489` arquivos `.xlsx` recursivos
       - `489` arquivos `.xlsx` elegiveis na raiz
       - `0` arquivos `.xlsx` em `processadas/`
       - `135` arquivos `.xls` ignorados pelo pipeline principal
     - `_get_files_to_process(..., force_import=True)` devolveu `489`
     - leitura atual: se o desktop de trabalho parou em `439`, a hipotese principal agora e corpus elegivel/discovery naquela maquina, nao lista/hash viciada
- Validacao relevante ja executada:
  1. `uv run --python 3.13 python -m py_compile utils/formatting.py tests/test_formatting.py gui/mixins/filter_gui_ssa_mixin.py gui/ssa/gui_filters_advanced_logic.py gui/gui_ssa.py tests/test_gui_filter_logic.py` -> pass.
  2. `uv run --python 3.13 ruff check utils/formatting.py tests/test_formatting.py gui/mixins/filter_gui_ssa_mixin.py gui/ssa/gui_filters_advanced_logic.py gui/gui_ssa.py tests/test_gui_filter_logic.py` -> pass.
  3. `uv run --python 3.13 ty check utils/formatting.py tests/test_formatting.py gui/mixins/filter_gui_ssa_mixin.py gui/ssa/gui_filters_advanced_logic.py gui/gui_ssa.py tests/test_gui_filter_logic.py` -> pass.
  4. `uv run --python 3.13 python -m pytest -q tests/test_formatting.py` -> `4 passed`.
  5. `uv run --python 3.13 python -m pytest -q tests/test_formatting.py tests/test_gui_filter_logic.py -k "nullable or num_reprogramacoes or column_filter or advanced_filter or format"` -> `32 passed, 142 deselected`.
  6. `uv run --python 3.13 python -m pytest -q tests/test_database.py tests/test_formatting.py -k "query_db or format"` -> `9 passed, 8 deselected`.
  7. `uv run --python 3.13 python -m pytest -q tests/test_gui_filters_advanced_logic.py` -> `16 passed`.
  8. `uv run --python 3.13 python -m pytest -q tests/test_gui_table_render_resilience.py` -> `11 passed`.
  9. `uv run --python 3.13 python -m pytest -q tests/test_gui_filters_advanced_logic.py tests/test_gui_filter_logic.py -k "derivada_all_ste or divisao or refresh_advanced_filter_options_excludes_na_literal_from_sector_values"` -> `4 passed, 183 deselected`.
  10. `uv run --python 3.13 python -m pytest -q tests/test_caching.py tests/test_import_run_report.py tests/test_import_derivadas_trigger.py tests/test_rescan_worker_advanced.py` -> `62 passed`.
  11. `uv run --python 3.13 python -m pytest -q tests/test_database.py tests/test_formatting.py tests/test_robust_importer.py tests/test_derivadas_sync.py` -> `50 passed`.
  12. `uv run --python 3.13 python -m pytest -q tests/test_gui_filters_advanced_logic.py tests/test_gui_table_render_resilience.py` -> `27 passed`.
  13. `uv run --python 3.13 python -m pytest -q tests/test_workers_advanced.py tests/test_main_streamlit_launcher.py tests/test_open_docs_folder_nonblocking.py tests/test_cli_loop_filter_rounds.py` -> `75 passed`.
  14. `uv run --python 3.13 python -m pytest -q tests/test_gui_filter_logic.py -k "refresh_advanced_filter_options_excludes_na_literal_from_sector_values or on_header_clicked_sorts_num_reprogramacoes_mixed_types or on_header_clicked_reuses_num_reprogramacoes_sort_cache or column_filter_treats_nullable_text_as_empty_instead_of_na_literal or advanced_filter_include_ignores_nullable_text_instead_of_na_literal or num_reprogramacoes_sort_keys_treat_nullable_values_as_empty_text or num_reprogramacoes_sort_rebuilds_stale_cache_with_mismatched_index"` -> `7 passed, 164 deselected`.
  15. `uv run --python 3.13 python -m pytest -q tests/test_gui_filter_logic.py` -> limitacao de harness neste ambiente; timeout seguido de `OSError: [Errno 22] Invalid argument` em `sys.stdout.flush()`, sem finding funcional novo do runtime.
- Leitura operacional:
  1. o erro desta rodada foi deixar um contrato novo de readback entrar sem fechar todos os callsites que stringificam valores faltantes.
  2. os caminhos centrais de exibicao e filtros relevantes ficaram alinhados.
  3. o proximo foco nao e mais nullable em tela; e decidir se o contrato de importacao deve continuar `root .xlsx only` ou se precisa ampliar discovery de forma explicita.

## HISTORICAL SNAPSHOT 2026-03-22 23h20

- Objetivo consolidado desta rodada:
  1. fechar o bug real do salto para SSA quando o alvo estava fora do `df_exibido` atual no fluxo assincrono.
  2. corrigir os dois regressos reais que a matriz ampla expôs durante a tentativa de hotfix.
  3. registrar a licao operacional: teste estreito de helper nao basta para fluxos que cruzam facade, mixin e detalhes.
- Estado atual do git:
  1. branch ativa: `dev`.
  2. commit funcional novo desta rodada:
     - `f03b9721` `HOTFIX_BLOCKER: stabilize async jump to SSA`
  3. working tree local continua sujo fora de escopo e nao deve ser limpo automaticamente:
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
- Diagnostico consolidado desta rodada:
  1. o bug real estava em [gui_details.py](C:/Users/mauri/git/SSA_Consulta_Rapida/gui/ssa/gui_details.py):
     - `_jump_to_ssa()` disparava `initiate_filtering()` quando o alvo nao estava no resultado atual
     - no caminho assincrono, a reavaliacao acontecia cedo demais e o salto se perdia
  2. a tentativa inicial de hotfix revelou dois regressos reais que a cobertura estreita nao pegou:
     - perda do contrato de decimal artifact em `_normalize_ssa_value("121911787.0")`
     - facade de [gui_ssa.py](C:/Users/mauri/git/SSA_Consulta_Rapida/gui/gui_ssa.py) sem aceitar o parametro interno `_allow_refilter`
  3. a correcao final entregue:
     - `filter_gui_ssa_mixin.py` consome um jump pendente apos `on_filter_finished()`
     - `gui_details.py` preserva o contrato funcional de normalizacao usado pela GUI
     - `gui_ssa.py` alinha o facade `_jump_to_ssa(...)` ao contrato interno do hotfix
  4. licao aprendida:
     - este fluxo cruza `gui_details.py`, `gui_table.py`, `gui_ssa.py` e `filter_gui_ssa_mixin.py`
     - teste de helper/call_count nao bastava; foi preciso matriz ampla + repro manual do fluxo assincrono real
- Validacao relevante ja executada:
  1. `uv run --python 3.13 python -m py_compile gui/gui_ssa.py gui/ssa/gui_details.py gui/mixins/filter_gui_ssa_mixin.py tests/test_gui_filter_logic.py tests/test_gui_table_render_resilience.py` -> pass.
  2. `uv run --python 3.13 ruff check gui/gui_ssa.py gui/ssa/gui_details.py gui/mixins/filter_gui_ssa_mixin.py tests/test_gui_filter_logic.py tests/test_gui_table_render_resilience.py` -> pass.
  3. `uv run --python 3.13 ty check gui/gui_ssa.py gui/ssa/gui_details.py gui/mixins/filter_gui_ssa_mixin.py tests/test_gui_filter_logic.py tests/test_gui_table_render_resilience.py` -> pass.
  4. `uv run --python 3.13 python -m pytest -q tests/test_gui_filter_logic.py tests/test_gui_table_render_resilience.py` -> `177 passed, 1 skipped`.
  5. repro manual do caso que tinha passado batido:
     - alvo fora do `df_exibido`
     - filtro assincrono
     - resultado final: `resolved=True`, `page=2`, `details_ssa=100157`, `selected_rows=[12]`, `pending_jump=None`

## HISTORICAL SNAPSHOT 2026-03-21 08h20

- Objetivo consolidado desta rodada:
  1. fechar o bug real de performance no refinamento sequencial do CLI.
  2. manter o escopo no `core`, sem reabrir parser, printer ou GUI.
  3. registrar o achado para o proximo ciclo sem misturar com a instrumentacao da GUI.
- Estado atual do git:
  1. branch ativa: `dev`.
  2. commit funcional novo desta rodada:
     - `ebebc1f7` `STABILITY_PATCH: drop inherited search cache in filtered dfs`
  3. working tree local continua sujo fora de escopo e nao deve ser limpo automaticamente:
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
- Diagnostico consolidado desta rodada:
  1. o gargalo dominante do repro `svp -> mel4` no CLI nao estava no parser nem no renderer ASCII.
  2. a causa real estava em [core/app_logic.py](C:/Users/mauri/git/SSA_Consulta_Rapida/core/app_logic.py):
     - `filter_dataframe()` devolvia subconjuntos com `_filter_search_cache` herdado do DataFrame original
     - o segundo refinamento reutilizava cache montado sobre `84592` linhas mesmo quando o subconjunto tinha `1117`
  3. o hotfix aplicado:
     - limpa attrs de cache no DataFrame retornado
     - centraliza token/cache/cleanup em `FilterSearchCacheManager`
     - reconstrui o cache no subconjunto correto no passo seguinte
  4. ganho medido no mesmo repro instrumentado:
     - antes: segundo filtro `mel4` apos `svp` na faixa de `11313 ms`
     - depois: segundo filtro `mel4` em `30.16 ms`
     - total da sequencia instrumentada caiu para `238.83 ms`
  5. a instrumentacao de GUI do slice anterior foi mantida, mas nao faz parte desta correcao de CLI.
- Validacao relevante ja executada:
  1. `uv run --python 3.13 python -m py_compile core/app_logic.py tests/test_app_logic_filter_contract.py` -> pass.
  2. `uv run --python 3.13 ruff check core/app_logic.py tests/test_app_logic_filter_contract.py` -> pass.
  3. `uv run --python 3.13 ty check core/app_logic.py tests/test_app_logic_filter_contract.py` -> pass.
  4. `uv run --python 3.13 python -m pytest -q tests/test_app_logic_filter_contract.py` -> `10 passed`.
  5. `uv run --python 3.13 python -m pytest -q tests/test_search_v_character.py tests/test_cli_loop_filter_rounds.py -k "svp or mel4 or parse_search_terms or remove_filter or back"` -> `7 passed, 25 deselected`.

## HISTORICAL SNAPSHOT 2026-03-21 00h20

- Objetivo consolidado desta rodada:
  1. fechar o slice local de UX do CLI para atalhos de filtro.
  2. medir com instrumentacao o custo real da pipeline de filtros da GUI.
  3. registrar propostas minimas para politica de render antes de editar runtime.
- Estado atual do git:
  1. branch ativa: `dev`.
  2. commit funcional novo desta rodada:
     - `19e68ba5` `STABILITY_PATCH: clarify CLI shortcuts and time filter refresh`
  3. working tree local continua sujo fora de escopo e nao deve ser limpo automaticamente:
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
- Diagnostico consolidado desta rodada:
  1. o contrato do CLI ficou ajustado:
     - `v` = voltar
     - `x <termo>` = remover termo
     - `x` sozinho agora mostra uso e nao volta
  2. a ajuda curta do CLI agora separa busca de comandos:
     - linha 1: busca
     - linha 2: comandos
  3. a lentidao percebida da GUI nao esta no parser:
     - o maior custo esta no render de `display_current_page(...)`
     - medido entre `~780 ms` e `~980 ms` por refresh nos cenarios principais
  4. custos secundarios medidos:
     - filtro por coluna na faixa `~68-78 ms`
     - exclusao `SCA/SES/STE` na faixa `~56-64 ms`
     - sincronizacao do combo rapido na faixa `~52-70 ms`
  5. medicao de refresh com banco real:
     - `svp_first`: total `1077 ms`, `render=973 ms`
     - `mel4_base`: total `1069 ms`, `render=978 ms`
     - `svp + MEL4 coluna`: total `1077 ms`, `render=916 ms`
     - `svp + MEL4 coluna + exclude`: total `998 ms`, `render=782 ms`
- Validacao relevante ja executada:
  1. `uv run --python 3.13 python -m py_compile interface/cli.py tests/test_cli_loop_filter_rounds.py gui/mixins/filter_gui_ssa_mixin.py` -> pass.
  2. `uv run --python 3.13 ruff check interface/cli.py tests/test_cli_loop_filter_rounds.py gui/mixins/filter_gui_ssa_mixin.py` -> pass.
  3. `uv run --python 3.13 ty check interface/cli.py tests/test_cli_loop_filter_rounds.py gui/mixins/filter_gui_ssa_mixin.py` -> pass.
  4. `uv run --python 3.13 python -m pytest -q tests/test_cli_loop_filter_rounds.py -k "help or prompt_hint or remove_filter or status_cli or toggle or enhanced or force_rescan or subprocess"` -> `19 passed, 11 deselected`.
- Leitura operacional para o proximo ciclo:
  1. o proximo slice util e de performance da politica de render, nao do parser.
  2. propostas minimas de politica de render:
     - render por delta visual quando so filtros mudam e a pagina continua a mesma
     - evitar re-render completo se `paginator.set_dataframe(...)` nao mudou a pagina efetiva
     - separar custo de tabela, resumo e sincronizacao para permitir early-exit barato
  3. nao reabrir parser do CLI para formas coladas; o contrato aprovado ficou `d #` e `x <termo>`.

## HISTORICAL SNAPSHOT 2026-03-20 17h25

- Objetivo consolidado deste ciclo:
  1. revisar a pilha real do CLI por subprocesso.
  2. corrigir hangs de fluxo basico sem refatoracao ampla.
  3. promover o baseline ativo para `v4.33`.
  4. fechar o micro-slice minimo do Streamlit e registrar achado ululante sem reabrir edicao de runtime maior.
- Estado atual do git:
  1. branch ativa: `dev`.
  2. commits principais deste ciclo:
     - `ec98013f` `STABILITY_PATCH: harden real CLI review flows`
     - `83660463` `STABILITY_PATCH: bump baseline to v4.33`
     - `c7992b39` `STABILITY_PATCH: align Streamlit title with v4.33`
     - `220e1847` `HOTFIX_BLOCKER: restore main streamlit launcher`
  3. working tree local continua sujo fora de escopo e nao deve ser limpo automaticamente:
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
- Diagnostico consolidado deste ciclo:
  1. o problema real do CLI nao era parser nem startup; era custo excessivo de renderizacao:
     - o printer formatava o DataFrame inteiro antes da paginacao
     - isso travava fluxos reais como `mel4 -> clear -> q`, `mel4 -> status-cli -> v -> q` e `mel4 -> m -> qq`
  2. a correcao adotada foi paginacao lazy:
     - preparar e renderizar so a pagina corrente
     - manter cache da pagina corrente para `l` e comandos invalidos
     - preservar o contrato de retomada com `m`
  3. o startup do CLI continua sem chamar rescan automatico.
  4. o CLI continua sem opcao de reescaneamento so de diff:
     - GUI tem diff/full rescan
     - CLI hoje tem apenas `rescan` / `force-rescan`
  5. furo ululante do launcher Streamlit foi corrigido:
     - [main.py](C:/Users/mauri/git/SSA_Consulta_Rapida/main.py) agora aponta para [dev_env/streamlit_app.py](C:/Users/mauri/git/SSA_Consulta_Rapida/dev_env/streamlit_app.py)
     - `uv run --python 3.13 python main.py --streamlit` voltou a subir o painel
- Micro-slice Streamlit entregue:
  1. [dev_env/streamlit_app.py](C:/Users/mauri/git/SSA_Consulta_Rapida/dev_env/streamlit_app.py) agora usa a versao ativa no `page_title` e no cabecalho
  2. [tests/test_streamlit_filter_cache.py](C:/Users/mauri/git/SSA_Consulta_Rapida/tests/test_streamlit_filter_cache.py) trava `SSA Consulta Rapida v4.33`
  3. [tests/test_main_streamlit_launcher.py](C:/Users/mauri/git/SSA_Consulta_Rapida/tests/test_main_streamlit_launcher.py) trava o launcher `main.py --streamlit`
- Validacao relevante ja executada:
  1. `uv run --python 3.13 python -m py_compile interface/enhanced_table_printer.py interface/cli.py interface/cli_enhancement_manager.py tests/test_cli_loop_filter_rounds.py tests/test_cli_pagination_prompt.py tests/test_build_multiplatform_manifest.py` -> pass.
  2. `uv run --python 3.13 ruff check interface/enhanced_table_printer.py interface/cli.py interface/cli_enhancement_manager.py tests/test_cli_loop_filter_rounds.py tests/test_cli_pagination_prompt.py tests/test_build_multiplatform_manifest.py` -> pass.
  3. `uv run --python 3.13 ty check interface/enhanced_table_printer.py interface/cli.py interface/cli_enhancement_manager.py tests/test_cli_loop_filter_rounds.py tests/test_cli_pagination_prompt.py tests/test_build_multiplatform_manifest.py` -> pass.
  4. `uv run --python 3.13 python -m pytest -q tests/test_cli_loop_filter_rounds.py tests/test_cli_pagination_prompt.py tests/test_table_printer.py tests/test_search_v_character.py tests/test_cli_get_ssa_query_identifier_guard.py` -> `44 passed`.
  5. `uv run --python 3.13 python -m pytest -q tests/test_build_multiplatform_manifest.py` -> `5 passed`.
  6. `uv run --python 3.13 python -m pytest -q tests/test_streamlit_filter_cache.py` -> `46 passed`.
  7. `uv run --python 3.13 python -m pytest -q tests/test_build_multiplatform_manifest.py tests/test_cli_loop_filter_rounds.py tests/test_streamlit_filter_cache.py` -> `77 passed`.
  8. `uv run --python 3.13 python -m pytest -q tests/test_main_streamlit_launcher.py` -> `2 passed`.
  6. subprocessos reais confirmados como `rc=0`:
     - `h -> q`
     - `mel4 -> q`
     - `mel4 -> clear -> q`
     - `mel4 -> status-cli -> v -> q`
     - `mel4 -> m -> qq`
     - `force-rescan -> q`
  7. launcher Streamlit real confirmado:
     - `uv run --python 3.13 python main.py --streamlit` -> sobe o painel em background
- Leitura operacional:
  1. `q` segue com semantica por escopo:
     - prompt principal: sai da aplicacao
     - paginacao: fecha a exibicao atual
     - `qq`: sai da aplicacao a partir da paginacao
  2. a principal lacuna restante do CLI nao e mais hang de fluxo basico; e cobertura/escopo funcional:
     - `_handle_rescan` continua grande demais
     - `ord` / `ordi` ainda merecem revisao de contrato
     - diff-only rescan ainda inexiste no CLI
- Pendencias e leitura para o proximo ciclo:
  1. fechar `DOC_SYNC` final da release e publicacao `v4.33`.
  2. decidir se o CLI deve ganhar comando de diff-only rescan.
  3. revisar `ord` / `ordi` contra ordem visual real.
  4. manter a politica de nao incluir residuos locais no commit.

## HISTORICAL SNAPSHOT 2026-03-20 14:00 - previous current truth

- Objetivo desta rodada:
  1. impedir que os testes CLI por subprocesso continuem sujando `config/cli_enhancements.json`.
  2. isolar persistencia de settings em arquivo temporario de teste.
  3. manter o caminho padrao do runtime intacto fora de testes.
- Estado atual do git:
  1. branch ativa: `dev`.
  2. working tree local continua sujo fora de escopo e nao deve ser limpo automaticamente:
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
  3. esse `M config/cli_enhancements.json` ja existia por testes anteriores; o slice atual evita novas sujeiras, mas nao faz rollback desse resido.
- Commit funcional novo desta rodada:
  1. `049b0b2e`
     - `CLIEnhancementManager` aceita override de arquivo por `SSA_CLI_ENHANCEMENTS_PATH`.
     - o override passa por validacao de path seguro.
     - subprocessos de teste usam arquivo temporario proprio.
- Diagnostico consolidado desta rodada:
  1. o resido em `config/cli_enhancements.json` vinha dos subprocessos que exercitavam `toggle-debug` e `enhanced-on/off`.
  2. o problema nao era logica do CLI em si:
     - era persistencia real em caminho fixo durante automacao
  3. a correcao exigia so um override seguro de caminho para teste.
- Validacao relevante ja executada:
  1. `uv run --python 3.13 python -m py_compile interface/cli_enhancement_manager.py tests/test_cli_loop_filter_rounds.py` -> pass.
  2. `uv run --python 3.13 ruff check interface/cli_enhancement_manager.py tests/test_cli_loop_filter_rounds.py` -> pass.
  3. `uv run --python 3.13 ty check interface/cli_enhancement_manager.py tests/test_cli_loop_filter_rounds.py` -> pass.
  4. `uv run --python 3.13 python -m pytest -q tests/test_cli_loop_filter_rounds.py -k "status_cli or toggle or enhanced or help or force_rescan or more_all or show_more or subprocess"` -> `13 passed, 9 deselected`.
- Pendencias e leitura para o proximo ciclo:
  1. `_handle_rescan` continua grande demais.
  2. `m`, `m z`, status e paginacao ainda merecem cobertura combinada de sessao longa.
  3. o resido ja existente em `config/cli_enhancements.json` continua fora de escopo ate voce decidir reverter explicitamente.
  4. manager de CLI ainda concentra texto de status e persistencia local em um bloco unico.

## HISTORICAL SNAPSHOT 2026-03-20 13:47 - previous current truth

- Objetivo desta rodada:
  1. impedir que `m z` trave a automacao do CLI por volume de saida.
  2. cobrir esse caso por subprocesso real.
  3. manter o `m` normal intocado.
- Estado atual do git:
  1. branch ativa: `dev`.
  2. working tree local continua sujo fora de escopo e nao deve ser limpo automaticamente:
     - `M .python-version`
     - `M config/gui_main_preferences.json`
     - `M data/ssas.db`
     - `M pyproject.toml`
     - `M requirements_build.txt`
     - `?? .backups/*`
     - `?? config/cli_enhancements.json.lock`
     - `?? docs_entrada/*.xlsx`
     - `?? *.bak.*`
  3. esses residuos continuam fora de escopo e nao devem ser revertidos por inferencia.
- Commit funcional novo desta rodada:
  1. `b796b6e5`
     - `m z` passa a falhar rapido em sessao non-interactive com mensagem clara.
     - testes novos travam:
       - recusa de `m z` no handler
       - subprocesso `mel4 -> m z -> q` encerrando limpo
- Diagnostico consolidado desta rodada:
  1. `m z` com banco real em pipe/non-interactive ainda causava timeout.
  2. o problema nao era quebra de loop:
     - era volume de saida excessivo em automacao
  3. o `m` normal seguia funcional; o alvo era so o `show_all`.
- Validacao relevante ja executada:
  1. `uv run --python 3.13 python -m py_compile interface/cli.py tests/test_cli_loop_filter_rounds.py` -> pass.
  2. `uv run --python 3.13 ruff check interface/cli.py tests/test_cli_loop_filter_rounds.py` -> pass.
  3. `uv run --python 3.13 ty check interface/cli.py tests/test_cli_loop_filter_rounds.py` -> pass.
  4. `uv run --python 3.13 python -m pytest -q tests/test_cli_loop_filter_rounds.py -k "more_all or show_more or status_cli or toggle or enhanced or help or force_rescan or subprocess"` -> `13 passed, 9 deselected`.
- Pendencias e leitura para o proximo ciclo:
  1. `_handle_rescan` continua grande demais.
  2. `m`, `m z`, status e paginacao ainda merecem mais cobertura combinada de sessao longa.
  3. o manager de CLI ainda concentra texto de status e persistencia local em um bloco unico.
  4. Kluster continua recomendando lotes pequenos para CLI grande.

## HISTORICAL SNAPSHOT 2026-03-20 13:33 - previous current truth

- Objetivo desta rodada:
  1. limpar a UX textual de `status-cli`, `toggle-debug` e `enhanced-on/off`.
  2. reduzir ruida visual do prompt principal do CLI.
  3. travar isso em subprocesso e testes unitarios pequenos.
- Estado atual do git:
  1. branch ativa: `dev`.
  2. working tree local continua sujo fora de escopo e nao deve ser limpo automaticamente:
     - `M .python-version`
     - `M config/gui_main_preferences.json`
     - `M data/ssas.db`
     - `M pyproject.toml`
     - `M requirements_build.txt`
     - `?? .backups/*`
     - `?? config/cli_enhancements.json.lock`
     - `?? docs_entrada/*.xlsx`
     - `?? *.bak.*`
  3. esses residuos continuam fora de escopo e nao devem ser revertidos por inferencia.
- Commit funcional novo desta rodada:
  1. `82d0465b`
     - `status-cli` passa a normalizar saida para ASCII.
     - `toggle-debug` e `enhanced-on/off` passam a responder com mensagens curtas e consistentes.
     - prompt principal do CLI fica mais compacto.
     - testes novos travam:
       - normalizacao ASCII do status
       - feedback compacto de debug/enhanced
       - subprocesso `status-cli -> q` com saida sem bullet unicode
- Diagnostico consolidado desta rodada:
  1. o fluxo estava correto, mas a UX textual ainda era ruim em captura real:
     - `status-cli` trazia bullets unicode e acentos
     - `toggle-debug` usava prefixo ruidoso `[Debug]`
     - o prompt principal ainda estava denso demais
  2. isso nao exigia refatoracao estrutural; so normalizacao e wrappers pequenos.
- Validacao relevante ja executada:
  1. `uv run --python 3.13 python -m py_compile interface/cli.py tests/test_cli_loop_filter_rounds.py` -> pass.
  2. `uv run --python 3.13 ruff check interface/cli.py tests/test_cli_loop_filter_rounds.py` -> pass.
  3. `uv run --python 3.13 ty check interface/cli.py tests/test_cli_loop_filter_rounds.py` -> pass.
  4. `uv run --python 3.13 python -m pytest -q tests/test_cli_loop_filter_rounds.py -k "status_cli or toggle or enhanced or help or force_rescan or subprocess"` -> `11 passed, 9 deselected`.
- Pendencias e leitura para o proximo ciclo:
  1. `_handle_rescan` continua grande demais.
  2. `status-cli` ainda depende de texto vindo do manager; o slice atual so limpou a borda de UX.
  3. `toggle-debug` ainda grava estado de config local; qualquer endurecimento adicional deve respeitar isso.
  4. `status-cli`, `toggle-debug` e `enhanced-on/off` ainda merecem cobertura mais ampla junto com `m`, `m z` e paginacao real.

## HISTORICAL SNAPSHOT 2026-03-20 13:18 - previous current truth

- Objetivo desta rodada:
  1. impedir que `rescan/force-rescan` trave sessao automatizada do CLI.
  2. reduzir o drift de densidade entre o help inicial e o help detalhado.
  3. manter o patch minimo antes do proximo refinamento maior do CLI.
- Estado atual do git:
  1. branch ativa: `dev`.
  2. working tree local continua sujo fora de escopo e nao deve ser limpo automaticamente:
     - `M .python-version`
     - `M config/gui_main_preferences.json`
     - `M data/ssas.db`
     - `M pyproject.toml`
     - `M requirements_build.txt`
     - `?? .backups/*`
     - `?? config/cli_enhancements.json.lock`
     - `?? docs_entrada/*.xlsx`
     - `?? *.bak.*`
  3. esses residuos continuam fora de escopo e nao devem ser revertidos por inferencia.
- Commit funcional novo desta rodada:
  1. `0f2f9a93`
     - `rescan/force-rescan` passam a retornar rapido com mensagem clara em `SSA_NON_INTERACTIVE=1` ou stdin sem TTY.
     - o help detalhado passa a declarar explicitamente que mantem o mesmo contrato da busca inicial.
     - testes novos travam:
       - consistencia textual do help detalhado
       - subprocesso `force-rescan -> q` encerrando limpo
- Diagnostico consolidado desta rodada:
  1. `force-rescan` em pipe/non-interactive ainda travava o harness e mascarava fluxo do CLI.
  2. o problema nao era parser nem renderer; era execucao pesada sem guarda de contexto.
  3. o help detalhado ainda repetia o contrato de busca com tom diferente do help inicial.
- Validacao relevante ja executada:
  1. `uv run --python 3.13 python -m py_compile interface/cli.py tests/test_cli_loop_filter_rounds.py` -> pass.
  2. `uv run --python 3.13 ruff check interface/cli.py tests/test_cli_loop_filter_rounds.py` -> pass.
  3. `uv run --python 3.13 ty check interface/cli.py tests/test_cli_loop_filter_rounds.py` -> pass.
  4. `uv run --python 3.13 python -m pytest -q tests/test_cli_loop_filter_rounds.py -k "help or force_rescan or subprocess"` -> `9 passed, 8 deselected`.
- Pendencias e leitura para o proximo ciclo:
  1. `_handle_rescan` ainda segue grande demais, apesar da guarda agora estar correta.
  2. `status-cli`, `toggle-debug` e comandos relacionados ainda merecem revisao de UX/texto no subprocesso real.
  3. consolidacao final de tom e densidade entre help inicial e help detalhado ainda pode ser refinada.
  4. Kluster segue oscilando por timeout em lotes grandes do CLI; manter lotes pequenos por slice.

## HISTORICAL SNAPSHOT 2026-03-20 12:55 - previous current truth

- Objetivo desta rodada:
  1. retirar `get_ssa_query()` da camada de UI/CLI.
  2. corrigir o help detalhado do CLI para nao quebrar sessao em modo pipe/non-interactive.
  3. manter o escopo restrito ao menor patch possivel antes do proximo refinamento do CLI.
- Estado atual do git:
  1. branch ativa: `dev`.
  2. working tree local continua sujo fora de escopo e nao deve ser limpo automaticamente:
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
  3. esses residuos continuam fora de escopo e nao devem ser revertidos por inferencia.
- Commit funcional novo desta rodada:
  1. `65351ef0`
     - `get_ssa_query()` sai de `interface/cli.py` e passa a morar em `armazenamento/database.py`.
     - `_handle_help()` deixa de bloquear stdin em `SSA_NON_INTERACTIVE=1` e em pipe sem TTY.
     - testes novos travam:
       - help sem pausa em modo non-interactive
       - subprocesso `h -> q` encerrando limpo
- Diagnostico consolidado desta rodada:
  1. o problema real do help nao era mais layout; era controle de fluxo:
     - o `input()` interno do help consumia o `q` do pipe
     - o loop principal recebia `EOFError` na rodada seguinte
  2. `get_ssa_query()` ainda vivia na camada de UI, apesar de ser contrato de acesso ao banco.
  3. a cobertura anterior nao pegava isso porque:
     - validava builder/fallback do help
     - nao validava o caminho real `h -> q` por subprocesso
- Validacao relevante ja executada:
  1. `uv run --python 3.13 python -m py_compile armazenamento/database.py interface/cli.py tests/test_cli_loop_filter_rounds.py tests/test_cli_get_ssa_query_identifier_guard.py` -> pass.
  2. `uv run --python 3.13 ruff check armazenamento/database.py interface/cli.py tests/test_cli_loop_filter_rounds.py tests/test_cli_get_ssa_query_identifier_guard.py` -> pass.
  3. `uv run --python 3.13 ty check armazenamento/database.py interface/cli.py tests/test_cli_loop_filter_rounds.py tests/test_cli_get_ssa_query_identifier_guard.py` -> pass.
  4. `uv run --python 3.13 python -m pytest -q tests/test_cli_get_ssa_query_identifier_guard.py tests/test_cli_loop_filter_rounds.py -k "get_ssa_query or help or force_rescan or subprocess"` -> `11 passed, 8 deselected`.
- Pendencias e leitura para o proximo ciclo:
  1. `_handle_rescan` segue grande demais.
  2. consolidacao final de tom e densidade entre help inicial e help detalhado segue pendente.
  3. `force-rescan` em sessao automatizada ainda merece guarda propria de UX antes de um ciclo maior de CLI.
  4. Kluster continua instavel por timeout no lote grande do CLI; esta rodada ficou limpa so em lote pequeno.

## HISTORICAL SNAPSHOT 2026-03-20 12:05 - previous current truth

- Objetivo desta rodada:
  1. revisar o CLI no ponto em que ele ainda estava defasado em help/menu e renderizacao estreita.
  2. alinhar o help completo ao contrato atual do runtime e eliminar o drift visual do box art.
  3. fechar cobertura real do `EnhancedTablePrinter` em terminal estreito.
- Estado atual do git:
  1. branch ativa: `dev`.
  2. working tree local continua sujo fora de escopo e nao deve ser limpo automaticamente:
     - `M .python-version`
     - `M config/gui_main_preferences.json`
     - `M data/ssas.db`
     - `M gui/gui_ssa.py`
     - `M pyproject.toml`
     - `M requirements_build.txt`
     - `?? .backups/*`
     - `?? docs_entrada/*.xlsx`
     - `?? *.bak.*`
  3. esses residuos continuam fora de escopo e nao devem ser revertidos por inferencia.
- Commits funcionais novos desta rodada:
  1. `43770be4`
     - help completo deixa de usar caixa hardcoded quebravel.
     - `force-rescan` vira alias real de `rescan` no loop do CLI.
     - testes novos travam:
       - help detalhado sem box art
       - largura maxima do help em 79 colunas
       - alias `force-rescan` funcional
  2. `3dd90c49`
     - `EnhancedTablePrinter` passa a respeitar terminal estreito sem impor largura minima 80.
     - `CLIWidthManager` passa a encolher colunas de texto ate piso minimo legivel quando houver deficit.
     - teste novo trava render real em terminal `70`.
- Diagnostico consolidado desta rodada:
  1. o startup do CLI continua correto:
     - nao chama `rescan` nem `run_importer_logic()` na abertura.
  2. o problema real estava em contrato e renderizacao:
     - help completo anunciava `force-rescan`, mas o loop nao tratava esse comando.
     - help completo em caixa tinha linhas de `79`, `82` e `88` caracteres para uma moldura base de `81`.
     - `EnhancedTablePrinter` ainda podia renderizar mais largo que o terminal estreito por causa de `max(terminal_width - 5, 80)`.
  3. cobertura anterior estava verde, mas ainda fraca em:
     - caminho normal do help completo
     - render em terminal estreito na camada enhanced
  4. erro operacional desta rodada:
     - houve tentativa incorreta de 2 commits em paralelo
     - o primeiro entrou e o segundo falhou por `index.lock`
     - isso foi corrigido seguindo a regra do repo: commits sequenciais
- Validacao relevante ja executada:
  1. `uv run --python 3.13 python -m py_compile interface/cli.py tests/test_cli_loop_filter_rounds.py interface/enhanced_table_printer.py interface/cli_width_manager.py tests/test_cli_pagination_prompt.py` -> pass.
  2. `uv run --python 3.13 ruff check interface/cli.py tests/test_cli_loop_filter_rounds.py interface/enhanced_table_printer.py interface/cli_width_manager.py tests/test_cli_pagination_prompt.py` -> pass.
  3. `uv run --python 3.13 ty check interface/cli.py tests/test_cli_loop_filter_rounds.py interface/enhanced_table_printer.py interface/cli_width_manager.py tests/test_cli_pagination_prompt.py` -> pass.
  4. `uv run --python 3.13 python -m pytest -q tests/test_cli_loop_filter_rounds.py tests/test_cli_pagination_prompt.py tests/test_table_printer.py tests/test_search_v_character.py` -> `24 passed`.
- Pendencias e leitura para o proximo ciclo:
  1. debt estrutural do CLI ainda aberto:
     - `_handle_rescan` segue grande
     - `get_ssa_query()` ainda mora no modulo de UI/CLI
  2. o help completo ja nao usa box art, mas ainda merece consolidacao final de tom e densidade com o help inicial.
  3. schema local segue sem `responsavel_solicitante`.
  4. termos curtos com escopo muito amplo na busca superior seguem como decisao de produto pendente.
  5. Kluster continuou em timeout no lote do CLI desta rodada; tratar como bloqueio de ferramenta, nao como clean absoluto.

## HISTORICAL SNAPSHOT 2026-03-20 11:32 - previous current truth

- Objetivo desta rodada:
  1. consolidar o contrato textual do CLI para nao voltar a divergir do runtime.
  2. confirmar no subprocesso que os fluxos antes suspeitos agora encerram normalmente.
  3. manter os debts estruturais de CLI isolados para proximos slices.
- Estado atual do git:
  1. branch ativa: `dev`.
  2. working tree local continua sujo fora de escopo e nao deve ser limpo automaticamente:
     - `M .python-version`
     - `M config/gui_main_preferences.json`
     - `M data/ssas.db`
     - `M gui/gui_ssa.py`
     - `M pyproject.toml`
     - `M requirements_build.txt`
     - `?? .backups/*`
     - `?? docs_entrada/*.xlsx`
     - `?? *.bak.*`
  3. esses residuos continuam fora de escopo e nao devem ser revertidos por inferencia.
- Commit funcional mais recente ja entregue:
  1. `067a05d3`
     - o help inicial e o fallback do help completo passam a consumir o mesmo texto compartilhado.
     - testes novos travam o contrato do texto compartilhado e o fallback do help.
  2. `6d29addf`
     - CLI passa a respeitar o contrato atual da busca superior e volta a reexibir dados em `v`.
- Diagnostico consolidado desta rodada:
  1. depois do hardening do loop, ainda havia duplicacao perigosa no help do CLI.
  2. essa duplicacao mantinha risco real de divergencia silenciosa entre:
     - help inicial
     - fallback sem unicode do help completo
  3. os repros por subprocesso para `clear`, `x mel4`, acumulacao e `v` agora encerram com `rc=0`.
- Validacao relevante ja executada:
  1. `uv run --python 3.13 python -m py_compile interface/cli.py tests/test_cli_loop_filter_rounds.py` -> pass.
  2. `uv run --python 3.13 ruff check interface/cli.py tests/test_cli_loop_filter_rounds.py` -> pass.
  3. `uv run --python 3.13 ty check interface/cli.py tests/test_cli_loop_filter_rounds.py` -> pass.
  4. `uv run --python 3.13 python -m pytest -q tests/test_cli_loop_filter_rounds.py tests/test_cli_config_preserve_session.py tests/test_cli_loop_missing_numero_ssa_guard.py tests/test_cli_remove_filter_non_lifo.py tests/test_cli_pagination_prompt.py tests/test_search_v_character.py` -> `18 passed`.
- Pendencias e leitura para o proximo ciclo:
  1. debt estrutural do CLI explicitamente fora deste slice:
     - `_handle_rescan` segue grande e misturando responsabilidades
     - help completo em caixa continua separado do texto plano compartilhado
     - `get_ssa_query()` ainda vive na camada de UI/CLI
  2. Kluster estourou timeout repetidamente no lote do CLI e nao devolveu findings adicionais apos o patch; tratar isso como bloqueio de ferramenta, nao como clean total garantido.
  3. schema local segue sem `responsavel_solicitante`.
  4. termos curtos com escopo muito amplo na busca superior seguem como decisao de produto pendente.

## HISTORICAL SNAPSHOT 2026-03-20 11:14 - previous current truth

- Objetivo desta rodada:
  1. estabilizar o loop interativo do CLI que ainda divergia do contrato atual da busca.
  2. fechar a regressao em que o CLI parava de exibir dados apos certas rodadas de filtro.
  3. registrar os debts estruturais do CLI separadamente, sem abrir refatoracao ampla neste slice.
- Commit funcional entregue:
  1. `6d29addf`
     - CLI passa a respeitar o contrato atual da busca superior.
     - `v` volta a reexibir o estado anterior.
     - exportacao, lookup direto e cache de render foram endurecidos.
- Validacao relevante:
  1. foco de CLI -> `16 passed`.

## HISTORICAL SNAPSHOT 2026-03-20 09:29 - previous current truth

- Objetivo desta rodada:
  1. tratar `SES` como equivalente funcional de `STE` nos filtros que usam essa classe terminal.
  2. ajustar a macro `Baixar` para excluir `SCA/SES/STE` e aceitar derivadas em `STE/SES`.
  3. registrar a avaliacao do atalho por triplo clique em limpar filtros sem implementa-lo neste slice.
- Estado atual do git:
  1. branch ativa: `dev`.
  2. working tree local continua sujo fora de escopo e nao deve ser limpo automaticamente:
     - `M .python-version`
     - `M config/gui_main_preferences.json`
     - `M data/ssas.db`
     - `M gui/gui_ssa.py`
     - `M pyproject.toml`
     - `M requirements_build.txt`
     - `?? .backups/*`
     - `?? docs_entrada/*.xlsx`
     - `?? *.bak.*`
  3. esses residuos continuam fora de escopo e nao devem ser revertidos por inferencia.
- Commits funcionais mais recentes ja entregues:
  1. `9b80344d`
     - trata `SES` como equivalente funcional de `STE` no macro `Baixar`, no filtro de derivadas terminais e na exclusao funcional `SCA/SES/STE`.
     - atualiza textos/resumo relacionados e adiciona testes de regressao para macro e exclusao funcional.
  2. `1c3709be`
     - adiciona `Opcoes > Limpar Filtros` como hard reset total de filtros.
  3. `2a1623bf`
     - upsert passa a logar troca de `setor_executor` quando a linha mais nova vence e muda o valor.
- Diagnostico consolidado desta rodada:
  1. `SES` nao ganhou semantica nova para o usuario; ele so entrou na mesma classe funcional terminal de `STE` nos filtros pedidos.
  2. a macro `Baixar` agora aplica:
     - `situacao` diferente de `SCA`, `SES` e `STE`
     - derivadas em `STE` ou `SES`
  3. a exclusao funcional legada `_exclude_ste_sca` continua com o mesmo nome interno por compatibilidade, mas o comportamento efetivo agora exclui `SCA/SES/STE`.
  4. o rotulo interno `derivada_all_ste` tambem foi mantido por compatibilidade, mas o comportamento efetivo agora cobre `STE/SES`.
- Validacao relevante ja executada:
  1. `uv run --python 3.13 python -m py_compile gui/ssa/gui_filters_advanced_logic.py gui/ssa/gui_filters_advanced_ui.py gui/mixins/filter_gui_ssa_mixin.py gui/gui_ssa.py tests/test_gui_filters_advanced_logic.py tests/test_gui_filter_logic.py` -> pass.
  2. `uv run --python 3.13 ruff check gui/ssa/gui_filters_advanced_logic.py gui/ssa/gui_filters_advanced_ui.py gui/mixins/filter_gui_ssa_mixin.py gui/gui_ssa.py tests/test_gui_filters_advanced_logic.py tests/test_gui_filter_logic.py` -> pass.
  3. `uv run --python 3.13 ty check gui/ssa/gui_filters_advanced_logic.py gui/ssa/gui_filters_advanced_ui.py gui/mixins/filter_gui_ssa_mixin.py gui/gui_ssa.py tests/test_gui_filters_advanced_logic.py tests/test_gui_filter_logic.py` -> pass.
  4. `uv run --python 3.13 python -m pytest -q tests/test_gui_filters_advanced_logic.py` -> `15 passed`.
  5. `uv run --python 3.13 python -m pytest -q tests/test_gui_filter_logic.py -k "macro_baixar or exclude_ste_sca_combined_with_or_group or filters_summary_shows_exclude_ste_sca_as_active_restriction or restore_last_filter_state_drops_hidden_lines_with_active_filters or clear_all_filters_global or hard_reset_filters_state or column_filter_buttons_flow"` -> `13 passed, 146 deselected`.
- Sugestoes e pendencias abertas:
  1. revisar outros pontos onde `STE` ainda e tratado isoladamente e pode merecer equivalencia com `SES`, especialmente:
     - ordenacao/priorizacao em `gui/workers/data_loader_worker.py`
     - labels/tooltips legados que ainda falem em `STE/SCA`
     - relatorios/exportacoes ou macros futuras que classifiquem "terminado" so por `STE`
  2. o atalho de triplo clique em botoes de limpar filtros e razoavel e barato de implementar, mas deve ficar como melhoria de UX separada:
     - contar 3 cliques consecutivos dentro de uma janela curta
     - abrir confirmacao para chamar o hard reset total
     - nao disparar reset silencioso
  3. schema local segue sem `responsavel_solicitante`.
  4. termos curtos com escopo muito amplo na busca superior seguem como decisao de produto pendente.

## HISTORICAL SNAPSHOT 2026-03-20 08:49 - previous current truth

- Objetivo desta rodada:
  1. sincronizar os docs com os ultimos slices funcionais ja entregues em `dev`.
  2. registrar o resultado do repro real `danilo, svp, mel4, !STE` no banco local atual.
  3. registrar a regra de upsert para troca de `setor_executor` em dado mais novo.
- Estado atual do git:
  1. branch ativa: `dev`.
  2. working tree local continua sujo fora de escopo e nao deve ser limpo automaticamente:
     - `M .python-version`
     - `M config/gui_main_preferences.json`
     - `M data/ssas.db`
     - `M gui/gui_ssa.py`
     - `M pyproject.toml`
     - `M requirements_build.txt`
     - `?? .backups/*`
     - `?? docs_entrada/*.xlsx`
     - `?? *.bak.*`
  3. esses residuos continuam fora do escopo dos slices abaixo e nao devem ser revertidos por inferencia.
- Commits funcionais mais recentes ja entregues:
  1. `fd2d9b09`
     - fecha handles SQLite antes da promocao do DB candidato no full rescan Windows.
  2. `3ea0881b`
     - trava em teste o contrato simplificado atual da busca superior.
  3. `2a1623bf`
     - upsert passa a logar troca de `setor_executor` quando a linha mais nova vence e muda o valor.
- Diagnostico consolidado desta rodada:
  1. repro real no banco local atual:
     - `danilo, svp, mel4, !STE` retorna `1` SSA no runtime atual.
     - o motivo e texto literal:
       - `danilo` em `responsavel_execucao`
       - `mel4` em `setor_executor`
       - `svp` em `descricao_ssa` (`SVP-04`)
       - `situacao` diferente de `STE`
  2. nao existe alias ativo `svp -> S/P` no runtime atual.
  3. `S/P` nao tem semantica especial no runtime atual.
  4. o schema local atual de `data/ssas.db` nao contem `responsavel_solicitante`.
  5. a logica de upsert aceita troca de `setor_executor` quando a linha nova e mais recente e agora registra isso em log de arquivo, sem alerta de UI e sem excecao.
- Validacao relevante ja executada:
  1. `uv run --python 3.13 python -m pytest -q tests/test_app_logic_filter_contract.py tests/test_search_v_character.py -k "svp or keeps_literals or default_search_columns or parse_search_terms"` -> `6 passed, 5 deselected`.
  2. `uv run --python 3.13 python -m pytest -q tests/test_upsert_behaviors.py -k "upsert_update_with_newer_date or upsert_ignore_older_date or upsert_existing_missing_date_new_has_date or upsert_both_missing_dates or upsert_existing_has_date_new_missing_does_not_update or setor_executor_change"` -> `7 passed, 2 deselected`.
  3. `uv run --python 3.13 python -m pytest -q tests/test_import_derivadas_trigger.py -k "run_importer_runs_db_only_sync_when_preflight_requires or run_importer_runs_db_only_derivadas_sync_for_regular_import or run_importer_runs_dedicated_derivadas_phase_even_without_regular_files"` -> `3 passed, 10 deselected`.
- Leitura objetiva para o proximo ciclo:
  1. o comportamento atual de `svp` e literal e esta coerente com o contrato vigente do `core`.
  2. se houver incomodo de produto com termo curto casando em descricao, isso virou decisao de escopo da busca superior, nao alias escondido.
  3. o backlog nao bloqueante agora e:
     - schema local sem `responsavel_solicitante`
     - termos curtos com escopo muito amplo na busca superior
     - comentarios/docstrings/configs mortos fora do runtime

## HISTORICAL SNAPSHOT 2026-03-19 15:49 - previous current truth

- Objetivo desta rodada:
  1. limpar a superficie morta de alias no core da busca superior sem reabrir semantica.
  2. separar claramente o contrato da busca superior vs filtro de coluna nos textos de ajuda.
  3. elevar a qualidade do gate local com verificadores extras e remover warnings ruidosos do pytest.
- Estado atual do git:
  1. branch ativa: `dev`.
  2. working tree local continua sujo fora de escopo e nao deve ser limpo automaticamente:
     - `M .python-version`
     - `M config/gui_main_preferences.json`
     - `M data/ssas.db`
     - `M requirements_build.txt`
     - `?? docs_entrada/*.xlsx`
     - `?? .backups/*`
     - `?? *.bak.*`
  3. `pyproject.toml` segue com diff misto local; o commit desta rodada deve separar apenas o delta desejado no stage.
- Diagnostico consolidado desta rodada:
  1. a busca superior no `core` nao deve aplicar alias, sinonimo nem reinterpretacao semantica.
  2. ainda existia legado morto no `core` sugerindo o contrario:
     - `get_filter_alias_map()`
     - `apply_filter_aliases()`
  3. o texto de ajuda ainda misturava busca geral e filtro de coluna como se fossem identicos.
  4. parte do ruido de qualidade vinha do ambiente e parte de config antiga:
     - `pytest` ainda avisava 4 chaves desconhecidas em `pyproject.toml`
     - `mypy/pylint/pylama` tinham ruido de setup/stubs alem de debt estrutural real do repo
- Mudancas aplicadas:
  1. `core/app_logic.py`
     - removidas as funcoes mortas `get_filter_alias_map()` e `apply_filter_aliases()`.
     - removida a docstring falsa dizendo que a busca superior aplicava alias.
  2. `tests/test_app_logic_filter_contract.py`
     - novo teste trava o contrato simplificado atual da busca superior.
  3. `tests/test_filter_alias_map_loading.py`
     - removido por cobrir apenas o legado morto do `core`
  4. `gui/widgets/filter_help_dialog.py`
     - texto agora separa explicitamente busca superior e fluxo de filtro por coluna.
  5. `gui/gui_ssa.py`
     - fallback de `get_app_version()` alinhado com a assinatura real
     - `_last_window_width` inicializado no `__init__`
     - cleanup pequeno para reduzir ruido de `ty`
  6. ambiente local de verificacao:
     - `pandas`, `openpyxl` e `PyQt6` confirmados na `.venv-win`
     - stubs e ferramentas extras instalados na `.venv-win`:
       - `pandas-stubs`
       - `PyQt6-stubs`
       - `mypy`
       - `pylint`
       - `pylama`
       - `setuptools<81`
  7. `pyproject.toml`
     - o delta desejado deste slice e apenas a remocao das 4 chaves antigas de pytest:
       - `module-root`
       - `tests-root`
       - `ignore-paths`
       - `formatter-cmds`
     - qualquer outro diff local no arquivo precisa ficar fora do commit.
- Validacao executada:
  1. `uv run --python 3.13 python -m py_compile core/app_logic.py tests/test_app_logic_filter_contract.py gui/widgets/filter_help_dialog.py gui/gui_ssa.py` -> pass.
  2. `uv run --python 3.13 ruff check core/app_logic.py tests/test_app_logic_filter_contract.py gui/widgets/filter_help_dialog.py gui/gui_ssa.py` -> pass.
  3. `uv run --python 3.13 ty check gui/gui_ssa.py gui/widgets/filter_help_dialog.py core/app_logic.py tests/test_app_logic_filter_contract.py` -> pass.
  4. `uv run --python 3.13 python -m pytest -q tests/test_app_logic_filter_contract.py tests/test_search_v_character.py` -> `10 passed`.
  5. `uv run --python 3.13 python -m pytest -q tests/test_app_logic_filter_contract.py tests/test_search_v_character.py tests/test_gui_filter_logic.py -k "search_help_texts_reflect_current_general_search_contract or filter_help_dialog_texts_separate_general_search_from_column_alternatives or test_v_character or test_no_logical_operators or default_search_columns or parse_search_terms_keeps_literals"` -> `9 passed, 157 deselected`.
  6. verificadores extras rodados com ambiente corrigido:
     - `mypy`
     - `pylint --errors-only`
     - `pylama`
     - `semgrep`
     - `qwen`
     - `kluster`
- Leitura objetiva dos verificadores extras:
  1. `mypy` e `pylama` agora rodam, mas expuseram debt estrutural antigo do repo fora deste slice.
  2. `pylint` deixou de acusar `_last_window_width` antes da definicao; restaram `E0611` ligados ao host/PyQt6.
  3. o principal ajuste funcional novo desta rodada ficou no texto de ajuda, nao no parser.
- Proximo passo:
  1. atualizar os docs de controle com esta verdade atual.
  2. separar o stage limpo de `pyproject.toml`.
  3. commitar e fazer push atomicamente.
  4. so depois abrir um novo slice para o backlog real revelado por `mypy/pylama`.

## HISTORICAL SNAPSHOT 2026-03-19 08:18 - previous current truth

- Objetivo desta rodada:
  1. corrigir o incidente grave de filtros GUI com slices A+B+C.
  2. fechar cobertura de contrato para impedir reintroducao rapida do defeito.
  3. registrar causa raiz, historico e regra nova de testes antes do proximo ciclo.
- Estado atual do git:
  1. branch ativa: `dev`.
  2. remoto localmente alinhado: `dev` e `origin/dev` sem divergencia observada no inicio do slice.
  3. working tree local continua sujo fora de escopo e nao deve ser limpo automaticamente:
     - `M .python-version`
     - `M config/gui_main_preferences.json`
     - `M data/ssas.db`
     - `M pyproject.toml`
     - `M requirements_build.txt`
     - `?? docs_entrada/*.xlsx`
- Incidente confirmado:
  1. busca geral ignorava campos humanos criticos.
  2. `cache_context` do filtro nao refletia o estado completo da GUI.
  3. botao `Ocultar` permitia filtro ativo invisivel.
  4. o sintoma de `clear nao funciona` era efeito combinado de cache parcial + filtro invisivel, nao ausencia de reset base.
- Causa raiz consolidada:
  0. ownership errado do contrato:
     - a GUI dependia implicitamente do default de `filter_dataframe(..., search_columns=None)`.
     - a lista de colunas da busca geral ficou escondida no core, em vez de existir como contrato explicito da GUI.
  1. `core/app_logic.py`
     - `priority_columns` nao incluia:
       - `solicitante`
       - `responsavel_solicitante`
       - `responsavel_programacao`
       - `responsavel_execucao`
  2. `gui/mixins/filter_gui_ssa_mixin.py`
     - `cache_context` incluia apenas `advanced_filters`.
     - faltavam `active_column_filters` e `exclude_ste_sca`.
  3. `gui/mixins/filter_gui_ssa_mixin.py`
     - `Ocultar` escondia a linha mantendo o filtro ativo.
- Historico de introducao provavel:
  1. buraco estrutural da busca:
     - base em `0c87e431`
     - lista consolidada sem os campos humanos em `e7ddea48`
  2. cache parcial:
     - introduzido em `ff266350`
     - mensagem: `fix(filter-cache): include advanced filter context in cache key`
  3. estado invisivel:
     - fluxo de hidden lines introduzido em `4df69305`
     - comportamento atual do `Ocultar` consolidado em `776c5905`
- Mudancas aplicadas:
  1. Slice A:
     - `priority_columns` expandido para incluir `solicitante` e `responsavel_*`.
     - testes de contrato reais com `danilo` e `mel4`.
  2. Slice B:
     - `cache_context` agora e deterministico e inclui:
       - `active_column_filters`
       - `advanced_filters`
       - `advanced_filters_active`
       - `exclude_ste_sca`
  3. Slice C:
     - `Ocultar` foi bloqueado quando existe filtro ativo na linha.
     - resumo segue expondo `exclude_ste_sca`.
  4. observacao de rastreabilidade:
     - este bloco DOC_SYNC registra mudancas de runtime ja presentes no mesmo working tree em:
       - `core/app_logic.py`
       - `gui/mixins/filter_gui_ssa_mixin.py`
       - `tests/test_app_logic_filter_contract.py`
       - `tests/test_filter_worker.py`
       - `tests/test_gui_filter_logic.py`
     - este diff de docs nao substitui o patch funcional; ele apenas sincroniza a verdade atual.
  5. segunda varredura:
     - `restore_last_filter_state` foi ajustado para nao reidratar filtro ativo invisivel via `hidden_column_filter_lines`.
     - a validacao ampliada tambem capturou um desalinhamento de altura no quick combo de `setor_executor`, ligado ao bloco estrutural de `c56d0e8e`.
  6. consolidacao posterior:
     - a GUI passou a ser dona explicita do contrato de colunas da busca geral.
     - o doc vivo da regra agora e `docs/GUI_GENERAL_SEARCH_COLUMN_CONTRACT.md`.
     - fuzzy search segue deferido para release futuro.
     - `gui/gui_ssa.py` passou a centralizar a aplicacao segura de alturas no toolbar e no sync inferior para evitar divergencia entre botoes, combo rapido e paineis.
- Validacao executada:
  1. `uv run --python 3.13 python -m py_compile` no escopo alterado -> pass.
  2. `uv run --python 3.13 ruff check` no escopo alterado -> pass.
  3. `uv run --python 3.13 ty check` no escopo alterado -> pass.
  4. `uv run --python 3.13 python -m pytest -q tests/test_app_logic_filter_contract.py` -> `7 passed`.
  5. `uv run --python 3.13 python -m pytest -q tests/test_filter_worker.py tests/test_gui_filter_logic.py -k "cache_context or column_filter_buttons_flow or filters_summary or clear_all_filters_global or exclude_ste_sca"` -> `15 passed`.
  6. `uv run --python 3.13 python -m pytest -q tests/test_app_logic_filter_contract.py tests/test_filter_worker.py tests/test_workers_advanced.py tests/test_gui_filter_logic.py` -> `204 passed, 1 skipped`.
  6. warnings remanescentes de pytest:
     - `formatter-cmds`
     - `ignore-paths`
     - `module-root`
     - `tests-root`
- Licao metodologica que virou regra:
  1. bug de filtros GUI reproduzivel em uso normal exige teste de jornada completa, nao apenas teste unitario local.
  2. a suite agora precisa cobrir, no minimo:
     - busca superior com dados reais de negocio
     - filtro de coluna
     - `exclude_ste_sca`
     - cache worker
     - `clear`
     - resumo
     - linha oculta
     - alinhamento funcional do quick toolbar quando novos controles entrarem na linha
- Proximo passo:
  1. revisar o diff atual.
  2. se aprovado, fazer commits atomicos por slice ou conforme estrategia definida pelo usuario.
  3. nao abrir novo escopo fora dos filtros sem confirmacao explicita.

## HISTORICAL SNAPSHOT 2026-03-17 00:30 - previous current truth

- Objetivo desta rodada:
  1. corrigir a semantica de status da importacao para rejeicoes deterministicas.
  2. eliminar mensagem falsa de falha global na GUI quando um arquivo esta fora do padrao esperado.
- Estado tecnico confirmado:
  1. cache atual existe em `data/file_cache.json` e esta funcional neste host.
  2. medicao local em `docs_entrada`: `431/431` arquivos em `metadata_match_skip`; diff atual selecionaria `0`.
  3. full e diff chegam corretamente ao worker:
     - `rescan_diff_data -> force_import=False`
     - `rescan_full_data -> force_import=True`
- Bug real confirmado:
  1. `bad-only diff`:
     - core retornava `status=no_success`
     - GUI concluia como `sem alteracoes`
  2. `bad-only full`:
     - core retornava `status=no_success`
     - GUI concluia como `falhou`
  3. ambos sao falsos para rejeicao esperada de arquivo fora do padrao.
- Decisao de patch minimo desta rodada:
  1. manter o algoritmo de cache intacto neste slice.
  2. introduzir status dedicado `deterministic_rejections_only` no core.
  3. ajustar o worker GUI para concluir com sucesso informativo nesse caso.
  4. travar comportamento em testes focados.
- Observacao estrutural que permanece:
  1. o cache e path-based; arquivos novos com nomes timestampados continuam sendo candidatos novos legitimos.

## HISTORICAL SNAPSHOT 2026-03-12 00:45 - previous current truth

- Objetivo desta rodada:
  1. consolidar relatorio unico com processo de build Windows/Linux/macOS nas 3 ferramentas.
  2. registrar de forma rastreavel: paths, limpeza, configuracoes, erros e status de atendimento de pedidos.
- Entrega principal:
  1. novo relatorio: `docs/BUILD_EXECUTION_AUDIT_20260311.md`.
  2. novo runbook operacional: `docs/BUILD_3X3_RUNBOOK.md`.
  3. sincronizacao dos docs de controle para apontar para este relatorio.
- Estado consolidado:
  1. branch ativa: `dev`.
  2. evidencia nova desta rodada:
     - `iscc` confirmado no host
     - instalador pyinstaller compilado com sucesso
     - `patchelf` instalado no WSL Debian 13
     - `build_nuitka_debian.sh` com melhoria de diagnostico e separacao GUI/CLI
  3. comandos canonicos do ciclo: sempre via `uv` com `--python 3.13`.
- Pendencias abertas para proximo ciclo:
  1. fechar validacao final de tempo/retorno do `build_nuitka_debian.sh --silent` no host.
  2. executar smoke final de release cross-platform apos novo build completo.

## HISTORICAL SNAPSHOT 2026-03-12 00:05 - previous current truth

- Objetivo desta rodada:
  1. registrar handover para continuar no Windows sem perder contexto do slice macOS finalizado.
  2. manter foco no proximo slice: scripts/build e tentativa de build no host Windows.
- Estado confirmado para migracao:
  1. branch alvo: `dev`.
  2. ultimo commit sincronizado: `05bbc2e1 STABILITY_PATCH: fix mac app launch, title/about, and icon-aligned rebuild docs`.
  3. artefatos macOS ja gerados no host atual:
     - `launchers/dist/macos_arm64/SSA_GUI_v4.32_macos_arm64.app`
     - `launchers/dist/macos_arm64/SSA_Consulta_Rapida_v4.32_macos_arm64.dmg`
  4. residuos locais fora de escopo (apenas desta maquina):
     - `M data/ssas.db`
     - `M docs/INDEX.md`
     - `?? config/settings.json.bak_20260308_212715`
- Regras operacionais para o proximo host (Windows):
  1. executar `git pull` em `dev` antes de editar.
  2. nao alterar runtime GUI/importacao sem plano aprovado por slice.
  3. priorizar somente scripts/build bloqueantes no Windows (sem sidequest).
  4. manter patch minimo e registrar decisoes nos 3 docs de controle.
- Checklist de arranque recomendado no Windows:
  1. `date '+%Y-%m-%d %H:%M:%S %z'` (ou equivalente PowerShell)
  2. `git status --short`
  3. `git branch --show-current`
  4. `git stash list | sed -n '1,10p'` (se aplicavel)
  5. reportar em 5 linhas: status, riscos, residuos, stashes, foco do slice.
- Observacao de sincronizacao:
  1. arquivos locais/stash podem divergir entre maquinas; confiar no que estiver commitado em `origin/dev`.
  2. se surgirem arquivos novos no Windows, validar escopo antes de incluir em commit.

## HISTORICAL SNAPSHOT 2026-03-11 00:36 - previous current truth

- Objetivo da rodada anterior:
  1. corrigir abertura do `.app` no macOS (duplo clique/Finder) sem fechamento imediato.
  2. garantir icone azul correto no `.app/.dmg` e manter nome da app.
  3. incluir versao no titulo da janela e menu `Sobre` com versoes de runtime.
- Correcoes aplicadas:
  1. `launchers/gui_entry.py`:
     - runtime frozen gravavel em user home.
     - seed de `config` empacotada para runtime local.
     - `cwd` movido para runtime para evitar erro em `logs`.
  2. `gui/gui_ssa.py`:
     - titulo atualizado para `Consulta Rapida de SSAs v<versao>`.
     - menu `Ajuda` com `Sobre` exibindo app/python/uv/pyqt/qt/pandas.
  3. build macOS:
     - `.app/.dmg` regenerados em `launchers/dist/macos_arm64`.
     - `CFBundleName` e `CFBundleDisplayName` = `Consulta Rapida de SSAs`.
     - `app_icon.icns` do bundle igual ao icone fonte.
- Evidencia da rodada anterior:
  1. `py_compile`, `ruff`, `ty` no escopo alterado -> pass.
  2. `pytest` focado -> `9 passed`.
  3. launch check com `cwd=/` -> `PROCESS_RUNNING`.
  4. titulo em runtime -> `Consulta Rapida de SSAs v4.32`.

## HISTORICAL SNAPSHOT 2026-03-10 22:52 - start from here

- Objetivo desta rodada:
  1. corrigir risco de stale lock no cache (`.lock` preso apos crash), apontado por cubic/copilot.
- Correcoes aplicadas:
  1. `utils/caching.py`
     - leitura de PID no lock file (`_read_lock_pid`).
     - check de processo vivo (`_is_process_alive`).
     - recuperacao de stale lock (`_recover_stale_cache_lock`) no ramo `FileExistsError`.
     - criterios:
       - remove lock com PID morto e idade minima.
       - remove lock sem PID apenas com idade de seguranca alta.
  2. `tests/test_caching_atomic_save.py`
     - teste para lock stale com PID morto (recupera e segue).
     - teste para lock ativo (nao remove e respeita timeout).
     - import de `pytest` e ajuste semantico de testes concorrentes.
- Evidencia de validacao:
  1. `uv run --python 3.13 python -m py_compile utils/caching.py tests/test_caching_atomic_save.py` -> pass.
  2. `uv run --python 3.13 ruff check utils/caching.py tests/test_caching_atomic_save.py` -> pass.
  3. `uv run --python 3.13 ty check utils/caching.py tests/test_caching_atomic_save.py` -> pass.
  4. `timeout 180s uv run --python 3.13 pytest -q tests/test_caching.py tests/test_caching_atomic_save.py` -> `17 passed`.
- Kluster desta rodada:
  1. `utils/caching.py`: 2 issues (HIGH+MEDIUM) de performance ampla, sem blocker funcional deste fix.
  2. `tests/test_caching_atomic_save.py`: HIGH (falta import pytest) corrigido; depois 1 MEDIUM semantico antigo; estado final tratado sem blocker.
- Decisao sobre comentario copilot em `install_hooks.sh`:
  1. comentario marcado como outdated/falso positivo para estado atual do arquivo.
  2. chamada ja esta agregada sem `exit` precoce via `install_failures`.
- Decisao intencional (cubic em `pre-push`):
  1. manter sem `--not --remotes`.
  2. motivo: evitar falso-negativo no gate de blob grande para alvo remoto.
  3. tradeoff aceito: possivel falso-positivo/perf maior em primeiro push.

## HISTORICAL SNAPSHOT 2026-03-10 22:41 - start from here

- Objetivo desta rodada:
  1. fechar 2 comentarios P2 do cubic nos hooks (`install_hooks.sh` e `pre-push`).
- Correcoes aplicadas:
  1. `scripts/install_hooks.sh`
     - chamadas de hooks agora validam os 2 obrigatorios no mesmo run.
     - falhas por hook sao acumuladas e reportadas ao final (sem `|| true` cego).
     - erros de `cp/chmod` passaram a gerar retorno explicito por hook.
  2. `scripts/git_hooks/pre-push`
     - removido `--not --remotes` para nao ocultar blob grande novo no alvo de push.
     - mantida tolerancia para range invalido (nao abortar push valido por um range ruim).
- Evidencia de validacao:
  1. `bash -n scripts/install_hooks.sh scripts/git_hooks/pre-push` -> pass.
  2. `kluster review file scripts/install_hooks.sh` -> clean.
  3. `kluster review file scripts/git_hooks/pre-push` -> 3 MEDIUM sem blocker novo.
- Classificacao:
  1. `BUG_REAL` corrigido:
     - risco de ocultar blob oversized no `pre-push`.
     - risco de falhar cedo no primeiro hook e perder relatorio completo no instalador.
  2. `NAO_BLOQUEANTE_DEFERIDO`:
     - `pre-push`: 3 MEDIUM (semantica/performance ampla do scan).

## HISTORICAL SNAPSHOT 2026-03-10 22:30 - start from here

- Objetivo desta rodada:
  1. fechar novo comentario de risco de concorrencia no cache sem refatoracao ampla.
- Correcoes aplicadas:
  1. `utils/caching.py`
     - introduzido lock sidecar (`<cache>.lock`) para serializar escrita entre processos.
     - `save_cache` agora grava sob lock exclusivo.
     - `get_files_to_process` passou a mesclar so updates diferenciais sob lock.
     - `update_cache_for_files` passou a usar merge sob lock (sem write cego de snapshot antigo).
  2. `tests/test_caching_atomic_save.py`
     - teste novo para validar lock file durante write e cleanup no final.
     - teste novo para validar merge concorrente de updates sem perda de entradas.
     - ajuste semantico de nome/expectativa no teste de `last writer wins` do `save_cache`.
- Resultado:
  1. comentario do copilot em `_cache_key_for_file` segue coberto pelo commit anterior `0b8705a2`.
  2. risco real de lost update concorrente no cache foi mitigado no fluxo de merge.
- Evidencia de validacao:
  1. `uv run --python 3.13 python -m py_compile utils/caching.py tests/test_caching_atomic_save.py` -> pass.
  2. `uv run --python 3.13 ruff check utils/caching.py tests/test_caching_atomic_save.py` -> pass.
  3. `uv run --python 3.13 ty check utils/caching.py tests/test_caching_atomic_save.py` -> pass.
  4. `timeout 180s uv run --python 3.13 pytest -q tests/test_caching.py tests/test_caching_atomic_save.py` -> `15 passed`.
- Kluster desta rodada:
  1. `utils/caching.py`: 3 MEDIUM (debt de naming/decomposicao/perf), sem blocker novo.
  2. `tests/test_caching_atomic_save.py`: clean apos ajuste semantico.

## HISTORICAL SNAPSHOT 2026-03-10 22:23 - start from here

- Objetivo desta rodada:
  1. corrigir comentarios novos de bot (cubic/copilot) em hooks e cache, sem refatoracao ampla e sem mudanca de layout/GUI.
- Correcoes aplicadas:
  1. `scripts/install_hooks.sh`
     - removido mascaramento `|| true` nas chamadas obrigatorias de `install_named_hook`.
  2. `scripts/git_hooks/pre-push`
     - coleta de objetos por range com tolerancia a range invalido (nao aborta push valido).
     - adicionado `--not --remotes` para reduzir scan de objetos ja conhecidos.
     - `git cat-file --batch-check` ajustado para TAB real no formato de saida.
  3. `utils/caching.py`
     - `_cache_key_for_file` trocado para excecoes especificas (`ValueError`, `OSError`, `RuntimeError`) com `logger.debug` no fallback.
- Evidencia de validacao:
  1. `uv run --python 3.13 python -m py_compile utils/caching.py` -> pass.
  2. `uv run --python 3.13 ruff check utils/caching.py` -> pass.
  3. `uv run --python 3.13 ty check utils/caching.py` -> pass.
  4. `timeout 180s uv run --python 3.13 pytest -q tests/test_caching.py tests/test_caching_atomic_save.py` -> `13 passed`.
  5. `bash -n scripts/install_hooks.sh scripts/git_hooks/pre-push` -> pass.
  6. reproducao manual do `cat-file --batch-check` com TAB real -> `oid, blob, size, path` preenchidos.
- Kluster nesta rodada:
  1. clean em `scripts/install_hooks.sh`.
  2. no `pre-push`, HIGH inicial foi confirmado e corrigido (`%x09` literal).
  3. MEDIUM remanescentes no `pre-push` e `utils/caching.py` classificados como debt de semantica/performance fora deste patch minimo.
- Estado local confirmado:
  1. branch: `codex/sprint-importacao-grave-fixes-20260305`.
  2. ultimo commit antes deste slice: `6ebe448e`.
  3. residuos fora de escopo mantidos:
     - `M data/ssas.db`
     - `?? config/settings.json.bak_20260308_212715`

## HISTORICAL SNAPSHOT 2026-03-10 22:03 - start from here

- Objetivo desta rodada:
  1. refresh completo de status para migracao de conversa, sem editar runtime.
- Estado local confirmado:
  1. branch: `codex/sprint-importacao-grave-fixes-20260305`.
  2. ultimo commit: `30500374 STABILITY_PATCH: fechar rodada bot (hooks pre-push ascii worker)`.
  3. residuos fora de escopo:
     - `M data/ssas.db`
     - `?? config/settings.json.bak_20260308_212715`
  4. stashes abertos:
     - `stash@{0}` `wip-before-return-import-branch-20260308_011343`
     - `stash@{1}` `incident-freeze-before-reapply-20260305-083301`
     - `stash@{2}` `local-wip-config-db-before-dev-switch-20260303`
- Estado de PR/checks:
  1. PR `#45` aberto, `mergeStateStatus=UNSTABLE`.
  2. threads abertas: `0`.
  3. checks com falha: `CodeFactor`, `code/snyk` (limit), `security/snyk` (limit).
  4. checks pendentes: `cubic`, `semgrep-cloud-platform/scan`.
- Decisao operacional:
  1. nao houve alteracao de codigo/runtime nesta rodada.
  2. manter foco em fechamento de PR #45 sem ampliar escopo.
- Proximo passo sugerido no novo chat:
  1. revalidar checks pendentes.
  2. se `cubic/semgrep` voltarem limpos e sem novos comentarios bloqueantes, seguir para merge.

## HISTORICAL SNAPSHOT 2026-03-10 21:42 - start from here
- Priority note (nao perder no proximo chat):
  1. debt BLE001 no restante do codigo continua alto e deve entrar no proximo ciclo curto.
  2. contagem atual: `860`.
  3. comando: `ruff check . --select BLE001`.
  4. hotspots iniciais: `armazenamento/database*.py`, `core/app_logic.py`, `core/config_manager.py`, `dev_env/streamlit_app.py`.
  5. estado de PR: `#45` aberto, `0` threads abertas; checks externos ainda bloqueando merge (`CodeFactor`, `code/snyk`, `security/snyk`).

- Slice aplicado:
  1. fechamento de nova rodada de comentarios bot (codereviewbot/copilot/codeant) com patch minimo.
- Arquivos alterados:
  1. `scripts/install_hooks.sh`
  2. `scripts/git_hooks/pre-push`
  3. `tests/test_robust_importer.py`
  4. `README.md`
  5. `gui/workers/data_loader_worker.py`
  6. `docs/RECOVERY_BACKLOG.md`
  7. `docs/NEXT_CHAT_MIGRATION.md`
  8. `docs/AGENTS_HANDOFF_NEXT_CYCLE.md`
- Resultado tecnico:
  1. `install_hooks.sh` agora marca hook ausente como erro obrigatorio e falha no final.
  2. `pre-push` preserva `oid + path` e mostra caminho real ao bloquear blob grande.
  3. `test_robust_importer.py` ficou 100% ASCII na fonte (escapes unicode em cabecalhos de teste).
  4. `README.md` linha apontada por copilot normalizada para ASCII.
  5. `DataLoaderWorker` agora captura tambem `pd.errors.DatabaseError` no handler superior.
- Gates desta rodada:
  1. `py_compile`, `ruff`, `ty` no escopo alterado -> pass.
  2. `pytest -q tests/test_robust_importer.py tests/test_data_loader_worker.py` -> `23 passed`.
  3. `bash -n scripts/install_hooks.sh scripts/git_hooks/pre-push` -> pass.
- Deferido:
  1. kluster em `pre-push`: custo sincrono de varredura grande (tradeoff intencional de seguranca no hook).
  2. kluster em `data_loader_worker`: debts antigos de semantica/performance fora deste patch, incluindo recalculo de `non_null_cols` por carregamento.
  3. kluster em `README`: contradicao historica de texto (slice documental dedicado).

## HISTORICAL SNAPSHOT 2026-03-10 16:37 - start from here

- Slice aplicado:
  1. hardening de tratamento de erro para zerar `BLE001` em `main.py` e `data_loader_worker.py`.
- Arquivos alterados:
  1. `main.py`
  2. `gui/workers/data_loader_worker.py`
  3. `docs/RECOVERY_BACKLOG.md`
  4. `docs/NEXT_CHAT_MIGRATION.md`
  5. `docs/AGENTS_HANDOFF_NEXT_CYCLE.md`
- Resultado tecnico:
  1. `except Exception` amplos removidos dos 2 arquivos alvo.
  2. `ruff --select BLE001` no escopo alvo ficou limpo.
  3. fluxo de importacao em `main` e fluxo de carregamento em `DataLoaderWorker` mantidos.
- Gates desta rodada:
  1. `py_compile`, `ruff`, `ty` no escopo alterado -> pass.
  2. `pytest -q tests/test_data_loader_worker.py tests/test_main_import_fallback.py tests/test_main_skip_import.py tests/test_main_gui_fallback.py` -> `17 passed`.
- Deferido:
  1. debts antigos de arquitetura/performance e semantica historica em `main.py` e `data_loader_worker.py`.

## HISTORICAL SNAPSHOT 2026-03-10 15:53 - start from here

- Slice aplicado:
  1. estabilizacao dos testes focados de `main` para nao travar em loop CLI durante pytest.
  2. ajuste final da faixa de filtros: `Setor Executor` com label externo + valor simples na combo.
  3. reposicionamento de `Colunas Visiveis` ao lado de `Linhas por Pagina`.
- Arquivos alterados:
  1. `tests/test_main_import_fallback.py`
  2. `tests/test_main_skip_import.py`
  3. `gui/gui_ssa.py`
  4. `tests/test_gui_filter_logic.py`
  5. `docs/RECOVERY_BACKLOG.md`
  6. `docs/NEXT_CHAT_MIGRATION.md`
  7. `docs/AGENTS_HANDOFF_NEXT_CYCLE.md`
- Resultado tecnico:
  1. `test_main_import_fallback` agora cobre o caminho correto (`--force-rescan`) sem stdin.
  2. contrato de prioridade do CLI ficou explicito em teste: `--force-rescan` sobrepoe `--skip-import`.
  3. quick filter de `setor_executor` nao altera `setor_emissor`.
  4. combo rapido exibe apenas setor (`Todos`, `IEE3`, `MEL4`) com label externo fixo.
  5. `remove_column_by_index` ganhou guarda de indice para evitar remocao errada/out-of-range.
- Gates desta rodada:
  1. `py_compile`, `ruff`, `ty` no escopo alterado -> pass.
  2. `pytest -q tests/test_main_import_fallback.py tests/test_main_skip_import.py tests/test_gui_filter_logic.py` -> `152 passed, 1 skipped`.
- Deferido:
  1. debts historicos de arquitetura/performance em `gui/gui_ssa.py` fora de escopo.
  2. alinhamento semantico global de tooltip de busca geral (fora deste slice).

## HISTORICAL SNAPSHOT 2026-03-10 15:29 - start from here

- Slice aplicado:
  1. reorganizacao da barra de filtros na aba Filtros conforme UX aprovada.
  2. remocao do botao superior `Atualizar Derivadas` (acao mantida no menu Database).
- Arquivos alterados:
  1. `gui/gui_ssa.py`
  2. `tests/test_gui_filter_logic.py`
  3. `docs/RECOVERY_BACKLOG.md`
  4. `docs/NEXT_CHAT_MIGRATION.md`
  5. `docs/AGENTS_HANDOFF_NEXT_CYCLE.md`
- Resultado tecnico:
  1. `Salvar Filtro` agora fica na mesma linha de `Pesquisa Geral`.
  2. tooltip de `Salvar Filtro` explicita que salva somente o filtro de busca geral.
  3. `Colunas Visiveis` + `Setor Executor` migraram para a linha de paginacao.
  4. `Setor Executor` segue no canto direito com ajuste leve de largura/altura para conforto visual.
  5. botao superior de derivadas saiu da barra sem remover fluxo de menu.
- Gates desta rodada:
  1. `py_compile`, `ruff`, `ty` no escopo alterado -> pass.
  2. `pytest` focado (5 testes) -> `5 passed`.
- Deferido:
  1. debts historicos de performance/arquitetura no `gui/gui_ssa.py` fora do escopo de patch minimo.

## HISTORICAL SNAPSHOT 2026-03-10 15:17 - start from here

- Slice aplicado:
  1. hardening de fallback GUI em `main.py` com escopo minimo.
  2. novo teste focado para evitar regressao de mascaramento de erro na importacao GUI.
- Arquivos alterados:
  1. `main.py`
  2. `tests/test_main_gui_fallback.py`
  3. `docs/RECOVERY_BACKLOG.md`
  4. `docs/NEXT_CHAT_MIGRATION.md`
  5. `docs/AGENTS_HANDOFF_NEXT_CYCLE.md`
- Resultado tecnico:
  1. fallback para CLI ocorre apenas em `ImportError` no import tardio GUI.
  2. erros inesperados de importacao GUI nao ficam silenciosos (encerram com `SystemExit=1`).
  3. setup de icone e criacao de janela GUI mantem fallback CLI apenas para falha operacional (`OSError`, `RuntimeError`).
- Gates desta rodada:
  1. `py_compile`, `ruff`, `ty` no escopo alterado -> pass.
  2. `pytest -q tests/test_main_gui_fallback.py tests/test_main_skip_import.py::test_main_skip_import_does_not_call_importer` -> `3 passed`.
- Deferido:
  1. debts antigos de arquitetura em `main.py` fora do trecho de bootstrap GUI.
  2. testes legados de `main` que hoje disparam importacao real sem isolamento.

## HISTORICAL SNAPSHOT 2026-03-10 14:54 - start from here

- Slice aplicado:
  1. fix de bug real em `import_external_excel_files` para compatibilidade com window-stub sem helper de destino.
  2. fix de seguranca no empacotamento: `build_dir/config` agora respeita ignore de sensiveis.
- Arquivos alterados:
  1. `gui/gui_ssa.py`
  2. `scripts/create_distribution.py`
  3. `tests/test_create_distribution.py`
  4. `docs/RECOVERY_BACKLOG.md`
  5. `docs/NEXT_CHAT_MIGRATION.md`
  6. `docs/AGENTS_HANDOFF_NEXT_CYCLE.md`
- Resultado tecnico:
  1. `import_external_excel_files` nao falha mais com `AttributeError` quando chamado com objeto leve sem `_build_unique_destination_path`.
  2. distribuicao nao inclui `.db/.xlsx/.xls` vindos de `build_dir/config`.
  3. cobertura de teste nova para esse caminho de configuracao foi adicionada.
- Gates desta rodada:
  1. `py_compile`, `ruff`, `ty` no escopo alterado -> pass.
  2. `pytest -q tests/test_gui_menu_import_external.py` -> `13 passed`.
  3. `pytest -q tests/test_create_distribution.py` -> `18 passed`.
- Deferido:
  1. debts antigos de qualidade/performance em `gui/gui_ssa.py` seguem fora de escopo deste hotfix.

## HISTORICAL SNAPSHOT 2026-03-10 14:44 - start from here

- Slice aplicado:
  1. correcao de bug real no robust importer para mapeamento semantico `SN/SN.1`.
  2. hardening no `RescanWorker` para nao mascarar full-rescan com falha como sucesso.
- Arquivos alterados:
  1. `utils/robust_importer.py`
  2. `gui/workers/rescan_worker.py`
  3. `tests/test_rescan_worker_advanced.py`
  4. `docs/RECOVERY_BACKLOG.md`
  5. `docs/NEXT_CHAT_MIGRATION.md`
  6. `docs/AGENTS_HANDOFF_NEXT_CYCLE.md`
- Resultado tecnico:
  1. `SN -> sn_retirado` e `SN.1 -> sn_instalado` no robust importer (alinhado com o extrator principal e com testes).
  2. full-rescan com `success=False` no worker agora diferencia:
     - no-op sem contexto de arquivos (`total=0`) -> sucesso sem alteracoes;
     - ciclo com arquivos (`total>0`) ou erro observado -> erro final.
  3. o worker marca erro observado via:
     - evento `file_error` do callback;
     - observer no `LogHandler` para logs `ERROR+`.
- Gates desta rodada:
  1. `py_compile`, `ruff`, `ty` no escopo alterado -> pass.
  2. `pytest -q tests/test_robust_importer.py tests/test_rescan_worker_advanced.py tests/test_rescan_worker_cleanup.py` -> `41 passed`.
- Deferido:
  1. comentarios de debt semantico/performance em `RescanWorker` para introducao de sinal dedicado (`finished_no_changes`) e throttling de logs ficam para slice dedicado.

## HISTORICAL SNAPSHOT 2026-03-10 14:31 - start from here

- Slice aplicado:
  1. fechamento do refactor minimo em `core/app_logic.py` para reduzir complexidade de orquestracao sem mudar contrato funcional.
  2. correcao de runtime (`cast` importado) e correcao de regressao no full-rescan com DB candidato ausente.
- Arquivos alterados:
  1. `core/app_logic.py`
  2. `docs/RECOVERY_BACKLOG.md`
  3. `docs/NEXT_CHAT_MIGRATION.md`
  4. `docs/AGENTS_HANDOFF_NEXT_CYCLE.md`
- Resultado tecnico:
  1. `run_importer_logic` passou a delegar fases para helpers especificos de processamento, sync derivadas e promocao.
  2. fluxo de promocao de DB candidato ficou explicito (`candidate -> primary`) e sem ambiguidade de parametros.
  3. full-rescan agora inicializa DB candidato explicitamente quando necessario antes da verificacao/reparo.
  4. suite de derivadas em full-rescan voltou a passar em cenarios mockados sem materializacao implicita de arquivo.
- Gates desta rodada:
  1. `py_compile`, `ruff`, `ty` em `core/app_logic.py` -> pass.
  2. `pytest -q tests/test_import_derivadas_trigger.py` -> `13 passed`.
  3. `pytest -q tests/test_app_logic_full_rescan_lock.py tests/test_import_derivadas_trigger.py tests/test_import_run_report.py tests/test_app_logic_postprocess_moves.py tests/test_import_cache_integrity.py` -> `27 passed`.
- Deferido:
  1. debts antigos de performance/arquitetura no bloco de filtro (`filter_dataframe`) e custo de rotacao WAL sincrona.

## HISTORICAL SNAPSHOT 2026-03-10 13:58 - start from here

- Slice aplicado:
  1. ajuste pontual do combo rapido de setor executor no topo (largura + texto popup/display).
  2. fix de icone no startup GUI (`python main.py --gui`) com aplicacao no `QApplication`.
- Arquivos alterados:
  1. `gui/gui_ssa.py`
  2. `main.py`
  3. `tests/test_gui_filter_logic.py`
  4. `docs/RECOVERY_BACKLOG.md`
  5. `docs/NEXT_CHAT_MIGRATION.md`
  6. `docs/AGENTS_HANDOFF_NEXT_CYCLE.md`
- Resultado tecnico:
  1. popup do setor executor exibe apenas valores curtos (`Todos`, `IEE3`, `MEL4`).
  2. combo fechado mostra `Setor Executor: <valor>` para manter contexto visual.
  3. largura do combo ficou limitada para evitar ocupacao excessiva na barra superior.
  4. icone passa a ser aplicado no `QApplication` no startup GUI e tambem no bloco da janela.
- Gates desta rodada:
  1. `py_compile`, `ruff`, `ty` no escopo alterado -> pass.
  2. `pytest` focado do combo rapido -> pass.
  3. smoke offscreen -> `window_icon_null=False`, `app_icon_null=False`.
- Deferido:
  1. debts antigos de arquitetura/performance em `gui/gui_ssa.py` (fora do escopo de patch minimo).

## HISTORICAL SNAPSHOT 2026-03-10 13:45 - start from here

- Slice aplicado:
  1. triagem final das threads do PR #45, uma a uma.
  2. encerradas threads com status `CORRIGIDO`, `FALSO_POSITIVO`, `NAO_BLOQUEANTE_DEFERIDO` e ruido `RATE_LIMIT_REPLY`.
  3. mantidas abertas apenas as threads `BUG_REAL`.
- Resultado no PR:
  1. aberto antes: `65` threads.
  2. encerradas nesta rodada: `56`.
  3. aberto apos triagem: `9` threads.
- Threads que ficaram abertas (todas `BUG_REAL`):
  1. `armazenamento/database_upsert_logic.py:407`
  2. `armazenamento/database_upsert_logic.py:951`
  3. `armazenamento/database_upsert_logic.py:743`
  4. `armazenamento/database_validation.py:61`
  5. `armazenamento/database_validation.py` (thread sem linha fixa)
  6. `extracao/extractor.py:536`
  7. `gui/ssa/gui_theme.py:458`
  8. `gui/ssa/gui_workers.py:239`
  9. `gui/workers/rescan_worker.py:169`
- Estado de checks no momento da triagem:
  1. `quality-gates` e `CodeQL`: pass.
  2. `code/snyk` e `security/snyk`: fail por limite/conta.
  3. `DeepScan`, `DeepSource Python`, `cubic`, `semgrep`: pendentes.

## HISTORICAL SNAPSHOT 2026-03-10 12:45 - start from here

- Slice aplicado:
  1. fechamento de pendencias reais do PR #45 sem alterar GUI/layout.
  2. hardening do hook de tamanho para blob staged (index), evitando bypass.
  3. ajuste do pipeline macOS para build `cli-only` com `package=dmg` sem falha falsa por ausencia de `.app`.
  4. normalizacao de docs para manter 1 unico bloco `CURRENT TRUTH`.
- Arquivos alterados:
  1. `scripts/git_hooks/pre-commit`
  2. `launchers/build_multiplatform.py`
  3. `tests/test_build_multiplatform_manifest.py`
  4. `docs/RECOVERY_BACKLOG.md`
  5. `docs/NEXT_CHAT_MIGRATION.md`
  6. `docs/AGENTS_HANDOFF_NEXT_CYCLE.md`
- Resultado tecnico:
  1. pre-commit agora mede tamanho do blob staged via `git cat-file -s`.
  2. `post_process` recebe `apps` e pula DMG quando build macOS nao inclui GUI.
  3. teste de regressao adicionado para esse fluxo (`cli-only` + `package=dmg`).
- Gates desta rodada:
  1. `py_compile`, `ruff`, `ty` no escopo alterado -> pass.
  2. `pytest -q tests/test_build_multiplatform_manifest.py tests/test_create_distribution.py` -> `22 passed`.
  3. `bash -n scripts/git_hooks/pre-commit` -> pass.
- Deferido:
  1. debt antigo de naming/performance/concentracao no `build_multiplatform.py` fica para slice dedicado.
  2. alerta kluster de `pip_exe` foi falso positivo (inicializacao ja existe no inicio da funcao).

## HISTORICAL SNAPSHOT 2026-03-10 12:13 - start from here

- Slice aplicado:
  1. icone oficial trocado para variante azul com `SSA` central e sem raio.
  2. artefatos oficiais cross-OS regenerados (`svg/png/ico/icns`).
- Arquivos alterados:
  1. `resources/app_icon.svg`
  2. `resources/app_icon.png`
  3. `resources/app_icon.ico`
  4. `resources/app_icon.icns`
  5. `docs/RECOVERY_BACKLOG.md`
  6. `docs/NEXT_CHAT_MIGRATION.md`
  7. `docs/AGENTS_HANDOFF_NEXT_CYCLE.md`
- Resultado operacional:
  1. `app_icon.png` em `1024x1024`.
  2. `app_icon.ico` multi-size valido para Windows.
  3. `app_icon.icns` valido para macOS.
  4. `app_icon.svg` mantido como fonte canonica para Linux/build.
- Observacao tecnica:
  1. `cairosvg` do venv ainda falha por bind nativo de `cairo`.
  2. para este slice, geracao foi feita por `rsvg-convert` + `Pillow` + `iconutil`.
- Gates desta rodada:
  1. `py_compile`, `ruff`, `ty` em scripts de build/icon -> pass.
  2. `pytest -q tests/test_build_multiplatform_manifest.py` -> `4 passed`.
- Deferido:
  1. hardening do `convert_icon.py` para fallback automatico sem dependencia de `cairosvg`.
  2. variacoes em `resources/icon_variants/*` ficam como material de design.

## HISTORICAL SNAPSHOT 2026-03-10 12:02 - start from here

- Slice aplicado:
  1. pipeline macOS agora gera `.dmg` no `build_multiplatform.py`, alem de `.app`/onedir.
  2. sem mudanca de GUI/runtime de negocio; foco exclusivo em build/distribuicao macOS.
- Arquivos alterados:
  1. `launchers/build_multiplatform.py`
  2. `launchers/platforms/macos_arm64/build_config.json`
  3. `tests/test_build_multiplatform_manifest.py`
  4. `docs/RECOVERY_BACKLOG.md`
  5. `docs/NEXT_CHAT_MIGRATION.md`
  6. `docs/AGENTS_HANDOFF_NEXT_CYCLE.md`
- Resultado operacional real:
  1. comando executado:
     - `uv run --python 3.13 python launchers/build_multiplatform.py --platform macos_arm64 --apps cli gui --skip-venv`
  2. saida validada:
     - `.dmg`: `launchers/dist/macos_arm64/SSA_Consulta_Rapida_v4.32_macos_arm64.dmg`
     - `.app`: `launchers/dist/macos_arm64/SSA_GUI_v4.32_macos_arm64.app`
     - onedir CLI/GUI preservados.
- Gates desta rodada:
  1. `py_compile`, `ruff`, `ty` -> pass.
  2. `pytest -q tests/test_build_multiplatform_manifest.py` -> `4 passed`.
- Deferido:
  1. pyoxidizer/nuitka continuam fora do pipeline operacional de release neste ciclo.
  2. assinatura/notarizacao macOS permanece pendente para ciclo dedicado de release.

## HISTORICAL SNAPSHOT 2026-03-10 11:51 - start from here

- Slice aplicado:
  1. remocao dos `try/except` proibidos restantes (`pass` e `continue`) em GUI/worker.
  2. patch minimo, sem alteracao de layout e sem mudanca de comportamento de negocio.
- Arquivos alterados:
  1. `gui/gui_ssa.py`
  2. `gui/workers/data_loader_worker.py`
  3. `docs/RECOVERY_BACKLOG.md`
  4. `docs/NEXT_CHAT_MIGRATION.md`
  5. `docs/AGENTS_HANDOFF_NEXT_CYCLE.md`
- Resultado tecnico:
  1. `gui/gui_ssa.py`: bloco `except ... pass` removido do combo rapido; leitor de report agora usa excecoes especificas com log e sem `continue` dentro de `except`.
  2. `data_loader_worker.py`: fallback de colunas nao nulas mantido com log debug, sem `except ... continue`.
  3. `bandit` nos dois arquivos nao reporta mais `B110/B112`.
- Gates desta rodada:
  1. `py_compile`, `ruff`, `ty` no escopo alterado -> pass.
  2. `pytest` focado -> `2 passed, 157 deselected`.
  3. `bandit` focado -> apenas alertas antigos de subprocess/SQL dinamico com sanitizacao.
- Leitura de risco:
  1. alerta kluster sobre assinatura de `query_db` em DataLoaderWorker e falso positivo:
     - assinatura real aceita `(db_path, table_name, query, params, raise_on_error)` em `armazenamento/database.py`.
  2. debts antigos de arquitetura/performance em `gui_ssa.py` continuam deferidos.

## HISTORICAL SNAPSHOT 2026-03-10 11:26 - start from here

- Slice aplicado:
  1. hotfix de build/runtime macOS para executavel util (sem erro de modulo ausente por exclusao de stdlib).
  2. hardening de hooks para bloqueio de arquivo grande (staged e push).
  3. ajuste de quick filter `setor_executor` com sync de UI no painel avancado e prefixo de rotulo.
  4. commit evidencia: `338614c6`.
- Resultado operacional:
  1. build `macos_arm64` (CLI+GUI) completou com sucesso apos reduzir exclusoes agressivas.
  2. erro `No module named 'concurrent'` deixou de ocorrer.
  3. erros subsequentes (`html`, `email`) tambem resolvidos removendo exclusoes stdlib.
  4. manifesto de build agora lista diretorios reais (inclui `.app`) e ignora hidden.
- Hooks:
  1. novo `scripts/git_hooks/pre-push` bloqueia blobs >= 95MB.
  2. `scripts/git_hooks/pre-commit` agora bloqueia staged >= 95MB.
  3. `scripts/install_hooks.sh` instala hooks de forma deterministica e seta `core.hooksPath=.git/hooks`.
- GUI/filtros:
  1. combo rapido exibe itens como `Setor Executor: <valor>`.
  2. ao mudar quick filter, UI de `Executor` em filtros avancados reflete o mesmo valor (inclusive apos troca de aba/refresh), sem persistir em `_advanced_filters`.
  3. `import_external_excel_files` usa apenas helper de instancia para destino unico (sem fallback ambigio via classe).
- Robustez adicional:
  1. calculo de tamanho de diretorio no manifesto ignora symlink para evitar ciclo.
- Arquivos tocados:
  1. `launchers/build_multiplatform.py`
  2. `launchers/platforms/macos_arm64/build_config.json`
  3. `launchers/platforms/windows_amd64/build_config.json`
  4. `launchers/platforms/debian_amd64/build_config.json`
  5. `scripts/git_hooks/pre-commit`
  6. `scripts/git_hooks/pre-push`
  7. `scripts/install_hooks.sh`
  8. `README.md`
  9. `gui/gui_ssa.py`
  10. `gui/ssa/gui_filters_advanced_ui.py`
  11. `tests/test_gui_filter_logic.py`
  12. `tests/test_build_multiplatform_manifest.py`
  13. `docs/RECOVERY_BACKLOG.md`
  14. `docs/NEXT_CHAT_MIGRATION.md`
  15. `docs/AGENTS_HANDOFF_NEXT_CYCLE.md`
- Gates desta rodada:
  1. `py_compile`, `ruff`, `ty` no escopo alterado -> pass.
  2. `pytest` focado (`quick_setor_executor...` + manifesto build) -> pass.
  3. build real macOS + smoke runtime -> sem `ModuleNotFoundError` de stdlib excluida.
- Deferido:
  1. debts estruturais antigos do kluster em `build_multiplatform` e `gui_ssa` (fora de escopo de patch minimo).
- Residuos locais fora de escopo mantidos:
  1. `data/ssas.db`
  2. `config/settings.json.bak_20260308_212715`

## HISTORICAL SNAPSHOT 2026-03-10 10:38 - start from here

- Slice aplicado:
  1. pente fino completo de build/distribuicao para `pyinstaller`, `nuitka`, `pyoxidizer`, `pytoexe`.
  2. correcoes de script para viabilizar pacote pyinstaller no host macOS atual.
  3. docs operacionais alinhados com status real das tools e backends.
- Resultado operacional real:
  1. `pyinstaller --skip-installer` -> OK (ZIP gerado em `dist_packages/SSA_Consulta_Rapida_v4.32_pyinstaller.zip`).
  2. `pyinstaller` -> ZIP OK, installer FAIL (sem origem Windows/Inno no host atual).
  3. `nuitka --skip-installer` -> FAIL (build ausente em `builds/nuitka`).
  4. `pyoxidizer --skip-installer` -> FAIL (build ausente em `builds/pyoxidizer`).
  5. `pytoexe` -> nao suportado (choice invalida no parser).
- Ferramentas detectadas:
  1. `pyinstaller` 6.19.0
  2. `nuitka` 4.0.1
  3. `pyoxidizer` 0.24.0
  4. `iscc` ausente
  5. `pytoexe/py2exe` ausentes
- Evidencia local:
  1. `/tmp/ssa_pack_audit_20260310_1030/summary.log`
- Arquivos tocados:
  1. `scripts/create_distribution.py`
  2. `tests/test_create_distribution.py`
  3. `docs/GUIA_DISTRIBUICAO.md`
  4. `docs/BUILD_PYINSTALLER_GUIA_COMPLETO.md`
  5. `docs/BUILD_NUITKA_GUIA_COMPLETO.md`
  6. `docs/BUILD_PYOXIDIZER_GUIA_COMPLETO.md`
  7. `docs/RECOVERY_BACKLOG.md`
  8. `docs/NEXT_CHAT_MIGRATION.md`
  9. `docs/AGENTS_HANDOFF_NEXT_CYCLE.md`
- Gates desta rodada:
  1. kluster clean nos arquivos tocados.
  2. `py_compile`, `ruff`, `ty` -> pass.
  3. `pytest -q tests/test_create_distribution.py` -> `17 passed`.
- Deferido:
  1. validar installer em host Windows com ISCC e build `windows_amd64` disponivel.
- Residuos locais fora de escopo mantidos:
  1. `data/ssas.db`
  2. `config/settings.json.bak_20260308_212715`

## HISTORICAL SNAPSHOT 2026-03-10 10:15 - start from here

- Slice aplicado:
  1. fechamento dos 3 itens que estavam em loop (ISS Source, reason de resolve, concentracao ZIP).
  2. `scripts/create_distribution.py`:
     - `_resolve_inno_source` usa `exe_path` de forma consistente.
     - `create_inno_setup_script` simplificado com helpers de path/excludes/template.
     - `Source` do ISS agora usa macro `SourceDir` explicita.
  3. `tests/test_create_distribution.py`:
     - asserts atualizados para `SourceDir` e mode `absolute`.
     - novo teste para pyoxidizer consumir `exe_path` em `_resolve_inno_source`.
- Arquivos tocados:
  1. `scripts/create_distribution.py`
  2. `tests/test_create_distribution.py`
  3. `docs/RECOVERY_BACKLOG.md`
  4. `docs/NEXT_CHAT_MIGRATION.md`
  5. `docs/AGENTS_HANDOFF_NEXT_CYCLE.md`
- Gates desta rodada:
  1. kluster em script -> clean.
  2. kluster em testes -> clean.
  3. `py_compile`, `ruff`, `ty` -> pass.
  4. `pytest -q tests/test_create_distribution.py` -> `16 passed`.
- Deferido:
  1. validar em Windows/ISCC real (confirmacao final de ambiente).
- Residuos locais fora de escopo mantidos:
  1. `data/ssas.db`
  2. `config/settings.json.bak_20260308_212715`

## HISTORICAL SNAPSHOT 2026-03-10 10:08 - start from here

- Slice aplicado:
  1. reforco de testes para alinhar `resolve` vs `failure_reason` em pyinstaller.
  2. runtime de distribuicao nao foi alterado neste micro-slice.
- Arquivos tocados:
  1. `tests/test_create_distribution.py`
  2. `docs/RECOVERY_BACKLOG.md`
  3. `docs/NEXT_CHAT_MIGRATION.md`
  4. `docs/AGENTS_HANDOFF_NEXT_CYCLE.md`
- Gates desta rodada:
  1. kluster em `tests/test_create_distribution.py` -> clean.
  2. `py_compile`, `ruff`, `ty` -> pass.
  3. `pytest -q tests/test_create_distribution.py` -> `15 passed`.
- Deferido:
  1. validacao Windows/ISCC real para path `Source` no `.iss`.
  2. continuar fatiamento de concentracao em `create_zip_package` e `create_inno_setup_script`.
- Residuos locais fora de escopo mantidos:
  1. `data/ssas.db`
  2. `config/settings.json.bak_20260308_212715`

## HISTORICAL SNAPSHOT 2026-03-10 10:05 - start from here

- Slice aplicado:
  1. modularizacao minima no fluxo ZIP e define explicito de `SourcePath` no `.iss`.
  2. `scripts/create_distribution.py`:
     - novos helpers: `_copy_runtime_bundle`, `_write_package_version_file`, `_create_package_zip`.
     - `create_zip_package` simplificado para orquestracao.
     - tipagem de `build_name` normalizada para `str`.
     - template Inno recebeu `#define SourcePath "<DIST_OUTPUT resolvido>"`.
  3. `tests/test_create_distribution.py`:
     - asserts adicionados para validar `#define SourcePath` em cenario relative e absolute.
- Arquivos tocados:
  1. `scripts/create_distribution.py`
  2. `tests/test_create_distribution.py`
  3. `docs/RECOVERY_BACKLOG.md`
  4. `docs/NEXT_CHAT_MIGRATION.md`
  5. `docs/AGENTS_HANDOFF_NEXT_CYCLE.md`
- Gates desta rodada:
  1. kluster em `scripts/create_distribution.py` -> 3 issues (1 HIGH sem repro local + 2 MEDIUM antigos).
  2. kluster em `tests/test_create_distribution.py` -> clean.
  3. `py_compile`, `ruff`, `ty` -> pass.
  4. `pytest -q tests/test_create_distribution.py` -> `13 passed`.
- Deferido:
  1. validar path absoluto/relativo de `Source` com ISCC real em Windows.
  2. alinhar razao de falha entre `_resolve_build_directory` e helper de failure reason.
  3. continuar reducao de concentracao em `create_zip_package`.
- Residuos locais fora de escopo mantidos:
  1. `data/ssas.db`
  2. `config/settings.json.bak_20260308_212715`

## HISTORICAL SNAPSHOT 2026-03-10 09:59 - start from here

- Slice aplicado:
  1. `compile_installer` foi reduzido em concentracao com extracao minima de blocos.
  2. `scripts/create_distribution.py`:
     - novo `_get_iscc_path()` para descoberta/validacao de caminho.
     - novo `_run_iscc_compile(...)` para execucao do compilador.
     - `compile_installer(...)` mantido com mesmo contrato e mesmos status.
- Arquivos tocados:
  1. `scripts/create_distribution.py`
  2. `docs/RECOVERY_BACKLOG.md`
  3. `docs/NEXT_CHAT_MIGRATION.md`
  4. `docs/AGENTS_HANDOFF_NEXT_CYCLE.md`
- Gates desta rodada:
  1. kluster em `scripts/create_distribution.py` -> 1 issue (`create_zip_package` longa, debt antigo fora de escopo).
  2. `py_compile`, `ruff`, `ty` -> pass.
  3. `pytest -q tests/test_create_distribution.py` -> `13 passed`.
- Deferido:
  1. debt de qualidade em `create_zip_package` segue para ciclo dedicado.
- Residuos locais fora de escopo mantidos:
  1. `data/ssas.db`
  2. `config/settings.json.bak_20260308_212715`

## HISTORICAL SNAPSHOT 2026-03-10 09:55 - start from here

- Slice aplicado:
  1. modo de origem do Inno ficou explicito no `.iss` via `SourcePathMode`.
  2. `scripts/create_distribution.py`:
     - `source_path_mode` agora e `relative` por padrao e `absolute` quando `os.path.relpath(...)` falha.
     - template recebeu `#define SourcePathMode "{source_path_mode}"`.
  3. testes:
     - assert de `SourcePathMode "relative"` no cenario de relpath normal.
     - assert de `SourcePathMode "absolute"` no cenario de fallback.
- Arquivos tocados:
  1. `scripts/create_distribution.py`
  2. `tests/test_create_distribution.py`
  3. `docs/RECOVERY_BACKLOG.md`
  4. `docs/NEXT_CHAT_MIGRATION.md`
  5. `docs/AGENTS_HANDOFF_NEXT_CYCLE.md`
- Gates desta rodada:
  1. kluster em `scripts/create_distribution.py` -> 3 issues (1 semantico intencional + 2 debts fora de escopo).
  2. kluster em `tests/test_create_distribution.py` -> clean.
  3. `py_compile`, `ruff`, `ty` -> pass.
  4. `pytest -q tests/test_create_distribution.py` -> `13 passed`.
- Deferido:
  1. manter `OutputDir={#SourcePath}` como decisao intencional deste ciclo.
  2. debt de qualidade em `create_zip_package` e `compile_installer` para ciclo dedicado.
- Residuos locais fora de escopo mantidos:
  1. `data/ssas.db`
  2. `config/settings.json.bak_20260308_212715`

## HISTORICAL SNAPSHOT 2026-03-10 09:33 - start from here

- Slice aplicado:
  1. hardening de confianca para `INNO_SETUP_COMPILER`.
  2. `scripts/create_distribution.py`:
     - override por env agora exige caminho absoluto, nome permitido, arquivo existente e parent confiavel.
     - allowlist minima inclui Program Files Inno Setup e parent do `which iscc` quando presente.
     - override invalido apenas gera warning e segue fallback normal.
  3. testes:
     - `test_compile_installer_rejects_relative_env_override`.
     - `test_compile_installer_accepts_absolute_env_override_in_trusted_parent`.
- Arquivos tocados:
  1. `scripts/create_distribution.py`
  2. `tests/test_create_distribution.py`
  3. `docs/RECOVERY_BACKLOG.md`
  4. `docs/NEXT_CHAT_MIGRATION.md`
  5. `docs/AGENTS_HANDOFF_NEXT_CYCLE.md`
- Gates desta rodada:
  1. `py_compile`, `ruff`, `ty` -> pass.
  2. `pytest -q tests/test_create_distribution.py` -> `13 passed`.
- Deferido:
  1. debt de qualidade em `create_zip_package`.
  2. semantica geral de resolucao por build system em ciclo dedicado.
  3. validacao de Source do Inno em Windows real em rodada dedicada.
  4. kluster final sinalizou HIGH em `Source` relativo; sem repro local, validar em runner Windows com ISCC real.
- Residuos locais fora de escopo mantidos:
  1. `data/ssas.db`
  2. `config/settings.json.bak_20260308_212715`

## HISTORICAL SNAPSHOT 2026-03-10 09:28

- Slice aplicado:
  1. origem `Source` do Inno Setup passou a usar relpath real entre `DIST_OUTPUT` e `source_dir`.
  2. `scripts/create_distribution.py`:
     - `source_dir_spec` agora usa `os.path.relpath(source_dir, DIST_OUTPUT)`.
     - fallback para caminho absoluto resolvido quando `relpath` falhar.
     - normalizacao de path mantida para formato Windows.
  3. testes:
     - `test_create_inno_setup_script_uses_sourcepath_outputdir` agora valida `Source` relativo esperado.
     - novo `test_create_inno_setup_script_uses_absolute_source_when_relpath_fails`.
- Arquivos tocados:
  1. `scripts/create_distribution.py`
  2. `tests/test_create_distribution.py`
  3. `docs/RECOVERY_BACKLOG.md`
  4. `docs/NEXT_CHAT_MIGRATION.md`
  5. `docs/AGENTS_HANDOFF_NEXT_CYCLE.md`
- Gates desta rodada:
  1. `py_compile`, `ruff`, `ty` -> pass.
  2. `pytest -q tests/test_create_distribution.py` -> `11 passed`.
- Deferido:
  1. debt de qualidade em `create_zip_package`.
  2. semantica geral de resolucao por build system em ciclo dedicado.
  3. deduplicacao de setup dos testes em ciclo de manutencao.
- Residuos locais fora de escopo mantidos:
  1. `data/ssas.db`
  2. `config/settings.json.bak_20260308_212715`

## HISTORICAL SNAPSHOT 2026-03-10 09:23

- Slice aplicado:
  1. `OutputDir` do Inno Setup ficou deterministico e independente de cwd.
  2. `scripts/create_distribution.py`:
     - template `.iss` usa `OutputDir={#SourcePath}`.
  3. testes:
     - novo `test_create_inno_setup_script_uses_sourcepath_outputdir`.
- Arquivos tocados:
  1. `scripts/create_distribution.py`
  2. `tests/test_create_distribution.py`
  3. `docs/RECOVERY_BACKLOG.md`
  4. `docs/NEXT_CHAT_MIGRATION.md`
  5. `docs/AGENTS_HANDOFF_NEXT_CYCLE.md`
- Gates desta rodada:
  1. `py_compile`, `ruff`, `ty` -> pass.
  2. `pytest -q tests/test_create_distribution.py` -> `10 passed`.
- Deferido:
  1. debt de qualidade em `create_zip_package`.
  2. semantica geral de resolucao por build system em ciclo dedicado.
  3. deduplicacao de setup dos testes em ciclo de manutencao.
- Residuos locais fora de escopo mantidos:
  1. `data/ssas.db`
  2. `config/settings.json.bak_20260308_212715`

## HISTORICAL SNAPSHOT 2026-03-10 09:18

- Slice aplicado:
  1. fallback de pyinstaller (canonical -> legacy) ficou explicito no codigo e coberto por teste.
  2. `scripts/create_distribution.py`:
     - `_resolve_build_directory` reorganizado com fallback canonical->legacy explicito.
  3. testes:
     - novo `test_resolve_build_directory_pyinstaller_falls_back_to_legacy_when_canonical_invalid`.
- Arquivos tocados:
  1. `scripts/create_distribution.py`
  2. `tests/test_create_distribution.py`
  3. `docs/RECOVERY_BACKLOG.md`
  4. `docs/NEXT_CHAT_MIGRATION.md`
  5. `docs/AGENTS_HANDOFF_NEXT_CYCLE.md`
- Gates desta rodada:
  1. `py_compile`, `ruff`, `ty` -> pass.
  2. `pytest -q tests/test_create_distribution.py` -> `9 passed`.
- Deferido:
  1. `create_zip_package` ainda concentrada (debt de qualidade).
  2. semantica geral de resolver por build system em slice dedicado.
- Residuos locais fora de escopo mantidos:
  1. `data/ssas.db`
  2. `config/settings.json.bak_20260308_212715`

## HISTORICAL SNAPSHOT 2026-03-10 09:11

- Slice aplicado:
  1. clarificado erro de resolucao de build no empacotador.
  2. `scripts/create_distribution.py`:
     - novo `_resolve_build_directory_failure_reason(...)`.
     - `create_zip_package(...)` passa a logar motivo detalhado da falha de resolucao.
  3. testes:
     - ajuste de asserts para mensagens especificas.
     - novo `test_create_zip_package_returns_none_when_build_directory_is_missing`.
- Arquivos tocados:
  1. `scripts/create_distribution.py`
  2. `tests/test_create_distribution.py`
  3. `docs/RECOVERY_BACKLOG.md`
  4. `docs/NEXT_CHAT_MIGRATION.md`
  5. `docs/AGENTS_HANDOFF_NEXT_CYCLE.md`
- Gates desta rodada:
  1. `py_compile`, `ruff`, `ty` -> pass.
  2. `pytest -q tests/test_create_distribution.py` -> `8 passed`.
- Deferido:
  1. `create_zip_package` ainda concentrada (debt de qualidade).
  2. semantica de `_resolve_build_directory` (resolver dir vs validar executavel) em slice futuro.
  3. duplicacao de setup em testes de distribuicao em slice de manutencao futuro.
- Residuos locais fora de escopo mantidos:
  1. `data/ssas.db`
  2. `config/settings.json.bak_20260308_212715`

## HISTORICAL SNAPSHOT 2026-03-10 08:49

- Slice aplicado:
  1. removido fallback generico de executavel no pacote staged.
  2. `scripts/create_distribution.py`:
     - `_detect_primary_executable_name(...)` agora retorna `Optional[str]`.
     - sem executavel detectado, `create_zip_package(...)` falha de forma explicita e encerra.
     - `_build_bundle_ignore(...)` agora detecta tipo real (`arquivo`/`diretorio`) via caminho origem.
  3. testes:
     - novo `test_detect_primary_executable_name_returns_none_when_package_has_no_binary`.
- Arquivos tocados:
  1. `scripts/create_distribution.py`
  2. `tests/test_create_distribution.py`
  3. `docs/RECOVERY_BACKLOG.md`
  4. `docs/NEXT_CHAT_MIGRATION.md`
  5. `docs/AGENTS_HANDOFF_NEXT_CYCLE.md`
- Gates desta rodada:
  1. `py_compile`, `ruff`, `ty` -> pass.
  2. `pytest -q tests/test_create_distribution.py` -> `7 passed`.
- Deferido:
  1. debt de qualidade: `create_zip_package` ainda concentrada.
  2. debt semantico: separacao entre "resolver dir" e "validar executavel" em `_resolve_build_directory` ficou para slice dedicado.
  3. hardening de trust para `INNO_SETUP_COMPILER` (allowlist de diretorios) fica para ciclo de seguranca dedicado.
  4. validacao de path absoluto Inno e heuristica pyinstaller precisam rodada em ambiente Windows dedicado.
- Residuos locais fora de escopo mantidos:
  1. `data/ssas.db`
  2. `config/settings.json.bak_20260308_212715`

## HISTORICAL SNAPSHOT 2026-03-10 08:43

- Slice aplicado:
  1. selecao do build canonico pyinstaller ficou deterministica por ordem de `canonical_dirs`.
  2. `scripts/create_distribution.py`:
     - `_resolve_build_directory("pyinstaller")` deixou de usar `mtime`.
     - primeiro diretorio valido na lista de `canonical_dirs` passa a ser o escolhido.
     - regra de exclusao de bundle consolidada em `_should_skip_bundle_entry(...)`.
  3. testes:
     - novo `test_resolve_build_directory_pyinstaller_prefers_canonical_order_over_mtime`.
- Arquivos tocados:
  1. `scripts/create_distribution.py`
  2. `tests/test_create_distribution.py`
  3. `docs/RECOVERY_BACKLOG.md`
  4. `docs/NEXT_CHAT_MIGRATION.md`
  5. `docs/AGENTS_HANDOFF_NEXT_CYCLE.md`
- Gates desta rodada:
  1. `py_compile`, `ruff`, `ty` -> pass.
  2. `pytest -q tests/test_create_distribution.py` -> `6 passed`.
- Deferido:
  1. debt de qualidade: `create_zip_package` ainda concentrada.
  2. debt conhecido do Inno cross-drive permanece fora do escopo deste slice.
  3. alerta semantico amplo sobre nao-pyinstaller ficou sem evidencias de regressao nesta rodada.
  4. fallback generico de `_detect_primary_executable_name` segue para slice semantico dedicado.
- Residuos locais fora de escopo mantidos:
  1. `data/ssas.db`
  2. `config/settings.json.bak_20260308_212715`

## HISTORICAL SNAPSHOT 2026-03-10 08:40

- Slice aplicado:
  1. hardening final do empacotador para status explicito de instalador e copia sanitizada consistente.
  2. `scripts/create_distribution.py`:
     - `compile_installer` agora retorna `success|missing|failed`.
     - caller separa `script_failed` para falha na geracao do `.iss`.
     - relatorio final diferencia dependencia ausente de falha real de compilacao.
     - `copytree` de `_internal` e `config` agora passa por filtro sanitizado comum.
     - `arcname` do ZIP agora deriva de `package_dir` (mais robusto).
     - validacao de bundle `.app` exige executavel real no conteudo do app.
     - readme tecnico ajustado: `ANTIVIRUS_EXCLUSOES.md` e copia `LEIA-ME.md`.
  3. testes:
     - novo `test_compile_installer_returns_missing_when_iscc_is_unavailable`.
  4. docs:
     - `docs/GUIA_DISTRIBUICAO.md` com troubleshooting separado para `missing` vs `failed`.
- Arquivos tocados:
  1. `scripts/create_distribution.py`
  2. `tests/test_create_distribution.py`
  3. `docs/GUIA_DISTRIBUICAO.md`
  4. `docs/RECOVERY_BACKLOG.md`
  5. `docs/NEXT_CHAT_MIGRATION.md`
  6. `docs/AGENTS_HANDOFF_NEXT_CYCLE.md`
- Gates desta rodada:
  1. `py_compile`, `ruff`, `ty` -> pass.
  2. `pytest -q tests/test_create_distribution.py` -> `5 passed`.
  3. `kluster review` no codigo e docs tocados -> sem blocker novo de runtime.
- Deferido:
  1. `create_zip_package` ainda concentrado (debt de qualidade).
  2. ponto semantico de selecao por mtime em canonical dirs mantido como decisao atual.
  3. alerta de cleanup de temp_dir em early-return foi classificado como falso positivo (cleanup ja existe no codigo).
- Residuos locais fora de escopo mantidos:
  1. `data/ssas.db`
  2. `config/settings.json.bak_20260308_212715`

## HISTORICAL SNAPSHOT 2026-03-10 08:28

- Slice aplicado:
  1. hardening de empacotamento para validar executavel primario no build selecionado.
  2. `scripts/create_distribution.py`:
     - `_get_pyinstaller_canonical_dirs()` com fallback para dirs canonicos padrao.
     - `_has_primary_executable(...)` para barrar diretorio parcial sem binario executavel.
     - `_resolve_build_directory(...)` agora exige conteudo + executavel valido.
  3. testes:
     - novo `test_create_zip_package_returns_none_when_canonical_has_no_primary_executable`.
     - mocks de `BUILD_SYSTEMS` com `canonical_dirs` explicito.
  4. docs:
     - `docs/GUIA_DISTRIBUICAO.md` troubleshooting atualizado com validacao de executavel primario.
- Arquivos tocados:
  1. `scripts/create_distribution.py`
  2. `tests/test_create_distribution.py`
  3. `docs/GUIA_DISTRIBUICAO.md`
  4. `docs/RECOVERY_BACKLOG.md`
  5. `docs/NEXT_CHAT_MIGRATION.md`
  6. `docs/AGENTS_HANDOFF_NEXT_CYCLE.md`
- Gates desta rodada:
  1. `py_compile`, `ruff`, `ty` -> pass.
  2. `pytest -q tests/test_create_distribution.py` -> `4 passed`.
  3. `kluster review` em codigo tocado -> clean.
- Deferido:
  1. hardening cross-platform mais amplo no empacotador fica para ciclo dedicado.
- Residuos locais fora de escopo mantidos:
  1. `data/ssas.db`
  2. `config/settings.json.bak_20260308_212715`

## HISTORICAL SNAPSHOT 2026-03-10 08:18

- Slice aplicado:
  1. alinhamento Debian para fluxo canonico ZIP.
  2. `launchers/platforms/debian_amd64/build_config.json`:
     - `post_build.package` agora `zip`.
     - limpeza de exclusoes de risco em `exclude_modules` (`json`, `argparse` e modulos core de concorrencia/rede).
  3. docs operacionais atualizados:
     - `docs/GUIA_DISTRIBUICAO.md` (Debian ZIP no baseline atual).
     - `docs/BUILD_MULTIPLATFORM.md` (UPX "quando disponivel" + nota Debian ZIP).
- Arquivos tocados:
  1. `launchers/platforms/debian_amd64/build_config.json`
  2. `docs/GUIA_DISTRIBUICAO.md`
  3. `docs/BUILD_MULTIPLATFORM.md`
  4. `docs/RECOVERY_BACKLOG.md`
  5. `docs/NEXT_CHAT_MIGRATION.md`
  6. `docs/AGENTS_HANDOFF_NEXT_CYCLE.md`
- Gates desta rodada:
  1. `kluster review` nos arquivos do slice -> clean na rodada final.
- Deferido:
  1. implementacao automatica de AppImage/.deb fora do fluxo ZIP.
  2. revisao equivalente de exclusoes em `windows_amd64` e `macos_arm64`.
- Residuos locais fora de escopo mantidos:
  1. `data/ssas.db`
  2. `config/settings.json.bak_20260308_212715`

## HISTORICAL SNAPSHOT 2026-03-10 08:04

- Slice aplicado:
  1. hardening do build canonico para nao embedar `data/` por padrao.
  2. `launchers/build_multiplatform.py` agora so inclui `data/` se `pyinstaller_args.include_local_data=true`.
  3. cobertura de regressao adicionada em `tests/test_create_distribution.py` para garantir exclusao de `.db/.xlsx/.xls` no pacote canonico.
  4. docs operacionais atualizados com a politica:
     - `docs/GUIA_DISTRIBUICAO.md`
     - `docs/BUILD_MULTIPLATFORM.md`
- Arquivos tocados:
  1. `launchers/build_multiplatform.py`
  2. `tests/test_create_distribution.py`
  3. `docs/GUIA_DISTRIBUICAO.md`
  4. `docs/BUILD_MULTIPLATFORM.md`
  5. `docs/RECOVERY_BACKLOG.md`
  6. `docs/NEXT_CHAT_MIGRATION.md`
  7. `docs/AGENTS_HANDOFF_NEXT_CYCLE.md`
- Gates desta rodada:
  1. `py_compile`, `ruff`, `ty` -> pass.
  2. `pytest -q tests/test_create_distribution.py` -> `3 passed`.
  3. `kluster review` em codigo tocado -> sem blocker novo do slice; sobram debts antigos estruturais fora de escopo.
- Deferido:
  1. naming/semantica do `MultiPlatformBuilder` versus limitacao de cross-compile.
  2. concentracao de responsabilidades em `build_multiplatform.py`.
  3. performance de scans/cleanup recursive no builder.
- Residuos locais fora de escopo mantidos:
  1. `data/ssas.db`
  2. `config/settings.json.bak_20260308_212715`

## HISTORICAL SNAPSHOT 2026-03-10 07:44

- Slice aplicado:
  1. deduplicacao minima do prune de workers em `gui/ssa/gui_workers.py`.
  2. novo helper comum `_classify_and_update_global_workers_locked(...)` usado por:
     - `prune_retired_data_loader_workers`
     - `prune_retired_rescan_workers`
  3. novo teste de regressao em `tests/test_gui_workers_rescan_data.py` para cap de workers e expiracao do mais antigo.
- Arquivos tocados:
  1. `gui/ssa/gui_workers.py`
  2. `tests/test_gui_workers_rescan_data.py`
  3. `docs/RECOVERY_BACKLOG.md`
  4. `docs/NEXT_CHAT_MIGRATION.md`
  5. `docs/AGENTS_HANDOFF_NEXT_CYCLE.md`
- Gates desta rodada:
  1. `py_compile`, `ruff`, `ty` -> pass.
  2. `pytest -q tests/test_gui_workers_rescan_data.py` -> `10 passed`.
  3. `kluster review file gui/ssa/gui_workers.py tests/test_gui_workers_rescan_data.py` -> sem novo blocker do slice; sobram debts medios antigos fora de escopo.
  4. `kluster review file docs/RECOVERY_BACKLOG.md` -> clean.
- Deferido:
  1. decompor `on_data_loaded` (god-function) em ciclo dedicado.
  2. desacoplar prompt de modo em `rescan_data` para caller.
  3. mover sanitizacao/sort pesado do UI thread para worker.
- Residuos locais fora de escopo mantidos:
  1. `data/ssas.db`
  2. `config/settings.json.bak_20260308_212715`

## HISTORICAL SNAPSHOT 2026-03-10 06:14

- Slice aplicado:
  1. doc sync de build/distribuicao para baseline v4.32.
  2. `docs/GUIA_DISTRIBUICAO.md` reescrito para fluxo canonico:
     - build: `launchers/build_multiplatform.py`
     - empacotamento: `scripts/create_distribution.py`
     - artefatos: `launchers/dist/*`
  3. `launchers/README.md` atualizado para plataformas reais ativas:
     - `windows_amd64`, `macos_arm64`, `debian_amd64`.
  4. guias completos de pyinstaller/nuitka/pyoxidizer receberam bloco `CURRENT TRUTH`
     e rebaixaram referencias antigas para historico.
- Arquivos tocados:
  1. `docs/GUIA_DISTRIBUICAO.md`
  2. `launchers/README.md`
  3. `docs/BUILD_PYINSTALLER_GUIA_COMPLETO.md`
  4. `docs/BUILD_NUITKA_GUIA_COMPLETO.md`
  5. `docs/BUILD_PYOXIDIZER_GUIA_COMPLETO.md`
  6. `docs/RECOVERY_BACKLOG.md`
  7. `docs/NEXT_CHAT_MIGRATION.md`
  8. `docs/AGENTS_HANDOFF_NEXT_CYCLE.md`
- Gates desta rodada:
  1. `kluster review` nos 5 docs-alvo -> clean.
- Deferido:
  1. referencias legadas dentro de secoes historicas extensas dos guias completos mantidas como snapshot.
- Residuos locais fora de escopo mantidos:
  1. `data/ssas.db`
  2. `config/settings.json.bak_20260308_212715`

## HISTORICAL SNAPSHOT 2026-03-10 02:39

- Slice aplicado:
  1. alinhamento de distribuicao para caminho canonico:
     - `scripts/create_distribution.py` agora resolve pyinstaller por `launchers/dist/*` com fallback legado `builds/*`.
     - `scripts/copy_data_to_builds.py` resolve destinos canonicos e legado.
  2. hardening de seguranca e instalador:
     - exclusao de dados locais sensiveis no bundle canonico (`data`, `docs_entrada`, `.db`, `.xlsx`, etc.).
     - `copy_data_to_builds.py` agora exige `--allow-local-data`.
     - Inno Setup com:
       - `INNO_SETUP_COMPILER` e lookup no PATH;
       - `OutputDir=.` e `SetupIconFile=..\\assets\\icon.ico`;
       - exclusoes sincronizadas com politica de bundle.
  3. testes:
     - novo teste para fallback canonico pyinstaller em `tests/test_create_distribution.py`.
     - ajuste de assert de erro no teste legado.
- Arquivos tocados:
  1. `scripts/create_distribution.py`
  2. `scripts/copy_data_to_builds.py`
  3. `tests/test_create_distribution.py`
  4. `docs/RECOVERY_BACKLOG.md`
  5. `docs/NEXT_CHAT_MIGRATION.md`
  6. `docs/AGENTS_HANDOFF_NEXT_CYCLE.md`
- Gates desta rodada:
  1. `py_compile`, `ruff`, `ty` -> pass.
  2. `pytest -q tests/test_create_distribution.py` -> `2 passed`.
- Deferido:
  1. debt de qualidade: `create_zip_package` ainda grande (sem refatoracao ampla neste ciclo).
  2. refinamento futuro de atalhos GUI/CLI no template Inno para cenarios com binarios separados.
  3. extracao de constantes compartilhadas de distribuicao para modulo comum.
- Residuos locais fora de escopo mantidos:
  1. `data/ssas.db`
  2. `config/settings.json.bak_20260308_212715`

## HISTORICAL SNAPSHOT 2026-03-10 01:11

- Slice aplicado:
  1. bugfix real sem mudar estrutura:
     - cache de tabela em `database.py`.
     - validacao estruturada para coluna obrigatoria ausente em `database_validation.py`.
     - `_debug_phases` com namespace por planilha em `extractor.py`.
     - ajustes de duplicadas semanticas em `robust_importer.py`.
     - hardening de fallback/path em `gui_ssa.py`.
     - `max_global_workers` efetivo + registro imediato de worker em `gui_workers.py`.
     - guarda segura de `blockSignals` no bind de aba.
     - reaplicacao de QSS global por estado real do app em `gui_theme.py`.
  2. testes/docs:
     - qWait dinamico no teste de resize.
     - assert mais forte no reimport de upsert.
     - troubleshooting com `PY_RUNTIME`.
- Arquivos tocados:
  1. `armazenamento/database.py`
  2. `armazenamento/database_validation.py`
  3. `extracao/extractor.py`
  4. `utils/robust_importer.py`
  5. `gui/gui_ssa.py`
  6. `gui/ssa/gui_workers.py`
  7. `gui/mixins/tab_context_gui_ssa_mixin.py`
  8. `gui/ssa/gui_theme.py`
  9. `tests/test_gui_workers_rescan_data.py`
  10. `tests/test_gui_filter_logic.py`
  11. `tests/test_db_reset_and_upsert.py`
  12. `docs/TROUBLESHOOTING_IMPORTACAO.md`
  13. `docs/RECOVERY_BACKLOG.md`
  14. `docs/NEXT_CHAT_MIGRATION.md`
  15. `docs/AGENTS_HANDOFF_NEXT_CYCLE.md`
- Gates desta rodada:
  1. `py_compile`, `ruff`, `ty` -> pass.
  2. `pytest` focado em workers/gui/upsert/validacao/importacao -> `8 passed`.
  3. `pytest` focado em extracao/report/signal -> `35 passed`.
  4. `pytest` focado em tema/resize/quick_filter -> `4 passed`.
- Deferido:
  1. debts estruturais amplos apontados por kluster (fora de escopo deste patch minimo).
- Residuos locais fora de escopo mantidos:
  1. `data/ssas.db`
  2. `config/settings.json.bak_20260308_212715`

## HISTORICAL SNAPSHOT 2026-03-10 00:55

- Slice aplicado:
  1. atalho rapido `Setor Executor` sincronizado com filtros avancados:
     - `setor_executor`
     - `setor_emissor`
     - excludes limpos.
  2. popup do combo rapido com rolagem real.
- Gates desta rodada:
  1. `py_compile`, `ruff`, `ty` -> pass.
  2. `pytest` focado quick setor/sort -> `5 passed`.
- Nota:
  1. comportamento foi revertido no hotfix 00:55 para remover sync indevido com avancados.

## HISTORICAL SNAPSHOT 2026-03-10 00:36

- Slice aplicado:
  1. hardening de sort `num_reprogramacoes` com alinhamento defensivo de indice.
  2. apos sort por `num_reprogramacoes`, cache e re-primado para coerencia com `df_exibido`.
  3. tooltip de `Limpar Busca` atualizado para refletir cancelamento da busca em andamento.
  4. abertura do guia de instalacao com `QUrl` explicito antes de `openUrl`.
- Arquivos tocados:
  1. `gui/gui_ssa.py`
  2. `docs/RECOVERY_BACKLOG.md`
  3. `docs/NEXT_CHAT_MIGRATION.md`
  4. `docs/AGENTS_HANDOFF_NEXT_CYCLE.md`
- Gates desta rodada:
  1. `py_compile`, `ruff`, `ty` -> pass.
  2. `pytest` focado GUI filtro/sort/tooltip -> `6 passed`.
  3. `pytest` focado importacao externa/guia -> `2 passed`.
- Deferido:
  1. debts antigos de arquitetura/performance em `gui/gui_ssa.py` seguem fora deste patch minimo.
- Residuos locais fora de escopo mantidos:
  1. `data/ssas.db`
  2. `config/settings.json.bak_20260308_212715`

## HISTORICAL SNAPSHOT 2026-03-10 00:22

- Slice aplicado:
  1. atalho rapido `Setor Executor` deixou de ter persistencia de estado.
  2. checkbox `Configuracao persistente` removido da UI.
  3. combo rapido passou a sincronizar corretamente com OR group/filtros de coluna:
     - atualiza `setor_executor`
     - sincroniza `setor_emissor` quando houver grupo OR
     - reconstrui painel de filtros e reaplica refresh.
  4. popup do combo limitado para rolagem (`maxVisibleItems=14`).
  5. fix critico no fallback de importacao externa:
     - `_build_unique_destination_path` agora chamado de forma segura em fallback.
- Arquivos tocados:
  1. `gui/gui_ssa.py`
  2. `tests/test_gui_filter_logic.py`
  3. `docs/RECOVERY_BACKLOG.md`
  4. `docs/NEXT_CHAT_MIGRATION.md`
  5. `docs/AGENTS_HANDOFF_NEXT_CYCLE.md`
- Gates desta rodada:
  1. `py_compile`, `ruff`, `ty` -> pass.
  2. `pytest` focado filtro rapido/cache -> `7 passed`.
  3. `pytest` focado importacao externa -> `2 passed`.
- Deferido:
  1. debts antigos de arquitetura/performance em `gui/gui_ssa.py` continuam fora deste patch minimo.
- Residuos locais fora de escopo mantidos:
  1. `data/ssas.db`
  2. `config/settings.json.bak_20260308_212715`

## HISTORICAL SNAPSHOT 2026-03-10 00:17

- Slice aplicado:
  1. cache de sort de `num_reprogramacoes` alinhado com `df_exibido` apos ordenacao.
  2. testes focados de GUI estabilizados para invariantes de cache (index/keys/source_len), sem acoplamento em `id(df)`.
  3. teste de persistencia do filtro rapido ficou deterministico (nao depende de estado salvo pre-existente).
- Arquivos tocados:
  1. `gui/gui_ssa.py`
  2. `tests/test_gui_filter_logic.py`
  3. `docs/RECOVERY_BACKLOG.md`
  4. `docs/NEXT_CHAT_MIGRATION.md`
  5. `docs/AGENTS_HANDOFF_NEXT_CYCLE.md`
- Gates desta rodada:
  1. `py_compile`, `ruff`, `ty` -> pass.
  2. `pytest` focado em filtros/cache -> `7 passed`.
- Deferido:
  1. debts antigos de arquitetura/performance em `gui/gui_ssa.py` seguem fora deste patch minimo.
- Residuos locais fora de escopo mantidos:
  1. `data/ssas.db`
  2. `config/settings.json.bak_20260308_212715`

## HISTORICAL SNAPSHOT 2026-03-09 23:53

- Slice aplicado:
  1. remocao do seletor `Perfil de filtro` da UI (mantido apenas `Salvar Filtro`).
  2. adicao de combo rapido `Setor Executor` ao lado de `Colunas Visiveis`.
  3. ordem do combo: `IEE1..IEE4`, depois `MEL1..MEL4`, depois ordem alfabetica.
  4. adicao do checkbox `Configuracao persistente` (default desmarcado) como primeira opcao da faixa de opcoes.
  5. quando persistencia ativa, salvar automaticamente:
     - `gui_settings.persist_quick_filter_config`
     - `gui_settings.quick_setor_executor`
     - `display_columns` (ao alterar colunas visiveis).
  6. `Colunas Visiveis` agora exibe contagem no proprio botao (`Colunas Visiveis: N`) e removeu o box lateral de resumo.
- Arquivos tocados:
  1. `gui/widgets/column_selector.py`
  2. `gui/gui_ssa.py`
  3. `gui/mixins/tab_context_gui_ssa_mixin.py`
  4. `gui/mixins/filter_gui_ssa_mixin.py`
  5. `tests/test_gui_filter_logic.py`
  6. `docs/RECOVERY_BACKLOG.md`
- Gates desta rodada:
  1. `py_compile`, `ruff`, `ty` -> pass.
  2. `pytest` focado novo comportamento -> `3 passed`.
  3. reteste `tests/test_gui_menu_import_external.py` -> `13 passed`.
- Deferido:
  1. debts antigos de arquitetura/performance em `gui/gui_ssa.py` e mixins (fora do escopo deste patch minimo).
- Residuos locais fora de escopo mantidos:
  1. `data/ssas.db`
  2. `config/settings.json.bak_20260308_212715`

## HISTORICAL SNAPSHOT 2026-03-09 23:24

- Micro-slice aplicado:
  1. correcao pontual na chamada fallback de `_build_unique_destination_path` em `gui/gui_ssa.py`.
  2. fallback agora usa descriptor bound call para evitar ambiguidade de assinatura em chamada via classe.
  3. comportamento funcional mantido (incluindo compatibilidade com janela stub de teste).
- Gates desta rodada:
  1. `py_compile`, `ruff`, `ty` -> pass.
  2. `pytest` focado de importacao/menu -> `5 passed`.
- Deferido:
  1. debts antigos de arquitetura/performance em `gui/gui_ssa.py` seguem fora de escopo neste micro-slice.
- Residuos locais fora de escopo mantidos:
  1. `data/ssas.db`
  2. `config/settings.json.bak_20260308_212715`

## HISTORICAL SNAPSHOT 2026-03-09 23:08

- Slice concluido: pendencia pesada + comentarios simples do PR.
  1. `gui/gui_ssa.py`:
     - `run_vacuum_analyze` agora roda `VACUUM/ANALYZE` em thread de fundo no runtime normal.
     - `_build_unique_destination_path` com limite de tentativas e erro explicito.
     - backup de opcoes com timestamp de microssegundos.
     - consolidacao: update-only nao vai para `nosurvivor`; contador `nosurvivor` incrementa so apos `move` bem-sucedido.
  2. `gui/ssa/gui_workers.py`:
     - `prompt` sem `QMessageBox` cai para modo incremental seguro.
     - `expired_all` deduplicado no prune.
     - `_active_rescan_dialog` limpo tambem em `worker.finished`.
  3. testes:
     - `tests/test_gui_menu_import_external.py`: monkeypatch `QUrl`/`QDesktopServices` headless, backup duplo unico, update-only fora de `nosurvivor`.
     - `tests/test_gui_workers_rescan_data.py`: `show_non_modal_called`, limpeza de dialogo em cancel+finish, `prompt` sem dialogo => incremental.
  4. docs:
     - `docs/CCR_LLM_PROVIDERS_SETUP.md`: nota de snapshot historico para `instructions` legadas.
- Gates desta rodada:
  1. `py_compile`, `ruff`, `ty` dos arquivos tocados -> pass.
  2. `pytest -q tests/test_gui_menu_import_external.py tests/test_gui_workers_rescan_data.py` -> `20 passed`.
- Deferido explicitamente:
  1. debts estruturais/performance antigos reportados por kluster em `gui/gui_ssa.py` e `gui/ssa/gui_workers.py` (fora deste patch minimo).
- Residuos locais fora de escopo mantidos:
  1. `data/ssas.db`
  2. `config/settings.json.bak_20260308_212715`

## HISTORICAL SNAPSHOT 2026-03-09 22:49

- Heavy pending slice executado (sem mudanca de layout):
  1. preprocessamento pesado movido para `DataLoaderWorker` (sanitize/sort/non-null cache).
  2. `on_data_loaded` passou a consumir `df.attrs` (`ssa_preprocessed_for_gui`, `ssa_sanitized_df`, `ssa_non_null_cols`) no caminho padrao.
  3. fallback legado mantido para chamadas sem attrs.
  4. `load_data` agora restaura UI mesmo em falha ao instanciar worker.
- Testes/gates desta rodada:
  1. `py_compile`, `ruff`, `ty` dos arquivos tocados -> pass.
  2. `pytest` focado (`8 passed`) + `test_workers_advanced.py -k DataLoaderWorker` (`14 passed`) -> pass.
- Deferido explicitamente:
  1. `query_db(self.db_path, '', query, ...)` no worker classificado como `FALSO_POSITIVO` por contrato atual de `query_db`.
  2. debt de concentracao/duplicacao em `on_data_loaded` segue para ciclo dedicado.
- Residuos locais fora de escopo mantidos:
  1. `data/ssas.db`
  2. `config/settings.json.bak_20260308_212715`

## HISTORICAL SNAPSHOT 2026-03-09 22:30

- Politica ASCII reforcada para review/documentacao tecnica:
  1. sugestoes ortograficas com acentos/cedilha em texto tecnico devem ser tratadas como `FALSO_POSITIVO` se conflitar com a politica ASCII do repo.
- Debts antigos priorizados (proximo ciclo):
  1. `gui/gui_ssa.py`: debt arquitetural na `SSAMainWindow`.
  2. `gui/ssa/gui_workers.py`: custo alto em `on_data_loaded` no UI thread.
  3. `gui/ssa/gui_workers.py`: duplicacao de prune/cleanup entre workers.
- Slice atual:
  1. apenas DOC_SYNC de governanca.
  2. sem alteracao de runtime.
  3. kluster em docs tocados -> clean.
- Residuos locais fora de escopo mantidos:
  1. `data/ssas.db`
  2. `config/settings.json.bak_20260308_212715`

## HISTORICAL SNAPSHOT 2026-03-09 22:11

- Follow-up de comentarios pendentes do PR #45 concluido com patch minimo:
  1. worker prune nao perde mais worker vivo quando ultrapassa cap.
  2. importacao externa aceita/copia somente `.xlsx` e separa `nao_suportados`.
  3. consolidacao para `nosurvivor` exige sucesso sem sobreviventes (status+contagem), evitando falso positivo.
  4. cache de descoberta de Excel agora e case-insensitive.
  5. integridade de DB passa a preferir tabela sobre view ao resolver alias.
- Testes/gates desta rodada:
  1. `py_compile`, `ruff`, `ty` dos arquivos tocados -> pass.
  2. `pytest -q tests/test_gui_workers_rescan_data.py tests/test_gui_menu_import_external.py tests/test_caching.py tests/test_database_verification.py` -> `47 passed`.
- Deferido explicitamente:
  1. debts estruturais/performance amplos em `gui/gui_ssa.py` e `gui/ssa/gui_workers.py` (fora do escopo de estabilidade minima).
  2. revisao semantica de `database_exists` em arquivo 0-byte mantida para ciclo dedicado por compatibilidade.
- Residuos locais fora de escopo mantidos:
  1. `data/ssas.db`
  2. `config/settings.json.bak_20260308_212715`

## HISTORICAL SNAPSHOT 2026-03-09 21:58

- Follow-up de comentarios P2 do PR #45 concluido (patch minimo):
  1. rescan worker registrado em `global_workers/global_meta` logo apos `start()`.
  2. importacao externa passou a reutilizar helper unico de dedup de destino.
  3. doc CCR alinhado para `*.instructions`.
- Testes/gates desta rodada:
  1. `py_compile`, `ruff`, `ty` dos arquivos tocados -> pass.
  2. `pytest -q tests/test_gui_workers_rescan_data.py tests/test_gui_menu_import_external.py` -> `16 passed`.
- Deferido explicitamente:
  1. debt transversal de nao-ascii em testes (fora deste slice de baixo risco).
- Residuos locais fora de escopo mantidos:
  1. `data/ssas.db`
  2. `config/settings.json.bak_20260308_212715`

## HISTORICAL SNAPSHOT 2026-03-09 21:43

- PR ativo: `#45` (base `dev`, head `codex/sprint-importacao-grave-fixes-20260305`).
- Hotfix aplicado para comentarios/checks bloqueantes:
  1. contrato de cancelamento em `tests/test_import_cancellation.py` alinhado ao runtime atual.
  2. warning de integridade em `core/app_logic.py` voltou a logar no caminho valido.
  3. `database_validation` nao retorna mais `set` interno em retorno precoce.
  4. `database.query_db` respeita `raise_on_error=False` tambem para `ValueError`.
  5. removido suppress silencioso em whitelist de colunas no insert simples.
  6. removido warning falso `Problemas detectados no banco: []` em `database_integrity`.
- Evidencia de qualidade desta rodada:
  1. pacote focado: `30 passed`.
  2. pacote equivalente ao `quality-gates`: `73 passed`.
- Residuos locais fora de escopo mantidos:
  1. `data/ssas.db`
  2. `config/settings.json.bak_20260308_212715`

## HISTORICAL SNAPSHOT 2026-03-09 19:26

- Integridade de documentacao reforcada no baseline `4.32`.
- Entregas principais:
  1. referencias quebradas de `.md` corrigidas nos docs ativos.
  2. referencias locais opcionais (`local_ai_private`) tratadas como nao obrigatorias.
  3. stubs `docs/ARCH_*` adicionados para compatibilidade com backlog historico.
  4. ponteiro de plano legado criado em `docs/archive/PLANO_REFATORACAO_SSA_CONSULTA_RAPIDA.md`.
- Evidencia de qualidade:
  1. varredura de referencias markdown em `README.md` + `docs/*.md` com resultado final `missing=0`.
  2. kluster limpo apos ajustes finais por arquivo.
- Residuos locais fora de escopo mantidos:
  1. `data/ssas.db`
  2. `config/settings.json.bak_20260308_212715`

## HISTORICAL SNAPSHOT 2026-03-09 19:01

- Ciclo de refinamento documental concluido para baseline `4.32`.
- Principais entregas:
  1. `docs/INDEX.md` e `docs/README.md` canonicos e consistentes.
  2. `docs/COMANDOS_RAPIDOS.md` atualizado para uv-first.
  3. `docs/ARQUITETURA_IMPORTACAO.md` ativo simplificado e snapshot arquivado.
  4. `docs/TROUBLESHOOTING*.md` ativos simplificados e snapshots arquivados.
  5. `docs/HISTORICO_RELEASES.md` atualizado com governanca de docs.
- Regra de continuidade:
  1. usar somente o bloco do topo deste arquivo.
  2. consultar `docs/archive/` apenas para contexto historico.
- Residuos locais fora de escopo mantidos:
  1. `data/ssas.db`
  2. `config/settings.json.bak_20260308_212715`

## HISTORICAL SNAPSHOT 2026-03-09 17:35

- Baseline ativo de versao/documentacao: `4.32`.
- Refinamento de governanca documental concluido:
  1. somente o bloco de topo e fonte ativa.
  2. historico antigo foi movido para arquivo dedicado para reduzir ambiguidade.
  3. referencias de release evitam logs efemeros.
- Escopo desta rodada:
  1. apenas docs e metadados de versao.
  2. nenhum runtime alterado (`core/gui/armazenamento/extracao/interface/tests`).
- Residuos locais fora de escopo mantidos:
  1. `data/ssas.db`
  2. `config/settings.json.bak_20260308_212715`

## REGRAS DE INTERPRETACAO

1. Este bloco do topo e a unica fonte ativa para continuidade.
2. Todo historico de iteracoes anteriores deve ser lido no arquivo de arquivo.
3. Em caso de conflito, prevalece sempre o topo deste arquivo.

## ARQUIVO HISTORICO

- Historico completo anterior (ate 2026-03-09 17:35):
  - `docs/archive/NEXT_CHAT_MIGRATION_legacy_until_20260309_1735.md`

## CHECKLIST DE CONTINUIDADE

1. confirmar branch alvo antes de editar.
2. validar residuos locais fora de escopo antes de commit.
3. registrar inicio/fim da sessao em `docs/RECOVERY_BACKLOG.md`.
4. atualizar `docs/AGENTS_HANDOFF_NEXT_CYCLE.md` no mesmo slice.

## AVISO FINAL - NAO COLAR NOVO ESTADO AQUI EMBAIXO

1. o fim deste arquivo e historico de auditoria, nao area de trabalho viva.
2. nao colar nova verdade atual, pendencias novas, status de branch ou logs soltos abaixo deste aviso.
3. qualquer estado atual novo deve entrar no topo, dentro de `CURRENT TRUTH`.
4. qualquer pendencia nova deve entrar no topo deste arquivo ou em `docs/RECOVERY_BACKLOG.md`, por prioridade.
5. colagem solta no fim deste arquivo aumenta custo de leitura, cria contexto stale e ja causou regressao de processo.

<!-- DOC_SYNC_MAC: 2026-03-29 host-agnostic paths, continue from repo root on macOS -->
