# Review de seguranca, logica, sincronismo e estado — v4.50..dev

- Data: 2026-09-18
- Escopo: `git diff v4.50...dev` (178 arquivos, ~20k insercoes, inclui PR #132)
- Ferramenta: `bitoreview review --prompt-only --base v4.50` (34 chunks, modo padrao)
- Natureza: somente leitura; nenhum arquivo de codigo alterado
- Ressalva: a ferramenta emitiu aviso de resposta truncada em um chunk; alguns
  achados podem ter ficado de fora. Os 155 reportados foram analisados.

## Metricas

| Severidade | Quantidade |
|---|---|
| Alta | 7 |
| Media | 54 |
| Baixa | 94 |

## Achados altos — validacao contra o codigo

### Confirmados / relevantes

1. `interface/cli.py` — possivel exposicao de caminhos em mensagens de erro.
   Generico, sem ponto exato confirmado; recomenda-se revisar mensagens
   exibidas ao usuario para nao vazar paths de banco. Severidade real: media.
2. `gui/ssa/pai_api_controller.py:234` — `except Exception` amplo na
   inicializacao do worker. Existe e e intencional (loga erro, limpa worker
   ativo, atualiza status). Risco: mascarar erros de programacao. Sugestao
   aceitavel: capturar tipos especificos conhecidos e logar traceback.
3. `gui/ssa/pai_api_controller.py:365` — `_window_is_deleted` retorna False se
   `PyQt6.sip` nao importar. Em configuracao sem sip, a guarda nao detecta
   janela destruida. Caso de borda; hoje a segunda condicao
   (`active_pai_api_worker() is not worker`) ainda protege a maioria dos
   caminhos. Severidade real: media/baixa.
4. `gui/ssa/pai_api_controller.py:299` — mudanca de assinatura dos handlers de
   sinal (parametro `worker` via `partial`). Verificado: todos os handlers
   internos (`_set_worker_progress`, `_set_worker_preview_status`,
   `_confirm_worker_import`) ja usam a nova assinatura e aceitam `*_args`.
   Risco residual apenas se codigo externo conectar esses sinais diretamente.
5. `gui/workers/data_loader_worker.py:290` — `except Exception` amplo no
   worker. Deliberado para nao derrubar a thread; emite erro generico.
   Melhoria util: logar traceback completo antes de emitir mensagem.

### Falsos positivos confirmados

- `tests/test_list_exporter.py:77` (2 ocorrencias "security"): sao testes que
  VERIFICAM a correcao de injecao de formula em TSV — a correcao ja esta
  presente, nao ha vulnerabilidade aberta.
- `tests/test_path_safety.py:158/162` (mencionado nas recomendacoes):
  alegado erro de sintaxe nao existe; `py_compile` passa no arquivo.
- `interface/cli.py:1235` e `:1519` ("usar `>` em vez de `>=` no limite do
  cache"): o `>=` esta correto — despeja a entrada mais antiga ANTES de
  inserir quando a capacidade e atingida. Com `>` o cache passaria do limite.

## Temas medios relevantes (sincronismo/estado/logica)

- `gui/ssa/persistent_filter_ui.py:60-90` — copia profunda do estado de
  filtros e restauracao em `finally` podem mascarar excecao do bloco `try` e
  restaurar estado incorreto. Padrao repetido em 3 achados; vale revisao.
- `gui/workers/rescan_worker.py:367,564` — `force_import` fixado em `False`
  no modo batched; mudanca comportamental potencial nao documentada.
- `gui/ssa/pai_api_controller.py:349` — checagem de identidade do worker em
  callback pode ter janela de corrida se worker for trocado entre o agendamento
  e a execucao do slot (parcialmente mitigado pelas guards atuais).
- `interface/streamlit_launcher.py:68,154` — estado global modificado em
  signal handler; correto exigir main thread, vale documentar comportamento.
- `core/import_database_rotation.py:52,62,154` — tres achados de TOCTOU em
  checagens de identidade/symlink de arquivo (st_ino, marker exclusivo,
  sidecar). Reais como endurecimento; explorabilidade baixa em uso local.
- `tests/` — varios achados de mocks desatualizados (`database_operation_in_progress`
  ausente em `_Window` de teste), risco de drift mock vs implementacao.

## Recomendacoes priorizadas

1. Logar traceback completo nos `except Exception` de workers
   (`data_loader_worker.py:290`, `pai_api_controller.py:234`).
2. Revisar bloco `try/finally` de restauracao de estado em
   `persistent_filter_ui.py` para nao engolir excecao do `try`.
3. Documentar/decidir o comportamento de `force_import=False` em modo batched
   (`rescan_worker.py`).
4. Alinhar mocks de teste com `database_operation_in_progress` para evitar
   drift mock/implementacao.
5. Opcional: endurecer checagens TOCTOU em `import_database_rotation.py` com
   operacoes baseadas em file descriptor.

## Validacao aprofundada (segunda passada, leitura do codigo)

Cada achado relevante foi conferido no arquivo atual. Conclusao: a maioria dos
pontos "reais" da primeira passada e falso positivo ou desenho deliberado ja
documentado no proprio codigo.

### Falsos positivos adicionais confirmados

- `rescan_worker.py:567` (`force_import = False` em modo batched): deliberado e
  comentado no codigo — candidato de full-rescan montado so com arquivos do
  batch seria promovido sobre o primario e perderia linhas. O valor original e
  restaurado em `finally` (linha 605). Correto.
- `data_loader_worker.py` catch-all: ja usa `logger.exception` (traceback
  completo) e tem comentario explicando por que existe — sem ele, `finished`
  dispararia e a GUI reportaria sucesso sobre dados antigos. A sugestao do
  reviewer ("logar traceback") ja esta implementada. As linhas citadas (290)
  nem existem — o arquivo termina em 275; o review leu offsets do diff.
- `tests/test_pai_api_controller.py` `_Window` sem atributos de
  `database_operation_in_progress`: falso positivo — a funcao real
  (`app_menus.py:20`) usa `getattr(window, flag, False)` com default para todos
  os flags e o `_Worker` de teste implementa `isRunning()` (:129). O mock
  funciona com a funcao real por construcao.
- `pai_api_controller.py:299` mudanca de assinatura dos handlers: todas as
  conexoes vivem em `_connect_worker` (:296-314) e usam
  `partial(handler, window, worker)` de forma consistente; todos os handlers
  aceitam `*_args` e fazem a mesma guarda
  `active_pai_api_worker() is not worker`. Nao ha conexao externa quebrada.
  O padrao de rejeicao de sinal obsoleto e, na verdade, um ponto positivo de
  sincronismo.
- `streamlit_launcher.py:68` estado global em signal handler: padrao correto —
  handler de sinal so deve mutar flag/terminar filhos; o docstring documenta
  por que nao faz `wait()` (deadlock de `_waitpid_lock`). Instalacao restrita
  a thread principal (:103). Deliberado.
- `persistent_filter_ui.py:80-95` `finally` de restauracao: correto — o
  `finally` roda tanto no caminho de excecao (log + QMessageBox + return)
  quanto no normal; a restauracao e atribuicao simples de atributo e nao pode
  falhar de forma relevante. `current_state` so e usado apos sucesso do try.
- `import_database_rotation.py:53` `not identity.st_ino`: inode 0 nao e inode
  valido em filesystems reais; trocar para `== 0` seria equivalente. A sugestao
  e cosmetica.

### Residual real (baixa severidade pratica)

- TOCTOU generico em `import_database_rotation.py` (janelas entre checagem de
  symlink e uso do path): endurecimento valido, mas o codigo ja verifica
  dev+inode antes de podar artefatos e preserva em qualquer divergencia.
  Exploravel apenas com escrita no diretorio de dados do usuario.
- `pai_api_controller.py:234` `except Exception` na inicializacao do worker:
  loga `logger.error` (sem traceback completo). Melhoria pequena e segura:
  trocar para `logger.exception` ou `logger.error(..., exc_info=True)`.
- `_window_is_deleted` sem `sip`: retorna False (assume viva). Borda teorica;
  a guarda seguinte (`is not worker`) cobre o cenario principal.
- `interface/cli.py` mensagens de erro: recomendacao generica de nao vazar
  paths; nenhum ponto concreto de vazamento encontrado na leitura.

### Recomendacoes revisadas apos validacao

1. (unica de codigo, trivial) `logger.error` -> `logger.exception` em
   `pai_api_controller.py:235`.
2. Opcional, endurecimento: operacoes baseadas em FD em
   `import_database_rotation.py`.
3. Nenhuma acao necessaria nos demais pontos — desenho ja correto/documentado.

## Nao executado nesta rodada

- Nenhuma correcao aplicada (pedido explicito de somente reporte).
- Suite completa nao rodada; `py_compile` executado apenas em arquivo citado.
- Review cobre apenas o delta v4.50..dev, nao o historico completo.
- A ferramenta truncou um chunk; cobertura pode ser menor que 100%.

---

# Anexo A — Analise de divergencia `dev` vs `main` (levantamento 2026-09-19)

Analise somente-leitura sobre `origin/main` vs `origin/dev` apos
`git fetch`. Nenhum branch, merge ou PR foi criado.

## Metricas de topo

| Medida | Valor |
|---|---|
| Commits so em `dev` | 378 |
| Commits so em `main` | 2 (`e33bcc2a` merge PR #129, `2d80af2c` RECONCILIATION) |
| Merge bases | 2 — `f7304677` "Clean snapshot of main" e `ae36e281` "STABILITY_PATCH" (historico criss-cross) |
| Diff ponta-a-ponta | 528 arquivos, +46.484 / -19.848 linhas |
| Diff desde merge-base | 571 arquivos, +55.694 / -21.183 linhas |
| Arquivos novos em dev | 98 |
| Arquivos removidos | 49 (maioria: `.github` de agentes/LLM, docs internos, `CLAUDE.md`, `RTK.md`, `.rtk/`) |
| Versao `pyproject.toml` | main `4.42.0` -> dev `4.50.0` |

## Composicao da historia de dev

- 378 commits; apenas 2 merges de PR (`#131` fix/audit-surgical-fixes,
  `#132` devin_review) + 1 merge de reconciliacao (`c1770108`). O restante
  e trabalho linear direto em `dev`.
- `3318e4ce` "Clean snapshot of dev. Original commit 64752aa..." — 449
  arquivos, +34.596 linhas, pai = `f7304677` (snapshot de main): a cadeia
  reconstruida de dev foi plantada sobre a cadeia reconstruida de main.
- Reconciliacao de historico em 31/ago nos dois lados: `c1770108` em dev
  ("preserve GitLab and schottge dev histories") e `2d80af2c` em main
  ("preserve GitHub original and schottge main histories"). Os merges
  costuram a historia original longa de volta na cadeia snapshot — por
  isso `bdf379b` (main original) e `64752aa` (dev original) sao ancestrais
  de dev hoje, e por isso existem 2 merge bases (criss-cross).
- Totais: `dev` alcanca 2.713 commits; `main` alcanca 2.337 — a diferenca
  liquida sao os ~376 commits de trabalho jun->set.
- Distribuicao semanal de commits: W26:56, W27:6, W28:60, W29:14, W32:41,
  W33:26, W36:31, W37:89, W38:55 — o pico (89) e a semana da reconciliacao
  de historico e do ciclo 4.50.
- Autoria: 309 commits `mauriciomenon@users.noreply.github.com`, 67
  `mauricio.menon@gmail.com`, 2 `54405514+mauriciomenon@users.noreply.github.com`
  — 100% Mauricio Menon, dentro dos emails autorizados pelas regras.

## Comparacao entre remotos (fetch real em 2026-09-19)

Fetch executado nos 4 remotos nesta data. `origin`, `schottge` e
`gitlab` responderam ao vivo; `bitbucket` falhou por acesso SSH ("make
sure you have the correct access rights") — seus refs sao do ultimo
fetch bem-sucedido.

| Remoto | dev | main | dev_feature |
|---|---|---|---|
| `origin` (GitHub mauriciomenon) | `f5aec1e4` | `2d80af2c` | — |
| `schottge` (GitHub schottge-menon) | `f5aec1e4` | `2d80af2c` | `98ea627f` "Clean snapshot update" (15/ago) |
| `gitlab` | `f5aec1e4` | `2d80af2c` | `df3c8655` (25/ago) |
| `bitbucket` (refs antigos) | `64752aa9` (11/ago) | `bdf379b0` (28/mai) | `c2aa4f3f` (25/ago) |

- `origin` = `schottge` = `gitlab`: `git diff` entre os devs/main dos
  tres = zero — mesma arvore e mesma ponta `f5aec1e4`/`2d80af2c`.
- `bitbucket` nao recebeu a reescrita: `bitbucket/main` = `bdf379b0` e
  `bitbucket/dev` = `64752aa9` sao exatamente os commits citados como
  "Original commit" nas mensagens dos snapshots `f7304677` e `3318e4ce`.
  Bitbucket permanece como espelho da historia pre-snapshot — prova
  material da reconstrucao e fonte de recuperacao dos hashes originais.
- Branches extras por remoto: `schottge/codspeed-wizard-*` (so no
  schottge); `gitlab` e `bitbucket` tem o mesmo conjunto auxiliar
  (`chore/GHA-*`, `codex/*` x4, `dependabot/pip/*` x5,
  `mauriciomenon/dulse`); gitlab ainda tem `archive/gitlab/20260831/*`
  (snapshot de branches feito em 31/ago, dia da reconciliacao).
- `dev_feature` diverge entre os remotos (3 pontas distintas) — branch
  auxiliar, fora do escopo da promocao.
- O remote `origin` tem push multiplo configurado (GitHub mauriciomenon,
  GitHub schottge-menon, GitLab) — pushes para origin replicam para os
  tres destinos.

## Classificacao dos commits

- Prefixos internos de processo dominam: `STABILITY_PATCH`, `DOC_SYNC`,
  `HOTFIX`, `FILTER_FIX`, `RELEASE`, `RECONCILIATION`, `BUILD_FIX` —
  ~222 dos 378 commits (59%).
- Convencionais: `fix` ~90 (escopos gui:17, sqlite:3, streamlit:3,
  derivadas:3, cli:3, core:4), `docs` ~70, `test` ~80, `build`/`ci` ~20,
  `feat` poucos (ex.: normalizador SSA sem prefixo de ano fabricado).
- Arquivos com maior churn (n. de commits que os tocaram):
  `gui/gui_ssa.py` (53), `tests/test_gui_filter_logic.py` (45),
  `docs/AUDIT_FIXES_REPORT.md` (40), `core/app_logic.py` (34),
  `gui/mixins/filter_gui_ssa_mixin.py` (24), `README.md` (24),
  `docs/RECOVERY_BACKLOG.md` (18), `armazenamento/database_integrity.py`
  (16), `armazenamento/database.py` (16), `interface/cli.py` (15).
- Maiores commits individuais: `3318e4ce` snapshot dev (449 arq.),
  `d3efc8bd` limpeza de docs internos (75 arq., -9.449 linhas),
  `45212f44` isolamento de harness nativo (40 arq.), `93da0a5d`
  estabilizacao de importacao/cancelamento/caches (38 arq., +1.512).

## Areas tocadas (linhas liquidas, ponta-a-ponta)

- `tests/`: maior volume de commits; arquivos de teste 221 -> 288 (+67).
- `gui/`: 115 -> 116 arquivos; novos `gui_preferences_dialog.py` (+825),
  `database_operations.py` (+356), `rescan_worker.py` (+325),
  `gui_workers.py` (+309), `gui_filters_advanced_ui.py` (+273),
  `derivadas_sync_controller.py` (+200).
- `armazenamento/`: novo `database_lock.py`; integridade e rotacao
  reforcadas.
- `launchers/` + `dev_env/` + `scripts/env/`: nova trilha de build
  multiplataforma — `windows_arm64` nativo, `native_host_guard`,
  `build_multiplatform.py`, harness de cenarios GUI.
- `.github/workflows/`: `opencode.yml` removido; `minimal-ci`,
  `release-windows` e `secret_scan` modificados. Nova `.gitlab-ci.yml` e
  `bitbucket-pipelines.yml` e `lefthook.yml`.
- `docs/`: reorganizacao pesada — novos `BUILD_WINDOWS_ARM64_AMD64.md`,
  `RECOVERY_BACKLOG.md`, `VALIDATION_PLAN.md`, `RELEASE_NOTES_v4.47.md`,
  `RELEASE_NOTES_v4.50.md`, diagramas drawio.

## Dependencias (uv.lock)

- 68 pacotes removidos do lock (stack de dev-tools: tree-sitter* (6
  linguagens), textual, tenacity, tomlkit, typing-inspect*, smmap,
  unidiff, z3-solver, zipp etc.) — emagrecimento deliberado do ambiente.
- 1 pacote adicionado como dependencia de primeiro nivel: `numpy`.
- `pywin32` atualizado para 312; Codeflash removido.
- `uv.lock` e o arquivo com maior divergencia (+3.887/-2.183 na base) —
  principal candidato a conflito textual em merge normal.

## Releases carregadas por dev (ausentes de main)

- Linha de versao: 4.42 (main) -> 4.43 -> 4.44 -> 4.45 -> 4.45.2 -> 4.46
  -> 4.47 -> 4.50 (dev). Sete entregas de versao so em dev.
- Tags `v4.45.2` (`0048f90d`), `v4.46` (`65532a32`), `v4.50` (`d3efc8bd`)
  sao ancestrais de `origin/dev`; nenhuma e ancestral de `origin/main`.
- Apos promocao, `main` passa a conter toda a linha de release de uma vez.

## O que main tem que dev nao tem

- Nada em conteudo: `git cherry origin/dev origin/main` retorna vazio —
  os patches dos 2 commits exclusivos de main ja existem em dev.
- `e33bcc2a` (merge PR #129: build scripts + review hardening) e
  `2d80af2c` (RECONCILIATION de historico) — absorvidos por equivalencia
  de patch.

## Riscos e recomendacao de merge

- Risco de perda de conteudo: nulo (dev ⊇ main por patch).
- Risco de conflito textual em merge normal: moderado — historico
  criss-cross (2 merge bases) e 168 arquivos que main tocou desde a base;
  `uv.lock` e o maior alvo.
- Caminho recomendado (ja anotado): `git merge -s ours origin/main`
  dentro de `dev` cria ancestralidade sem trazer a arvore de main;
  depois o PR dev->main fica trivial. Alternativa: merge normal com
  resolucao "ours" nos conflitos espurios.
- Atencao pos-merge: CI de main herda workflows novos (gitlab/bitbucket
  pipelines sao inertes no GitHub); regras de protecao de main devem
  cobrir o verificador de autoria.
- Nao autorizado nesta rodada: nenhum merge, PR ou alteracao de branch.

# Anexo B — Evidencias de build dos 3 alvos (commit f5aec1e4)

Builds executados de `dev` @ `f5aec1e48c170cf56cdd6010e52178250d2da6dd`
(v4.50, merge PR #132). Todos os artefatos com SHA-256 conferido.

## windows_amd64 (VM Windows 11 ARM, Python win-amd64, .venv-win)

| Item | Evidencia |
|---|---|
| PE arch | `0x8664` (x86-64) — CLI e GUI |
| Smoke CLI | `--force-rescan` exit 0, importacao ok (status=updated, rejeicoes=0) |
| GUI | abriu (WS 229MB) e fechada limpa |
| ZIPs no Mac | `builds/packages/windows_amd64/` — combinado 103MB `135cbf9a…`, cli 37MB `975a9573…`, gui 66MB `41d05115…` |
| Report | `builds/reports/release_report_windows_amd64.json` `86fd9d6c…` |

## windows_arm64 (mesma VM, Python win-arm64 nativo, .venv-win-arm64)

| Item | Evidencia |
|---|---|
| PE arch | `0xAA64` (ARM64) — CLI e GUI |
| Smoke CLI | `--force-rescan` exit 0, importacao ok |
| GUI | abriu (WS 181MB) e fechada limpa |
| ZIPs no Mac | `builds/packages/windows_arm64/` — combinado 78MB `c5426878…`, cli 30MB `bb25de1d…`, gui 48MB `60acc845…` |
| Report | `builds/reports/release_report_windows_arm64.json` `29b3d073…` |

## macos_arm64 (build local, ambiente macOS)

| Item | Evidencia |
|---|---|
| Mach-O | CLI, GUI.app e libs internas = `Mach-O 64-bit arm64` |
| DMG | `hdiutil verify` checksum VALID, 54MB, sha256 `c2b90398…` |
| Smoke | CLI executa ate camada de banco; GUI abriu via `open` e fechada |
| Saida | `launchers/dist/macos_arm64/` + `build_manifest.json` `19a428c8…` |

## Infraestrutura de acesso a VM (registro definitivo)

- Inbound host->guest nao funciona na camada virtual do Fusion 26
  (vmenet/bridge): frames unicast nao sao entregues ao guest — firewall
  do Windows inocente (log de drops vazio, regras Allow ok, sshd
  LocalSystem escutando, perfis Private).
- Acesso definitivo: tunel SSH reverso guest->Mac —
  `ssh -i ~/.ssh/ssa_debian_arm64 -p 2224 build@127.0.0.1`.
  Persistencia via Scheduled Task `SSA-ReverseSSH` (SYSTEM, AtStartup,
  retry 10s). Chave dedicada `ssa_w11arm_tunnel` restrita a
  port-forwarding no authorized_keys do Mac.
- Canal oficial alternativo sem rede: `vmrun -gu build -gp menon`
  (runProgramInGuest + CopyFileFromHostToGuest/FromGuestToHost).
- Detalhes completos na skill `~/.config/devin/skills/w11arm-vm-access/SKILL.md`.

## Falha do pytest-full no GitLab (pipeline 66, f5aec1e4)

Duas falhas so no Linux do CI (ambas passam no macOS), investigadas com
reproducao em ambiente identico ao do job (mesma imagem/apt/uv em container
linux/amd64):

1. `test_details_db_signature_memoized_by_db_and_wal_generation` —
   DEFEITO REAL. `_details_db_file_generation` incluia `st_ctime_ns` no
   slot de cada arquivo; no Linux cada consulta read-only ao WAL altera o
   ctime do `-wal` sem mudar conteudo (+3ms medido por render, mtime/size/
   ino estaveis), derrubando a memoizacao a cada chamada. No macOS o ctime
   nao varia; no Windows st_ctime e creation time (constante). Fix:
   ctime ignorado somente no slot `-wal` (`gui/ssa/gui_details.py`);
   `.db`/`-journal` mantidos. Invalidacao continua coberta por size/
   mtime_ns do -wal (commits) e dev/ino (troca por rename).
2. `test_seed_runtime_folder_updates_previous_bundle_file` — FLAKE de
   teste (falhou nas pipelines 64 e 66, passou na 65). O marker do seed
   compara `st_mtime_ns+st_size` do diretorio-fonte; o teste usava
   `os.utime(dir, None)`, que pode cair no mesmo tick de timestamp do FS
   do runner e nao alterar o marker -> early-return mantinha `bundle-v1`.
   Fix no teste: `os.utime` com `ns=` explicito +5s (2 pontos, incluindo o
   teste irmao com o mesmo padrao). Codigo de producao intocado.

Validacao: 18/18 testes dos 2 modulos no macOS e no container Linux;
105 passed + 8 skipped nos modulos adjacentes (release_artifact_guard,
shell_ci_contracts). Suite completa no container: 3060 passed, as demais
falhas foram artefatos da copia sem `.git`, confirmadas verdes com o
mount completo. Sem commit/push; verde no CI so se confirma na proxima
pipeline apos publicar.

## Ambiente de teste Linux definitivo (~/.local/share/ssa-test-linux)

Container exclusivo de teste via `container` da Apple (apiserver em
`container system start`), imagem `ssa-test` linux/amd64 identica ao job
pytest-full (mesma base, apt e `uv sync --frozen --extra dev`):

- Build: `bash ~/.local/share/ssa-test-linux/build.sh` (contexto = so a pasta +
  pyproject/uv.lock copiados; repo de 5+ GB nao vira contexto).
- Uso: `bash ~/.local/share/ssa-test-linux/run.sh [args pytest]` — container efemero
  `--rm`, repo montado read-only em `/src`, venv em `/opt/venv`.
- amd64 e o alvo de paridade com o CI; arm64 exige base com glibc>=2.39
  (pyqt6-qt6 so tem wheel manylinux_2_39_aarch64; bookworm e 2.36).
- Documentacao completa: `~/.local/share/ssa-test-linux/README.md`.
- Equivalente macOS: nao ha container nativo para guests macOS; o analogo
  e VM descartavel via Tart (Virtualization.framework, imagens OCI,
  clone CoW por execucao). Nao instalado neste host; a suite macOS roda
  nativa e a VM so se justifica por isolacao de ambiente.

## Briefing: avaliacao do merge dev -> main

Documento para um modelo/avaliador externo analisar a promocao `dev` -> `main`
do SSA_Consulta_Rapida. Escopo: AVALIAR e recomendar. Nao executar merge,
nao criar branch/PR, nao dar push e nao reescrever historico sem autorizacao
explicita do usuario.

### 1. Estado medido (19/09/2026)

- Repo local: `/Users/menon/git/SSA_Consulta_Rapida`, branch `dev`.
- Pontas: `dev` = `f5aec1e4` (merge PR #132, versao 4.50);
  `main` = `2d80af2c` ("RECONCILIATION: preserve GitHub original and
  schottge main histories").
- Contagem: `dev` esta 378 commits a frente, `main` 2 commits a frente
  (`git rev-list --left-right --count origin/main...origin/dev`).
- `git cherry` vazio: os 2 commits de main ja estao absorvidos em dev por
  patch — nenhum conteudo de main seria perdido.
- Merge bases multiplas (criss-cross): `f7304677` ("Clean snapshot of
  main. Original commit bdf379b...") e `ae36e281` ("STABILITY_PATCH
  address cubic review findings").
- Merge ortodoxo medido: `git merge-tree --write-tree origin/main
  origin/dev` retorna exit 1 com ~77 arquivos em conflito de conteudo —
  ruido do criss-cross, nao divergencia semantica real.

### 2. Historia reconstruida (contexto obrigatorio)

- 15/08/2026: main e dev foram reescritos como "clean snapshots"
  (`f7304677` main; `3318e4ce` "Clean snapshot of dev", 449 arquivos,
  +34,6k linhas), filhos um do outro.
- 31/08/2026: reconciliacoes costuraram as cadeias originais de volta:
  `c1770108` (dev: "preserve GitLab and schottge dev histories") e
  `2d80af2c` (main). Por isso ha 2 merge bases e por isso o merge
  ortodoxo conflita.
- Fossil pre-reescrita preservado no Bitbucket: `main`=`bdf379b0`,
  `dev`=`64752aa9` (citados como "Original commit" nas mensagens dos
  snapshots). Fetch do bitbucket pode falhar (acesso SSH); refs sao do
  ultimo fetch bem-sucedido.

### 3. Remotos (fetch de 19/09/2026)

| remoto | dev | main | nota |
| --- | --- | --- | --- |
| origin (GitHub mauriciomenon) | f5aec1e4 | 2d80af2c | push multiplo: GitHub+Schottge+GitLab |
| schottge | f5aec1e4 | 2d80af2c | identico |
| gitlab | f5aec1e4 | 2d80af2c | identico; pipeline #66 falhou (ver secao 7) |
| bitbucket | 64752aa9 | bdf379b0 | linha pre-rewrite, stale (fetch falha) |

`git diff` entre `origin/dev`, `schottge/dev` e `gitlab/dev`: zero.

### 4. Divergencia de conteudo

- Diff ponta-a-ponta `main...dev`: 528 arquivos alterados,
  ~+46.484/-19.848 linhas (vs merge base: 571 arq., +55.694/-21.183).
- `dev` carrega releases 4.43->4.50; `main` parou na linha 4.42. Tags
  `v4.45.2`, `v4.46`, `v4.50` sao ancestrais de dev e ausentes de main.
- Maior arquivo divergente: `uv.lock` (-68 pacotes, +1 numpy; pywin32->312).
- Autoria em dev: 100% "Mauricio Menon" com emails autorizados
  (`mauriciomenon@users.noreply.github.com`, `54405514+...`,
  `mauricio.menon@gmail.com`).

### 5. Opcoes de merge a avaliar

A) **`git merge -s ours origin/main` dentro de dev**, depois PR dev->main.
   O elo de ancestralidade resolve o criss-cross; o merge do PR fica
   trivial e sem conflito. Resultado final = arvore de dev (desejado, ja
   que main esta absorvido). Recomendacao previa do relatorio.
B) **Merge ortodoxo direto** (PR dev->main): ~77 arquivos em conflito
   medido; resolveria "dev vence" em todos, mas a janela de review fica
   grande e com ruido espurio.
C) **Reescrita**: proibida sem autorizacao especifica.

Avaliar e recomendar entre A e B com justificativa; confirmar com
`git merge-tree` proprio antes de concluir.

### 6. Checklist de verificacao para o avaliador

```bash
cd /Users/menon/git/SSA_Consulta_Rapida
git fetch --all --prune            # bitbucket pode falhar; marcar stale
git rev-list --left-right --count origin/main...origin/dev
git merge-base --all origin/main origin/dev
git cherry origin/main origin/dev  # deve ser vazio
git merge-tree --write-tree origin/main origin/dev   # exit 1, ~77 conflitos
git diff --stat origin/main origin/dev
git log --format=fuller -5 origin/dev   # conferir autoria
git status --short                 # ha mudancas locais (secao 7)
```

Criterios de aceite da avaliacao: nenhum patch exclusivo de main perdido;
lista de conflitos explicada; recomendacao com riscos e plano de rollback;
nao afirmar sucesso de CI sem pipeline verde.

### 7. Estado pendente no working tree (nao commitado)

- `gui/ssa/gui_details.py`: fix real — ctime do `-wal` ignorado na
  geracao de assinatura (memoizacao nunca funcionava em Linux; causa da
  falha do pipeline #66). Validado macOS+Linux.
- `tests/test_main_frozen_runtime.py`: `os.utime` deterministico (flake
  de granularidade de FS no runner; falhou nas pipelines 64/66).
- `docs/BUILD_WINDOWS_ARM64_AMD64.md`, `docs/TESTING_STRATEGY.md`,
  `docs/BUILD_TOOLING_LESSONS_LEARNED.md`: docs de acesso VM e ambiente
  de teste.
- `docs/REVIEW_SEG_SINC_v4.50_dev_20260918.md` (untracked): relatorio
  completo da rodada — ler antes de avaliar; contem evidencias de build
  dos 3 alvos e a comparacao detalhada de remotos.

O avaliador deve decidir se esses arquivos entram no commit de preparacao
do merge ou ficam fora — nao commitar por conta propria.

### 8. Evidencias de release (mesmo commit f5aec1e4)

- Windows amd64: `builds/packages/windows_amd64/` (PE 0x8664, smoke ok,
  sha256 135cbf9a…).
- Windows arm64: `builds/packages/windows_arm64/` (PE 0xaa64, smoke ok,
  sha256 c5426878…).
- macOS arm64: `launchers/dist/macos_arm64/` (Mach-O arm64, DMG verify
  VALID, sha256 c2b90398…).
- Relatorios: `builds/reports/release_report_windows_{amd64,arm64}.json`.

### 9. Regras obrigatorias do repositorio

- Autoria exclusivamente humana (Mauricio Menon); proibidos
  Co-authored-by/Generated-by/Signed-off-by e creditos a assistentes.
- Portugues ASCII em mensagens tecnicas; sem emoji/emdash em codigo.
- `uv run --no-sync` para Python; validacao minima: py_compile + ruff +
  pytest focado.
- Nao comitar `.env`, `.envrc`, `.python-version`, configs locais de
  ferramentas, binarios ou `builds/`.
- Reportar: entregue / parcial / nao feito, com comandos e evidencia.

### 10. Referencias

- `docs/REVIEW_SEG_SINC_v4.50_dev_20260918.md` — relatorio da rodada
  (divergencia, remotos, builds, VM, falha CI).
- `docs/BUILD_WINDOWS_ARM64_AMD64.md` — runbook de builds + acesso VM.
- `docs/TESTING_STRATEGY.md` — inclui ambiente de teste Linux local
  (`~/.local/share/ssa-test-linux`, imagem `ssa-test`).
- `AGENTS.md` — regras de autorizacao e autoria.
- Skill local `~/.config/devin/skills/w11arm-vm-access/SKILL.md` — acesso
  definitivo a VM Windows.
