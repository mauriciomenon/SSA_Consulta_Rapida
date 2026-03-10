# AGENTS Handoff For Next Cycle

Este handoff esta pronto para reutilizacao no proximo ciclo.

## CURRENT TRUTH 2026-03-10 09:18 - authoritative block

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
