# AGENTS Handoff For Next Cycle

Este handoff esta pronto para reutilizacao no proximo ciclo.

## CURRENT TRUTH 2026-03-10 16:45 - authoritative block

- Slice entregue:
  1. ajuste de layout: chips/atalhos de filtro salvo reposicionados para a linha da pesquisa.
- Arquivos alterados:
  1. `gui/gui_ssa.py`
  2. `tests/test_gui_filter_logic.py`
  3. `docs/RECOVERY_BACKLOG.md`
  4. `docs/NEXT_CHAT_MIGRATION.md`
  5. `docs/AGENTS_HANDOFF_NEXT_CYCLE.md`
- Validacao:
  1. `py_compile`, `ruff`, `ty` no escopo alterado -> pass.
  2. `pytest` focado (`3` testes de layout/filtro) -> `3 passed`.
- Decisao aplicada:
  1. `filter_tags_widget` agora pertence a `search_row` ao lado de `Salvar Filtro`.
  2. linha de paginacao mantida para paginator + `Colunas Visiveis` + `Setor Executor`.
- Observacao global:
  1. `BLE001` em escopo repo completo continua alto (`860` ocorrencias), nao tratado neste slice de layout.
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
