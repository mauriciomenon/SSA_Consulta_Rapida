# Next Chat Migration Guide

Arquivo historico arquivado.
Todos os blocos `CURRENT TRUTH` abaixo sao snapshots preservados e nao representam a fonte ativa atual.

Fontes ativas atuais:
1. `AGENTS.md`
2. `docs/NEXT_CHAT_MIGRATION.md`
3. `docs/AGENTS_HANDOFF_NEXT_CYCLE.md`

## CURRENT TRUTH 2026-03-09 17:35 - start from here

- Refinamento de governanca documental concluido sem runtime:
  1. `NEXT_CHAT` e `HANDOFF` com regra explicita de interpretacao do topo autoritativo.
  2. `RECOVERY_BACKLOG` com fechamento de validacao executada no sync 4.32.
  3. `HISTORICO_RELEASES` ajustado para evitar acoplamento com logs efemeros.
- Baseline ativo permanece `4.32`.
- Escopo nao tocado:
  1. runtime de importacao/GUI/DB.
  2. testes e codigo de producao.
- Residuos locais fora de escopo mantidos:
  1. `data/ssas.db`
  2. `config/settings.json.bak_20260308_212715`

## CURRENT TRUTH 2026-03-09 08:41 - start from here

- Baseline ativo promovido para `4.32` neste ciclo.
- Sincronizacao de versao concluida em:
  1. `VERSION`
  2. `config/version.json`
  3. `README.md`
  4. `docs/HISTORICO_RELEASES.md`
  5. `docs/FILTER_TAB_OPTIMIZATIONS.md`
  6. `docs/GUIA_MIGRACAO_NOVA_INSTALACAO.md`
- Regra de leitura para continuidade:
  1. usar este bloco como ponto inicial.
  2. tratar blocos abaixo como historico de iteracoes anteriores.
- Estado de residuos locais fora de escopo mantido:
  1. `data/ssas.db` (local)
  2. `config/settings.json.bak_20260308_212715` (backup local)

### Regras de interpretacao deste arquivo

1. Apenas o primeiro bloco `CURRENT TRUTH` no topo e fonte ativa.
2. Blocos `CURRENT TRUTH` abaixo do topo devem ser tratados como snapshot historico.
3. Divergencias de versao em blocos antigos nao substituem o baseline ativo.

## CURRENT TRUTH 2026-03-09 06:45 - start from here

- Pacote unico executado sem etapas manuais:
  1. backup de DB
  2. full rescan real
  3. consolidacao automatica de metricas e saude
  4. comparativo com baseline anterior
- Evidencias principais:
  1. `logs/import_run_20260309_010936_830587.json`
  2. `logs/full_rescan_runtime_20260309_010934.log`
  3. `docs/indicios_importacao.md` (secao `Sessao 2026-03-09`)
  4. `logs/full_rescan_summary_20260309_063007.json`
- Resultado:
  1. `status=updated`, `result=true`
  2. `431/431` arquivos com sucesso
  3. `497162` linhas inseridas
  4. DB final sem drift (`id` presente, sem `nan*`, `integrity_check=ok`)
- Nota de interpretacao de tempo:
  1. `duration_seconds` total do run inclui tempo em loop CLI apos import.
  2. para comparar throughput de import, usar `run_file_processing_seconds=1251.979s`.

## CURRENT TRUTH 2026-03-09 01:05 - start from here

- Slice de performance focado entregue:
  1. sort de `num_reprogramacoes` com menor custo de memoria/copia.
  2. prewarm de cache de sort apos `on_data_loaded`.
  3. recompute de width no resize agora coalescido por timer restartavel unico.
- Mudancas tecnicas:
  1. `gui/gui_ssa.py`
     - `_sort_num_reprogramacoes_robust`: ordena por indice de `sort_keys`.
     - `_prime_num_reprogramacoes_sort_cache` + `_reset_num_reprogramacoes_sort_cache`.
     - `_schedule_resize_recompute` + `_on_resize_recompute_timeout`.
  2. `gui/ssa/gui_workers.py`
     - prewarm de cache de sort no fim de `on_data_loaded`.
  3. `tests/test_gui_filter_logic.py`
     - cobertura para prewarm de cache.
     - cobertura para coalescing de resize recompute.
- Validacao:
  1. `py_compile` pass
  2. `ruff` pass
  3. `ty` pass
  4. `pytest` focado -> `5 passed`
- Risco residual:
  1. primeira ordenacao ainda pode custar em base extrema.
  2. width recompute ainda ocorre em UI thread (agora sem explosao de chamadas por burst).

## CURRENT TRUTH 2026-03-09 00:30 - start from here

- Slice fechado para 3 pontos solicitados:
  1. `MEDIUM quality`: dedup de manutencao entre prunes de workers.
  2. `HIGH performance` (escopo local): cache de sort para `num_reprogramacoes` no clique de header.
  3. versao do guia de instalacao/help alinhada para `v4.31`.
- Mudancas tecnicas:
  1. `gui/ssa/gui_workers.py`:
     - helper comum `_process_expired_workers`;
     - helper comum `_drop_orphaned_worker_meta`;
     - ambos prunes reutilizam fluxo compartilhado.
  2. `gui/gui_ssa.py`:
     - `_build_num_reprogramacoes_sort_keys` + `_get_num_reprogramacoes_sort_keys`;
     - `_sort_num_reprogramacoes_robust` agora usa cache por dataset filtrado.
  3. `tests/test_gui_filter_logic.py`:
     - novo teste de reuso de cache no toggle de sort.
  4. `docs/GUIA_MIGRACAO_NOVA_INSTALACAO.md`:
     - cabecalho atualizado para `v4.31`.
- Validacao da rodada:
  1. `py_compile` pass
  2. `ruff` pass
  3. `ty` pass
  4. `pytest` focado -> `3 passed` + `19 passed`
- Risco residual mapeado para proximo ciclo:
  1. debts amplos de arquitetura/performance em `SSAMainWindow` permanecem fora de escopo.
  2. reescaneamento prompt/naming continua como tema de UX separado.
  3. semantica de tooltip/placeholder da busca geral precisa alinhar texto com modos avancados.
  4. hardening adicional no path opener pode ser aplicado em slice dedicado.
  5. lock contention potencial no prune global de workers requer medicao sob carga.

## CURRENT TRUTH 2026-03-09 00:04 - start from here

- Hotfix aplicado para 3 pontos de risco real:
  1. semantica: comentario de topo da busca alinhado ao comportamento real.
  2. security hardening: validacao de caminho em aberturas de arquivo/pasta.
  3. estabilidade worker: status update via helper seguro no load/rescan.
- Multi-OS confirmado na implementacao de menus de abertura:
  1. `QDesktopServices.openUrl` como caminho principal.
  2. fallback: `explorer` (Windows), `open` (macOS), `xdg-open` (Linux/Debian).
- Validacao da rodada:
  1. `py_compile` pass
  2. `ruff` pass
  3. `ty` pass
  4. `pytest` focado -> `19 passed`
- Debt mantido para ciclo proprio:
  1. duplicacao prune workers.
  2. naming/UX de `Reescanear` vs `prompt`.
  3. perf ampla de sort/recompute/canonical columns.

## CURRENT TRUTH 2026-03-08 23:05 - start from here

- Menus padronizados conforme grade final aprovada:
  1. `Arquivo`: `Recarregar Dados`, `Atualizar Dados`, `Exportar lista`, `Sair`.
  2. `Importacao`: `Importar XLS/XLSX externo`, `Atualizar Dados`, `Reescaneamento Completo`, 3 atalhos de pasta, `Consolidar arquivos de entrada`.
  3. `Database`: `Reescanear`, `Atualizar derivadas`, `Carregar outro DB`, `Compactar DB`.
  4. `Ajuda`: `Instalacao`, `Ajuda`.
- Prompt de `Reescanear` padronizado:
  1. texto informativo sem sufixo `(diff)`.
  2. botao `Atualizar Dados` (sem `(diff)`).
- Nova acao de ajuda:
  1. `Instalacao` abre `docs/GUIA_MIGRACAO_NOVA_INSTALACAO.md`.
- Validacao da rodada:
  1. `py_compile` pass
  2. `ruff` pass
  3. `ty` pass
  4. `pytest` focado -> `16 passed`

## CURRENT TRUTH 2026-03-08 22:28 - start from here

- Micro hardening de tema aplicado sem mudanca de layout:
  1. short-circuit extra em `_apply_global_palette` para evitar rebuild de QSS global quando cache de tema ja esta valido.
  2. cache da fonte reduzida de `details_text` com reuso quando base size nao muda.
- Cobertura de regressao adicionada:
  1. teste de reuso do cache de fonte.
  2. teste de skip de rebuild global de QSS com cache valido.
- Validacao da rodada:
  1. `py_compile` pass
  2. `ruff` pass
  3. `ty` pass
  4. `pytest` focado de tema -> `4 passed`
- Debt mantido para ciclo dedicado:
  1. separar responsabilidades em `_apply_global_palette`.
  2. reduzir custo de setStyleSheet em massa em `_apply_theme_widget_styles`.

## CURRENT TRUTH 2026-03-08 21:38 - start from here

- Tema agora abre em caixa/dialogo (como ajuda), nao menu popup.
- Barra principal simplificada conforme pedido:
  1. removeu `Carregar Outro DB`, `Abrir Pasta`, `Ajuda`.
  2. manteve `Carregar Dados`, `Reescanear`, `Atualizar Derivadas`.
  3. `Tema` ficou no lado direito.
- `Database > Avancado` com linguagem amigavel:
  1. acao segue `Compactar DB`.
  2. prompt/status usam texto de compactacao + atualizacao de estatisticas.
- Validacao da rodada:
  1. `48 passed` nos testes focados de menu/reescaneamento/worker.

## CURRENT TRUTH 2026-03-08 21:06 - start from here

- Menus atualizados conforme texto aprovado:
  1. `Arquivo` com rotulos finais (Recarregar Dados, Reescanear, Atualizar Dados, etc.).
  2. `Importacao`, `Database`, `Database > Avancado`, `Opcoes` ajustados.
  3. novo menu top-level `Ajuda`.
- Ajuste de box de reescaneamento:
  1. prompt de modo com texto refinado (`Reescanear`, `Atualizar Dados (diff)`, `Reescaneamento Completo`).
  2. diff sem alteracoes nao aparece mais como falha vermelha.
  3. status final referencia `Recarregar Dados`.
- Validacao:
  1. `48 passed` nos testes focados de menu e reescaneamento.

## CURRENT TRUTH 2026-03-08 20:29 - start from here

- Menu de opcoes clarificado:
  1. `Abrir arquivo de opcoes (editor externo)` abre `settings.json` principal.
  2. backup continua sendo criado antes de abrir.
- Nova acao de seguranca operacional:
  1. `Restaurar opcoes padrao`
  2. fluxo: carrega defaults -> confirma -> backup -> grava em `settings.json`.
- Resultado:
  1. nao ha mais ambiguidade sobre editar backup vs arquivo principal.
  2. restauracao padrao virou acao explicita ao lado da abertura de arquivo.
- Validacao da rodada:
  1. `pytest -q tests/test_gui_menu_import_external.py tests/test_open_docs_folder_nonblocking.py tests/test_gui_workers_rescan_data.py` -> `19 passed`

## CURRENT TRUTH 2026-03-08 20:10 - start from here

- `Arquivo` foi refinado como fluxo diario:
  1. ordem por uso + separadores.
  2. atalhos diarios mantidos no topo.
- Menus de origem preservados:
  1. `Importacao` continua com operacoes de processamento e agora inclui diff/importar.
  2. `Database` e `Opcoes` mantidos.
- Hardening anteriores mantidos:
  1. pasta inexistente pergunta e cria sob confirmacao.
  2. menu `Tema` funciona com fallback no cursor.
- Validacao da rodada:
  1. `pytest -q tests/test_gui_menu_import_external.py tests/test_open_docs_folder_nonblocking.py tests/test_gui_workers_rescan_data.py` -> `18 passed`

## CURRENT TRUTH 2026-03-08 19:56 - start from here

- Menu operacional ajustado para uso diario:
  1. `Arquivo` agora concentra atalhos principais sem remover menus de origem.
  2. `DB` foi renomeado para `Database` para melhor clique/leitura.
- Equivalencia e navegacao:
  1. `Arquivo` ganhou atalhos de reescaneamento (diff/perguntar/completo), derivadas, consolidacao, tema e ajuda.
  2. `Importacao`, `Database` e `Opcoes` permanecem com as mesmas operacoes especializadas.
- Pastas:
  1. ao abrir pasta inexistente, agora a GUI pergunta se deseja criar.
  2. se confirmado, cria e abre.
- Tema:
  1. fallback corrigido para abrir menu de tema no cursor quando acionado por menu action.
- Validacao da rodada:
  1. `pytest -q tests/test_gui_menu_import_external.py tests/test_open_docs_folder_nonblocking.py tests/test_gui_workers_rescan_data.py` -> `18 passed`

## CURRENT TRUTH 2026-03-08 19:32 - start from here

- Metadata de versao runtime alinhada com release:
  1. `VERSION=4.31`
  2. `config/version.json.version_short=4.31`
  3. `main.py --version` retorna `4.31`
- Equivalencia principal botao x menu reforcada:
  1. botao `Reescanear` agora tem equivalente no menu:
     - `Importacao > Reescaneamento (perguntar modo)`
  2. botao `Ajuda` agora tem equivalente no menu:
     - `Opcoes > Ajuda`
- Validacao da rodada:
  1. `pytest -q tests/test_gui_menu_import_external.py tests/test_open_docs_folder_nonblocking.py tests/test_gui_workers_rescan_data.py` -> `17 passed`

## CURRENT TRUTH 2026-03-08 19:23 - start from here

- Baseline local de documentacao: `4.31`.
- Menus da GUI reorganizados por atividade:
  1. `Arquivo`
  2. `Importacao`
  3. `DB`
  4. `Opcoes`
- Ajustes de nomenclatura aprovados:
  1. `Abrir pasta de entrada` (sem `docs_entrada` no texto)
  2. `Abrir pasta processadas`
  3. `Abrir pasta sem sobreviventes`
  4. `Reescaneamento completo`
- Operacao avancada isolada:
  1. `DB > Avancado > Executar VACUUM/ANALYZE`
  2. handler novo: `run_vacuum_analyze` (manual)
- Validacao da rodada:
  1. `pytest -q tests/test_gui_menu_import_external.py tests/test_open_docs_folder_nonblocking.py tests/test_gui_workers_rescan_data.py` -> `17 passed`

## CURRENT TRUTH 2026-03-08 19:02 - start from here

- Baseline local de documentacao: `4.31`.
- Menu `DB` ganhou atalhos operacionais de pasta:
  1. `Abrir pasta processadas`
  2. `Abrir pasta processadas/nosurvivor`
- Implementacao:
  1. `gui/gui_ssa.py` adicionou:
     - `open_processadas_folder`
     - `open_nosurvivor_folder`
     - helper `_open_folder_non_blocking(folder_path, folder_label)`
  2. `open_docs_folder` agora usa o mesmo helper (comportamento mantido).
- Cobertura de regressao:
  1. `tests/test_gui_menu_import_external.py`:
     - menu `DB` agora com `10` acoes
     - testes de roteamento para os 2 atalhos novos
- Validacao da rodada:
  1. `pytest -q tests/test_gui_menu_import_external.py tests/test_open_docs_folder_nonblocking.py tests/test_gui_workers_rescan_data.py` -> `15 passed`

## CURRENT TRUTH 2026-03-08 18:36 - start from here

- Baseline local de documentacao: `4.31`.
- Reescaneamento agora explicito no menu `DB`:
  1. `Reescanear Diff (hash)` -> sem prompt, `force_import=false`
  2. `Reescanear Full (zera e reprocessa)` -> sem prompt, `force_import=true`
- Compatibilidade mantida:
  1. botao/acao antiga `rescan_data` segue com `prompt` (escolha de modo).
- Implementacao tecnica:
  1. `gui/ssa/gui_workers.py`: `rescan_data(..., rescan_mode=\"prompt|diff|full\")`
  2. `gui/gui_ssa.py`: `rescan_diff_data` e `rescan_full_data`
- Validacao da rodada:
  1. `pytest -q tests/test_gui_menu_import_external.py tests/test_gui_workers_rescan_data.py tests/test_open_docs_folder_nonblocking.py` -> `13 passed`

## CURRENT TRUTH 2026-03-08 18:32 - start from here

- Baseline local de documentacao: `4.31`.
- GUI menu concluido (slice 2/2):
  1. menu `DB` agora inclui:
     - `Consolidar arquivos de entrada`
     - `Abrir opcoes (backup failsafe)`
  2. sem mudanca de layout/posicao da toolbar.
- Failsafe de opcoes entregue:
  1. `open_settings_file_with_backup` cria backup timestampado antes de abrir.
- Consolidacao dedicada entregue:
  1. `consolidate_input_files` usa ultimo `import_run_*.json` com `file_reports`.
  2. roteia para `processadas/` ou `processadas/nosurvivor/` por `rows_inserted`.
  3. arquivos sem evidencia no report ficam em `docs_entrada` (`pending`).
- Validacao da rodada:
  1. `pytest -q tests/test_gui_menu_import_external.py tests/test_open_docs_folder_nonblocking.py tests/test_gui_workers_rescan_data.py` -> `11 passed`

## CURRENT TRUTH 2026-03-08 18:19 - start from here

- Baseline local de documentacao: `4.31`.
- GUI menu iniciado (slice 1/2) sem alterar layout da toolbar:
  1. menu `Arquivo` e `DB` adicionados em `gui/gui_ssa.py`
  2. acoes agrupadas para importacao/db/exportacao/tema usando handlers existentes
- Nova funcao de importacao externa:
  1. `import_external_excel_files` copia XLS/XLSX externo para `docs_entrada`
  2. sem sobrescrita silenciosa (sufixo `__N`)
  3. retorna sumario (`copied/skipped/failed`) e atualiza status
- Testes focados novos:
  1. `tests/test_gui_menu_import_external.py` (menu + copia com colisao)
  2. pacote de regressao da rodada: `9 passed`
- Docs baseline promovidos:
  1. `README.md` agora em `v4.31`.

## CURRENT TRUTH 2026-03-08 17:56 - start from here

- Baseline local de documentacao: `4.31`.
- Pendentes de organizacao de importacao foram fechados neste ciclo.
- Politica de short-circuit agora vem de config:
  1. `config/default_settings.json` -> `import_settings.upsert_short_circuit_policy`
  2. valores aceitos: `consulta_only`, `no_short`, `all_short`
  3. invalido cai para `consulta_only`
- Full rescan agora aplica enforcement de subpastas/politica no runtime:
  1. `include_processadas=false`
  2. `ignore_nosurvivor=true`
  3. `move_processed_after_import=false`
- Consolidacao de alias de tabela no upsert:
  1. `database_upsert_logic` agora usa o resolvedor unico de `database.py`
  2. remove duplicacao de loops locais com `ssa_table/ssas/ssa_chamados`
- Regras operacionais finais de subpasta:
  1. full rescan ignora `processadas/` e `nosurvivor/`
  2. incremental/controlado pode mover para `processadas/` e `processadas/nosurvivor/`
- Validacao focada desta rodada:
  1. `pytest -q tests/test_default_settings_import_settings.py tests/test_import_run_report.py tests/test_upsert_fast_path.py tests/test_database_upsert_canonical_write.py` -> `33 passed`
  2. `pytest -q tests/test_app_logic_postprocess_moves.py tests/test_app_logic_full_rescan_lock.py` -> `4 passed`

## CURRENT TRUTH 2026-03-08 17:39 - start from here

- Comparativo final A/B consolidado (duas rodadas):
  1. tabela base: `logs/move_policy_comparison_20260308_172923.csv`
  2. familias por insert: `logs/move_policy_family_insert_20260308_172923.csv`
  3. visual: `logs/move_policy_comparison_20260308_172923.svg`
- Leitura de desempenho:
  1. par com `.xls` (`on_first` vs `off_second`):
     - `move_on` pior em `+35.36%` (duracao)
     - `move_on` pior em `+36.08%` (`sum_insert`)
  2. par so `.xlsx` (`off_first` vs `on_second`):
     - `move_on` pior em `+15.67%` (duracao)
     - `move_on` pior em `+16.37%` (`sum_insert`)
  3. no par `.xlsx`, `move_on` piorou todas as familias (destaque: `Consulta SSA`, `Todas as SSAs`, `SSAs Executadas`).
- Diretriz operacional ativa:
  1. full rescan pesado: `move_processed_after_import=false`.
  2. incremental/controlado: `move` permitido.
  3. runtime reforca isso: `force_import=true` desativa `move` com warning.
- Runtime/teste associados a esta diretriz:
  1. `core/app_logic.py`: warning + desativacao de move no full rescan.
  2. `tests/test_import_run_report.py`: cobertura dedicada da regra.
  3. validacao focada mais recente: `pytest -q tests/test_import_run_report.py` -> `7 passed`.

## CURRENT TRUTH 2026-03-08 17:18 - start from here

- Benchmark full A/B reverso concluido com evidencia:
  1. `logs/full_ab_move_policy_reverse_summary_20260308_171101.json`
  2. no par reverso (`off_first` -> `on_second`), `move_on` ficou mais lento:
     - duracao: `+15.67%`
     - `sum_insert`: `+16.37%`
- Benchmark full anterior (par normal) continua valido e aponta mesmo sinal:
  1. `logs/full_ab_move_policy_summary_20260308_154314.json`
  2. `move_on` mais lento:
     - duracao: `+35.36%`
     - `sum_insert`: `+36.08%`
- Conclusao de operacao:
  1. para full rescan pesado, manter `move_processed_after_import=false`.
  2. manter `move` para fluxo incremental/controlado.
  3. runtime agora reforca essa politica: em `force_import=true`, o move e desativado com warning explicito.
- Instrumentacao nova entregue em runtime (sem mudar comportamento):
  1. `core/app_logic.py` agora grava no `import_run_*.json`:
     - `durations.sum_file_extraction_seconds`
     - `durations.sum_file_validation_seconds`
     - `durations.sum_file_insert_seconds`
     - `durations.run_file_processing_seconds`
     - `durations.run_postprocess_move_seconds`
     - `durations.run_success_cache_update_seconds`
     - `durations.run_deterministic_cache_update_seconds`
  2. cobertura adicionada em `tests/test_import_run_report.py`.
- Validacao da rodada:
  1. py_compile + ruff + ty dos arquivos tocados: pass
  2. `pytest -q tests/test_import_run_report.py`: `6 passed`
  3. `pytest -q tests/test_app_logic_postprocess_moves.py tests/test_app_logic_full_rescan_lock.py`: `4 passed`
- Artefatos comparativos prontos:
  1. `logs/move_policy_comparison_20260308_172923.csv`
  2. `logs/move_policy_family_insert_20260308_172923.csv`
  3. `logs/move_policy_comparison_20260308_172923.svg`

