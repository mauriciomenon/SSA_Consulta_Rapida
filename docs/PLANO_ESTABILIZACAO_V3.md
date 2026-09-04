# PLANO MESTRE DE ESTABILIZACAO - SSA_Consulta_Rapida (v3.1)

Data: 2026-09-03 (v3.1 incorpora o parecer codex "APROVAR COM CORRECOES VINCULANTES", triado item a item na Parte G). Branch `dev`, HEAD `04ed2b44` (4 commits locais: `76d1f131` marker, `64442bf2`+`04ed2b44` S1, `f49e3488` S2-parcial). NADA publicado; remotos GitHub/schottge/GitLab em `c1770108`.

Estrutura: Parte A = meu plano original do ciclo (executado). Partes B-F = levantamento, triagem codex, slices, testes, controle. Parte G = parecer externo 2026-09-03 com validade verificada e correcoes incorporadas. Este e o unico plano valido.

---

# PARTE A - MEU PLANO ORIGINAL DO CICLO (fechado)

A.1 Objetivo: filtro "Setor Executor" nao repintava a tabela (contador/paginator atualizavam, tabela stale). Meta: estabilidade maxima antes do main.

A.2 Diagnostico provado: marker de render vazio (`fillna("")` sobre `Int64` com NA -> TypeError engolido em DEBUG, `gui_table.py:382`) + `_data_revision` congelada desde `b97cc46e` -> colisao da chave do cache formatado (`gui_table.py:615-624`) e da assinatura de render (`gui_table.py:409-419`) entre paginas de mesmo tamanho. Probe: cache devolveu pagina antiga (in 202609684 -> out 202609694).

A.3 Segunda opiniao: codex GPT-5.6-sol read-only confirmou por rota independente; grok bloqueado por quota (declarado).

A.4 Fix: `.astype("string")` + warning; commit `76d1f131`; testes `tests/test_gui_table_marker_sample.py` (vermelho provado 3/4 no codigo velho).

A.5 Validacao: py_compile/ruff/ty; 4/4 novos, 27/27 render, 21/21 executor; repro offscreen FAIL->PASS; semgrep 0; review codex APROVADO; smoke GUI real com screenshot (`svp` repinta; `IEE3` painel -> "50 de 96028" tudo IEE3; remocao repinta). Residuo: item de popup Qt nao automatizavel por AX.

A.6 Adicoes da execucao: laudo 318 excepts (B.1); REL-01 filelock (S1); CI/CD SSH verificado (3 remotos em `c1770108`; `gh`/token GitLab ausentes = status pendente declarado).

---

# PARTE B - MEU LEVANTAMENTO NOVO

## B.1 Laudo de excepts silenciosos (fluxo busca/filtros/render)

Total: 318 sitios. Contagem EXATA de mudos: 15 (lista fechada na tabela R1; os demais tem ao menos logger.debug).

| Arquivo | R1 | R2 | R3 | R4 | Total |
|---|---|---|---|---|---|
| gui/mixins/filter_gui_ssa_mixin.py | 3 | 20 | 54 | 12 | 89 |
| gui/ssa/gui_table.py | 3 | 6 | 61 | 2 | 72 |
| gui/ssa/gui_filters_advanced_logic.py | 18 | 0 | 2 | 1 | 21 |
| gui/ssa/gui_filters_advanced_ui.py | 1 | 8 | 29 | 9 | 47 |
| gui/ssa/gui_workers.py | 1 | 6 | 13 | 27 | 47 |
| gui/ssa/main_window_filter_bar.py | 0 | 0 | 23 | 0 | 23 |
| gui/ssa/filter_search_undo_controller.py | 0 | 2 | 5 | 1 | 8 |
| gui/ssa/filter_worker_lifecycle.py | 0 | 2 | 0 | 5 | 7 |
| gui/workers/filter_worker.py | 0 | 2 | 0 | 0 | 2 |
| gui/ssa/filter_cache_context.py | 0 | 1 | 0 | 0 | 1 |
| gui/ssa/filter_domain_rules.py | 1 | 0 | 0 | 0 | 1 |
| gui/ssa/gui_filters_advanced_state_reader.py | 0 | 0 | 0 | 0 | 0 |

