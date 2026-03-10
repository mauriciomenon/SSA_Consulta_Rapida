# Next Chat Migration Guide

Use este arquivo para migrar contexto para um novo chat sem perder qualidade de execucao.

## CURRENT TRUTH 2026-03-09 23:24 - start from here

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