## CURRENT TRUTH 2026-03-08 12:44 - start from here

- Full rescan real com move pos-processamento ligado foi executado e concluido.
- Evidencia:
  1. run report: `logs/import_run_20260308_115621_528621.json`
  2. resumo: `logs/move_policy_full_rescan_summary_20260308_115621.json`
  3. baseline usado: `logs/import_run_20260307_213713_316719.json`
- Resultado funcional:
  1. `431` candidatos, `431` sucesso, `0` erro
  2. `rows_inserted_total=497162`
  3. `rows_removed_invalid_identity_total=2763`
- Resultado de desempenho:
  1. baseline `354.675s`
  2. run com move `2791.239s`
  3. degradacao aproximada `+687%`
  4. impacto distribuiu por todas as familias (insert_seconds), nao ficou restrito a uma unica familia.
- Diretriz imediata:
  1. manter `move_processed_after_import=false` em full rescan pesado.
  2. manter move ligado apenas para fluxo incremental/controlado ate novo diagnostico de performance.
- Higiene:
  1. diretorio temporario de execucao foi removido (`data/full_rescan_move_policy_20260308_115621`).

## CURRENT TRUTH 2026-03-08 11:54 - start from here

- Validacao runtime de `move_processed_after_import` concluida sem alterar codigo:
  1. mini importacao com 2 arquivos controlados (1 valido + 1 sem sobreviventes).
  2. run report: `logs/import_run_20260308_115306_645961.json`.
  3. resultado confirmado:
     - `ok.xlsx` -> `processadas/ok.xlsx`
     - `empty.xlsx` -> `processadas/nosurvivor/empty.xlsx`
     - cache com chaves finais movidas
     - DB final do mini teste com `1` linha
- Contagens do report:
  1. `total_candidates=2`
  2. `success_count=2`
  3. `rows_removed_invalid_identity_total=1`
  4. `rows_inserted_total=1`
- Higiene:
  1. diretorio temporario do teste foi removido apos validacao.
  2. nenhum arquivo de codigo alterado neste slice.

## CURRENT TRUTH 2026-03-08 00:50 - start from here

- Regressao de testes fechada apos mudanca de assinatura em `core/app_logic.py`:
  1. `tests/test_import_deterministic_failure_cache.py` tinha mocks com 2 args para `_update_cache_for_deterministic_failures`.
  2. runtime atual usa 3 args; mocks foram atualizados.
- Nova cobertura de fluxo pos-importacao:
  1. `tests/test_import_run_report.py` agora valida move de arquivos para:
     - `processadas/` (`record_count > 0`)
     - `processadas/nosurvivor/` (`record_count == 0`)
  2. teste tambem garante que `_update_cache_after_import` recebe caminhos finais movidos.
- Evidencia da rodada:
  1. `pytest -q tests/test_import_deterministic_failure_cache.py tests/test_import_run_report.py tests/test_app_logic_postprocess_moves.py` -> `11 passed`
  2. py_compile + ruff + ty dos testes alterados -> pass
  3. kluster clean.

## CURRENT TRUTH 2026-03-08 00:37 - start from here

- Config padrao agora declara `import_settings` explicitamente em `config/default_settings.json`.
- Chaves formalizadas:
  1. `include_processadas_in_full_rescan`
  2. `processadas_subdir`
  3. `ignore_nosurvivor_in_full_rescan`
  4. `nosurvivor_subdir`
  5. `move_processed_after_import`
  6. `route_zero_survivor_to_nosurvivor`
- Backup local de seguranca feito antes da mudanca:
  1. `config/default_settings.json.bak_20260308_003720`
- Regressao coberta:
  1. `tests/test_default_settings_import_settings.py`
  2. pacote focado da rodada: `13 passed`
- Sem mudanca de runtime neste slice:
  1. apenas explicitacao no config padrao e teste de contrato.

## CURRENT TRUTH 2026-03-08 00:29 - start from here

- Slice de pos-processamento de arquivo entregue no runtime padrao:
  1. `core/app_logic.py` agora suporta mover arquivos processados para `processadas/*` sob flag.
  2. zero-survivor (`record_count==0`) pode ser roteado para `processadas/nosurvivor` via flag.
  3. movimentacao acontece no fim do fluxo (apos promocao do DB candidato em full rescan), reduzindo risco de perder input em run com falha.
- Flags de `import_settings` usadas neste slice:
  1. `move_processed_after_import` (default `false`)
  2. `route_zero_survivor_to_nosurvivor` (default `true`)
  3. `processadas_subdir` e `nosurvivor_subdir` (defaults `processadas` e `nosurvivor`)
- Cache:
  1. update de cache usa caminho final movido quando o flag esta habilitado.
  2. evita reprocessamento acidental apos mover arquivo.
- Validacao:
  1. `pytest -q tests/test_app_logic_postprocess_moves.py tests/test_caching.py tests/test_app_logic_full_rescan_lock.py tests/test_import_run_report.py` -> `19 passed`
  2. py_compile + ruff + ty -> pass
  3. kluster clean no patch.

## CURRENT TRUTH 2026-03-08 00:24 - start from here

- Slice de discovery/cache para `processadas` fechado com risco baixo:
  1. runtime de import agora le `import_settings` (com defaults seguros) via `core/app_logic.py`.
  2. discovery de arquivos pode incluir `docs_entrada/processadas` e ignorar `processadas/nosurvivor`.
  3. comportamento default permanece igual ao atual (`include_processadas=false`).
- Cache/hashing reforcado:
  1. chaves de cache usam caminho relativo no `docs_dir` quando disponivel.
  2. fallback por basename mantido para cache legado.
  3. colisoes de nomes iguais em subpastas deixam de sobrescrever hash.
- Testes e gates:
  1. `pytest -q tests/test_caching.py tests/test_app_logic_full_rescan_lock.py` -> `12 passed`
  2. py_compile + ruff + ty dos arquivos tocados -> pass
  3. kluster clean para `core/app_logic.py`, `utils/caching.py`, `tests/test_caching.py`
- Proximo passo planejado:
  1. Slice B de movimentacao pos-processamento (`processadas` e `nosurvivor`) por flag, sem tocar robust nem GUI layout.

## CURRENT TRUTH 2026-03-07 22:59 - start from here

- Sentinela A/B final do hot path (4 arquivos criticos, DB isolado por politica):
  1. `consulta_only`: `40.064s`
  2. `no_short`: `40.590s` (`+1.31%`)
  3. `all_short`: `41.644s` (`+3.95%`)
  4. decisao: manter `consulta_only` como policy padrao.
- Evidencia preservada em logs:
  1. `logs/import_run_20260307_224052_346788.json`
  2. `logs/import_run_20260307_224225_365396.json`
  3. `logs/import_run_20260307_224305_447338.json`
  4. `logs/import_run_20260307_224346_053142.json`
- Limpeza local executada:
  1. removidos 4 diretorios `data/sentinel_*` criados nesta rodada.
  2. nao houve alteracao de runtime/codigo neste sub-slice.
- Residuos locais ainda fora de escopo (nao subir):
  1. `data/ablation_all_short/` (~106M)
  2. `data/ablation_consulta_only/` (~106M)
  3. `data/ablation_no_short/` (~106M)
  4. tracked modified antigos: `armazenamento/database.py`, `armazenamento/database_integrity.py`, `armazenamento/database_validation.py`, `core/app_logic.py`, `data/ssas.db`, `docs_entrada/Copia de SSAPendSectorEjecutorConsulta_26-02-2021.xls`, `extracao/extractor.py`, `tests/test_db_reset_and_upsert.py`.

## CURRENT TRUTH 2026-03-07 22:23 - start from here

- Slice fechado no hot path de upsert sem tocar robust:
  1. `armazenamento/database_upsert_logic.py` agora usa cache lazy de `existing_row` tambem no ramo sem short-circuit.
  2. tuple de comparacao (`existing_chunk_tuple_by_ssa`) agora so e atualizado quando `enable_exact_overlap_short_circuit=True`.
  3. `_perform_upsert` foi quebrado de forma minima com helper `_collect_chunk_upsert_delta` para reduzir complexidade local.
  4. custo de inicializacao por chunk no ramo normal foi reduzido sem alterar regra de merge.
- Teste novo:
  1. `tests/test_upsert_fast_path.py::test_perform_upsert_non_short_policy_uses_lazy_existing_cache`
- Validacao desta rodada:
  1. py_compile + ruff + ty: pass
  2. `pytest -q tests/test_upsert_fast_path.py`: `22 passed`
  3. kluster: `1 P4 -> clean` no mesmo slice.
- Escopo preservado:
  1. nenhum ajuste em `extracao/*` nem em robust.
  2. nenhuma mudanca em GUI/layout.

## CURRENT TRUTH 2026-03-07 22:14 - start from here

- Contrato de arquitetura confirmado em testes:
  - upsert: `consulta_only`, `no_short`, `all_short` permanecem politicas separadas em `armazenamento/database_upsert_logic.py`.
  - `consulta_only` e valido apenas para chaves de origem `Consulta SSA*`.
  - `all_short` ativa em chunk de arquivo unico, sem exigir prefixo `Consulta SSA`.
  - `no_short` desliga atalho de overlap para preservar fluxo seguro.
  - `robust` **nao** esta no caminho de `extract_data_from_excel` (`core/app_logic.py -> extract_data_from_excel`).
  - `robust` e exclusivo no caminho `read_report` via `extract_excel_robust`.
- Evidencia de teste adicionada:
  - `tests/test_upsert_fast_path.py`
  - `tests/test_extracao.py`
- Validação desta rodada:
  - `uv run --python 3.13 pytest -q tests/test_extracao.py tests/test_upsert_fast_path.py` -> `43 passed`.

## CURRENT TRUTH 2026-03-07 22:02 - start from here

- Resultado de benchmark A/B desta rodada final:
  1. `SSA_UPSERT_SHORT_CIRCUIT_POLICY=consulta_only` manteve-se como melhor default
  2. tempos em banco candidato com 431 arquivos reais:
     - consulta_only: `354.675s`
     - no_short: `479.403s`
     - all_short: `654.330s`
  3. decisoes de risco e escala:
     - manter `consulta_only` como politica padrão
     - **nao adotar** `no_short` e `all_short` como default
  4. evidencia objetivo:
     - `logs/import_run_20260307_213713_316719.json`
     - `logs/import_run_20260307_214318_967821.json`
     - `logs/import_run_20260307_215122_180024.json`
     - `data/ablation_consulta_only/ssas.db`
     - `data/ablation_no_short/ssas.db`
     - `data/ablation_all_short/ssas.db`

- Branch ativa: `codex/sprint-importacao-grave-fixes-20260305`.
 - Antes de avaliar performance no upsert, ler:
   1. `docs/ARCHITECTURE_OVERVIEW.md`
   2. `docs/ARCH_IMPORT_PIPELINE.md`
   3. `docs/ARCH_DB_UPSERT.md`
   4. `docs/ARCH_VALIDATION_AND_INTEGRITY.md`
   5. `docs/ARCH_GUI_LOAD_AND_FILTER.md`
 - Estado atual do upsert:
   1. foi implementada policy por variavel para short-circuit de overlap exato em `_perform_upsert()`
   2. policy ativa em operação e validada por teste unitario: default `consulta_only`
   3. novas options: `no_short` e `all_short` para A/B controlado
 - Residuos fora de escopo continuam fora do commit:
   1. `data/ssas.db`
   2. `docs_entrada/Copia de SSAPendSectorEjecutorConsulta_26-02-2021.xls`
   3. `tests/test_db_reset_and_upsert.py`
   4. `data/db_backups/`
   5. `data/tmp_import_sample/`
   6. `shared/semantic_duplicate_resolution.py`

## CURRENT TRUTH 2026-03-07 13:35 - start from here

- Branch ativa: `codex/sprint-importacao-grave-fixes-20260305`.
- Baseline local de release: `4.30`.
- Slice entregue no caminho padrao de DB/import:
  1. `armazenamento/database.py`
     - proibiu `if_exists='replace'` para `ssa_table`, `ssas` e `ssa_chamados`
     - manteve `replace` apenas para tabelas genericas nao-SSA
     - ganhou rollback explicito em falha e modularizacao interna minima sem trocar a API publica
  2. `armazenamento/database_upsert_logic.py`
     - bucket de `chunk_size` do upsert agora:
       - ate `1000` linhas -> `100`
       - acima de `1000` -> `250`
     - `_prepare_upsert_target_row()` agora corta no-op cedo:
       - linha mais antiga nao substitui
       - merge identico nao gera `DELETE + append`
- Evidencia quantitativa mais importante:
  1. o benchmark correto do merge real e sobre tabela ja populada, nao tabela vazia
  2. no arquivo `Todas as SSAs - 18-08-2022_1144AM.xlsx`:
     - `chunk_size=100` -> `95.3781s`
     - `chunk_size=250` -> `75.8729s`
     - `chunk_size=500` -> `95.1726s`
  3. depois do short-circuit:
     - `resolved_chunk_size=250`
     - `seconds=44.9060`
     - `processed=0`
     - `rows_after=18513`
- Gates focados do slice:
  1. `py_compile`: pass
  2. `ruff`: pass
  3. `ty`: pass
  4. `pytest tests/test_database.py tests/test_upsert_fast_path.py`: `22 passed`
- Importante:
  1. houve um full rescan real iniciado com a heuristica intermediaria errada (`500`) e ele foi cancelado apos evidenciar regressao forte no merge real
  2. essa regressao ja foi diagnosticada e corrigida
  3. o rerun final do full rescan ja foi executado com sucesso:
     - report: `logs/import_run_20260307_135928_727735.json`
     - log: `logs/full_rescan_runtime_20260307_135927.log`
     - `result=True`
     - `duration_seconds=930.885`
     - DB final: `76426` linhas, `76426` SSAs distintas, `82` colunas, `0` `BLOB` em `semana_programada`
  4. delta agregado contra a baseline anterior (`logs/import_run_20260307_102956_247952.json`):
     - tempo total: `1161.133s` -> `930.885s`
     - ganho: `-19.83%`
  5. melhoria pesada confirmada:
     - `Todas as SSAs - 14-07-2022_1010AM - Copia.xlsx`: `36.294s` -> `16.774s`
     - `Todas as SSAs - 18-08-2022_1144AM.xlsx`: `19.083s` -> `12.348s`
  6. regressao localizada ainda aberta:
     - `Consulta SSA - 02-03-2026_0540PM.xlsx`: `10.050s` -> `32.887s`
     - `SSAscomReprogramações_07-01-2026_0225PM.xlsx`: `10.537s` -> `17.922s`
- Estado local fora de escopo, nao comitar:
  1. `data/ssas.db`
  2. `docs_entrada/Copia de SSAPendSectorEjecutorConsulta_26-02-2021.xls`
  3. `tests/test_db_reset_and_upsert.py`
  4. `data/db_backups/`
  5. `data/tmp_import_sample/`
  6. `shared/semantic_duplicate_resolution.py`

## CURRENT TRUTH 2026-03-07 00:39 - start from here

- Branch ativa: `codex/sprint-importacao-grave-fixes-20260305`.
- Baseline local de release: `4.30`.
- Fechamento tecnico do sprint:
  1. `core.app_logic.py` fechou o ajuste local do cache de busca e do matching `prefix/suffix/exact` com separador de campo, sem warnings de regex e com `20 passed` nos testes focados.
  2. a reclamacao ampla do kluster sobre `rule_13/rule_23` ficou como decisao intencional:
     - nao reintroduzir parser exotico `OR/OU`
     - filtros de coluna da GUI continuam com OR no fluxo proprio de mixin/worker, nao pelo parser geral
- Comparacao direta padrao vs robust no corpus completo, em ambiente isolado:
  1. artefato consolidado: `LocalTemp/compare_standard_vs_robust_20260306_234004/comparison_summary.json`
  2. padrao:
     - report: `logs/import_run_20260306_234004_171299.json`
     - elapsed: `1707.121s`
     - agregados:
       - `extracao=157.886s`
       - `validacao=221.986s`
       - `insercao=1314.608s`
     - DB final: `76426` linhas, `82` colunas, sem `nan_*`, sem `BLOB` em `semana_programada`
  3. robust:
     - report: `logs/import_run_20260307_000831_376554.json`
     - elapsed: `1812.105s`
     - agregados:
       - `extracao=530.664s`
       - `validacao=160.659s`
       - `insercao=1111.881s`
     - DB final: `76426` linhas, `84` colunas, sem `nan_*`, mas com `sn` e `sn_1`
  4. delta:
     - padrao foi `6.15%` mais rapido no total
     - robust foi `236.106%` mais lento em extracao
     - robust foi `27.627%` mais rapido em validacao
     - robust foi `15.421%` mais rapido em insercao
  5. diferenca de linhas:
     - robust extraiu `2` linhas a menos
     - so em duplicatas exatas de:
       - `Todas as SSAs - 14-07-2022_1010AM - Copia.xlsx`
       - `Todas as SSAs - 18-08-2022_1144AM.xlsx`
     - DB final permaneceu identico em linhas e `numero_ssa` distintos
- Leitura operacional:
  1. o gargalo dominante ainda e o merge/upsert
  2. o robust nao vence no fim-a-fim neste estado do branch
  3. o robust ainda carrega debt proprio de schema/cabecalho, visivel em `sn`, `sn_1` e nos warnings repetidos de sanitizacao de colunas dinamicas
- Proximo foco recomendado:
  1. atacar performance do upsert com benchmark controlado
  2. ou atacar cleanup especifico do caminho robust (`sn`, `sn_1`, `desde.1`, `ate.1`) se o objetivo for maturar esse caminho

## CURRENT TRUTH 2026-03-07 10:21 - start from here

- Branch ativa: `codex/sprint-importacao-grave-fixes-20260305`.
- Baseline local de release: `4.30`.
- Slice entregue no robust:
  1. `utils/robust_importer.py` agora nunca preserva duplicatas pontuadas como nome final de coluna.
  2. duplicatas semanticas conhecidas continuam indo para canones dedicados:
     - `SN` -> `sn_retirado`, `sn_instalado`, `sn_extra`
     - `desde/ate` -> sufixos com underscore
     - `Numero da SSA.1/.2`, `Setor Emissor.1/.2`, `Setor Executor.1/.2`, `Situacao.1/.2` -> colunas relacionadas canonicas
  3. duplicata pontuada desconhecida no robust agora vira sufixo com underscore, nunca com ponto.
- Evidencia tecnica:
  1. `uv run --python 3.13 pytest -q tests/test_robust_importer.py tests/test_real_spreadsheet_import.py tests/test_import_novas_colunas.py` -> `15 passed`
  2. scan real do corpus robust:
     - `TOTAL 431`
     - `BAD_COUNT 0`
     - nenhum `.1/.2`
     - nenhum `sn` ou `sn_1`
- Decisao de escopo:
  1. o helper compartilhado experimental `shared/semantic_duplicate_resolution.py` nao foi ligado ao runtime neste slice
  2. o caminho fechado foi o patch local de menor risco no robust
- Proximo foco recomendado:
  1. rerodar a comparacao direta padrao vs robust para medir o robust limpo contra o padrao atual
  2. ou voltar ao principal gargalo, que segue no merge/upsert

## CURRENT TRUTH 2026-03-06 22:02 - start from here

- Branch ativa: `codex/sprint-importacao-grave-fixes-20260305`.
- Baseline local de release: `4.30`.
- Slice entregue:
  1. logs de validacao agora usam mensagem amigavel tambem para regras sem label dedicado: `Violacao de validacao [...]`.
  2. `core.app_logic` agora resume validacao critica, sucesso de import e skip por extracao vazia com texto operacional claro e nome do arquivo.
  3. `extracao.extractor` agora inclui o nome do arquivo nos warnings de `sem numero de SSA`, `sem semana de cadastro` e no resumo final da extracao.
- Arquivos alterados:
  1. `core/app_logic.py`
  2. `extracao/extractor.py`
  3. `tests/test_extracao.py`
  4. `tests/test_import_single_error_classification.py`
- Snapshot de validacao:
  1. `uv run --python 3.13 python -m py_compile core/app_logic.py extracao/extractor.py tests/test_extracao.py tests/test_import_single_error_classification.py`: pass.
  2. `uv run --python 3.13 ruff check core/app_logic.py extracao/extractor.py tests/test_extracao.py tests/test_import_single_error_classification.py`: pass.
  3. `uv run --python 3.13 ty check core/app_logic.py extracao/extractor.py tests/test_extracao.py tests/test_import_single_error_classification.py`: pass.
  4. `timeout 180s uv run --python 3.13 pytest -q tests/test_extracao.py tests/test_import_single_error_classification.py`: `25 passed`.
- Significado operacional:
  1. o log de import fica mais legivel para operador sem precisar conhecer nome interno de regra.
  2. a proxima rodada ampla do kluster em importacao/DB ja parte de mensagens menos opacas.

## CURRENT TRUTH 2026-03-06 21:52 - start from here

- Branch ativa: `codex/sprint-importacao-grave-fixes-20260305`.
- Baseline local de release: `4.30`.
- Slice entregue:
  1. `core.app_logic` agora coleta tempos por arquivo em `extracao`, `validacao` e `insercao` sem alterar a semantica do import.
  2. `run_importer_logic` agora grava `file_reports` em `import_run_*.json`, com totais agregados de linhas extraidas, removidas por invalidos sem identidade, prontas para inserir e inseridas.
  3. `extracao.extractor` agora classifica invalidos sem identidade em `vazios` e `com payload`, incluindo linhas totalmente vazias removidas cedo.
  4. o classificador de payload agora ignora whitespace puro para nao inflar falsamente o grupo `com payload`.
- Arquivos alterados:
  1. `core/app_logic.py`
  2. `extracao/extractor.py`
  3. `tests/test_extracao.py`
  4. `tests/test_import_run_report.py`
- Snapshot de validacao:
  1. `uv run --python 3.13 python -m py_compile core/app_logic.py extracao/extractor.py tests/test_extracao.py tests/test_import_run_report.py tests/test_import_single_error_classification.py`: pass.
  2. `uv run --python 3.13 ruff check core/app_logic.py extracao/extractor.py tests/test_extracao.py tests/test_import_run_report.py tests/test_import_single_error_classification.py`: pass.
  3. `uv run --python 3.13 ty check core/app_logic.py extracao/extractor.py tests/test_extracao.py tests/test_import_run_report.py tests/test_import_single_error_classification.py`: pass.
  4. `timeout 180s uv run --python 3.13 pytest -q tests/test_extracao.py tests/test_import_run_report.py tests/test_import_single_error_classification.py`: `30 passed`.
- Significado operacional:
  1. o proximo full rescan vai sair com evidencia por arquivo/fase, em vez de log agregado opaco.
  2. a triagem dos invalidos agora distingue ruido vazio de payload real sem identidade, sem mudar a regra de descarte.

## CURRENT TRUTH 2026-03-06 21:10 - start from here