Politica (por EFEITO, nao mecanica):
- Mascara incorreta (filtro vira sem restricao): fail-closed via AdvancedFilterMaskError (S2).
- Cache/assinatura colidivel: degradacao INVALIDA a chave (nunca colide) (S8/S12).
- Teardown com fallback comprovadamente seguro: manter debug.
- Falha cosmetica (largura/label/tooltip): manter debug; mudo ganha log de 1 linha.
- BLE001 ratchet SOMENTE nas linhas alteradas por um slice; nunca zerar o diretorio; NAO tocar R2/R3 incidentalmente por o arquivo ter sido editado.

Registro auditavel dos 27 R1: tabela com ID (R1-01..R1-27), funcao, arquivo:linha, efeito, degradacao atual, politica, slice destino, teste. A tabela completa fica no slice S12 (quando executado); os 18 do advanced_logic foram tratados no S2-parcial (ver G/PARTE D S2).

## B.2 Fence S0 (feito)
Baseline; REL-01 confirmado; GUI-07 confirmado (amostra 3 linhas >100 vs page_size 500 -> ver S8 OBRIGATORIO); duas ocorrencias `${var,,}` (`native_host_guard.sh:54,101`).

---

# PARTE C - MATERIAL DO CODEX TRIADO

## C.1 Confirmados por leitura propria
- IMP-06 `except Exception: return True` duplo (`database_upsert_logic.py:509-512`).
- GUI-02 refresh cache deep copy sem lifecycle (`filter_refresh_pipeline.py:14,115-118`).
- GUI-07 amostra 3 linhas >100 (`gui_table.py:378-381`) com page_size 500 (`data_paginator.py:9`).
- GUI-08 chave do worker com pos-filtros (`filter_cache_context.py`).

## C.1-bis IMP REPRODUZIDOS EM RUNTIME (2026-09-04; scripts /tmp/repro_imp01.py, imp02, imp05, imp07; workspaces /tmp; repo intacto)
- IMP-01 REPRODUZIDO: full rescan com 1 arquivo ok + 1 erro NAO-deterministico ("unexpected", `app_logic.py:994`) promove o candidato (`:1521` gate = `successfully_processed_files` nao vazio; `_has_only_deterministic_rejections` so aplica quando NADA teve sucesso); SSA antes importada pelo arquivo falho SUMIU do primario ativo; `result=True/status=updated`. Perda de dados real.
- IMP-02 REPRODUZIDO (simulacao deterministica na janela): escrita concorrente de diff commitada no primary imediatamente antes da promocao e rotacionada ao backup (`import_database_rotation.py:38-70`); ativo final sem a linha do diff; linha preservada so no backup. Sem re-base do delta.
- IMP-04 REPRODUZIDO (duas direcoes): `run_importer_logic` devolve True para `deterministic_rejections_only` (sem update; docstring diz True=atualizado) E devolveu False numa rodada diff que MUDOU o banco (evidencia colhida no repro do IMP-07). Dez pontos de return mapeados na conversa.
- IMP-05 REPRODUZIDO: mesmo lote (mesma SSA, mesma data, STE depois ADM): canonical mantem STE; optimized mantem ADM (`database_optimized.py:63-101` keep-last pre-upsert vs `database_upsert_logic.py:1110-1160` reducer sequencial). DBs divergem por caminho.
- IMP-07 REPRODUZIDO: modo diff importou arquivo existente SOMENTE em `processadas/` (`app_logic.py:747-756` le flags `*_in_full_rescan` sem depender de force_import; `utils/caching.py:319-348` varre processadas; defaults True em `config_defaults.py:95/97`).

