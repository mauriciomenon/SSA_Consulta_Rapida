# AGENTS Handoff For Next Cycle

Este handoff esta pronto para reutilizacao no proximo ciclo.

## CURRENT TRUTH 2026-03-10 00:55 - authoritative block

- Slice entregue:
  1. `gui/gui_ssa.py`:
     - remove sync do quick filter `Setor Executor` com `_advanced_filters`.
     - mantem sync apenas em OR group/filtros por coluna (`setor_executor`/`setor_emissor`).
     - popup do combo rapido segue com rolagem real (`combobox-popup: 0`, `maxVisibleItems=14`, scrollbar no `view`).
  2. `tests/test_gui_filter_logic.py`:
     - contrato atualizado: quick combo altera OR group de coluna, sem alterar `_advanced_filters`.
     - cobertura mantida para popup limitado/rolavel.
- Gates desta rodada:
  1. `py_compile`, `ruff`, `ty` -> pass.
  2. `pytest` focado em quick setor/OR group -> `2 passed`.
- Pendencia deferida:
  1. debts antigos de arquitetura/performance em `gui/gui_ssa.py` fora deste slice.
- Residuos locais fora de escopo (nao commitar):
  1. `data/ssas.db`
  2. `config/settings.json.bak_20260308_212715`

## HISTORICAL SNAPSHOT 2026-03-10 00:42

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