- Branch ativa: `codex/sprint-importacao-grave-fixes-20260305`.
- Baseline local de release: `4.30`.
- Slice entregue:
  1. `armazenamento.database_upsert_logic` agora usa fast path de append direto para chunks com `numero_ssa` unicos e ausentes no banco.
  2. o mesmo modulo agora converte `numpy scalar` para escalar Python antes do `to_sql` no fallback, evitando persistencia como `BLOB`.
  3. o fast path reabre transacao quando `to_sql` encerra o contexto, mantendo o loop multi-chunk estavel.
- Arquivos alterados:
  1. `armazenamento/database_upsert_logic.py`
  2. `tests/test_upsert_fast_path.py`
- Snapshot de validacao:
  1. `uv run --python 3.13 python -m py_compile armazenamento/database_upsert_logic.py tests/test_upsert_fast_path.py`: pass.
  2. `uv run --python 3.13 ruff check armazenamento/database_upsert_logic.py tests/test_upsert_fast_path.py`: pass.
  3. `uv run --python 3.13 ty check armazenamento/database_upsert_logic.py tests/test_upsert_fast_path.py`: pass.
  4. `timeout 180s uv run --python 3.13 pytest -q tests/test_upsert_fast_path.py`: `5 passed`.
- Prova pratica:
  1. lote real usado: `Todas as SSAs - 18-08-2022_1144AM.xlsx`
  2. `time_fast=1.476s`
  3. `time_legacy=3.902s`
  4. `speedup=2.644x`
  5. `rows_fast=18512`, `rows_legacy=18512`
  6. `blob_fast=0`, `blob_legacy=0`
- Significado operacional:
  1. ganho real agora esta no hot path do upsert, nao no extrator.
  2. o slice elimina a serializacao incorreta observada em `semana_programada` no caminho medido.

## CURRENT TRUTH 2026-03-06 21:03 - start from here

- Branch ativa: `codex/sprint-importacao-grave-fixes-20260305`.
- Baseline local de release: `4.30`.
- Slice entregue:
  1. `core.app_logic` agora traduz as duas novas categorias de duplicidade no log:
     - `Duplicidade exata no export`
     - `Duplicidade conflitante no export`
  2. regras sem mapeamento especifico continuam no formato generico.
  3. nao houve mudanca em import, schema ou resultado final do DB.
- Arquivos alterados:
  1. `core/app_logic.py`
  2. `tests/test_import_single_error_classification.py`
- Snapshot de validacao:
  1. `uv run --python 3.13 python -m py_compile core/app_logic.py tests/test_import_single_error_classification.py`: pass.
  2. `uv run --python 3.13 ruff check core/app_logic.py tests/test_import_single_error_classification.py`: pass.
  3. `uv run --python 3.13 ty check core/app_logic.py tests/test_import_single_error_classification.py`: pass.
  4. `timeout 180s uv run --python 3.13 pytest -q tests/test_import_single_error_classification.py`: `5 passed`.
- Significado operacional:
  1. o operador agora consegue diferenciar duplicidade exata de conflito real sem ler o nome interno da regra.
  2. proximo foco aprovado continua sendo a investigacao dos registros invalidos removidos no extrator.

## CURRENT TRUTH 2026-03-06 20:21 - start from here

- Branch ativa: `codex/sprint-importacao-grave-fixes-20260305`.
- Baseline local de release: `4.30`.
- Slice entregue:
  1. a validacao do dataframe agora distingue `duplicate_numero_ssa_exact` de `duplicate_numero_ssa_conflict`.
  2. a criacao inicial de DB ausente em `repair_database_if_needed()` nao loga mais `Problemas detectados no banco` no caminho esperado de create-from-zero.
  3. o comportamento de import e o resultado final do DB permaneceram iguais.
  4. licao de processo registrada:
     - nao assumir etapa como concluida sem confirmacao explicita
     - nao iniciar slice secundario sem aprovacao explicita
     - manter PT-BR ASCII nos blocos ativos
- Arquivos alterados:
  1. `armazenamento/database_validation.py`
  2. `armazenamento/database_integrity.py`
  3. `tests/test_database_verification.py`
- Snapshot de validacao:
  1. `uv run --python 3.13 python -m py_compile armazenamento/database_validation.py armazenamento/database_integrity.py tests/test_database_verification.py`: pass.
  2. `uv run --python 3.13 ruff check armazenamento/database_validation.py armazenamento/database_integrity.py tests/test_database_verification.py`: pass.
  3. `uv run --python 3.13 ty check armazenamento/database_validation.py armazenamento/database_integrity.py tests/test_database_verification.py`: pass.
  4. `timeout 180s uv run --python 3.13 pytest -q tests/test_database_verification.py`: `16 passed`.
- Significado operacional:
  1. export duplicado exato nao parece mais conflito de payload.
  2. bootstrap do DB candidato nao parece mais problema real de integridade no startup normal do full rescan.

## CURRENT TRUTH 2026-03-06 19:40 - start from here

- Active branch: `codex/sprint-importacao-grave-fixes-20260305`.
- Local release baseline: `4.30`.
- Slice delivered:
  1. extractor now exposes optional phase snapshots for tests only via `_debug_phases`.
  2. those snapshots cover the real pipeline transitions used in the historical malformed execution-tail cases:
     - `header_raw`
     - `after_empty_column_prune`
     - `after_rename`
     - `after_structural_repair`
     - `after_deduplicate`
  3. runtime behavior stays unchanged unless a test explicitly passes the debug dict.
- Files changed:
  1. `extracao/extractor.py`
  2. `tests/test_extracao.py`
- Regression evidence:
  1. `test_extract_data_from_excel_remaps_executadas_trailing_nan_columns_to_tempo_totals`
  2. `test_extract_data_from_excel_remaps_single_numeric_tex_column_after_anomalia`
  3. `test_extract_data_from_excel_does_not_remap_textual_unnamed_column_to_tex`
  4. `test_extract_data_from_excel_remaps_single_numeric_tex_column_when_anomalia_was_dropped`
- Validation snapshot:
  1. `uv run --python 3.13 python -m py_compile extracao/extractor.py tests/test_extracao.py`: pass.
  2. `uv run --python 3.13 ruff check extracao/extractor.py tests/test_extracao.py`: pass.
  3. `uv run --python 3.13 ty check extracao/extractor.py tests/test_extracao.py`: pass.
  4. `timeout 180s uv run --python 3.13 pytest -q tests/test_extracao.py`: `19 passed`.
- Key operational meaning:
  1. the tricky historical cases are now guarded against regressions at the phase level, not only by final extracted columns.
  2. this reduces the chance of reintroducing offset-based or order-of-operations bugs in the extractor.

## CURRENT TRUTH 2026-03-06 17:00 - start from here

- Active branch: `codex/sprint-importacao-grave-fixes-20260305`.
- Local release baseline: `4.30`.
- Slice delivered:
  1. extractor now remaps the second historical malformed execution-tail pattern:
     - after empty-column pruning, `1 trailing unnamed numeric column` in the execution block becomes `total_tempo_tex_executada`
  2. remap is guarded by structural checks and numeric payload validation.
  3. robust importer path was not changed.
- Files changed:
  1. `extracao/extractor.py`
  2. `tests/test_extracao.py`
- New regressions:
  1. `test_extract_data_from_excel_remaps_single_numeric_tex_column_after_anomalia`
  2. `test_extract_data_from_excel_does_not_remap_textual_unnamed_column_to_tex`
  3. `test_extract_data_from_excel_remaps_single_numeric_tex_column_when_anomalia_was_dropped`
- Validation snapshot:
  1. `uv run --python 3.13 python -m py_compile extracao/extractor.py tests/test_extracao.py`: pass.
  2. `uv run --python 3.13 ruff check extracao/extractor.py tests/test_extracao.py`: pass.
  3. `uv run --python 3.13 ty check extracao/extractor.py tests/test_extracao.py`: pass.
  4. `timeout 180s uv run --python 3.13 pytest -q tests/test_extracao.py`: `19 passed`.
  5. real-file repro for the 6 historical `SSAs Executadas_22-07-2025_*` warning sources:
     - all now return `nan_cols=[]`
     - all now expose `total_tempo_tex_executada`
  6. full rescan confirmation:
     - `logs/import_run_20260306_162834_535342.json`
     - `logs/full_rescan_runtime_20260306_162833.log`
     - placeholder warning count for `['nan']`: `0`
     - final DB columns: `82`
     - `nan_*` absent from schema
- Key operational meaning:
  1. the runtime is now clean for both historical execution-tail malformed patterns already diagnosed:
     - 3 trailing unnamed -> `TPE/TEX/TPO`
     - 1 surviving trailing unnamed numeric -> `TEX`
  2. schema drift from `nan_*` is closed in the promoted DB and the residual warning for raw `nan` also disappeared in the confirmation rescan.

## CURRENT TRUTH 2026-03-06 16:15 - start from here

- Active branch: `codex/sprint-importacao-grave-fixes-20260305`.
- Local release baseline: `4.30`.
- Runtime validation completed after the extractor remap hotfix:
  1. real full rescan finished successfully in `868.266s`.
  2. report file: `logs/import_run_20260306_160032_646798.json`.
  3. runtime log: `logs/full_rescan_runtime_20260306_160032.log`.
  4. `success_count=431`, `error_count=0`, `deterministic_failure_count=0`.
  5. ignored legacy `.xls` count remained `135`.
  6. promoted backup path: `data/ssas.db.full_rescan_backup_20260306_161500`.
- Final DB metrics after promotion:
  1. rows: `76426`
  2. distinct `numero_ssa`: `76426`
  3. columns: `82`
  4. null `data_cadastro`: `608`
  5. `nan_1` and `nan_2` are absent from the final schema
- Important interpretation:
  1. the concrete root cause for `nan_1`/`nan_2` is fixed in the promoted DB.
  2. runtime still logs raw placeholder discard `['nan']` for some historical `SSAs Executadas_22-07-2025_*` exports, so there may still be a separate semantic cleanup slice if those unlabeled single columns carry useful data.

## CURRENT TRUTH 2026-03-06 16:02 - start from here

- Active branch: `codex/sprint-importacao-grave-fixes-20260305`.
- Local release baseline: `4.30`.
- Slice delivered:
  1. the extractor now remaps the concrete malformed pattern `anomalia + 3 unnamed trailing columns` to:
     - `total_tempo_tpe_executada`
     - `total_tempo_tex_executada`
     - `total_tempo_tpo_executada`
  2. the rule is structural, not filename-based.
  3. robust importer path was not changed.
- Files changed:
  1. `extracao/extractor.py`
  2. `tests/test_extracao.py`
- New regression:
  1. `test_extract_data_from_excel_remaps_executadas_trailing_nan_columns_to_tempo_totals`
- Validation snapshot:
  1. `uv run --python 3.13 python -m py_compile extracao/extractor.py tests/test_extracao.py`: pass.
  2. `uv run --python 3.13 ruff check extracao/extractor.py tests/test_extracao.py`: pass.
  3. `uv run --python 3.13 ty check extracao/extractor.py tests/test_extracao.py`: pass.
  4. `timeout 180s uv run --python 3.13 pytest -q tests/test_extracao.py`: `16 passed`.
  5. real-file repro for `docs_entrada/SSAs Executadas_22-07-2025_0309PM.xlsx`:
     - `has_nan_cols=[]`
     - tail columns now end with `anomalia`, `total_tempo_tpe_executada`, `total_tempo_tex_executada`, `total_tempo_tpo_executada`, `status_execucao_prazo`
- Key operational meaning:
  1. the diagnosed source of `nan_1`/`nan_2` in malformed `SSAs Executadas` exports is now corrected at extraction time.
  2. the next verification step is a fresh full-corpus rescan to confirm whether any second source of `nan_*` still exists.

## CURRENT TRUTH 2026-03-06 15:46 - start from here

- Active branch: `codex/sprint-importacao-grave-fixes-20260305`.
- Local release baseline: `4.30`.
- Slice delivered:
  1. main runtime now records ignored legacy `.xls` files explicitly in the import JSON report.
  2. no `.xls` ingestion was enabled; the main pipeline still processes only `.xlsx`.
- Files changed:
  1. `utils/caching.py`
  2. `core/app_logic.py`
  3. `tests/test_caching.py`
  4. `tests/test_import_run_report.py`
- New regression:
  1. `test_get_ignored_legacy_excel_files_lists_only_xls`
- Validation snapshot:
  1. `uv run --python 3.13 python -m py_compile utils/caching.py core/app_logic.py tests/test_caching.py tests/test_import_run_report.py`: pass.
  2. `uv run --python 3.13 ruff check utils/caching.py core/app_logic.py tests/test_caching.py tests/test_import_run_report.py`: pass.
  3. `uv run --python 3.13 ty check utils/caching.py core/app_logic.py tests/test_caching.py tests/test_import_run_report.py`: pass.
  4. `timeout 180s uv run --python 3.13 pytest -q tests/test_caching.py tests/test_import_run_report.py`: `11 passed`.
- Key operational meaning:
  1. legacy `.xls` files are now visible in governance/reporting without contaminating the main DB path.
  2. next approved focus remains the root-cause cleanup for unlabeled numeric columns that become `nan_1` and `nan_2`.

## CURRENT TRUTH 2026-03-06 14:20 - start from here

- Active branch: `codex/sprint-importacao-grave-fixes-20260305`.
- Local release baseline: `4.30`.
- Slice delivered:
  1. reescaneamento dialog is now non-modal.
  2. main window stays usable while the worker runs.
  3. layout, button set, and user-visible texts were preserved.
  4. active dialog reference is retained on the window until the dialog finishes.
- Files changed:
  1. `gui/widgets/rescan_progress_dialog.py`
  2. `gui/ssa/gui_workers.py`
  3. `tests/test_rescan_progress_dialog.py`
  4. `tests/test_gui_workers_rescan_data.py`
- New regression:
  1. `test_rescan_progress_dialog_starts_non_modal`
  2. `test_rescan_data_shows_progress_dialog_without_blocking`
- Validation snapshot:
  1. `uv run --python 3.13 python -m py_compile gui/widgets/rescan_progress_dialog.py gui/ssa/gui_workers.py tests/test_rescan_progress_dialog.py tests/test_gui_workers_rescan_data.py`: pass.
  2. `uv run --python 3.13 ruff check gui/widgets/rescan_progress_dialog.py gui/ssa/gui_workers.py tests/test_rescan_progress_dialog.py tests/test_gui_workers_rescan_data.py`: pass.
  3. `uv run --python 3.13 ty check gui/widgets/rescan_progress_dialog.py gui/ssa/gui_workers.py tests/test_rescan_progress_dialog.py tests/test_gui_workers_rescan_data.py`: pass.
  4. `timeout 180s uv run --python 3.13 pytest -q tests/test_rescan_progress_dialog.py tests/test_gui_workers_rescan_data.py tests/test_rescan_worker_cleanup.py`: `13 passed`.
  5. offscreen GUI smoke reached timeout without traceback.
- Key operational meaning:
  1. full rescan no longer monopolizes the GUI event loop through `progress_dialog.exec()`.
  2. import/runtime logic was not changed in this slice.
- Remaining high-risk follow-up:
  1. import/schema drift from unlabeled numeric columns (`nan_1`, `nan_2`) still needs dedicated runtime cleanup.

## CURRENT TRUTH 2026-03-06 14:09 - start from here

- Active branch: `codex/sprint-importacao-grave-fixes-20260305`.
- Local release baseline: `4.30`.
- Runtime validation completed:
  1. real full staged rescan finished successfully in `918.206s`.
  2. report file: `logs/import_run_20260306_135404_209159.json`.
  3. runtime log: `logs/full_rescan_runtime_20260306_135403.log`.
  4. `success_count=431`, `error_count=0`, `deterministic_failure_count=0`.
  5. candidate DB was promoted and not preserved.
  6. promoted backup path: `data/ssas.db.full_rescan_backup_20260306_140922`.
- Final DB metrics after promotion:
  1. rows: `76426`
  2. distinct `numero_ssa`: `76426`
  3. columns: `84`
  4. null `data_cadastro`: `608`
  5. placeholder columns still present: `nan_1`, `nan_2`
- Important interpretation:
  1. the staged full-rescan flow is now runtime-validated on the full corpus.
  2. extractor blocker from duplicate/`NaN` headers is fixed.
  3. remaining open runtime risk is schema drift from unlabeled numeric columns, not the candidate promotion flow.
- Next approved focus:
  1. remove GUI modal blocking during rescan without changing layout.

## CURRENT TRUTH 2026-03-06 13:51 - start from here

- Active branch: `codex/sprint-importacao-grave-fixes-20260305`.
- Local release baseline: `4.30`.
- Slice delivered:
  1. the traditional extractor now handles duplicate header labels and `NaN` header labels safely during the empty-column preservation pass.
  2. preservation of mandatory empty aliases remains intact.
  3. robust importer path was not changed.
- Files changed:
  1. `extracao/extractor.py`
  2. `tests/test_extracao.py`
- New regression:
  1. `test_extract_data_from_excel_handles_duplicate_header_labels_without_ambiguity`
  2. `test_extract_data_from_excel_drops_nan_header_columns_safely`
- Validation snapshot:
  1. `uv run --python 3.13 python -m py_compile extracao/extractor.py tests/test_extracao.py`: pass.
  2. `uv run --python 3.13 ruff check extracao/extractor.py tests/test_extracao.py`: pass.
  3. `uv run --python 3.13 ty check extracao/extractor.py tests/test_extracao.py`: pass.
  4. `timeout 180s uv run --python 3.13 pytest -q tests/test_extracao.py`: `15 passed`.
  5. real-file repro now passes for:
     - `SSAs Pendentes de Aprovação na Emissão_02-02-2026_1141AM.xlsx`
     - `SSAs Executadas_22-07-2025_0303PM (2).xlsx`
     - `Pendentes de Planejamento_02-02-2026_1142AM.xlsx`
- Key operational meaning:
  1. the real staged rescan blocker found at `logs/full_rescan_runtime_20260306_121612.log` was in the new extractor preservation block, not in robust.
  2. duplicate labels such as `Desde` and raw `NaN` headers no longer abort extraction before normalization.
- Next required step:
  1. rerun the full real-corpus staged rescan and validate its JSON/log outputs before moving on to GUI non-modal hardening.

## CURRENT TRUTH 2026-03-06 10:28 - start from here

- Active branch: `codex/sprint-importacao-grave-fixes-20260305`.
- Local release baseline: `4.30`.
- Slice delivered:
  1. full rescan now builds and validates a candidate DB first.
  2. the primary DB is rotated/promoted only at the end of a successful run.
  3. on failure or mid-run cancellation, the primary DB stays untouched and the candidate DB is preserved.
  4. robust importer path was not changed.
- Files changed:
  1. `core/app_logic.py`
  2. `tests/test_import_run_report.py`
- New regression:
  1. `test_run_importer_logic_full_rescan_failure_preserves_primary_db`
  2. `test_run_importer_logic_full_rescan_success_promotes_candidate_at_end`
- Validation snapshot:
  1. `uv run --python 3.13 python -m py_compile core/app_logic.py tests/test_app_logic_full_rescan_lock.py tests/test_import_run_report.py`: pass.
  2. `uv run --python 3.13 ruff check core/app_logic.py tests/test_app_logic_full_rescan_lock.py tests/test_import_run_report.py`: pass.
  3. `uv run --python 3.13 ty check core/app_logic.py tests/test_app_logic_full_rescan_lock.py tests/test_import_run_report.py`: pass.
  4. `timeout 240s uv run --python 3.13 pytest -q tests/test_app_logic_full_rescan_lock.py tests/test_import_run_report.py`: `6 passed`.
- Operational meaning:
  1. full rescan no longer destroys the active DB up front.
  2. import JSON report now distinguishes `primary_db_path` from `working_db_path` and records candidate promotion details.
- Still deferred:
  1. GUI remains modal during rescan.
  2. optional user confirmation before loading/promoting a new DB is not implemented yet.

## CURRENT TRUTH 2026-03-06 10:09 - start from here

- Active branch: `codex/sprint-importacao-grave-fixes-20260305`.
- Local release baseline: `4.30`.
- Slice delivered:
  1. runtime now has shared constants for canonical SSA table naming.
  2. primary entry points use `ssa_table` explicitly while still accepting `ssas` and `ssa_chamados` as compatibility aliases.
  3. `DataLoaderWorker` now falls back safely to the canonical table when an invalid identifier is requested.
  4. robust importer path was not changed.
- Files changed:
  1. `shared/db_names.py`
  2. `interface/cli.py`
  3. `gui/workers/data_loader_worker.py`
  4. `gui/gui_ssa.py`
  5. `armazenamento/database_validation.py`
  6. `armazenamento/database_integrity.py`
  7. `armazenamento/database.py`
  8. `tests/test_cli_get_ssa_query_identifier_guard.py`
  9. `tests/test_data_loader_worker.py`
  10. `tests/test_database_verification.py`
- New regression:
  1. `test_get_ssa_query_accepts_second_legacy_alias`
  2. `test_resolve_target_table_accepts_second_legacy_alias`
  3. `test_resolve_target_table_invalid_identifier_falls_back_to_canonical`
- Validation snapshot:
  1. `uv run --python 3.13 python -m py_compile shared/db_names.py interface/cli.py gui/workers/data_loader_worker.py gui/gui_ssa.py armazenamento/database_validation.py armazenamento/database_integrity.py armazenamento/database.py tests/test_cli_get_ssa_query_identifier_guard.py tests/test_data_loader_worker.py tests/test_database_verification.py`: pass.
  2. `uv run --python 3.13 ruff check shared/db_names.py interface/cli.py gui/workers/data_loader_worker.py gui/gui_ssa.py armazenamento/database_validation.py armazenamento/database_integrity.py armazenamento/database.py tests/test_cli_get_ssa_query_identifier_guard.py tests/test_data_loader_worker.py tests/test_database_verification.py`: pass.
  3. `uv run --python 3.13 ty check shared/db_names.py interface/cli.py gui/workers/data_loader_worker.py gui/gui_ssa.py armazenamento/database_validation.py armazenamento/database_integrity.py armazenamento/database.py tests/test_cli_get_ssa_query_identifier_guard.py tests/test_data_loader_worker.py tests/test_database_verification.py`: pass.
  4. `timeout 180s uv run --python 3.13 pytest -q tests/test_cli_get_ssa_query_identifier_guard.py tests/test_data_loader_worker.py tests/test_database_verification.py`: `28 passed`.
- Deferred by user-approved scope control:
  1. out-of-scope Kluster findings in CLI/GUI architecture and performance were intentionally not implemented in this slice.
  2. deeper alias cleanup across the remaining runtime/test corpus is still pending and should stay incremental.

## CURRENT TRUTH 2026-03-06 09:41 - start from here

- Active branch: `codex/sprint-importacao-grave-fixes-20260305`.
- Local release baseline: `4.30`.
- Slice delivered:
  1. traditional extractor no longer drops fully empty columns when they canonically map to mandatory schema fields.
  2. minimal shared contract added for extraction/validation policy:
     - `MANDATORY_SCHEMA_COLUMNS`
     - `VALIDATION_REQUIRED_COLUMNS`
     - `ALLOWED_MISSING_DATA_CADASTRO_STATUSES`
  3. robust importer path was intentionally not changed in this slice.