## C.2 Alegados - repro obrigatoria antes do patch
IMP-03 (schema parcial; repro no slice S5a), GUI-01/03/04/05/06/09/10 (estado/callbacks), MEM-01..04, REL-03/04/05, QA-01..04.

## C.3 Recusas/ajustes
Documento paralelo como plano (contratos entram nos slices); S8 condicionado (CORRIGIDO: agora obrigatorio, ver D); teto arbitrario de colunas (recusado); ruff massivo (recusado).

---

# PARTE D - SLICES (ordem corrigida por dependencia; nenhum inicia sem o anterior fechado)

Processo fixo: (1) levantamento/repro sem editar; (2) AVISO FORMAL com evidencias + diff previsto + testes + rollback; (3) aprovacao em texto; (4) patch cirurgico; (5) gates py_compile/ruff/ty/pytest focado/semgrep; (6) commit atomico. Gate de validacao FALHOU = parar, preservar diff, diagnosticar (nunca reverter sozinho). Revert somente com `reverter <slice>` explicito.

## S1 - HOTFIX filelock [FECHADO: 64442bf2 + 04ed2b44]
- `filelock>=3.20.3` em requirements.txt + 4 manifests; gate `tests/test_runtime_manifest_parity.py` (semantica COVERAGE por nome + assert explicito de piso `filelock>=3.20.3` em cada manifest); `pyoxidizer.bzl:50` pip_install recebe filelock.
- Verificado: scripts de env (`setup_env.sh/ps1`) e `build_multiplatform.py` instalam A PARTIR dos manifests (ja cobertos); nao existem "dois scripts Debian" com lista propria (ver G, item parcialmente invalido).
- Commit exclui o plano (doc fica untracked ate decisao DOC_SYNC).

## S2 - FAIL-CLOSED AVANCADO [BASE MANTIDA f49e3488; complementacao bloqueada ate aprovacao do contrato]
Estado: commit `f49e3488` (fail-closed das excessoes, 14 pontos, testes verdes) MANTIDO por decisao do usuario. A complementacao abaixo entra como commit SEGUINTE, apos aprovacao deste contrato.

DIFF PREVISTO DA COMPLEMENTACAO (levantamento fechado, aguardando aprovacao):
- Gap central: `_refresh_after_advanced_filters_apply` (ui:1571-1590) retorna so `notice`; falha do refresh nao e sinalizada ao caller (`_apply_advanced_filters_from_ui`), que ja gravou UI nova -> dessincronizacao.
- (a) `_refresh_after_advanced_filters_apply` passa a retornar `tuple[str | None, bool]` (notice, ok); callers no mesmo arquivo atualizados (2 call sites).
- (b) `_apply_advanced_filters_from_ui`: snapshot ANTES das mutacoes (`previous_filters` ja existe; acrescentar copia de `_advanced_filters`, `_advanced_filters_active`, `_active_column_filters`, flag `_filter_cache_context_dirty`); com ok=False restaura tudo, marca cache dirty, re-synca UI do estado restaurado (combo executor, botoes situacao, resumo, botao clear); df e Undo permanecem os anteriores (handler do mixin ja preserva).
- (c) `gui_filters_advanced_logic.py`: raise quando criterio ATIVO e coluna ausente (339 reprogramacoes; 419/443 anos sem data_cadastro nem semana_cadastro; 719 derivada sem numero_ssa); `derivada_all_ste` sem situacao falha fechada (721); `mask.all()` (822) via `_mask_any`.
- (d) Testes: transacional (falha injetada -> UI restaurada identica); criterio ativo + coluna ausente -> raise; criterio inativo + coluna ausente -> aplica normal; happy path inalterado.
1. Restantes no-ops por coluna ausente COM criterio ativo: reprogramacoes (`gui_filters_advanced_logic.py:339`), ano emissao (419/443 quando nem data_cadastro nem semana_cadastro), derivada (719 sem numero_ssa). Ausencia de coluna so falha quando o criterio correspondente estiver ATIVO; dataset parcial sem o criterio continua valido.
2. `derivada_all_ste` sem coluna situacao (721) nao pode degradar para "tem derivada": falha fechada com causa.
3. `mask.all()` (822) avaliado via contrato `_mask_any` (AdvancedFilterMaskError), nao excecao generica.
4. CONTRATO TRANSACIONAL (o ponto central): `_apply_advanced_filters_from_ui` (`gui_filters_advanced_ui.py:1625-1665`) grava `_advanced_filters`, flags, syncs de executor/situacao/botoes ANTES do refresh; em AdvancedFilterMaskError o handler preserva o DataFrame mas a UI fica nova com tabela velha. Correcao: snapshot do estado (filtros avancados, flag ativa, `_active_column_filters`, fingerprint/cache `_filter_cache_context_*`, resumo, chips, botoes) ANTES da gravacao; em falha, restauracao atomica de TUDO; Undo e tabela anterior intactos; warning + status visivel.
5. Testes: contrato transacional (falha injetada -> UI restaurada identica), criterio ativo com coluna ausente -> falha fechada, criterio inativo com coluna ausente -> valida normalmente, casos 1-3 acima.

