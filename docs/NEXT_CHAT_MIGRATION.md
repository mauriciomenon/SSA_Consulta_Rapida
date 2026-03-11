# Next Chat Migration Guide

Use este arquivo para migrar contexto para um novo chat sem perder qualidade de execucao.

## CURRENT TRUTH 2026-03-10 23:03 - start from here

- Objetivo desta rodada:
  1. fechar DOC_SYNC final com decisao intencional ja aprovada e preparar texto de transicao.
- Correcoes aplicadas:
  1. docs de controle sincronizados com snapshot final desta sessao.
  2. decisao `DECISAO_INTENCIONAL` mantida: `scripts/git_hooks/pre-push` segue sem `--not --remotes`.
- Estado local confirmado:
  1. branch: `codex/sprint-importacao-grave-fixes-20260305`.
  2. ultimo commit: `fa9d6f0d DOC_SYNC: register intentional pre-push gate policy`.
  3. residuos fora de escopo mantidos:
     - `M data/ssas.db`
     - `?? config/settings.json.bak_20260308_212715`
  4. stashes abertos:
     - `stash@{0}` `wip-before-return-import-branch-20260308_011343`
     - `stash@{1}` `incident-freeze-before-reapply-20260305-083301`
     - `stash@{2}` `local-wip-config-db-before-dev-switch-20260303`
- Proximo passo recomendado:
  1. iniciar novo chat lendo os 5 blocos de topo (AGENTS + 4 docs de controle/politica).
  2. manter foco em estabilidade com slices minimos e commit atomico por risco real.

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