- Files changed:
  1. `extracao/extractor.py`
  2. `armazenamento/database_validation.py`
  3. `shared/import_contract.py`
  4. `tests/test_extracao.py`
- New regression:
  1. `test_extract_data_from_excel_preserves_empty_required_alias_until_normalization`
- Validation snapshot:
  1. `uv run --python 3.13 python -m py_compile extracao/extractor.py armazenamento/database_validation.py shared/import_contract.py tests/test_extracao.py tests/test_database_verification.py`: pass.
  2. `uv run --python 3.13 ruff check extracao/extractor.py armazenamento/database_validation.py shared/import_contract.py tests/test_extracao.py tests/test_database_verification.py`: pass.
  3. `uv run --python 3.13 ty check extracao/extractor.py armazenamento/database_validation.py shared/import_contract.py tests/test_extracao.py tests/test_database_verification.py`: pass.
  4. `timeout 180s uv run --python 3.13 pytest -q tests/test_extracao.py tests/test_database_verification.py`: `26 passed`.
- Key operational meaning:
  1. files with `Emitida Em` in the header but empty values should now survive extraction and reach validation instead of failing as missing required column.
  2. runtime still uses the traditional extractor path; robust remains diagnostic/isolation only.
- Remaining high-risk follow-up:
  1. unify canonical table name usage across runtime/tests and remove legacy aliases where safe.
  2. move full-rescan to staged DB creation + final swap after validation/import completes.

## CURRENT TRUTH 2026-03-05 21:31 - start from here

- Active branch: `codex/sprint-importacao-grave-fixes-20260305`.
- Local release baseline: `4.30`.
- Slice delivered:
  1. automatic JSON report generation for every `run_importer_logic` execution.
  2. helper extraction applied to keep function complexity controlled (`_build_import_run_payload`).
  3. no runtime business-rule changes in import validation.
- Files changed:
  1. `core/app_logic.py`
  2. `tests/test_import_run_report.py`
- Report output:
  1. format: `logs/import_run_<timestamp>.json`
  2. runtime smoke evidence: `logs/import_run_20260305_213050_586834.json` (`status=no_changes`).
- Validation snapshot:
  1. `uv run --python 3.13 python -m py_compile core/app_logic.py tests/test_import_run_report.py`: pass.
  2. `uv run --python 3.13 ruff check core/app_logic.py tests/test_import_run_report.py`: pass.
  3. `uv run --python 3.13 ty check core/app_logic.py tests/test_import_run_report.py`: pass.
  4. `uv run --python 3.13 pytest -q tests/test_import_run_report.py tests/test_import_cache_integrity.py`: `3 passed`.
- Deferred by user:
  1. `1778` continuation rows in `SSAscomReprogramacoes_*` remain out of this slice and must be handled in a dedicated next group.

## CURRENT TRUTH 2026-03-05 20:27 - start from here

- Active branch: `codex/sprint-importacao-grave-fixes-20260305`.
- Local release baseline: `4.30`.
- Bootstrap hardening delivered:
  1. `ensure_column_exists` no longer attempts `ALTER TABLE` when target table does not exist yet.
  2. expected result: no false `no such table: ssa_table` error during startup/bootstrap window.
- Files changed:
  1. `armazenamento/database.py`
  2. `tests/test_database_verification.py`
- New regression:
  1. `test_ensure_column_exists_no_error_when_table_absent`
- Validation snapshot:
  1. `uv run --python 3.13 python -m py_compile armazenamento/database.py tests/test_database_verification.py`: pass.
  2. `uv run --python 3.13 ruff check armazenamento/database.py tests/test_database_verification.py`: pass.
  3. `uv run --python 3.13 ty check armazenamento/database.py tests/test_database_verification.py`: pass.
  4. `uv run --python 3.13 pytest -q tests/test_database_verification.py -k "ensure_column_exists_no_error_when_table_absent or validate_missing_data_cadastro_status_exceptions_are_allowed or verify_valid_database"`: `3 passed, 10 deselected`.

## CURRENT TRUTH 2026-03-05 20:09 - start from here

- Active branch: `codex/sprint-importacao-grave-fixes-20260305`.
- Local release baseline: `4.30`.
- New runtime decision applied:
  1. validation now accepts missing `data_cadastro` for statuses `SCC`, `ADI`, and `ASE`.
  2. no deferred queue/reconciliation list was introduced (minimal path preserved).
- Files changed:
  1. `armazenamento/database_validation.py`
  2. `tests/test_database_verification.py`
- Focused regression updated:
  1. `test_validate_missing_data_cadastro_status_exceptions_are_allowed`
- Validation snapshot:
  1. `uv run --python 3.13 python -m py_compile armazenamento/database_validation.py tests/test_database_verification.py`: pass.
  2. `uv run --python 3.13 ruff check armazenamento/database_validation.py tests/test_database_verification.py`: pass.
  3. `uv run --python 3.13 ty check armazenamento/database_validation.py tests/test_database_verification.py`: pass.
  4. `uv run --python 3.13 pytest -q tests/test_database_verification.py -k "validate_missing_data_cadastro_status_exceptions_are_allowed or validate_missing_data_cadastro_scc_is_allowed or validate_valid_dataframe or validate_invalid_dates"`: `3 passed, 9 deselected`.
- Expected lane impact:
  1. `missing_data_cadastro` residual after SCC patch (`221`) becomes `0` with ADI/ASE exception in current observed corpus.

## CURRENT TRUTH 2026-03-05 19:42 - start from here

- Active branch: `codex/sprint-importacao-grave-fixes-20260305`.
- Local release baseline: `4.30`.
- Cross-file diagnostic completed for ADI/ASE missing `data_cadastro`.
- Scope:
  1. files scanned: `431` (excluding lock files), `406` parsed, `25` extraction errors.
  2. target rows: `situacao in {ADI, ASE}` and missing `data_cadastro`.
- Result set:
  1. unique SSAs: `213`
  2. rows: `279`
- Cross-file behavior:
  1. same SSA with data in other occurrence: `158/213` (`74.18%`)
  2. same SSA with no data in any occurrence: `55/213` (`25.82%`)
  3. same SSA with status transitions outside ADI/ASE: `164/213` (`76.99%`)
  4. same SSA only ADI/ASE statuses: `49/213` (`23.00%`)
  5. ADI/ASE with data present somewhere: `7/213` (`3.29%`)
- Data-presence states (same SSA family):
  1. top with-data statuses: `STE`, `SPG`, `AAT`, `SEE`, `APG`.
  2. ADI/ASE with data exist but low (`ADI=8`, `ASE=6` occurrences).
- Date clues:
  1. for all `279` target rows, `file_year - ssa_year = 0`.
  2. week approximation (`semana_cadastro` monday) vs file date:
     - p50 `3` days, p75 `8` days
     - within 14 days: `254/279`
     - within 30 days: `276/279`
- Interpretation:
  1. no strict deterministic relation between ADI/ASE and missing `data_cadastro`.
  2. pattern behaves like temporal snapshot progression in the same yearly batch.

## CURRENT TRUTH 2026-03-05 19:26 - start from here

- Active branch: `codex/sprint-importacao-grave-fixes-20260305`.
- Local release baseline: `4.30`.
- New diagnostics delivered after SCC patch:
  1. full status scan executed on `431` xlsx files (excluding `~$` lock files).
  2. ADI/ASE are NOT universally missing `data_cadastro`.
  3. mini importacao test confirmed SCC exception works in runtime path.
- Status vs missing `data_cadastro` (extractor-level global view):
  1. `ADI`: total `208`, missing `155`, non-missing `53` (`74.519%` missing).
  2. `ASE`: total `179`, missing `124`, non-missing `55` (`69.274%` missing).
  3. `SCC`: total `3044`, missing `2409`, non-missing `635` (`79.139%` missing).
- Full-run baseline consistency (same lane used in prior impact estimate):
  1. `missing_data_cadastro` lane remains `2171`.
  2. split confirmed: `1950` SCC + `221` non-SCC (`ADI/ASE`).
- File note requested by user:
  1. `SSAs Pendentes Geral - 02-02-2026_1142AM.xlsx`: `ADI=16` and `ASE=22`, both 100% missing in this file.
- Meaning gap:
  1. repository search found no canonical textual definition for `ADI` or `ASE`; classify as domain-definition pending.
- Low-risk hardening candidates queued:
  1. avoid false startup warning by skipping `ALTER TABLE` when `ssa_table` does not exist yet.
  2. add source file context to `Removidos X registros invalidos` log line in extractor.

## CURRENT TRUTH 2026-03-05 16:43 - start from here

- Active branch: `codex/sprint-importacao-grave-fixes-20260305`.
- Local release baseline: `4.30`.
- New delivered validation rule (minimal slice):
  1. `situacao=SCC` with missing `data_cadastro` is accepted as valid (no critical issue/drop for this condition).
  2. non-SCC missing `data_cadastro` keeps current strict behavior.
- Files changed:
  1. `armazenamento/database_validation.py`
  2. `tests/test_database_verification.py`
- Focused test added:
  1. `test_validate_missing_data_cadastro_scc_is_allowed`
- Validation snapshot:
  1. `uv run --python 3.13 python -m py_compile armazenamento/database_validation.py tests/test_database_verification.py`: pass.
  2. `uv run --python 3.13 ruff check armazenamento/database_validation.py tests/test_database_verification.py`: pass.
  3. `uv run --python 3.13 ty check armazenamento/database_validation.py tests/test_database_verification.py`: pass.
  4. `uv run --python 3.13 pytest -q tests/test_database_verification.py -k "validate_missing_data_cadastro_scc_is_allowed or validate_valid_dataframe or validate_invalid_dates"`: `3 passed`.
- Impact evidence (from previous full-run diagnostics):
  1. baseline missing-data drop: `2171`.
  2. SCC share in that set: `1950`.
  3. estimated reduction with rule: `2171 -> 221` (`-89.820%` in missing-data drop lane).

## CURRENT TRUTH 2026-03-05 14:12 - start from here

- Active branch: `codex/sprint-importacao-grave-fixes-20260305`.
- Local release baseline: `4.30`.
- Diagnostic status:
  1. full rescan zero-db foi executado com backup manual previo.
  2. execucao forcada ficou ativa por ~35m e terminou sem status final confiavel no shell.
  3. DB final ficou com `integrity_check=ok`, mas com drift de schema (colunas canonicas perdidas).
- Critical findings:
  1. schema drift: `id` ausente e perda de 12 colunas canonicas no `ssa_table`.
  2. colunas espurias `nan`, `nan_1`, `nan_2` no schema atual.
  3. regra `missing_data_cadastro` removeu 2171 linhas em 138 arquivos nesta rodada.
  4. dois arquivos `SSAs Pendentes de Aprovacao na Emissao_*` foram pulados por missing `data_cadastro` apos normalizacao.
- Root-cause evidence:
  1. caminho de upsert ainda permite `to_sql(... if_exists='replace')` quando tabela nao existe, criando schema pelo DataFrame.
  2. extrator remove colunas totalmente vazias antes da normalizacao (`dropna(axis=1, how='all')`), impedindo fallback de `data_cadastro` para alguns lotes.
- Evidence files:
  1. `docs/indicios_importacao.md`
  2. `logs/full_rescan_20260305_132813.log`
  3. `logs/rescan_resume_20260305_140405.log`
  4. `logs/gui_smoke_20260305_140702.log`
- Validation snapshot:
  1. `uv run --python 3.13 python -m py_compile extracao/extractor.py core/app_logic.py armazenamento/database_upsert_logic.py armazenamento/database_integrity.py`: pass.
  2. `uv run --python 3.13 ruff check extracao/extractor.py core/app_logic.py armazenamento/database_upsert_logic.py armazenamento/database_integrity.py`: pass.
  3. `uv run --python 3.13 ty check extracao/extractor.py core/app_logic.py armazenamento/database_upsert_logic.py armazenamento/database_integrity.py`: pass.
  4. `uv run --python 3.13 pytest -q tests/test_extracao.py tests/test_database_verification.py tests/test_app_logic_full_rescan_lock.py tests/test_cli_clearall_uses_table_name.py tests/test_database.py`: `34 passed`.
  5. GUI smoke: `GUI_SMOKE_EXIT=0`.
- Next slices (approved plan candidate):
  1. `HOTFIX_BLOCKER`: forcar schema canonico antes da primeira escrita no full rescan (eliminar criacao por `replace`).
  2. `STABILITY_PATCH`: preservar coluna critica vazia para permitir fallback de data (evitar skip total de arquivo).
  3. `STABILITY_PATCH`: adicionar progresso/fechamento deterministico no full rescan para observabilidade operacional.

## CURRENT TRUTH 2026-03-05 13:15 - start from here

- Active branch: `codex/sprint-importacao-grave-fixes-20260305`.
- Local release baseline: `4.30`.
- Slice status:
  1. importacao hotfix applied for strict numeric handling in `num_reprogramacoes`.
  2. legacy textual values in `num_reprogramacoes` are now coerced to null.
  3. controlled backfill: `total_de_reprogramacoes` now fills `num_reprogramacoes` only when `num_reprogramacoes` is null after coercion.
- Files changed in this slice:
  1. `extracao/extractor.py`
  2. `tests/test_extracao.py`
  3. `docs/RECOVERY_BACKLOG.md`
  4. `docs/NEXT_CHAT_MIGRATION.md`
  5. `docs/AGENTS_HANDOFF_NEXT_CYCLE.md`
- Validation snapshot:
  1. `uv run --python 3.13 python -m py_compile extracao/extractor.py tests/test_extracao.py`: pass.
  2. `uv run --python 3.13 ruff check extracao/extractor.py tests/test_extracao.py`: pass.
  3. `uv run --python 3.13 ty check extracao/extractor.py tests/test_extracao.py`: pass.
  4. `uv run --python 3.13 pytest -q tests/test_extracao.py -k "normalize_datatypes_num_reprogramacoes or read_report or extract_data_from_excel"`: `9 passed, 3 deselected`.
  5. kluster auto in this slice: clean -> clean.
- Scope guard:
  1. no GUI/layout changes.
  2. no schema migration.
  3. no broad refactor.

## CURRENT TRUTH 2026-03-05 09:41 - start from here

- Active branch: `codex/reapply-good-commits-20260305`.
- Local release baseline: `4.30`.
- PR #44 triage status:
  1. critical-only fixes applied in `a07afd7a`.
  2. fixed now: date-filter negation bug, hash width clamp regression, and silent width-manager exception suppression.
  3. non-blocking/broad comments deferred to backlog for separate slices.
- Validation snapshot:
  1. `uv run --python 3.13 python -m py_compile gui/mixins/filter_gui_ssa_mixin.py gui/simple_width_manager.py gui/ssa/gui_table.py tests/test_gui_filter_logic.py`: pass.
  2. `uv run --python 3.13 ruff check gui/mixins/filter_gui_ssa_mixin.py gui/simple_width_manager.py gui/ssa/gui_table.py tests/test_gui_filter_logic.py`: pass.
  3. `uv run --python 3.13 ty check gui/mixins/filter_gui_ssa_mixin.py gui/simple_width_manager.py gui/ssa/gui_table.py tests/test_gui_filter_logic.py`: pass.
  4. `uv run --python 3.13 pytest -q tests/test_gui_filter_logic.py -k "data_cadastro_column_filter_accepts_display_date_on_first_apply or data_cadastro_column_filter_negation_matches_display_date or best_fit_width_respects_predefined_max_for_long_columns or compute_optimal_widths_keeps_hash_column_minimum_24 or on_header_clicked_preserves_column_widths_after_sort or header_context_menu_exposes_best_fit_visible_action"`: `6 passed`.
  5. kluster auto in this slice: clean -> clean -> clean -> clean -> clean.
- Evidence commit:
  1. `a07afd7a`.
- Next cycle:
  1. complete PR comment status replies (fixed/deferred/falso-positivo) with links to evidence.
  2. keep deferred architectural suggestions outside this PR.

## HISTORICAL SNAPSHOT 2026-03-05 08:40 - start from here

- Active branch: `codex/reapply-good-commits-20260305`.
- Local release baseline: `4.30`.
- Replay status:
  1. clean replay branch created from `bf78666e`.
  2. replayed: `9601ffb8`, `a87c72d7`, `88de4155`, `8400fe42`, `df65682c`, `6899894b`, `956c0f4a`.
  3. excluded by decision: `d4c2c5ca` (kept as short-term deferred reimplementation item).
- Validation snapshot:
  1. `uv run --python 3.13 python -m py_compile core/config_manager.py gui/simple_width_manager.py gui/gui_ssa.py gui/ssa/gui_table.py gui/mixins/filter_gui_ssa_mixin.py tests/test_gui_filter_logic.py`: pass.
  2. `uv run --python 3.13 ruff check core/config_manager.py gui/simple_width_manager.py gui/gui_ssa.py gui/ssa/gui_table.py gui/mixins/filter_gui_ssa_mixin.py tests/test_gui_filter_logic.py`: pass.
  3. `uv run --python 3.13 ty check core/config_manager.py gui/simple_width_manager.py gui/gui_ssa.py gui/ssa/gui_table.py gui/mixins/filter_gui_ssa_mixin.py tests/test_gui_filter_logic.py`: pass.
  4. `uv run --python 3.13 pytest -q tests/test_gui_filter_logic.py -k "num_reprogramacoes or best_fit or show_all_columns_by_affinity or data_cadastro_column_filter_accepts_display_date_on_first_apply"`: `7 passed`.
  5. kluster auto in replay cycle: clean -> clean -> clean.
- Evidence commit:
  1. HEAD replay branch: `5b145b78`.
- Next cycle:
  1. evaluate requirements-only reimplementation for `d4c2c5ca` in a new controlled slice.
  2. keep extraction path exactly as replayed baseline until this decision is approved.

## HISTORICAL SNAPSHOT 2026-03-04 10:29 - start from here

- Active branch: `codex/sprint-colunas-exibicao-db-saneamento`.
- Local release baseline: `4.30`.
- Slice status:
  1. sprint7 delivered guardrails for ultra-long columns and sort width stability.
  2. header context menu now includes `Exibir todas colunas (afinidade)`.
- Runtime change summary:
  1. `core/config_manager.py`: added `COLUMN_AFFINITY_SCORES` (desc ranking map for reusable column affinity order).
  2. `gui/simple_width_manager.py`: introduced `max_pixel_widths` and hard clamp in width computation.
  3. `gui/ssa/gui_table.py`: width apply now respects per-column max map and can skip one recompute cycle (`_skip_width_recompute_once`).
  4. `gui/gui_ssa.py`: sort now captures/restores widths to avoid lateral width drift after asc/desc click.
  5. `gui/gui_ssa.py`: new menu action `Exibir todas colunas (afinidade)` uses same source set as selector `Selecionar tudo`, then applies affinity order.
  6. `tests/test_gui_filter_logic.py`: added focused regressions for:
     - new context action exposure;
     - show-all affinity ordering with same source set;
     - width preservation after sort;
     - max-width clamp for long columns.
- Validation snapshot:
  1. `uv run --python 3.13 python -m py_compile core/config_manager.py gui/simple_width_manager.py gui/gui_ssa.py gui/ssa/gui_table.py tests/test_gui_filter_logic.py`: pass.
  2. `uv run --python 3.13 ruff check core/config_manager.py gui/simple_width_manager.py gui/gui_ssa.py gui/ssa/gui_table.py tests/test_gui_filter_logic.py`: pass.
  3. `uv run --python 3.13 ty check core/config_manager.py gui/simple_width_manager.py gui/gui_ssa.py gui/ssa/gui_table.py tests/test_gui_filter_logic.py`: pass.
  4. `uv run --python 3.13 pytest -q tests/test_gui_filter_logic.py -k "header_context_menu_exposes_best_fit_visible_action or header_context_menu_exposes_show_all_columns_by_affinity_action or show_all_columns_by_affinity_reorders_same_select_all_set or on_header_clicked_preserves_column_widths_after_sort or best_fit_width_respects_predefined_max_for_long_columns or best_fit_width_guard_ignores_single_extreme_outlier or on_header_clicked_sorts_num_reprogramacoes_mixed_types"`: `7 passed`.
  5. kluster auto in this slice: clean across all touched files.
- Evidence commit:
  1. `6899894b` (`HOTFIX_BLOCKER`: align date column filters with displayed format).
  2. pending commit in current sprint7 slice.
- Next cycle:
  1. user validation focused on sort behavior under repeated toggles in full-column mode.
  2. optional extension: expose affinity order as explicit preset in column selector dialog.

## HISTORICAL SNAPSHOT 2026-03-04 10:01 - start from here

- Active branch: `codex/sprint-colunas-exibicao-db-saneamento`.
- Local release baseline: `4.30`.
- Slice status:
  1. sprint6 delivered: `data_cadastro` column filter now applies consistently with displayed date format.
  2. user report ("cadastro not immediate / needs extra operation") traced to raw-vs-display date mismatch in filter path.
- Runtime change summary:
  1. `gui/mixins/filter_gui_ssa_mixin.py`: `_apply_column_filters` now OR-combines raw date matching with display-date matching (`DD/MM/YYYY`) for slash-based filters.
  2. `gui/mixins/filter_gui_ssa_mixin.py`: added `_should_match_date_display_filter(...)`.
  3. `gui/mixins/filter_gui_ssa_mixin.py`: added `_get_column_filter_date_display_series(...)` with per-DataFrame cache to avoid repeated parse/format work.
  4. `tests/test_gui_filter_logic.py`: added `test_data_cadastro_column_filter_accepts_display_date_on_first_apply`.
- Data evidence snapshot:
  1. `data/ssas.db`: `data_cadastro` persisted as ISO datetime (`YYYY-MM-DD HH:MM:SS`) across `70954` non-null rows.
  2. GUI renders `data_*` columns as `DD/MM/YYYY`, so prior behavior could fail on first apply when user typed displayed date text.
- Validation snapshot:
  1. `uv run --python 3.13 python -m py_compile gui/mixins/filter_gui_ssa_mixin.py tests/test_gui_filter_logic.py`: pass.
  2. `uv run --python 3.13 ruff check gui/mixins/filter_gui_ssa_mixin.py tests/test_gui_filter_logic.py`: pass.
  3. `uv run --python 3.13 ty check gui/mixins/filter_gui_ssa_mixin.py tests/test_gui_filter_logic.py`: pass.
  4. `uv run --python 3.13 pytest -q tests/test_gui_filter_logic.py -k "data_cadastro_column_filter_accepts_display_date_on_first_apply or column_filter_buttons_flow or column_filter_row_clear_button_clears_value_without_hiding_row or clear_filter_button_state_syncs_across_tabs_without_switch"`: `4 passed`.
  5. kluster auto in this slice: issue(P4,P4) -> clean -> clean -> clean.