## S3 - PUBLICACAO (protocolo novo)
`commitar` NAO autoriza push. Publicacao so com comando separado e explicito (`publicar dev nos 3 destinos`); apos push, verificar CADA destino com `git ls-remote` (origin tem 3 push URLs: GitHub, schottge, GitLab) e reportar SHA de cada; publicacao parcial = reportar, sem rollback automatico.

## Ordem corrigida por dependencia (alteracoes do parecer)
1. S4a-S4e IMPORT (abaixo) - pre-requisito: higiene de testes (S11a) ANTES.
2. S5 DB.
3. S6/S7 GUI.
4. S8 DIGEST OBRIGATORIO (ver abaixo).
5. S9 memoria - pre-requisito: coletor RSS (S11b) ANTES do profiling.
6. S10 build - pre-requisito: Bash 3.2 (S11c) ANTES; cadeia locked (abaixo).
7. S12 divida - INTEGRIDADE DO BANCO movida para ANTES do S4a (o outcome depende do relatorio de integridade estruturado).

## S4 - IMPORT (dividido em commits atomicos)
- S4a outcome: `core/import_outcome.py` com tipos EXATOS (paths como `str`, contadores `int`, `integrity_report: Mapping[str, object]` com schema fechado; `ImportStatus` e `ImportOutcome` conforme v2).
- S4b promotion gate: whitelist deterministica fechada (`extraction` + `MISSING_REQUIRED_COLUMNS`/`ALL_ROWS_REJECTED`); decisao pura antes de cache/move/backup/promocao; matriz de cenarios (sucesso / +det / somente-det / bloqueante / cancelamento / integridade invalida / falha de promocao).
- S4c lock/concorrencia: lock do primary antes de discovery ate pos move/cache; timeout -> BUSY sem side effect; full vs diff nunca sobrepoem (repro IMP-02).
- S4d consumers: main.py, CLI, launcher, worker GUI, Streamlit -> `status` + `primary_database_changed`; exit 0 so nao-bloqueante; reload so por primary_database_changed.
- S4e IMP-07: escopo de `*_in_full_rescan` isolado do modo diff.
- CONTRATO POS-PROMOCAO: falha de move/cache APOS promocao -> `UPDATED_PARTIAL`, `primary_database_changed=True`, reload obrigatorio, sem fingir rollback do DB. Falha somente do report -> outcome funcional preservado, `report_path=None`, warning.
- IMP-05 pertence ao S5 (nao ao pre-requisito do S4).
- Pre-requisitos: repro IMP-01/02/04; integridade estruturada (S12-integridade) concluida.

