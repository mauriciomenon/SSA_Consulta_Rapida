# Next Chat Migration Guide

Use este arquivo para migrar contexto para um novo chat sem perder qualidade de execucao.

## CURRENT TRUTH 2026-03-10 08:04 - start from here

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