- Evidence commit:
  1. `05c443cf` (`STABILITY_PATCH`: canonical reprogramacoes numeric flow).
  2. pending commit in current sprint6 slice.
- Next cycle:
  1. run user validation on affected columns (`data_cadastro`, `data_programada`, other `data_*`) in both tabs.
  2. if approved, continue display-label cleanup sprint without DB mutation.

## HISTORICAL SNAPSHOT 2026-03-04 09:46 - start from here

- Active branch: `codex/sprint-colunas-exibicao-db-saneamento`.
- Local release baseline: `4.30`.
- Slice status:
  1. sprint4 is closed and committed (`df65682c`) with best-fit calibration aligned to Qt baseline.
  2. sprint5 delivered canonical numeric handling for reprogramacoes across sort/filter/menu cache, without DB schema mutation.
- Runtime change summary:
  1. `gui/ssa/reprogramacoes_numeric.py`: new canonical helper `get_num_reprogramacoes_numeric_series(...)` with priority `total_de_reprogramacoes` -> numeric `num_reprogramacoes` -> digit extraction fallback.
  2. `gui/gui_ssa.py`: robust sort path now reuses shared helper; best-fit baseline probe guarded (`sizeHintForColumn` only when `rowCount <= 500`).
  3. `gui/ssa/gui_filters_advanced_logic.py`: advanced `num_reprogramacoes` filter now uses shared numeric helper.
  4. `gui/ssa/gui_filters_advanced_ui.py`: advanced options cache for reprogramacoes now uses shared numeric helper.
  5. `tests/test_gui_filters_advanced_logic.py` + `tests/test_gui_filter_logic.py`: new regressions for legacy-text rows preferring `total_de_reprogramacoes`.
- Data evidence snapshot:
  1. mixed-source dataset confirmed: `num_reprogramacoes` has `5589` numeric-like rows and `1099` legacy text rows (`Reprogramacao #1`).
  2. all `1099` legacy-text rows overlap with non-null `total_de_reprogramacoes` and `situacao_reprogramacao='(SPG)'`.
  3. active runtime usage now normalized through one helper to avoid sort/filter drift.
- Validation snapshot:
  1. `uv run --python 3.13 python -m py_compile gui/ssa/reprogramacoes_numeric.py gui/gui_ssa.py gui/ssa/gui_filters_advanced_logic.py gui/ssa/gui_filters_advanced_ui.py tests/test_gui_filters_advanced_logic.py tests/test_gui_filter_logic.py`: pass.
  2. `uv run --python 3.13 ruff check gui/ssa/reprogramacoes_numeric.py gui/gui_ssa.py gui/ssa/gui_filters_advanced_logic.py gui/ssa/gui_filters_advanced_ui.py tests/test_gui_filters_advanced_logic.py tests/test_gui_filter_logic.py`: pass.
  3. `uv run --python 3.13 ty check gui/ssa/reprogramacoes_numeric.py gui/gui_ssa.py gui/ssa/gui_filters_advanced_logic.py gui/ssa/gui_filters_advanced_ui.py tests/test_gui_filters_advanced_logic.py tests/test_gui_filter_logic.py`: pass.
  4. `uv run --python 3.13 pytest -q tests/test_gui_filters_advanced_logic.py tests/test_gui_filter_logic.py -k "reprogramacoes or on_header_clicked_sorts_num_reprogramacoes_mixed_types or best_fit_width_guard_ignores_single_extreme_outlier or header_context_menu_exposes_best_fit_visible_action"`: `8 passed`.
  5. kluster auto in this slice: clean.
- Evidence commit:
  1. `df65682c` (`STABILITY_PATCH`: sprint4 best-fit calibration).
  2. pending commit in current sprint5 slice.
- Next cycle:
  1. sprint de exibicao: continuar ajuste de labels amigaveis em tabela e adicionar-colunas (sem alterar runtime de dados).
  2. sprint de DB (se aprovado): auditoria controlada de campos legados/redundantes antes de qualquer saneamento.

## HISTORICAL SNAPSHOT 2026-03-04 09:27 - start from here

- Active branch: `codex/sprint-colunas-exibicao-db-saneamento`.
- Local release baseline: `4.30`.
- Slice status:
  1. sprint4 delivered: best-fit width behavior recalibrated to align with real Qt auto-fit baseline.
  2. performance hardening added to best-fit text measurement path.
- Runtime change summary:
  1. `gui/simple_width_manager.py`: best-fit now uses sampled real text pixel widths (not synthetic `"W"*N` sizing).
  2. `gui/simple_width_manager.py`: baseline clamp uses Qt auto-fit reference plus anti-outlier limits.
  3. `gui/simple_width_manager.py`: added measurement cache and reduced default sample size (`800`).
- Validation snapshot:
  1. `uv run --python 3.13 python -m py_compile gui/simple_width_manager.py gui/gui_ssa.py tests/test_gui_filter_logic.py`: pass.
  2. `uv run --python 3.13 ruff check gui/simple_width_manager.py gui/gui_ssa.py tests/test_gui_filter_logic.py`: pass.
  3. `uv run --python 3.13 ty check gui/simple_width_manager.py gui/gui_ssa.py tests/test_gui_filter_logic.py`: pass.
  4. `uv run --python 3.13 pytest -q tests/test_gui_filter_logic.py -k "best_fit_width_guard_ignores_single_extreme_outlier or header_context_menu_exposes_best_fit_visible_action or table_header_uses_merged_default_alias_for_extra_column"`: `3 passed`.
  5. kluster auto in this slice: issue(P4) -> clean -> clean.
- Evidence commit:
  1. pending commit in current sprint4 slice.
- Next cycle:
  1. immediate diagnostic slice for reprogramacao fields (`num_reprogramacoes`, `total_de_reprogramacoes`, `situacao_reprogramacao`) with source/use-risk mapping.
  2. decide policy: keep current behavior, force numeric canonical source, or defer to DB cleanup sprint.

## HISTORICAL SNAPSHOT 2026-03-04 09:11 - start from here

- Active branch: `codex/sprint-colunas-exibicao-db-saneamento`.
- Local release baseline: `4.30`.
- Slice status:
  1. sprint3 delivered in label lane: display-map merge hardening for table headers and add-columns selectors.
  2. canonical alias source now always includes defaults + gui overrides.
- Runtime change summary:
  1. `gui/gui_ssa.py`: switched window init mapping source to `load_display_mappings()` merged path.
  2. `tests/test_gui_filter_logic.py`: new regression `test_table_header_uses_merged_default_alias_for_extra_column`.
- Validation snapshot:
  1. `uv run --python 3.13 python -m py_compile gui/gui_ssa.py tests/test_gui_filter_logic.py`: pass.
  2. `uv run --python 3.13 ruff check gui/gui_ssa.py tests/test_gui_filter_logic.py`: pass.
  3. `uv run --python 3.13 ty check gui/gui_ssa.py tests/test_gui_filter_logic.py`: pass.
  4. `uv run --python 3.13 pytest -q tests/test_gui_filter_logic.py -k "table_header_uses_merged_default_alias_for_extra_column or on_header_clicked_sorts_num_reprogramacoes_mixed_types or header_context_menu_exposes_best_fit_visible_action"`: `3 passed`.
  5. kluster auto in this slice: clean -> clean.
- Evidence commit:
  1. pending commit in current sprint3 label slice.
- Next cycle:
  1. optional fine-grained label curation for remaining column aliases (display-only, no DB rewrite).
  2. keep db-saneamento as separate sprint boundary.

## HISTORICAL SNAPSHOT 2026-03-04 08:39 - start from here

- Active branch: `codex/sprint-colunas-exibicao-db-saneamento`.
- Local release baseline: `4.30`.
- Slice status:
  1. sprint1 completed: robust mixed-type sort for `num_reprogramacoes`.
  2. sprint2 completed: reusable `best fit colunas visiveis` wired in header menu and centralized in width manager.
- Runtime change summary:
  1. `gui/simple_width_manager.py`: new `compute_best_fit_width(...)` with anti-outlier guard.
  2. `gui/gui_ssa.py`: new header menu action `Best fit colunas visiveis` and helper methods for reusable best-fit application.
  3. `gui/gui_ssa.py`: `auto_fit_column` now prioritizes centralized best-fit logic.
  4. `tests/test_gui_filter_logic.py`: new regressions for menu action trigger and outlier guard behavior.
- Validation snapshot:
  1. `uv run --python 3.13 python -m py_compile gui/simple_width_manager.py gui/gui_ssa.py tests/test_gui_filter_logic.py`: pass.
  2. `uv run --python 3.13 ruff check gui/simple_width_manager.py gui/gui_ssa.py tests/test_gui_filter_logic.py`: pass.
  3. `uv run --python 3.13 ty check gui/simple_width_manager.py gui/gui_ssa.py tests/test_gui_filter_logic.py`: pass.
  4. `uv run --python 3.13 pytest -q tests/test_gui_filter_logic.py -k "header_context_menu_exposes_best_fit_visible_action or best_fit_width_guard_ignores_single_extreme_outlier or on_header_clicked_sorts_num_reprogramacoes_mixed_types"`: `3 passed`.
  5. kluster auto in this slice: clarification(P4) -> issue(P3) -> issue(P4) -> clean.
- Evidence commit:
  1. pending commit in current sprint2 slice.
- Next cycle:
  1. finish display-label cleanup lane (friendly names in table/add-columns, no DB rewrite).
  2. plan db-saneamento sprint as separate controlled scope.
  3. keep no-layout-change policy and minimal-risk patching.

## HISTORICAL SNAPSHOT 2026-03-04 08:28 - start from here

- Active branch: `codex/sprint-colunas-exibicao-db-saneamento`.
- Local release baseline: `4.30`.
- Slice status:
  1. sprint1 blocker hotfix delivered for mixed-type sort in `num_reprogramacoes`.
  2. targeted regression test added for asc/desc sort with legacy mixed values.
- Runtime change summary:
  1. `gui/gui_ssa.py`: `on_header_clicked` now uses robust sort path for `num_reprogramacoes` to avoid `int` vs `str` comparison crash.
  2. `tests/test_gui_filter_logic.py`: new regression `test_on_header_clicked_sorts_num_reprogramacoes_mixed_types`.
- Validation snapshot:
  1. `uv run --python 3.13 python -m py_compile gui/gui_ssa.py tests/test_gui_filter_logic.py`: pass.
  2. `uv run --python 3.13 ruff check gui/gui_ssa.py tests/test_gui_filter_logic.py`: pass.
  3. `uv run --python 3.13 ty check gui/gui_ssa.py tests/test_gui_filter_logic.py`: pass.
  4. `uv run --python 3.13 pytest -q tests/test_gui_filter_logic.py -k "on_header_clicked_sorts_num_reprogramacoes_mixed_types or reprogramacoes_menu_builds_without_responsavel_materialized"`: `2 passed`.
  5. kluster auto in this slice: clean -> clean.
- Evidence commit:
  1. pending commit in current hotfix slice.
- Next cycle:
  1. sprint2 step A: add reusable `best fit all visible columns` action (header/table context menu entry point) with anti-outlier rule.
  2. sprint2 step B: label cleanup in table and add-columns flow (display naming only, no DB rewrite).
  3. keep no-layout-change policy and minimal-risk patching.

## HISTORICAL SNAPSHOT 2026-03-04 08:14 - start from here

- Active branch: `codex/sprint-colunas-exibicao-db-saneamento`.
- Local release baseline: `4.30`.
- Slice status:
  1. GitHub snapshot of previous stable state created before sprint start:
     - tag `v4.29` on commit `bf78666e`;
     - release `SSA Consulta Rapida v4.29`.
  2. Version metadata promoted to `4.30`:
     - `VERSION`
     - `config/version.json`.
  3. Active reference docs promoted to `4.30` baseline.
  4. Technical sprint queued next: sorting fix for `num_reprogramacoes` + global best-fit for visible columns (with anti-outlier rule).
- Runtime change summary:
  1. none yet in runtime logic for this slice (release/version/doc sync only).
- Validation snapshot:
  1. `gh release view v4.29`: published.
  2. `git tag -l v4.29`: present and pushed.
- Evidence commit:
  1. pending commit in current version/doc sync slice.
- Next cycle:
  1. execute runtime Slice A (sort robustness for mixed int/str in `num_reprogramacoes`).
  2. execute runtime Slice B (reusable `best fit all visible columns` action with anti-outlier guard).
  3. keep no-layout-change policy and minimal-risk patches.

## HISTORICAL SNAPSHOT 2026-03-04 07:50 - start from here

- Active branch: `dev`.
- Slice status:
  1. PR #43 was merged into `dev` (`f6f10596`).
  2. feature branch cleanup completed; only `dev` and `main` remain local.
  3. remote branch cleanup completed; only `origin/dev` and `origin/main` remain (plus `origin/HEAD` pointer).
  4. local preference noise mitigation applied: `config/gui_main_preferences.json` added to `.gitignore` and marked `skip-worktree` locally.
  5. stash inspection completed; `stash@{0}` contains only `config/gui_main_preferences.json` and `data/ssas.db`.
- Runtime change summary:
  1. none in this slice (environment hygiene only).
- Validation snapshot:
  1. `git branch --list`: only `dev`, `main`.
  2. `git fetch --prune && git branch -r`: only `origin/dev`, `origin/main`, `origin/HEAD -> origin/main`.
  3. local gates (periodic): `uv run --python 3.13 python -m py_compile gui/gui_ssa.py gui/mixins/filter_gui_ssa_mixin.py gui/mixins/tab_context_gui_ssa_mixin.py gui/widgets/filter_help_dialog.py tests/test_gui_filter_logic.py`: pass.
  4. local gates (periodic): `uv run --python 3.13 ruff check gui/gui_ssa.py gui/mixins/filter_gui_ssa_mixin.py gui/mixins/tab_context_gui_ssa_mixin.py gui/widgets/filter_help_dialog.py tests/test_gui_filter_logic.py`: pass.
  5. local gates (periodic): `uv run --python 3.13 ty check gui/gui_ssa.py gui/mixins/filter_gui_ssa_mixin.py gui/mixins/tab_context_gui_ssa_mixin.py gui/widgets/filter_help_dialog.py tests/test_gui_filter_logic.py`: pass.
  6. local gates (periodic): `uv run --python 3.13 pytest -q tests/test_gui_filter_logic.py`: `125 passed, 1 skipped`.
  7. kluster auto in this slice: clean -> clean -> clean.
- Evidence commit:
  1. pending commit in current hygiene slice.
- Next cycle:
  1. confirm final stash action (`drop` recommended because it is only local prefs + local db delta).
  2. keep working from `dev` with minimal-scope stabilization slices.
- Local residue contract:
  1. `config/gui_main_preferences.json` should stay local-only and ignored in day-to-day status.
  2. `stash@{0}` pending explicit confirmation for final disposal.

## HISTORICAL SNAPSHOT 2026-03-04 06:29 - start from here

- Active branch: `codex/fix-filter-buttons-state-sync`.
- Slice status:
  1. high-risk stale async state after `Limpar Filtro` fixed.
  2. medium-risk undo snapshot gaps for column filter entry points fixed.
  3. debounce floor increased to encourage explicit `Aplicar` usage.
  4. deferred header context-menu apply + undo end-to-end regression added and validated.
  5. global clear now restores default column-filter baseline (no hardcoded subset).
  6. week tooltip encoding issue fixed; column-filter row now has 3 actions (`Aplicar`, `Limpar`, `Ocultar`).
  7. clear-search button wording clarified (`Limpar Busca`) with explicit scope tooltip.
  8. clear-search button enabled-state sync now updates both tabs in same cycle.
  9. undo button enabled-state now syncs between both tabs, including advanced-filter clear/restore flow.
  10. search apply/clear buttons now route through dedicated handlers per tab (`main` and `filters`) with equivalent behavior.
  11. regex safety guard in column filter path tightened to reduce catastrophic regex risk.
  12. PR #43 feedback triage executed; all `BUG_REAL` comments fixed in minimal patch.
  13. non-blocking/noise PR comments classified with explicit status (`DECISAO_INTENCIONAL`, `NAO_BLOQUEANTE_DEFERIDO`, `FALSO_POSITIVO`).
- Runtime change summary:
  1. `gui/mixins/filter_gui_ssa_mixin.py`: `clear_filter` now resets `_active_filter_search_display` and `_active_filter_search_request_id`.
  2. `gui/gui_ssa.py`: general search debounce now enforces minimum `1400 ms`.
  3. `gui/gui_ssa.py` + `gui/mixins/filter_gui_ssa_mixin.py`: undo snapshot capture added in header context apply and activate/deactivate column filter paths.
  4. `gui/widgets/filter_help_dialog.py`: help text aligned with real button behavior (`Aplicar` + `Ocultar`).
  5. `gui/mixins/filter_gui_ssa_mixin.py`: `_clear_all_filters_global` now resets column keys from `_column_filter_default_columns()`.
  6. `gui/gui_ssa.py`: week tooltip normalized to `Semana ISO atual`.
  7. `gui/mixins/filter_gui_ssa_mixin.py`: per-row column filter now has dedicated `Limpar` action that clears value without hiding row.
  8. `gui/widgets/filter_help_dialog.py`: filter-help updated to describe three row actions.
  9. `gui/gui_ssa.py`: clear-search button text and tooltip now state explicit scope (search only).
  10. `gui/mixins/filter_gui_ssa_mixin.py` + `gui/mixins/tab_context_gui_ssa_mixin.py`: clear-search button state now syncs across both tab contexts via centralized helper.
  11. `gui/mixins/filter_gui_ssa_mixin.py`: undo-state sync helper now updates all `undo_filter_btn` widgets across tab contexts.
  12. `gui/gui_ssa.py` + `gui/mixins/filter_gui_ssa_mixin.py`: search apply/clear now use tab-specific handlers while keeping same filtering behavior.
  13. `gui/mixins/filter_gui_ssa_mixin.py`: regex guard added (`meta_char_count` and alternation+quantifier block) for safer fallback to literal search.
  14. `gui/mixins/filter_gui_ssa_mixin.py`: `_clear_all_filters_global` now resets `_column_or_groups`/`_column_to_or_group` using `_reset_or_groups()`.
  15. `gui/mixins/filter_gui_ssa_mixin.py`: `_mk_remove_line` no longer hides errors with broad silent `except`.
  16. `gui/gui_ssa.py` + `gui/mixins/tab_context_gui_ssa_mixin.py`: debounce parse fallback now logs explicitly and bind flow no longer duplicates clear-button sync call.
- Validation snapshot:
  1. `uv run --python 3.13 python -m py_compile gui/gui_ssa.py gui/mixins/filter_gui_ssa_mixin.py gui/widgets/filter_help_dialog.py tests/test_gui_filter_logic.py`: pass
  2. `uv run --python 3.13 ruff check gui/gui_ssa.py gui/mixins/filter_gui_ssa_mixin.py gui/widgets/filter_help_dialog.py tests/test_gui_filter_logic.py`: pass
  3. `uv run --python 3.13 ty check gui/gui_ssa.py gui/mixins/filter_gui_ssa_mixin.py gui/widgets/filter_help_dialog.py tests/test_gui_filter_logic.py`: pass
  4. `uv run --python 3.13 pytest -q tests/test_gui_filter_logic.py -k "clear_filter or debounce or activate_column_filter_stores_undo_snapshot or deactivate_column_filter_stores_undo_snapshot"`: `15 passed, 1 skipped`
  5. `uv run --python 3.13 pytest -q tests/test_gui_filter_logic.py -k "test_header_context_menu_apply_stores_undo_snapshot"`: `1 passed`
  6. `uv run --python 3.13 pytest -q tests/test_gui_filter_logic.py -k "clear_all_filters_global_resets_full_filter_state_matrix or clear_all_filters_global_restores_default_column_filter_keys or clear_all_filters_global_resets_exclude_and_advanced_filters"`: `3 passed`
  7. `uv run --python 3.13 pytest -q tests/test_gui_filter_logic.py -k "default_column_filter_rows_show_apply_clear_and_hide_buttons or column_filter_buttons_flow or column_filter_row_clear_button_clears_value_without_hiding_row or clear_all_filters_global_restores_default_column_filter_keys or clear_filter_on_filters_tab_clears_search_in_all_tabs"`: `5 passed`
  8. `uv run --python 3.13 pytest -q tests/test_gui_filter_logic.py -k "test_clear_search_button_label_and_tooltip_are_explicit_on_both_tabs or test_clear_filter_clears_only_general_search_and_keeps_advanced_filters or test_clear_filter_on_filters_tab_clears_search_in_all_tabs"`: `3 passed`
  9. `uv run --python 3.13 pytest -q tests/test_gui_filter_logic.py -k "clear_filter_button_state_syncs_across_tabs_without_switch or clear_filter_button_reflects_active_filters or clear_filter_on_filters_tab_clears_search_in_all_tabs"`: `3 passed`
  10. `uv run --python 3.13 pytest -q tests/test_gui_filter_logic.py -k "undo_button_state_syncs_across_tabs_after_advanced_clear_and_restore or clear_advanced_filters_forces_refresh_when_pending_schedule or test_header_context_menu_apply_stores_undo_snapshot"`: `3 passed`
  11. `uv run --python 3.13 pytest -q tests/test_gui_filter_logic.py -k "search_buttons_route_to_tab_specific_handlers or clear_search_button_label_and_tooltip_are_explicit_on_both_tabs or clear_filter_button_state_syncs_across_tabs_without_switch or build_column_mask_blocks_heavy_regex_patterns"`: `4 passed`
  12. `uv run --python 3.13 pytest -q tests/test_gui_filter_logic.py -k "clear_all_filters_global_resets_or_group_metadata or clear_all_filters_global_resets_full_filter_state_matrix or clear_all_filters_global_restores_default_column_filter_keys or clear_filter_button_state_syncs_across_tabs_without_switch or undo_button_state_syncs_across_tabs_after_advanced_clear_and_restore"`: `5 passed`
  13. kluster auto: clean -> clean -> clean -> clean -> clean -> clean -> clean -> clean -> clean -> clean -> clean -> clean -> clean -> clean -> issue(P4 regex safety) -> clean -> clean -> clean -> clean -> clean -> clean