## S5 - DB (dividido)
- S5a transacao: DDL dinamico + parent SSA + events na mesma transacao/savepoint; falha pos ALTER deixa schema e linhas identicos ao pre-estado.
- S5b comparador: `_should_update_existing` fail-closed (so TypeError/ValueError/OverflowError no parse; inesperado propaga e causa rollback) [IMP-06].
- S5c paridade/performance: reducer canonical apenas para duplicados iniciado pela linha existente; fast path SSA unica; budget 1,10x baseline optimized / 0,50x canonical [IMP-05 aqui].
- Pre-requisito: repro IMP-03 (S5a) e IMP-05 (S5c).

## S6 - GUI requests/callbacks/undo [repros GUI-01/03/04/05 antes]
Contrato draft/pending/applied sobre campos atuais; callback stale sem efeito; `on_data_loaded/on_load_error -> bool accepted`; busca vazia por identidade; hard reset completo; harness espera workers aposentados. Testes designados: T-GUI-01..06 E T-GUI-09 E T-GUI-12.

## S7 - GUI owner unico executor/situacao [repros GUI-04/06 antes]
Quick/header/coluna/advanced editam o mesmo valor em `_active_column_filters`; gramatica `!valor`; ultima edicao vence; um conceito, uma mascara. T-GUI-07/08.

## S8 - DIGEST INTEGRAL DE PAGINA [OBRIGATORIO - condicao ja satisfeita]
Justificativa obrigatoria: `data_paginator.py:9` suporta page_size=500 enquanto o marker amostra 3 linhas acima de 100 (`gui_table.py:378-381`) - risco real de colisao stale pelo contrato do produto.
- `_build_page_content_digest(display_df) -> bytes | None`: ordem, indice, colunas, dtypes, todas as celulas (hash_pandas_object + BLAKE2b 128).
- Budget: mediana <=10 ms / p95 <=15 ms em 500x84. SE EXCEDER: desabilitar cache/reuse para paginas acima de 100 linhas; PROIBIDO manter chave amostral colidivel. `None` desabilita cache na rodada e forca rebuild.
- T-GUI-10/11.

## S9 - MEMORIA (commits por grupo de owner + gate agregado final)
- Grupos: (1) normalized search + FilterCache; (2) refresh last-result + paginas formatadas; (3) ColumnFilterCaches + advanced; (4) responsavel + sort + CacheManager.dataframes. Cada grupo = commit proprio com budget (tabela v2: 64/16-16/8/8/16/8/8/8 MiB) e regras (medir deep antes de reter; desconhecido = skip; atribuir inclusive None no refresh; load/revisao/clear/hard reset limpam dependentes; busca vazia nunca em cache; chave do worker sem pos-filtros; exportar bytes/hits/misses/evictions).
- Gate RSS AGREGADO apos todos os grupos (aceites da Parte E). Pre-requisito: coletor RSS corrente (S11b).

## S10 - BUILD UV LOCKED [executavel, corrigido]
```text
uv lock --check
uv export --locked --format requirements.txt --no-dev --extra build \
  --no-emit-project --no-header --no-annotate \
  --output-file <export-temporario>
uv pip sync --python <python-da-venv> --require-hashes --strict \
  <export-temporario>
uv pip check --python <python-da-venv>
```
- Eliminar bypasses `--frozen` existentes em Nuitka, PyOxidizer, build multiplataforma e CI.
- Nova venv preparada e validada SEPARADAMENTE antes de substituir a anterior; assinatura JSON (SHA256 pyproject/uv.lock/export + args + uv + platform + Python tags); manifests corrigidos ficam 1 release como fallback manual.
- Pre-requisito: Bash 3.2 corrigido (S11c). Plataformas: macOS arm64, Windows amd64, Debian amd64/arm64.

## S11 - PORTABILIDADE/HIGIENE (dividido)
- S11a higiene de testes: FECHADO 2026-09-03 com correcao de levantamento. Confirmados e CORRIGIDOS (2):
  1. `tests/test_performance_import.py` — escrevia `reports/perf_last_import.json` + `perf_history.jsonl` no repo. Corrigido em `585d881c` (tmp_path com override `SSA_PERF_REPORTS_DIR`).
  2. `scripts/ci_quality_gates.sh` + `tests/test_shell_ci_contracts.py` — jsonl incondicional no CWD (raiz). Corrigido em `da41080c` (`QUALITY_GATES_JSONL` configuravel; teste aponta tmp; shellcheck ok). Artefato stale da raiz (16/jul) removido.
  O alegado "3o poluente (DB)" NAO se confirmou na investigacao dedicada: `test_cli_loop_missing_numero_ssa_guard` nao abre o DB real (`_get_initial_state` mockado — path inerte); nenhum outro teste abre DB fora de tmp. Resultado: 2 reais + 1 falso positivo do levantamento.
  EVIDENCIA EXTRA: as 5 falhas pre-existentes de `test_shell_ci_contracts` sao o REL-02 ao vivo (`native_host_guard.sh:54 ${os_release,,}` no Bash 3.2) — reforca S11c ANTES de S10.
- S11b coletor RSS corrente por plataforma (WorkingSetSize/statm/libproc; pico so diagnostico). ANTES do S9.
- S11c Bash 3.2: DUAS ocorrencias `${var,,}` (`native_host_guard.sh:54,101`) -> `LC_ALL=C tr`; teste EXECUTA em 3.2 e atual. ANTES do S10.

## S12 - DIVIDA (dividido)
- S12-integridade: operacao unica `{ok, report}` com wrapper booleano legado; MOVIDA para antes do S4a.
- S12-assinaturas: quarteto (`gui_table.py:950`, `mixin:2515`, `gui_workers.py:1083`, `filter_domain_rules.py:365`) + `advanced_ui:1689` com regra "degradacao nunca colide".
- S12-tipos: erros ty conhecidos (`DetailsSeriesIndex.get`; `msvcrt` via cast).
- S12-logging: R2/R3 do laudo conforme politica por efeito (B.1); registro auditavel dos 27 R1.
- S12-backlog: RECOVERY_BACKLOG (extrator XLSX, complexidade, dead code).

---

# PARTE E - CATALOGO DE TESTES NUMERADOS

Importacao/banco: T-IMP-01..07 e T-DB-01..05 (v2, mantidos; T-DB-03 inclui IMP-05 em S5c). GUI: T-GUI-01..12 (T-GUI-09 e T-GUI-12 designados ao S6). S2: T-S2-01..03 (existentes) + novos do contrato transacional (S2 item 4-5). Memoria: 8 variantes x 5 processos; aceites numerados (RSS pos-GC <= +96 MiB; pico <= +160; zero crescimento monotono em 20 ciclos; busca fria <=1,25x; quick/advanced/undo <=1,10x; digest 500x84 <=10/15 ms; acima do limite nunca retido; funcional identico com caches on/off). Release/qualidade: cadeia locked + `uv pip check`; Bash 3.2 executa; py_compile/ruff/ty/pytest/ShellCheck/PSScriptAnalyzer; semgrep/bandit/vulture/pip-audit/detect-secrets/gitleaks/trufflehog; snyk/safety so com auth; smoke nativo 4 alvos; evidencia visual com screenshot por slice GUI.

---

# PARTE F - CONTROLE, ROLLBACK, PUBLICACAO, PLACAR

- Slice = unidade atomica; commits separados por concern (S1/S2 ja sao); diff previsto antes de editar; commit so com autorizacao.
- Gate falhou = parar, preservar diff, diagnosticar. Revert SOMENTE com `reverter <slice>` explicito. Proibido `reset --hard`.
- `commitar` cria commits; NAO empurra. Publicacao: comando separado explicito (`publicar dev nos 3 destinos`) + `git ls-remote` por destino + report de SHA; sem rollback automatico em publicacao parcial.
- Sem branch/worktree/PR/push/merge sem comando explicito. Nenhum teste escreve no DB real. Candidates/backups nao apagados automaticamente.
- Fora do ciclo: Windows arm64, Artix/Arch, profiles, SAM automatico, roadmap 4.9.x/5.0.
- Veredito 007 vigente: BLOQUEADO PARCIAL para main enquanto S2 (contrato transacional), promotion gate (S4b) e cadeia locked (S10) estiverem incompletos.