- Evidence commit:
  1. `2c7982b1` (`STABILITY_PATCH`).
  2. `22bbd3dc` (`STABILITY_PATCH`: follow-up regression for header context-menu undo path).
  3. `98269107` (`STABILITY_PATCH`: global clear baseline consistency).
  4. `776c5905` (`STABILITY_PATCH`: tooltip encoding fix and 3-button row behavior).
  5. `182c51b0` (`STABILITY_PATCH`: clear-search button wording clarity).
  6. `50bf94f0` (`STABILITY_PATCH`: cross-tab clear-button state sync).
  7. `32fca7c1` (`STABILITY_PATCH`: cross-tab undo-button state sync).
  8. `fcc3715e` (`STABILITY_PATCH`: tab-specific search handlers + regex guard hardening).
  9. `6f1ef11b` (`STABILITY_PATCH`: PR #43 bug-real triage fixes).
- Next cycle:
  1. keep no-layout-change policy and minimal-scope slices.
  2. monitor for regressions around async filter state and request-scoped display markers.
- Local residue contract:
  1. keep out-of-scope file unchanged: `config/gui_main_preferences.json`.
  2. keep stash untouched: `stash@{0}` (`local-wip-config-db-before-dev-switch-20260303`).

## HISTORICAL SNAPSHOT 2026-03-03 22:23 - start from here

- Active branch: `dev`.
- Slice status:
  1. Slice G delivered: targeted regression coverage for A/B/C in tests only.
  2. Sprint A-E package remains closed; no runtime behavior change introduced.
- Runtime change summary:
  1. no runtime file changed in this slice.
  2. new tests validate sidecar backup move, cancel classification cache behavior, and lock-file cleanup path.
- Validation snapshot:
  1. `uv run --python 3.13 python -m py_compile tests/test_app_logic_full_rescan_lock.py tests/test_import_deterministic_failure_cache.py tests/test_cli_enhancement_manager_lock_usage.py`: pass
  2. `uv run --python 3.13 ruff check tests/test_app_logic_full_rescan_lock.py tests/test_import_deterministic_failure_cache.py tests/test_cli_enhancement_manager_lock_usage.py`: pass
  3. `uv run --python 3.13 ty check tests/test_app_logic_full_rescan_lock.py tests/test_import_deterministic_failure_cache.py tests/test_cli_enhancement_manager_lock_usage.py`: pass
  4. `uv run --python 3.13 pytest -q tests/test_app_logic_full_rescan_lock.py tests/test_import_deterministic_failure_cache.py tests/test_cli_enhancement_manager_lock_usage.py`: `14 passed`
  5. kluster auto: clean -> clean
- Next cycle:
  1. keep stabilization in minimal slices and preserve no-layout-change policy.
  2. monitor runtime lanes; prioritize only bug-real deltas with focused tests.
- Local residue contract:
  1. keep out-of-scope file unchanged: `config/gui_main_preferences.json`.
  2. keep stash untouched: `stash@{0}` (`local-wip-config-db-before-dev-switch-20260303`).

## HISTORICAL SNAPSHOT 2026-03-03 19:31 - start from here

- Active branch: `dev`.
- Slice status:
  1. Sprint D delivered (docs-only): portability and naming consistency updates completed.
  2. no runtime module changed in this slice.
- Docs change summary:
  1. `docs/OHMYOPENCODE_MANUAL.md`: `$HOME` path normalization for bun path export.
  2. `docs/OPENCODE_CONFIG.md`: Gemini provider naming aligned to `google/antigravity-gemini-3-pro`.
  3. `docs/GUIA_MIGRACAO_NOVA_INSTALACAO.md`: runtime command examples now use `$PY_RUNTIME` with explicit fallback chain `3.13 -> 3.12 -> 3.11 -> 3.10`.
- Validation snapshot (periodic gates):
  1. `uv run --python 3.13 python -m py_compile core/app_logic.py interface/cli_enhancement_manager.py`: pass
  2. `uv run --python 3.13 ruff check core/app_logic.py interface/cli_enhancement_manager.py`: pass
  3. `uv run --python 3.13 ty check core/app_logic.py interface/cli_enhancement_manager.py`: pass
  4. `uv run --python 3.13 pytest -q tests/test_app_logic_full_rescan_lock.py tests/test_cli_enhancement_manager_lock_usage.py tests/test_import_deterministic_failure_cache.py`: `11 passed`
  5. kluster auto: clean -> clean
- Deferred order for next cycle:
  1. Sprint E (controlled debt cleanup in GUI table helper path, no layout change).
- Local residue contract:
  1. keep out-of-scope file unchanged: `config/gui_main_preferences.json`.
  2. keep stash untouched: `stash@{0}` (`local-wip-config-db-before-dev-switch-20260303`).

## HISTORICAL SNAPSHOT 2026-03-03 19:27 - start from here

- Active branch: `dev`.
- Slice status:
  1. Sprint B delivered: extraction error classification migrated from substring checks to structured `error_code`.
  2. deterministic-failure cache trigger covered by dedicated regression tests.
- Runtime change summary:
  1. `ExtractionError` in extractor/core now carries optional `error_code`.
  2. importer loop in `core/app_logic.py` uses `error_code` (`OPERATION_CANCELLED`, `MISSING_REQUIRED_COLUMNS`) instead of message substring parsing.
- Validation snapshot:
  1. `uv run --python 3.13 python -m py_compile core/app_logic.py extracao/extractor.py tests/test_import_deterministic_failure_cache.py`: pass
  2. `uv run --python 3.13 ruff check core/app_logic.py extracao/extractor.py tests/test_import_deterministic_failure_cache.py`: pass
  3. `uv run --python 3.13 ty check core/app_logic.py extracao/extractor.py tests/test_import_deterministic_failure_cache.py`: pass
  4. `uv run --python 3.13 pytest -q tests/test_import_deterministic_failure_cache.py tests/test_extracao.py tests/test_import_derivadas_trigger.py`: `24 passed`
  5. kluster auto: clean -> clean
- Deferred order for next cycle:
  1. Sprint D (docs-only consistency/portability, no runtime).
  2. Sprint E (controlled debt cleanup in GUI table helper, no layout change).
- Local residue contract:
  1. keep out-of-scope file unchanged: `config/gui_main_preferences.json`.
  2. keep stash untouched: `stash@{0}` (`local-wip-config-db-before-dev-switch-20260303`).

## HISTORICAL SNAPSHOT 2026-03-03 19:24 - start from here

- Active branch: `dev`.
- Slice status:
  1. Sprint C delivered: TOCTOU hardening for CLI settings lock-file path.
  2. focused race regression added for preexisting lock-file preservation.
- Runtime change summary:
  1. lock-file creation now attempts atomic exclusive create first (`O_EXCL`).
  2. when lock file already exists, flow reopens existing lock file without marking it as created-by-current-process.
  3. lock-file cleanup on lock acquisition failure now preserves third-party preexisting lock files.
- Validation snapshot:
  1. `uv run --python 3.13 python -m py_compile interface/cli_enhancement_manager.py tests/test_cli_enhancement_manager_lock_usage.py`: pass
  2. `uv run --python 3.13 ruff check interface/cli_enhancement_manager.py tests/test_cli_enhancement_manager_lock_usage.py`: pass
  3. `uv run --python 3.13 ty check interface/cli_enhancement_manager.py tests/test_cli_enhancement_manager_lock_usage.py`: pass
  4. `uv run --python 3.13 pytest -q tests/test_cli_enhancement_manager_lock_usage.py tests/test_cli_enhancement_manager_atomic_save.py`: `10 passed`
  5. kluster auto: clean -> clean
- Deferred order for next cycle:
  1. Sprint B (structured extraction error classification + deterministic cache coverage).
  2. Sprint D (docs consistency/portability, no runtime).
  3. Sprint E (controlled debt in GUI table helper path, no layout change).
- Local residue contract:
  1. keep out-of-scope file unchanged: `config/gui_main_preferences.json`.
  2. keep stash untouched: `stash@{0}` (`local-wip-config-db-before-dev-switch-20260303`).

## HISTORICAL SNAPSHOT 2026-03-03 19:20 - start from here

- Active branch: `dev`.
- Slice status:
  1. Sprint A delivered: lock/checkpoint hotfix in `_recreate_database_for_full_rescan`.
  2. Focused regression added for WAL checkpoint + DB rotation path.
- Runtime change summary:
  1. removed explicit `BEGIN IMMEDIATE` before `PRAGMA wal_checkpoint(TRUNCATE)` in the same checkpoint block.
  2. goal: avoid self-lock during full-rescan preparation.
- Validation snapshot:
  1. `uv run --python 3.13 python -m py_compile core/app_logic.py tests/test_app_logic_full_rescan_lock.py`: pass
  2. `uv run --python 3.13 ruff check core/app_logic.py tests/test_app_logic_full_rescan_lock.py`: pass
  3. `uv run --python 3.13 ty check core/app_logic.py tests/test_app_logic_full_rescan_lock.py`: pass
  4. `uv run --python 3.13 pytest -q tests/test_app_logic_full_rescan_lock.py`: `1 passed`
  5. kluster auto: clean -> clean
- Deferred order for next cycle:
  1. Sprint C (TOCTOU lock-file in CLI enhancement settings).
  2. Sprint B (structured extraction error classification + deterministic cache test).
  3. Sprint D and Sprint E (docs consistency and controlled debt).
- Local residue contract:
  1. keep out-of-scope file unchanged: `config/gui_main_preferences.json`.
  2. keep stash untouched: `stash@{0}` (`local-wip-config-db-before-dev-switch-20260303`).

## HISTORICAL SNAPSHOT 2026-03-03 15:25 - start from here

- Frozen policy baseline: `docs/POLICY_BASELINE_V1_1_FROZEN.md` (read before execution).

- Active branch: `dev`.
- Control-source baseline:
  1. `AGENTS.md` is the operational source of truth for process/policies.
  2. `docs/RECOVERY_BACKLOG.md` tracks deferred and non-blocking items.
  3. `docs/AGENTS_HANDOFF_NEXT_CYCLE.md` tracks compact handoff for next session.
- Critical continuity note:
  1. chat-only decisions are not sufficient.
  2. every approved policy/process update must be mirrored to control files in-repo.
- Incident and correction:
  1. commit `e3c7cdcb` consolidated AGENTS operational model.
  2. regression removed detailed kluster block.
  3. commit `ce0d3fc1` restored full kluster block.
- Migration contract for next chat:
  1. read `AGENTS.md` first.
  2. read top block of `docs/RECOVERY_BACKLOG.md` second.
  3. use this file only as session bootstrap and timeline map.

## HISTORICAL SNAPSHOT 2026-03-01 23:55 - start from here

- Active branch: `codex/dev-filtros-stability`.
- Local release baseline: `4.29`.
- Latest patch package:
  1. importer deterministic-failure cache marks for unchanged invalid files.
  2. derivadas dedicated phase kept compatible with existing contract/tests.
  3. advanced filter action buttons compacted and separator removed.
  4. multiselect popup width constrained and stale-widget guards added.
  5. canonical column candidate sources reduced to avoid noisy placeholder columns.
  6. direnv path exports now force `${VIRTUAL_ENV}/bin` precedence and refresh shell cache.
- Validation snapshot:
  1. touched-file `py_compile`, `ruff`, `ty`: pass
  2. focused pytest package (`import_derivadas_trigger`, `import_cancellation`, `gui_filters_advanced_logic`): `28 passed`
- Pending structural work remains deferred:
  1. split of large GUI routines/classes
  2. deeper breakup of multiselect menu builder

## HISTORICAL SNAPSHOT 2026-03-01 02:20

- Active branch: `codex/dev-filtros-stability`.
- Local release baseline: `4.27`.
- Runtime standard:
  1. use `uv run --python 3.13 ...` as first choice.
  2. fallback order: `3.12 -> 3.11 -> 3.10`.
  3. keep `requirements*.txt` as compatibility-only path.
- Compatibility matrix status:
  1. 3.10.18: pass
  2. 3.11.14: pass
  3. 3.12.11: pass
  4. 3.13.12: pass
- Focused gate used:
  1. `py_compile`, `ruff`, `ty`
  2. `pytest -q tests/test_open_docs_folder_nonblocking.py tests/test_cli_enhancement_manager_lock_usage.py tests/test_cli_enhancement_manager_atomic_save.py`
- GUI reference docs for continuity:
  1. `ANALISE_PROFUNDA_GUI.md`
  2. `GUI_SSA_REFACTOR_NOTES.md`

## HISTORICAL SNAPSHOT 2026-02-28 23:46

- Active branch: `codex/dev-filtros-stability`.
- Local release baseline: `4.27`.
- Release alignment status:
  1. streamlit deliveries from `v4.24.1` preserved.
  2. hardening package from `v4.25.0` preserved.
  3. metadata and docs aligned for pre-PR baseline `v4.27`.
- Working tree status:
  1. clean and synced with origin before pre-PR gates.
- Next execution order:
  1. run kluster on release/doc slice.
  2. run `py_compile`, `ruff`, `ty`, and focused `pytest`.
  3. commit atomic release/doc update and push.

## HISTORICAL SNAPSHOT 2026-02-28 22:10 - start from here

- Active branch: `codex/dev-filtros-stability`.
- Local release baseline: `4.25.0`.
- Sprint D status:
  1. P1 cache guard delivered in GUI + Streamlit cache paths.
  2. matrix item `9` moved to `resolved` (older deferred snapshots are historical only).
  3. stats now include `skipped_large_entries` and `max_entry_mb`.
- Optional P3 status:
  1. item `104` resolved: persistent width profile memory across sessions.
  2. item `107` resolved: render telemetry persistence across sessions.
- Streamlit colors/behavior follow-up:
  1. theme palettes + CSS variables implemented.
  2. runtime theme selector moved to header (always visible).
  3. selected theme now persists across sessions.
- Streamlit usability follow-up:
  1. situacao is always visible again and now includes quick mode + count labels.
  2. executor/emissor compacted to single-select (`(Todos)` fallback).
  3. quick "colunas exibidas" shortcut added in table tab.
  4. source controls moved to hidden advanced section in `Cache e API`.
  5. table render height is now dynamic per page row count.
  6. extra charts added (`Top executor`, `Top emissor`) under situacao distribution.
  7. presets renamed to business labels (`Operacao diaria`, `Analise completa`, `Minimo`).
  8. table metrics row expanded (`situacoes/executores/emissores distintos`).
- Item `92` status:
  1. resolved with cache architecture micro-refactor (shared helpers for get/store paths).
- Validation snapshot for Sprint D closeout:
  - `py_compile`, `ruff`, `ty` on touched streamlit/tests: pass
  - focused `pytest -q tests/test_filter_cache_locking.py tests/test_streamlit_filter_cache.py`: `40 passed`
- Deferred map (explicit, by difficulty):
  - structural (P2):
    1. `SSAMainWindow` split (`item 84`) - difficulty alta
    2. streamlit god-module split (`item 101`) - difficulty alta
- Retomada checklist (ordem de execucao):
  1. rodar `git status --short` e manter escopo minimo.
  2. selecionar somente item aprovado de risco real.
  3. apos editar: kluster auto -> `py_compile` -> `ruff` -> `ty` -> `pytest` focado.
  4. atualizar matrix/backlog/handoff no mesmo slice.
  5. manter blocos antigos somente como historico, sem usar como fonte de verdade.

## HISTORICAL SNAPSHOT 2026-02-28 12:25 - start from here

- Active branch: `codex/dev-filtros-stability`.
- Local release baseline: `4.25.0`.
- Sprint status:
  1. pacote "25 graves v4" aplicado e validado.
  2. docs de handoff/matriz/backlog sincronizados para continuidade.
  3. release local incrementado em +0.1 (`4.24.0 -> 4.25.0`).
- Validation snapshot (ultimo pacote tecnico):
  - touched-scope `py_compile`, `ruff`, `ty`: pass
  - focused pytest package: `30 passed`
- Kluster snapshot:
  - `kluster_code_review_auto` no pacote tecnico: clean
- Retomada checklist (ordem de execucao):
  1. rodar `git status --short` e confirmar escopo local.
  2. escolher slice da fila ativa em `docs/PENDING_ACTION_MATRIX.md` por risco real.
  3. aplicar patch minimo no slice escolhido.
  4. apos editar: rodar kluster auto e corrigir `agent_todo_list`.
  5. executar gates: `py_compile`, `ruff`, `ty`, `pytest` focado.
  6. atualizar `docs/PENDING_ACTION_MATRIX.md` e `docs/RECOVERY_BACKLOG.md`.

## HISTORICAL SNAPSHOT 2026-02-28 04:40 - start from here

- Active branch: `codex/dev-filtros-stability`.
- Local release baseline: `4.24.0`.
- Latest sprint package delivered (25 graves v4):
  1. command-handlers mapping path safety + centralized config resolution + save-cache coherence.
  2. importer guardrails for early cancel and unexpected `None` extractor result.
  3. stream wrapper reader-join timeout configurability across timeout/normal/error paths.
  4. focused regressions added for command-handlers/importer/stream wrappers.
- Validation snapshot:
  - touched-scope `py_compile`, `ruff`, `ty`: pass
  - focused pytest package: `30 passed`
- Kluster snapshot:
  - `kluster_code_review_auto` runs in this package: clean

## HISTORICAL SNAPSHOT 2026-02-28 04:10 - start from here

- Active branch: `codex/dev-filtros-stability`.
- Local release baseline: `4.24.0`.
- Latest sprint package delivered (20 graves v3):
  1. rescan dialog finish/cancel contract hardened for duplicate finish and running-cancel phase.
  2. rescan worker lifecycle hardened (pre-prune, stale active ref cleanup, deterministic cancel status, post-dialog prune).
  3. stream wrapper queue poll timeout configurable and faster deterministic loop exit conditions.
  4. sentinel path excluded from dropped-line accounting.
- Validation snapshot:
  - touched-scope `py_compile`, `ruff`, `ty`: pass
  - focused pytest (`rescan dialog + gui workers + stream guards`): `15 passed`
- Kluster snapshot:
  - `kluster_code_review_auto` runs in this package: clean

## HISTORICAL SNAPSHOT 2026-02-28 03:35 - start from here

- Active branch: `codex/dev-filtros-stability`.
- Local release baseline: `4.24.0`.
- Latest sprint package delivered (10 graves v2):
  1. rescan dialog cancel-close contract hardened.
  2. rescan worker active/stale/cap metadata handling hardened.
  3. stream wrapper dropped-line warning cadence and sentinel accounting hardened.
  4. focused regressions updated for dialog/worker/wrapper guards.
- Validation snapshot:
  - touched-scope `py_compile`, `ruff`, `ty`: pass
  - focused pytest (`rescan dialog + gui workers + stream guards`): `12 passed`
- Kluster snapshot:
  - `kluster_code_review_auto` runs in this package: clean

## HISTORICAL SNAPSHOT 2026-02-28 02:55 - start from here

- Active branch: `codex/dev-filtros-stability`.
- Local release baseline: `4.24.0`.
- Latest sprint package delivered (10 high-risk minimal fixes):
  1. dynamic GUI config path resolution API + loader usage in `gui/gui_config.py`.
  2. runtime/env path regressions in `tests/test_gui_main_configuration.py`.
  3. streamlit width-profile memory hardening and viewport fallback in `dev_env/streamlit_app.py`.
  4. streamlit snapshot clear idempotent guard + regressions in `tests/test_streamlit_filter_cache.py`.
  5. closeEvent rescan defensive shutdown hardening in `gui/gui_ssa.py` with focused regression in `tests/test_gui_filter_logic.py`.
- Validation snapshot:
  - `py_compile`, `ruff`, `ty` on touched files: pass
  - `uv run pytest -q tests/test_gui_main_configuration.py tests/test_streamlit_filter_cache.py tests/test_gui_filter_logic.py`: `150 passed, 1 skipped`
- Kluster snapshot:
  - `kluster_code_review_auto` runs in this package: clean

## HISTORICAL SNAPSHOT 2026-02-28 02:05 - start from here

- Active branch: `codex/dev-filtros-stability`.
- Local release baseline: `4.24.0`.
- Latest sprint package (5 high-risk minimal slices) delivered:
  1. closeEvent rescan retention cap/meta hardening in `gui/gui_ssa.py`.
  2. canonical candidate regression + rescan cap regression in `tests/test_gui_filter_logic.py`.
  3. config fallback regression for missing `SSA_CONFIG_DIR` in `tests/test_gui_main_configuration.py`.
  4. unified API snapshot clear helper in `dev_env/streamlit_app.py`.
  5. streamlit API snapshot clear regression in `tests/test_streamlit_filter_cache.py`.
- Validation snapshot:
  - `py_compile`, `ruff`, `ty` on touched files: pass
  - `uv run pytest -q tests/test_gui_filter_logic.py tests/test_gui_main_configuration.py tests/test_streamlit_filter_cache.py`: `145 passed, 1 skipped`
- Kluster snapshot:
  - `kluster_code_review_auto` runs in this package: clean
- Retomada checklist (ordem de execucao):
  1. validar `git status --short` e manter escopo minimo.
  2. escolher proximo slice aprovado na fila de risco real.
  3. apos editar: kluster auto -> `py_compile` -> `ruff` -> `ty` -> `pytest` focado.
  4. atualizar `docs/PENDING_ACTION_MATRIX.md` e `docs/RECOVERY_BACKLOG.md`.

## HISTORICAL SNAPSHOT 2026-02-28 01:10 - start from here

- Active branch: `codex/dev-filtros-stability`.
- Local release baseline: `4.24.0`.
- Latest streamlit slice delivered (requested order: item 2 then item 1):
  1. item 2: width-profile memory by width bucket in `dev_env/streamlit_app.py`.
  2. item 1: tabs/API smoke hardening with stable tab labels and API snapshot availability guard.
- Focused test scope:
  - `tests/test_streamlit_filter_cache.py` now includes bucket-memory and tabs/API smoke coverage.
- Validation snapshot:
  - `py_compile`, `ruff`, `ty` on touched files: pass
  - `uv run pytest -q tests/test_streamlit_filter_cache.py`: `21 passed`
- Kluster snapshot:
  - `kluster_code_review_auto` on touched files: clean
- Retomada checklist (ordem de execucao):
  1. `git status --short` e confirmar escopo local antes de novo patch.
  2. Escolher o proximo item aprovado da fila streamlit (patch minimo).
  3. Apos editar: kluster auto -> `py_compile` -> `ruff` -> `ty` -> `pytest` focado.
  4. Atualizar `docs/PENDING_ACTION_MATRIX.md` e `docs/RECOVERY_BACKLOG.md`.

## HISTORICAL SNAPSHOT 2026-02-28 00:18 - start from here

- Active branch: `codex/dev-filtros-stability`.
- Local release baseline: `4.24.0`.
- Latest streamlit slice delivered:
  1. telemetry profile window cap in `dev_env/streamlit_app.py` to bound session-state growth.
  2. focused regression added in `tests/test_streamlit_filter_cache.py`.
- Validation snapshot:
  - `py_compile`, `ruff`, `ty` on touched streamlit files: pass
  - `uv run pytest -q tests/test_streamlit_filter_cache.py`: `16 passed`
- Queue status:
  1. matrix has no immediate `pending` rows.
  2. streamlit queue remains active for next approved deferred item.
- Important:
  - blocks below are historical context and must not override this top block.

## HISTORICAL SNAPSHOT 2026-02-28 00:00 - start from here

- Active branch: `codex/dev-filtros-stability`.
- Local release baseline: `4.24.0`.
- Latest package delivered:
  1. kluster custom-rule alignment in `gui/gui_config.py`:
     - GUI config path now honors `SSA_CONFIG_DIR` with safe fallback.
  2. closeEvent lifecycle hardening in `gui/gui_ssa.py`:
     - active rescan worker now has defensive global-retention fallback in shutdown edge cases.
  3. focused regressions added:
     - `tests/test_gui_main_configuration.py` (`SSA_CONFIG_DIR` path resolution)
     - `tests/test_gui_filter_logic.py` (mid-shutdown `isRunning()` failure path)
- Validation snapshot (focused package scope):
  - `py_compile`, `ruff`, `ty`: pass
  - focused `pytest`: pass
- Current pending queue:
  1. no immediate `pending` in `docs/PENDING_ACTION_MATRIX.md`.
  2. streamlit stabilization queue remains separate.
- Important:
  - blocks below are historical context and must not override this top block.

## HISTORICAL SNAPSHOT 2026-02-27 16:32 - start from here

- Active branch: `codex/dev-filtros-stability`.
- Local release baseline: `4.24.0`.
- Residual runtime group status:
  1. `39, 46, 49, 50, 70, 76` is now documented as `resolved` in `docs/PENDING_ACTION_MATRIX.md`.
  2. Functional closure is based on already-merged runtime/test slices:
     - rescan worker closeEvent shutdown hardening;
     - global data-loader retention/prune consistency with lock snapshot;
     - cancel contract reinforcement across importer and extractor.
- Current pending queue after closeout:
  1. no immediate `pending` in this matrix.
  2. streamlit stabilization queue (separate track).
  3. `9` moved to `deferred` by explicit user decision (Opcao A).
- Additional closure in this cycle:
  1. `27` resolved with full `finish` payload assertion in `tests/test_import_cancellation.py`.
  2. `22/23` resolved in `tests/test_database_optimized_alias_views.py` (explicit init success contract + explicit cleanup).
  3. `21` resolved by existing concurrent-write coverage in `tests/test_caching_atomic_save.py`.
  4. `24/25` resolved by current lock/modal test hardening.
  5. `9` deferred by explicit user decision (Opcao A), no runtime patch.
- Retomada checklist (ordem de execucao):
  1. Confirm scope with `git status --short`.
  2. Pick next approved slice from streamlit queue or another explicitly selected deferred item.
  3. After edits: run kluster auto first, then `py_compile`, `ruff`, `ty`, and focused `pytest`.
  4. Update `docs/PENDING_ACTION_MATRIX.md` and `docs/RECOVERY_BACKLOG.md` with slice evidence.
- Important:
  - blocks below are historical context and must not override this top block.

## HISTORICAL SNAPSHOT 2026-02-27 15:53 - start from here

- Active branch: `codex/dev-filtros-stability`.
- Local release baseline: `4.24.0`.
- Current state from interrupted chat (local patch present, not committed):
  1. `gui/ssa/gui_filters_advanced_ui.py`:
     - action buttons container and sizing adjusted;
     - `_set_checkbox_checked_quietly` now keeps `QSignalBlocker` context and guarded manual unblock.
  2. `gui/mixins/filter_gui_ssa_mixin.py`:
     - add-column menu now builds deterministic ordered set with dedupe and duplicate-label disambiguation.
  3. `gui/widgets/column_manager_dialog.py`:
     - explicit `available_columns` no longer gets auto-polluted by full `display_map` reinjection.
  4. `gui/gui_ssa.py` + `gui/ssa/gui_workers.py`:
     - canonical menu candidate filter now uses cached non-null columns;
     - non-null cache is computed on data load and reused in UI candidate paths.
- Validation closeout for interrupted patch (done):
  - `uv run --python 3.13 python -m py_compile` on touched runtime files: pass
  - `uv run ruff check` on touched runtime files: pass
  - `uv run ty check` on touched runtime files: pass
  - `uv run pytest -q tests/test_gui_filter_logic.py tests/test_gui_main_configuration.py tests/test_display.py`:
    - `121 passed, 1 skipped`
  - kluster auto on touched runtime files: clean (no issues)
- Retomada checklist (ordem de execucao):
  1. Confirm local scope with `git status --short` and keep edits limited to expected files.
  2. Start next slice only with minimal patch over active filter/runtime scope.
  3. After any new edit, rerun kluster auto and local gates on touched scope.
  4. Keep non-blocking follow-ups in `docs/RECOVERY_BACKLOG.md`.
- Important:
  - sections below remain historical context and must not override this block.

## HISTORICAL SNAPSHOT 2026-02-26 21:40 - start from here

- Active branch: `codex/dev-filtros-stability`.
- Local release baseline: `4.24.0`.
- Latest delivered slice:
  1. Added single synchronized height lock for the 3 lower panels:
     - `Detalhes da SSA Selecionada`
     - `Filtros Avancados`
     - `Filtros por Coluna`
  2. Height sync is now triggered on init, tab change, resize, and column-filter panel rebuild.
  3. Tab/bind sync was switched to deferred queue (`QTimer.singleShot(0, ...)`) to avoid layout thrashing.
  4. Added regression test to lock equal min/max heights after resize.
  5. Code evidence:
     - `gui/gui_ssa.py`: `_compute_bottom_panel_target_height`, `_queue_bottom_panel_height_sync`, `_sync_bottom_panel_heights`
     - `gui/mixins/tab_context_gui_ssa_mixin.py`: bind path now queues height sync
     - `gui/mixins/filter_gui_ssa_mixin.py`: column-filter rebuild re-applies height sync
     - `tests/test_gui_filter_logic.py`: `test_bottom_panels_keep_single_synced_height_after_resize`
- Validation snapshot:
  - `python -m py_compile` (touched files): pass
  - `ruff check` (touched files): pass
  - `ty check` (touched files): pass
  - `uv run pytest -q` full suite: `582 passed, 6 skipped, 11 subtests passed`
  - focused GUI tests:
    - `test_bottom_panels_keep_single_synced_height_after_resize`: pass
    - `test_filters_tab_layout_keeps_bottom_panel_below_table_with_few_rows`: pass
- Important:
  - sections below remain historical context and must not override this block.

## HISTORICAL SNAPSHOT 2026-02-26 17:05 - start from here

- Active branch: `codex/dev-filtros-stability`.
- Local release baseline: `4.22.0`.
- Latest delivered slice:
  1. Re-ran MD audit and refreshed active control docs only.
  2. Enforced consistent status counter in filter clear flows:
     - `Status: SSAs filtradas: N de M`.
  3. Unified footer button style in SSA column-filter panel:
     - `Adicionar filtro de coluna` == `Limpar todos filtros de colunas`.
- Latest validation snapshot:
  - `python -m py_compile` on touched files: pass
  - `ruff check` on touched files: pass
  - `ty check` on touched files: pass
  - `.venv/bin/python -m pytest -q tests/test_gui_filter_logic.py tests/test_gui_main_configuration.py tests/test_display.py`
    => `117 passed, 1 skipped`
- Important:
  - sections below remain historical context and must not override this block.

## HISTORICAL SNAPSHOT 2026-02-26 14:07 - start from here

- Active branch: `codex/dev-filtros-stability`.
- Local release baseline: `4.22.0`.
- Latest delivered slice:
  1. Added regression tests for column-filter stability in `tests/test_gui_filter_logic.py`.
  2. Locked behavior for:
     - add-column menu candidate coverage + exclusion of legacy ghost aliases;
     - clear-all restore of default visible columns and hidden-line reset;
     - Apply/Hide controls present in default rows.
- Latest validation snapshot:
  - `.venv/bin/python -m pytest -q tests/test_gui_filter_logic.py` => `97 passed, 1 skipped`.
  - `.venv/bin/python -m pytest -q tests/test_gui_main_configuration.py` => `12 passed`.
  - `.venv/bin/python -m pytest -q tests/test_display.py tests/test_streamlit_filter_cache.py` => `20 passed`.
- Important:
  - any references below to `codex/import-review` or `PR #31` are historical and non-operational.

## Update 2026-02-26 (sprint migration snapshot)

- Active branch: `codex/dev-filtros-stability`.
- Delivered in this cycle:
  - Sprint A closed (extractor contract ids `6,7,33,34,35,58`).
  - Sprint B closed (rescan ids `11,12,28,29,38,79`; `71` stale-doc).
  - Sprint C closed (cli lock ids `13,26,30,31,41,80`).
  - E closed: pytest ignores removed from `pyproject.toml` and former script-like test files converted to deterministic pytest tests.
- Pending priority queue:
  1. Main/config/gui residual group: `39, 42, 43, 44, 46, 49, 50, 70, 76`.
  2. Streamlit stabilization queue (separate track).
- Guardrail:
  - keep minimal patches and avoid broad refactor while closing high-impact semantic/security items first.

## Update 2026-02-26 (deep analysis refresh)

- Gate snapshot:
  - `py_compile`, `ruff`, `ty`: pass.
  - `flake8`: baseline debt still high (`E501`/spacing), many legacy files.
  - `mypy`: baseline debt still high (missing stubs and typing issues in GUI/data paths).
  - `pylama`: unavailable in current env (`ModuleNotFoundError: pkg_resources`), no deps changed.
- Kluster snapshot:
  - stream scripts (`run_pytest_stream_and_log*.py`) now highest practical priority due security/path handling and perf pressure.
  - `main.py`, `core/config_manager.py`, `gui/gui_ssa.py` findings are mostly medium and structural; keep for later slices/sprints.
- Practical next queue:
  1. Stream scripts mini-slice: delivered (path guard + buffered flush + shared runner).
  2. Main resilience mini-slice (Batch 11): delivered with deterministic fail-fast behavior.
  3. Main/config/gui residual group and streamlit stabilization queue.

## Update 2026-02-26 (batch11 resilience lock delivered)

- `main.py`:
  - optimized import failure now fails fast by default with full context logs;
  - no automatic legacy retry path (including `--force-rescan`) to keep predictable runtime.
- `tests/test_main_import_fallback.py`:
  - added fail-fast lock test without retry.
- Validation:
  - `py_compile`, `ruff`, `ty` pass on touched files.
  - `uv run pytest -q tests/test_main_import_fallback.py tests/test_main_skip_import.py`: pass.

## Update 2026-02-26 (config restore fallback lock)

- Added focused regression tests in `tests/test_config_manager_mappings_integrity.py`:
  - restore write failure in `load_display_mappings_integrity` returns defaults in memory;
  - restore write failure in `load_column_mappings_integrity` returns defaults in memory.
- Validation:
  - `py_compile`, `ruff`, `ty` pass for touched files.
  - `uv run pytest -q tests/test_config_manager_mappings_integrity.py`: pass (`4 passed`).

## Update 2026-02-26 (stream scripts mini-slice delivered)

- Added shared helper `scripts/pytest_stream_common.py`.
- Both wrappers now use shared runtime path:
  - `scripts/run_pytest_stream_and_log.py`
  - `scripts/run_pytest_stream_and_log_v2.py`
- Added focused tests:
  - `tests/test_stream_log_wrapper_guards.py` (`4 passed`).

## OVERRIDE 2026-02-24 (ativo)

- Branch ativa para continuidade: `codex/dev-filtros-stability` (base `origin/dev`).
- Commits base desta rodada:
  - `1c56addb` fix(gui): stabilize advanced filters responsive grid and action buttons.
  - `06633471` fix(cli,db): harden config flow and maintenance schema targets.
  - `4adcf35b` fix(extracao): resolve tempo_excedido `m` ambiguity and add focused regression tests.
  - `resolved` fix(maintenance): avoid VACUUM-in-transaction and add script regression tests.
  - `resolved` test(db): add schema_manager identifier guard regression lock.
  - `resolved` fix(maintenance): harden analyze_db_integrity for empty-table and report consistency.
  - `resolved` perf(maintenance): refactor verify_database_integrity query flow.
  - `resolved` fix(cli): guard direct SSA search when `numero_ssa` is absent.
- Scope ativo:
  - estabilizacao de filtros avancados (resize/layout interno de botoes no painel de filtros avancados);
  - hardening pontual de CLI/schema/scripts de manutencao;
  - sem refactor amplo.
- Status de PR:
  - nenhum PR novo deve ser aberto sem autorizacao explicita do usuario.
- Nota de migracao:
  - secoes antigas com `codex/import-review` e PR `#31` abaixo ficam como historico de auditoria.
  - pendencias abertas foram separadas em duas filas no backlog:
    - `Pendencias longas`
    - `Pendencias para sprint exclusivo`

## Latest update 2026-02-24 (tempo_excedido)

- Parser update in `extracao/extractor.py`:
  - `m` interpreted as minutes.
  - months require explicit `mo`.
- Regression tests added in `tests/test_extracao.py`.
- Local validation for touched scope:
  - `python -m py_compile`, `ruff check`, `ty check`, `uv run pytest -q tests/test_extracao.py` all green.

## Latest update 2026-02-24 (maintenance scripts)

- `scripts_manutencao/limpar_banco.py` runtime fix:
  - `VACUUM` executes after `commit`, avoiding transaction error.
- logging aligned with local rule in same script:
  - `print()` replaced by robust logger calls.
- regression lock:
  - new `tests/test_scripts_manutencao_schema_targets.py` for `analyze_db_integrity` paths.

## Latest update 2026-02-24 (schema_manager guard lock)

- new `tests/test_schema_manager_identifier_guards.py`:
  - asserts invalid column identifiers are rejected with `ValueError`;
  - asserts valid missing columns are added.

## Latest update 2026-02-24 (analyze_db_integrity hardening)

- `scripts_manutencao/analyze_db_integrity.py`:
  - moved to robust logger outputs;
  - added `verify_database_integrity` entrypoint with compatibility alias;
  - fixed empty-table edge cases (`0` totals and `SUM NULL` handling);
  - aligned return payload with `stats_dict`.
- focused tests:
  - `tests/test_scripts_manutencao_schema_targets.py` validates aggregate empty-fields and empty-table no-crash path.

## Latest update 2026-02-24 (verify_database_integrity performance refactor)

- consolidated integrity metrics into one core SQL query;
- duplicate total now computed across full grouped set while keeping top-10 display;
- added guard before import-date query when `data_importacao` is not present;
- regression test expanded for duplicate-count correctness beyond top-10.

## Latest update 2026-02-24 (cli direct search guard)

- `interface/cli.py`:
  - avoids `KeyError` when `numero_ssa` column is absent in current dataframe;
  - uses exact match on normalized SSA and literal contains fallback with `regex=False`.
- focused regression:
  - `tests/test_cli_loop_missing_numero_ssa_guard.py`.

## Scope

- Branch: `codex/dev-filtros-stability`
- PR: sem PR ativo para esta branch neste momento
- Goal now: seguir com patches minimos de estabilidade e validar por slice.

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
uv run --python 3.13 python -m py_compile <files>
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
- uv run --python 3.13 python -m py_compile <files>
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

## Latest update 2026-02-24 (gui invalid regex fallback guard)

- `gui/mixins/filter_gui_ssa_mixin.py`:
  - fallback de regex invalido em `_build_column_mask` agora usa busca literal (`regex=False`);
  - cobre ambos caminhos: token explicito `~...` e modo padrao `regex`.
- focused regression:
  - `tests/test_filter_regex_invalid_fallback.py` com 2 cenarios:
    - regex explicita invalida (`~abc[`);
    - regex invalida no modo default `regex` (`abc[`).

## Latest update 2026-02-24 (cli remove-filter non-lifo guard)

- `interface/cli.py`:
  - `_handle_remove_filter` reaplica da base apenas quando a remocao e fora de ordem;
  - mantem reaplicacao do estado anterior para remocao LIFO (otimizacao).
- focused regression:
  - `tests/test_cli_remove_filter_non_lifo.py`:
    - remove termo do meio e garante base state;
    - remove ultimo termo e garante previous state.

## Nova regra 2026-02-24 (error-handling e performance)

- Manter tratamento de erro sempre presente, mas cobrindo porcoes relevantes de fluxo.
- Evitar `if/try` em excesso a cada poucas linhas, pois isso degrada legibilidade e pode introduzir custo.
- Nao usar `try/except` vazio nem suppress que esconda erro real.
- Para cada captura de erro, exigir saida objetiva (log curto) e tratamento coerente (retorno/raise/rollback).
- Em cada patch, revisar custo computacional para evitar solucoes caras por seguranca excessiva.

## Latest update 2026-02-24 (cli config refresh and query guard)

- `interface/cli.py`:
  - novo helper local para refresh pos `c/config`, removendo bloco duplicado;
  - refresh completo apenas quando `default_filters` muda;
  - sem mudanca de `default_filters`, mantem dataframe atual e evita requery caro;
  - `get_ssa_query` aplica allowlist de tabela (`ssa_table` + aliases legados).
- focused regression:
  - `tests/test_cli_config_preserve_session.py` valida caminho com reload e sem reload;
  - `tests/test_cli_get_ssa_query_identifier_guard.py` valida bloqueio de tabela fora da allowlist.

## Latest update 2026-02-24 (cli clearall table consistency)

- `interface/cli.py`:
  - `clearall` agora respeita `table_name` recebido pelo loop (`get_ssa_query(table_name)`).
- focused regression:
  - `tests/test_cli_clearall_uses_table_name.py`.

## Latest update 2026-02-24 (cli pagination tracker prune)

- `interface/cli.py`:
  - pagination tracker now has a small local manager class for state ops;
  - prune runs after stack mutations to remove orphan tracker entries.
  - pagination state key is persisted in `df.attrs` to preserve state across dataframe copies.
- focused regression:
  - `tests/test_cli_pagination_tracker_prune.py` (including copy-preservation check).

## Latest update 2026-02-24 (cli enhancement settings lock and root)

- `interface/cli_enhancement_manager.py`:
  - logger now uses robust logger API;
  - project root now resolved via `_get_project_root()`;
  - settings save keeps lock only on lockfile (no lock on temp file);
  - if lock cannot be acquired, save aborts and write is skipped.
- focused regression:
  - `tests/test_cli_enhancement_manager_lock_usage.py`.

## Latest update 2026-02-24 (command handlers root-safe mappings cache)

- `interface/command_handlers.py`:
  - path for mapping files now resolves from project root helper;
  - module logger aligned to robust logger API;
  - mappings cache moved to a small dedicated manager in-module.
- focused regression:
  - `tests/test_command_handlers_project_root_mapping.py`.

## Latest update 2026-02-24 (command handlers save flow cleanup)

- `interface/command_handlers.py`:
  - extracted `_attempt_save_settings(...)` to remove repeated `try/except ... pass` blocks;
  - helper returns explicit boolean (success/failure) for clear semantics;
  - call sites now rollback local changes when save fails;
  - save error handling remains centralized in `_save_settings_handler`.

## Latest update 2026-02-24 (optimized upsert legacy decimal key normalization)

- `armazenamento/database_optimized.py`:
  - lookup chunk now matches both canonical and legacy decimal SSA keys;
  - update branch deletes matched legacy key aliases plus canonical key before reinserting normalized rows;
  - savepoint-safe batch insert now uses parameterized `executemany` instead of `to_sql` in `DELETE + INSERT` path.
- focused regression:
  - `tests/test_database_optimized_alias_views.py::test_optimized_upsert_replaces_legacy_decimal_key_without_duplicate`.
- gate local deste slice:
  - `python -m py_compile armazenamento/database_optimized.py tests/test_database_optimized_alias_views.py`: pass.
  - `ruff check armazenamento/database_optimized.py tests/test_database_optimized_alias_views.py`: pass.
  - `ty check armazenamento/database_optimized.py tests/test_database_optimized_alias_views.py`: pass.
  - `uv run pytest -q tests/test_database_optimized_alias_views.py`: pass (3 tests).
- deferred-by-scope:
  - kluster P4 quality concern about function size in `insert_dataframe_optimized` (requires dedicated refactor sprint, out of current minimal patch scope).

## Latest update 2026-02-24 (canonical write policy for SSA ids)

- `armazenamento/database_optimized.py`:
  - removed legacy read compatibility branch for `numero_ssa + ".0"`.
  - added `_validate_canonical_storage_ids(...)` to reject decimal artifacts in write path.
- tests:
  - removed legacy-runtime compatibility test from `tests/test_database_optimized_alias_views.py`.
- gate local deste slice:
  - `python -m py_compile armazenamento/database_optimized.py tests/test_database_optimized_alias_views.py`: pass.
  - `ruff check armazenamento/database_optimized.py tests/test_database_optimized_alias_views.py`: pass.
  - `ty check armazenamento/database_optimized.py tests/test_database_optimized_alias_views.py`: pass.
  - `uv run pytest -q tests/test_database_optimized_alias_views.py`: pass (2 tests).
- kluster:
  - `kluster_code_review_auto`: clean (no issues).

## Latest update 2026-02-24 (canonical write parity in non-optimized upsert)

- `armazenamento/database_upsert_logic.py`:
  - added canonical storage normalization helper for SSA ids;
  - applied normalization to both `numero_ssa` and `derivada_de`;
  - added fail-fast canonical validation for storage id columns.
- tests:
  - added `tests/test_database_upsert_canonical_write.py`.
- gate local deste slice:
  - `python -m py_compile armazenamento/database_upsert_logic.py tests/test_database_upsert_canonical_write.py`: pass.
  - `ruff check armazenamento/database_upsert_logic.py tests/test_database_upsert_canonical_write.py`: pass.
  - `ty check armazenamento/database_upsert_logic.py tests/test_database_upsert_canonical_write.py`: pass.
  - `uv run pytest -q tests/test_database_upsert_canonical_write.py tests/test_database_optimized_alias_views.py`: pass (3 tests).

## Latest update 2026-02-24 (upsert chunk dedupe perf)

- `armazenamento/database_upsert_logic.py`:
  - `chunk_num_ssa` now uses `dropna().drop_duplicates().tolist()` (removed manual O(n2) loop).
- tests:
  - `tests/test_db_reset_and_upsert.py`: added duplicate-in-chunk regression scenario.
- gate local deste slice:
  - `python -m py_compile armazenamento/database_upsert_logic.py tests/test_db_reset_and_upsert.py`: pass.
  - `ruff check armazenamento/database_upsert_logic.py tests/test_db_reset_and_upsert.py`: pass.
  - `ty check armazenamento/database_upsert_logic.py tests/test_db_reset_and_upsert.py`: pass.
  - `uv run pytest -q tests/test_db_reset_and_upsert.py tests/test_database_upsert_canonical_write.py`: pass (6 tests).
- kluster:
  - `kluster_code_review_auto`: clean (no issues).

## Latest update 2026-02-24 (prepare_dataframe_for_upsert copy-path perf)

- `armazenamento/database_upsert_logic.py`:
  - `prepare_dataframe_for_upsert` now uses `frame.copy().reset_index(drop=True)`.
- tests:
  - added `tests/test_database_upsert_prepare.py` for immutability + normalization lock.
- gate local deste slice:
  - `python -m py_compile armazenamento/database_upsert_logic.py tests/test_database_upsert_prepare.py`: pass.
  - `ruff check armazenamento/database_upsert_logic.py tests/test_database_upsert_prepare.py`: pass.
  - `ty check armazenamento/database_upsert_logic.py tests/test_database_upsert_prepare.py`: pass.
  - `uv run pytest -q tests/test_database_upsert_prepare.py tests/test_db_reset_and_upsert.py`: pass (6 tests).
- kluster:
  - `kluster_code_review_auto`: clean (no issues).

## Latest update 2026-02-24 (logging mapping interpolation fix)

- files:
  - `main.py`
  - `dev_env/streamlit_app.py`
  - `tests/test_ascii_logging_filter.py`
- change:
  - ASCII logging filter keeps `dict` args intact for named interpolation (`%(name)s`) and keeps tuple path unchanged.
- gate local deste slice:
  - `python -m py_compile main.py dev_env/streamlit_app.py tests/test_ascii_logging_filter.py`: pass.
  - `ruff check main.py dev_env/streamlit_app.py tests/test_ascii_logging_filter.py`: pass.
  - `ty check main.py dev_env/streamlit_app.py tests/test_ascii_logging_filter.py`: pass.
  - `uv run pytest -q tests/test_ascii_logging_filter.py`: pass (2 tests).
- ops clarification:
  - legacy DB reset is operational/controlled; code path now enforces canonical write and validation for new writes.

## Latest update 2026-02-24 (streamlit cache fallback parity)

- `dev_env/streamlit_app.py`:
  - `get_cached_filter` and `cache_filter_result` now branch by `_use_session_state` and update proper stats backend.
- gate local deste slice:
  - `python -m py_compile dev_env/streamlit_app.py`: pass.
  - `ruff check dev_env/streamlit_app.py`: pass.
  - `ty check dev_env/streamlit_app.py`: pass.
  - `uv run pytest -q tests/test_ascii_logging_filter.py`: pass (2 tests).
- kluster:
  - `kluster_code_review_auto`: clean (no issues).

## Latest update 2026-02-24 (streamlit filter guards and telemetry)

- `dev_env/streamlit_app.py`:
  - column-presence guards added for `situacao`, `setor_executor`, `setor_emissor` filters;
  - slow-filter telemetry now uses logger instead of `st.info` per cache miss.
- gate local deste slice:
  - `python -m py_compile dev_env/streamlit_app.py`: pass.
  - `ruff check dev_env/streamlit_app.py`: pass.
  - `ty check dev_env/streamlit_app.py`: pass.
  - `uv run pytest -q tests/test_ascii_logging_filter.py`: pass (2 tests).
- kluster:
  - `kluster_code_review_auto`: clean (no issues).

## Latest update 2026-02-24 (streamlit import ui unblock)

- `dev_env/streamlit_app.py`:
  - removed `time.sleep(0.5)` from `_execute_import` finally block.
- gate local deste slice:
  - `python -m py_compile dev_env/streamlit_app.py`: pass.
  - `ruff check dev_env/streamlit_app.py`: pass.
  - `ty check dev_env/streamlit_app.py`: pass.
  - `uv run pytest -q tests/test_ascii_logging_filter.py`: pass (2 tests).
- kluster:
  - `kluster_code_review_auto`: clean (no issues).

## Latest update 2026-02-24 (streamlit broad hardening cycle)

- `dev_env/streamlit_app.py`:
  - safe import fallback when `streamlit` is missing;
  - `StreamlitFilterCache` now uses centralized backend resolver;
  - cache get/put now supports `df_token` and `apply_all_filters_cached` computes token via `_compute_df_cache_token`;
  - token computation optimized with sample-only string conversion + memoization in `df.attrs`;
  - removed deprecated pandas CoW option assignment.
- tests:
  - added `tests/test_streamlit_filter_cache.py`.
- gate local deste slice:
  - `python -m py_compile dev_env/streamlit_app.py tests/test_streamlit_filter_cache.py`: pass.
  - `ruff check dev_env/streamlit_app.py tests/test_streamlit_filter_cache.py`: pass.
  - `ty check dev_env/streamlit_app.py tests/test_streamlit_filter_cache.py`: pass.
  - `uv run pytest -q tests/test_streamlit_filter_cache.py tests/test_ascii_logging_filter.py`: pass (4 tests).
- kluster:
  - `kluster_code_review_auto`: clean (no issues).

## Latest update 2026-02-24 (streamlit long cycle: layout and broad improvements)

- `dev_env/streamlit_app.py`:
  - UI repositioning/layout expanded to tabs: `Filtros`, `Tabela`, `Exportacao`, `Cache e API`.
  - table rendering now paginates filtered data (`_paginate_dataframe`) before arrow conversion/render.
  - API fetch now manual via button; snapshot persisted in session state and clearable.
  - runtime detection strengthened and non-streamlit import fallback added.
  - cache backend logic centralized; cache keys now include lightweight memoized dataframe token.
  - removed deprecated pandas CoW option write.
- tests:
  - expanded `tests/test_streamlit_filter_cache.py`.
- gate local deste slice:
  - `python -m py_compile dev_env/streamlit_app.py tests/test_streamlit_filter_cache.py`: pass.
  - `ruff check dev_env/streamlit_app.py tests/test_streamlit_filter_cache.py`: pass.
  - `ty check dev_env/streamlit_app.py tests/test_streamlit_filter_cache.py`: pass.
  - `uv run pytest -q tests/test_streamlit_filter_cache.py tests/test_ascii_logging_filter.py`: pass (6 tests).
- kluster:
  - `kluster_code_review_auto`: clean (no issues).

## Latest update 2026-02-24 (streamlit long cycle v2)

- `dev_env/streamlit_app.py`:
  - filters tab now uses form submit/reset workflow (state stored in `session_state`);
  - introduced `_normalize_filter_selection(...)` to skip no-op full selections;
  - mixed-type safe `_build_filter_options(...)` sorting;
  - table tab now supports sorting before pagination;
  - rerun fallback supports `rerun` and `experimental_rerun` APIs.
- tests:
  - expanded `tests/test_streamlit_filter_cache.py`.
- gate local deste slice:
  - `python -m py_compile dev_env/streamlit_app.py tests/test_streamlit_filter_cache.py`: pass.
  - `ruff check dev_env/streamlit_app.py tests/test_streamlit_filter_cache.py`: pass.
  - `ty check dev_env/streamlit_app.py tests/test_streamlit_filter_cache.py`: pass.
  - `uv run pytest -q tests/test_streamlit_filter_cache.py tests/test_ascii_logging_filter.py`: pass (8 tests).
- kluster:
  - `kluster_code_review_auto`: clean (no issues).

## Latest update 2026-02-24 (streamlit long cycle v3)

- `dev_env/streamlit_app.py`:
  - fixed scope bug: table tab now renders regardless of API toggle state;
  - introduced width profile state (`Compacto/Padrao/Largo/XL`) for deterministic table width behavior;
  - replaced hardcoded table `column_config` with `_build_streamlit_column_config(...)` + `SimpleWidthManager`;
  - added fallback path in column-config builder when streamlit column API is unavailable.
- tests:
  - expanded `tests/test_streamlit_filter_cache.py` with width-bucket and column-config assertions.
- gate local deste slice:
  - `python -m py_compile dev_env/streamlit_app.py tests/test_streamlit_filter_cache.py`: pass.
  - `ruff check dev_env/streamlit_app.py tests/test_streamlit_filter_cache.py`: pass.
  - `ty check dev_env/streamlit_app.py tests/test_streamlit_filter_cache.py`: pass.
  - `uv run pytest -q tests/test_streamlit_filter_cache.py`: pass (10 tests).
- kluster:
  - `kluster_code_review_auto`: clean (no issues).

## Latest update 2026-02-24 (streamlit long cycle v4)

- final scope delivered in this cycle:
  - table tab flow fix (no hidden coupling with API toggle);
  - width profile controls + deterministic width buckets from `SimpleWidthManager`;
  - path safety validation for sidebar file-system inputs;
  - cache token guard for zero-column frames;
  - width manager signature alignment in GUI table call site.
- regression/tests:
  - `tests/test_streamlit_filter_cache.py` now 11 passing tests.
- gate local deste slice:
  - `python -m py_compile dev_env/streamlit_app.py gui/simple_width_manager.py gui/ssa/gui_table.py tests/test_streamlit_filter_cache.py`: pass.
  - `ruff check dev_env/streamlit_app.py gui/simple_width_manager.py gui/ssa/gui_table.py tests/test_streamlit_filter_cache.py`: pass.
  - `ty check dev_env/streamlit_app.py gui/simple_width_manager.py gui/ssa/gui_table.py tests/test_streamlit_filter_cache.py`: pass.
  - `uv run pytest -q tests/test_streamlit_filter_cache.py`: pass (11 tests).
- kluster progression:
  - intermediate P4/P3 findings resolved in-sequence;
  - final `kluster_code_review_auto`: clean.

## Latest update 2026-02-24 (streamlit long cycle v5 final)

- final width-manager decision for this cycle: deterministic signature without external override params.
- `gui/ssa/gui_table.py` updated to same deterministic call contract.
- final kluster state: clean after iterative fixes.

## Latest update 2026-02-25 (streamlit long cycle v6)

- layout/positioning expansion delivered in `dev_env/streamlit_app.py`:
  - filters form grouped by functional blocks;
  - table controls split in two rows and view mode toggle added;
  - export and cache/api tabs reorganized for faster scan and less crowding.
- behavioral scope unchanged for filter semantics and data processing.
- gate local deste slice:
  - `python -m py_compile dev_env/streamlit_app.py`: pass.
  - `ruff check dev_env/streamlit_app.py tests/test_streamlit_filter_cache.py`: pass.
  - `ty check dev_env/streamlit_app.py tests/test_streamlit_filter_cache.py`: pass.
  - `uv run pytest -q tests/test_streamlit_filter_cache.py`: pass (11 tests).
- kluster:
  - `kluster_code_review_auto`: clean.

## Latest update 2026-02-25 (streamlit long cycle v7)

- delivered:
  - `Compacto` toggle in table controls;
  - compact caption behavior in table mode;
  - render telemetry by width profile in cache panel.
- gate local deste slice:
  - `python -m py_compile dev_env/streamlit_app.py`: pass.
  - `ruff check dev_env/streamlit_app.py tests/test_streamlit_filter_cache.py`: pass.
  - `ty check dev_env/streamlit_app.py tests/test_streamlit_filter_cache.py`: pass.
  - `uv run pytest -q tests/test_streamlit_filter_cache.py`: pass (11 tests).
- kluster:
  - `kluster_code_review_auto`: clean.

## Latest update 2026-02-25 (streamlit long cycle v7.1)

- follow-up cleanup in `dev_env/streamlit_app.py`:
  - extracted small helpers for table caption and render telemetry update.
- behavior unchanged; maintenance improved.

## Latest update 2026-02-25 (streamlit direct-run import fix)

- fixed startup path issue for direct invocation:
  - `/Users/menon/git/SSA_Consulta_Rapida/.venv/bin/python /Users/menon/git/SSA_Consulta_Rapida/dev_env/streamlit_app.py`
  - previous error `ModuleNotFoundError: No module named 'core'` is resolved.

## Latest update 2026-02-25 (streamlit tests)

- added regression tests for:
  - `_build_table_caption` in compact and non-compact modes;
  - `_update_render_telemetry` session-state accumulation.
- focused streamlit test suite now at 14 passing tests.

## Latest update 2026-02-25 (streamlit telemetry panel refinement)

- cache tab improvements:
  - profile picker for render telemetry;
  - dedicated button to clear telemetry state;
  - telemetry caption formatting centralized in helper.
- focused streamlit suite now 15 passing tests.

## Latest update 2026-02-25 (qwen config and batch01 start)

- created `docs/QWEN_CODE_DELEGATION_CONFIG.md` with setup, delegation rules, and validation contract.
- batch01 progress:
  - done ids 21, 22, 23.
- focused tests: 5 passed.

## Latest update 2026-02-25 (batch01 tests + qwen check delegation)

- batch01 completed for ids 24/25/27/28/29 with focused test-only patches.
- qwen delegation confirmed in practice for `ruff` + `ty` execution (with `-y`), followed by independent final validation by main agent.
- observed tradeoff: qwen helps reduce reasoning-token load for repetitive checks, but has higher per-call latency.

## Latest update 2026-02-25 (extractor batch02)

- scope delivered:
  - stabilized `read_report` return contract to avoid `NoneType` regressions in legacy callers.
  - primary Excel read in `read_report` now goes through `import_excel_robust`.
  - preserved compatibility with controlled fallback to `extract_data_from_excel` when robust output is empty.
- tests and checks:
  - `py_compile`, `ruff`, `ty` for touched files: pass.
  - focused test `tests/test_extracao.py`: 5 passed.
- risk note:
  - strict "robust-only everywhere" migration in full extraction stack is intentionally deferred to exclusive sprint (cross-module impact).

## Latest update 2026-02-25 (extractor batch02 follow-up)

- `read_report` ficou com caminho unico de ingestao via `import_excel_robust`.
- para evitar custo excessivo em arquivos grandes no caminho de resultado vazio, foi aplicado gate por tamanho com `SSA_READ_REPORT_FALLBACK_MAX_MB` (default 8).
- parse de env invalido agora cai para default com warning.
- suite focada `tests/test_extracao.py` em 7/7.

## Latest update 2026-02-25 (extractor batch02 cleanup)

- ajuste final: removido trecho de guard de fallback-size que ficou incoerente apos robust-only.
- estado final: `read_report` robust-only, sem fallback legado.

## Latest update 2026-02-25 (batch03 config path alignment)

- `config_manager` agora usa caminho resolvido por env (`SSA_CONFIG_DIR`) de forma consistente tambem em load/save/ensure.
- env de config agora passa por validacao de path safety, com fallback para `config` quando invalido.
- suite focada de config verde (5/5).

## Latest update 2026-02-25 (batch03 fail-fast)

- `ensure_default_settings` agora retorna erro explicito (RuntimeError agregado) quando falha em criar/copi ar arquivos de config.
- cobertura nova valida os dois caminhos de falha (copy e generation).
- status da suite focada de config: 7/7.

## Latest update 2026-02-25 (batch03 startup contract final)

- estado final de `ensure_default_settings`:
  - retorna lista de erros para diagnostico.
  - pode levantar `RuntimeError` quando `fail_fast=True`.
- `main` utiliza modo resiliente (`fail_fast=False`) com warning explicito.

## Latest update 2026-02-25 (batch03 final stabilization)

- `config_manager._atomic_copy_file` agora usa `NamedTemporaryFile(delete=False)`.
- `main` segue com `ensure_default_settings(fail_fast=False)` e warning de erros nao bloqueantes.
- suite focada de config permanece 7/7.

## Latest update 2026-02-25 (batch04 lock retry hardening)

- lock de settings da CLI enhancement recebeu retry limitado e nao bloqueante.
- comportamento em contencao: tenta poucas vezes e aborta sem travar a CLI.
- suite focada lock/atomic da CLI enhancement: 7/7.

## Latest update 2026-02-25 (batch04 windows lock retries)

- melhorias no lock Windows da CLI enhancement: `LK_NBLCK` com retry limitado e fail-fast para erro nao relacionado a lock.
- suite focada lock/atomic da CLI enhancement agora em 9/9.
- qwen foi usado para tarefas repetitivas de validacao; revisao final continuou sob controle do agente principal.

## Latest update 2026-02-25 (batch04 windows lock region normalization)

- lock Windows da CLI enhancement agora usa regiao fixa de 1 byte com retry limitado.
- erro nao relacionado a lock contention no backend Windows nao entra em retry.
- suite lock/atomic da CLI enhancement permaneceu verde em 9/9.

## Latest update 2026-02-26 (batch05+06 sync)

- batch05 (ids 3,14,54,55,57,59,61):
  - `id 3`/`id 59` tratados com patch minimo em `core/app_logic.py` para rastreabilidade de erro inesperado sem mudar fluxo.
  - `id 14/54/55/57/61` classificados como stale-doc com evidencia no codigo/testes atuais.
- batch06 (ids 1,2,32,47,60,75,81):
  - `id 60` recebeu hardening adicional em `armazenamento/database_optimized.py` com quoting estrito de tabela validada.
  - demais ids confirmados como cobertos no estado atual (rollback sem suppress, normalizacao, guardas de identificador).
- teste novo:
  - `tests/test_database_optimized_identifier_guards.py::test_insert_dataframe_optimized_rejects_invalid_table_identifier`
- gate do ciclo:
  - `py_compile`, `ruff`, `ty` nos arquivos tocados: pass.
  - pytest focado:
    - `tests/test_import_single_error_classification.py`
    - `tests/test_database_optimized_identifier_guards.py`
    - `tests/test_database_optimized_alias_views.py`
    - `tests/test_command_handlers_save_settings.py`
    - `tests/test_rescan_progress_dialog.py`
    - `tests/test_main_skip_import.py`
    - resultado: 16 passed.

## Latest update 2026-02-26 (batch07.1 ids 53/68)

- id 53:
  - cobertura nova adicionada em `tests/test_caching.py` para garantir reenfileiramento quando `_safe_file_stat` retorna `None`.
- id 68:
  - confirmado contrato atual de `load_display_mappings_integrity` (releitura do arquivo restaurado antes de fallback em memoria).
- docs:
  - `docs/PENDING_ACTION_MATRIX.md` e `docs/RECOVERY_BACKLOG.md` sincronizados com status `resolved`.
- gate do ciclo:
  - `py_compile`, `ruff`, `ty` em arquivos tocados: pass.
  - `pytest -q tests/test_caching.py tests/test_config_manager_mappings_integrity.py`: 8 passed.

## Latest update 2026-02-26 (batch07.2 id 66)

- id 66:
  - `tests/test_rescan_progress_dialog.py` mudou de `processEvents()` unico para espera curta por condicao (`_spin_until`) em pontos sensiveis.
  - objetivo: reduzir nondeterminism/flakiness sem alterar runtime.
- docs:
  - `docs/PENDING_ACTION_MATRIX.md` e `docs/RECOVERY_BACKLOG.md` sincronizados.
- gate do ciclo:
  - `py_compile`, `ruff`, `ty` nos arquivos tocados: pass.
  - `pytest -q tests/test_rescan_progress_dialog.py tests/test_gui_workers_rescan_data.py`: 6 passed.

## Latest update 2026-02-26 (batch08 id 64)

- id 64:
  - confirmado que cleanup de `gui/workers/rescan_worker.py` nao usa `suppress` e registra warning em falha de detach.
- docs:
  - `docs/PENDING_ACTION_MATRIX.md` e `docs/RECOVERY_BACKLOG.md` sincronizados para `resolved`.
- gate do ciclo:
  - `pytest -q tests/test_rescan_worker_cleanup.py`: 2 passed.

## Latest update 2026-02-26 (batch09-10 ids 62/67/69/72/74/77/78)

- scripts stream:
  - confirmados `nonlocal` correto, lock para contador compartilhado e caminho de sentinel nao bloqueante em v1/v2.
  - guard de warning duplicado (`warn_count != last_warned`) presente em v1/v2.
- config mappings:
  - `load_column_mappings_integrity()` confirmado com releitura de arquivo restaurado antes de fallback.
- docs:
  - `docs/PENDING_ACTION_MATRIX.md` e `docs/RECOVERY_BACKLOG.md` sincronizados para os ids acima.
- gate do ciclo:
  - `py_compile`, `ruff`, `ty` nos scripts de stream: pass.

## Latest update 2026-02-26 (batch11.1 id 8)

- id 8:
  - `FilterCache.put()` agora valida tipo e ignora valor nao-DataFrame sem levantar excecao.
  - docstring de `put()` alinhada ao contrato real.
  - logger do modulo migrado para `get_robust_logger()`.
- testes:
  - novo teste em `tests/test_filter_cache_locking.py` cobrindo entrada invalida.
- docs:
  - `docs/PENDING_ACTION_MATRIX.md` e `docs/RECOVERY_BACKLOG.md` sincronizados.
- gate do ciclo:
  - `py_compile`, `ruff`, `ty` nos arquivos tocados: pass.
  - `pytest -q tests/test_filter_cache_locking.py tests/test_filter_worker.py`: 10 passed.

## Latest update 2026-02-26 (batch12 ids 4/5/73)

- ids 4/5:
  - confirmados como resolvidos pelo contrato atual de `ensure_default_settings` e `_atomic_write_json_file` (erro explicito, sem suppress silencioso).
- id 73:
  - confirmado como resolvido pelo uso de `NamedTemporaryFile(delete=False)` em `_atomic_copy_file`.
- docs:
  - `docs/PENDING_ACTION_MATRIX.md` e `docs/RECOVERY_BACKLOG.md` sincronizados.
- gate do ciclo:
  - `pytest -q tests/test_config_manager_atomic_save.py tests/test_config_manager_mappings_integrity.py tests/test_column_mappings_integrity.py`: 8 passed.

## Latest update 2026-02-26 (global summary + next steps)

- current matrix snapshot:
  - total=108
  - pending=65
  - resolved=27
  - stale-doc=5
  - deferred=11
- security:
  - `main` recebeu hotfix de dependencia (`pillow>=12.1.1` em manifests de build).
  - dependabot open alerts para pillow retornou `[]`.
- next execution queue:
  - extractor validation/contract: ids 6/7/33/34/35/58
  - rescan worker concurrency: ids 11/12/38/79
  - cli enhancement lock residual: ids 13/26/30/31/41/80
  - main fallback/debug resilience: ids 15/16/45/48

## Atualizacao 2026-03-01 (ciclo gui-tema-import)
- Corrigido tema dos menus de selecao para herdar cores do tema ativo (sem fallback escuro fixo).
- Reduzido tamanho efetivo dos botoes Aplicar/Limpar dos filtros avancados.
- Corrigido comportamento de largura de popup dos seletores para evitar expansao excessiva.
- Reforcado import otimizado: deduplicacao por numero_ssa e falha explicita em lookup SQL parcial.
- Corrigidos comentarios recentes de review (scripts/tests/docs) e removidos emojis em arquivos versionados.

## Atualizacao 2026-03-05 (slice import schema drift)
- Contexto:
  - problema confirmado de drift no reimport: colunas dinamicas invalidas podiam gerar sufixos (`nome_paciente_1`) e lixo (`nan`, `nan_1`, `nan_2`).
- O que foi aplicado:
  - patch minimo em `armazenamento/database_upsert_logic.py` para:
    - descartar headers placeholder,
    - sanitizar com mapeamento deterministico,
    - reutilizar nome canonico existente quando aplicavel,
    - aplicar whitelist no estado final antes de sincronizar schema.
  - testes novos em `tests/test_db_reset_and_upsert.py` cobrindo:
    - reimport sem criacao de sufixo,
    - descarte de placeholder,
    - enforce de whitelist apos sanitizacao.
- Validacao rodada:
  - gates tecnicos verdes (`py_compile`, `ruff`, `ty`).
  - bateria focada verde: `39 passed`.
  - reproducao manual verde: sem `nome_paciente_1` e sem colunas `nan*`.
- Observacoes operacionais:
  - `opencode run` ainda bloqueado por billing no host atual.
  - `snyk test --all-projects` sem retorno util por timeout.