PLACAR (v3.1, atualizado 2026-09-04):
- COMMITS LOCAIS (12, sem push): `76d1f131` marker; `64442bf2`+`04ed2b44` S1 filelock; `f49e3488` S2-parcial; `6225d37e` S2 complemento transacional; `585d881c`+`da41080c` S11a; `d295d198` DOC_SYNC plano; `bab88e37` GATE lefthook pre-commit (ruff+py_compile nos staged; nunca mais commit com gate vermelho); `918dbb2f` S11c Bash 3.2 (tr nas 2 ocorrencias; contratos shell 42/42, as 5 falhas pre-existentes resolvidas); `d3587960` S11b RSS corrente (WorkingSetSize/statm/ps; pico vira diagnostico; ambos os gates de performance verdes).
- FECHADO: REN-01; S1; S2 COMPLETO; laudo 318; S0; S11a; S11b; S11c; gate de commit permanente; CI/CD SSH; verificacao GUI real em tela.
- S12-INTEGRIDADE FECHADO 2026-09-04 em 3 commits: `c640e8a9` (ensure_database_integrity -> (ok, report); wrapper bool; re-verify so quando o DB muda), `7b3c2bd6` (facade + full rescan usa ensure UMA vez, sem o verify duplicado de app_logic:1343/1349), `5a30e8de` (testes de contrato).
- REPROS IMP FECHADOS 2026-09-04 (C.1-bis): IMP-01/02/04/05/07 REPRODUZIDOS em runtime; IMP-03 adiado ao S5a.
- S4a FECHADO `ef5c0310`: core/import_outcome.py (ImportStatus 14 estados com normalizacao; ImportOutcome frozen; primary_database_changed so em updated/updated_partial/derivadas_materialized; get_last_import_outcome thread-safe); _finalize_and_return grava o outcome em TODOS os finais com bool inalterado.
- S4b FECHADO `2079bb17`+`f022f0ee`: `_has_blocking_candidate_errors` (conjunto deterministico identico ao existente) + gate antes das duas promocoes -> `candidate_incomplete` com primary intacto, candidato preservado, zero cache/move/backup; matriz 4/4; repro IMP-01 agora NOT REPRODUCED. NOTA semgrep: binario saiu de `uv run` (usar `uv tool run semgrep`); S4a re-coberto, 0 findings em S4a+S4b.
- S4c FECHADO `b97dea4a`: round lock `database_writer_lock(primary)` envolve a rodada inteira (pos-contexto read-only ate pos move/cache); `Timeout` -> `result=False/status=import_busy` sem candidato/escrita/cache; reentrada in-process pelo singleton do filelock; `git diff -w` = +20 linhas (imports + wrapper; corpo so reindentado). Testes: BUSY sem efeitos colaterais (bytes do primary inalterados), lock liberado apos rodada, rodada pos-liberacao atualiza. 125 suites + 3 novos verdes; semgrep 0.
- PROXIMO: S4d consumers (migrar main/cli/launcher/worker/streamlit para `get_last_import_outcome` com exit codes por status; fecha IMP-04); depois S4e IMP-07, S5, S6-S9, S10.
- VERIFICACAO GUI REAL 2026-09-03 22:3x (app com os 4 commits, banco 99.152 SSAs): busca svp repinta (row1 202612584); paginacao pagina 2 renderiza pagina de mesmo tamanho com conteudo novo; situacao STE aplica (2-31 resultados, tudo STE) e remocao pelo chip de resumo com dialog de confirmacao restaura; week-range Emissao >=202636 aplica (`2 de 99152`, chip `Sem Emis`, linhas 202636) e limpeza restaura 1507; log da sessao SEM warnings de fail-closed (as 4 ocorrencias existentes sao de 12:53, codigo pre-S2, guard `_mask_any` legacy ja tratado com warning + df preservado). LIMITACAO helper: selecao de item em popup de QComboBox (chip superior e multiselecao do painel) nao automatizavel por AXPress/teclado (bundle_id nulo); cliques nativos roteiam para overlay do ZCode. Caminhos cobertos por 21+164 testes de executor/avancados.
- S2-PARCIAL MANTIDO (decisao do usuario 2026-09-03): commit `f49e3488` (fail-closed das excessoes + testes) permanece como BASE; a complementacao transacional (itens 1-5) entra como commit seguinte apos aprovacao do contrato; NAO reverter.
- AGUARDA: decisao DOC_SYNC deste plano; `publicar` quando ordenado; S11a antes de S4a.
- BLOQUEIOS: grok/clawpatch quota; gh/token GitLab; codex-review externo falhou (state_5.sqlite read-only) - declarado, nao repetido cegamente.

---

# PARTE G - PARECER EXTERNO 2026-09-03: TRIAGEM DE VALIDADE (verificada contra o repo)

| Item do parecer | Validade verificada | Disposicao |
|---|---|---|
| S1: ruff falhou (os/sys nao usados) | INVALIDO PARA O HEAD - corrigi ANTES do commit `64442bf2` (verificado em `git show`) | nada a fazer |
| S1: teste e coverage por nome (aceita filelock==0) | VALIDO | corrigido em `04ed2b44` (assert de piso) |
| S1: filelock ausente no pyoxidizer.bzl | VALIDO (`pip_install` linha 50) | corrigido em `04ed2b44` |
| S1: "dois scripts Debian" sem filelock | PARCIALMENTE INVALIDO - scripts de env e builder instalam a partir dos manifests (ja cobertos); nao existe lista propria em scripts Debian | verificado e registrado |
| S1: commit deve excluir o plano | VALIDO (ja ocorre; doc untracked) | mantido |
| S2: no-ops restantes (reprogramacoes:339, anos:419/443, derivada:719) | VALIDO | contrato S2 item 1 |
| S2: derivada_all_ste sem situacao degrada p/ "tem derivada" (:721) | VALIDO | contrato S2 item 2 |
| S2: mask.all() escapa generico (:822) | VALIDO | contrato S2 item 3 |
| S2: UI grava estado antes do refresh (ui:1625-1665) | VALIDO - dessincronizacao visual em falha | contrato S2 item 4 (transacional) |
| Laudo nao auditavel; ~15 -> exato; classificacao por efeito; ratchet so em linhas alteradas; nao tocar R2/R3 incidentalmente | VALIDO | B.1 + S12-logging |
| S4/S5/S9/S11/S12 nao atomicos | VALIDO | divididos em D |
| Outcome pos-promocao sem contrato; IMP-05 no lugar errado | VALIDO | S4 contrato pos-promocao; IMP-05 -> S5c |
| S8 deve ser obrigatorio (page_size 500 vs 3 linhas) | VALIDO - condicao ja satisfeita pelo produto | S8 OBRIGATORIO em D |
| Ordem: higiene antes S4; RSS antes S9; Bash antes S10; 2 ocorrencias var,,; 3o teste poluente a identificar; T-GUI-09/12 ao S6 | VALIDO (2 ocorrencias confirmadas em 54/101) | ordem corrigida em D |
| S10 nao executavel como escrito + bypasses --frozen | VALIDO | bloco executavel + eliminacao de bypasses em D |
| Rollback/publicacao (gate falhou=parar; revert explicito; commitar != push; ls-remote por destino) | VALIDO | Parte F + memoria |
| Codex-review externo falhou (sqlite read-only) | Registrado como bloqueio declarado | Parte F |
